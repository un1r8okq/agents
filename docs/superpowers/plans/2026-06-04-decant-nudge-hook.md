# Decant Nudge Hook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `SessionStart` hook that detects undecanted past daily notes (last 14 days) and nudges the user to run `/decant`, without ever auto-running it.

**Architecture:** A self-contained, portable bash script lives at `skills/decant/hooks/undecanted-notes.sh`. It reads the session `cwd` from the hook's stdin JSON, acts only when inside the vault or the skills repo, scans `$OBSIDIAN_VAULT/daily` for `YYYY-MM-DD.md` notes from the last 14 days lacking a `# Summary`, and prints a nudge to stdout (which Claude Code injects as session context). A bash test harness validates it against a fixture matrix. The hook is wired into user-scope `~/.claude/settings.json`.

**Tech Stack:** bash 5.x (GNU; BSD `date` fallback included), `jq` (with a `sed` fallback), GNU coreutils. No Python.

**Reference spec:** `docs/superpowers/specs/2026-06-04-decant-nudge-hook-design.md`

---

## Setup: branch

We are on `main`. Create a feature branch before committing.

- [ ] **Create branch**

```bash
cd /c/dev/agents
git checkout -b feat/decant-nudge-hook
```

---

## File Structure

- **Create:** `skills/decant/hooks/undecanted-notes.sh` — the hook (cwd guard, vault resolution, scan, nudge).
- **Create:** `skills/decant/hooks/test-undecanted-notes.sh` — standalone bash test harness.
- **Create:** `skills/decant/hooks/README.md` — what the hook does + install snippet (reproducible, committable).
- **Modify:** `~/.claude/settings.json` — register the `SessionStart` hook (user scope, outside the repo; not committed).

---

## Task 1: Write the failing test harness

**Files:**
- Create: `skills/decant/hooks/test-undecanted-notes.sh`

The test builds a temp vault with a fixture matrix and asserts the hook's stdout. It is written first; with no script present yet it must fail.

- [ ] **Step 1: Write the test harness**

Create `skills/decant/hooks/test-undecanted-notes.sh`:

```bash
#!/usr/bin/env bash
# Tests for undecanted-notes.sh — builds a temp vault and asserts hook output.
set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
hook="$here/undecanted-notes.sh"

fails=0
pass() { printf 'PASS: %s\n' "$1"; }
fail() { printf 'FAIL: %s\n' "$1"; fails=$((fails + 1)); }

# Date N days ago (GNU date, with BSD/macOS fallback)
d_ago() { date -d "$1 days ago" +%F 2>/dev/null || date -v-"$1"d +%F; }

# Pipe a hook stdin JSON with the given cwd, run the hook with a controlled env.
# CLAUDE_ENV_FILE points at a nonexistent path so the vault fallback never sources
# the real machine env.
run_hook() {
  local vault="$1" cwd="$2"
  printf '{"cwd":"%s"}' "$cwd" \
    | OBSIDIAN_VAULT="$vault" CLAUDE_ENV_FILE="/nonexistent-$$" bash "$hook"
}

# --- Fixtures ---
vault="$(mktemp -d)"
mkdir -p "$vault/daily"
IN1="$(d_ago 2)"      # in-window, undecanted
IN2="$(d_ago 4)"      # in-window, undecanted
DEC="$(d_ago 3)"      # in-window, decanted (has # Summary)
EMPTY="$(d_ago 5)"    # in-window, empty (no content filter -> still listed)
OLD="$(d_ago 20)"     # out of window
TODAY="$(date +%F)"   # today -> excluded

printf '# Notes\n- did stuff\n'              > "$vault/daily/$IN1.md"
printf '# Notes\n- more stuff\n'             > "$vault/daily/$IN2.md"
printf '# Summary\n- decanted\n\n# Notes\n'  > "$vault/daily/$DEC.md"
: > "$vault/daily/$EMPTY.md"
printf '# Notes\n- ancient\n'                > "$vault/daily/$OLD.md"
printf '# Notes\n- today\n'                  > "$vault/daily/$TODAY.md"
printf '# Notes\n'                           > "$vault/daily/template.md"

# --- Test 1: happy path (cwd inside vault) ---
out="$(run_hook "$vault" "$vault")"
case "$out" in *"$IN1"*)   pass "lists in-window undecanted ($IN1)";; *) fail "missing $IN1 -- got: $out";; esac
case "$out" in *"$IN2"*)   pass "lists in-window undecanted ($IN2)";; *) fail "missing $IN2 -- got: $out";; esac
case "$out" in *"$EMPTY"*) pass "lists empty in-window note (no content filter)";; *) fail "missing empty $EMPTY";; esac
case "$out" in *"$DEC"*)   fail "should NOT list decanted $DEC";;  *) pass "excludes decanted note";; esac
case "$out" in *"$OLD"*)   fail "should NOT list out-of-window $OLD";; *) pass "excludes out-of-window note";; esac
case "$out" in *"$TODAY"*) fail "should NOT list today $TODAY";; *) pass "excludes today";; esac
case "$out" in *template*) fail "should NOT list template.md";; *) pass "excludes template.md";; esac
case "$out" in *"/decant"*) pass "includes offer-to-decant instruction";; *) fail "missing offer instruction";; esac

# --- Test 2: cwd outside vault and skills repo -> silent ---
out="$(run_hook "$vault" "/")"
[ -z "$out" ] && pass "silent when cwd outside allowed roots" || fail "expected silence, got: $out"

# --- Test 3: vault unset -> silent ---
out="$(printf '{"cwd":"%s"}' "$vault" | OBSIDIAN_VAULT="" CLAUDE_ENV_FILE="/nonexistent-$$" bash "$hook")"
[ -z "$out" ] && pass "silent when OBSIDIAN_VAULT unset" || fail "expected silence, got: $out"

# --- Test 4: nothing to decant -> silent ---
empty_vault="$(mktemp -d)"; mkdir -p "$empty_vault/daily"
out="$(run_hook "$empty_vault" "$empty_vault")"
[ -z "$out" ] && pass "silent when nothing qualifies" || fail "expected silence, got: $out"
rm -rf "$empty_vault"

# --- Cleanup + result ---
rm -rf "$vault"
if [ "$fails" -eq 0 ]; then echo "All tests passed."; exit 0; else echo "$fails test(s) failed."; exit 1; fi
```

