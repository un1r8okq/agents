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
