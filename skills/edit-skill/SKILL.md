---
name: edit-skill
description: Always invoke this skill whenever you need to edit, create, or review a skill. It contains important rules and guidelines.
---

1. Follow the specification at `./resources/specification.md` closely. It contains important rules and guidelines that ensure your skill is effective and compatible with the system.
2. **The `description` field determines whether the skill is surfaced — write it to match the user's words, not yours.** Name the entities, tasks, and triggers a user will reference (e.g. "look up people, orgs, engagements") and include a "Use when..." or "Use proactively when..." clause. Avoid meta phrasings like "Outlines how agents interact with X" or "Helps with X" — the skill won't surface on real queries. Sanity check: would the user's natural wording of the task match a keyword in the description?
3. Focus on content that is not in your training data: context and direct learnings from your work on this project.
4. Keep it concise and machine readable. Avoid fluff words and repeating yourself.
5. Add anonymized real examples, but put full examples in `./references` so that agents can choose to load them optionally. Examples are useful, but can pollute the body and context window. **Always anonymize examples** using the `anonymise` skill.
6. After updating a skill, consider it holistically and consider refactoring its structure to make it more effective.