- [ ] **Step 2: Make it executable and run it — expect FAIL**

```bash
chmod +x skills/decant/hooks/test-undecanted-notes.sh
skills/decant/hooks/test-undecanted-notes.sh
```

Expected: the script-under-test does not exist yet, so `bash "$hook"` errors (`No such file or directory`), every assertion fails, and the harness exits non-zero with `N test(s) failed.`

- [ ] **Step 3: Commit the failing test**

```bash
git add skills/decant/hooks/test-undecanted-notes.sh
git commit -m "test: add failing harness for decant nudge hook"
```

---

## Task 2: Implement the hook script

**Files:**
- Create: `skills/decant/hooks/undecanted-notes.sh`
- Test: `skills/decant/hooks/test-undecanted-notes.sh` (from Task 1)

- [ ] **Step 1: Write the hook script**

Create `skills/decant/hooks/undecanted-notes.sh`:

```bash
#!/usr/bin/env bash
# SessionStart hook — nudge about undecanted past daily notes.
#
# Scans $OBSIDIAN_VAULT/daily for YYYY-MM-DD.md notes from the last 14 days that
# lack a "# Summary" heading and prints a nudge to stdout (SessionStart stdout is
# injected as session context). Offers; never auto-runs /decant. Always exits 0.

set -u
export LC_ALL=C

# --- Read the hook's stdin JSON; extract cwd (fallback: $PWD) ---
stdin_json="$(cat 2>/dev/null || true)"
cwd=""
if [ -n "$stdin_json" ] && command -v jq >/dev/null 2>&1; then
  cwd="$(printf '%s' "$stdin_json" | jq -r '.cwd // empty' 2>/dev/null || true)"
fi
if [ -z "$cwd" ] && [ -n "$stdin_json" ]; then
  cwd="$(printf '%s' "$stdin_json" \
    | sed -n 's/.*"cwd"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)"
fi
[ -z "$cwd" ] && cwd="$PWD"

# --- Resolve the vault (portable, with CLAUDE_ENV_FILE fallback) ---
if [ -z "${OBSIDIAN_VAULT:-}" ] && [ -n "${CLAUDE_ENV_FILE:-}" ] && [ -f "${CLAUDE_ENV_FILE}" ]; then
  # shellcheck disable=SC1090
  . "$CLAUDE_ENV_FILE" 2>/dev/null || true
fi
vault="${OBSIDIAN_VAULT:-}"
[ -n "$vault" ] || exit 0
[ -d "$vault" ] || exit 0

# --- Self-locate the skills-repo root (no hardcoded paths) ---
hooks_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"   # .../skills/decant/hooks
skills_repo="$(cd "$hooks_dir/../../.." && pwd -P)"            # repo root containing skills/

# --- Normalise cwd and vault for prefix matching ---
norm() { (cd "$1" 2>/dev/null && pwd -P) || printf '%s' "$1"; }
cwd="$(norm "$cwd")"
vault="$(norm "$vault")"

# --- cwd guard: act only inside the vault or the skills repo ---
case "$cwd" in
  "$vault"|"$vault"/*|"$skills_repo"|"$skills_repo"/*) : ;;
  *) exit 0 ;;
esac

# --- Window bounds: lower (14 days ago) <= d < today ---
today="$(date +%F)"
if ! lower="$(date -d '14 days ago' +%F 2>/dev/null)"; then
  lower="$(date -v-14d +%F 2>/dev/null)"   # BSD/macOS date fallback
fi
[ -n "$lower" ] || exit 0

# --- Scan for in-window undecanted notes (glob excludes template.md by shape) ---
found=()
shopt -s nullglob
for f in "$vault"/daily/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md; do
  d="$(basename "$f" .md)"
  [[ "$d" < "$lower" ]] && continue   # older than the window
  [[ "$d" < "$today" ]] || continue   # today or future -> exclude
  grep -q '^# Summary' "$f" || found+=("$d")
done
shopt -u nullglob

[ "${#found[@]}" -eq 0 ] && exit 0

# --- Build a "a, b, c" list (glob already yields chronological order) and emit ---
list="$(printf '%s, ' "${found[@]}")"; list="${list%, }"

cat <<EOF
Undecanted daily notes (no \`# Summary\`) from the last 14 days: ${list}.
These past daily notes haven't been decanted. Briefly mention them to the user and offer to run the
/decant skill on them. Do NOT start decanting unless the user agrees — it is a heavy, interactive
process. Offer; don't auto-run.
EOF
exit 0
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x skills/decant/hooks/undecanted-notes.sh
```

