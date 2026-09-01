---
name: refresh-person
description: Refresh the `# Summary`, (optional) `# Stated views`, and `description:` frontmatter on a vault person note (`$OBSIDIAN_VAULT/people/<Name>.md`) so the meeting-prep view stays current with `# My notes`. Use when the user asks to regenerate, refresh, or update a person's summary or stated views, or when prepping for a meeting where the summary feels stale. Use proactively after meaningful edits to `# My notes`. Propose the new content as a diff for confirmation before writing.
---

Vault conventions are defined in the `obsidian` skill body — activate it first.

## Scope

Edits the `# Summary` and `# Stated views` blocks and the `description:` frontmatter field. `# Stated views` is optional — create it when there's view content worth a section, skip it otherwise. Never touches `# My notes` (user-owned) or `# From LinkedIn` (owned by the `background` skill). All **other** frontmatter (`role`, `organisation`, `aliases`, …) is read-only — if it looks stale, surface it; don't change silently.

## Inputs

- Person's name, or the file path. If missing, ask.
- Optional: a specific reason to refresh (e.g. prepping for a meeting, just added a note) — affects emphasis.

## Steps

1. Read `$OBSIDIAN_VAULT/people/<Name>.md`. Capture: frontmatter, current `# Summary`, current `# Stated views` (if present), `# My notes`, `# From LinkedIn` (context only).
2. Draft new content per "What goes where" below.
3. Show the user a clear before/after diff for the `# Summary`, `# Stated views`, and `description:`. **Wait for explicit confirmation** ("apply", "go ahead", "yes"). Do not write yet.
4. On confirmation, update the `description:` line and replace the affected blocks via `Edit` — including the `*Summary refreshed: [[<today>]].*` marker as the first line of `# Summary`. Touch nothing else.

## What goes where

The Summary answers **what do I need in my head before working with this person?** Stated views answers **what positions have they expressed that will shape how they react?** Working background usually beats current views in the Summary — views get their own block.

### `# Summary` — narrative, 3-4 dense sentences

**Stamp the freshness marker.** The first line under the `# Summary` heading is `*Summary refreshed: [[YYYY-MM-DD]].*` — set it to **today's date** (resolve from the shell with `date +%Y-%m-%d`; the sandbox runs in NZ time). This marker is the authoritative signal the `validate-vault` hook reads to decide the meeting-prep view is current: **refreshing the Summary without stamping it leaves the person flagged as stale** (dated engagement refs alone no longer clear it). Add the line if absent; update the date if present.

**Lead with working background:**
- Position in the current work landscape (not job title alone)
- Sponsorship, ownership, who they back
- Relationships and prior history relevant to live engagements
- Current dynamics — what they're actively working at the moment, including political ones
- Verification flags from `# My notes` (claims to confirm before they land in a report)

**Don't put here:**
- Career chronology — that's `# From LinkedIn`
- Stated views and framings — those go in `# Stated views`
- Generic adjectives ("experienced", "passionate")
- Anything that won't change how the user prepares or behaves in the room

### `# Stated views` — bulleted, optional

Each bullet is a position the person has expressed on record:
- Technical stances ("X should be owned by Y, not Z")
- Problem framings ("A is 10% of the problem")
- Open questions they've raised — include rebuttals from others, attributed

Create the section only when there's at least one substantive view. Don't write filler bullets like "interested in observability". Skip the section entirely on thin profiles.

### `description:` — one plain-prose line

The grep-survey hook — a one-sentence distillation that lets the person surface in a `grep ^description:` sweep across `people/`. Lead with role + org + the load-bearing context that distinguishes them from siblings. Keep it **coherent with the refreshed `# Summary`**: when the Summary changes materially, refresh the description to match.

**Plain prose — no wikilinks.** `description:` is a metadata field: `[[…]]` adds noise to the grep survey and doesn't render as a link in Obsidian's properties view. Reserve wikilinks for the body blocks. Quote-wrap the value.

## Voice

Match the user's existing tone — declarative, direct, no padding. Preserve load-bearing phrasings the user authored (specific quotes, framings) verbatim where still accurate.

**Wikilinks:** apply the vault rule — wikilink every mention of a vault entity (people, orgs, engagements, glossary terms). Use explicit `[[Target|Alias]]` syntax.

## Quick example

For a fictional Skye (anonymised):

```markdown
# Summary
*Summary refreshed: [[2026-04-29]].*
Platform product lead in [[Lookout Tower Foundations]] at [[Adventure Bay Co]]; sponsors [[Rocky]]'s tooling team. Prior history with [[Marshall]] (from [[Adventure Bay]]) and [[Chase]]. Currently working political ground for [[FDC]] / [[WDF]] — pulled [[Marshall]] aside at the 2026-04-29 meeting ("we don't want no part of this"). Carries a secondhand 70% delivery-uplift claim about [[PupTech]] worth verifying before it lands in any report.

# Stated views
- Architectural standards should be contributed to but owned by the architects, not embedded in the framework. Cites the failed "Adventure Bay way" as cautionary.
- Code generation is "10% of the problem" — review capacity is the real constraint at scale.
- Reviewing AI-generated code needs a different model *family* — not just Opus vs Sonnet.
```

Matching `description:` (plain prose, no wikilinks): `"Platform product lead in Lookout Tower Foundations at Adventure Bay Co; sponsors Rocky's tooling team; currently working FDC/WDF political ground."`

Full before/after at [references/example.md](references/example.md).

## Constraints

- **Propose-and-confirm only.** Never silently rewrite either block.
- **Don't editorialise `# My notes`.** Read it; never change it.
- **Don't flatten nuance.** If the notes capture competing positions or contested dynamics, keep both threads.
- **Carry forward verification flags.** If `# My notes` flags a claim as needing verification, the Summary should signal it too.
- **Stated views is optional.** Skip the section on thin profiles rather than writing filler.
- **Keep `description:` coherent with the Summary.** Refresh it whenever the Summary changes materially; plain prose, no wikilinks, quote-wrapped.
- **Always stamp `Summary refreshed:`** with today's date — it is what clears the `validate-vault` stale-person flag; a refresh that omits it leaves the person looking stale.
- **Minimal `Edit` calls.** One per block (the `description:` is a separate frontmatter edit) — or a single combined call when blocks are contiguous.
