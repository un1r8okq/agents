---
name: slack-thread
description: Extract a pasted Slack thread into a structured Obsidian table at $OBSIDIAN_VAULT/daily/detail/, and add a consultant-lens summary bullet to the daily note. Use when the user pastes Slack thread text and asks to extract, save, capture, transcribe, or format a Slack thread for their knowledgebase.
---

# slack-thread

Captures a pasted Slack thread, parses it, wikilinks it against the user's vault, writes a detail note, and adds a single summary bullet to the relevant daily note.

The user's intent is to give LLMs more context on their work via Obsidian. Optimise for fidelity (verbatim message text) and discoverability (rich wikilinking).

## Invocation

The user pastes raw Slack thread text and asks to extract/save/capture it. They may also include:

- A Slack permalink — used to derive the originating message's date.
- A channel name (e.g. `#aesdlc`) — included in the lead sentence if provided.
- A topic hint — used in the H1, slug, and summary.

If the paste lacks a date and a permalink, ask the user for the start date before proceeding. Do not invent dates.

## Procedure

### 1. Parse the paste into ordered messages

- **New message** opens a row: a line of form `<DisplayName>  [<HH:MM AM/PM>]`. The display name may contain spaces or be a lowercase handle (e.g. `chaseh`).
- **Continuation** from the same author: a bare `[<HH:MM AM/PM>]` line — render as a separate row with the same author. Preserves chronology.
- **Strip** these artefacts:
  - `(edited)` markers
  - `N replies` (Slack often jams this onto an adjacent line — strip the substring, not the line)
  - Image / file attachment lines like `image.png [time]`, `screenshot.png [time]`, `*.pdf [time]`
- **Detect day rollover**: if a message's time is earlier than the previous message's time, the day has rolled over. Single-day filing requires confirming with the user that they still want one detail file (default → use start date) or split.

### 2. Determine the date

- **Permalink given**: extract the timestamp from the URL pattern `/p<digits>` (Slack permalinks). Divide by 1,000,000 to get unix epoch seconds. Treat as the originating message's date in the user's local time. Confirm with the user if any uncertainty.
- **No permalink**: ask the user for the start date.
- Convert to `YYYY-MM-DD`.

### 3. Resolve display names → vault people

- Read the `people/` directory of `$OBSIDIAN_VAULT` to enumerate person notes (filenames are display names, e.g. `Chase Hubble.md`).
- Match Slack display names against vault people. Slack handles vary: `chaseh`, `skye.flyer`, `Ryder`, `Chase H.`. Lowercase both sides and match on first-name and last-name fragments. Where ambiguous, ask.
- The user maps to `me.md`. When the user is referenced (their Slack name, an `@`-mention, or first-name appearance), wikilink to `me` preserving the displayed text: `[[me|Ryder]]`, `[[me|Me]]`, `[[me|ryder]]`.
- Surface any unresolved names in the post-write summary so the user can fix them.

### 4. Wikilink the message text

Apply these transforms to the body of every message. **The verbatim rule applies**: do not alter wording. The only allowed transforms are:

- **People wikilinks**: every match of any vault person, every occurrence (not just first). Use `[[Person Name|First]]` when the displayed text is just a first name; use `[[Person Name]]` when the full name appears.
- **`@`-mentions**: `@<handle>` → `@[[Person Name|First]]` if resolvable, else leave as `@<handle>`.
- **Concept wikilinks**: every match of any term whose filename exists in `glossary/` or `orgs/`. Match the full term (case-insensitive on first letter); preserve original casing in the displayed text. Use `[[Term]]` when the casing matches; `[[Term|displayed casing]]` otherwise.
- **Emoji shortcodes** → unicode:
  - `:thread:` → 🧵
  - `:rotating_light:` → 🚨
  - `:white_check_mark:` → ✅
  - `:heavy_check_mark:` → ✔️
  - `:x:` → ❌
  - `:warning:` → ⚠️
  - `:100:` → 💯
  - `:fire:` → 🔥
  - `:tada:` → 🎉
  - `:rocket:` → 🚀
  - `:eyes:` → 👀
  - `:pray:` → 🙏
  - `:raised_hands:` → 🙌
  - `:+1:` → 👍
  - `:-1:` → 👎
  - `:question:` → ❓
  - `:exclamation:` → ❗
  - `:sparkles:` → ✨
  - For other shortcodes, use your training knowledge of standard Slack/Unicode emoji shortcodes. If unknown (e.g. a workspace-custom emoji), leave as-is and surface in the post-write summary.

