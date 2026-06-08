# No-wikilinks-in-`description:` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Codify "`description:` is plain prose — no `[[wikilinks]]`" in the obsidian skill + authoring skills + vault conventions docs, and add a validate-vault hook check that detects violations.

**Architecture:** New pure check `find_wikilinks_in_description` in the existing hook (TDD), wired into `format_report`/`main`; plus prose edits to `obsidian/SKILL.md` (canonical) and the description-authoring skills; plus a rule in the vault's `meta/conventions/frontmatter.md`. Report-only; the hook surfaces the ~90 existing violations rather than migrating them.

**Tech Stack:** Python 3 stdlib, pytest. Builds on the merged Inc1+Inc2 hook.

**Spec:** `docs/superpowers/specs/2026-06-08-no-wikilinks-in-description-design.md`

**Worktree:** all git work is on branch `feat/no-wikilinks-in-description` in `/c/dev/agents/.claude/worktrees/nowiki`. Stage explicit paths only; never `git commit -a`/`--amend -a`. Task 4 edits the VAULT (`/c/notes`, not git) and produces no commit.

---

## Task 1: `find_wikilinks_in_description` check

**Files:**
- Modify: `skills/obsidian/hooks/validate_vault.py`
- Test: `skills/obsidian/hooks/test_validate_vault.py`

- [ ] **Step 1: Write the failing tests** — APPEND to `skills/obsidian/hooks/test_validate_vault.py`:

```python
def test_find_wikilinks_in_description_flags_wikilink(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Linked.md").write_text('---\ndescription: "Lead at [[ClearPoint]]"\n---\n# body\n')
    assert (tmp_path / "people" / "Linked.md") in vv.find_wikilinks_in_description(tmp_path)


def test_find_wikilinks_in_description_ignores_plain_and_body_links(tmp_path):
    (tmp_path / "people").mkdir()
    # plain description; the [[ClearPoint]] is in the BODY, which must NOT be flagged
    (tmp_path / "people" / "Plain.md").write_text("---\ndescription: Lead at ClearPoint\n---\n# body [[ClearPoint]]\n")
    assert vv.find_wikilinks_in_description(tmp_path) == []


def test_find_wikilinks_in_description_ignores_no_description(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "NoFm.md").write_text("# just body, no frontmatter\n")
    assert vv.find_wikilinks_in_description(tmp_path) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v -k wikilinks_in_description`
Expected: FAIL — `AttributeError: module 'validate_vault' has no attribute 'find_wikilinks_in_description'`.

- [ ] **Step 3: Write minimal implementation** — in `skills/obsidian/hooks/validate_vault.py`, add this IMMEDIATELY AFTER `find_uppercase_frontmatter_keys`:

```python
def find_wikilinks_in_description(vault: Path) -> list[Path]:
    """Return notes whose `description:` frontmatter contains a [[wikilink]] (must be plain prose)."""
    found = []
    for path in sorted(_iter_notes(vault)):
        if "[[" in _read_frontmatter(path).get("description", ""):
            found.append(path)
    return found
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: PASS (all prior + 3 new).

- [ ] **Step 5: Commit** (explicit paths, no -a):

```bash
git add skills/obsidian/hooks/validate_vault.py skills/obsidian/hooks/test_validate_vault.py
git commit -m "feat: validate-vault — detect wikilinks in description:

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Wire into `format_report` + `main` + subprocess test

**Files:**
- Modify: `skills/obsidian/hooks/validate_vault.py`
- Test: `skills/obsidian/hooks/test_validate_vault.py`

- [ ] **Step 1: Write the failing tests** — APPEND to `skills/obsidian/hooks/test_validate_vault.py`:

```python
def test_format_report_includes_desc_links(tmp_path):
    (tmp_path / "people").mkdir()
    linked = tmp_path / "people" / "Linked.md"
    linked.write_text('---\ndescription: "Lead at [[ClearPoint]]"\n---\n')
    report = vv.format_report([], [], tmp_path, desc_links=[linked])
    assert "Wikilink in description: people/Linked.md" in report


def test_format_report_empty_with_desc_links_empty(tmp_path):
    assert vv.format_report([], [], tmp_path, desc_links=[]) == ""


def test_hook_reports_wikilink_in_description(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Linked.md").write_text('---\ndescription: "Lead at [[ClearPoint]]"\n---\n')
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert "Wikilink in description: people/Linked.md" in r.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v -k "desc_links or wikilink_in_description"`
Expected: FAIL — `format_report()` got an unexpected keyword argument `desc_links` (and the subprocess test finds no "Wikilink in description" line).

- [ ] **Step 3: Write minimal implementation**

(a) In `skills/obsidian/hooks/validate_vault.py`, change the `format_report` signature to add the new keyword-only param. Replace:
```python
    *,
    missing_desc: list[Path] = (),
    bad_keys: list[tuple[Path, list[str]]] = (),
) -> str:
```
with:
```python
    *,
    missing_desc: list[Path] = (),
    bad_keys: list[tuple[Path, list[str]]] = (),
    desc_links: list[Path] = (),
) -> str:
```

(b) Change the empty-guard. Replace:
```python
    if not (empty or dups or missing_desc or bad_keys):
        return ""
```
with:
```python
    if not (empty or dups or missing_desc or bad_keys or desc_links):
        return ""
```

(c) Add the new section. Immediately AFTER the `for p, keys in bad_keys:` loop (the block ending with the `keys must be lowercase.` append) and BEFORE the final `lines.append("Mention these to the user...")`, insert:
```python
    for p in desc_links:
        rel = p.relative_to(vault)
        lines.append(f"- Wikilink in description: {rel} — descriptions must be plain text (no [[...]]).")
```

