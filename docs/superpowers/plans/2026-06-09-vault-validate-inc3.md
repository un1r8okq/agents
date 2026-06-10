# Vault-validate Inc 3 (freshness / decant-lag) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two freshness nudges to the validate-vault hook — stale person notes (discussed more recently than their newest dated entry) and stale engagement `context.md` (lagging a newer decant) — report-only, compact, exits 0.

**Architecture:** New date helpers + two pure checks (`find_stale_person_notes`, `find_stale_context`), wired into `format_report`/`main` via keyword args, rendered as compact suggestion lines. `today` is injected for deterministic tests.

**Tech Stack:** Python 3 stdlib (`datetime`), pytest. Builds on the merged 7-check hook.

**Spec:** `docs/superpowers/specs/2026-06-09-vault-validate-inc3-design.md`

**Worktree:** all work on `feat/vault-validate-inc3` in `/c/dev/agents/.claude/worktrees/inc3`. Stage explicit paths only; never `git commit -a`/`--amend -a`.

**Current code facts (anchors):** imports include `time` (line ~14) but NOT `datetime`. The last check function is `find_invalid_enum_values` (ends ~line 198); `read_cwd` follows. `format_report` has keyword-only params through `bad_enums`; its guard is `if not (empty or dups or missing_desc or bad_keys or desc_links or missing_keys or bad_enums):`; it ends with `lines.append("Mention these to the user and offer to fix; do NOT auto-edit the vault.")` then `return "\n".join(lines)`. `main()` builds the report via `_timed("name", fn, vault)` wrappers.

---

## Task 1: Date helpers + `datetime` import

**Files:** Modify `skills/obsidian/hooks/validate_vault.py`; Test `skills/obsidian/hooks/test_validate_vault.py`

- [ ] **Step 1: Write the failing tests** — APPEND to `test_validate_vault.py`:

```python
from datetime import date


def test_daily_date_parses_filename(tmp_path):
    assert vv._daily_date(tmp_path / "2026-06-08.md") == date(2026, 6, 8)
    assert vv._daily_date(tmp_path / "template.md") is None
    assert vv._daily_date(tmp_path / "2026-13-99.md") is None  # invalid date


def test_recent_daily_files_window(tmp_path):
    (tmp_path / "daily").mkdir()
    for d in ("2026-05-01", "2026-06-05", "2026-06-09"):
        (tmp_path / "daily" / f"{d}.md").write_text("x")
    (tmp_path / "daily" / "template.md").write_text("x")  # not a date -> excluded
    got = {p.name for p in vv._recent_daily_files(tmp_path, 14, date(2026, 6, 9))}
    assert got == {"2026-06-05.md", "2026-06-09.md"}  # 05-01 is outside 14d


def test_wikilink_targets_handles_alias_and_heading():
    t = "see [[Gagan Dhaliwal|Gagan]] and [[DSO2]] and [[Note#Heading]] and [[2026-06-08]]"
    assert vv._wikilink_targets(t) == {"Gagan Dhaliwal", "DSO2", "Note", "2026-06-08"}


def test_max_date_ref():
    assert vv._max_date_ref("a [[2026-05-29]] b [[2026-06-08-ww-standup]] c") == date(2026, 6, 8)
    assert vv._max_date_ref("no dates here") is None


def test_last_refreshed_parses_marker():
    assert vv._last_refreshed("*Last refreshed: [[2026-06-09]]. Next refresh: next decant.*") == date(2026, 6, 9)
    assert vv._last_refreshed("Last refreshed: 2026-06-05") == date(2026, 6, 5)
    assert vv._last_refreshed("no marker") is None
```

- [ ] **Step 2: Run to verify fail**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v -k "daily_date or recent_daily_files or wikilink_targets or max_date_ref or last_refreshed"`
Expected: FAIL — `AttributeError` for the missing helpers.

- [ ] **Step 3: Write minimal implementation**

(a) In the import block, change `from pathlib import Path` to be preceded by a datetime import — add this line immediately after `import time`:
```python
from datetime import date, timedelta
```

(b) Add the following helpers IMMEDIATELY AFTER `find_invalid_enum_values` (and before `read_cwd`):
```python
def _daily_date(path: Path) -> date | None:
    """Parse a YYYY-MM-DD date from a daily-note filename stem, else None."""
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", path.stem)
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError:
        return None


def _recent_daily_files(vault: Path, days: int, today: date) -> list[Path]:
    """Return daily/YYYY-MM-DD.md files whose date is in [today-days, today]."""
    cutoff = today - timedelta(days=days)
    out = []
    for path in (vault / "daily").glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md"):
        d = _daily_date(path)
        if d is not None and cutoff <= d <= today:
            out.append(path)
    return sorted(out)


