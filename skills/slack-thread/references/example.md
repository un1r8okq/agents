# End-to-end example

Anonymised with Paw Patrol characters and locations. The user is **Ryder**.

Vault state assumed:

- `people/Chase.md`, `people/Skye.md`, `people/Marshall.md`, `people/Rubble.md`, `people/Mayor Goodway.md`, `people/me.md`
- `glossary/Pup Pup Boogie.md`, `glossary/Lookout.md`, `glossary/PupPad.md`
- `orgs/Paw Patrol.md`, `orgs/Adventure Bay.md`

## Input — what the user pastes

User says: "Extract this Slack thread. Permalink https://pawpatrol.slack.com/archives/C12LOOK/p1745798700123456 — channel is #lookout-ops."

```
Ryder  [10:15 AM]
:rotating_light::sparkles: Concerns about the Pup Pup Boogie demo for Saturday (edited) 
4 repliesRyder  [10:17 AM]
The current routine assumes every pup knows the steps. Skye and Rubble haven't trained on the new sequence yet.
[10:19 AM]
Mayor Goodway is bringing the school class — if it falls apart in front of them we'll have a credibility problem.
chase  [10:24 AM]
Agreed — and the Lookout signal is still routing through the old PupPad config. We should test the comms first.
Ryder  [10:30 AM]
@skye can you confirm whether the new sequence has been on the PupPad since the last update?
skye  [11:02 AM]
The update went out last Tuesday but I haven't trained the new pups on it. Can do this afternoon.
```

## Parse decisions

- Date from permalink: `1745798700` → 2025-04-27 (in user's local time, but for this example assume 2026-04-27).
- Display-name resolutions: `Ryder` → `me`, `chase` → `Chase`, `skye` → `Skye`.
- Cruft stripped: `(edited)`, `4 replies`, no image lines present.
- Continuation row at `[10:19 AM]` carries author `Ryder` (→ `[[me|Me]]`).
- Emoji: `:rotating_light:` → 🚨, `:sparkles:` → ✨.
- Concept wikilinks: every occurrence of `Pup Pup Boogie`, `Lookout`, `PupPad`. Person wikilinks: every occurrence of `Skye`, `Rubble`, `Mayor Goodway`.

## Proposed (and confirmed) artefacts

**Filename**: `daily/detail/2026-04-27-pup-pup-boogie-demo-concerns.md`

**H1**: `# Concerns about the [[Pup Pup Boogie]] demo for Saturday`

**Lead sentence**: `On [[2026-04-27]] I flagged concerns about Saturday's [[Pup Pup Boogie]] demo in the [[Paw Patrol]] Slack workspace in #lookout-ops:`

**Daily-note bullet** (consultant-lens): `Flagged risk that Saturday's [[Pup Pup Boogie]] demo could fail in front of [[Mayor Goodway]]'s school class — new sequence not trained, [[Lookout]] comms still on old [[PupPad]] config. See [[2026-04-27-pup-pup-boogie-demo-concerns]].`

## Detail file written

```markdown
---
description: "Slack thread flagging Saturday Pup Pup Boogie demo readiness risks"
---
# Concerns about the [[Pup Pup Boogie]] demo for Saturday

On [[2026-04-27]] I flagged concerns about Saturday's [[Pup Pup Boogie]] demo in the [[Paw Patrol]] Slack workspace in #lookout-ops:

| Person      | Time     | Message                                                                                                                                            | Reacts |
| ----------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| [[me\|Me]]  | 10:15 AM | 🚨✨ Concerns about the [[Pup Pup Boogie]] demo for Saturday                                                                                       |        |
| [[me\|Me]]  | 10:17 AM | The current routine assumes every pup knows the steps. [[Skye]] and [[Rubble]] haven't trained on the new sequence yet.                            |        |
| [[me\|Me]]  | 10:19 AM | [[Mayor Goodway]] is bringing the school class — if it falls apart in front of them we'll have a credibility problem.                              |        |
| [[Chase]]   | 10:24 AM | Agreed — and the [[Lookout]] signal is still routing through the old [[PupPad]] config. We should test the comms first.                            |        |
| [[me\|Me]]  | 10:30 AM | @[[Skye]] can you confirm whether the new sequence has been on the [[PupPad]] since the last update?                                               |        |
| [[Skye]]    | 11:02 AM | The update went out last Tuesday but I haven't trained the new pups on it. Can do this afternoon.                                                  |        |
```

## Daily-note edit

Appended to `# Notes` in `daily/2026-04-27.md`:

```markdown
- Flagged risk that Saturday's [[Pup Pup Boogie]] demo could fail in front of [[Mayor Goodway]]'s school class — new sequence not trained, [[Lookout]] comms still on old [[PupPad]] config. See [[2026-04-27-pup-pup-boogie-demo-concerns]].
```

## Report back to user

> Wrote `daily/detail/2026-04-27-pup-pup-boogie-demo-concerns.md` and appended a summary bullet to `daily/2026-04-27.md`. Reacts column is empty for you to fill. No unresolved mentions; no unrecognised emoji.
