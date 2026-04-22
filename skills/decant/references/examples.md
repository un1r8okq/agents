# Decant Examples

## Splitting long sections verbatim

When moving a long subsection out of a daily note into a detail note, preserve the original formatting, headings, bullet points, and exact wording. Do not synthesize or summarize the content within the detail note itself. Provide a short description in the frontmatter.

**Original text in daily note (`2026-04-20.md`):**
```markdown
## First team leader meeting
Present: [[Ryder]], [[Chase]], [[Skye]], [[Rubble]], [[Marshall]], [[me]].

### Intros
- Ryder is HoE at The Lookout. Pick pack, safety, automation. Adventure Bay.
- Chase is Eng Manager in one of the teams. Picking product productivity. Prediction algorithms. Productivity of the pup-pack.
...
```

**Updated daily note (`2026-04-20.md`):**
```markdown
# Notes
- Started the day working with Project Pup-Tag.
- ... (other daily notes)
- Met with [[Ryder]], [[Chase]], [[Skye]], [[Rubble]], and [[Marshall]] to discuss AI PoC experiences in rescue logistics. Complaints about vague/nonsensical requirements from Mayor Humdinger. Skepticism about lack of AI guardrails. Dubious productivity gains reported without shipping anything. Strange attempts to one-shot huge complex software with a single prompt. See [[2026-04-20-first-team-leader-meeting]] for full details.

## Next remaining short heading...
```

## Never editorialise the user's bullets in `# Notes`

The user's bullets in `# Notes` are their voice in the moment. Emotional content (frustration, self-criticism, relief) is part of the record and must stay verbatim. The critical-consultant-lens rule applies to the `# Summary` you add at the top of the daily and to knowledgebase extractions — **not** to bullets the user already wrote.

When splitting a section out to a detail note, any bullet in `# Notes` that *references* that section should be edited **minimally**: swap a phrase like "See X below" for a wikilink to the new detail note, and leave every other word alone.

**Original bullet in daily note:**
```markdown
- I had an awful realisation that I'd caused a data leak. See Email to [[Mayor Goodway]] below. I feel like such an idiot, and I think he's definitely going to see me as the problem child after [[2026-04-15-incident]]. However, given the policy implications (potentially getting fired for a cover-up), I feel like I had to send it.
```

**Bad — rewrites the user's prose into neutral corporate voice:**
```markdown
- Caught and self-reported a minor compliance misstep — my notes were syncing to a personal cloud bucket. Stopped it, deleted the bucket, and emailed [[Mayor Goodway]] — see [[2026-04-22-data-leak-self-report]]. Felt awful doing it, especially after [[2026-04-15-incident]], but the cover-up risk was worse.
```

**Good — minimal edit; only the reference changes:**
```markdown
- I had an awful realisation that I'd caused a data leak. See [[2026-04-22-data-leak-self-report]]. I feel like such an idiot, and I think he's definitely going to see me as the problem child after [[2026-04-15-incident]]. However, given the policy implications (potentially getting fired for a cover-up), I feel like I had to send it.
```

The same rule applies when adding wikilinks alone: insert `[[ ]]` around entity names; do not touch the surrounding sentence.

## Analytical vs. Literal Summaries

Avoid "secretary-style" literal summaries. Instead, use a "consultant-style" analytical lens to surface subtext, risks, and skepticism.

**Bad (Literal)**:
> Meeting with [[Ryder]] and [[Chase]] revealed 200-300% productivity gains from AI PoCs, though with increased cognitive load and planning requirements.

**Good (Analytical)**:
> Meeting with first [[Adventure Bay]] PoC team leads [[Ryder]] and [[Chase]]. Complaints about vague/nonsensical requirements from Mayor Humdinger. Skepticism about lack of AI guardrails. Dubious productivity gains reported without shipping anything. Strange attempts to one-shot huge complex software with a single prompt.

## When to ask follow-up questions

Ask when context would meaningfully improve the quality of an extraction. Ask *before* extracting — not after noticing a gap.

**Situation**: Note says "Mayor Goodway personally called me about a security ticket."
**Signal**: A Mayor handling a security ticket directly is unusual. Organisation size and culture are relevant context.
**Question to ask**: "How big is the Adventure Bay administration?"
**Outcome**: User says ~150 employees. Senior leadership involvement in operations is more normal at that size. This context belongs in the Adventure Bay org note and shapes how you interpret future entries.

**Rule of thumb**: If you'd write something that might be wrong or misleading without more context, ask first. One targeted question is better than a generic extraction.