def _wikilink_targets(text: str) -> set[str]:
    """Return the set of [[Target]] targets (text before any | or #), stripped."""
    targets = set()
    for m in re.finditer(r"\[\[([^\]]+)\]\]", text):
        target = re.split(r"[|#]", m.group(1), 1)[0].strip()
        if target:
            targets.add(target)
    return targets


def _max_date_ref(text: str) -> date | None:
    """Return the newest [[YYYY-MM-DD...]] date referenced in text, else None.

    Matches both pure date-links ([[2026-06-08]]) and date-prefixed detail-note
    links ([[2026-06-08-ww-standup]]).
    """
    dates = []
    for m in re.finditer(r"\[\[(\d{4})-(\d{2})-(\d{2})", text):
        try:
            dates.append(date(int(m[1]), int(m[2]), int(m[3])))
        except ValueError:
            pass
    return max(dates) if dates else None


def _last_refreshed(text: str) -> date | None:
    """Parse the date from a `Last refreshed: [[YYYY-MM-DD]]` marker, else None."""
    m = re.search(r"Last refreshed:\s*\[?\[?(\d{4})-(\d{2})-(\d{2})", text, re.IGNORECASE)
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError:
        return None
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: PASS (all prior + 5 new). Note: the test file's `from datetime import date` import is added at the top of the appended test block; if pytest complains about a mid-file import, move `from datetime import date` to the top of the test file with the other imports.

- [ ] **Step 5: Commit** (explicit paths, no -a):

```bash
git add skills/obsidian/hooks/validate_vault.py skills/obsidian/hooks/test_validate_vault.py
git commit -m "feat: validate-vault — date helpers for freshness checks

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: `find_stale_person_notes`

**Files:** Modify `skills/obsidian/hooks/validate_vault.py`; Test `skills/obsidian/hooks/test_validate_vault.py`

- [ ] **Step 1: Write the failing tests** — APPEND to `test_validate_vault.py`:

```python
def _make_person(tmp_path, name, body):
    (tmp_path / "people").mkdir(exist_ok=True)
    (tmp_path / "people" / f"{name}.md").write_text(body)


def _make_daily(tmp_path, d, body):
    (tmp_path / "daily").mkdir(exist_ok=True)
    (tmp_path / "daily" / f"{d}.md").write_text(body)


def test_find_stale_person_notes_flags_lagging_note(tmp_path):
    _make_person(tmp_path, "Gagan Dhaliwal", "# Summary\nseen [[2026-06-04]]\n")
    _make_daily(tmp_path, "2026-06-08", "standup with [[Gagan Dhaliwal|Gagan]]\n")
    assert vv.find_stale_person_notes(tmp_path, date(2026, 6, 9)) == ["Gagan Dhaliwal"]


def test_find_stale_person_notes_fresh_note_not_flagged(tmp_path):
    _make_person(tmp_path, "Gagan Dhaliwal", "# Summary\nupdated [[2026-06-08]]\n")
    _make_daily(tmp_path, "2026-06-08", "standup with [[Gagan Dhaliwal|Gagan]]\n")
    assert vv.find_stale_person_notes(tmp_path, date(2026, 6, 9)) == []


def test_find_stale_person_notes_no_date_ref_skipped(tmp_path):
    _make_person(tmp_path, "Leon", "# Summary\nno dates in this note\n")
    _make_daily(tmp_path, "2026-06-08", "chat with [[Leon]]\n")
    assert vv.find_stale_person_notes(tmp_path, date(2026, 6, 9)) == []


def test_find_stale_person_notes_old_mention_outside_window(tmp_path):
    _make_person(tmp_path, "Gagan Dhaliwal", "# Summary\nseen [[2026-04-01]]\n")
    _make_daily(tmp_path, "2026-05-01", "old standup with [[Gagan Dhaliwal]]\n")  # >14d before today
    assert vv.find_stale_person_notes(tmp_path, date(2026, 6, 9)) == []
```

- [ ] **Step 2: Run to verify fail**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v -k find_stale_person_notes`
Expected: FAIL — `AttributeError: module 'validate_vault' has no attribute 'find_stale_person_notes'`.

