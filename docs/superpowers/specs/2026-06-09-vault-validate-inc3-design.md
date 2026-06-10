# Vault-validate hook — Increment 3 (freshness / decant-lag) design

**Status:** approved design, pre-implementation
**Date:** 2026-06-09
**Builds on:** the merged, now-firing validate-vault hook (Inc1 + Inc2a + Inc2b + no-wikilinks; 57 tests, 7 checks). This is the freshness slice — the review's #1 answer-quality lever (decant-lag).

## Goal

Nudge when the durable, decant-maintained notes have fallen behind recent activity: a person note discussed more recently than its newest dated entry (the meeting-prep gap), and an engagement `context.md` whose `Last refreshed` marker lags a newer decant. Report-only, exits 0, zero dependencies. Unlike the structural checks these are *suggestions* (run `refresh-person` / re-decant), and their output is compact.

## Recency window

14 days (matches the existing decant-nudge hook). A daily older than `today - 14d` does not trigger freshness checks. `today` is injected (real `date.today()` in `main`; a fixed date in tests) for deterministic testing.

## Check A — `find_stale_person_notes(vault, today)`

Returns a sorted `list[str]` of person-note stems that look stale.

1. Build the set of person stems = filenames (without `.md`) under `people/` (via `_iter_notes`, people/ only).
2. For each recent daily `daily/YYYY-MM-DD.md` (filename date in `[today-14d, today]`): extract wikilink targets (`[[Target` up to `|` or `]]`); for each target matching a person stem, record that person's **most-recent mention date** = max daily filename-date seen.
3. For each mentioned person, read `people/<stem>.md` and compute its **newest internal date reference** = max `[[YYYY-MM-DD]]` found in the note text.
   - If the note has **no** `[[YYYY-MM-DD]]` reference → **skip** (cannot establish staleness; avoids false positives).
4. **Stale** iff `most_recent_mention_date > note_newest_date_ref`. Collect the stem.

Rationale: if a 2026-06-08 daily wikilinks `[[Gagan Dhaliwal]]` but her note's newest dated entry is 2026-06-04, the recent discussion hasn't propagated into the durable note (the exact meeting-prep gap the review found). If the note already references 2026-06-08, it is fresh. Content-date based, so a decant editing `# My notes` (which bumps mtime) doesn't produce a false "fresh".

## Check B — `find_stale_context(vault, today)`

Returns a sorted `list[tuple[str, str, str]]` of `(engagement_name, last_refreshed, triggering_daily_date)`.

1. For each `engagements/*/context.md`: parse the `Last refreshed: [[YYYY-MM-DD]]` (or unbracketed `Last refreshed: YYYY-MM-DD`) date `D`. If no such marker → skip. Engagement name = parent directory name.
2. **Stale** iff there exists a **decanted** daily (`daily/YYYY-MM-DD.md` containing a `# Summary` heading) with filename date `> D` that wikilinks the engagement (`[[<EngagementName>` appears in the daily). Record the newest such daily date as the trigger.
3. (No 14-day window here — "after the last-refreshed date" is naturally bounded and we don't want to miss a lagging refresh.)

Rationale: `context.md` is contractually refreshed every decant. A decanted daily after the marker that still references the engagement means a refresh was due but the marker wasn't bumped.

## New helpers (small, pure, testable)

- `_recent_daily_files(vault, days, today) -> list[Path]` — `daily/[0-9]{4}-..md` whose parsed filename date is in `[today-days, today]`. Reuses the date-prefixed glob shape from the decant hook.
- `_wikilink_targets(text) -> set[str]` — all `[[Target]]`/`[[Target|alias]]` targets (the part before `|`/`#`/`]]`), stripped.
- `_max_date_ref(text) -> date | None` — newest `[[YYYY-MM-DD]]` parsed from text, else None.
- `_daily_date(path) -> date | None` — parse `YYYY-MM-DD` from a daily filename.

These are the only date-aware additions; `from datetime import date` is added to imports.

## Reporting

`format_report` gains two keyword-only params:
```python
    stale_people: list[str] = (),
    stale_context: list[tuple[str, str, str]] = (),
```
Compact, suggestion-phrased output (one summary line per check; names capped at 15 with `+N more`):
```
- Stale person notes (discussed more recently than their newest dated entry) — consider refresh-person: Gagan Dhaliwal, Leon, Subu.
- Stale engagement context: DSO2 (last refreshed 2026-06-05; 2026-06-08 decant mentions it) — re-run the context refresh.
```
`main()` wires both checks, passing `today=date.today()`. The empty-guard includes the new params.

## Error handling / performance

Never-fail/exit-0 unchanged. Work is bounded by the 14-day daily window (~14 files) plus the notes of people actually mentioned there; `find_stale_context` scans dailies after each marker date. Any per-file parse error → skip that file. No network.

## Testing (TDD)

`skills/obsidian/hooks/test_validate_vault.py` — all with an injected fixed `today`:
- helpers: `_daily_date`, `_recent_daily_files` (in/out of window), `_wikilink_targets` (alias + heading forms), `_max_date_ref` (newest of several; None when absent).
- `find_stale_person_notes`: flagged when a recent daily mention is newer than the note's newest date-ref; not flagged when the note's date-ref ≥ latest mention; skipped when the note has no date-ref; not flagged when the only mention is outside the 14-day window.
- `find_stale_context`: flagged when a decanted, engagement-mentioning daily postdates `Last refreshed`; not flagged when no newer daily, when the newer daily isn't decanted, or when it doesn't mention the engagement; skipped when no `Last refreshed` marker.
- `format_report`: both new sections render (incl. the `+N more` cap); all-empty still `""`; existing positional call sites unchanged.
- subprocess: a vault with one stale person surfaces the summary line in stdout, exit 0.

## Execution

Repo work on `feat/vault-validate-inc3` in the worktree, subagent-driven TDD, merged to `main`. Main checkout stays free.

## Out of scope

`todo.md` staleness (no reliable signal); undecanted-note backlog (owned by the decant-nudge hook); a `refreshed:` frontmatter marker; Inc 4 (warnings tier / `--fix`); the broader nudge-summarisation tuning for the *structural* checks; a module split of `validate_vault.py` (flag-only).
