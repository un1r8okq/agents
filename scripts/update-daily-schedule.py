#!/usr/bin/env python3
"""Refresh today's daily note with a `## Schedule` table from gcalcli.

Idempotent: replaces any existing `## Schedule` block. Creates the daily note
from the template if it doesn't exist. Triggered by Claude Code's SessionStart
hook; can also be run manually.

Wikilinks people, orgs, glossary terms, and engagements in event titles using
each entity's filename and any `aliases:` list in its frontmatter. The user's
own `me.md` aliases produce `[[me|...]]` links.

Exit codes:
  0  always (any failure is logged to stderr; the hook never blocks startup).
"""
from __future__ import annotations

import datetime
import os
import re
import shutil
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

VAULT = os.environ.get("OBSIDIAN_VAULT")
if not VAULT:
    print("update-daily-schedule: OBSIDIAN_VAULT not set; skipping.", file=sys.stderr)
    sys.exit(0)

VAULT_PATH = Path(VAULT)
ENTITY_DIRS = ["people", "orgs", "glossary", "engagements"]
WORKING_LOCATION_TITLES = {"home", "office", "working from home", "in office", "remote", "wfh", "wfo"}
MIN_ALIAS_LEN = 2  # avoid pathological one-letter matches like "I"

today = datetime.date.today()
daily_dir = VAULT_PATH / "daily"
daily_path = daily_dir / f"{today.isoformat()}.md"
template_path = daily_dir / "template.md"


def fetch_events() -> list[dict]:
    try:
        from gcalcli.gcal import GoogleCalendarInterface
        from dateutil.tz import tzlocal
    except ImportError as e:
        print(f"update-daily-schedule: gcalcli import failed; skipping. ({e})", file=sys.stderr)
        return []

    try:
        gcal = GoogleCalendarInterface(
            refresh_cache=False, use_cache=True,
            ignore_calendars=[], military=True,
        )
    except Exception as e:
        print(f"update-daily-schedule: gcalcli init failed; skipping. ({e})", file=sys.stderr)
        return []

    tz = tzlocal()
    start = datetime.datetime.combine(today, datetime.time.min, tzinfo=tz)
    end = start + datetime.timedelta(days=1)

    seen_ids: set[str] = set()
    out = []
    for cal in gcal.cals:
        try:
            for ev in gcal._GetAllEvents(cal, start, end, None):
                ev_id = ev.get("id", "")
                if ev_id in seen_ids:
                    continue
                seen_ids.add(ev_id)

                attendees = ev.get("attendees", [])
                self_att = next((a for a in attendees if a.get("self")), None)
                if self_att and self_att.get("responseStatus") == "declined":
                    continue

                title = ev.get("summary", "").strip()
                is_all_day = (
                    "date" in ev.get("start", {})
                    and "dateTime" not in ev.get("start", {})
                )
                if is_all_day and title.lower() in WORKING_LOCATION_TITLES:
                    continue

                s = ev.get("s")
                e_time = ev.get("e")

                out.append({
                    "start_time": s.strftime("%H:%M") if s and not is_all_day else "",
                    "end_time": e_time.strftime("%H:%M") if e_time and not is_all_day else "",
                    "title": title,
                    "location": ev.get("location", "").strip(),
                    "attendees": [
                        a for a in attendees
                        if not a.get("self")
                        and not a.get("resource")
                        and a.get("responseStatus") != "declined"
                    ],
                })
        except Exception as e:
            print(f"update-daily-schedule: calendar error: {e}", file=sys.stderr)

    out.sort(key=lambda r: (r["start_time"] == "", r["start_time"]))
    return out


def parse_frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    fm_text = text[4:end]
    if yaml is None:
        return {}
    try:
        data = yaml.safe_load(fm_text)
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return {}


def load_entities() -> list[tuple[str, str]]:
    """Return (target, display) tuples for every entity + alias.

    `target` is the wikilink target (filename without `.md`, or `me` for the user).
    `display` is the text to scan for in event titles.
    """
    out: list[tuple[str, str]] = []
    for subdir in ENTITY_DIRS:
        d = VAULT_PATH / subdir
        if not d.is_dir():
            continue
        for f in d.glob("*.md"):
            stem = f.stem
            target = "me" if subdir == "people" and stem == "me" else stem
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            fm = parse_frontmatter(content)
            displays = {stem}  # always match the canonical filename
            aliases = fm.get("aliases") or []
            if isinstance(aliases, list):
                for a in aliases:
                    if isinstance(a, str) and len(a) >= MIN_ALIAS_LEN:
                        displays.add(a)
            for d_text in displays:
                out.append((target, d_text))
    return out


def build_wikilinker(entities: list[tuple[str, str]]):
    """Compile a single longest-first, case-insensitive regex over all displays.

    Matching is case-insensitive but the source text's casing is preserved in
    the rendered link (e.g. `marshall` → `[[Marshall|marshall]]`).
    """
    if not entities:
        return lambda text: text
    sorted_entries = sorted(entities, key=lambda e: -len(e[1]))
    target_by_lower: dict[str, str] = {}
    seen_lower: set[str] = set()
    alts = []
    for target, display in sorted_entries:
        key = display.lower()
        target_by_lower.setdefault(key, target)
        if key in seen_lower:
            continue
        seen_lower.add(key)
        alts.append(re.escape(display))
    pattern = re.compile(r"\b(" + "|".join(alts) + r")\b", re.IGNORECASE)

    def linkify(text: str) -> str:
        def repl(m: re.Match) -> str:
            matched = m.group(1)
            tgt = target_by_lower[matched.lower()]
            return f"[[{tgt}]]" if tgt == matched else f"[[{tgt}|{matched}]]"
        return pattern.sub(repl, text)

    return linkify


