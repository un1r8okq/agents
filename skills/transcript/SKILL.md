---
name: transcript
description: Process a meeting transcript into a wikilinked detail note with summary and analysis. Use when the user provides a transcript (file path or pasted text) and asks to summarise, process, extract, or create a detail note from it.
---

Activate the `obsidian` skill first to load vault conventions.

## Inputs

The user provides one of:
1. A **file name** (e.g. `AB CDE1 Marshall PoC Standup - 2026_05_18 09_30 NZST - Notes by Gemini.md`) to a transcript in `/mnt/c/Users/<username>/Downloads/`.
2. A **file path** — may be an export with a raw name that needs normalising (see step 1).

They may also provide:
- A topic hint for the slug and summary.
- A date (if not derivable from the filename or content).

## Procedure

### 0. Gate: verbatim transcript, not a summary

Before anything else, read the file and confirm it is a **verbatim turn-by-turn transcript**, not an auto-generated **summary**.

Tell-tale signs it's a Gemini/Meet **summary** (not a transcript):
- Sections like `### Summary`, `### Decisions`, `### Next steps`, `### Details` instead of timestamped speaker turns.
- Prose attributed to a room resource (e.g. *"someone in SYD-SO-NOR-W1-C1-MR.10 [HO]"*) rather than named `**Speaker:**` labels.
- Bullet recaps with `[00:00:00]` heading links instead of continuous dialogue.

A real transcript has continuous `**Name:**` speaker turns and usually a trailing *"This editable transcript was computer generated…"* line.

**If it's a summary: STOP immediately.** Do not rename, process, or write anything. Tell the user the file is a summary, not a verbatim transcript — summaries lose the signal the detail note depends on (real quotes, speaker attribution, room dynamics) and sanitise tone and conflict. Ask whether they have the verbatim transcript export (often a separate `… (1).md` sibling, or the Google Doc behind the "Transcript" link), or want you to proceed from the summary anyway. **Wait for an explicit "continue" / "proceed" before any further work.** If they opt to proceed from the summary, add a source-fidelity caveat at the top of the detail note (body is paraphrase not verbatim; attribution partial).

### 1. Ingest and normalise the transcript

**If the file is already in `daily/transcripts/` with a conforming name:** read it. Extract the date from the filename.

**If the file has a raw export name** (e.g. from Google Meet/Gemini): normalise it before processing.

1. **Resolve the date** — see date resolution below.
2. Match the meeting title against the recurring meetings table below. If matched, use the canonical slug. Otherwise derive a slug (kebab-case, max 6 words) from the title.
3. Rename/move to `$OBSIDIAN_VAULT/daily/transcripts/YYYY-MM-DD-<slug>-transcript.md`.

#### Date resolution

The filing date is the **user's local date (NZ time)**, which may differ from dates in the export. The user is in NZ (NZST = UTC+12, NZDT = UTC+13).

Sources, in priority order:

1. **User-provided date** — always wins if given.
2. **Raw export filename** — Gemini exports embed `YYYY_MM_DD HH_MM TZ` (e.g. `2026_05_15 08_59 AEST`). Parse the datetime and convert to NZ time. For most business-hours meetings AEST (UTC+10) → NZ is same calendar day, but late-afternoon AEST can roll forward.
3. **First line of transcript content** — Gemini exports put `Month DD, YYYY` (e.g. `May 17, 2026`) on line 1. This date is in the meeting organiser's timezone (usually AEST), not the user's. It may be one day behind the NZ date.
4. **Cross-check the daily note** — if `$OBSIDIAN_VAULT/daily/YYYY-MM-DD.md` references the meeting in its `## Schedule`, that confirms the correct NZ date.

If the resolved NZ date differs from the date in the transcript content (common for Australian-timezone meetings), use the NZ date for the filename without flagging — this is expected.

#### Filename transformations for recurring meetings

Transcript file names should be consistent for recurring meetings. The canonical mapping of
recurring meetings to target filenames lives in `$OBSIDIAN_VAULT/meta/transcript-data.md` (loaded
in step 2) — match the meeting title against that table first.

Illustrative pattern (fictional — real mappings are in the vault file):

| Example starting filename | Example target filename |
| --- | --- |
| `Adventure Bay Pup Standup - 2026_05_18 09_30 NZST - Notes by Gemini.md` | `2026-05-18-adventure-bay-standup-transcript.md` |
| `Lookout Tower Daily Check In – 2026_05_18 09_00 AEST – Notes by Gemini.md` | `2026-05-18-lookout-standup-transcript.md` |

The `-transcript` suffix is reserved for **raw transcripts** in `daily/transcripts/` only. The corresponding **detail note** in `daily/detail/` drops the suffix (e.g. `2026-05-18-lookout-standup.md`).

When the user establishes new recurring meetings, ask for the intended target filename and add it to the table in `$OBSIDIAN_VAULT/meta/transcript-data.md`.

### 2. Build the name-resolution table (mandatory)

