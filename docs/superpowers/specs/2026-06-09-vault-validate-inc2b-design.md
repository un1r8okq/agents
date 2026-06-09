# Vault-validate hook — Increment 2b (per-directory required-key matrix) design

**Status:** approved design, pre-implementation
**Date:** 2026-06-09
**Builds on:** the merged validate-vault hook (Inc1 + Inc2a + no-wikilinks check; 43 tests). This is the deferred second half of Increment 2.

## Goal

Enforce the rest of SKILL.md's "Required fields per directory" table beyond `description:` — the per-directory required keys, with value validation for the two enum fields. Report-only, always exits 0, zero dependencies, hard-coded rules guarded by a SKILL.md drift test (same pattern as Inc2a).

## The matrix (non-`description:` keys)

`description:` is already enforced by Inc2a's `find_missing_description`, so it is EXCLUDED here to avoid double-reporting.

| Path | Required keys | Enum constraint |
| --- | --- | --- |
| `people/*.md` | `organisation`, `role` | — |
| `orgs/*.md` | `relationship` | `employer` \| `client` \| `partner` \| `vendor` |
| `glossary/*.md` | `full` | — |
| `engagements/<E>/<E>.md` (overview only) | `client`, `status` | `status`: `active` \| `complete` |
| `engagements/<E>/glossary/*.md` | `full` | — |
| engagement companion files (`context`/`timeline`/`decisions`/`people`), and everything else | (none beyond `description`) | — |

## Architecture

Extend `skills/obsidian/hooks/validate_vault.py` (same pure-check + thin-shell structure).

### Rule encoding (hard-coded + drift-guard)

- `ENUM_FIELDS = {"status": {"active", "complete"}, "relationship": {"employer", "client", "partner", "vendor"}}`
- `_required_keys(rel: Path) -> set[str]` — returns the non-`description` required keys for a vault-relative path:
  - `people/` → `{"organisation", "role"}`; `orgs/` → `{"relationship"}`; `glossary/` → `{"full"}`.
  - `engagements/`:
    - overview (`parts == ("engagements", E, f"{E}.md")`) → `{"client", "status"}`
    - engagement glossary (`parts[0]=="engagements"` and `len(parts) >= 4` and `parts[2]=="glossary"`) → `{"full"}`
    - any other engagement file (companion files, etc.) → `set()`
  - everything else → `set()`.

### Checks

- `find_missing_required_keys(vault) -> list[tuple[Path, list[str]]]` — for each note via `_iter_notes`, `missing = sorted(_required_keys(rel) - set(_read_frontmatter(path)))`; if non-empty, append `(path, missing)`.
- `find_invalid_enum_values(vault) -> list[tuple[Path, str, str]]` — for each note, for each enum field in `ENUM_FIELDS` that is **required for that note** (`field in _required_keys(rel)`) AND **present** in the frontmatter, if the quote-stripped value ∉ the allowed set, append `(path, field, value)`. (A missing enum field is reported by `find_missing_required_keys`, not here.) Value normalisation: strip a matching surrounding quote pair (reuse the same logic shape as `_env_from_file`), exact-match against the allowed set (so case drift like `Active` is flagged).

### Reporting

`format_report` gains two keyword-only params (existing positional/keyword call sites unchanged):
```python
    missing_keys: list[tuple[Path, list[str]]] = (),
    bad_enums: list[tuple[Path, str, str]] = (),
```
New nudge lines (rendered after the existing sections):
```
- Missing required frontmatter: <rel> (client, status) — required for this directory.
- Invalid status value: <rel> ("done") — must be one of active, complete.
```
`main()` wires both new checks in. The empty-guard includes the new params.

### Drift guard

Extend the existing SKILL.md drift-guard test (`_skill_md_required_rows` already parses the "Required fields per directory" table, handling escaped `\|`). Add assertions:
- people row's Required cell contains `organisation:` and `role:`.
- orgs row contains `relationship:` and all four values `employer`/`client`/`partner`/`vendor`.
- glossary row contains `full:`; the engagement-glossary row contains `full:`.
- the engagement overview row (`engagements/<Engagement>/<Engagement>.md`) contains `client:`, `status:`, and `active`/`complete`.

This fails loudly if SKILL.md's table changes shape so the hard-coded matrix/enums drift.

## Error handling / performance

Unchanged never-fail contract (any exception → print nothing → exit 0). Two more `_iter_notes`/`_read_frontmatter` passes; milliseconds for ~480 files. Single-pass optimisation still deferred (YAGNI).

## Testing (TDD)

`skills/obsidian/hooks/test_validate_vault.py`:
- `_required_keys`: people→{organisation,role}; orgs→{relationship}; glossary→{full}; engagement overview `DSO2/DSO2.md`→{client,status}; companion `DSO2/context.md`→∅; engagement glossary `DSO2/glossary/MVR.md`→{full}; `misc/x.md`→∅; `daily/2026-01-01.md`→∅.
- `find_missing_required_keys`: people note missing `role` flagged with `["role"]`; people note with both org+role not flagged; engagement overview missing `client`/`status` flagged; companion file with only description NOT flagged.
- `find_invalid_enum_values`: orgs note `relationship: partner` (valid) not flagged; `relationship: friend` flagged `(path, "relationship", "friend")`; engagement overview `status: "active"` (quoted) not flagged; `status: done` flagged; a note where the enum field is absent is NOT flagged here (the missing-key check owns that).
- `format_report`: missing_keys + bad_enums sections render; all-empty still `""`; existing positional behaviour preserved.
- subprocess: a vault with a people note missing `role` surfaces the missing-required line in stdout, exit 0.
- drift-guard: the extended assertions pass against the current SKILL.md.

## Execution

Repo work on branch `feat/vault-validate-inc2b` in the worktree, subagent-driven TDD, merged to `main`. The main checkout stays free.

## Out of scope

Fixing the data the checks surface; the `description:` check (already shipped); freshness checks (Inc 3); the warnings tier / `--fix` (Inc 4); nudge-volume summarisation tuning.
