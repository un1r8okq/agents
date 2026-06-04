# decant hooks

## undecanted-notes.sh

A `SessionStart` hook that nudges about undecanted past daily notes.

When a Claude Code session starts **inside the Obsidian vault (`$OBSIDIAN_VAULT`) or this
skills repo**, the hook scans `$OBSIDIAN_VAULT/daily` for `YYYY-MM-DD.md` notes from the last
14 days that lack a `# Summary` heading (the marker `/decant` writes), and prints a nudge to
stdout. Claude Code injects that as session context. The hook **offers**; it never runs
`/decant` automatically.

Paths are portable: the vault comes from `$OBSIDIAN_VAULT`, and the skills-repo root is
self-located from the script's own path. The only required contract is that `$OBSIDIAN_VAULT`
is set (the same contract the `decant`/`obsidian` skills already assume).

### Install

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|clear",
        "hooks": [
          { "type": "command", "command": "$HOME/.claude/skills/decant/hooks/undecanted-notes.sh" }
        ]
      }
    ]
  }
}
```

`compact` is intentionally excluded so the nudge does not re-fire after mid-session
auto-compaction. If these skills are ever packaged as a Claude Code plugin, use
`${CLAUDE_PLUGIN_ROOT}/hooks/undecanted-notes.sh` instead.

### Test

```bash
skills/decant/hooks/test-undecanted-notes.sh
```
