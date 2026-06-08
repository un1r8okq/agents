# Vault-validate hook — Increment 2 (discovery checks) design

**Status:** approved design, pre-implementation
**Date:** 2026-06-08
**Builds on:** Increment 1 (`2026-06-08-vault-validate-hook-design.md`) — the shipped `skills/obsidian/hooks/validate_vault.py` hook (empty-notes + duplicate-basename checks). This is the next roadmapped slice.

## Goal

Add the two highest-value, near-uniform frontmatter checks to the hook so it catches the defects that break the vault's discovery model (intent.md goal #2: "survey a category by grepping `^description:`"). Report-only, always exits 0, zero dependencies — same contract as Increment 1.

This slice deliberately covers only `description:` presence and lowercase-key conformance. The full per-directory required-key matrix (`client:`/`status:`/`full:`/`relationship:`/`organisation:`/`role:`) is a later slice.

## Scope decisions (settled in brainstorming)

- **Check scope:** `description:` presence + non-lowercase frontmatter keys only. Defer the per-directory required-key matrix.
- **Rule source:** hard-code the directory rules in the script, guarded by a unit test that fails if they drift from SKILL.md's "Required fields per directory" table.

## Architecture

Extend `skills/obsidian/hooks/validate_vault.py` (same module, same pure-checks + thin-shell structure). No new files except the existing test file grows.

### New helper

- `_read_frontmatter(path: Path) -> dict[str, str]` — hand-rolled scanner: if the file's first non-blank line is `---`, read until the closing `---`; for each line matching `^([A-Za-z0-9_-]+):(.*)`, record `key -> value.strip()`. Returns `{}` when there is no frontmatter block. List items (`  - Will` under `aliases:`) and nested content don't match the key pattern, so they're ignored — they can't false-positive the lowercase-key check. Top-level keys only; no YAML dependency.

### New rule constant

```python
# Directories whose .md notes require a `description:` (intent.md goal #2 / SKILL.md
# "Required fields per directory"). SKILL.md is the source of truth; the
# drift-guard test (test_description_required_dirs_match_skill_md) fails if these
# diverge from that table.
DESCRIPTION_REQUIRED_DIRS = ("people", "orgs", "glossary", "misc", "engagements")
# daily/detail/ also requires it; daily/ top-level and daily/transcripts/ do NOT.
```

`_requires_description(rel: Path) -> bool`: True if `rel.parts[0]` is in `DESCRIPTION_REQUIRED_DIRS`, OR `rel.parts[:2] == ("daily", "detail")`. False otherwise (covers `daily/*.md`, `daily/transcripts/`, `meta/`, root files like README/todo).

### New checks

- `find_missing_description(vault: Path) -> list[Path]` — for each note from `_iter_notes` where `_requires_description(rel)` is True, flag it if `_read_frontmatter(path).get("description", "").strip()` is empty. (An uppercase `Description:` therefore counts as missing — correct, since the grep-survey keys on lowercase `^description:`.) Sorted output.
- `find_uppercase_frontmatter_keys(vault: Path) -> list[tuple[Path, list[str]]]` — for each note (any directory), flag it with the list of frontmatter keys `k` where `k != k.lower()`. Applies vault-wide because "all keys lowercase" is a universal rule; notes without frontmatter (e.g. `daily/*.md`) yield no keys and are never flagged. Sorted output.

### Reporting

Extend `format_report` with two keyword-only parameters so existing positional call sites and their tests are untouched:

```python
def format_report(empty, dups, vault, *, missing_desc=(), bad_keys=()) -> str:
```

Returns `""` only when ALL of empty/dups/missing_desc/bad_keys are empty. New sections render after the integrity lines:

```
- Missing description: people/Gagan Dhaliwal.md — invisible to the grep-survey discovery model.
- Non-lowercase frontmatter keys: people/Gagan Dhaliwal.md (Role, Organisation, Description) — keys must be lowercase.
```

`main()` wires the two new checks in as the keyword args; no other change to `main`.

### Drift guard

`test_description_required_dirs_match_skill_md` (in the test file): locate the skills repo via `Path(__file__).resolve().parents[3]`, read `skills/obsidian/SKILL.md`, extract the rows of the "Required fields per directory" table, and assert:
1. Every dir in `DESCRIPTION_REQUIRED_DIRS` (plus `daily/detail/`) appears as a table row whose Required cell contains `description:`.
2. The `daily/` (top-level) row's Required cell does NOT contain `description:`.
3. The literal lowercase-keys rule (`All keys` … `lowercase`) is present in SKILL.md.

If parsing the table fails to find the expected rows, the test fails — that is the intended loud signal that SKILL.md changed shape and the rules need review.

## Error handling / performance

Unchanged never-fail contract: any exception in a check or in `main` → print nothing → exit 0. Three light read passes over ~480 small files (empty / missing-description / uppercase-keys). Milliseconds; a single-pass optimisation is explicitly deferred (YAGNI).

## Testing (TDD)

Append to `skills/obsidian/hooks/test_validate_vault.py`:

- `_read_frontmatter`: parses keys from a `---` block; returns `{}` for no-frontmatter; ignores `aliases:` list items.
- `find_missing_description`: entity note with `description:` not flagged; entity note without it flagged; `daily/2026-01-01.md` (no frontmatter, top-level) not flagged; `daily/detail/x.md` without description flagged; `daily/transcripts/x.md` without description NOT flagged; a note with uppercase `Description:` flagged (case-sensitive).
- `find_uppercase_frontmatter_keys`: note with `Role:`/`Organisation:` flagged with those keys; all-lowercase note not flagged; no-frontmatter note not flagged; `aliases:` list doesn't cause a false positive.
- `format_report`: missing_desc/bad_keys sections appear; all-empty still returns `""`; existing positional behaviour preserved.
- drift guard: `test_description_required_dirs_match_skill_md` as specified above.
- subprocess: a vault with one entity note missing `description:` produces a nudge mentioning it on stdout, exit 0.

Quality bar: the full suite stays green (Increment 1's 22 tests plus the new ones).

## Out of scope (explicitly)

- The per-directory required-key matrix (`client:`, `status:`, `full:`, `relationship:`, `organisation:`, `role:`) — a later slice.
- Auto-fixing / backfilling descriptions (still report-only).
- Freshness/decant-lag checks (Increment 3).
- Single-pass read optimisation.