- [ ] **Step 3: Write minimal implementation** — add IMMEDIATELY AFTER `_last_refreshed`:
```python
def find_stale_person_notes(vault: Path, today: date, days: int = 14) -> list[str]:
    """Return person stems discussed in a recent daily more recently than their newest dated entry."""
    people_dir = vault / "people"
    if not people_dir.is_dir():
        return []
    stems = {p.stem for p in people_dir.glob("*.md")}
    if not stems:
        return []
    latest_mention: dict[str, date] = {}
    for daily in _recent_daily_files(vault, days, today):
        d = _daily_date(daily)
        try:
            text = daily.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for target in _wikilink_targets(text):
            if target in stems and (target not in latest_mention or d > latest_mention[target]):
                latest_mention[target] = d
    stale = []
    for person, mention_date in latest_mention.items():
        try:
            note_text = (people_dir / f"{person}.md").read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        note_date = _max_date_ref(note_text)
        if note_date is not None and mention_date > note_date:
            stale.append(person)
    return sorted(stale)
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: PASS (all prior + 4 new).

- [ ] **Step 5: Commit** (explicit paths, no -a):
```bash
git add skills/obsidian/hooks/validate_vault.py skills/obsidian/hooks/test_validate_vault.py
git commit -m "feat: validate-vault — detect stale person notes vs recent mentions

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: `find_stale_context`

**Files:** Modify `skills/obsidian/hooks/validate_vault.py`; Test `skills/obsidian/hooks/test_validate_vault.py`

- [ ] **Step 1: Write the failing tests** — APPEND to `test_validate_vault.py`:

```python
def _make_context(tmp_path, engagement, refreshed):
    d = tmp_path / "engagements" / engagement
    d.mkdir(parents=True, exist_ok=True)
    (d / "context.md").write_text(f"---\ndescription: ctx\n---\n*Last refreshed: [[{refreshed}]].*\n")


def test_find_stale_context_flags_lagging(tmp_path):
    _make_context(tmp_path, "DSO2", "2026-06-05")
    _make_daily(tmp_path, "2026-06-08", "# Summary\nstandup re [[DSO2]]\n")  # decanted, newer, mentions it
    assert vv.find_stale_context(tmp_path, date(2026, 6, 9)) == [("DSO2", "2026-06-05", "2026-06-08")]


def test_find_stale_context_not_flagged_when_daily_not_decanted(tmp_path):
    _make_context(tmp_path, "DSO2", "2026-06-05")
    _make_daily(tmp_path, "2026-06-08", "raw notes re [[DSO2]] (no summary heading)\n")
    assert vv.find_stale_context(tmp_path, date(2026, 6, 9)) == []


def test_find_stale_context_not_flagged_when_engagement_not_mentioned(tmp_path):
    _make_context(tmp_path, "DSO2", "2026-06-05")
    _make_daily(tmp_path, "2026-06-08", "# Summary\nunrelated day, no engagement link\n")
    assert vv.find_stale_context(tmp_path, date(2026, 6, 9)) == []


def test_find_stale_context_not_flagged_when_up_to_date(tmp_path):
    _make_context(tmp_path, "DSO2", "2026-06-09")
    _make_daily(tmp_path, "2026-06-08", "# Summary\nstandup re [[DSO2]]\n")  # daily is older than refresh
    assert vv.find_stale_context(tmp_path, date(2026, 6, 9)) == []
```

- [ ] **Step 2: Run to verify fail**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v -k find_stale_context`
Expected: FAIL — `AttributeError: module 'validate_vault' has no attribute 'find_stale_context'`.

- [ ] **Step 3: Write minimal implementation** — add IMMEDIATELY AFTER `find_stale_person_notes`:
```python
def find_stale_context(vault: Path, today: date) -> list[tuple[str, str, str]]:
    """Return (engagement, last_refreshed, trigger_date) where context.md lags a newer decant that mentions it."""
    eng_dir = vault / "engagements"
    if not eng_dir.is_dir():
        return []
    out = []
    daily_dir = vault / "daily"
    for ctx in sorted(eng_dir.glob("*/context.md")):
        engagement = ctx.parent.name
        try:
            ctx_text = ctx.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        refreshed = _last_refreshed(ctx_text)
        if refreshed is None:
            continue
        trigger: date | None = None
        for daily in daily_dir.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md"):
            dd = _daily_date(daily)
            if dd is None or dd <= refreshed or dd > today:
                continue
            try:
                dtext = daily.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if not re.search(r"^# Summary", dtext, re.MULTILINE):
                continue
            if engagement in _wikilink_targets(dtext) and (trigger is None or dd > trigger):
                trigger = dd
        if trigger is not None:
            out.append((engagement, refreshed.isoformat(), trigger.isoformat()))
    return sorted(out)
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: PASS (all prior + 4 new).

