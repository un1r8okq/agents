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
