# Vault-validate Hook (Increment 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a deterministic, zero-dependency SessionStart hook that detects vault integrity defects (empty notes, duplicate basenames) and nudges the user — report-only, never mutates, always exits 0.

**Architecture:** A single Python module `skills/obsidian/hooks/validate_vault.py` split into **pure check functions** (unit-tested directly) and a **thin hook shell** (stdin/cwd-guard/stdout/exit-0, integration-tested via subprocess). Registered as a second SessionStart hook alongside the decant nudge. Supersedes the dead vault-root `validate.py`.

**Tech Stack:** Python 3 (stdlib only — no PyYAML), pytest. Mirrors the contract of `skills/decant/hooks/undecanted-notes.sh`.

**Spec:** `docs/superpowers/specs/2026-06-08-vault-validate-hook-design.md`

**Naming note:** the file is `validate_vault.py` (underscore, not hyphen) so the test suite can `import validate_vault`. The hook command references this exact path.

---

## File Structure

- **Create** `skills/obsidian/hooks/validate_vault.py` — the hook. Pure checks + hook shell.
- **Create** `skills/obsidian/hooks/test_validate_vault.py` — pytest suite (unit + subprocess integration).
- **Modify** `~/.claude/settings.json` — add the second SessionStart hook entry (via the `update-config` skill).
- **Modify** `README.md` — document the hook, its install, and the `validate.py` supersession.

---

## Task 1: `find_empty_notes` + module scaffold

**Files:**
- Create: `skills/obsidian/hooks/validate_vault.py`
- Test: `skills/obsidian/hooks/test_validate_vault.py`

- [ ] **Step 1: Write the failing test**

Create `skills/obsidian/hooks/test_validate_vault.py`:

```python
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import validate_vault as vv


def _vault(tmp_path: Path) -> Path:
    """A minimal, valid vault: a few non-empty notes in typical dirs."""
    (tmp_path / "people").mkdir()
    (tmp_path / "misc").mkdir()
    (tmp_path / "people" / "Real Person.md").write_text("# Real Person\nbody\n")
    (tmp_path / "misc" / "A Note.md").write_text("content\n")
    return tmp_path


def test_find_empty_notes_flags_zero_byte_note(tmp_path):
    vault = _vault(tmp_path)
    (vault / "people" / "Empty.md").write_text("")
    found = vv.find_empty_notes(vault)
    assert vault / "people" / "Empty.md" in found


def test_find_empty_notes_flags_whitespace_only_note(tmp_path):
    vault = _vault(tmp_path)
    (vault / "misc" / "Blank.md").write_text("   \n\t\n")
    found = vv.find_empty_notes(vault)
    assert vault / "misc" / "Blank.md" in found


def test_find_empty_notes_ignores_nonempty_and_dotdirs(tmp_path):
    vault = _vault(tmp_path)
    (vault / ".obsidian").mkdir()
    (vault / ".obsidian" / "Empty In Dotdir.md").write_text("")  # excluded
    found = vv.find_empty_notes(vault)
    assert found == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'validate_vault'` (the module doesn't exist yet).

- [ ] **Step 3: Write minimal implementation**

Create `skills/obsidian/hooks/validate_vault.py`:

```python
#!/usr/bin/env python3
"""SessionStart hook — validate vault integrity and nudge.

Scans $OBSIDIAN_VAULT for integrity defects (empty notes, duplicate basenames)
and prints a nudge to stdout (SessionStart stdout is injected as session
context). Report-only: never edits the vault. Always exits 0.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path


def _iter_notes(vault: Path):
    """Yield *.md files under vault, skipping dot-directories (.obsidian, .trash, .claude)."""
    for path in vault.rglob("*.md"):
        if any(part.startswith(".") for part in path.relative_to(vault).parts):
            continue
        yield path


def find_empty_notes(vault: Path) -> list[Path]:
    """Return .md files whose content is empty or whitespace-only."""
    found = []
    for path in sorted(_iter_notes(vault)):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not text.strip():
            found.append(path)
    return found
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add skills/obsidian/hooks/validate_vault.py skills/obsidian/hooks/test_validate_vault.py
git commit -m "feat: validate-vault hook — detect empty notes

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: `find_duplicate_basenames`

**Files:**
- Modify: `skills/obsidian/hooks/validate_vault.py`
- Test: `skills/obsidian/hooks/test_validate_vault.py`

- [ ] **Step 1: Write the failing test**

Append to `skills/obsidian/hooks/test_validate_vault.py`:

```python
def test_find_duplicate_basenames_flags_collision(tmp_path):
    vault = _vault(tmp_path)
    (vault / "engagements").mkdir()
    (vault / "engagements" / "Dup.md").write_text("stub\n")
    (vault / "misc" / "Dup.md").write_text("rich\n")
    dups = vv.find_duplicate_basenames(vault)
    names = [name for name, _ in dups]
    assert "Dup.md" in names
    paths = dict(dups)["Dup.md"]
    assert (vault / "engagements" / "Dup.md") in paths
    assert (vault / "misc" / "Dup.md") in paths


def test_find_duplicate_basenames_ignores_unique(tmp_path):
    vault = _vault(tmp_path)  # all basenames unique
    assert vv.find_duplicate_basenames(vault) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: FAIL — `AttributeError: module 'validate_vault' has no attribute 'find_duplicate_basenames'`.

- [ ] **Step 3: Write minimal implementation**

Add to `skills/obsidian/hooks/validate_vault.py` after `find_empty_notes`:

```python
def find_duplicate_basenames(vault: Path) -> list[tuple[str, list[Path]]]:
    """Return (basename, paths) for .md basenames appearing in 2+ locations."""
    by_name: dict[str, list[Path]] = defaultdict(list)
    for path in _iter_notes(vault):
        by_name[path.name].append(path)
    dups = []
    for name in sorted(by_name):
        paths = sorted(by_name[name])
        if len(paths) > 1:
            dups.append((name, paths))
    return dups
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add skills/obsidian/hooks/validate_vault.py skills/obsidian/hooks/test_validate_vault.py
git commit -m "feat: validate-vault hook — detect duplicate basenames

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Hook-shell helpers (`read_cwd`, `_env_from_file`, `resolve_vault`, `in_scope`, `format_report`)

**Files:**
- Modify: `skills/obsidian/hooks/validate_vault.py`
- Test: `skills/obsidian/hooks/test_validate_vault.py`

- [ ] **Step 1: Write the failing test**

Append to `skills/obsidian/hooks/test_validate_vault.py`:

```python
def test_read_cwd_parses_json(tmp_path):
    assert vv.read_cwd('{"cwd": "/c/notes"}') == "/c/notes"


def test_read_cwd_falls_back_to_getcwd_on_garbage(monkeypatch):
    monkeypatch.chdir("/")
    assert vv.read_cwd("not json") == os.getcwd()
    assert vv.read_cwd("") == os.getcwd()


def test_in_scope_accepts_inside_vault_rejects_outside(tmp_path):
    vault = tmp_path / "vault"
    repo = tmp_path / "repo"
    other = tmp_path / "other"
    for d in (vault, repo, other):
        d.mkdir()
    (vault / "daily").mkdir()
    assert vv.in_scope(str(vault), vault, repo) is True            # vault root
    assert vv.in_scope(str(vault / "daily"), vault, repo) is True  # inside vault
    assert vv.in_scope(str(repo / "skills"), vault, repo) is True  # inside skills repo
    assert vv.in_scope(str(other), vault, repo) is False           # outside both


def test_resolve_vault_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT", str(tmp_path))
    monkeypatch.delenv("CLAUDE_ENV_FILE", raising=False)
    assert vv.resolve_vault() == tmp_path


def test_resolve_vault_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT", str(tmp_path / "nope"))
    monkeypatch.delenv("CLAUDE_ENV_FILE", raising=False)
    assert vv.resolve_vault() is None


def test_resolve_vault_from_claude_env_file(tmp_path, monkeypatch):
    vault = tmp_path / "v"
    vault.mkdir()
    env_file = tmp_path / "persist.sh"
    env_file.write_text(f'export OBSIDIAN_VAULT="{vault}"\n')
    monkeypatch.delenv("OBSIDIAN_VAULT", raising=False)
    monkeypatch.setenv("CLAUDE_ENV_FILE", str(env_file))
    assert vv.resolve_vault() == vault


def test_format_report_empty_when_clean(tmp_path):
    assert vv.format_report([], [], tmp_path) == ""


def test_format_report_lists_findings(tmp_path):
    (tmp_path / "people").mkdir()
    empty = tmp_path / "people" / "Empty.md"
    empty.write_text("")
    report = vv.format_report(
        [empty], [("Dup.md", [tmp_path / "misc" / "Dup.md", tmp_path / "engagements" / "Dup.md"])], tmp_path
    )
    assert "people/Empty.md" in report
    assert 'Duplicate basename "Dup.md"' in report
    assert "do NOT auto-edit" in report
```

Note on `test_in_scope...` line for the subdir: replace the ambiguous middle assertion with the exact expected value once you read the implementation below — a path inside the vault IS in scope, so it must be `True`. Use:

```python
    assert vv.in_scope(str(vault / "daily"), vault, repo) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: FAIL — `AttributeError` for `read_cwd` / `in_scope` / `resolve_vault` / `format_report`.

- [ ] **Step 3: Write minimal implementation**

Add to `skills/obsidian/hooks/validate_vault.py` after `find_duplicate_basenames`:

```python
def read_cwd(stdin_text: str) -> str:
    """Extract `cwd` from the hook's stdin JSON; fall back to the process cwd."""
    if stdin_text:
        try:
            data = json.loads(stdin_text)
            cwd = data.get("cwd")
            if isinstance(cwd, str) and cwd:
                return cwd
        except (ValueError, AttributeError):
            pass
    return os.getcwd()


def _env_from_file(var: str) -> str | None:
    """Best-effort read of `export VAR=value` from $CLAUDE_ENV_FILE."""
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if not env_file:
        return None
    try:
        text = Path(env_file).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        m = re.match(rf"\s*export\s+{re.escape(var)}=(.*)", line)
        if m:
            val = m.group(1).strip().strip('"').strip("'")
            if val:
                return val
    return None


def resolve_vault() -> Path | None:
    """Resolve the vault dir from $OBSIDIAN_VAULT (env, then CLAUDE_ENV_FILE)."""
    raw = os.environ.get("OBSIDIAN_VAULT") or _env_from_file("OBSIDIAN_VAULT")
    if not raw:
        return None
    vault = Path(raw)
    return vault if vault.is_dir() else None


def _resolve(path: str) -> str:
    try:
        return str(Path(path).resolve())
    except OSError:
        return path


def in_scope(cwd: str, vault: Path, skills_repo: Path) -> bool:
    """True iff cwd is the vault/skills-repo root or a path inside either."""
    cwd_r = _resolve(cwd)
    for root in (_resolve(str(vault)), _resolve(str(skills_repo))):
        if cwd_r == root or cwd_r.startswith(root + os.sep):
            return True
    return False


def format_report(
    empty: list[Path], dups: list[tuple[str, list[Path]]], vault: Path
) -> str:
    """Render findings as a nudge, or '' when there are none."""
    if not empty and not dups:
        return ""
    lines = ["Vault integrity issues found by validate-vault:"]
    for p in empty:
        rel = p.relative_to(vault)
        lines.append(f"- Empty note (0 bytes): {rel} — an empty note is a dead wikilink target.")
    for name, paths in dups:
        dirs = ", ".join(sorted(str(p.relative_to(vault).parent) for p in paths))
        lines.append(
            f'- Duplicate basename "{name}": {dirs} — wikilinks resolve nondeterministically.'
        )
    lines.append("Mention these to the user and offer to fix; do NOT auto-edit the vault.")
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: PASS (all unit tests green).

- [ ] **Step 5: Commit**

```bash
git add skills/obsidian/hooks/validate_vault.py skills/obsidian/hooks/test_validate_vault.py
git commit -m "feat: validate-vault hook — stdin/vault/scope/report helpers

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: `main` + subprocess integration tests + executable bit

**Files:**
- Modify: `skills/obsidian/hooks/validate_vault.py`
- Test: `skills/obsidian/hooks/test_validate_vault.py`

- [ ] **Step 1: Write the failing test**

Append to `skills/obsidian/hooks/test_validate_vault.py`:

```python
import subprocess

HOOK = os.path.join(os.path.dirname(__file__), "validate_vault.py")


def _run(stdin_text, env_extra):
    env = dict(os.environ)
    env.pop("OBSIDIAN_VAULT", None)
    env.pop("CLAUDE_ENV_FILE", None)
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, HOOK],
        input=stdin_text, capture_output=True, text=True, env=env,
    )


def test_hook_reports_findings_when_cwd_in_vault(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Empty.md").write_text("")
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert "people/Empty.md" in r.stdout


def test_hook_silent_when_cwd_outside_scope(tmp_path):
    (tmp_path / "people").mkdir()
    (tmp_path / "people" / "Empty.md").write_text("")
    outside = tmp_path.parent
    r = _run(f'{{"cwd": "{outside}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert r.stdout == ""


def test_hook_silent_when_clean(tmp_path):
    (tmp_path / "misc").mkdir()
    (tmp_path / "misc" / "Fine.md").write_text("ok\n")
    r = _run(f'{{"cwd": "{tmp_path}"}}', {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0
    assert r.stdout == ""


def test_hook_exit_zero_on_malformed_stdin(tmp_path):
    r = _run("not json at all", {"OBSIDIAN_VAULT": str(tmp_path)})
    assert r.returncode == 0


def test_hook_exit_zero_when_vault_unset(tmp_path):
    r = _run(f'{{"cwd": "{tmp_path}"}}', {})
    assert r.returncode == 0
    assert r.stdout == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: FAIL — the script has no `main`/`__main__`, so it produces no output and `test_hook_reports_findings_when_cwd_in_vault` fails on the `assert "people/Empty.md" in r.stdout`.

- [ ] **Step 3: Write minimal implementation**

Add to the end of `skills/obsidian/hooks/validate_vault.py`:

```python
def main() -> int:
    try:
        stdin_text = sys.stdin.read()
    except Exception:
        stdin_text = ""
    try:
        vault = resolve_vault()
        if vault is None:
            return 0
        skills_repo = Path(__file__).resolve().parents[3]
        if not in_scope(read_cwd(stdin_text), vault, skills_repo):
            return 0
        report = format_report(
            find_empty_notes(vault), find_duplicate_basenames(vault), vault
        )
        if report:
            print(report)
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py -v`
Expected: PASS (all unit + integration tests green).

- [ ] **Step 5: Make the hook executable and record the bit in git**

Run:
```bash
chmod +x skills/obsidian/hooks/validate_vault.py
git update-index --add --chmod=+x skills/obsidian/hooks/validate_vault.py
```
(Per repo history — committed scripts silently lose `+x` unless the mode is recorded explicitly.)

- [ ] **Step 6: Commit**

```bash
git add skills/obsidian/hooks/validate_vault.py skills/obsidian/hooks/test_validate_vault.py
git commit -m "feat: validate-vault hook — main entrypoint + subprocess contract tests

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Register the hook, document it, verify on the real vault

**Files:**
- Modify: `~/.claude/settings.json`
- Modify: `README.md`

- [ ] **Step 1: Register the hook in settings.json**

Use the `update-config` skill to add a second `command` hook to the existing `SessionStart` matcher (`startup|resume|clear`), so the array becomes:

```json
"SessionStart": [
  {
    "matcher": "startup|resume|clear",
    "hooks": [
      { "type": "command", "command": "$HOME/.claude/skills/decant/hooks/undecanted-notes.sh" },
      { "type": "command", "command": "$HOME/.claude/skills/obsidian/hooks/validate_vault.py" }
    ]
  }
]
```

- [ ] **Step 2: Verify the script runs standalone against the real vault**

Run (simulating the hook invocation):
```bash
echo "{\"cwd\": \"$OBSIDIAN_VAULT\"}" | "$HOME/.claude/skills/obsidian/hooks/validate_vault.py"
```
Expected: a nudge listing **`people/Mike Nguyen 1.md`** (empty note) and the **`Microsoft Practice Catch-up.md`** duplicate (engagements/ + misc/), then exit 0. This is the "it works for real" checkpoint.

- [ ] **Step 3: Verify it stays silent outside scope**

Run:
```bash
echo '{"cwd": "/tmp"}' | "$HOME/.claude/skills/obsidian/hooks/validate_vault.py"; echo "exit=$?"
```
Expected: no output, `exit=0`.

- [ ] **Step 4: Document the hook in the repo README**

Add to `README.md` (near the existing hooks/setup section) a subsection:

```markdown
### Vault-validate hook (SessionStart)

`skills/obsidian/hooks/validate_vault.py` runs at session start and nudges about
vault integrity defects (empty notes, duplicate basenames). Report-only — it never
edits the vault, and always exits 0. Supersedes the old vault-root `validate.py`.

Install: add to the `SessionStart` hooks in `~/.claude/settings.json`:

    { "type": "command", "command": "$HOME/.claude/skills/obsidian/hooks/validate_vault.py" }

Run the tests with `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py`.
```

- [ ] **Step 5: Commit the documentation**

```bash
git add README.md
git commit -m "docs: document the validate-vault SessionStart hook

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Definition of done (Increment 1)

- `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py` is green.
- The hook, run against the real vault, flags `Mike Nguyen 1.md` and the `Microsoft Practice Catch-up.md` duplicate, and is silent outside the vault/skills-repo.
- The hook is registered in `~/.claude/settings.json` and documented in `README.md`.
- The hook never mutates the vault and always exits 0.

Fixing the two flagged defects, and Increments 2–4 (frontmatter/discovery checks, freshness nudges, warnings + `--fix`), are out of scope for this plan — each is a separate ship per the spec.
