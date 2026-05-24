# Example: end-to-end transcript processing

## Input

User says: "Read daily/transcripts/2026-05-18-paw-patrol-ops-standup-transcript.md, then add a short summary and analysis to daily/detail/2026-05-18-paw-patrol-ops-standup.md"

## Step 2: Name-resolution table built

From `people/` directory, `aliases:` grep, and known mistranscriptions table:

| Transcript name | Vault person | Source |
| --- | --- | --- |
| Ryder | Ryder Goodway | filename |
| Chase | Chase Hubble | filename |
| Marshal | Marshall Porter | known mistranscription |
| Sky | Skye Flyer | known mistranscription |
| Rocky | Rocky Recycle | filename |

## Step 3: Participants identified

From speaker labels in transcript: Ryder, Chase, Marshal (→ Marshall), Sky (→ Skye).

## Step 5: Detail note written

```markdown
---
description: "Ops standup — bridge permit blocked by Humdinger's lobbying, Rocky's drone grounded by retaliatory airspace complaint"
---
Full transcript: [[2026-05-18-paw-patrol-ops-standup-transcript]]

Present:
- [[Chase Hubble|Chase]]
- [[Marshall Porter|Marshall]]
- [[me|Ryder]]
- [[Skye Flyer|Skye]]

Summary:

Two blockers converging on the same political obstruction from [[Mayor Humdinger|Humdinger]] — bridge permit and drone airspace. [[Chase Hubble|Chase]] escalating to [[Mayor Goodway|Goodway]] directly.

## Bridge permit

Third week stuck with [[Mayor Goodway|Goodway]]'s office. [[Chase Hubble|Chase]] suspects [[Mayor Humdinger|Humdinger]] lobbying against it through the regional council. [[Skye Flyer|Skye]] corroborated via [[Everest Walker|Everest]] at the mountain base.

**Risk:** if permit doesn't clear by June, east-side emergency response adds **40 minutes** via [[Foggy Bottom]] detour. [[Marshall Porter|Marshall]]'s new ladder truck routing demo is also blocked — depends on the bridge.

## Rocky's drone

[[Rocky Recycle|Rocky]]'s prototype grounded after [[Mayor Humdinger|Humdinger]] filed an airspace complaint. [[Skye Flyer|Skye]]: *"the complaint is retaliatory."*

## Action items

- **[[Chase Hubble|Chase]]:** escalate permit to [[Mayor Goodway|Goodway]] directly this week

## Analysis

**Two independent [[Mayor Humdinger|Humdinger]] obstructions in the same week is a pattern, not a coincidence.** The bridge lobbying and the airspace complaint are separate mechanisms targeting different projects — suggests a coordinated campaign rather than opportunistic blocking. Worth checking whether [[Mayor Humdinger|Humdinger]] has line of sight to other active projects.

The 40-minute [[Foggy Bottom]] detour is the load-bearing risk — it degrades response times for the entire east side, not just bridge-adjacent calls. If [[Chase Hubble|Chase]]'s escalation to [[Mayor Goodway|Goodway]] doesn't move by mid-week, consider going directly to the regional council with the emergency-response impact data.
```

## Step 6: Daily note bullet appended

```markdown
- [[Mayor Humdinger|Humdinger]] blocking both bridge permit and [[Rocky Recycle|Rocky]]'s drone via separate mechanisms — coordinated campaign pattern. [[Chase Hubble|Chase]] escalating to [[Mayor Goodway|Goodway]]. See [[2026-05-18-paw-patrol-ops-standup]].
```

## Step 7: Report

- Written: `daily/detail/2026-05-18-paw-patrol-ops-standup.md`
- Appended bullet to `daily/2026-05-18.md`
- Unresolved names: none
- Known-mistranscription resolutions applied: "Marshal" → [[Marshall Porter]], "Sky" → [[Skye Flyer]]
