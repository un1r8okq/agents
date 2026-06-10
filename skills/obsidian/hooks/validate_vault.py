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
import time
from datetime import date, timedelta
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


ENUM_FIELDS = {
    "status": {"active", "complete"},
    "relationship": {"employer", "client", "partner", "vendor", "organisation"},
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


def find_uppercase_frontmatter_keys(vault: Path) -> list[tuple[Path, list[str]]]:
    """Return (path, bad_keys) for notes whose frontmatter has non-lowercase keys."""
    found = []
    for path in sorted(_iter_notes(vault)):
        bad = [k for k in _read_frontmatter(path) if k != k.lower()]
        if bad:
            found.append((path, bad))
    return found


def find_wikilinks_in_description(vault: Path) -> list[Path]:
    """Return notes whose `description:` frontmatter contains a [[wikilink]] (must be plain prose)."""
    found = []
    for path in sorted(_iter_notes(vault)):
        if "[[" in _read_frontmatter(path).get("description", ""):
            found.append(path)
    return found


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
        target = re.split(r"[|#]", m.group(1), maxsplit=1)[0].strip()
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
    empty: list[Path],
    dups: list[tuple[str, list[Path]]],
    vault: Path,
    *,
    missing_desc: list[Path] = (),
    bad_keys: list[tuple[Path, list[str]]] = (),
    desc_links: list[Path] = (),
    missing_keys: list[tuple[Path, list[str]]] = (),
    bad_enums: list[tuple[Path, str, str]] = (),
) -> str:
    """Render findings as a nudge, or '' when there are none."""
    if not (empty or dups or missing_desc or bad_keys or desc_links or missing_keys or bad_enums):
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
            f"- Non-lowercase frontmatter keys: {rel} ({', '.join(sorted(keys))}) — keys must be lowercase."
        )
    for p in desc_links:
        rel = p.relative_to(vault)
        lines.append(f"- Wikilink in description: {rel} — descriptions must be plain text (no [[...]]).")
    for p, keys in missing_keys:
        rel = p.relative_to(vault)
        lines.append(
            f"- Missing required frontmatter: {rel} ({', '.join(sorted(keys))}) — required for this directory."
        )
    for p, field, value in bad_enums:
        rel = p.relative_to(vault)
        allowed = ", ".join(sorted(ENUM_FIELDS[field]))
        lines.append(f'- Invalid {field} value: {rel} ("{value}") — must be one of {allowed}.')
    lines.append("Mention these to the user and offer to fix; do NOT auto-edit the vault.")
    return "\n".join(lines)


def _debug_enabled() -> bool:
    """True when $VALIDATE_VAULT_DEBUG is set to a non-empty value."""
    return bool(os.environ.get("VALIDATE_VAULT_DEBUG"))


def _debug(msg: str) -> None:
    """Emit a diagnostic line to stderr, gated on $VALIDATE_VAULT_DEBUG.

    stdout is reserved for the SessionStart nudge (injected as context), so all
    debugging goes to stderr and stays silent unless the flag is set.
    """
    if _debug_enabled():
        print(f"[validate-vault] {msg}", file=sys.stderr)


def _read_stdin() -> str:
    """Read the hook's stdin JSON, returning '' without blocking on a TTY.

    The SessionStart hook pipes a JSON payload and closes the stream, so read()
    returns at once. Run manually in a terminal, stdin is a TTY and a bare
    read() would block forever waiting for input — so skip it there and let
    read_cwd() fall back to os.getcwd().
    """
    try:
        if sys.stdin.isatty():
            _debug("stdin: tty — skipping read (falling back to cwd)")
            return ""
        text = sys.stdin.read()
        _debug(f"stdin: read {len(text)} byte(s)")
        return text
    except Exception as exc:  # never let stdin handling break the hook
        _debug(f"stdin: read failed ({exc!r}); falling back to cwd")
        return ""


def _timed(label: str, fn, *args, **kwargs):
    """Run a check, logging its finding count and elapsed time when debugging."""
    if not _debug_enabled():
        return fn(*args, **kwargs)
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000
    try:
        count = len(result)
    except TypeError:
        count = "?"
    _debug(f"{label}: {count} finding(s) in {elapsed_ms:.0f}ms")
    return result


def _ok_message(checked: int) -> str:
    """Positive happy-path confirmation: in-scope, scanned, no findings.

    Returns '' when nothing was scanned (empty/misconfigured vault) — there is
    nothing to affirm, so the hook stays silent rather than print "0 notes".
    """
    if checked <= 0:
        return ""
    noun = "note" if checked == 1 else "notes"
    return f"validate-vault: vault integrity OK — {checked} {noun} checked, no issues."


def main() -> int:
    stdin_text = _read_stdin()
    try:
        vault = resolve_vault()
        if vault is None:
            _debug("OBSIDIAN_VAULT not resolved to a directory — exiting 0")
            return 0
        skills_repo = Path(__file__).resolve().parents[3]
        cwd = read_cwd(stdin_text)
        scoped = in_scope(cwd, vault, skills_repo)
        _debug(f"vault={vault}")
        _debug(f"cwd={cwd} skills_repo={skills_repo} in_scope={scoped}")
        if not scoped:
            _debug("cwd outside vault/skills-repo — exiting 0 (silent)")
            return 0
        start = time.perf_counter()
        report = format_report(
            _timed("find_empty_notes", find_empty_notes, vault),
            _timed("find_duplicate_basenames", find_duplicate_basenames, vault),
            vault,
            missing_desc=_timed("find_missing_description", find_missing_description, vault),
            bad_keys=_timed("find_uppercase_frontmatter_keys", find_uppercase_frontmatter_keys, vault),
            desc_links=_timed("find_wikilinks_in_description", find_wikilinks_in_description, vault),
            missing_keys=_timed("find_missing_required_keys", find_missing_required_keys, vault),
            bad_enums=_timed("find_invalid_enum_values", find_invalid_enum_values, vault),
        )
        _debug(
            f"scan complete in {(time.perf_counter() - start) * 1000:.0f}ms — "
            f"report {'non-empty' if report else 'empty'}"
        )
        # Findings -> the report; clean & in-scope -> positive confirmation (note
        # count evaluated only on the clean path, via short-circuit).
        out = report or _ok_message(sum(1 for _ in _iter_notes(vault)))
        if out:
            print(out)
    except Exception as exc:
        _debug(f"exception suppressed (exit 0): {exc!r}")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
