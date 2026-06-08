# Vault-validate Hook — Increment 2 (discovery checks) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `description:`-presence and lowercase-frontmatter-key checks to the existing validate-vault SessionStart hook; report-only, always exits 0, zero dependencies.

**Architecture:** Extend `skills/obsidian/hooks/validate_vault.py` with a hand-rolled frontmatter scanner, a hard-coded `DESCRIPTION_REQUIRED_DIRS` rule (guarded by a test against SKILL.md), and two new pure check functions wired into `format_report`/`main` via keyword args so Increment 1's call sites stay intact.

**Tech Stack:** Python 3 stdlib only, pytest. Builds on the shipped Increment 1 module.

**Spec:** `docs/superpowers/specs/2026-06-08-vault-validate-inc2-design.md`

**Baseline:** Increment 1 is on `main`. `validate_vault.py` currently ends at `main()`/`__main__` (line ~156); `test_validate_vault.py` has 22 passing tests. New work APPENDS — do not rewrite Increment 1 code except the one `format_report` signature change and the one `main()` wiring change in Task 4.

---

## File Structure

- **Modify** `skills/obsidian/hooks/validate_vault.py` — add `DESCRIPTION_REQUIRED_DIRS`, `_read_frontmatter`, `_requires_description`, `find_missing_description`, `find_uppercase_frontmatter_keys`; extend `format_report`; wire `main`.
- **Modify** `skills/obsidian/hooks/test_validate_vault.py` — append unit + drift-guard + subprocess tests.

---

## Task 1: Frontmatter scanner + description-required rule

**Files:**
- Modify: `skills/obsidian/hooks/validate_vault.py`
- Test: `skills/obsidian/hooks/test_validate_vault.py`

- [ ] **Step 1: Write the failing tests**

Append to `skills/obsidian/hooks/test_validate_vault.py`:

```python
def test_read_frontmatter_parses_top_level_keys(tmp_path):
    p = tmp_path / "n.md"
    p.write_text('---\nrole: Lead Engineer\norganisation: "[[ClearPoint]]"\naliases:\n  - Will\n  - Will V\n---\n# Body\n')
    fm = vv._read_frontmatter(p)
    assert fm["role"] == "Lead Engineer"
    assert fm["organisation"] == '"[[ClearPoint]]"'
    assert fm["aliases"] == ""        # key present; its list items are not parsed
    assert "Will" not in fm           # list items never become keys


def test_read_frontmatter_empty_when_no_block(tmp_path):
    p = tmp_path / "n.md"
    p.write_text("# Just a heading\nbody\n")
    assert vv._read_frontmatter(p) == {}


def test_requires_description_by_directory():
    from pathlib import Path as P
    assert vv._requires_description(P("people/Foo.md")) is True
    assert vv._requires_description(P("orgs/Bar.md")) is True
    assert vv._requires_description(P("glossary/x.md")) is True
    assert vv._requires_description(P("misc/y.md")) is True
    assert vv._requires_description(P("engagements/DSO2/context.md")) is True
    assert vv._requires_description(P("daily/detail/2026-01-01-x.md")) is True
    assert vv._requires_description(P("daily/2026-01-01.md")) is False
    assert vv._requires_description(P("daily/transcripts/x.md")) is False
    assert vv._requires_description(P("meta/architecture.md")) is False
    assert vv._requires_description(P("README.md")) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v -k "read_frontmatter or requires_description"`
Expected: FAIL — `AttributeError: module 'validate_vault' has no attribute '_read_frontmatter'` / `_requires_description`.

- [ ] **Step 3: Write minimal implementation**

In `skills/obsidian/hooks/validate_vault.py`, add the following immediately AFTER the `_iter_notes` function (before `find_empty_notes`):