**HARD GATE — do this before any name resolution.** You MUST read
`$OBSIDIAN_VAULT/meta/transcript-data.md`. It holds the real recurring-meeting filename mappings
(step 1) and the known-mistranscriptions table — the personal lookup data this skill depends on,
kept out of the shared skill body. **If that file does not exist, STOP and ask the user** where
the lookup data lives; do not attempt resolution from the fictional examples below.

Then build a lookup of vault people. Issue in parallel:

- `ls` of `$OBSIDIAN_VAULT/people/` to enumerate all person filenames.
- `grep` for `^aliases:` across `$OBSIDIAN_VAULT/people/` — then read the list values for each match.

Build a map: `{lowercase display form → vault filename}`. Sources:
- The filename itself (e.g. `Ryder.md` → "ryder").
- The `aliases:` list (e.g. `["Cap"]` on `Captain Turbot.md` → "cap" maps to Captain Turbot).
- The known mistranscriptions table from `$OBSIDIAN_VAULT/meta/transcript-data.md`.

**Collision handling:** one person's mistranscription may match another person's real name (e.g. a mistranscription of "Marshall" might collide with a substring of "Marshfield"). Use transcript context (role, conversation topic, who else is present) to disambiguate. If genuinely ambiguous, ask the user.

#### Known mistranscriptions (illustrative)

The **real** table lives in `$OBSIDIAN_VAULT/meta/transcript-data.md` — you loaded it at the top of
this step. The fictional rows below only illustrate the *kinds* of error to expect and how the
`Notes` column drives disambiguation. Record new mistranscriptions in the vault file, not here.

| Mistranscription(s) | Actual | Notes | Pattern illustrated |
| --- | --- | --- | --- |
| skylar | Skye | Gender-neutral STT slip; *"Skylar landed her chopper"* — "her" disambiguates | Gender/name flip |
| marsh, mars, marshell | Marshall | "marsh"/"mars" are truncations; close to real name | Truncation |
| rubble, rble, rumble | Rubble | "rble" is a tail-of-word artefact | STT artefact |
| chase, chace | Chase | Collides with the verb "chase" — disambiguate by whether a person is being addressed | Collision (word vs name) |
| cap, capn, captain turbo | Captain Turbot | "Cap" is his go-by; "turbo" drops the final "t" | Short-form + truncation |
| ryder, rider, writer | Ryder | "writer" is an STT substitution on the team lead's name | STT substitution |
| zuma, zoomer, zoom a | Zuma | Collides with the meeting tool "Zoom" — disambiguate by context | Collision (tool vs name) |
| jay curve | J-curve | Concept, not person — productivity-dip-then-rise framing | Concept (not a person) |
| pup pack, pup pac | PupPack | Org/product — STT splits the compound word | Org/product truncation |
| paw trol, patrol a i | PawPatrol AI | Product name mistranscribed many ways | Product, many variants |

### 3. Identify participants

Scan the transcript for speaker labels (bold names, `**Name:**` patterns). Map each to a vault person using the resolution table from step 2. The user maps to `[[me|<Display Name>]]`.

**Shared room/resource mics.** A speaker label may be a meeting-room device (e.g. `**Lookout Tower:**`) carrying several people on one label. The label is not a person — treat its turns as unattributed until proven otherwise:

1. **Establish the roster behind the mic** before attributing any turn: from the user's input, greeting/roll-call chatter, or self-identification (*"on the call was Marshall and me"* rules the speaker in or out by elimination).
2. **Track arrivals and departures** (*"thanks Rubble"*, *"I need to head back downstairs"*). The dominant voice can change mid-meeting; a recurring first-person narrative thread that spans a departure identifies the speaker as someone who stayed.
3. **Attribute turn-by-turn from context** — who the turn addresses, first-person facts only one person could know, role-consistent content. Mark inferred attributions as such in the detail note (an attribution note under Present), and prefer "(room mic — A or B)" over a confident guess.

**Ask the user when not confident — they were in the meeting.** If an attribution is ambiguous and load-bearing (a quote in the Summary/Analysis, an action-item owner, who proposed a key decision), resolve it via `AskUserQuestion` before writing the detail note — batch all ambiguous turns into one question. Never silently guess the speaker of a quote that carries strategic weight.

### 4. Gather vault context

Before writing anything, build understanding of the people, projects, and terms in the transcript by reading relevant vault notes. This step is what makes the summary and analysis informed rather than surface-level.

1. **Start with participants.** Read the person note for each identified speaker (from step 3). Skim `# Summary` and `# My notes` for role, dynamics, and patterns.
2. **Identify entities from the transcript.** Scan for proper nouns, project names, acronyms, and initialisms. Search across `engagements/`, `orgs/`, `glossary/`, and `misc/` for matches.
3. **Follow wikilinks.** From the notes read in steps 1–2, follow `[[wikilinks]]` to related entities — people mentioned in patterns, linked engagements, referenced orgs. Go multiple layers deep where relevant: if a person note links to an engagement, and that engagement links to a glossary term that appears in the transcript, read the glossary entry too.
4. **Stop when diminishing returns.** The goal is enough context to write an informed analysis — not to read the entire vault. Skip links that are incidental (date links, passing mentions in lists).
5. **Build the entity resolution set.** Grep `^description:` across `glossary/`, `orgs/`, and `engagements/`. The filenames (minus `.md`) are wikilink targets. Use this set when writing — every transcript mention of a glossary term, org, or engagement gets wikilinked on every occurrence, not just people.

