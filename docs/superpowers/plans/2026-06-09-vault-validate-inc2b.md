# Vault-validate Inc 2b (per-directory required-key matrix) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enforce SKILL.md's per-directory required frontmatter keys (beyond `description:`) plus enum-value validation for `status:`/`relationship:`, as new validate-vault hook checks.

**Architecture:** Hard-coded `_required_keys` matrix + `ENUM_FIELDS` (guarded by a SKILL.md drift test), two new pure checks (`find_missing_required_keys`, `find_invalid_enum_values`), wired into `format_report`/`main` via keyword args. Report-only, exits 0.

**Tech Stack:** Python 3 stdlib, pytest. Builds on the merged Inc1+Inc2a+no-wikilinks hook.

**Spec:** `docs/superpowers/specs/2026-06-09-vault-validate-inc2b-design.md`

**Worktree:** all work on branch `feat/vault-validate-inc2b` in `/c/dev/agents/.claude/worktrees/inc2b`. Stage explicit paths only; never `git commit -a`/`--amend -a`.

---

## Task 1: Rule encoding — `ENUM_FIELDS` + `_required_keys`

**Files:** Modify `skills/obsidian/hooks/validate_vault.py`; Test `skills/obsidian/hooks/test_validate_vault.py`

- [ ] **Step 1: Write the failing tests** — APPEND to `test_validate_vault.py`:

```python
def test_required_keys_by_directory():
    from pathlib import Path as P
    assert vv._required_keys(P("people/Foo.md")) == {"organisation", "role"}
    assert vv._required_keys(P("orgs/Bar.md")) == {"relationship"}
    assert vv._required_keys(P("glossary/x.md")) == {"full"}
    assert vv._required_keys(P("engagements/DSO2/DSO2.md")) == {"client", "status"}
    assert vv._required_keys(P("engagements/DSO2/context.md")) == set()
    assert vv._required_keys(P("engagements/DSO2/glossary/MVR.md")) == {"full"}
    assert vv._required_keys(P("misc/x.md")) == set()
    assert vv._required_keys(P("daily/2026-01-01.md")) == set()
    assert vv._required_keys(P("daily/detail/2026-01-01-x.md")) == set()


def test_enum_fields_constant():
    assert vv.ENUM_FIELDS["status"] == {"active", "complete"}
    assert vv.ENUM_FIELDS["relationship"] == {"employer", "client", "partner", "vendor"}
```

- [ ] **Step 2: Run to verify fail**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v -k "required_keys_by_directory or enum_fields_constant"`
Expected: FAIL — `AttributeError: module 'validate_vault' has no attribute '_required_keys'` / `ENUM_FIELDS`.

- [ ] **Step 3: Write minimal implementation** — in `validate_vault.py`, add the following IMMEDIATELY AFTER the `_requires_description` function:

```python
ENUM_FIELDS = {
    "status": {"active", "complete"},
    "relationship": {"employer", "client", "partner", "vendor"},
}


def _required_keys(rel: Path) -> set[str]:
    """Non-`description` required frontmatter keys for a vault-relative path (per SKILL.md).

    `description:` is enforced separately by find_missing_description, so it is
    intentionally excluded here. The drift-guard test keeps this aligned with the
    SKILL.md "Required fields per directory" table.
    """
    parts = rel.parts
    if not parts:
        return set()
    top = parts[0]
    if top == "people":
        return {"organisation", "role"}
    if top == "orgs":
        return {"relationship"}
    if top == "glossary":
        return {"full"}
    if top == "engagements":
        # engagement-scoped glossary: engagements/<E>/glossary/<term>.md
        if len(parts) >= 4 and parts[2] == "glossary":
            return {"full"}
        # engagement overview: engagements/<E>/<E>.md (file named after its dir)
        if len(parts) == 3 and parts[2] == f"{parts[1]}.md":
            return {"client", "status"}
        return set()
    return set()
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: PASS (all prior + 2 new).

- [ ] **Step 5: Commit** (explicit paths, no -a):