```python
DESCRIPTION_REQUIRED_DIRS = ("people", "orgs", "glossary", "misc", "engagements")
# SKILL.md "Required fields per directory" is the source of truth for the above;
# daily/detail/ also requires description: (handled in _requires_description).
# The drift-guard test (test_description_required_dirs_match_skill_md) fails loudly
# if these diverge from that table.


def _read_frontmatter(path: Path) -> dict[str, str]:
    """Parse the leading ---/--- block into top-level key:value pairs.

    Returns {} when there is no frontmatter block. Only top-level `key: value`
    lines are captured; indented list items (e.g. under `aliases:`) and nested
    content don't match the key pattern and are ignored. No YAML dependency.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    lines = text.splitlines()
    i = 0
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    if i >= len(lines) or lines[i].strip() != "---":
        return {}
    fm: dict[str, str] = {}
    for line in lines[i + 1:]:
        if line.strip() == "---":
            break
        m = re.match(r"([A-Za-z0-9_-]+):(.*)", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return fm


def _requires_description(rel: Path) -> bool:
    """True if a note at this vault-relative path must carry a `description:`."""
    parts = rel.parts
    if parts and parts[0] in DESCRIPTION_REQUIRED_DIRS:
        return True
    if parts[:2] == ("daily", "detail"):
        return True
    return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: PASS (all prior 22 + the 3 new).

- [ ] **Step 5: Commit**

```bash
git add skills/obsidian/hooks/validate_vault.py skills/obsidian/hooks/test_validate_vault.py
git commit -m "feat: validate-vault — frontmatter scanner + description-required rule

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: `find_missing_description` check

**Files:**
- Modify: `skills/obsidian/hooks/validate_vault.py`
- Test: `skills/obsidian/hooks/test_validate_vault.py`

- [ ] **Step 1: Write the failing tests**

Append to `skills/obsidian/hooks/test_validate_vault.py`:

```python
def test_find_missing_description_flags_entity_without_it(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "NoDesc.md").write_text("---\nrole: x\n---\n# body\n")
    (tmp_path / "people" / "HasDesc.md").write_text("---\ndescription: a real person\n---\n# body\n")
    found = vv.find_missing_description(tmp_path)
    assert (tmp_path / "people" / "NoDesc.md") in found
    assert (tmp_path / "people" / "HasDesc.md") not in found


def test_find_missing_description_excludes_daily_and_transcripts(tmp_path):
    (tmp_path / "daily").mkdir()
    (tmp_path / "daily" / "detail").mkdir()
    (tmp_path / "daily" / "transcripts").mkdir()
    (tmp_path / "daily" / "2026-01-01.md").write_text("# Notes\n")
    (tmp_path / "daily" / "transcripts" / "t.md").write_text("raw transcript\n")
    (tmp_path / "daily" / "detail" / "2026-01-01-x.md").write_text("notes\n")
    found = vv.find_missing_description(tmp_path)
    assert (tmp_path / "daily" / "2026-01-01.md") not in found
    assert (tmp_path / "daily" / "transcripts" / "t.md") not in found
    assert (tmp_path / "daily" / "detail" / "2026-01-01-x.md") in found


def test_find_missing_description_uppercase_counts_as_missing(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Upper.md").write_text("---\nDescription: capitalized key\n---\n")
    assert (tmp_path / "people" / "Upper.md") in vv.find_missing_description(tmp_path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v -k missing_description`
Expected: FAIL — `AttributeError: module 'validate_vault' has no attribute 'find_missing_description'`.

- [ ] **Step 3: Write minimal implementation**

In `skills/obsidian/hooks/validate_vault.py`, add this immediately AFTER `find_duplicate_basenames`:

```python
def find_missing_description(vault: Path) -> list[Path]:
    """Return entity notes (per _requires_description) lacking a non-empty `description:`."""
    found = []
    for path in sorted(_iter_notes(vault)):
        if not _requires_description(path.relative_to(vault)):
            continue
        if not _read_frontmatter(path).get("description", "").strip():
            found.append(path)
    return found
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: PASS (all prior + 3 new).

- [ ] **Step 5: Commit**

```bash
git add skills/obsidian/hooks/validate_vault.py skills/obsidian/hooks/test_validate_vault.py
git commit -m "feat: validate-vault — detect entity notes missing description:

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: `find_uppercase_frontmatter_keys` check

**Files:**
- Modify: `skills/obsidian/hooks/validate_vault.py`
- Test: `skills/obsidian/hooks/test_validate_vault.py`

- [ ] **Step 1: Write the failing tests**

Append to `skills/obsidian/hooks/test_validate_vault.py`:

```python
def test_find_uppercase_frontmatter_keys_flags_capitalized(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Drift.md").write_text('---\nRole: x\nOrganisation: "[[Y]]"\ndescription: ok\n---\n')
    found = dict(vv.find_uppercase_frontmatter_keys(tmp_path))
    assert (tmp_path / "people" / "Drift.md") in found
    assert set(found[tmp_path / "people" / "Drift.md"]) == {"Role", "Organisation"}


def test_find_uppercase_frontmatter_keys_ignores_lowercase_and_aliases(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Good.md").write_text('---\nrole: x\ndescription: y\naliases:\n  - Will\n---\n')
    assert vv.find_uppercase_frontmatter_keys(tmp_path) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v -k uppercase_frontmatter`
