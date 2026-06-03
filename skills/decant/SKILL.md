---
name: decant
description: Process a daily Obsidian note — extract learnings into the knowledgebase, update todo list, and add a summary. Use when the user asks to decant, process, or tidy up daily notes (files in the daily directory).
---

The user may specify a date for the daily note. If no date is provided, use today's date.

## Procedure

Seven phases. **Phases 1 and 4 must each be issued as a single parallel tool batch** — sequential execution there is the main reason this skill is slow. Phase 5's daily-note edits are deliberately sequential for safer recovery; its `todo.md` write runs in parallel with the first daily-note Edit. Phase 6 refreshes engagement `context.md` files; Phase 7 closes the loop with a focus/concerns question.

### Phase 1: Discover (parallel batch)

Issue these reads in a single set of parallel tool calls:

- `$OBSIDIAN_VAULT/daily/YYYY-MM-DD.md` (the target daily note)
- `$OBSIDIAN_VAULT/todo.md`
- `^description:` grep across each of `people/`, `orgs/`, `engagements/`, `glossary/` (one Grep call per directory; recursive so it picks up engagement-scoped glossary and companion files)
- For each engagement directory referenced in the daily note (e.g. `[[DSO2]]`), read its `context.md` (e.g. `$OBSIDIAN_VAULT/engagements/DSO2/context.md`)

If the daily note already contains a `# Summary`, it has been decanted — confirm with the user before proceeding.

**Partially-decanted days.** No `# Summary` but referenced detail notes / entity edits / todo strikethroughs already exist (common when the transcript skill ran in-session). Proceed, but switch from full extraction to gap-filling:

