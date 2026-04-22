---
name: obsidian
description: Look up people, organisations, engagements, daily notes, and past context from the user's personal knowledgebase at `$OBSIDIAN_VAULT`. Use proactively whenever the user references someone, a company, or ongoing work that isn't obvious from the current directory — and when adding/updating notes about any of those.
---

Always read `$OBSIDIAN_VAULT/README.md` before doing anything else. It outlines the structure of the notes and principles for working with them.

## Setup & Troubleshooting
If you encounter errors accessing the vault, or if the user asks you to verify the setup, run the setup checker:
`run_shell_command("~/.agents/skills/obsidian/scripts/check_setup.sh")`

If `$OBSIDIAN_VAULT` is not set or the script reports failures, advise the user to:
1. Add `export OBSIDIAN_VAULT="/path/to/your/vault"` to their shell profile (`~/.bashrc` or `~/.zshrc`).
2. Add `"$OBSIDIAN_VAULT"` to `context.includeDirectories` in `~/.gemini/settings.json`.