- [ ] **Step 5: Commit** (explicit paths, no -a):
```bash
git add skills/obsidian/hooks/validate_vault.py skills/obsidian/hooks/test_validate_vault.py
git commit -m "feat: validate-vault — detect stale engagement context vs newer decant

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Wire into `format_report` + `main` + subprocess test + real-vault verify

**Files:** Modify `skills/obsidian/hooks/validate_vault.py`; Test `skills/obsidian/hooks/test_validate_vault.py`

- [ ] **Step 1: Write the failing tests** — APPEND to `test_validate_vault.py`:

```python
def test_format_report_includes_freshness(tmp_path):
    report = vv.format_report(
        [], [], tmp_path,
        stale_people=["Gagan Dhaliwal", "Leon"],
        stale_context=[("DSO2", "2026-06-05", "2026-06-08")],
    )
    assert "consider refresh-person: Gagan Dhaliwal, Leon" in report
    assert "Stale engagement context: DSO2 (last refreshed 2026-06-05; 2026-06-08 decant mentions it)" in report


def test_format_report_freshness_caps_at_15(tmp_path):
    people = [f"P{i:02d}" for i in range(20)]
    report = vv.format_report([], [], tmp_path, stale_people=people)
    assert "+5 more" in report


def test_format_report_empty_with_freshness_empty(tmp_path):
    assert vv.format_report([], [], tmp_path, stale_people=[], stale_context=[]) == ""


def test_hook_reports_stale_person(tmp_path):
    _make_person(tmp_path, "Gagan Dhaliwal", "# Summary\nseen [[2026-04-04]]\n")
    _make_daily(tmp_path, date.today().isoformat(), "standup with [[Gagan Dhaliwal]]\n")
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert "consider refresh-person: Gagan Dhaliwal" in r.stdout
```

Note: `test_hook_reports_stale_person` uses `date.today()` for the daily filename so the subprocess (which calls `find_stale_person_notes(vault, date.today())`) sees it as in-window and newer than the note's `[[2026-04-04]]`.

- [ ] **Step 2: Run to verify fail**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v -k "format_report_includes_freshness or freshness_caps or empty_with_freshness or reports_stale_person"`
Expected: FAIL — `format_report()` got an unexpected keyword argument `stale_people`.

- [ ] **Step 3: Write minimal implementation**

(a) In `format_report`'s signature, after the `bad_enums: list[tuple[Path, str, str]] = (),` line and before `) -> str:`, add:
```python
    stale_people: list[str] = (),
    stale_context: list[tuple[str, str, str]] = (),
```

(b) Change the empty-guard line to add the two new params at the end:
```python
    if not (empty or dups or missing_desc or bad_keys or desc_links or missing_keys or bad_enums or stale_people or stale_context):
```

(c) Immediately BEFORE the final `lines.append("Mention these to the user and offer to fix; do NOT auto-edit the vault.")`, insert:
```python
    if stale_people:
        shown = ", ".join(stale_people[:15])
        more = f" (+{len(stale_people) - 15} more)" if len(stale_people) > 15 else ""
        lines.append(
            "- Stale person notes (discussed more recently than their newest dated entry) — "
            f"consider refresh-person: {shown}{more}."
        )
    for engagement, refreshed, trigger in stale_context:
        lines.append(
            f"- Stale engagement context: {engagement} (last refreshed {refreshed}; "
            f"{trigger} decant mentions it) — re-run the context refresh."
        )
```

(d) In `main()`, define `today` just before the `report = format_report(` line:
```python
        today = date.today()
```
and inside the `format_report(...)` call, after the `bad_enums=...` line, add:
```python
            stale_people=_timed("find_stale_person_notes", find_stale_person_notes, vault, today),
            stale_context=_timed("find_stale_context", find_stale_context, vault, today),
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: PASS — all tests, including existing positional `format_report` tests (unchanged).

- [ ] **Step 5: Verify on the real vault**

Run:
```bash
echo "{\"cwd\": \"$OBSIDIAN_VAULT\"}" | python3 /c/dev/agents/.claude/worktrees/inc3/skills/obsidian/hooks/validate_vault.py 2>/dev/null | grep -E "Stale person notes|Stale engagement context" || echo "(no freshness findings right now)"
```
Report the output verbatim (freshness findings depend on current vault state; "none" is a valid result if everything is current).

- [ ] **Step 6: Commit** (explicit paths, no -a):
```bash
git add skills/obsidian/hooks/validate_vault.py skills/obsidian/hooks/test_validate_vault.py
git commit -m "feat: validate-vault — surface freshness nudges (stale people + context)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Definition of done

- Full suite green (`python3 -m pytest skills/obsidian/hooks/test_validate_vault.py`).
- The hook emits compact freshness suggestions when a person note lags a recent mention or an engagement `context.md` lags a newer decant; report-only, exits 0.
- `today` is injected (real in `main`, fixed in tests).
- Existing positional `format_report` call sites/tests unchanged; never-fail contract intact.

Out of scope: `todo.md` staleness; undecanted backlog (decant-nudge hook owns it); a `refreshed:` marker; Inc 4; structural-check nudge summarisation; a module split.
