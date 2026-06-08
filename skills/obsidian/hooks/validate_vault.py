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
from collections.abc import Iterator
from pathlib import Path


def _iter_notes(vault: Path) -> Iterator[Path]:
    """Yield *.md content files under vault, skipping dot-directories and README.md (conventional per-directory files, not wikilink targets)."""
    for path in vault.rglob("*.md"):
        if any(part.startswith(".") for part in path.relative_to(vault).parts):
            continue
        if path.name.lower() == "readme.md":
            continue
        yield path


DESCRIPTION_REQUIRED_DIRS = ("people", "orgs", "glossary", "misc", "engagements")
# SKILL.md "Required fields per directory" is the source of truth for the above;
# daily/detail/ also requires description: (handled in _requires_description).
# The drift-guard test (test_description_required_dirs_match_skill_md) fails loudly
# if these diverge from that table.


def _read_frontmatter(path: Path) -> dict[str, str]:
    """Parse the leading ---/--- block into top-level key:value pairs.

    Returns {} when there is no opening `---` fence, or when the block is never closed. Only top-level `key: value`
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
            return fm          # closed properly
        m = re.match(r"([A-Za-z0-9_-]+):(.*)", line)
        if m:
            fm[m.group(1)] = m.group(2).strip()
    return {}                  # no closing fence -> treat as no frontmatter


def _requires_description(rel: Path) -> bool:
    """True if a note at this vault-relative path must carry a `description:`."""
    parts = rel.parts
    if parts and parts[0] in DESCRIPTION_REQUIRED_DIRS:
        return True
    if parts[:2] == ("daily", "detail"):
        return True
    return False


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


def find_missing_description(vault: Path) -> list[Path]:
    """Return entity notes (per _requires_description) lacking a non-empty `description:`."""
    found = []
    for path in sorted(_iter_notes(vault)):
        if not _requires_description(path.relative_to(vault)):
            continue
        if not _read_frontmatter(path).get("description", "").strip():
            found.append(path)
    return found


def read_cwd(stdin_text: str) -> str:
    """Extract `cwd` from the hook's stdin JSON; fall back to the process cwd on empty/invalid/non-object input."""
    if stdin_text:
        try:
            data = json.loads(stdin_text)
        except ValueError:
            data = None
        if isinstance(data, dict):
            cwd = data.get("cwd")
            if isinstance(cwd, str) and cwd:
                return cwd
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
            val = m.group(1).strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                val = val[1:-1]
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
        lines.append(f"- Empty note (no content): {rel} — a blank note is a dead wikilink target.")
    for name, paths in dups:
        dirs = ", ".join(sorted(str(p.relative_to(vault).parent) for p in paths))
        lines.append(
            f'- Duplicate basename "{name}": {dirs} — wikilinks resolve nondeterministically.'
        )
    lines.append("Mention these to the user and offer to fix; do NOT auto-edit the vault.")
    return "\n".join(lines)


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