Issue reads in parallel where possible — don't serialise avoidable round-trips.

### 5. Analyse and draft

Read the transcript fully and draft three sections:

**Summary** (`## Summary`) — 1-2 sentences. What was the vibe/outcome? Not a table of contents.

**Topic sections** — each distinct topic gets its own `##` heading. Within each:
- **Tight prose, not bullet dumps.** Write like compressed field notes — drop articles, tighten sentences (e.g. "Bulk of call was X" not "The bulk of the call was X").
- **Direct quotes are gold.** Preserve verbatim quotes with *italics* — they carry tone and evidence.
- **Bold for emphasis.** Key claims, risks, and dynamics get `**bold**`.
- **Structure within sections.** Use sub-headings (`###`), short bullet lists, or bold leads as needed. Don't flatten everything into prose.
- **Every vault entity wikilinked on every occurrence** — people, orgs, glossary terms, engagements.
- End with an **Action items** section if applicable (one bullet per person, bold the person name).

**Analysis** — a separate `## Analysis` section at the end. Draw insights and potential actions given the wider vault context:
- Risks, political dynamics, strategic implications.
- Connect to patterns and history from vault notes.
- Recommend actions or flag decision points.
- This is the consultant value-add — not just what happened, but what it means.

### 6. Write the detail note

Path: `$OBSIDIAN_VAULT/daily/detail/YYYY-MM-DD-<slug>.md`

Derive `<slug>` from the transcript filename (strip date prefix and `-transcript` suffix).

Format:

```markdown
---
description: "<specific ~15-word description>"
---
Full transcript: [[YYYY-MM-DD-<slug>-transcript]]

## Present

- [[Person A|Full Name]]
- [[me|User's Full Name]]

## Summary

<1-2 sentence vibe/outcome>

## <Topic 1>

<tight prose with **bold**, *quotes*, structure>

## <Topic N>

...

## Action items

- **[[Person A]]:** <actions>

## Analysis

<insights, risks, strategic implications drawing on vault context>
```

**Wikilink rules:**
- Every occurrence of every vault entity — person, org, engagement, glossary term.
- Always use explicit alias form: `[[Captain Turbot|Cap]]`, never bare `[[Cap]]`.
- The user is always `[[me|<Full Name>]]` in the Present list. Body text may use bare first name without linking (the user is implicitly present).
- The Present list always uses **full names** as the alias (e.g. `[[Captain Turbot]]`, `[[me|<Full Name>]]`), not short forms.
- Unresolved names (no vault page): wikilink anyway — `[[Alex]]`. Unresolved links preserve semantic intent for future stub creation.

### 7. Append bullet to daily note

Target: `$OBSIDIAN_VAULT/daily/YYYY-MM-DD.md`. If it doesn't exist, create from `$OBSIDIAN_VAULT/daily/template.md`.

Append a bullet to `# Notes`. The bullet:
- Frames through a consultant lens — capture the risk, decision, or dynamic, not the activity.
- Max two sentences.
- Wikilinks people, orgs, concepts.
- Ends with: ` See [[YYYY-MM-DD-<slug>]].`

### 8. Report back

Tell the user:
- The detail file path written.
- The bullet appended to the daily note.
- Any unresolved names (no vault page found).
- Any ambiguous name resolutions or inferred speaker attributions that were made (so the user can verify).
- **New mistranscriptions observed.** If any transcript name was resolved to a vault person via context rather than an existing entry in the known mistranscriptions table, propose adding it. On confirmation, update the table in `$OBSIDIAN_VAULT/meta/transcript-data.md` (never the fictional table in this skill file).

## Edge cases

- **Multiple meetings same day**: each gets its own transcript and detail note. Slugs must differ.
- **Transcript already has a detail note**: check before writing. If one exists, confirm with the user before overwriting.
- **Names not in transcript speaker labels**: people mentioned in conversation but not speaking. Still wikilink in the notes/summary; don't add to Present list.
- **Garbled transcript**: transcription tools produce errors beyond names (sentence fragments, merged speakers). Interpret intent but note when quoting uncertain passages.
- **No date derivable**: ask the user. Do not invent dates.

## Tool usage

Prefer `Read`, `Glob`, `Grep` over `Bash`. When `Bash` is needed (e.g. `ls`, `mv`, `grep`), avoid piped compound commands (`&&`, `|`) but multi-file arguments in a single call are fine (e.g. `grep -A 5 "^aliases:" file1.md file2.md`).