- [ ] **Step 3: Run the test harness — expect PASS**

```bash
skills/decant/hooks/test-undecanted-notes.sh
```

Expected: every line `PASS: ...` and a final `All tests passed.` (exit 0).

- [ ] **Step 4: Lint the script (optional but recommended)**

```bash
command -v shellcheck >/dev/null && shellcheck skills/decant/hooks/undecanted-notes.sh || echo "shellcheck not installed; skipping"
```

Expected: no errors (informational warnings acceptable). If shellcheck is absent, skip.

- [ ] **Step 5: Commit**

```bash
git add skills/decant/hooks/undecanted-notes.sh
git commit -m "feat: add decant nudge SessionStart hook script"
```

---

## Task 3: Document the hook (install README)

**Files:**
- Create: `skills/decant/hooks/README.md`

- [ ] **Step 1: Write the README**

Create `skills/decant/hooks/README.md`:

````markdown
# decant hooks

## undecanted-notes.sh

A `SessionStart` hook that nudges about undecanted past daily notes.

When a Claude Code session starts **inside the Obsidian vault (`$OBSIDIAN_VAULT`) or this
skills repo**, the hook scans `$OBSIDIAN_VAULT/daily` for `YYYY-MM-DD.md` notes from the last
14 days that lack a `# Summary` heading (the marker `/decant` writes), and prints a nudge to
stdout. Claude Code injects that as session context. The hook **offers**; it never runs
`/decant` automatically.

Paths are portable: the vault comes from `$OBSIDIAN_VAULT`, and the skills-repo root is
self-located from the script's own path. The only required contract is that `$OBSIDIAN_VAULT`
is set (the same contract the `decant`/`obsidian` skills already assume).