def cell(text: str) -> str:
    return text.replace("|", r"\|")


def _attendee_name(att: dict) -> str:
    name = (att.get("displayName") or "").strip()
    if name:
        return name
    local = att.get("email", "").split("@")[0]
    cleaned = re.sub(r"\d+$", "", local).replace(".", " ").replace("_", " ")
    return cleaned.strip().title()


def resolve_attendees(
    att_list: list[dict],
    entities: list[tuple[str, str]],
    linkify,
) -> str:
    """Deduplicated, wikilinked attendee string.

    Handles people invited via multiple emails (e.g. CP + WW) by:
    1. Entity-name matching via the wikilinker
    2. Surname extraction from abbreviated emails (awaters → waters → Ashleigh Waters)
    3. Filtering the user's own secondary emails (target "me")
    """
    surname_lists: dict[str, list[str]] = {}
    for target, display in entities:
        words = display.split()
        if len(words) >= 2:
            surname_lists.setdefault(words[-1].lower(), []).append(target)
    surname_map = {
        s: targets[0]
        for s, targets in surname_lists.items()
        if len(set(targets)) == 1
    }

    seen: set[str] = set()
    parts: list[str] = []

    for a in att_list:
        name = _attendee_name(a)
        linked = linkify(name)
        target_m = re.match(r"^\[\[([^|\]]+)", linked)

        if target_m:
            key = target_m.group(1).lower()
            if key == "me" or key in seen:
                continue
            seen.add(key)
            parts.append(linked)
            continue

        email = (a.get("email") or "").lower()
        local = email.split("@")[0]
        cleaned = re.sub(r"\d+$", "", local)
        if "." not in cleaned and "_" not in cleaned and len(cleaned) > 2:
            surname_guess = cleaned[1:]
            target = surname_map.get(surname_guess)
            if target:
                key = target.lower()
                if key == "me" or key in seen:
                    continue
                seen.add(key)
                parts.append(linkify(target))
                continue

        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        parts.append(name)

    return ", ".join(parts)


def render_block(
    events: list[dict],
    linkify,
    entities: list[tuple[str, str]],
    include_location: bool,
) -> str:
    if not events:
        return "## Schedule\n\n_No events today._\n"

    rows = []
    for ev in events:
        start = (ev.get("start_time") or "").strip()
        end = (ev.get("end_time") or "").strip()
        title = (ev.get("title") or "").strip()
        location = (ev.get("location") or "").strip()
        time_part = f"{start} - {end}" if start and end else "all-day"
        att_text = resolve_attendees(ev.get("attendees", []), entities, linkify)
        row = [time_part, cell(linkify(title))]
        if include_location:
            row.append(cell(location))
        row.append(cell(att_text))
        rows.append(tuple(row))

    headers = ["Time", "Description"]
    if include_location:
        headers.append("Location")
    headers.append("Invited")
    headers = tuple(headers)
    widths = [len(h) for h in headers]
    for r in rows:
        for i, c in enumerate(r):
            widths[i] = max(widths[i], len(c))

    def fmt(r: tuple[str, ...]) -> str:
        return "| " + " | ".join(c.ljust(widths[i]) for i, c in enumerate(r)) + " |"

    sep = "| " + " | ".join("-" * w for w in widths) + " |"
    lines = ["## Schedule", "", fmt(headers), sep]
    lines.extend(fmt(r) for r in rows)
    return "\n".join(lines) + "\n"


def upsert_schedule(content: str, block: str) -> str:
    """Insert or replace the `## Schedule` block immediately after frontmatter."""
    if content.startswith("---\n"):
        end_fm = content.find("\n---\n", 4)
        if end_fm != -1:
            frontmatter = content[: end_fm + len("\n---\n")]
            body = content[end_fm + len("\n---\n") :]
        else:
            frontmatter, body = "", content
    else:
        frontmatter, body = "", content

    body_lines = body.splitlines()

    start_idx = next(
        (i for i, line in enumerate(body_lines) if line.rstrip() == "## Schedule"),
        None,
    )

    if start_idx is None:
        new_body = block.rstrip("\n") + "\n\n" + body.lstrip("\n")
    else:
        end_idx = len(body_lines)
        for j in range(start_idx + 1, len(body_lines)):
            if body_lines[j].lstrip().startswith("#"):
                end_idx = j
                break
        after = body_lines[end_idx:]
        while after and after[0] == "":
            after = after[1:]
        new_body_lines = (
            body_lines[:start_idx]
            + block.rstrip("\n").splitlines()
            + [""]
            + after
        )
        new_body = "\n".join(new_body_lines)
        if not new_body.endswith("\n"):
            new_body += "\n"

    return frontmatter + new_body


def main() -> int:
    if not daily_dir.exists():
        print(f"update-daily-schedule: {daily_dir} missing; skipping.", file=sys.stderr)
        return 0

    if not daily_path.exists():
        if template_path.exists():
            shutil.copyfile(template_path, daily_path)
        else:
            daily_path.write_text("# Notes\n")

    events = fetch_events()
    entities = load_entities()
    linkify = build_wikilinker(entities)
    original = daily_path.read_text()
    daily_fm = parse_frontmatter(original)
    include_location = str(daily_fm.get("location", "")).strip().lower() != "home"
    block = render_block(events, linkify, entities, include_location)
    updated = upsert_schedule(original, block)

    if updated != original:
        daily_path.write_text(updated)
        print(f"update-daily-schedule: refreshed {daily_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # never block session start
        print(f"update-daily-schedule: unexpected error: {e}", file=sys.stderr)
        sys.exit(0)
