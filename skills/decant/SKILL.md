---
name: decant
description: Process a daily Obsidian note — extract learnings into the knowledgebase, update todo list, and add a summary. Use when the user asks to decant, process, or tidy up daily notes (files in the daily directory).
---

The user may specify a date for the daily note. If no date is provided, use today's date.

## Steps

1. Activate the `obsidian` skill to load vault structure from its README.
2. Read the daily note at `$OBSIDIAN_VAULT/daily/YYYY-MM-DD.md`. If it already contains a `# Summary` section, it has been decanted — confirm with the user before proceeding.
3. Add wikilinks to any people, organisations, or projects mentioned in the note where they were only linked once, or where you are highly confident. **Never reword the user's prose when inserting links** — only add `[[ ]]` around entity names. If you create a page, add a brief description and the source as the daily note.
4. **Split out long sections.** For each `##` subsection in `# Notes` that exceeds ~20 lines:
   - Create `$OBSIDIAN_VAULT/daily/detail/YYYY-MM-DD-topic-name.md` with a `description` frontmatter field and the **verbatim** content. Never summarise or reformat the content of the detail note. See [examples](references/examples.md).
   - Completely remove the `##` heading and its contents from the daily note.
   - Ensure `# Notes` contains a chronological reference to the split-out section:
     - If an existing bullet already mentions the section (e.g. "See Email to X below"), preserve the bullet **verbatim** and only replace the reference phrase with a wikilink to the new detail note. Do not re-tone, condense, or sanitise the user's words.
     - If no existing bullet mentions it, add a new 1-2 sentence analytical summary bullet with a wikilink to the new detail note.
   - Do this before knowledgebase extraction so subsequent steps work against the tidied daily note.
   - See [examples](references/examples.md) for the "never editorialise" rule.
5. Rename/relocate images to put them in the same directory of the document that uses them, with the same prefix and a descriptive suffix. E.g. an image `./20260101 Screenshot.png` in `./daily/2026-01-01.md` should be moved to `daily/2026-01-01-org-chart.png`
6. Extract useful information into the knowledgebase. Map content to vault directories:
   - **People**: new people → create/update `people/` note; convert plain-text references to wikilinks
   - **Orgs**: new organisations → create/update `orgs/` note
   - **Engagements**: project updates → add to relevant `engagements/` note
   - **Terms/acronyms**: create/update `glossary/` entry
   - **Other**: anything that doesn't fit neatly → `misc/`
   - For each extraction, cite the source: `Source: [[YYYY-MM-DD]]`
   - **Consultant Lens**: After editing each note, review holistically for structure, clarity, and conciseness. Preserve the critical tone and observations from the daily note; avoid sanitising skepticism or risks into "corporate speak".
7. Ask follow-up questions one at a time *before* extracting when context is needed to get it right. See [examples](references/examples.md).
8. Offer to create new notes for topics not yet in the knowledgebase.
9. Update `$OBSIDIAN_VAULT/todo.md`:
   - Remove completed items (`- [x] ...`) and any sub-items nested under them. The todo list is meant to be cleared as items finish — leaving them in clutters the file and dilutes the active list. If the completed item has durable context worth keeping (a decision, a lesson, a reference), move it to the relevant engagement / person / misc note first, then delete. Purely transactional items ("book room", "send email") can be deleted outright.
   - Add any new action items surfaced in today's note, grouped under the relevant heading.
10. Add a `# Summary` section at the top of the daily note. **Crucially, apply a critical consultant's lens.** Do not just summarise literally; read between the lines to capture subtext, skepticism, dysfunctions, and risks. If notes imply dubious claims (e.g., massive gains but nothing shipped) or bad practices (e.g., one-shotting huge PRs), call them out explicitly. Its presence signals the note has been decanted.
11. Suggest improvements to note structure or process only if something significant stands out.
