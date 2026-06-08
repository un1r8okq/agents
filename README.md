# Agents files

This repository contains my Claude Code skills and instructions (`AGENTS.md`). It's designed to be mounted into a Docker Sandbox alongside the project I'm working on.

## Setup

Create a sandbox with the `my-sbx-kit/` mixin:

```bash
sbx create claude --kit ./my-sbx-kit/ c:\dev\my-project c:\dev\agents
```

This mounts both directories into the sandbox (Windows `c:\dev\…` paths land at `/c/dev/…` inside) and runs the kit's startup commands:

- `mkdir /home/agent/.claude` — create the target dir; fails fast if it already exists (the sandbox is expected to be fresh)
- `ln -s /c/dev/agents/skills /home/agent/.claude/skills` — my skills are auto-discovered
- `ln -s /c/dev/agents/AGENTS.md /home/agent/.claude/CLAUDE.md` — Claude Code picks up my instructions
- `claude plugin install superpowers@claude-plugins-official` — superpowers skills available
- `apt-get install python3-icalendar python3-yaml` — deps for the daily-schedule hook
- `jq` patch to `/home/agent/.claude/settings.json` adding the `SessionStart` hook

## Hooks

### Refresh daily note schedule on session start

A `SessionStart` hook runs `/c/dev/agents/scripts/update-daily-schedule.py`, which fetches today's events from Google Calendar's secret iCal URL and inserts/replaces a `## Schedule` table at the top of `$OBSIDIAN_VAULT/daily/YYYY-MM-DD.md`. Wikilinks known entities (people, orgs, glossary, engagements) in event titles and attendees. Idempotent; exits 0 on any failure so a flaky calendar can never block session start.

**Workaround note:** This setup uses Google Calendar's secret iCal URL with `sbx secret set-custom` because my Google Workspace admin currently has third-party app access disabled (blocking the Google Calendar MCP server). When that's re-enabled, this should be replaced with a skill that uses the GCal MCP — no script, no secrets, no apt installs.

**One-time host setup** (per machine, before first `sbx create`):
1. In Google Calendar → Settings → My calendars → your calendar → "Integrate calendar" → copy the "Secret address in iCal format".
2. Strip the `https://calendar.google.com/calendar/ical/` prefix; the remainder (e.g. `<email>/private-<TOKEN>/basic.ics`) is the value to inject.
3. Register it as an sbx custom secret bound to `calendar.google.com`:
    ```bash
    sbx secret set-custom -g --host calendar.google.com --env SECRET_ICAL_SUFFIX --value '<suffix>'
    ```
   The proxy substitutes the placeholder `SECRET_ICAL_SUFFIX` in outbound requests to `calendar.google.com` with the real suffix value; the sandbox never sees it.
4. `OBSIDIAN_VAULT` must be exported in the sandbox shell (already set via your sbx env config).

**Manual run**: `/c/dev/agents/scripts/update-daily-schedule.py` — useful if a meeting moves and you want a fresh schedule mid-session.

**Disable**: edit `/home/agent/.claude/settings.json` to remove the hook block, or run `/hooks` in Claude Code and toggle it off.

### Vault-validate hook (SessionStart)

`skills/obsidian/hooks/validate_vault.py` runs at session start and nudges about
vault integrity defects (empty notes, duplicate basenames). Report-only — it never
edits the vault, and always exits 0. Supersedes the old vault-root `validate.py`.

Install: add to the `SessionStart` hooks in `~/.claude/settings.json`:

    { "type": "command", "command": "$HOME/.claude/skills/obsidian/hooks/validate_vault.py" }

Run the tests with `python3 -m pytest skills/obsidian/hooks/test_validate_vault.py`.
