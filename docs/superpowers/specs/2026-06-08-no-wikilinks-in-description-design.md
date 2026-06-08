# No wikilinks in `description:` — design

**Status:** approved design, pre-implementation
**Date:** 2026-06-08
**Context:** `description:` frontmatter is the grep-survey discovery entry point (intent.md goal #2). 90 vault notes currently embed `[[wikilinks]]` in their (quoted) `description:`. Wikilinks there create no Obsidian graph edge (free-text property renders as literal `[[...]]` clutter), add noise to the `^description:` survey, and duplicate the body's wikilink-every-occurrence linking. Decision: `description:` is plain prose.

## The rule (canonical wording)

> `description:` is plain prose — spell entity names out; do **not** use `[[wikilinks]]`. (Entity-relationship frontmatter fields — `organisation:`, `client:` — keep full wikilink syntax, quote-wrapped; that is a separate, deliberate rule.)

## Surfaces to codify

### 1. Skills (`/c/dev/agents/skills/`, git-tracked)
- **`obsidian/SKILL.md`** — canonical home. Add the rule to the **Description shape** block (after line ~100), as a new bullet. This is the single source of truth.
- **Short deferring pointer** in the skills that *author* descriptions, only where they instruct writing one — `refresh-person`, `background`, `decant`, `transcript`, `slack-thread`. One terse clause each (e.g. "(plain text — no `[[wikilinks]]`)"), NOT a restatement, to avoid the drift the review flagged.
- No change to consumers (`cp-team-update`) or skills that only have their own `description:` frontmatter (anonymise, edit-skill, llms-txt, mentor).

### 2. Vault conventions docs (`/c/notes/meta/conventions/`, NOT git-tracked)
- **`frontmatter.md`** — add the rule (canonical for the vault-doc copy).
- Scan `people-notes.md`, `detail-notes.md`, `engagements.md`, `glossary.md`, `orgs.md`, `misc-notes.md` and fix any `description:` *example* that itself contains a wikilink. State the rule once in `frontmatter.md`; the others reference it. (These are vault files, edited directly against `/c/notes` — not part of the git branch.)

### 3. The hook (`skills/obsidian/hooks/validate_vault.py`) — the "corruption" detector
- New pure check `find_wikilinks_in_description(vault) -> list[Path]`: for each note via `_iter_notes`, flag it if `_read_frontmatter(path).get("description", "")` contains `[[`.
- Wire into `format_report` (new keyword-only param `desc_links=()`) and `main`. New nudge line: `- Wikilink in description: <rel> — descriptions must be plain text (no [[...]]).`
- Report-only; never edits; always exits 0. TDD.
- **Known limitation (documented):** `_read_frontmatter` captures single-line `description:` values — which is all 90 current cases. A rare multi-line block-scalar description (`description: >`/`|`) would not be inspected. Acceptable; noted.

## Existing 90 violations

Not migrated (per decision). The new hook check surfaces them so they can be fixed incrementally. The hook stays report-only, so this adds nudge lines but changes nothing in the vault.

## Testing (TDD, hook only)

`skills/obsidian/hooks/test_validate_vault.py`:
- `find_wikilinks_in_description`: a note with `description: "... [[X]] ..."` is flagged; a plain-prose description is not; a note with no description / no frontmatter is not; an `[[X]]` in the BODY (not description) is not flagged.
- `format_report`: a `desc_links` section renders; all-empty still returns `""`; existing positional call sites unchanged.
- subprocess: a vault with a wikilink-in-description note surfaces the line in stdout, exit 0.
- The skills/docs prose edits are not unit-tested (prose); verified by reading + the hook running clean on a fixture.

## Execution

- Repo work (hook + tests + skills edits) on branch `feat/no-wikilinks-in-description` in the worktree, subagent-driven TDD, merged to `main`.
- `meta/conventions/` edits performed directly against `/c/notes` (vault, not git) as a separate task.
- Real-vault verification: the hook flags the ~90 wikilink-in-description notes alongside existing findings.

## Out of scope

Bulk-migrating the 90 existing descriptions; the deferred per-directory required-key matrix; freshness checks; converting `meta/conventions/` away from being drift copies (a separate review recommendation).
