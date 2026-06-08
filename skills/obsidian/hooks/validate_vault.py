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
