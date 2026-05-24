---
name: cp-team-update
description: Draft a value-dense Slack status update for the user's project delivery team — structured as numbered overview facts + numbered risks, no prose paragraphs. Use when the user asks for a team update, project update, Slack post for the team, status post, read-out for the channel, or any short structured update aimed at the project delivery channel.
---

# cp-team-update

Drafts a Slack update for the user's project delivery team channel. Output is value-dense, structured, and ready to paste — the user edits lightly and sends.

The user writes these multiple times per day. Every word counts.

## Audience — load from the vault

Channel composition lives in the user's Obsidian vault, not in this skill. **Before drafting, find and read the relevant channel note via the `obsidian` skill** to get the current active/lurking split.

**Discovery:** grep `^description:` across `$OBSIDIAN_VAULT/misc/` for notes describing Slack channels (per the obsidian skill convention — every vault note has a `description:` line summarising it). Look for descriptions mentioning "Slack channel" plus the engagement / team the user named. If multiple channel notes match, ask. If none match, ask the user which channel before drafting.

The channel note will contain a **Members** table with at least three columns: person (wikilinked), role, posture (`Active reader` | `Lurks`). Use it as the source of truth for who reads the post.

The audience is senior consultants and leadership — they already know the engagement context. **Do not re-explain who people are, what engagements/frameworks/acronyms mean.** Lead with new information.

**The lurker test:** would a partner who hasn't read updates this week understand the *stakes* (not the context) from this post? Write to pass that test without restating context the active readers already have.

## Structure

Two optional blocks. Numbered items, not prose paragraphs (each item may be a 1-3 sentence cluster). Either block can be omitted entirely rather than padded with lukewarm content — though shipping Risks without Insights is rare in practice. No closing question unless a decision is genuinely required.

**Bar: high-value signals only.** One insight with no risks beats five facts and four risks the channel skims past. If a fact or risk doesn't change a reader's model of the engagement, cut it.

```
ℹ️ <headline — substantive event name OR topic label for recurring meeting types>:  (omit block if no high-value insight)

1. <fact or short paragraph-cluster — lead claim + inline quote where it carries weight>
2. <fact>
3. ...


⚠️ Risks:  (omit block if no sharp risk to flag)

1. **<Optional bold lead.>** <One sentence naming mechanism + consequence; name specific stakeholders the risk implicates.>
2. ...
```

Rules for each block:

- **Headline:** name the event substantively (✅ "Update on the session with X") OR use a topic label for recurring meeting types the channel knows (✅ "Workflow tier updates:"). Avoid the *meta* (❌ "Update on conversations").
- **Insights (facts):** 1-5 numbered items in narrative order. Each can be a tight sentence OR a short paragraph-cluster (lead claim + supporting context + inline quote). Prefer inline `"..."` quotes; use `>` blockquote only when length warrants its own block. Quote verbatim — never paraphrase.
- **Editorial leads welcome in the Insights block** when they're the load-bearing signal ("Everest is seeing PSDLC for what it is" *is* the news). First-person OK ("I steered..."). The editorialising antipattern only applies inside risks.
- **Risks:** 0-4 numbered. Prefer one sharp risk over many lukewarm ones; omit the block entirely if nothing sharp to flag. Bold lead optional (1-3 words ending with period). Body names mechanism + consequence. **Name the specific stakeholders implicated** ("Mayor Goodway/Katie still unaware...") — the lurker test relies on this. No hedging.
- **Spacing:** blank line between blocks. Emojis as block delimiters only.

## Density rules

Cut on draft:

- **Articles where droppable.** "We highlighted overengineering" beats "We highlighted the overengineering issue".
- **Process narration.** Drop "we discussed", "we explored", "happy to chat", "wanted to flag". State the substance, not the meeting structure.
- **Restatement.** Drop "the bit that needs the team's attention", "the key takeaway is", "to summarise". The reader knows it's the summary.
- **Hedging openers.** Drop "I want to flag", "I think", "it seems", "potentially". Risks should be declarative — if they need a hedge, they're not risks yet.
- **Softening closers.** Drop "happy to bring this to a quick call", "let me know what you think", "open to thoughts". If you need a decision, ask the specific question; otherwise stop.
- **Re-explanation of known entities.** Drop "PSDLC (the existing framework)", "Mr. Porter (the client stakeholder)". The channel knows.

Keep:

- Direct quotes verbatim with the speaker named.
- Names of people and frameworks (the channel knows them; brevity > redundancy).
- The mechanism inside each risk (*why* it's a risk, not just that it is).

## Antipatterns

Real edits from a previous draft → cut:

| Drafted | Why cut |
| --- | --- |
| "Quick read-out on this morning's session…" | "Quick" + "read-out" = self-narration. Just lead with the topic. |
| "…but the bit that needs the team's attention:" | Restating the summary. |
| "I want to flag before we say yes:" | Hedging opener; risks should stand alone. |
| "Happy to bring this to a quick call." | Softening closer; if a call is needed, propose a time. |
| "Two simultaneous 'modest' asks rarely stay modest." | Editorialising inside a risk; state the consequence directly. |
| "PSDLC (the existing framework we've been reviewing)" | Re-explaining a known entity. |
| "Mayor Goodway/Katie unaware of how invaluable it is" (when meaning the opposite) | Semantic-opposite word reverses the risk. Sense-check inverting words (invaluable ↔ dispensable, indispensable ↔ optional) before posting. |

## Worked examples

Read both before first drafting to calibrate density, tone, and the high-value-signals bar.

- `references/abf-update-example.md` — wordy first draft → terse shipped version. Teaches the density cuts (hedging openers, restatement, self-narration, re-explaining known entities).
- `references/workflow-tier-comparison-example.md` — agent's formal-shape draft → user's real-talk shape with a single load-bearing risk. Teaches the high-value-signals bar, topic-label headlines, paragraph-cluster facts, editorial leads, and stakeholder-named risks.

## Procedure

1. **Load the audience.** Discover the relevant channel note in `$OBSIDIAN_VAULT/misc/` by grepping `^description:` and matching on "Slack channel" + the engagement/team the user named. Read it via the obsidian skill. Use the Members table to inform tone, what to omit, and the lurker test.
2. **Confirm the trigger event.** What happened that needs the team to know? If unclear, ask before drafting.
3. **Draft the overview block.** 3-5 numbered facts. Nest verbatim quotes where they carry an ask or commitment.
4. **Draft the risks block.** Each risk: bold name + one sentence with mechanism + consequence.
5. **Self-edit pass.** Apply the density rules above — cut articles, process narration, restatement, hedges, softeners.
6. **Present as a code block** the user can copy directly into Slack. Note any judgement calls (recipients, optional cuts) below the block, not inside it.
7. **Do not save to the vault.** This is an outgoing comms artefact, not a knowledgebase entry.