(d) In `main()`, add the new check to the `format_report(...)` call. Replace:
```python
            missing_desc=find_missing_description(vault),
            bad_keys=find_uppercase_frontmatter_keys(vault),
        )
```
with:
```python
            missing_desc=find_missing_description(vault),
            bad_keys=find_uppercase_frontmatter_keys(vault),
            desc_links=find_wikilinks_in_description(vault),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: PASS — all tests, including the existing positional `format_report` tests (unchanged).

- [ ] **Step 5: Commit** (explicit paths, no -a):

```bash
git add skills/obsidian/hooks/validate_vault.py skills/obsidian/hooks/test_validate_vault.py
git commit -m "feat: validate-vault — surface wikilink-in-description in the nudge

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Codify the rule in the skills

**Files:**
- Modify: `skills/obsidian/SKILL.md`, `skills/decant/SKILL.md`, `skills/transcript/SKILL.md`, `skills/slack-thread/SKILL.md`

- [ ] **Step 1: Add the canonical rule to `obsidian/SKILL.md`**

Find the "Description shape:" block (the two bullets `✅`/`❌` after the line beginning `**Description shape:**`). Immediately AFTER the `❌` bullet line (`- ❌ \`"An engineer at Adventure Bay Council."\` — too generic to surface in a grep survey.`), add this new bullet:

```markdown
- **Plain text — no wikilinks.** Spell entity names out; never put `[[wikilinks]]` in `description:`. A wikilink in a free-text frontmatter value creates no Obsidian graph edge, adds noise to the `^description:` survey, and duplicates the body's linking. (Entity-relationship fields `organisation:`/`client:` keep wikilink syntax — see "Wikilinks in frontmatter" above.)
```

- [ ] **Step 2: Add a terse pointer to `decant/SKILL.md`**

Find the line ending `Required frontmatter: \`description:\`.` (in the "Detail notes." bullet). Replace `Required frontmatter: \`description:\`.` with:
```
Required frontmatter: `description:` (plain text — no `[[wikilinks]]`).
```

- [ ] **Step 3: Add a terse pointer to `transcript/SKILL.md`**

Find the template line `description: "<specific ~15-word description>"` and replace it with:
```
description: "<specific ~15-word description — plain text, no [[wikilinks]]>"
```

- [ ] **Step 4: Add a terse pointer to `slack-thread/SKILL.md`**

Find the template line `description: "<~12-word description, mirrors H1>"` and replace it with:
```
description: "<~12-word description, mirrors H1 — plain text, no [[wikilinks]]>"
```

- [ ] **Step 5: Verify and commit** (explicit paths, no -a):

Verify the edits read correctly (`git diff`). Then:
```bash
git add skills/obsidian/SKILL.md skills/decant/SKILL.md skills/transcript/SKILL.md skills/slack-thread/SKILL.md
git commit -m "docs: codify plain-text (no-wikilink) description: rule in skills

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

Note: `refresh-person` and `background` are NOT edited — `refresh-person` activates the obsidian skill (so the canonical rule is in-context), and `background` does not currently author a `description:` (a separate review finding). No restatement, to avoid drift.

---

## Task 4: Codify the rule in the vault conventions docs (VAULT — not git)

**Files (in `/c/notes`, NOT the worktree):**
- Modify: `/c/notes/meta/conventions/frontmatter.md`
- Possibly modify: the other `/c/notes/meta/conventions/*.md` files (only to fix description examples that contain wikilinks)

This task edits the vault directly. It produces NO git commit (the vault is not a git repo). Follow obsidian vault conventions for edits.

- [ ] **Step 1: Add the rule to `frontmatter.md`**

Read `/c/notes/meta/conventions/frontmatter.md`. Find where it describes the `description:` field. Add this sentence/bullet adjacent to that description (match the file's existing prose/bullet style):
```
`description:` is plain prose — spell entity names out; do NOT use `[[wikilinks]]` (they create no graph edge in a free-text property, add noise to the `^description:` survey, and duplicate the body's links). Entity-relationship fields `organisation:`/`client:` keep wikilinks, quote-wrapped.
```

- [ ] **Step 2: Scan the per-entity conventions files for wikilink-bearing description examples**

Run: `grep -rn -E '^description:.*\[\[' /c/notes/meta/conventions/` and also check any `description: "..."` example lines in `people-notes.md`, `detail-notes.md`, `engagements.md`, `glossary.md`, `orgs.md`, `misc-notes.md`. For each example description that contains `[[...]]`, rewrite it to plain text (`[[Target|Alias]]` → `Alias`, `[[Target]]` → `Target`). Do NOT touch `organisation:`/`client:` example values (those keep wikilinks). If a file has no wikilink-bearing description example, leave it unchanged.

- [ ] **Step 3: Verify**

Run: `grep -rn -E '^description:.*\[\[' /c/notes/meta/conventions/`
Expected: no matches (every example description is now plain text).

---

## Definition of done

- Full hook suite green (`python3 -m pytest skills/obsidian/hooks/test_validate_vault.py`).
- The hook, run against the real vault, additionally flags the ~90 wikilink-in-`description:` notes alongside existing findings; still report-only, exits 0.
- `obsidian/SKILL.md` states the plain-text rule canonically; `decant`/`transcript`/`slack-thread` carry a terse deferring pointer.
- `/c/notes/meta/conventions/frontmatter.md` states the rule; no convention-doc description example contains a wikilink.
- Existing positional `format_report` call sites/tests unchanged.

Out of scope: migrating the 90 existing vault notes; per-directory required-key matrix; freshness checks.