### Install

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|clear",
        "hooks": [
          { "type": "command", "command": "$HOME/.claude/skills/decant/hooks/undecanted-notes.sh" }
        ]
      }
    ]
  }
}
```

`compact` is intentionally excluded so the nudge does not re-fire after mid-session
auto-compaction. If these skills are ever packaged as a Claude Code plugin, use
`${CLAUDE_PLUGIN_ROOT}/hooks/undecanted-notes.sh` instead.

### Test

```bash
skills/decant/hooks/test-undecanted-notes.sh
```
````

- [ ] **Step 2: Commit**

```bash
git add skills/decant/hooks/README.md
git commit -m "docs: document decant nudge hook and install steps"
```

---

## Task 4: Wire the hook into settings.json + manual smoke test

**Files:**
- Modify: `~/.claude/settings.json` (user scope — not in the repo, not committed)

- [ ] **Step 1: Back up current settings**

```bash
cp ~/.claude/settings.json ~/.claude/settings.json.bak
```

- [ ] **Step 2: Add the SessionStart hook via jq**

The single-quoted value keeps `$HOME` as a literal string in the JSON (the hook runner shell
expands it at execution time).

```bash
cmd='$HOME/.claude/skills/decant/hooks/undecanted-notes.sh'
tmp="$(mktemp)"
jq --arg cmd "$cmd" \
  '.hooks.SessionStart = [{"matcher":"startup|resume|clear","hooks":[{"type":"command","command":$cmd}]}]' \
  ~/.claude/settings.json > "$tmp" && mv "$tmp" ~/.claude/settings.json
```

- [ ] **Step 3: Verify the JSON is valid and contains the hook**

```bash
jq '.hooks' ~/.claude/settings.json
```

Expected:
```json
{
  "SessionStart": [
    {
      "matcher": "startup|resume|clear",
      "hooks": [
        {
          "type": "command",
          "command": "$HOME/.claude/skills/decant/hooks/undecanted-notes.sh"
        }
      ]
    }
  ]
}
```

- [ ] **Step 4: Manual smoke — direct invocation inside the vault**

```bash
echo '{"cwd":"'"$OBSIDIAN_VAULT"'"}' | $HOME/.claude/skills/decant/hooks/undecanted-notes.sh
```

Expected: a nudge listing the currently-undecanted in-window notes (at the time of writing:
`2026-05-31, 2026-06-01, 2026-06-02, 2026-06-03`), ending with the offer-to-decant instruction.

- [ ] **Step 5: Manual smoke — outside the allowed roots is silent**

```bash
echo '{"cwd":"/tmp"}' | $HOME/.claude/skills/decant/hooks/undecanted-notes.sh; echo "exit=$?"
```

Expected: no output, `exit=0`.

- [ ] **Step 6: Manual smoke — real session**

Start a fresh Claude Code session with the working directory set to the vault, and confirm the
assistant proactively mentions the undecanted notes and offers to decant (without starting).
Then start a session in an unrelated repo and confirm no nudge appears.

---

## Self-Review

**Spec coverage:**
- Trigger = `SessionStart`, cwd guard for vault + skills repo → Task 2 (cwd guard), Task 4 (matcher). ✓
- 14-day window, excludes today → Task 2 (window bounds), Task 1 (fixtures IN/OLD/TODAY). ✓
- `YYYY-MM-DD.md` only, excludes `template.md` → Task 2 (numeric glob), Task 1 (template fixture). ✓
- No content filter (empty notes surfaced) → Task 1 (EMPTY fixture asserts listed). ✓
- Offer, never auto-run → Task 2 (nudge text), Task 1 (`/decant` instruction assertion). ✓
- Portability: `$OBSIDIAN_VAULT`, self-located repo, `$HOME` command path, env fallback → Task 2 + Task 4. ✓
- Error handling: silent outside roots / vault unset / nothing found; always exit 0 → Task 1 Tests 2–4. ✓
- Testing matrix → Task 1. ✓

**Placeholder scan:** No TBD/TODO; all steps contain runnable code or exact commands with expected output.

**Type/name consistency:** Script path `skills/decant/hooks/undecanted-notes.sh` and command `$HOME/.claude/skills/decant/hooks/undecanted-notes.sh` consistent across Tasks 2–4 and README. Matcher `startup|resume|clear` consistent in Task 4 and README. Helper names (`run_hook`, `d_ago`, `norm`) used consistently.

**Non-goals (unchanged from spec):** no content filtering, no auto-run, no window config, no notes outside `daily/`, no plugin packaging.
