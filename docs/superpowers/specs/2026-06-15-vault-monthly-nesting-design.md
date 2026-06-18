# Vault monthly nesting + processing inbox — design

**Date:** 2026-06-15
**Status:** Draft for review

## Problem

The Obsidian vault's `daily/`, `daily/detail/`, and `daily/transcripts/` directories are
flat and large (≈48 daily notes, 143 detail notes, 102 transcripts). In the Obsidian file
explorer this causes three concrete pains:

1. No clean target to **drag/drop a raw transcript** into — the folder is buried under
   hundreds of files.
2. Hard to **find a specific detail note** in a flat list of 143.
3. Subfolders (`detail/`, `transcripts/`) get **buried** beneath the daily `.md` files, so
   even finding a folder is slow.

A flat folder cannot be collapsed, so the only structural fix for (2) and (3) is nesting
into collapsible subfolders. (1) is best solved by a dedicated, near-empty drop zone.

## Goals

- Collapsible monthly subfolders for all dated notes, so each explorer list is short.
- One stable, easy-to-find drop target for anything awaiting processing.
- **Uniform** structure — every dated note lives in a `YYYY-MM/` folder, no flat/nested
  split to remember.
- No broken wikilinks: `[[YYYY-MM-DD]]` and detail/transcript links keep resolving.
- No silent tooling breakage: every path-coupled script/skill updated and tested.

## Non-goals

- No change to filenames (only their parent folder changes).
- No view-layer plugins (Dataview/Calendar) — they don't give a drop target or surface
  folders, which are the actual pains.
- No yearly granularity — at ≈24 daily notes/month, monthly is the right grain.

## Key facts that shape the design

- **Obsidian resolves `[[link]]` by basename, not path.** Nesting a note into a subfolder
  does not break inbound wikilinks, provided basenames stay globally unique.
- **The vault is NOT a git repository.** Migration uses plain `mv` and needs its own safety
  net (backup + dry-run + count verification) — there is no `git mv` and no `git` undo.
- **All tooling lives in the one `/c/dev/agents` git repo.** `scripts/` is tracked directly;
  `~/.claude/skills` is a symlink to `/c/dev/agents/skills/`. So every code change is one
  atomic, reviewable commit, and the live hooks/skills pick it up once merged to `main`.
- **Who creates each note type** (determines what the user touches by hand):
  - Daily notes → auto-created by `scripts/update-daily-schedule.py` (SessionStart hook).
  - Detail notes → auto-created by `decant` / `transcript` / `slack-thread` skills.
  - Raw transcripts → the only thing dragged in by hand.

## Design

### Directory shape

```
daily/
  2026-04/2026-04-13.md ...                  ← daily notes, nested by month
  2026-05/2026-05-01.md ...
  detail/2026-04/2026-04-13-topic.md ...     ← detail notes, nested by month
  detail/2026-05/...
  transcripts/2026-05/2026-05-18-...-transcript.md ...  ← processed transcripts
  template.md                                ← stays flat (not dated)
inbox/                                       ← NEW drop zone (vault root)
```

- `inbox/` at **vault root** sorts to the top of the explorer, stays near-empty, and is the
  single place to drop anything to be processed (raw transcripts, screenshots, exports).
- The relevant skill reads the dropped file, produces the proper note nested in its month
  folder, and removes the raw file from `inbox/`.
- `template.md` and any other non-dated files stay at the `daily/` root.

### Month derivation

The `YYYY-MM` folder is always the first 7 characters of the note's date-prefixed filename
(`2026-05-18-...` → `2026-05`). Daily notes use the full stem (`2026-05-18.md` → `2026-05`).

### Tooling changes (one-time)

