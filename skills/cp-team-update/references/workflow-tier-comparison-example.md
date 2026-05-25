# Worked example — workflow tier framework comparison update

Anonymised real example. Shows the user reshaping a *formal*-shape draft into a *real-talk* shape — and dropping three risks down to one. Teaches the high-value-signals bar.

## Context

Daily workflow pup-pack standup. Everest (senior architect at the client, co-author of the in-house **PSDLC** framework) walked the team through his weekend review of Tracker's PSDLC-generated Lookout connector and **publicly compared it to a Foggy Bottom Spec Kit equivalent** — concluding PSDLC's output was *"cognitively challenging… fluffy… bloated"*. Asked Marshall to trial Foggy Bottom Spec Kit on a parallel flow. Chase (CP consultant) offered the *"spec is a liability — slash and burn bloat before iterating"* reframe; Marshall endorsed.

## First draft (formal shape — kept here as a teaching contrast)

```
ℹ️ Workflow pup-pack standup — Everest compared PSDLC vs Foggy Bottom Spec Kit on Lookout connector, PSDLC lost:

1. Everest reviewed Tracker's PSDLC-generated Lookout connector on Friday — called it *"cognitively challenging"*, *"fluffy"*, *"bloated"*.
2. Put a Foggy Bottom Spec Kit-generated equivalent of the same code next to it; *"much simpler… much more logical."*
3. Asked Marshall to trial Foggy Bottom Spec Kit on discovery in parallel:
    > *"If Foggy Bottom Spec Kit proves to be easy to adapt, understand, and generate the right quality stuff — why would we invest time on building in-house workflows?"*
4. Chase offered "spec is a liability — flamethrower the bloat before iterating" reframe; Marshall endorsed.
5. Skye (PA pressure-testing Lookout spec) found a lot of missing test scenarios in Tracker's spec — first independent quality-gate finding.


⚠️ Risks:

1. **Workflow ownership now contested on the record.** Everest opening the door to ditching in-house workflows aligns with CP's knowledge-is-the-IP thesis, but the team may keep building something it then swaps out.
2. **Tracker's "designed for complex projects" defense.** Doesn't fit Lookout scope; simplification PR has no commitment date — risk a leaner PSDLC ships right as the spec-kit comparison wins anyway.
3. **Skye findings have no backlog route.** First independent quality finding heard once then lost unless we close the loop into the KB.
4. **Tracker-change disruption pattern.** Third week running of downstream teams regenerating after Tracker ships unannounced — still no release/changelog discipline.
```

## Shipped version (gold standard)

```
ℹ️ Workflow tier updates:
1. Everest is seeing PSDLC for what it is. She compared its output with Foggy Bottom Spec Kit and said "If Foggy Bottom Spec Kit proves to be easy to adapt... why would we invest time on building in-house workflows?". She asked Marshall to trial Foggy Bottom Spec Kit in parallel.
2. Spec bloat still a problem. I steered away from Skill tweaking (diminishing returns) toward aggressive human spec edits. "Every line of spec is a liability - slash and burn bloat before iterating". Endorsed by Marshall/Everest.

⚠️ Risks:
1. Misalignment on current workflow's value. Everest opened the door to ditching PSDLC, but we're still making changes to it. Mayor Goodway/Katie still seem unaware of how little value it adds.
```

## What the user changed

| Change | Lesson |
| --- | --- |
| Headline `Workflow pup-pack standup — Everest compared…` → `Workflow tier updates:` | Topic label is fine for recurring meeting types the channel knows. Substantive event-naming isn't always needed. |
| 5 single-sentence facts → 2 multi-sentence paragraph-clusters | Facts can be short clusters (lead claim + supporting context + inline quote). Not every fact needs to stand alone on one line. |
| `>` nested blockquote → inline `"..."` quote | Inline quotes are usually enough; reserve blockquote for length that warrants its own visual block. |
| Added editorial lead `Everest is seeing PSDLC for what it is.` | Editorial reads are welcome in the Insights block when they ARE the load-bearing signal. The editorialising antipattern only applies inside risks. |
| Added first-person `I steered away from Skill tweaking (diminishing returns)…` | First-person OK when the user's action is the load-bearing fact. Don't disappear yourself from a post about what you did. |
| Cut Skye finding, Tracker defense, regeneration pattern (3 of 4 facts dropped from risks block) | High-value signals only. Lukewarm risks dilute the sharp one. One risk worth posting beats four the channel skims past. |
| Risk bold lead `**Workflow ownership now contested on the record.**` → `Misalignment on current workflow's value.` (no bold) | Bold lead is optional. Use it when it sharpens scanning; skip it when the sentence carries itself. |
| Generic `the team may keep building…` → `Mayor Goodway/Katie still seem unaware…` | Name the specific stakeholders the risk implicates. The lurker test relies on this — anonymous "the team" doesn't tell a lurker who needs to be talked to. |
| `…how invaluable it is` (first user pass) → `…how little value it adds` (after agent catch) | Sense-check semantic-opposite words. "Invaluable" reversed the risk's meaning before catch. |

## Why the shipped version is sharper

- **One load-bearing risk, not four mediocre ones.** The risks block could justifiably have been omitted entirely; the single risk that survived is genuinely sharp and names the specific stakeholders (Mayor Goodway, Katie) whose perception needs managing.
- **Editorial leads do work.** *"Everest is seeing PSDLC for what it is"* is exactly the news. A formal "Everest reviewed Tracker's PSDLC-generated Lookout connector on Friday" buries it under process narration.
- **The user's role is in the post.** *"I steered away from Skill tweaking (diminishing returns)"* is information the channel needs — formal third-person ("Chase offered…") flattens it.
- **Topic-label headline is fine.** The channel knows what *Workflow tier updates* means; explicit event-naming would just add a comma.

## Density delta

- First draft: ~205 words, 5 facts + 4 risks.
- Shipped: ~115 words, 2 fact-clusters + 1 risk.
- Information loss: zero — the load-bearing signals (Everest's public flip, spec-bloat principle, Mayor Goodway/Katie blindspot) all survived. The cut content was real but not channel-worthy.
