# Refresh-person example

Anonymised before/after on a fictional person note showing the Summary + Stated views split. Names use the [[anonymise]] cast.

## Before

```markdown
---
organisation: "[[Adventure Bay Co]]"
role: "Platform Product Lead, Lookout Tower Foundations"
description: "Platform PM for Adventure Bay's Lookout Tower engineering group."
---
# Summary
Skye is platform product lead at Adventure Bay Co.

# My notes
- First met [[2026-04-29]] at the rescue planning workshop ([[2026-04-29-rescue-planning]]).
- Strong views: architectural patterns and observability standards should be *contributed to* the framework but *owned* by the architects who maintain them — not embedded by framework authors. Cited the failed "Adventure Bay way" as a cautionary tale.
- Sees code generation as 10% of the problem; reviewer capacity is the actual constraint when AI-generated PRs scale up.
- Suggested a different model *family* for cross-checking AI-generated code — not just Opus vs Sonnet.
- Open question she raised: AI may push us back from microservices toward monoliths. [[Marshall]] disagreed; offered "miniith" as alternative framing.
- Has prior history with [[Marshall]] (from his earlier years at [[Adventure Bay]]) and [[Chase]].
- Sponsors [[Rocky]]'s tooling team at [[Adventure Bay Co]].
- **At the [[2026-04-29]] [[FDC]] / [[WDF]] accelerated-delivery meeting:** Skye (with [[Rubble]]) pulled [[Marshall]] aside looking for an ally — *"we don't want no part of this. We're about to go live"* (per [[Marshall]]'s recall). Working political ground for [[FDC]] on the side; her on-record questions there were *"on point but not for that meeting"* (per [[Chase]]) — they displaced what should have been a discovery interview.
- **Worth verifying:** repeated a 70% delivery-uplift claim about the [[PupTech]] team — secondhand. Different from other figures floating around. Flag before it lands in any report.

# From LinkedIn
[... career history ...]
```

## After

```markdown
# Summary
Platform product lead in [[Lookout Tower Foundations]] at [[Adventure Bay Co]]; sponsors [[Rocky]]'s tooling team. Prior history with [[Marshall]] (from [[Adventure Bay]]) and [[Chase]]. Currently working political ground for [[FDC]] / [[WDF]] — pulled [[Marshall]] aside at the 2026-04-29 meeting ("we don't want no part of this. We're about to go live"); her on-record questions there were "on point but not for that meeting". Carries a secondhand 70% delivery-uplift claim about [[PupTech]] worth verifying before it lands in any report.

# Stated views
- Architectural and observability standards should be *contributed to* the framework but *owned* by the architects who maintain them, not embedded by framework authors. Cites the failed "Adventure Bay way" as cautionary.
- Code generation is "10% of the problem" — reviewer capacity is the real constraint at scale.
- Cross-checking AI-generated code needs a different model *family* — not just Opus vs Sonnet.
- Open question: AI may push us back from microservices toward monoliths. ([[Marshall]] disagreed; offered "miniith" as alternative.)
```

## What goes where, and why

| Bullet from My notes | Lands in | Why |
|----------------------|----------|-----|
| Sponsorship of Rocky's team | Summary (sentence 1) | Working background — who she backs |
| Prior history with Marshall / Chase | Summary (sentence 2) | Relationship context |
| FDC / WDF political ground; "we don't want no part of this" | Summary (sentence 3) | Live dynamic — affects what she'll say in the room |
| 70% PupTech claim | Summary (sentence 4) | Verification flag — protects future report |
| "Contributed to but owned by architects" stance | Stated views | Position that will shape how she reacts to framework proposals |
| "10% of the problem" framing | Stated views | Problem framing she'll bring to any AI-coding discussion |
| Different model family for review | Stated views | Technical stance she's taken |
| Monoliths vs microservices open question | Stated views | Open question with attribution and rebuttal |
| First-met date | Neither | Episodic; stays in My notes |

## Voice notes

- Summary leads with **working background** — position, sponsorship, relationships, dynamics, flags. Views are deliberately absent here.
- Stated views captures positions in bullet form, scannable, growable over time.
- Load-bearing user phrasings preserved verbatim ("contributed to but owned by", "10% of the problem", "we don't want no part of this", "on point but not for that meeting").
- Wikilinks restored on every vault-entity mention per the vault rule.
- The [[Marshall]] disagreement on the monolith question is preserved — nuance not flattened.
