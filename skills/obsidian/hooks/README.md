# obsidian hooks

## validate_vault.py

A `SessionStart` hook that checks the Obsidian vault for integrity defects and nudges.

When a Claude Code session starts, the hook scans `$OBSIDIAN_VAULT` for defects (empty notes,
duplicate basenames, wikilinks in `description:` frontmatter, …) and prints a report to stdout.
Claude Code injects that as session context. When the vault is clean it prints a one-line positive
confirmation instead (`validate-vault: vault integrity OK — N notes checked, no issues.`), so a
successful run is visible rather than silent. It stays fully silent only when out of scope or when
no notes were scanned. The hook is **report-only**: it never edits the vault and always exits 0, so
it can never block a session start.

Paths are portable: the vault comes from `$OBSIDIAN_VAULT`. The only required contract is that
`$OBSIDIAN_VAULT` is set (the same contract the `obsidian`/`decant` skills already assume).

### Install

Add to `~/.claude/settings.json` (sits in the same `SessionStart` block as the `decant` nudge):

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          { "type": "command", "command": "$HOME/.claude/skills/decant/hooks/undecanted-notes.sh" },
          { "type": "command", "command": "$HOME/.claude/skills/obsidian/hooks/validate_vault.sh" }
        ]
      }
    ]
  }
}
```

> **Point the hook at the bare `.sh` wrapper, not the `.py` directly — and never at a
> `bash "…"` / `python3 "…"` wrapper.** Two distinct failure modes have bitten this hook:
> 1. A wrapped, multi-token command like `bash "$HOME/…/x.sh"` registers (shows in `/hooks`) but
>    **silently never executes** (CC 2.1.169, 2026-06-09) — only a single bare executable path runs.
> 2. A **bare `.py`** path *also* silently never executes (CC 2.1.170, 2026-06-10): a fresh session
>    fired the sibling bare `.sh` hooks but produced zero hook attachments for `validate_vault.py`,
>    despite it being `+x`, having a valid shebang, and running fine by hand.
>
> A **bare `.sh`** path is the only form observed to fire reliably across versions (the decant hook
> proves it every startup). So `validate_vault.sh` is a thin shim that `exec python3 validate_vault.py`
> (stdin inherited, so the payload JSON passes straight through). Both `.sh` and `.py` must stay `+x`
> (git tracks them `100755`; `core.fileMode=false` here, so set it with `git update-index --chmod=+x`
> if a checkout ever drops it).
>
> `matcher: "startup"` runs it only on a fresh start. Add `resume`/`clear` entries (or the combined
> `"startup|resume|clear"`, which works) if you want it on those too; `compact` is best left out so
> the nudge doesn't re-fire after mid-session auto-compaction.

It **must** live in user-level `~/.claude/settings.json`, not a skills-directory plugin: skills-dir
plugins are gated behind workspace trust (`hasTrustDialogAccepted`) and silently never load in an
untrusted workspace such as a fresh `sbx` sandbox — which is exactly where this hook needs to run.
User-level `settings.json` hooks are not subject to that gate. The tradeoff is that `settings.json`
does not travel with the repo, so a fresh sandbox must provision it at bootstrap.

Earlier versions wrapped the commands as `python3 …` / `bash …` to avoid depending on the exec
bit, and a later version pointed the hook at the bare `.py`. **Do neither** — the wrapped form does
not execute on CC 2.1.169, and the bare `.py` does not execute on CC 2.1.170 (see the note above).
Point the hook at the bare `.sh` wrapper and keep both scripts `+x`.

### Run / debug manually

The hook reads its `cwd` from stdin JSON the way Claude Code invokes it. Run by hand by piping
that JSON in:

```bash
echo "{\"cwd\": \"$OBSIDIAN_VAULT\"}" | python3 skills/obsidian/hooks/validate_vault.py
```

Running it with **no** stdin from an interactive terminal is safe: stdin is a TTY, so the hook
skips the read (it would otherwise block waiting for input) and falls back to the process `cwd`.

Set `VALIDATE_VAULT_DEBUG=1` for diagnostics on **stderr** (stdout stays reserved for the nudge):
the resolved vault, the `cwd`/`in_scope` decision, and per-check finding counts and timings.

```bash
echo "{\"cwd\": \"$OBSIDIAN_VAULT\"}" | VALIDATE_VAULT_DEBUG=1 python3 skills/obsidian/hooks/validate_vault.py
```

### Test

```bash
pytest skills/obsidian/hooks/test_validate_vault.py
```
