# Vault-validate SessionStart hook — design

**Status:** approved design, pre-implementation
**Date:** 2026-06-08
**Origin:** [`knowledgebase-review-2026-06-08`](../../../../notes/meta/knowledgebase-review-2026-06-08.md) — the "Automatability / Job 1" sketch. The user has no long-running sessions, so a SessionStart hook (not a cron/cloud routine) is the right mechanism.

## Goal

A deterministic, zero-dependency vault validator that runs at session start, detects integrity/convention defects, and **nudges** the user — turning the review's one-off findings into "can't silently come back" gates. It supersedes the dead vault-root `validate.py` (wrong schema, won't run — missing PyYAML).

Primary lens: **agent answer quality**. The defects it catches (empty notes, filename collisions) cause an agent to traverse to *nothing* or resolve a wikilink nondeterministically.

## Principles

- **Report-only, never mutates the vault.** It offers; it never edits. (`--fix` is a future, opt-in increment.)
- **Never disrupts the session.** Any error → print nothing → exit 0.
- **Silent when clean.** Output only when there are findings (mirrors the decant hook).
- **Zero external dependencies.** No PyYAML — the failure that killed the old validator. Frontmatter is read with a hand-rolled line scanner when needed (not in the MVP).
- **Incremental.** Ship the smallest useful slice, see it fire, then add checks.

## Architecture

New file: `skills/obsidian/hooks/validate-vault.py` — co-located with the `obsidian` skill, which owns the conventions it enforces. Reachable from settings as `$HOME/.claude/skills/obsidian/hooks/validate-vault.py` (the `~/.claude/skills → repo/skills` symlink).

### Two seams (this split is the point of TDD-ing it)

1. **Pure check functions** — the logic, unit-tested directly:
   - `find_empty_notes(vault: Path) -> list[Path]` — `*.md` files that are 0-byte or whitespace-only.
   - `find_duplicate_basenames(vault: Path) -> list[tuple[str, list[Path]]]` — basenames appearing in 2+ directories.
   - Each returns plain data; no I/O beyond reading the tree. Increments 2–4 add more functions of this shape.
2. **Thin hook shell** — I/O and safety, integration-tested via subprocess:
   - Read stdin JSON; extract `cwd` (stdlib `json`, fallback to `$PWD`).
   - Resolve `$OBSIDIAN_VAULT` (env; `CLAUDE_ENV_FILE` fallback, matching the decant hook).
   - cwd-guard: act only when `cwd` is inside the vault or the skills repo; else exit 0.
   - Run the registered checks, format findings, print the nudge, `exit 0`.
   - Whole body wrapped in `try/except` → on any exception, print nothing, exit 0.

### Hook contract

Mirrors `skills/decant/hooks/undecanted-notes.sh`: SessionStart, stdin = hook JSON, stdout = injected session context, always exit 0.

### Registration

Add a *second* SessionStart hook entry alongside the decant nudge in `~/.claude/settings.json` (matcher `startup|resume|clear`), using the `update-config` skill. Document the install + the supersession of the old `validate.py` in the repo `README.md`.

## Increment 1 — MVP (this spec's build target)

Two pure, zero-false-positive checks:

| Check | Detects | Known first-run hit |
| --- | --- | --- |
| Empty notes | 0-byte / whitespace-only `*.md` | `people/Mike Nguyen 1.md` |
| Duplicate basenames | same filename in 2+ dirs (Obsidian collision) | `Microsoft Practice Catch-up.md` (engagements/ + misc/) |

**Output (only when findings exist)** — a concise nudge to stdout, e.g.:

```
Vault integrity issues found by validate-vault:
- Empty note (0 bytes): people/Mike Nguyen 1.md — an empty note is a dead wikilink target.
- Duplicate basename "Microsoft Practice Catch-up.md": engagements/ + misc/ — wikilinks resolve nondeterministically.
Mention these to the user and offer to fix; do NOT auto-edit the vault.
```

The nudge states only what the checks compute (the 0-byte fact, the colliding paths). Richer enrichment (inbound-link counts, "likely a duplicate of X") is deliberately deferred — the MVP does not parse links.

**Acceptance:** on the real vault, the first run flags exactly those two issues; after they're fixed, the hook is silent.

## Increment roadmap (each a separate ship, after the prior proves out)

- **Inc 2 — discovery checks:** missing required `description:`; non-lowercase / missing required frontmatter keys (catches the `background`-skill drift class + the ~20 missing descriptions). Adds the hand-rolled frontmatter line scanner. Still pure-deterministic, no deps.
- **Inc 3 — freshness nudges:** person notes stale vs recent mentions; engagement `context.md` older than recent activity; `todo.md` staleness (the decant-lag theme). Heuristic; nudges to `refresh-person` / `decant`.
- **Inc 4 (optional) — warnings tier + opt-in `--fix`:** bare-first-name links, high-frequency dangling links, oversized notes, doc-path existence; safe auto-fix for trivial cases (empty vestigial dirs, key-case normalisation).

## Error handling

- Vault unset / not a directory → exit 0, no output.
- Malformed or empty stdin → fall back to `$PWD` for the cwd-guard.
- Any exception anywhere → swallow, print nothing, exit 0. The hook must never block or noise up a session.
- No network, single `os.walk` — fast.

## Testing (TDD)

`skills/obsidian/hooks/test_validate_vault.py` (pytest, per repo convention):

- **Unit (check functions, written test-first):**
  - empty 0-byte note is found; whitespace-only note is found; non-empty note is not.
  - basename in two dirs is reported with both paths; unique basenames are not.
  - clean fixture vault → both functions return empty.
- **Integration (subprocess, crafted stdin):**
  - cwd inside vault → runs; cwd outside vault and skills repo → silent, exit 0.
  - malformed stdin JSON → exit 0 (falls back to `$PWD`).
  - findings present → nudge on stdout, exit 0; clean vault → no stdout, exit 0.

Quality bar: match the decant hook's green suite. Fixtures build a throwaway temp vault (`tmp_path`), so tests never touch the real vault.

## Out of scope (explicitly)

- Auto-fixing / mutating the vault (deferred to Inc 4, opt-in).
- Frontmatter parsing (Inc 2+).
- Freshness/decant-lag detection (Inc 3).
- Wiring the unrelated `update-daily-schedule.py` hook or fixing its RRULE bug (separate review findings).