- **Verify every `See [[...]]` link in the daily note resolves** — in-session captures sometimes reference detail notes that were never created or were merged into another note. Repoint or create as appropriate (ask in Phase 3 if it's a judgement call).
- **Check for duplicate bullets** — multiple in-day captures of the same event leave near-duplicate bullets with slightly different framings (and sometimes contradictory attributions). Merging or correcting them is a Phase 3 question, not a silent fix.
- **Diff against the knowledgebase, don't recreate** — check `timeline.md` for a missing dated row, person notes for missing `## Patterns` / `## Engagement events` entries, and `todo.md` for surfaced actions. Write only what's missing.
- **Out-of-order decants:** if an engagement `context.md`'s *Last refreshed* date is **later** than the target note, don't recompute the full Phase 6 diff — make additive updates only, marked `([[YYYY-MM-DD]], decanted late)`, keep the newer refresh date, and don't demote/remove items the newer refresh already placed.

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
  - **Engagement notes** are directory-shaped: dated rows append to `engagements/<Engagement>/timeline.md`, **not** the main `<Engagement>.md` file. Person notes do not carry timelines.
- **Image moves** (one Bash `mv` per image).

The daily note and `todo.md` are **excluded** from Phase 4 — handled in Phase 5. Engagement `context.md` refresh is **excluded** — handled in Phase 6.

### Phase 5: Daily note edits + todo

Issue these sequentially against the daily note — each Edit operates on the file as left by the previous one. Run the `todo.md` write **in parallel with the first daily-note Edit** (different files):

1. **Section removals.** For each `##` subsection planned in Phase 2.2: Edit the daily note to replace the heading + content with the planned bullet. Preserve existing reference bullets verbatim; only insert a new analytical bullet where none exists.
2. **Wikilink insertions.** Edit to add `[[ ]]` around entity names — **never reword the user's prose**, only insert link syntax. Use `replace_all=true` only when the entity name is unambiguous (no substring overlap with other names); otherwise per-occurrence Edits.
3. **Summary prepend.** Edit to insert a `# Summary` section at the very top of the file. **Apply a critical consultant's lens** — read between the lines for subtext, skepticism, dysfunctions, and risks. If notes imply dubious claims (e.g. massive gains but nothing shipped) or bad practices (e.g. one-shotting huge PRs), call them out explicitly. Its presence signals the note has been decanted.

Sequential rather than single `Write`: incremental Edits are easier to recover from if one step misfires; a full-file `Write` would corrupt the note on a single bad computation.

### Phase 6: Refresh engagement context.md

For each engagement directory touched by today's daily note (i.e. any engagement whose `timeline.md` got a row in Phase 4, or whose people/dynamics appeared substantively in the daily note), refresh its `context.md` to reflect current state:

1. **Re-read** `engagements/<Engagement>/context.md` (already loaded in Phase 1).
2. **Compute the diff** in your head — based on today's daily note, what changed across the four sections?
   - **`## This week's priorities`** — promote/demote items; remove what's been completed; add new priorities surfaced today.
   - **`## Active concerns / risks`** — add risks that surfaced; remove those that have de-risked; sharpen wording on continuing ones.
   - **`## Watching`** — items not yet actionable but worth tracking. Move resolved items down to `## Recently resolved`.
   - **`## Recently resolved`** — add decisions/items resolved today. Move stale items (older than ~1 week) **out** of context.md into `decisions.md` (resolved table) or `timeline.md` (narrative) as appropriate, so context.md stays current.
3. **Update the `*Last refreshed:*` line** at the top to today's date.
4. **Write the refreshed file.**

If context.md doesn't exist yet for an engagement (i.e. the engagement is still in single-file shape at `engagements/<Engagement>.md`), skip context.md refresh — flag in Phase 7 instead as a candidate for directory promotion.

### Phase 7: Confirm focus and concerns (AskUserQuestion)

Close the loop with the user via `AskUserQuestion` (the multi-choice picker — per user preference in `~/.agents/AGENTS.md`, always use AskUserQuestion for questions even when the natural answer is free-text).

Ask **one batched question per engagement touched**, with options drawn from what you computed in Phase 6:

- **Question:** *"For [[Engagement]], what's your top focus / biggest concern for the rest of this week?"*
- **Options (2–4, drawn from your Phase 6 priorities + risks)**: each option a short, specific framing of a candidate priority or concern. User picks one, or selects "Other" to type a free-form reply.

Use the user's answer to:
- **Pin / elevate** the chosen item to the top of `## This week's priorities` (or `## Active concerns / risks`) in `context.md`.
- **Surface a follow-up question** if the answer reveals something not yet captured (e.g. a new risk you didn't list).

If only one engagement was touched, ask the one question. If multiple were touched, batch into one `AskUserQuestion` call with multiple sub-questions (one per engagement). Don't ask sequentially across turns.

### Phase 8: Report and offer

- Report what was created/edited (including which `context.md` files were refreshed and which engagement-scoped entries were promoted).
- Offer to create new notes for topics not yet in the knowledgebase (if any surfaced and the user hasn't already greenlit them).
- Suggest improvements to note structure or process only if something significant stands out.

## Extraction map

- **People**: new → new `people/` stub; existing → wikilink updates + pattern bullets in `## Patterns` + pointer in `## Engagement events` (see Phase 4 person-note rule). New stubs may earn a `background` todo (see Phase 4).
- **Orgs**: new organisations → `orgs/` note.
- **Engagements**: project updates → relevant `engagements/<Engagement>/timeline.md` row; current-state changes → `context.md` refresh in Phase 6; new open questions / resolved decisions → `decisions.md`.
- **Recognition**: client/stakeholder praise of the user (verbal, relayed, or written) → surface as a candidate for `[[recognition]]` with the quote, source, and provenance (was it solicited?). Don't add silently — add to Phase 3 follow-ups. See `recognition.md`'s "How this is maintained".
- **Terms/acronyms**: cross-engagement → top-level `glossary/`; engagement-specific (project codenames, tier names, internal tools) → `engagements/<Engagement>/glossary/`.
- **Other**: anything that doesn't fit neatly → `misc/`.

After computing each note's new content, sanity-check for structure, clarity, and conciseness. Preserve the critical tone and observations from the daily note; avoid sanitising skepticism or risks into "corporate speak".

See [examples](references/examples.md) for the verbatim rules and detail-note format.
