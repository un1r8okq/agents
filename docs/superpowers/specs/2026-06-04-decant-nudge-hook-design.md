# Decant Nudge Hook — Design

**Date:** 2026-06-04
**Status:** Approved (design)

## Problem

Daily Obsidian notes accumulate undecanted (no `# Summary` section). Remembering *which* past
notes still need decanting is its own burden — the actual `/decant` run is interactive and
judgement-heavy, so it cannot be fully automated, but the *remembering* can be.

This is "Option A" from the brainstorm: a hook that **detects and nudges**, never one that
decants unattended. `/decant` keeps all its interactive guardrails (Phase 3 ambiguity, Phase 7
focus/concerns); the hook only surfaces the backlog and offers.

## Why not automate the decant itself

`/decant` fans out writes across the whole vault (person notes, org notes, `timeline.md`,
`context.md`) and is saturated with "ask in Phase 3" judgement calls. It also has two
`AskUserQuestion` gates that cannot run with nobody present. Automating away the human means
automating away the safety. So the hook stops at "offer".

## Behaviour summary

| Decision | Choice |
|---|---|
| Trigger | `SessionStart` hook, acts only when cwd is under the vault **or** the skills repo |
| Window | Undecanted `YYYY-MM-DD.md` notes from the last 14 days (excludes today) |
| Content filter | None — surface all in-window undecanted notes |
| Behaviour | Inject the list + instruction to *mention and offer*; never auto-run `/decant` |
| Portability | All paths self-locate or come from `$OBSIDIAN_VAULT`; no hardcoded machine paths |

## Component 1 — the hook script

**Location:** `skills/decant/hooks/undecanted-notes.sh` (executable, in git, co-located with the
skill it serves).

**Inputs:**
- Claude Code passes a JSON object on **stdin** containing a `cwd` field. The script reads `cwd`
  from it, falling back to `$PWD` if parsing fails or the field is absent.
- Vault path from `$OBSIDIAN_VAULT`.

**Vault resolution (portable, with fallback):**
1. If `$OBSIDIAN_VAULT` is set, use it.
2. Else, if `$CLAUDE_ENV_FILE` exists, source it and re-check `$OBSIDIAN_VAULT`.
3. Else exit 0 silently — on a machine without the vault configured, the hook does nothing.

**Skills-repo root (self-located, no hardcode):** derive from the script's own path via
`BASH_SOURCE`/`realpath` — walk up from `…/skills/decant/hooks/` to the skills root. This is the
"skills repo" arm of the cwd guard.

**Logic:**
1. **cwd guard** — resolve the session cwd. If it is **not** under `$OBSIDIAN_VAULT` and **not**
   under the self-located skills-repo root, exit 0 with no output.
2. **Window** — `today = date +%F`; `lower = date -d "14 days ago" +%F`. A note date `d`
   qualifies when `lower ≤ d < today` (lexicographic comparison on `YYYY-MM-DD` is valid).
3. **Scan** — glob `"$OBSIDIAN_VAULT"/daily/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md`. The
   numeric glob inherently excludes `template.md` and any non-date file. For each in-window file,
   collect its date if `grep -q '^# Summary' "$f"` **fails** (not yet decanted).
4. **Emit** — if any collected, print the nudge to stdout; otherwise exit 0 silently.

**Output (plain stdout — `SessionStart` stdout is injected as session context):**

```
Undecanted daily notes (no `# Summary`) from the last 14 days: 2026-05-31, 2026-06-01, 2026-06-02, 2026-06-03.
These past daily notes haven't been decanted. Briefly mention them to the user and offer to run the
/decant skill on them. Do NOT start decanting unless the user agrees — it is a heavy, interactive
process. Offer; don't auto-run.
```

(The date list is generated; the instructional text is fixed.)

**Error handling:**
- Vault missing/unset → exit 0 silent (see vault resolution).
- cwd outside the two allowed roots → exit 0 silent.
- Never write to stderr (would surface to the user as error noise).
- **Always exit 0** — a `SessionStart` hook must never block a session from starting.

## Component 2 — the wiring

Add to `~/.claude/settings.json` (user scope, so it applies to every session regardless of
where it starts — the cwd guard does the filtering):

```json
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
```

- Command path routes through the `~/.claude/skills` symlink via `$HOME` (shell-evaluated), not
  the machine-specific repo path. Portable to any machine where the skills live under
  `~/.claude/skills`.
- `compact` is deliberately excluded from the matcher so the nudge doesn't re-fire after
  mid-session auto-compaction.
- If these skills are ever packaged as a Claude Code *plugin*, the portable command form becomes
  `${CLAUDE_PLUGIN_ROOT}/hooks/undecanted-notes.sh`. Out of scope now; noted for the future.

## Testing

**Standalone script test** (`skills/decant/hooks/test-undecanted-notes.sh`): build a temp vault
with a fixture matrix and assert the emitted output:

| Fixture | Expected |
|---|---|
| Decanted in-window note (`# Summary` present) | not listed |
| Undecanted in-window note | listed |
| Undecanted out-of-window note (>14 days old) | not listed |
| `template.md` (no date filename, no `# Summary`) | not listed |
| Empty undecanted in-window note | listed (no content filter) |

Plus:
- cwd outside both allowed roots → no output, exit 0.
- No qualifying notes → no output, exit 0.
- `$OBSIDIAN_VAULT` unset and no `$CLAUDE_ENV_FILE` → no output, exit 0.

**Manual smoke:** start a session in the vault → nudge appears; start one in an unrelated repo →
silence.

## Non-goals (YAGNI)

- No content/empty filtering — surface all in-window undecanted notes.
- No auto-running `/decant`.
- No config file for the window; `14` is a constant in the script.
- No handling of notes outside `daily/`.
- No plugin packaging (noted as future portability path only).