```bash
git add skills/obsidian/hooks/validate_vault.py skills/obsidian/hooks/test_validate_vault.py
git commit -m "feat: validate-vault — per-directory required-key matrix + enum sets

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: `find_missing_required_keys`

**Files:** Modify `skills/obsidian/hooks/validate_vault.py`; Test `skills/obsidian/hooks/test_validate_vault.py`

- [ ] **Step 1: Write the failing tests** — APPEND to `test_validate_vault.py`:

```python
def test_find_missing_required_keys_flags_people_missing_role(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "NoRole.md").write_text('---\norganisation: "[[X]]"\ndescription: d\n---\n')
    found = dict(vv.find_missing_required_keys(tmp_path))
    assert found[tmp_path / "people" / "NoRole.md"] == ["role"]


def test_find_missing_required_keys_passes_complete_people(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Ok.md").write_text('---\norganisation: "[[X]]"\nrole: Lead\ndescription: d\n---\n')
    assert vv.find_missing_required_keys(tmp_path) == []


def test_find_missing_required_keys_engagement_overview(tmp_path):
    (tmp_path / "engagements" / "DSO2").mkdir(parents=True)
    (tmp_path / "engagements" / "DSO2" / "DSO2.md").write_text("---\ndescription: d\n---\n")
    (tmp_path / "engagements" / "DSO2" / "context.md").write_text("---\ndescription: d\n---\n")
    found = dict(vv.find_missing_required_keys(tmp_path))
    assert found[tmp_path / "engagements" / "DSO2" / "DSO2.md"] == ["client", "status"]
    assert (tmp_path / "engagements" / "DSO2" / "context.md") not in found  # companion file: no extra keys
```

- [ ] **Step 2: Run to verify fail**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v -k find_missing_required_keys`
Expected: FAIL — `AttributeError: module 'validate_vault' has no attribute 'find_missing_required_keys'`.

- [ ] **Step 3: Write minimal implementation** — in `validate_vault.py`, add IMMEDIATELY AFTER `find_wikilinks_in_description`:

```python
def find_missing_required_keys(vault: Path) -> list[tuple[Path, list[str]]]:
    """Return (path, missing keys) for notes lacking required frontmatter keys (per the directory matrix)."""
    found = []
    for path in sorted(_iter_notes(vault)):
        required = _required_keys(path.relative_to(vault))
        if not required:
            continue
        missing = sorted(required - set(_read_frontmatter(path)))
        if missing:
            found.append((path, missing))
    return found
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: PASS (all prior + 3 new).

- [ ] **Step 5: Commit** (explicit paths, no -a):

```bash
git add skills/obsidian/hooks/validate_vault.py skills/obsidian/hooks/test_validate_vault.py
git commit -m "feat: validate-vault — detect missing required frontmatter keys

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: `find_invalid_enum_values` (+ `_strip_quotes` helper)

**Files:** Modify `skills/obsidian/hooks/validate_vault.py`; Test `skills/obsidian/hooks/test_validate_vault.py`

- [ ] **Step 1: Write the failing tests** — APPEND to `test_validate_vault.py`:

```python
def test_find_invalid_enum_values_flags_bad_relationship(tmp_path):
    (tmp_path / "orgs").mkdir()
    (tmp_path / "orgs" / "Bad.md").write_text("---\nrelationship: friend\ndescription: d\n---\n")
    assert (tmp_path / "orgs" / "Bad.md", "relationship", "friend") in vv.find_invalid_enum_values(tmp_path)


def test_find_invalid_enum_values_accepts_valid_quoted_status(tmp_path):
    (tmp_path / "engagements" / "DSO2").mkdir(parents=True)
    (tmp_path / "engagements" / "DSO2" / "DSO2.md").write_text('---\nclient: "[[X]]"\nstatus: "active"\ndescription: d\n---\n')
    assert vv.find_invalid_enum_values(tmp_path) == []


def test_find_invalid_enum_values_flags_bad_status(tmp_path):
    (tmp_path / "engagements" / "DSO2").mkdir(parents=True)
    (tmp_path / "engagements" / "DSO2" / "DSO2.md").write_text('---\nclient: "[[X]]"\nstatus: done\ndescription: d\n---\n')
    assert (tmp_path / "engagements" / "DSO2" / "DSO2.md", "status", "done") in vv.find_invalid_enum_values(tmp_path)


def test_find_invalid_enum_values_ignores_absent_field(tmp_path):
    # relationship absent -> missing-key check owns that, not the enum check
    (tmp_path / "orgs").mkdir()
    (tmp_path / "orgs" / "NoRel.md").write_text("---\ndescription: d\n---\n")
    assert vv.find_invalid_enum_values(tmp_path) == []
```

- [ ] **Step 2: Run to verify fail**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v -k find_invalid_enum_values`
Expected: FAIL — `AttributeError: module 'validate_vault' has no attribute 'find_invalid_enum_values'`.

- [ ] **Step 3: Write minimal implementation** — in `validate_vault.py`, add IMMEDIATELY AFTER `find_missing_required_keys`:

```python
def _strip_quotes(value: str) -> str:
    """Strip a single matching surrounding quote pair from a frontmatter value."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def find_invalid_enum_values(vault: Path) -> list[tuple[Path, str, str]]:
    """Return (path, field, value) where a required enum field is present but its value is not allowed."""
    found = []
    for path in sorted(_iter_notes(vault)):
        required = _required_keys(path.relative_to(vault))
        fm = _read_frontmatter(path)
        for field, allowed in ENUM_FIELDS.items():
            if field in required and field in fm:
                value = _strip_quotes(fm[field])
                if value not in allowed:
                    found.append((path, field, value))
    return found
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: PASS (all prior + 4 new).

- [ ] **Step 5: Commit** (explicit paths, no -a):

```bash
git add skills/obsidian/hooks/validate_vault.py skills/obsidian/hooks/test_validate_vault.py
git commit -m "feat: validate-vault — validate status/relationship enum values

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Wire into `format_report` + `main` + subprocess test

**Files:** Modify `skills/obsidian/hooks/validate_vault.py`; Test `skills/obsidian/hooks/test_validate_vault.py`

- [ ] **Step 1: Write the failing tests** — APPEND to `test_validate_vault.py`:

```python
def test_format_report_includes_missing_keys_and_bad_enums(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "orgs").mkdir()
    nokey = tmp_path / "people" / "NoRole.md"
    nokey.write_text("---\norganisation: x\ndescription: d\n---\n")
    badenum = tmp_path / "orgs" / "Bad.md"
    badenum.write_text("---\nrelationship: friend\ndescription: d\n---\n")
    report = vv.format_report(
        [], [], tmp_path,
        missing_keys=[(nokey, ["role"])],
        bad_enums=[(badenum, "relationship", "friend")],
    )
    assert "Missing required frontmatter: people/NoRole.md (role)" in report
    assert 'Invalid relationship value: orgs/Bad.md ("friend")' in report
    assert "must be one of client, employer, partner, vendor" in report


def test_format_report_empty_with_inc2b_kwargs_empty(tmp_path):
    assert vv.format_report([], [], tmp_path, missing_keys=[], bad_enums=[]) == ""


def test_hook_reports_missing_required_key(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "NoRole.md").write_text("---\norganisation: x\ndescription: d\n---\n")
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert "Missing required frontmatter: people/NoRole.md (role)" in r.stdout
```

Note: the enum allowed-list is rendered sorted, so `relationship`'s set renders as `client, employer, partner, vendor`.

- [ ] **Step 2: Run to verify fail**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v -k "missing_keys_and_bad_enums or inc2b_kwargs or reports_missing_required_key"`
Expected: FAIL — `format_report()` got an unexpected keyword argument `missing_keys`.

- [ ] **Step 3: Write minimal implementation**

(a) In `format_report`'s signature, after the `desc_links: list[Path] = (),` line and before `) -> str:`, add:
```python
    missing_keys: list[tuple[Path, list[str]]] = (),
    bad_enums: list[tuple[Path, str, str]] = (),
```

(b) Change the empty-guard line `    if not (empty or dups or missing_desc or bad_keys or desc_links):` to:
```python
    if not (empty or dups or missing_desc or bad_keys or desc_links or missing_keys or bad_enums):
```

(c) Immediately AFTER the `for p in desc_links:` loop body and BEFORE the final `lines.append("Mention these to the user and offer to fix; do NOT auto-edit the vault.")`, insert:
```python
    for p, keys in missing_keys:
        rel = p.relative_to(vault)
        lines.append(
            f"- Missing required frontmatter: {rel} ({', '.join(keys)}) — required for this directory."
        )
    for p, field, value in bad_enums:
        rel = p.relative_to(vault)
        allowed = ", ".join(sorted(ENUM_FIELDS[field]))
        lines.append(f'- Invalid {field} value: {rel} ("{value}") — must be one of {allowed}.')
```

(d) In `main()`, in the `format_report(...)` call, after the `desc_links=find_wikilinks_in_description(vault),` line, add:
```python
            missing_keys=find_missing_required_keys(vault),
            bad_enums=find_invalid_enum_values(vault),
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: PASS — all tests, including existing positional `format_report` tests (unchanged).

- [ ] **Step 5: Commit** (explicit paths, no -a):

```bash
git add skills/obsidian/hooks/validate_vault.py skills/obsidian/hooks/test_validate_vault.py
git commit -m "feat: validate-vault — surface missing-required-key + bad-enum findings

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Drift-guard the matrix against SKILL.md + real-vault verify

**Files:** Test `skills/obsidian/hooks/test_validate_vault.py`

- [ ] **Step 1: Write the test** — APPEND to `test_validate_vault.py` (reuses the existing `_skill_md_required_rows` helper):

```python
def test_required_key_matrix_matches_skill_md():
    skill, rows = _skill_md_required_rows()

    def req(key):
        assert key in rows, f"SKILL.md table missing row {key}"
        return rows[key]

    people = req("`people/`")
    assert "organisation:" in people and "role:" in people

    orgs = req("`orgs/`")
    assert "relationship:" in orgs
    for v in vv.ENUM_FIELDS["relationship"]:
        assert v in orgs, f"orgs relationship enum value {v!r} missing from SKILL.md"

    assert "full:" in req("`glossary/`")
    assert "full:" in req("`engagements/<Engagement>/glossary/`")

    overview = req("`engagements/<Engagement>/<Engagement>.md`")
    assert "client:" in overview and "status:" in overview
    for v in vv.ENUM_FIELDS["status"]:
        assert v in overview, f"status enum value {v!r} missing from SKILL.md"
```

- [ ] **Step 2: Run the test (and full suite)**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: PASS — the current SKILL.md table matches the hard-coded matrix/enums. If `test_required_key_matrix_matches_skill_md` FAILS, the code and SKILL.md genuinely disagree — STOP and reconcile; do NOT weaken the test.

- [ ] **Step 3: Verify on the real vault**

Run:
```bash
echo "{\"cwd\": \"$OBSIDIAN_VAULT\"}" | python3 /c/dev/agents/.claude/worktrees/inc2b/skills/obsidian/hooks/validate_vault.py 2>/dev/null | grep -E "Missing required frontmatter:|Invalid (status|relationship) value:" | head -20
```
Report the sample output (expected: people notes missing `organisation`/`role` — e.g. the capitalised-key notes — plus any orgs/engagements gaps). This is read-only.

- [ ] **Step 4: Commit** (explicit path, no -a):

```bash
git add skills/obsidian/hooks/test_validate_vault.py
git commit -m "test: drift-guard the required-key matrix + enums against SKILL.md

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Definition of done

- Full suite green (`python3 -m pytest skills/obsidian/hooks/test_validate_vault.py`).
- The hook additionally flags missing required keys (`organisation`/`role`/`client`/`status`/`full`/`relationship`) per the directory matrix and invalid `status`/`relationship` enum values; report-only, exits 0.
- `_required_keys`/`ENUM_FIELDS` are drift-guarded against the SKILL.md table.
- Existing positional `format_report` call sites/tests unchanged.

Out of scope: fixing the data; freshness checks (Inc 3); warnings tier / `--fix` (Inc 4); nudge-volume summarisation.