| Touchpoint | Change |
|---|---|
| `scripts/update-daily-schedule.py` | Create/write today's note at `daily/<YYYY-MM>/<date>.md`; `mkdir` the month folder. `template.md` stays at `daily/` root. |
| `skills/decant/hooks/undecanted-notes.sh` | Scan `daily/<YYYY-MM>/` month folders (one level deep), not just flat `daily/`. |
| `skills/obsidian/hooks/validate_vault.py` | `_recent_daily_files` and `find_stale_context` daily globs become month-folder aware (`[0-9][0-9][0-9][0-9]-[0-9][0-9]/<date>.md`); `inbox/` excluded from frontmatter/empty-note/description checks. `rglob`-based checks already recurse and are unchanged. |
| `skills/transcript/SKILL.md` | Auto-discover dropped files from `inbox/`; write detail to `daily/detail/<YYYY-MM>/`, processed transcript to `daily/transcripts/<YYYY-MM>/`. |
| `skills/decant/SKILL.md`, `skills/slack-thread/SKILL.md`, `skills/obsidian/SKILL.md` | Path templates and structure table gain the `/<YYYY-MM>/` segment; document `inbox/`. |

`validate_vault.py`'s `_requires_description` keys on `parts[:2] == ("daily", "detail")`,
which still holds for `daily/detail/<YYYY-MM>/x.md` — unchanged. Its duplicate-basename
check (`rglob`) actively protects the basename-uniqueness invariant during migration.

### Migration (one-shot script, vault is not git)

`scripts/migrate-daily-nesting.py` (Python, matching the project), with safety appropriate
to a non-git tree:

1. **Backup**: archive the entire `daily/` tree to a timestamped tarball **outside** the
   vault (e.g. `<vault-parent>/vault-daily-bak-YYYY-MM-DD.tar.gz`) before any move. It must
   be outside the indexed vault — an in-vault copy would duplicate every basename, breaking
   Obsidian link resolution and tripping the duplicate-basename check.
2. **Dry-run** (`--dry-run`, default on): print every planned `src → dst` move; make no
   changes. Require an explicit `--apply` to move.
3. **Move**: for each dated `.md` under `daily/`, `daily/detail/`, `daily/transcripts/`,
   `mkdir -p` the `YYYY-MM/` folder and `mv` the file in. Skip `template.md` and already-
   nested files (idempotent / re-runnable).
4. **Verify**: assert in-count == out-count (≈293) and zero files left at the flat roots
   (excluding `template.md`); print a summary. Abort/loud-fail on mismatch.

Files whose names lack a parseable `YYYY-MM-DD` prefix are reported and left in place, not
guessed.

## Testing

- Extend `skills/decant/hooks/test-undecanted-notes.sh` to place notes in month subfolders
  and assert the hook still finds recent undecanted notes.
- Extend `skills/obsidian/hooks/test_validate_vault.py` for: month-nested daily discovery in
  `_recent_daily_files`/`find_stale_context`; `inbox/` exclusion; `daily/detail/<YYYY-MM>/`
  still requiring `description:`.
- Migration script: unit/dry-run test against a temp fixture vault asserting correct
  src→dst mapping, idempotency, and count verification.

## Risks & mitigations

- **Basename collision** (two notes same filename in different months) → would break
  Obsidian resolution. Mitigation: migration preserves existing unique filenames; the
  validate_vault duplicate-basename check flags any collision.
- **No git undo on the vault** → backup copy + dry-run default + count verification.
- **Worktree skills copy ≠ live skills** → live `~/.claude/skills` symlink points at the
  canonical `/c/dev/agents/skills/`; changes take effect only after merge to `main`. Develop
  and test in the worktree; merge to activate.
- **Obsidian core Daily Notes plugin** (if used) creates new notes flat — out of scope here;
  the schedule hook is the note creator. Note for follow-up if the plugin is also in use.

## Rollout

1. Implement + test tooling changes in the worktree (all in the `/c/dev/agents` repo).
2. Run the migration `--dry-run`, review, back up, `--apply`, verify counts.
3. Merge worktree → `main` so the live hooks/skills pick up the new paths.
