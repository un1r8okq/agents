---
name: background
description: Add or update a person's professional background in the Obsidian vault from pasted LinkedIn Experience and/or Education text. Use when the user pastes LinkedIn profile data and wants it structured into a people note. Formats for working context (narrative summary, expertise areas) rather than a raw chronology.
---

Activate the `obsidian` skill first to load vault structure and rules.

## Inputs

The user provides:
- Person's full name
- Pasted LinkedIn text
    - About (optional)
    - Experience
    - Education (optional)
    - Volunteer experience (optional)

If the name is missing, ask.

## Steps

1. Check whether `people/<Name>.md` already exists.
    1. If it does, read it first to preserve the `# My notes` section.
    2. If it doesn't existing, you will create a new note.
2. List `orgs/` to know which org pages exist in the vault.
3. Parse the LinkedIn text into structured roles: company, title, type (contract/full-time), dates, and highlights.
4. Write or update the note at `people/<Name>.md` with the structure below.

## Note structure

```markdown
---
Organisation: "[[Current Org]]"
Role: "Current Title"
---
# Summary
3–4 sentence narrative based on LinkedIn info and info in the vault (including prior notes). Career arc, core strengths, anything directly relevant to current work or engagements.
Not a list. Written to be useful before a meeting.

# My notes
- Preserved from existing file, or empty if new. Use bullets for personal observations and relationships.

# From LinkedIn

## Expertise
- 4–8 themed tags drawn from the full history (e.g. PMO establishment, large-scale retail IT, risk & compliance). Used by AI for framing their skills in the context of vault engagements. Not a comprehensive list of skills, but the most relevant ones.

## Work history

**Org** · Title (Contract/FT)
*Date–Date*
- Achievement bullets only when genuinely useful — omit for thin or early-career roles

**Org**
*Date–Date*
- Role A (Date–Date) — notable highlight if any
- Role B (Date–Date)

## Education

**Institution** · Qualification
*Years* · Grade if notable
- Include only if it adds context — omit high school unless it reveals useful background (e.g. international origin)
- Ongoing informal study worth a brief note if it reveals something about the person
```

## Formatting rules

- **Wikilinks**: only wikilink orgs that have an existing page in `orgs/`. Plain text for everything else.
- **Single role at an org**: put the title inline (`**Org** · Title`), skip bullets unless there's something worth noting.
- **Multiple roles at an org**: drop the inline title, list roles as bullets with their own date ranges.
- **Separate stints at the same org** (years apart): treat as distinct entries — it's a timeline.
- **Achievements**: include only when notable (e.g. scale, crisis response, something directly relevant to current engagements). Omit for routine or early-career roles.
- **Summary**: flag experience relevant to known vault engagements (e.g. prior work at a client's competitor).
- Preserve contract vs. full-time distinction where stated.

## Reference

See [example](references/example.md) — Alex Mercer, fictionalized LinkedIn paste processed to final note.
