#!/usr/bin/env python3
"""SessionStart hook — validate vault integrity and nudge.

Scans $OBSIDIAN_VAULT for integrity defects (empty notes, ambiguous wikilinks)
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


def find_ambiguous_wikilinks(vault: Path) -> list[tuple[Path, str, list[Path]]]:
    """Return (note, target, candidates) for bare wikilinks to an ambiguous basename.

    A bare ``[[context]]`` resolves nondeterministically when 2+ notes share that
    stem (e.g. each engagement's companion ``context.md``). This is the precise
    defect behind duplicate basenames: duplicate companion files are sanctioned
    by the convention, so a duplicate is only a problem when a *bare* link
    actually points at the shared name. Path-qualified links (``[[DSO2/context]]``)
    and links to a unique stem are fine and never flagged. Findings are
    de-duplicated per (note, target), so one note linking ``[[context]]`` five
    times yields a single finding.
    """
    by_stem: dict[str, list[Path]] = defaultdict(list)
    for path in _iter_notes(vault):
        by_stem[path.stem].append(path)
    found = []
    for path in sorted(_iter_notes(vault)):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for target in sorted(_wikilink_targets(text)):
            if "/" in target:
                continue  # path-qualified — already disambiguated
            candidates = by_stem.get(target, [])
            if len(candidates) > 1:
                found.append((path, target, sorted(candidates)))
    return found


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


def find_invalid_source(vault: Path) -> list[tuple[Path, str]]:
    """Return (path, reason) for notes whose optional `source:` is present but malformed.

    Per SKILL.md "Source", `source:` must be a bare http(s) URL — not a wikilink
    (a URL is not a vault entity) and not a bare vault path. Absent/empty source
    is fine; the field is optional everywhere.
    """
    found = []
    for path in sorted(_iter_notes(vault)):
        raw = _read_frontmatter(path).get("source", "")
        if "[[" in raw:
            found.append((path, "contains a wikilink — source must be a plain URL"))
            continue
        value = _strip_quotes(raw)
        if not value:
            continue
        if not value.startswith(("http://", "https://")):
            found.append((path, "not a URL — source must be a plain http(s) URL; for local-only documents, omit source: and record provenance in the body"))
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


def _daily_note_files(vault: Path) -> Iterator[Path]:
    """Yield daily-note files in either layout: flat (daily/YYYY-MM-DD.md) or
    month-nested (daily/YYYY-MM/YYYY-MM-DD.md). The month-folder glob never
    matches daily/detail/ or daily/transcripts/, so those stay excluded."""
    daily = vault / "daily"
    yield from daily.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md")
    yield from daily.glob(
        "[0-9][0-9][0-9][0-9]-[0-9][0-9]/[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md"
    )


def _recent_daily_files(vault: Path, days: int, today: date) -> list[Path]:
    """Return daily-note files whose date is in [today-days, today].

    Handles both flat (daily/YYYY-MM-DD.md) and month-nested
    (daily/YYYY-MM/YYYY-MM-DD.md) layouts via _daily_note_files.
    """
    cutoff = today - timedelta(days=days)
    out = []
    for path in _daily_note_files(vault):
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


def find_stale_person_notes(vault: Path, today: date, days: int = 14) -> list[str]:
    """Return person stems discussed in a recent daily more recently than their newest dated entry.

    Relies on the full-name wikilink convention: a daily must link the person by
    their note stem (`[[Gagan Dhaliwal]]` or `[[Gagan Dhaliwal|Gagan]]`); a bare
    alias `[[Gagan]]` with no matching people/ file is not counted.
    """
    people_dir = vault / "people"
    if not people_dir.is_dir():
        return []
    stems = {p.stem for p in people_dir.glob("*.md")}
    if not stems:
        return []
    latest_mention: dict[str, date] = {}
    for daily in _recent_daily_files(vault, days, today):
        d = _daily_date(daily)
        if d is None:  # _recent_daily_files already filters these out; defensive
            continue
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


def find_stale_context(vault: Path, today: date) -> list[tuple[str, str, str]]:
    """Return (engagement, last_refreshed, trigger_date) where context.md lags a newer decant that mentions it."""
    eng_dir = vault / "engagements"
    if not eng_dir.is_dir():
        return []
    out = []
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
        for daily in _daily_note_files(vault):
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
    ambiguous: list[tuple[Path, str, list[Path]]],
    vault: Path,
    *,
    missing_desc: list[Path] = (),
    bad_keys: list[tuple[Path, list[str]]] = (),
    desc_links: list[Path] = (),
    bad_sources: list[tuple[Path, str]] = (),
    missing_keys: list[tuple[Path, list[str]]] = (),
    bad_enums: list[tuple[Path, str, str]] = (),
    stale_people: list[str] = (),
    stale_context: list[tuple[str, str, str]] = (),
) -> str:
    """Render findings as a nudge, or '' when there are none."""
    if not (empty or ambiguous or missing_desc or bad_keys or desc_links or bad_sources or missing_keys or bad_enums or stale_people or stale_context):
        return ""
    lines = ["Vault integrity issues found by validate-vault:"]
    for p in empty:
        rel = p.relative_to(vault)
        lines.append(f"- Empty note (no content): {rel} — a blank note is a dead wikilink target.")
    for note, target, candidates in ambiguous:
        rel = note.relative_to(vault)
        cands = ", ".join(str(c.relative_to(vault)) for c in candidates)
        lines.append(
            f"- Ambiguous wikilink [[{target}]] in {rel} — basename matches {len(candidates)} notes "
            f"({cands}); disambiguate with a path-prefix wikilink, e.g. [[<dir>/{target}]]."
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
    for p, reason in bad_sources:
        rel = p.relative_to(vault)
        lines.append(f"- Invalid source: {rel} — {reason}.")
    for p, keys in missing_keys:
        rel = p.relative_to(vault)
        lines.append(
            f"- Missing required frontmatter: {rel} ({', '.join(sorted(keys))}) — required for this directory."
        )
    for p, field, value in bad_enums:
        rel = p.relative_to(vault)
        allowed = ", ".join(sorted(ENUM_FIELDS[field]))
        lines.append(f'- Invalid {field} value: {rel} ("{value}") — must be one of {allowed}.')
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
        today = date.today()
        report = format_report(
            _timed("find_empty_notes", find_empty_notes, vault),
            _timed("find_ambiguous_wikilinks", find_ambiguous_wikilinks, vault),
            vault,
            missing_desc=_timed("find_missing_description", find_missing_description, vault),
            bad_keys=_timed("find_uppercase_frontmatter_keys", find_uppercase_frontmatter_keys, vault),
            desc_links=_timed("find_wikilinks_in_description", find_wikilinks_in_description, vault),
            bad_sources=_timed("find_invalid_source", find_invalid_source, vault),
            missing_keys=_timed("find_missing_required_keys", find_missing_required_keys, vault),
            bad_enums=_timed("find_invalid_enum_values", find_invalid_enum_values, vault),
            stale_people=_timed("find_stale_person_notes", find_stale_person_notes, vault, today),
            stale_context=_timed("find_stale_context", find_stale_context, vault, today),
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