Expected: FAIL — `AttributeError: module 'validate_vault' has no attribute 'find_uppercase_frontmatter_keys'`.

- [ ] **Step 3: Write minimal implementation**

In `skills/obsidian/hooks/validate_vault.py`, add this immediately AFTER `find_missing_description`:

```python
def find_uppercase_frontmatter_keys(vault: Path) -> list[tuple[Path, list[str]]]:
    """Return (path, bad_keys) for notes whose frontmatter has non-lowercase keys."""
    found = []
    for path in sorted(_iter_notes(vault)):
        bad = [k for k in _read_frontmatter(path) if k != k.lower()]
        if bad:
            found.append((path, bad))
    return found
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: PASS (all prior + 2 new).

- [ ] **Step 5: Commit**

```bash
git add skills/obsidian/hooks/validate_vault.py skills/obsidian/hooks/test_validate_vault.py
git commit -m "feat: validate-vault — detect non-lowercase frontmatter keys

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Extend `format_report` + wire `main` + subprocess test

**Files:**
- Modify: `skills/obsidian/hooks/validate_vault.py`
- Test: `skills/obsidian/hooks/test_validate_vault.py`

- [ ] **Step 1: Write the failing tests**

Append to `skills/obsidian/hooks/test_validate_vault.py`:

```python
def test_format_report_includes_missing_desc_and_bad_keys(tmp_path):
    (tmp_path / "people").mkdir()
    nodesc = tmp_path / "people" / "NoDesc.md"
    nodesc.write_text("---\nrole: x\n---\n")
    drift = tmp_path / "people" / "Drift.md"
    drift.write_text("---\nRole: x\n---\n")
    report = vv.format_report([], [], tmp_path, missing_desc=[nodesc], bad_keys=[(drift, ["Role"])])
    assert "Missing description: people/NoDesc.md" in report
    assert "Non-lowercase frontmatter keys: people/Drift.md (Role)" in report


def test_format_report_empty_with_all_kwargs_empty(tmp_path):
    assert vv.format_report([], [], tmp_path, missing_desc=[], bad_keys=[]) == ""


def test_hook_reports_missing_description(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "NoDesc.md").write_text("---\nrole: x\n---\n")
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert "Missing description: people/NoDesc.md" in r.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v -k "format_report_includes or reports_missing_description"`
Expected: FAIL — `format_report()` got an unexpected keyword argument `missing_desc` (and the subprocess test finds no "Missing description" in stdout).

- [ ] **Step 3: Write minimal implementation**

In `skills/obsidian/hooks/validate_vault.py`, REPLACE the entire existing `format_report` function (currently `def format_report(empty, dups, vault) -> str: ...`) with:

```python
def format_report(
    empty: list[Path],
    dups: list[tuple[str, list[Path]]],
    vault: Path,
    *,
    missing_desc: list[Path] = (),
    bad_keys: list[tuple[Path, list[str]]] = (),
) -> str:
    """Render findings as a nudge, or '' when there are none."""
    if not (empty or dups or missing_desc or bad_keys):
        return ""
    lines = ["Vault integrity issues found by validate-vault:"]
    for p in empty:
        rel = p.relative_to(vault)
        lines.append(f"- Empty note (no content): {rel} — a blank note is a dead wikilink target.")
    for name, paths in dups:
        dirs = ", ".join(sorted(str(p.relative_to(vault).parent) for p in paths))
        lines.append(
            f'- Duplicate basename "{name}": {dirs} — wikilinks resolve nondeterministically.'
        )
    for p in missing_desc:
        rel = p.relative_to(vault)
        lines.append(f"- Missing description: {rel} — invisible to the grep-survey discovery model.")
    for p, keys in bad_keys:
        rel = p.relative_to(vault)
        lines.append(
            f"- Non-lowercase frontmatter keys: {rel} ({', '.join(keys)}) — keys must be lowercase."
        )
    lines.append("Mention these to the user and offer to fix; do NOT auto-edit the vault.")
    return "\n".join(lines)
```

Then in `main()`, REPLACE the existing `report = format_report(...)` call with:

