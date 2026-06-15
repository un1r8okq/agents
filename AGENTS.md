## Base expectations

The user always wants you to:
- Ask questions to understand context/intent/assumptions
- Suggest potentially unconsidered alternatives
- Treat questions like "should we X?" or "can we Y?" as requests for analysis, not authorisation. Wait for an explicit imperative ("do it", "apply", "go ahead") before making changes. I'm a Kiwi and often phrase proposals as open questions.
- Ask questions via the `AskUserQuestion` tool (the multi-choice picker) rather than inline in chat — even when the natural answer is free-text written prose. Provide 2–4 plausible options; the user can always pick "Other" and type a free-form reply. Batch multiple questions into a single AskUserQuestion call.

## Network access and 403s

The user typically runs Claude Code inside of a [Docker Sandbox](https://docs.docker.com/ai/sandboxes.md) with default deny egress controls. You will get an HTTP 403 if a hostname is not yet on the allow list. Ask the user to allow a host if this happens instead of just moving on.

## Persisting rules and durable guidance

When the user gives durable guidance about how I should work — coaching, behavioural rules, do/don't preferences — **update the relevant skill (`/c/dev/agents/skills/<name>/SKILL.md`) or `/c/dev/agents/AGENTS.md` file**. Do not write the guidance into the auto-memory system. Skills and `AGENTS.md` are the source of truth for how I work; auto-memory is for ephemeral session context only.

## Writing docs

When writing explainer, reference, or rollout docs (audience is usually busy senior engineers or stakeholders):

1. **Lead with the problem to solve, not a topic intro.** Section 1 answers "what's wrong without this" — not "what is X". The "what is X" emerges naturally once the reader knows why they're reading. Gives them an immediate "is this for me" filter.
2. **Lean on external links for well-known background.** Don't reproduce widely-available content (textbook material, industry primers, methodology overviews). Link to authoritative primary sources. Reserve word count for what's *specific to this team / project / moment* — outsource the generic.
3. **Anchor related concepts to a familiar lifecycle.** When a doc covers concepts that map onto a process or workflow (SDLC stages, request lifecycle, incident lifecycle, etc.), structure it around that lifecycle and show where each concept sits — rather than a flat list or table. ASCII pipeline diagrams work well in markdown.

## Knowledgebase

The user keeps extensive structured notes at the path defined by the `$OBSIDIAN_VAULT` environment variable. Refer to these for context on what the user is working on, or to get more info on people (including the user at `$OBSIDIAN_VAULT/people/me.md`), engagements, and organisations. Suggest updating these notes where you learn something that could be useful to add.

**Vault design docs** at `$OBSIDIAN_VAULT/meta/` are the source of truth for vault structure and conventions. Consult `meta/conventions/<area>.md` before non-trivial edits to vault content or to the skills that operate on the vault — skills should reference the conventions, not restate them.

## AI Policy — Hard Rules

These apply in every session. Use the `/policy-check` skill for a full compliance review.
- Never submit Restricted client data (including source code) to any AI tool without explicit prior written client approval — even secure enterprise tools.
- Never use a personal or free AI subscription for any work data.
- AI output from client work is the client's IP; AI output from internal work is the company's IP.