Do **not**: expand abbreviations, fix typos, add words, inline image content, or otherwise touch prose.

### 5. Propose, then confirm

Before writing anything, present to the user:

- **Filename**: `daily/detail/YYYY-MM-DD-<slug>.md`. Slug: kebab-case, ≤ 6 words, derived from the topic. E.g. `pup-pup-boogie-demo-concerns`.
- **H1**: `# <topic with wikilinks>`.
- **Lead sentence**: `On [[YYYY-MM-DD]] I <verb> <subject> in the [[Adventure Bay]] Slack workspace<channel-suffix>:` where `<channel-suffix>` is ` in #<channel>` if known, else empty. Verb default: `discussed`. Use a more accurate verb if the thread is clearly a flag/question/decision (`flagged`, `asked`, `proposed`).
- **Daily-note bullet** (draft) — see step 7 for the rule.

Wait for the user to confirm or amend before writing.

### 6. Write the detail file

Path: `$OBSIDIAN_VAULT/daily/detail/YYYY-MM-DD-<slug>.md`.

Format:

```markdown
---
description: "<~12-word description, mirrors H1>"
---
# <H1>

<lead sentence>

| Person | Time    | Message | Reacts |
| ------ | ------- | ------- | ------ |
| ...    | 2:25 PM | ...     |        |
```

- `Reacts` column is included but left empty. The user fills it manually.
- Times: render in the original format from the paste (e.g. `2:25 PM`).
- Pipe characters inside message bodies must be escaped as `\|`.
- Newlines inside message bodies must be rendered as `<br>` (table cells can't contain literal newlines).

### 7. Append a consultant-lens bullet to the daily note

Target file: `$OBSIDIAN_VAULT/daily/YYYY-MM-DD.md`. If the file does not exist, create it from `$OBSIDIAN_VAULT/daily/template.md`.

Append a bullet to the `# Notes` section (not `# Summary`). The bullet:

- **Frames the thread through a consultant lens** — capture the substantive risk, decision, insight, or stakeholder dynamic, not the activity. Compare:
  - ❌ Activity-framed: "Posted a Slack thread about Bruce's deck."
  - ✅ Consultant-framed: "Flagged that the kick-off deck pre-commits to rolling out the framework as-is, which would lock us out of the modular-library recommendation our discovery is converging on."
- One or two sentences.
- Wikilink people, orgs, concepts.
- End with: ` See [[YYYY-MM-DD-<slug>]].`

**This is an explicit carve-out from the general rule of not editorialising daily notes.** It applies only to slack-thread summary lines. Do not edit any other content in the daily note.

### 8. Report back

Tell the user:

- The detail file path that was written.
- The bullet that was appended to the daily note.
- Any unresolved `@`-mentions or display names.
- Any unrecognised emoji shortcodes left as-is.

## Edge cases

- **Multi-day thread**: ask whether to file under `daily/detail/` (using start date) or `misc/<descriptive-title>.md` (the user's stated default for multi-day). For `misc/` filing, follow the misc convention: no frontmatter, no H1, lead sentence as the first line, table after.
- **No permalink**: ask for the start date.
- **Reactions in the paste**: Slack copy-paste does not include reactions. If the user pastes them as a postscript like `react: chaseh 💯 on last msg`, place them in the `Reacts` column.
- **Image / file attachments**: drop silently. The user adds manually if they want.
- **Channel not known**: omit the `in #<channel>` clause.
- **Unrecognised emoji shortcode**: leave as-is and surface to the user.
- **Unresolved person**: leave plain (no wikilink) and surface to the user. Do not invent a vault entry.
- **Thread starter is a quote / forward**: render verbatim; no special handling.

## Tool usage

Prefer `Read`, `Glob`, `Grep`, `Edit`, `Write`. Avoid `Bash` compound commands (`&&`, `|`) — they bypass the user's allowlist.

If unfamiliar with the vault structure, read `$OBSIDIAN_VAULT/README.md` once at the start.

## Example

For an anonymised end-to-end walkthrough, see [`references/example.md`](references/example.md).
