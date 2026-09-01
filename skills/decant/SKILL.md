---
name: decant
description: Process a daily Obsidian note — extract learnings into the knowledgebase, update todo list, and add a summary. Use when the user asks to decant, process, or tidy up daily notes (files in the daily directory).
---

The user may specify a date for the daily note. If no date is provided — or they give a relative date like "yesterday" — resolve it from the shell with `date +%Y-%m-%d` (the sandbox is set to the user's NZ timezone). **Do not** use the context-provided date, which is UTC and can be a day behind the user's local date. "yesterday" = local today minus one.

## Procedure

Nine phases. **Phases 1 and 5 must each be issued as a single parallel tool batch** — sequential execution there is the main reason this skill is slow. Phase 2 offers a short interview to capture your first-person read of the day before extraction. Phase 6's daily-note edits are deliberately sequential for safer recovery. Phase 7 refreshes engagement `context.md` files; Phase 8 closes the loop — a focus/concerns question **only when priorities genuinely compete**, plus approval of any proposed `todo.md` additions. **Never add a todo silently — additions are always proposed for the user to pick from.**

### Phase 1: Discover (parallel batch)

Issue these reads in a single set of parallel tool calls:

- `$OBSIDIAN_VAULT/daily/YYYY-MM/YYYY-MM-DD.md` (the target daily note)
- `$OBSIDIAN_VAULT/todo.md`
- `^description:` grep across each of `people/`, `orgs/`, `engagements/`, `glossary/` (one Grep call per directory; recursive so it picks up engagement-scoped glossary and companion files)
- For each engagement directory referenced in the daily note (e.g. `[[DSO2]]`), read its `context.md` (e.g. `$OBSIDIAN_VAULT/engagements/DSO2/context.md`)
- Each detail note / transcript the daily note links (`See [[...]]` bullets and `daily/detail/YYYY-MM/...` links) — so Phase 2's interview can ground its follow-ups in what actually happened.

If the daily note already contains a `# Summary`, it has been decanted — confirm with the user before proceeding. Otherwise the day has **not** been decanted — do the full extraction below. Detail notes and `See [[...]]` bullets from `/transcript` are normal un-decanted input, not a sign of prior processing.

### Phase 2: Interview (AskUserQuestion, then conversational)

This is the step that gets your first-person read of the day into the note before extraction. Offer it **every** run — no detection logic — but only once Phase 1's already-decanted check has passed (don't offer on a note you're merely re-confirming).

1. **Offer (always, trivially declined).** A single `AskUserQuestion`: *"Before I decant, want to add your own take on today?"* — options *"Yes, interview me"* / *"Skip — decant as-is"* (the user may also use "Other" to type their overview directly). If they skip, go straight to Phase 3. Per `~/.agents/AGENTS.md`, use AskUserQuestion here even though the real answer is free-text.
2. **Open prompt.** If they engage: *"Anything you want to capture about today — your read, decisions, what you'd change?"* Let them answer freely.
3. **Grounded follow-ups.** Ask 3–5 short questions **drawn from the open answer and the Phase 1 detail notes/transcripts** — e.g. *"You sat in on the [[DSO2]] architecture review; where do you actually think that landed?"* Ask conversationally, one at a time, and **stop early once they're done** — never pad to five.
4. **Capture verbatim.** Write the exchange into a `## Overview` subsection at the top of `# Notes` as **verbatim Q&A** — each question and the user's raw answer, unedited (no synthesis, no analysis; the Phase 6 summary supplies the lens later). This block is **exempt from Phase 3's detail-note extraction** — it always stays in the daily note. Everything else treats it as ordinary input: entities/patterns extract in Phase 5, wikilinks get added and the summary reads it in Phase 6.

On a genuinely nothing-to-add day this costs one keystroke.

### Phase 3: Plan (no tool calls)

Plan the whole run in one pass before issuing any writes:

1. **Wikilinks to add.** Entity mentions in the daily note that are unlinked or only linked once.
2. **Sections to split out.** Extract any `##` subsection in `# Notes` to `daily/detail/YYYY-MM/YYYY-MM-DD-topic-name.md` if EITHER (a) it exceeds ~20 lines, OR (b) it captures an event involving **3+ vault people** — multi-person events otherwise propagate the same inline content across multiple person notes at entity-edit time. **Exception: the `## Overview` interview block from Phase 2 is never extracted — it stays in the daily note regardless of length.** Plan the verbatim detail content and the bullet that will replace it (preserve existing reference bullets verbatim; only add a new analytical bullet where none exists). Detail notes need `description:` frontmatter and a `Present:` wikilinked attendee list.
3. **Image renames.** Match images in `daily/` against the daily note (e.g. `./daily/20260101 Screenshot.png` referenced by `daily/2026-01/2026-01-01.md` → `daily/2026-01/2026-01-01-org-chart.png`).
4. **Extractions** per the map below.
5. **Todo updates.** Plan items to *remove* (completed; if durable context, move to the relevant note first) — removals are applied automatically since they reduce bloat. For *additions* (new actions surfaced), **do not plan to write them directly** — collect them as a proposal list for the user to approve in Phase 8. Never add a todo silently.
6. **Follow-up questions** for ambiguities or judgement calls that block extraction.

### Phase 4: Resolve ambiguity (batched)

If you have follow-up questions, batch them into a single AskUserQuestion. **Don't ask one at a time.** Wait for answers before Phase 5.

### Phase 5: Write everything except the daily note (parallel batch)

Issue as one parallel batch:

- **Detail notes.** Create each `daily/detail/YYYY-MM/YYYY-MM-DD-*.md` with verbatim content. **Never summarise or reformat the body.** Required frontmatter: `description:` (plain text — no `[[wikilinks]]`).
- **New entity stubs** (people / orgs / glossary entries). Required frontmatter per `meta/conventions/frontmatter.md`. For new *people* stubs, judge whether high-value (key stakeholder, technical/practice lead, recurring contact, framework critic, named decision-maker) — if so, **add it to the Phase 8 todo-proposal list** (don't write it now): `- [ ] Pull LinkedIn background for [[Name]] via the background skill.` Skip for one-off mentions.
- **Existing entity edits** (engagement / org / person notes). Each is a different file → fully parallel. Cite source: `Source: [[YYYY-MM-DD]]`.
  - **Person notes follow the durable-portrait shape** (canonical: `meta/conventions/people-notes.md`). When updating an existing person note for a session/meeting:
    - Add **pattern-level** observations under `## Patterns` as `- **<title>.** <one-sentence invariant — durable behaviour, no dates/narrative>.` with an indented instance log beneath (`    - [[date]] — <≤~15-word distinctive clause>.`). The instance's full narrative lives once in the `timeline.md` row / detail note — the person note keeps only the clause. **If a matching pattern already exists, add an instance-log sub-bullet under it** — never a sibling pattern bullet, and never an "extend the source line" reminder. Mint a new pattern bullet only when the *behaviour itself* is new.
    - Add a one-line pointer under `## Engagement events` linking to the detail note (or to the daily section if no detail note exists yet).
    - **Stamp the `*Summary refreshed: [[YYYY-MM-DD]].*` marker** (first line under `# Summary`) to the **daily note's date** whenever you substantively update a note this way — it's what clears the `validate-vault` stale-person flag. Late-decant rule: never downgrade a marker that already carries a **newer** date. A note only *name-dropped* in the daily (no pattern/event added) gets **no** marker bump — leaving it flagged is correct until it's genuinely refreshed.
    - Do **NOT** create dated `## <Engagement> X YYYY-MM-DD` sub-sections of tactical recap — that content belongs in the detail note + engagement timeline. The same fact ending up in 4–5 person notes with slightly different framings is the failure mode this rule prevents.
    - **Group patterns into `### <frame>` sub-headings** once the note has ~8+ patterns (flat list fine below that); name frames for the behaviour, not the date.
    - **De-dupe against `# Stated views`.** Don't write a stated *position* as a pattern bullet — positions live in `# Stated views`; `## Patterns` is for *behaviour*. A position may surface as an *instance* of a behavioural pattern, not a duplicate bullet.
  - **Engagement notes** are directory-shaped: dated rows append to `engagements/<Engagement>/timeline.md`, **not** the main `<Engagement>.md` file. Person notes do not carry timelines.
- **Image moves** (one Bash `mv` per image).

The daily note and `todo.md` are **excluded** from Phase 5 — handled in Phase 6. Engagement `context.md` refresh is **excluded** — handled in Phase 7.

### Phase 6: Daily note edits

Issue these sequentially against the daily note — each Edit operates on the file as left by the previous one. (`todo.md` is **not** touched here — it's handled in Phase 8, after additions are approved. See Phase 3.5.)

1. **Section removals.** For each `##` subsection planned in Phase 3.2: Edit the daily note to replace the heading + content with the planned bullet. Preserve existing reference bullets verbatim; only insert a new analytical bullet where none exists.
2. **Wikilink insertions.** Edit to add `[[ ]]` around entity names — **never reword the user's prose**, only insert link syntax. Use `replace_all=true` only when the entity name is unambiguous (no substring overlap with other names); otherwise per-occurrence Edits.
3. **Summary prepend.** Edit to insert a `# Summary` section at the very top of the file. **Apply a critical consultant's lens** — read between the lines for subtext, skepticism, dysfunctions, and risks. If notes imply dubious claims (e.g. massive gains but nothing shipped) or bad practices (e.g. one-shotting huge PRs), call them out explicitly. Its presence signals the note has been decanted.

Sequential rather than single `Write`: incremental Edits are easier to recover from if one step misfires; a full-file `Write` would corrupt the note on a single bad computation.

### Phase 7: Refresh engagement context.md

For each engagement directory touched by today's daily note (i.e. any engagement whose `timeline.md` got a row in Phase 5, or whose people/dynamics appeared substantively in the daily note), refresh its `context.md` to reflect current state:

1. **Re-read** `engagements/<Engagement>/context.md` (already loaded in Phase 1).
2. **Compute the diff** in your head — based on today's daily note, what changed across the four sections?
   - **`## This week's priorities`** — promote/demote items; remove what's been completed; add new priorities surfaced today.
   - **`## Active concerns / risks`** — add risks that surfaced; remove those that have de-risked; sharpen wording on continuing ones.
   - **`## Watching`** — items not yet actionable but worth tracking. Move resolved items down to `## Recently resolved`.
   - **`## Recently resolved`** — add decisions/items resolved today. Move stale items (older than ~1 week) **out** of context.md into `decisions.md` (resolved table) or `timeline.md` (narrative) as appropriate, so context.md stays current.
3. **Update the `*Last refreshed:*` line** at the top to today's date.
4. **Write the refreshed file.**

**Late decants (out-of-order):** if `context.md`'s *Last refreshed* date is **later** than the target daily note (you're decanting an older note after a newer one already ran), don't recompute the full diff — make additive updates only, marked `([[YYYY-MM-DD]], decanted late)`, keep the newer refresh date, and don't demote/remove items the newer refresh already placed.

If context.md doesn't exist yet for an engagement (i.e. the engagement is still in single-file shape at `engagements/<Engagement>.md`), skip context.md refresh — flag in Phase 8 instead as a candidate for directory promotion.

### Phase 8: Confirm focus + approve todo additions (AskUserQuestion)

Close the loop via a **single** `AskUserQuestion` call (the multi-choice picker — per user preference in `~/.agents/AGENTS.md`, always use AskUserQuestion even when the natural answer is free-text). **Batch every applicable question into one call** — don't ask sequentially across turns. Both question types below are conditional: if neither a focus question nor a todo-approval question applies, **skip Phase 8's question entirely** and go to Phase 9.

**Focus question — ask only when it would produce signal the decant couldn't compute itself.** Per engagement touched, ask it when *either* (a) two or more priorities/risks genuinely compete and Phase 7 couldn't tell which you'd rank top, *or* (b) your likely focus plausibly diverges from the computed pin. **Skip it when Phase 7 already produced one clear, unchanged top priority** — re-confirming the model's own pin is make-work (and trains rubber-stamping); just state that pin in the Phase 9 report and move on. When you do ask:
- *"For [[Engagement]], what's your top focus / biggest concern this week?"* — frame around the **current** week, not the note's date (matters for late decants).
- 2–4 options, each a short, specific framing of a *competing* priority or concern from your Phase 7 priorities + risks. User picks one, or "Other" for free-form.

**Todo-approval question — include it whenever Phase 3.5 / Phase 5 surfaced any additions** (`multiSelect: true`):
- *"Which of these surfaced actions should I add to todo.md? (Pick none if you don't want any.)"*
- One option per proposed todo, phrased concisely. The user selects which to keep. **Never write a todo that wasn't selected.**
- AskUserQuestion caps a question at 4 options. If more than 4 additions surface, put the top 4 in the picker and list the rest in the Phase 9 report as optional adds the user can request.

After the answers:
- **Pin / elevate** (only if you asked a focus question) the chosen item to the top of `## This week's priorities` (or `## Active concerns / risks`) in `context.md`. Surface a follow-up question if the answer reveals something not yet captured. If you *skipped* the focus question, leave the Phase 7 pin as-is.
- **Write `todo.md` once:** apply the planned *removals* and append **only the user-approved additions** under the right engagement / `## Personal / Internal` heading, each with a `Source: [[YYYY-MM-DD]]` link. If the user picked no additions, only the removals are applied.

### Phase 9: Report and offer

- Report what was created/edited (including which `context.md` files were refreshed and which engagement-scoped entries were promoted).
- Offer to create new notes for topics not yet in the knowledgebase (if any surfaced and the user hasn't already greenlit them).
- Suggest improvements to note structure or process only if something significant stands out.

## Extraction map

- **People**: new → new `people/` stub; existing → wikilink updates + pattern bullets in `## Patterns` + pointer in `## Engagement events` (see Phase 5 person-note rule). New stubs may earn a `background` todo (see Phase 5).
- **Orgs**: new organisations → `orgs/` note.
- **Engagements**: project updates → relevant `engagements/<Engagement>/timeline.md` row; current-state changes → `context.md` refresh in Phase 7; new open questions / resolved decisions → `decisions.md`.
- **Recognition**: client/stakeholder praise of the user (verbal, relayed, or written) → surface as a candidate for `[[recognition]]` with the quote, source, and provenance (was it solicited?). Don't add silently — add to Phase 4 follow-ups. See `recognition.md`'s "How this is maintained".
- **Terms/acronyms**: cross-engagement → top-level `glossary/`; engagement-specific (project codenames, tier names, internal tools) → `engagements/<Engagement>/glossary/`.
- **Other**: anything that doesn't fit neatly → `misc/`.

After computing each note's new content, sanity-check for structure, clarity, and conciseness. Preserve the critical tone and observations from the daily note; avoid sanitising skepticism or risks into "corporate speak".

See [examples](references/examples.md) for the verbatim rules and detail-note format.