```python
        report = format_report(
            find_empty_notes(vault),
            find_duplicate_basenames(vault),
            vault,
            missing_desc=find_missing_description(vault),
            bad_keys=find_uppercase_frontmatter_keys(vault),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: PASS — all tests, including Increment 1's existing positional `format_report` tests (`test_format_report_empty_when_clean`, `test_format_report_lists_findings`) which still call it with 3 positional args.

- [ ] **Step 5: Commit**

```bash
git add skills/obsidian/hooks/validate_vault.py skills/obsidian/hooks/test_validate_vault.py
git commit -m "feat: validate-vault — surface discovery findings in the nudge

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Drift-guard test + real-vault verification

**Files:**
- Test: `skills/obsidian/hooks/test_validate_vault.py`

- [ ] **Step 1: Write the failing test**

Append to `skills/obsidian/hooks/test_validate_vault.py`:

```python
def _skill_md_required_rows():
    """Map each `dir`-cell -> Required-cell from SKILL.md's frontmatter table.

    Treats escaped pipes (\\|) inside cells as literal, not column separators.
    """
    repo = Path(vv.__file__).resolve().parents[3]
    skill = (repo / "skills" / "obsidian" / "SKILL.md").read_text(encoding="utf-8")
    assert "Required fields per directory" in skill
    rows = {}
    for line in skill.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        safe = line.replace(r"\|", "\x00")
        cells = [c.replace("\x00", "|").strip() for c in safe.strip().strip("|").split("|")]
        if len(cells) >= 2:
            rows[cells[0]] = cells[1]
    return skill, rows


def test_description_required_dirs_match_skill_md():
    skill, rows = _skill_md_required_rows()

    def required_cell_for(token):
        for dircell, req in rows.items():
            if token in dircell:
                return req
        return None

    # 1. Every code-required dir is a SKILL.md row whose Required cell has description:
    for d in vv.DESCRIPTION_REQUIRED_DIRS:
        cell = required_cell_for(f"`{d}/")
        assert cell is not None, f"no SKILL.md row for {d}/"
        assert "description:" in cell, f"{d}/ row no longer requires description: in SKILL.md"
    detail = required_cell_for("`daily/detail/`")
    assert detail is not None and "description:" in detail, "daily/detail/ must require description:"

    # 2. The top-level daily/ row must NOT require description:
    daily_top = rows.get("`daily/`")
    assert daily_top is not None, "no `daily/` row found in SKILL.md table"
    assert "description:" not in daily_top, "daily/ must not require description:"

    # 3. The lowercase-keys rule must still be present.
    assert re.search(r"All keys.*lowercase", skill), "SKILL.md lowercase-keys rule missing"
```

Note: this test imports `re` and `Path`, both already imported at the top of the test file from earlier tasks. `vv.DESCRIPTION_REQUIRED_DIRS` and `vv.__file__` are used to locate the real SKILL.md.

- [ ] **Step 2: Run the test to verify it passes against the real SKILL.md**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v -k description_required_dirs_match`
Expected: PASS — the current SKILL.md table matches the hard-coded rules. (If it FAILS, the rules and SKILL.md genuinely disagree — stop and reconcile before continuing; do not weaken the test to force a pass.)

- [ ] **Step 3: Run the full suite**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: PASS (all Increment 1 + Increment 2 tests).

- [ ] **Step 4: Verify on the real vault**

Run:
```bash
echo "{\"cwd\": \"$OBSIDIAN_VAULT\"}" | python3 /c/dev/agents/skills/obsidian/hooks/validate_vault.py; echo "exit=$?"
```
Expected: the nudge now ALSO lists `Missing description:` lines (several people/glossary/misc notes) and `Non-lowercase frontmatter keys:` lines (e.g. `people/Gagan Dhaliwal.md (Role, Organisation, ...)`), alongside the Increment 1 empty-note + duplicate-basename findings, exit=0. Report the full verbatim output.

- [ ] **Step 5: Commit**

```bash
git add skills/obsidian/hooks/test_validate_vault.py
git commit -m "test: drift-guard validate-vault rules against SKILL.md table

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Definition of done (Increment 2)

- Full suite green (`python3 -m pytest skills/obsidian/hooks/test_validate_vault.py`).
- The hook, run against the real vault, additionally flags missing-`description:` entity notes and non-lowercase frontmatter keys, alongside the Increment 1 findings; still report-only and exits 0.
- `format_report`'s Increment 1 positional call sites and tests are unchanged.
- The drift-guard test passes against the current SKILL.md and would fail if the rules diverged.

Out of scope (deferred): the per-directory required-key matrix (`client:`/`status:`/`full:`/`relationship:`/`organisation:`/`role:`), backfilling/auto-fix, freshness checks (Increment 3), single-pass read optimisation.
