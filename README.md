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
