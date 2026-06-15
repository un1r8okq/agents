# Vault Monthly Nesting + Processing Inbox — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nest all dated vault notes (daily/detail/transcripts) into `YYYY-MM/` subfolders and add a vault-root `inbox/` drop zone, updating every path-coupled tool so nothing silently breaks.

**Architecture:** Make the four path-coupled tools (`validate_vault.py`, `undecanted-notes.sh`, `update-daily-schedule.py`, and the writing skills' docs) month-folder-aware and inbox-aware; then a one-shot, non-git-safe migration script relocates the ~293 existing files. Obsidian resolves `[[links]]` by basename, so nesting preserves all inbound links.

**Tech Stack:** Python 3 (stdlib only), Bash, pytest. All code lives in the `/c/dev/agents` git repo (`scripts/` tracked directly; `~/.claude/skills` is a symlink into `skills/`). The vault itself is NOT a git repo.

**Spec:** `docs/superpowers/specs/2026-06-15-vault-monthly-nesting-design.md`

**Working location:** worktree `.claude/worktrees/vault-monthly-nesting` (branch `worktree-vault-monthly-nesting`), already rebased onto local `main`.

**Glob conventions used throughout:**
- Flat daily note: `daily/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md`
- Month-nested daily note: `daily/[0-9][0-9][0-9][0-9]-[0-9][0-9]/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md`
- The month-folder pattern `[0-9][0-9][0-9][0-9]-[0-9][0-9]/` matches `daily/2026-05/` but never `daily/detail/` or `daily/transcripts/`, so daily-note discovery stays correctly scoped.

---

## Task 1: Make `validate_vault.py` month-aware + inbox-aware

**Files:**
- Modify: `skills/obsidian/hooks/validate_vault.py`
- Test: `skills/obsidian/hooks/test_validate_vault.py`

Two behavior changes: (a) daily-note discovery (`_recent_daily_files`, `find_stale_context`) must find month-nested notes; (b) `_iter_notes` must skip the new `inbox/` staging dir so dropped files aren't validated as vault notes. `_requires_description` already returns True for `daily/detail/<YYYY-MM>/x.md` because it keys on `parts[:2] == ("daily", "detail")` — we add a test to lock that in, no code change.

- [ ] **Step 1: Write failing tests**

Add to `skills/obsidian/hooks/test_validate_vault.py`:

```python
def test_recent_daily_files_finds_month_nested(tmp_path):
    daily = tmp_path / "daily" / "2026-06"
    daily.mkdir(parents=True)
    nested = daily / "2026-06-10.md"
    nested.write_text("# Notes\n")
    today = date(2026, 6, 12)
    found = vv._recent_daily_files(tmp_path, days=14, today=today)
    assert nested in found


def test_recent_daily_files_still_finds_flat(tmp_path):
    daily = tmp_path / "daily"
    daily.mkdir()
    flat = daily / "2026-06-10.md"
    flat.write_text("# Notes\n")
    found = vv._recent_daily_files(tmp_path, days=14, today=date(2026, 6, 12))
    assert flat in found


def test_recent_daily_files_ignores_detail_and_transcripts(tmp_path):
    # detail/transcripts live under daily/ but must not be treated as daily notes
    (tmp_path / "daily" / "detail" / "2026-06").mkdir(parents=True)
    (tmp_path / "daily" / "detail" / "2026-06" / "2026-06-10-topic.md").write_text("x\n")
    (tmp_path / "daily" / "transcripts" / "2026-06").mkdir(parents=True)
    (tmp_path / "daily" / "transcripts" / "2026-06" / "2026-06-10-x-transcript.md").write_text("x\n")
    found = vv._recent_daily_files(tmp_path, days=14, today=date(2026, 6, 12))
    assert found == []


def test_stale_context_finds_month_nested_trigger(tmp_path):
    ctx = tmp_path / "engagements" / "Acme" / "context.md"
    ctx.parent.mkdir(parents=True)
    ctx.write_text("---\ndescription: x\n---\n*Last refreshed: [[2026-06-01]]*\n")
    nested = tmp_path / "daily" / "2026-06" / "2026-06-09.md"
    nested.parent.mkdir(parents=True)
    nested.write_text("# Summary\n- [[Acme]] talked\n")
    out = vv.find_stale_context(tmp_path, today=date(2026, 6, 12))
    assert ("Acme", "2026-06-01", "2026-06-09") in out


def test_iter_notes_skips_inbox(tmp_path):
    (tmp_path / "inbox").mkdir()
    dropped = tmp_path / "inbox" / "raw-transcript.md"
    dropped.write_text("")  # empty + no description — would normally be flagged
    (tmp_path / "misc").mkdir()
    (tmp_path / "misc" / "Real.md").write_text("content\n")
    names = {p.name for p in vv._iter_notes(tmp_path)}
    assert "raw-transcript.md" not in names
    assert "Real.md" in names


def test_detail_month_nested_still_requires_description(tmp_path):
    rel = Path("daily") / "detail" / "2026-06" / "2026-06-10-topic.md"
    assert vv._requires_description(rel) is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd skills/obsidian/hooks && python3 -m pytest test_validate_vault.py -k "month_nested or skips_inbox or detail_month_nested or still_finds_flat or ignores_detail" -v`
Expected: FAIL — `test_recent_daily_files_finds_month_nested`, `test_stale_context_finds_month_nested_trigger`, `test_iter_notes_skips_inbox` fail (flat glob misses nested; inbox not skipped). `still_finds_flat` and `detail_month_nested_still_requires_description` may already pass.

- [ ] **Step 3: Add the month-aware daily helper**

In `validate_vault.py`, add this helper just above `_recent_daily_files` (after `_daily_date`, ~line 209):

```python
def _daily_note_files(vault: Path) -> Iterator[Path]:
    """Yield daily-note files in either layout: flat (daily/YYYY-MM-DD.md) or
    month-nested (daily/YYYY-MM/YYYY-MM-DD.md). The month-folder glob never
    matches daily/detail/ or daily/transcripts/, so those stay excluded."""
    daily = vault / "daily"
    yield from daily.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md")
    yield from daily.glob(
        "[0-9][0-9][0-9][0-9]-[0-9][0-9]/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md"
    )
```

- [ ] **Step 4: Use the helper in `_recent_daily_files`**

Replace the loop in `_recent_daily_files` (the `for path in (vault / "daily").glob(...)` line) with:

```python
    for path in _daily_note_files(vault):
```

- [ ] **Step 5: Use the helper in `find_stale_context`**

In `find_stale_context`, replace the inner `for daily in daily_dir.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md"):` line with:

```python
        for daily in _daily_note_files(vault):
```

(The surrounding `daily_dir = vault / "daily"` line becomes unused; remove it to avoid a dead variable.)

- [ ] **Step 6: Skip `inbox/` in `_iter_notes`**

Replace the body of `_iter_notes` with:

```python
def _iter_notes(vault: Path) -> Iterator[Path]:
    """Yield *.md content files under vault, skipping dot-directories, the inbox/
    staging area, and README.md (conventional per-directory files, not wikilink targets)."""
    for path in vault.rglob("*.md"):
        rel = path.relative_to(vault)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if rel.parts and rel.parts[0] == "inbox":
            continue
        if path.name.lower() == "readme.md":
            continue
        yield path
```

- [ ] **Step 7: Run the full test file**

Run: `cd skills/obsidian/hooks && python3 -m pytest test_validate_vault.py -v`
Expected: PASS (all tests, including the new ones and the existing drift-guard `test_description_required_dirs_match_skill_md`).

- [ ] **Step 8: Commit**

```bash
git add skills/obsidian/hooks/validate_vault.py skills/obsidian/hooks/test_validate_vault.py
git commit -m "feat: validate-vault — month-nested daily discovery + inbox exclusion

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Make `undecanted-notes.sh` scan month folders

**Files:**
- Modify: `skills/decant/hooks/undecanted-notes.sh:58`
- Test: `skills/decant/hooks/test-undecanted-notes.sh`

The hook globs only flat `daily/*.md`. After migration, in-window notes live in `daily/YYYY-MM/`. Glob both.

- [ ] **Step 1: Add a failing test case**

In `skills/decant/hooks/test-undecanted-notes.sh`, find the fixture setup block (the `printf ... > "$vault/daily/$IN1.md"` lines near the top, ~lines 34–40). After the existing fixtures, add a month-nested undecanted note that should be detected:

```bash
# Month-nested undecanted note (post-migration layout) — must be detected
IN_NESTED="$(date -d '3 days ago' +%F 2>/dev/null || date -v-3d +%F)"
mkdir -p "$vault/daily/${IN_NESTED:0:7}"
printf '# Notes\n- nested undecanted\n' > "$vault/daily/${IN_NESTED:0:7}/$IN_NESTED.md"
```

Then locate the assertion block that checks the emitted list contains the expected dates and add an assertion that `$IN_NESTED` appears in the output. Match the file's existing assertion style — if it greps the captured output variable, add:

```bash
case "$out" in
  *"$IN_NESTED"*) : ;;
  *) echo "FAIL: month-nested note $IN_NESTED not detected"; exit 1 ;;
esac
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `bash skills/decant/hooks/test-undecanted-notes.sh`
Expected: FAIL — the nested note is not detected by the flat-only glob.

- [ ] **Step 3: Update the glob to include month folders**

In `skills/decant/hooks/undecanted-notes.sh`, replace the `for f in ...` line (line 58) with a two-pattern glob (under the already-set `shopt -s nullglob`, an unmatched pattern expands to nothing):

```bash
for f in "$vault"/daily/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md \
         "$vault"/daily/[0-9][0-9][0-9][0-9]-[0-9][0-9]/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md; do
```

The `basename "$f" .md` on line 59 already yields the date stem regardless of parent folder, so the window comparison logic is unchanged.

- [ ] **Step 4: Run the test to verify it passes**

Run: `bash skills/decant/hooks/test-undecanted-notes.sh`
Expected: PASS (existing flat-note cases plus the new nested case).

- [ ] **Step 5: Commit**

```bash
git add skills/decant/hooks/undecanted-notes.sh skills/decant/hooks/test-undecanted-notes.sh
git commit -m "feat: undecanted-notes hook — scan month-nested daily folders

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Make `update-daily-schedule.py` write into the month folder

**Files:**
- Modify: `scripts/update-daily-schedule.py:39-42` and `scripts/update-daily-schedule.py:360-364`
- Test: `scripts/test_update_daily_schedule.py` (create)

Today's note must be created/updated at `daily/<YYYY-MM>/<date>.md`. Extract the path into a pure, testable helper, then ensure the month folder exists before creating the file.

- [ ] **Step 1: Write the failing test**

Create `scripts/test_update_daily_schedule.py`:

```python
import datetime
import os
import sys
from pathlib import Path

# The module computes paths at import time and sys.exit()s if OBSIDIAN_VAULT is
# unset, so set it before import.
os.environ.setdefault("OBSIDIAN_VAULT", "/tmp/uds-test-vault")
sys.path.insert(0, str(Path(__file__).parent))
import importlib
import update_daily_schedule as uds  # noqa: E402


def test_daily_note_path_is_month_nested():
    vault = Path("/tmp/some-vault")
    day = datetime.date(2026, 6, 9)
    assert uds.daily_note_path(vault, day) == vault / "daily" / "2026-06" / "2026-06-09.md"
```

Note: the module file is `update-daily-schedule.py` (hyphens). Importing by the name `update_daily_schedule` requires the file to be importable; create a thin loader at the top of the test if needed:

```python
import importlib.util
spec = importlib.util.spec_from_file_location(
    "update_daily_schedule", Path(__file__).parent / "update-daily-schedule.py"
)
uds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(uds)
```

Use this loader form (replace the plain `import update_daily_schedule as uds` line with it) since the source filename has hyphens.

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd scripts && python3 -m pytest test_update_daily_schedule.py -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'daily_note_path'`.

- [ ] **Step 3: Add the helper and use it for the module-level path**

In `scripts/update-daily-schedule.py`, add the helper just below the constants (after line 37, before `today = ...`):

```python
def daily_note_path(vault: Path, day: datetime.date) -> Path:
    """Path to a daily note, nested by month: daily/YYYY-MM/YYYY-MM-DD.md."""
    return vault / "daily" / day.strftime("%Y-%m") / f"{day.isoformat()}.md"
```

Then replace lines 40–41:

```python
daily_dir = VAULT_PATH / "daily"
daily_path = daily_dir / f"{today.isoformat()}.md"
```

with:

```python
daily_dir = VAULT_PATH / "daily"
daily_path = daily_note_path(VAULT_PATH, today)
```

(`template_path = daily_dir / "template.md"` on line 42 stays — the template lives at the `daily/` root, unnested.)

- [ ] **Step 4: Ensure the month folder exists before creating the note**

In `main()`, replace the create block (lines 360–364):

```python
    if not daily_path.exists():
        if template_path.exists():
            shutil.copyfile(template_path, daily_path)
        else:
            daily_path.write_text("# Notes\n")
```

with:

```python
    if not daily_path.exists():
        daily_path.parent.mkdir(parents=True, exist_ok=True)
        if template_path.exists():
            shutil.copyfile(template_path, daily_path)
        else:
            daily_path.write_text("# Notes\n")
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd scripts && python3 -m pytest test_update_daily_schedule.py -v`
Expected: PASS.

- [ ] **Step 6: Smoke-check import and path**

Run: `cd scripts && OBSIDIAN_VAULT=/tmp/v python3 -c "import importlib.util,datetime; s=importlib.util.spec_from_file_location('u','update-daily-schedule.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); print(m.daily_note_path(__import__('pathlib').Path('/tmp/v'), datetime.date(2026,6,9)))"`
Expected output: `/tmp/v/daily/2026-06/2026-06-09.md`

- [ ] **Step 7: Commit**

```bash
git add scripts/update-daily-schedule.py scripts/test_update_daily_schedule.py
git commit -m "feat: daily-schedule — create today's note in daily/YYYY-MM/

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Update skill docs for month nesting + inbox

**Files:**
- Modify: `skills/obsidian/SKILL.md`
- Modify: `skills/decant/SKILL.md`
- Modify: `skills/slack-thread/SKILL.md`
- Modify: `skills/transcript/SKILL.md`

Docs are the agent's instructions; if they say `daily/detail/YYYY-MM-DD-x.md` the agent will write to the flat path. Update path templates to the nested form and document `inbox/`. **Do NOT rename the row labels `` `daily/` `` and `` `daily/detail/` `` in `skills/obsidian/SKILL.md`'s "Required fields per directory" table** — `test_validate_vault.py::test_description_required_dirs_match_skill_md` parses those exact keys and will fail if they change. Only the *structure* table and prose change.

- [ ] **Step 1: Update `skills/obsidian/SKILL.md` structure table + conventions**

In the "Vault structure" table, change these rows:

```
| `daily/YYYY-MM/YYYY-MM-DD.md` | Daily notes — schedule + free-form notes (nested by month) |
| `daily/detail/YYYY-MM/YYYY-MM-DD-topic.md` | Overflow or multi-person session notes. Verbatim. |
| `daily/transcripts/YYYY-MM/` | Raw transcripts after processing (Google Meet exports etc.) |
| `inbox/` | Drop zone (vault root) for files awaiting processing — raw transcripts, screenshots, exports. Transient; skills move processed output into the dated tree and clear the file. |
```

In the "Daily notes" section, change `Files in `daily/YYYY-MM-DD.md`.` to `Files in `daily/YYYY-MM/YYYY-MM-DD.md` (nested by month; `template.md` stays at the `daily/` root).`

In the "Detail notes" section, change `Files in `daily/detail/YYYY-MM-DD-topic-name.md`.` to `Files in `daily/detail/YYYY-MM/YYYY-MM-DD-topic-name.md` (nested by month).`

Leave the "Required fields per directory" table row labels exactly as-is (`` `daily/` ``, `` `daily/detail/` ``).

- [ ] **Step 2: Update `skills/decant/SKILL.md` paths**

Change the detail-note path references from `daily/detail/YYYY-MM-DD-topic-name.md` to `daily/detail/YYYY-MM/YYYY-MM-DD-topic-name.md` (the line in step 2 and the "Detail notes" line in step's create list). Change the target daily note reference `$OBSIDIAN_VAULT/daily/YYYY-MM-DD.md` to `$OBSIDIAN_VAULT/daily/YYYY-MM/YYYY-MM-DD.md`. Change the image-rename target `daily/YYYY-MM-DD-org-chart.png` example to `daily/YYYY-MM/YYYY-MM-DD-org-chart.png`.

- [ ] **Step 3: Update `skills/slack-thread/SKILL.md` paths**

Change `daily/detail/YYYY-MM-DD-<slug>.md` → `daily/detail/YYYY-MM/YYYY-MM-DD-<slug>.md` (both the Filename line and the Path line). Change the target daily `$OBSIDIAN_VAULT/daily/YYYY-MM-DD.md` → `$OBSIDIAN_VAULT/daily/YYYY-MM/YYYY-MM-DD.md`, and update the "create from `$OBSIDIAN_VAULT/daily/template.md`" note to clarify the new note is created at the month-nested path.

- [ ] **Step 4: Update `skills/transcript/SKILL.md` paths + inbox discovery**

- Change the auto-discovery source: where it says to glob `$OBSIDIAN_VAULT/daily/transcripts/` for non-conforming files, change it to glob `$OBSIDIAN_VAULT/inbox/` (the new drop zone). Update the "No matches" message to reference `inbox/`.
- Change the processed-transcript destination `$OBSIDIAN_VAULT/daily/transcripts/YYYY-MM-DD-<slug>-transcript.md` → `$OBSIDIAN_VAULT/daily/transcripts/YYYY-MM/YYYY-MM-DD-<slug>-transcript.md` (create the month folder if missing; remove the raw file from `inbox/` after writing).
- Change the detail-note destination `$OBSIDIAN_VAULT/daily/detail/YYYY-MM-DD-<slug>.md` → `$OBSIDIAN_VAULT/daily/detail/YYYY-MM/YYYY-MM-DD-<slug>.md`.
- Change the target daily `$OBSIDIAN_VAULT/daily/YYYY-MM-DD.md` → `$OBSIDIAN_VAULT/daily/YYYY-MM/YYYY-MM-DD.md`.

- [ ] **Step 5: Verify no stale flat paths remain in skill docs**

Run: `grep -rn "daily/detail/YYYY-MM-DD\|daily/transcripts/YYYY-MM-DD\|daily/YYYY-MM-DD\b" skills/ | grep -v "YYYY-MM/"`
Expected: no output (every dated path now includes the `/YYYY-MM/` segment). Investigate and fix any remaining hits.

- [ ] **Step 6: Verify the drift-guard still passes**

Run: `cd skills/obsidian/hooks && python3 -m pytest test_validate_vault.py -k description_required_dirs -v`
Expected: PASS (proves the `daily/` and `daily/detail/` frontmatter-table keys were left intact).

- [ ] **Step 7: Commit**

```bash
git add skills/obsidian/SKILL.md skills/decant/SKILL.md skills/slack-thread/SKILL.md skills/transcript/SKILL.md
git commit -m "docs: skills — month-nested note paths + inbox drop zone

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Migration script

**Files:**
- Create: `scripts/migrate-daily-nesting.py`
- Test: `scripts/test_migrate_daily_nesting.py`

A one-shot, idempotent, non-git-safe migrator. Defaults to dry-run; `--apply` performs moves; always backs up (tarball outside the vault) before applying; verifies counts after.

- [ ] **Step 1: Write the failing test**

Create `scripts/test_migrate_daily_nesting.py`:

```python
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "migrate_daily_nesting", Path(__file__).parent / "migrate-daily-nesting.py"
)
mdn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mdn)


def _fixture(tmp_path: Path) -> Path:
    v = tmp_path / "vault"
    (v / "daily").mkdir(parents=True)
    (v / "daily" / "detail").mkdir()
    (v / "daily" / "transcripts").mkdir()
    (v / "daily" / "2026-05-01.md").write_text("# Notes\n")
    (v / "daily" / "2026-06-02.md").write_text("# Notes\n")
    (v / "daily" / "template.md").write_text("# Notes\n")
    (v / "daily" / "detail" / "2026-05-01-topic.md").write_text("x\n")
    (v / "daily" / "transcripts" / "2026-06-02-mtg-transcript.md").write_text("x\n")
    return v


def test_plan_moves_maps_to_month_folders(tmp_path):
    v = _fixture(tmp_path)
    moves = mdn.plan_moves(v)
    pairs = {(src.relative_to(v).as_posix(), dst.relative_to(v).as_posix()) for src, dst in moves}
    assert ("daily/2026-05-01.md", "daily/2026-05/2026-05-01.md") in pairs
    assert ("daily/2026-06-02.md", "daily/2026-06/2026-06-02.md") in pairs
    assert ("daily/detail/2026-05-01-topic.md", "daily/detail/2026-05/2026-05-01-topic.md") in pairs
    assert (
        "daily/transcripts/2026-06-02-mtg-transcript.md",
        "daily/transcripts/2026-06/2026-06-02-mtg-transcript.md",
    ) in pairs


def test_plan_moves_skips_template_and_nested(tmp_path):
    v = _fixture(tmp_path)
    # already-nested file must not be re-planned (idempotency)
    (v / "daily" / "2026-05").mkdir(exist_ok=True)
    (v / "daily" / "2026-05" / "2026-05-09.md").write_text("# Notes\n")
    srcs = {src.relative_to(v).as_posix() for src, _ in mdn.plan_moves(v)}
    assert "daily/template.md" not in srcs
    assert "daily/2026-05/2026-05-09.md" not in srcs


def test_apply_moves_files_and_verifies(tmp_path):
    v = _fixture(tmp_path)
    moves = mdn.plan_moves(v)
    mdn.apply_moves(moves)
    assert (v / "daily" / "2026-05" / "2026-05-01.md").exists()
    assert not (v / "daily" / "2026-05-01.md").exists()
    assert (v / "daily" / "template.md").exists()  # untouched
    # idempotent: re-planning after apply yields nothing
    assert mdn.plan_moves(v) == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd scripts && python3 -m pytest test_migrate_daily_nesting.py -v`
Expected: FAIL — module/file does not exist.

- [ ] **Step 3: Write the migration script**

Create `scripts/migrate-daily-nesting.py`:

```python
#!/usr/bin/env python3
"""Migrate flat daily/detail/transcript notes into YYYY-MM/ month folders.

The vault is NOT a git repo, so this is the safety net:
  * defaults to --dry-run (prints planned moves, changes nothing)
  * --apply performs the moves, after writing a tarball backup OUTSIDE the vault
  * verifies in-count == out-count and reports leftovers
Idempotent: already-nested files and template.md are skipped, so re-runs are safe.
"""
import argparse
import datetime
import os
import re
import sys
import tarfile
from pathlib import Path

DATE_PREFIX = re.compile(r"(\d{4})-(\d{2})-\d{2}")
# Directories whose dated *.md files get nested. Each is relative to the vault.
SCAN_DIRS = ("daily", "daily/detail", "daily/transcripts")


def _month_of(name: str) -> str | None:
    """Return 'YYYY-MM' from a filename starting with a YYYY-MM-DD date, else None."""
    m = DATE_PREFIX.match(name)
    if not m:
        return None
    try:
        datetime.date(int(m[1]), int(m[2]), 1)
    except ValueError:
        return None
    return f"{m[1]}-{m[2]}"


def plan_moves(vault: Path) -> list[tuple[Path, Path]]:
    """Return (src, dst) pairs for dated .md files not yet in their month folder."""
    moves = []
    for rel in SCAN_DIRS:
        d = vault / rel
        if not d.is_dir():
            continue
        for child in sorted(d.iterdir()):
            if not child.is_file() or child.suffix != ".md":
                continue
            month = _month_of(child.name)
            if month is None:
                continue  # template.md, non-dated files: leave in place
            dst = d / month / child.name
            if child.resolve() == dst.resolve():
                continue
            moves.append((child, dst))
    return moves


def unparseable(vault: Path) -> list[Path]:
    """Dated-dir .md files at the flat root whose names lack a YYYY-MM-DD prefix."""
    out = []
    for rel in SCAN_DIRS:
        d = vault / rel
        if not d.is_dir():
            continue
        for child in sorted(d.iterdir()):
            if child.is_file() and child.suffix == ".md" and _month_of(child.name) is None:
                if child.name != "template.md":
                    out.append(child)
    return out


def apply_moves(moves: list[tuple[Path, Path]]) -> None:
    for src, dst in moves:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            raise FileExistsError(f"refusing to overwrite {dst}")
        src.rename(dst)


def backup(vault: Path) -> Path:
    """Tar the daily/ tree to a timestamped archive OUTSIDE the vault."""
    stamp = datetime.date.today().isoformat()
    archive = vault.parent / f"{vault.name}-daily-bak-{stamp}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(vault / "daily", arcname="daily")
    return archive


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="perform moves (default: dry-run)")
    ap.add_argument("--vault", default=os.environ.get("OBSIDIAN_VAULT"))
    args = ap.parse_args(argv)
    if not args.vault:
        print("OBSIDIAN_VAULT not set and --vault not given", file=sys.stderr)
        return 2
    vault = Path(args.vault)
    if not (vault / "daily").is_dir():
        print(f"{vault}/daily not found", file=sys.stderr)
        return 2

    moves = plan_moves(vault)
    skipped = unparseable(vault)
    print(f"Planned moves: {len(moves)}")
    for src, dst in moves:
        print(f"  {src.relative_to(vault)}  ->  {dst.relative_to(vault)}")
    if skipped:
        print(f"Left in place (no YYYY-MM-DD prefix): {len(skipped)}")
        for p in skipped:
            print(f"  {p.relative_to(vault)}")

    if not args.apply:
        print("\nDRY RUN — nothing changed. Re-run with --apply to migrate.")
        return 0

    before = sum(1 for _ in (vault / "daily").rglob("*.md"))
    archive = backup(vault)
    print(f"\nBackup written: {archive}")
    apply_moves(moves)
    after = sum(1 for _ in (vault / "daily").rglob("*.md"))
    leftovers = [src for src, _ in plan_moves(vault)]  # should be empty now
    print(f"Moved {len(moves)} file(s). daily/ .md count before={before} after={after}.")
    if before != after:
        print("ERROR: file count changed — investigate against the backup!", file=sys.stderr)
        return 1
    if leftovers:
        print(f"ERROR: {len(leftovers)} file(s) still un-nested — investigate.", file=sys.stderr)
        return 1
    print("OK — counts match, no leftovers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd scripts && python3 -m pytest test_migrate_daily_nesting.py -v`
Expected: PASS (all three tests).

- [ ] **Step 5: Make the script executable**

Run: `chmod +x scripts/migrate-daily-nesting.py && git update-index --chmod=+x scripts/migrate-daily-nesting.py`
(The `git update-index --chmod` is required so the exec bit survives the commit — `core.fileMode` can be false in this repo.)

- [ ] **Step 6: Commit**

```bash
git add scripts/migrate-daily-nesting.py scripts/test_migrate_daily_nesting.py
git commit -m "feat: migration script for daily/detail/transcript month nesting

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Full-suite green + dry-run against the real vault

**Files:** none (verification only)

- [ ] **Step 1: Run every test in the repo**

Run: `cd skills/obsidian/hooks && python3 -m pytest -q` then `cd scripts && python3 -m pytest -q` then `bash skills/decant/hooks/test-undecanted-notes.sh`
Expected: all PASS.

- [ ] **Step 2: Dry-run the migration against the live vault**

Run: `python3 scripts/migrate-daily-nesting.py` (reads `$OBSIDIAN_VAULT`)
Expected: prints ~293 planned moves and a "DRY RUN — nothing changed" footer. Eyeball that every `src -> dst` looks right and the "Left in place" list contains only `template.md` / genuinely non-dated files.

- [ ] **Step 3: Report to the user before applying**

Summarize the dry-run output (count, any surprises in the "Left in place" list) and **stop for explicit go-ahead** before running `--apply`. The apply step mutates the non-git vault and is the point of no return (mitigated by the tarball backup).

---

## Execution-time procedure (after plan tasks land, user-gated)

Not a code task — the operator runs these once, in order:

1. `python3 scripts/migrate-daily-nesting.py --apply` — backs up, moves, verifies counts.
2. Open Obsidian; confirm daily/detail/transcript notes appear under collapsible `YYYY-MM/` folders and a few `[[YYYY-MM-DD]]` links still resolve.
3. Create the `inbox/` folder at the vault root (the migration script doesn't create it): `mkdir -p "$OBSIDIAN_VAULT/inbox"`.
4. Merge the worktree branch to `main` so the live `~/.claude/skills` symlink and `scripts/` pick up the new behavior:
   `git checkout main && git merge --no-ff worktree-vault-monthly-nesting`.
5. Start a new session and confirm: the schedule hook writes today's note into `daily/YYYY-MM/`; validate-vault and undecanted hooks run clean.
6. Once Obsidian looks correct, delete the backup tarball beside the vault.

---

## Self-review notes

- **Spec coverage:** directory shape → Tasks 3/4 (creators) + Task 5 (migration); inbox → Tasks 1 (exclusion), 4 (docs/discovery), execution step 3; tooling table (all 5 touchpoints) → Tasks 1–4; migration w/ backup+dry-run+count → Task 5; testing → tests in Tasks 1–5; risks (basename collision, no-git undo, worktree skills copy) → dup-basename check retained (Task 1), backup/dry-run/verify (Task 5), merge step (execution procedure).
- **No placeholders:** all code shown in full.
- **Type/name consistency:** `_daily_note_files` (Task 1) used in both `_recent_daily_files` and `find_stale_context`; `daily_note_path` (Task 3); `plan_moves`/`apply_moves`/`backup`/`unparseable` (Task 5) match the test references.
