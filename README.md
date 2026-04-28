# Agents files
This repository contains `AGENTS.md` and a collection of skills that I use day-to-day. Its content should to live at `~/.agents` on your computer.

## Setup
Setup symbolic links for harnesses not following the open skills spec to discover `AGENTS.md`:

```bash
# Claude Code
ln -s ~/.agents/AGENTS.md ~/.claude/CLAUDE.md
# GitHub Copilot CLI
ln -s ~/.agents/AGENTS.md ~/.copilot/copilot-instructions.md
# Gemini CLI
ln -s ~/.agents/AGENTS.md ~/.gemini/GEMINI.md
```

## Harness permissions
For each harness, allowlist trusted local directories (e.g. the Obsidian vault at `$OBSIDIAN_VAULT`) so agents can read them without per-call permission prompts. Skip this and you'll get a prompt every `Read`, `Glob`, `Grep`, `ls`, `find`, etc. against the vault.

### Claude Code
Add to `~/.claude/settings.json` (substitute your actual vault path and user home path — permission strings are literal, env vars don't expand):
```json
{
  "permissions": {
    "allow": [
      "Read(/home/user/.agents/**)",
      "Grep(/home/user/.agents/**)",
      "Glob(/home/user/.agents/**)",
      "Read(/home/user/.claude/skills/**)",
      "Grep(/home/user/.claude/skills/**)",
      "Glob(/home/user/.claude/skills/**)",
      "Read(/absolute/path/to/vault/**)",
      "Glob(/absolute/path/to/vault/**)",
      "Grep(/absolute/path/to/vault/**)",
      "Bash(ls /absolute/path/to/vault*)",
      "Bash(ls $OBSIDIAN_VAULT*)",
      "Bash(ls \"$OBSIDIAN_VAULT\"*)",
      "Bash(find /absolute/path/to/vault*)",
      "Bash(cat /absolute/path/to/vault*)",
      "Bash(head /absolute/path/to/vault*)",
      "Bash(tail /absolute/path/to/vault*)",
      "Bash(echo *)"
    ]
  }
}
```
Caveats:
- Bash rules support trailing-wildcard prefix matching only, so path-scoping works when the vault path is the *first argument* (`ls`, `find`, `cat`, etc.) but not for `grep "pattern" /path` — prefer the built-in Grep tool, which is path-scoped cleanly.
- Include both `$OBSIDIAN_VAULT` and `"$OBSIDIAN_VAULT"` forms for Bash; the tool sees the raw (unexpanded) command string.
- `Bash(echo *)` is safe to allow broadly — echo is pure stdout, no side effects — and it comes up constantly in diagnostic/setup commands.
- If many read-only Bash calls still prompt in practice, run `/fewer-permission-prompts` — it scans your transcripts and proposes a tighter allowlist based on actual usage.

### Other harnesses
GitHub Copilot CLI, Gemini CLI, and others have different permission models. Configure the equivalent allowlist when setting each up — consult their docs.

## Hooks

Hooks are harness-specific automations that run at lifecycle events (session start, before/after tool calls, etc.). They live in the harness's settings file, but the scripts they invoke live under `~/.agents/scripts/` so they're portable across machines.

### Claude Code: refresh daily note schedule on session start

A `SessionStart` hook in `~/.claude/settings.json` runs `~/.agents/scripts/update-daily-schedule.py`, which:

- Calls `gcalcli agenda --details location --tsv --nodeclined` for today.
- Drops Working Location all-day events ("Home", "Office", "WFH", etc.).
- Wikilinks people, orgs, glossary terms, and engagements found in event titles. Matching is case-insensitive and uses each entity's filename plus any `aliases:` list in its frontmatter (e.g. `BB` → `[[Barkingburg|BB]]`, `Ryder` → `[[me|Ryder]]`). Aliases shorter than 2 characters are ignored to prevent pathological matches.
- Inserts/replaces a `## Schedule` table at the top of `$OBSIDIAN_VAULT/daily/YYYY-MM-DD.md` (creating the file from `daily/template.md` if it doesn't exist). Columns: Time, Description, Location — the Location column is omitted when the daily note's frontmatter has `location: home`.
- Idempotent — safe to run repeatedly.
- Exits 0 on any failure so a flaky calendar can never block session start.

**Prerequisites**:
- `gcalcli` installed and authenticated (`gcalcli list` should print your calendars).
- `$OBSIDIAN_VAULT` exported in the shell that launches Claude Code.
- `python3` on `PATH` with `PyYAML` available (used to parse vault frontmatter for aliases). Optional — without it, only canonical filenames are linked, no aliases.

**Settings entry**:
```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/home/<user>/.agents/scripts/update-daily-schedule.py",
            "timeout": 30,
            "statusMessage": "Refreshing daily note schedule…"
          }
        ]
      }
    ]
  }
}
```

**Disable**: remove the hook block from `~/.claude/settings.json`, or run `/hooks` in Claude Code and toggle it off.

**Manual run**: `~/.agents/scripts/update-daily-schedule.py` — useful if a meeting moves and you want a fresh schedule mid-session.
