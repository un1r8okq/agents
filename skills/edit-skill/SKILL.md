---
name: edit-skill
description: Always invoke this skill whenever you need to edit, create, or review a skill. It contains important rules and guidelines.
---

1. Follow the specification at `./resources/specification.md` closely. It contains important rules and guidelines that ensure your skill is effective and compatible with the system.
2. Focus on content that is not in your training data: context and direct learnings from your work on this project.
3. Keep it concise and machine readable. Avoid fluff words and repeating yourself.
4. Add anonymized real examples, but put full examples in `./references` so that agents can choose to load them optionally. Examples are useful, but can pollute the body and context window. **Always anonymize examples** using the `anonymise` skill.
5. After updating a skill, consider it holistally and consider refactoring its structure to make it more effective.
