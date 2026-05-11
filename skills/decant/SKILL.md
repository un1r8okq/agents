---
name: decant
description: Process a daily Obsidian note — extract learnings into the knowledgebase, update todo list, and add a summary. Use when the user asks to decant, process, or tidy up daily notes (files in the daily directory).
---

The user may specify a date for the daily note. If no date is provided, use today's date.

## Procedure

Six phases. **Phases 1 and 4 must each be issued as a single parallel tool batch** — sequential execution there is the main reason this skill is slow. Phase 5's daily-note edits are deliberately sequential for safer recovery; its `todo.md` write runs in parallel with the first daily-note Edit.

### Phase 1: Discover (parallel batch)

Issue these reads in a single set of parallel tool calls:

- `$OBSIDIAN_VAULT/meta/conventions/README.md` (convention index; skip if already loaded this session)
- `$OBSIDIAN_VAULT/daily/YYYY-MM-DD.md` (the target daily note)
- `$OBSIDIAN_VAULT/todo.md`
- `^description:` grep across each of `people/`, `orgs/`, `engagements/`, `glossary/` (one Grep call per directory)

If the daily note already contains a `# Summary`, it has been decanted — confirm with the user before proceeding.

### Phase 2: Plan (no tool calls)

Plan the whole run in one pass before issuing any writes:

1. **Wikilinks to add.** Entity mentions in the daily note that are unlinked or only linked once.
2. **Sections to split out.** Extract any `##` subsection in `# Notes` to `daily/detail/YYYY-MM-DD-topic-name.md` if EITHER (a) it exceeds ~20 lines, OR (b) it captures an event involving **3+ vault people** — multi-person events otherwise propagate the same inline content across multiple person notes at entity-edit time. Plan the verbatim detail content and the bullet that will replace it (preserve existing reference bullets verbatim; only add a new analytical bullet where none exists). Detail notes need `description:` frontmatter and a `Present:` wikilinked attendee list.
3. **Image renames.** Match images in `daily/` against the daily note (e.g. `./daily/20260101 Screenshot.png` referenced by `2026-01-01.md` → `daily/2026-01-01-org-chart.png`).
4. **Extractions** per the map below.
5. **Todo updates.** Items to remove (completed; if durable context, move to the relevant note first) or add (new actions surfaced).
6. **Follow-up questions** for ambiguities or judgement calls that block extraction.

### Phase 3: Resolve ambiguity (batched)

If you have follow-up questions, batch them into a single AskUserQuestion. **Don't ask one at a time.** Wait for answers before Phase 4.

### Phase 4: Write everything except the daily note (parallel batch)

Issue as one parallel batch:

- **Detail notes.** Create each `daily/detail/YYYY-MM-DD-*.md` with verbatim content. **Never summarise or reformat the body.** Required frontmatter: `description:`.
- **New entity stubs** (people / orgs / glossary entries). Required frontmatter per `meta/conventions/frontmatter.md`. For new *people* stubs, judge whether high-value (key stakeholder, technical/practice lead, recurring contact, framework critic, named decision-maker) — if so, add to the `todo.md` plan: `- [ ] Pull LinkedIn background for [[Name]] via the background skill.` Skip for one-off mentions.
- **Existing entity edits** (engagement / org / person notes). Each is a different file → fully parallel. Cite source: `Source: [[YYYY-MM-DD]]`.
  - **Person notes follow the durable-portrait shape** (canonical: `meta/conventions/people-notes.md`). When updating an existing person note for a session/meeting:
    - Add **pattern-level** observations under `## Patterns` — one short rule per bullet (`**<title>.** <one-sentence observation>. Source: [[date]], [[date]].`). If a matching pattern already exists, **extend its source line** with the new date rather than duplicating.
    - Add a one-line pointer under `## Engagement events` linking to the detail note (or to the daily section if no detail note exists yet).
    - Do **NOT** create dated `## <Engagement> X YYYY-MM-DD` sub-sections of tactical recap — that content belongs in the detail note + engagement timeline. The same fact ending up in 4–5 person notes with slightly different framings is the failure mode this rule prevents.
    - Genuinely *new pattern frames* (not just new instances of an existing pattern) may warrant a named sub-section under `## Patterns` — name it for the *frame*, not the date.
  - **Engagement notes** carry the chronological timeline; dated rows accumulate there happily. Person notes do not.
- **Image moves** (one Bash `mv` per image).

The daily note and `todo.md` are **excluded** from Phase 4 — handled in Phase 5.

### Phase 5: Daily note edits + todo

Issue these sequentially against the daily note — each Edit operates on the file as left by the previous one. Run the `todo.md` write **in parallel with the first daily-note Edit** (different files):

1. **Section removals.** For each `##` subsection planned in Phase 2.2: Edit the daily note to replace the heading + content with the planned bullet. Preserve existing reference bullets verbatim; only insert a new analytical bullet where none exists.
2. **Wikilink insertions.** Edit to add `[[ ]]` around entity names — **never reword the user's prose**, only insert link syntax. Use `replace_all=true` only when the entity name is unambiguous (no substring overlap with other names); otherwise per-occurrence Edits.
3. **Summary prepend.** Edit to insert a `# Summary` section at the very top of the file. **Apply a critical consultant's lens** — read between the lines for subtext, skepticism, dysfunctions, and risks. If notes imply dubious claims (e.g. massive gains but nothing shipped) or bad practices (e.g. one-shotting huge PRs), call them out explicitly. Its presence signals the note has been decanted.

Sequential rather than single `Write`: incremental Edits are easier to recover from if one step misfires; a full-file `Write` would corrupt the note on a single bad computation.

### Phase 6: Report and offer

- Report what was created/edited.
- Offer to create new notes for topics not yet in the knowledgebase (if any surfaced and the user hasn't already greenlit them).
- Suggest improvements to note structure or process only if something significant stands out.

## Extraction map

- **People**: new → new `people/` stub; existing → wikilink updates + pattern bullets in `## Patterns` + pointer in `## Engagement events` (see Phase 4 person-note rule). New stubs may earn a `background` todo (see Phase 4).
- **Orgs**: new organisations → `orgs/` note.
- **Engagements**: project updates → relevant `engagements/` note.
- **Recognition**: client/stakeholder praise of the user (verbal, relayed, or written) → surface as a candidate for `[[recognition]]` with the quote, source, and provenance (was it solicited?). Don't add silently — add to Phase 3 follow-ups. See `recognition.md`'s "How this is maintained".
- **Terms/acronyms**: `glossary/` entry.
- **Other**: anything that doesn't fit neatly → `misc/`.

After computing each note's new content, sanity-check for structure, clarity, and conciseness. Preserve the critical tone and observations from the daily note; avoid sanitising skepticism or risks into "corporate speak".

See [examples](references/examples.md) for the verbatim rules and detail-note format.
