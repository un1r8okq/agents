---
name: obsidian
description: Look up people, organisations, engagements, daily notes, and past context from the user's personal knowledgebase at `$OBSIDIAN_VAULT`, and apply vault conventions to every read or edit there. Use proactively when (a) the user references someone, a company, an engagement, daily note, or ongoing work that isn't obvious from the current directory; OR (b) you read, edit, create, or update ANY file under `$OBSIDIAN_VAULT` — daily notes, detail notes, transcripts, people, orgs, engagements, glossary, misc. Vault conventions are defined below — consult the relevant section before any edits.
---

## Orientation

This vault is **agent-first**: conventions exist for reliable structured reads and edits, not human aesthetic preference. Every design decision prioritises discoverability and graph traversability by an LLM with no long-term memory.

Key principles:
- **Semantic structure over prose.** Frontmatter for typed metadata; wikilinks for relationships; directory placement for entity type.
- **Reliable discovery.** Every entity has a `description:` frontmatter — survey a category by grepping `^description:` across a directory without reading each file.
- **Durable portraits.** Person notes describe *who* someone is and how they operate, not *what they did each day*.
- **Critical lens.** The vault is private working memory — preserve skepticism, dysfunctions, and risks. Do not sanitise into corporate speak.
- **Verbatim where it matters.** Detail notes preserve raw content; never reformat or summarise their bodies.

## Vault structure

| Path | Purpose |
| --- | --- |
| `daily/YYYY-MM-DD.md` | Daily notes — schedule + free-form notes |
| `daily/detail/YYYY-MM-DD-topic.md` | Overflow or multi-person session notes. Verbatim. |
| `daily/transcripts/` | Raw transcripts (Google Meet exports etc.) |
| `engagements/<Engagement>/` | Per-engagement directory (see below) |
| `engagements/<Engagement>/<Engagement>.md` | Engagement overview — thesis, recommendations, background |
| `engagements/<Engagement>/context.md` | Current week's priorities, concerns, risks (refreshed every daily decant) |
| `engagements/<Engagement>/timeline.md` | Chronological day-by-day narrative table |
| `engagements/<Engagement>/decisions.md` | Decision register — open questions + resolved decisions |
| `engagements/<Engagement>/people.md` | Engagement-specific who's who roster |
| `engagements/<Engagement>/glossary/<term>.md` | Engagement-scoped terminology (project codenames, tier names, project-internal tools) |
| `glossary/<term>.md` | Cross-engagement terms, acronyms, tools, project names |
| `misc/<topic>.md` | Reference notes that don't fit other categories |
| `orgs/<Org>.md` | Organisations referenced from other notes |
| `people/<Name>.md` | People Will works with (global — cross-engagement) |
| `todo.md` | Persistent cross-session task list |

Smaller / single-file engagements may still live at `engagements/<Engagement>.md` until they grow enough to justify the directory split. New engagements default to directory shape from day one.

## Discovery model

Grep `^description:` across a directory to scan all entities without reading each file:

```
Grep: pattern="^description:", path="$OBSIDIAN_VAULT/people/"
```

Once a relevant note is found, follow `[[wikilinks]]` to traverse the graph — every mention of a vault entity is wikilinked, so adjacent context is always reachable without guessing filenames.

## Wikilink traversal

When reading a vault note, **proactively follow `[[wikilinks]]` to people, orgs, and engagements relevant to the task** — do not wait to be asked.

**Follow when:**
- The linked entity is a person, org, or engagement and the task involves their context, relationships, dynamics, or history
- The note references someone by name and you need their role, background, or stated views to answer well

**Skip when:**
- The link is incidental (passing mention in a list, date link, glossary term)
- You have already read the target this session

Read multiple linked notes in parallel — don't serialise avoidable round-trips.

## Tool usage

Prefer `Read`, `Glob`, and `Grep` over `Bash` — they are allowlisted and don't require permission prompts.

When `Bash` is needed (e.g. `ls`, `find`), make one call per command. Do not chain with `&&` or `|` — compound commands bypass the user's allowlist.

---

## Conventions

Apply the relevant section before any non-trivial write. These are the authoritative rules — `meta/` in the vault is human documentation only.

### Frontmatter

**Universal rules:**
- All keys **lowercase**.
- After meaningful edits (~10% body added or restructured, new heading, material new claims), reconsider whether `description:` still represents the file. Propose updated description before writing. Skip for trivial edits.
- For person notes, prefer the `refresh-person` skill — it handles `# Summary` and `# Stated views` together and updates `description:` coherently.

**Required fields per directory:**

| Directory | Required | Optional |
| --- | --- | --- |
| `daily/` | (none) | (none) — daily notes carry no frontmatter; an optional `location: office \| client` may be added by hand to surface a Location column in `## Schedule` |
| `daily/detail/` | `description:` | |
| `engagements/<Engagement>/<Engagement>.md` | `client:`, `description:`, `status:` (`active` \| `complete`) | |
| `engagements/<Engagement>/{context,timeline,decisions,people}.md` | `description:` | |
| `engagements/<Engagement>/glossary/` | `full:`, `description:` | |
| `glossary/` | `full:`, `description:` | |
| `misc/` | `description:` | |
| `orgs/` | `relationship:` (`employer` \| `client` \| `partner` \| `vendor`), `description:` | |
| `people/` | `organisation:`, `role:`, `description:` | `joined:` (YYYY-MM-DD), `aliases:`, `mistranscriptions:` |

**Wikilinks in frontmatter:** for entity fields (`organisation:`, `client:`), use full wikilink syntax — `organisation: "[[Adventure Bay Council]]"`. Quote-wrap to avoid YAML parsing issues.

**Description shape:** specific, not generic. Lead with role + org + the load-bearing context distinguishing this entity from siblings.
- ✅ `"Engineering Manager in Rescue Ops, 7 years at ABC. Led AI PoC 2 in the dispatch application."`
- ❌ `"An engineer at Adventure Bay Council."` — too generic to surface in a grep survey.
- **Plain text — no wikilinks.** Spell entity names out; never put `[[wikilinks]]` in `description:`. A wikilink in a free-text frontmatter value creates no Obsidian graph edge, adds noise to the `^description:` survey, and duplicates the body's linking. (Entity-relationship fields `organisation:`/`client:` keep wikilink syntax — see "Wikilinks in frontmatter" above.)

### Wikilinks

**Rule: wikilink every occurrence** of a vault entity (person, org, engagement, glossary term, daily/detail/misc note) — not just the first mention. If Cap appears in five bullets, all five get `[[Captain Turbot|Cap]]`. This enables grep-based queries like "which bullets mention Cap?" across all note types. Linking is a semantic type marker — complete coverage enables reliable relationship traversal by agents and Obsidian's graph view.

**Alias syntax:** always use explicit display-name form `[[Target|Alias]]` — never rely on frontmatter alias resolution:
- ✅ `[[Adventure Bay Council|ABC]]`
- ❌ `[[ABC]]` — an agent reading only the current file can't follow it.

**Missing targets:** you can wikilink a page that doesn't exist yet — the link is unresolved in Obsidian but preserves semantic intent for future stub creation. Do NOT remove existing wikilinks just because the target is missing.

**Headings:** wikilinks in `##` section headings are valid Obsidian syntax and the established pattern.

**Inside markdown links:** do NOT nest wikilinks inside markdown link text — `[plain text](url)` must stay plain.

**Substring caution:** `replace_all` can corrupt substrings (e.g. replacing `Tim` hits `Time`, `sometimes`). Only use `replace_all` when the entity name is unambiguous; otherwise per-occurrence Edits.

### People notes

Files in `people/<Name>.md`. One per person Will works with.

**Required frontmatter:** `organisation:` (wikilinked), `role:`, `description:`.

**Optional frontmatter:** `joined:`, `aliases:`, `mistranscriptions:`.

**Section structure:**

| Section | Purpose |
| --- | --- |
| `# Summary` | Durable bio. Refreshed by `refresh-person` from `# My notes` + `# From LinkedIn`. |
| `# Stated views` | Optional. Positions and stances expressed on record. Refreshed by `refresh-person`. |
| `# My notes` | Personal observations — see shape below. User-owned; never edit silently. |
| `# From LinkedIn` | Professional history + expertise. Generated by the `background` skill. |

**`# My notes` shape — durable portrait, not a tactical event journal:**

1. **Durable opener** — short prose: role, key relationships, what they want, relevant dynamics.
2. **`## Patterns`** — recurring behavioural/strategic observations. One short rule per bullet. Shape:
   `- **<title>.** <one-sentence observation>. Source: [[YYYY-MM-DD]], [[YYYY-MM-DD]].`
   When a new instance of an existing pattern surfaces, **extend the source line** rather than adding a new bullet.
3. **`## Engagement events`** — pointer list to detail notes / daily sections. One line each, no inline content.

**What NOT to do:**
- ❌ Add dated `## <Engagement> YYYY-MM-DD` sub-sections of tactical recap — that belongs in the detail note + engagement timeline.
- ❌ Inline blow-by-blow meeting content in person notes.
- ❌ Duplicate a pattern bullet for each new instance — extend the source line.

Genuinely new pattern *frames* (not just new instances) may warrant a named sub-section under `## Patterns` — name it for the frame, not the date.

### Daily notes

Files in `daily/YYYY-MM-DD.md`.

**Frontmatter:** none. Daily notes carry no frontmatter by default. The `update-daily-schedule.py` hook maintains the `## Schedule` table from Google Calendar regardless. An optional `location: office | client` may be added by hand to make the schedule table include a Location column; a missing or `home` location omits it.

**Template:**
```
# Notes
## <Topic or meeting>
```

**Splitting rule:** extract any `##` subsection from `# Notes` to a detail note if EITHER:
- (a) it exceeds ~20 lines, OR
- (b) it captures an event involving **3+ vault people** (even if shorter — multi-person events otherwise duplicate the same content across person notes).

Replace the extracted section with a 1–2 sentence summary bullet + wikilink to the detail note. Preserve existing reference bullets verbatim; only add a new analytical bullet where none exists.

**`# Summary` section:** decanted notes have a `# Summary` at the very top. Apply a critical consultant's lens — subtext, skepticism, dysfunctions, risks. Its presence signals the note has been decanted.

### Detail notes

Files in `daily/detail/YYYY-MM-DD-topic-name.md`. Date prefix ties the note to its parent daily.

**Required frontmatter:** `description:`.

**Standard shape:**
```markdown
---
description: ""
---

Present:
- [[Person A]]
- [[Person B]]

Summary:
<analytical paragraph>

Notes:
- <verbatim bullet>
```

**Verbatim rule:** never summarise or reformat the body — `description:` and `Summary:` are the only places for analytical compression. Agents downstream rely on the raw signal.

If a detail note outgrows its origins and becomes a standalone reference, promote to `misc/<topic>.md`.

### Engagement notes

Engagements live in a per-engagement **directory** at `engagements/<Engagement>/`, containing the main note plus companion files. Smaller engagements may still live as a single file `engagements/<Engagement>.md`, but new and active engagements default to directory shape.

**Directory layout:**

| File | Purpose |
| --- | --- |
| `<Engagement>.md` | Engagement overview — durable thesis, recommendations, background. Folder note (Obsidian recognises the same-named file as the folder's main note). |
| `context.md` | Current week's priorities, active concerns / risks, watching items, recently-resolved decisions. **Refreshed every daily decant.** |
| `timeline.md` | Chronological day-by-day narrative table. The file that grows fastest. |
| `decisions.md` | Decision register — open questions and resolved decisions. |
| `people.md` | Engagement-specific who's who roster (table form). |
| `glossary/<term>.md` | Engagement-scoped terminology — project codenames, tier names, internal tools. Globally-applicable terms stay in top-level `glossary/`. |

**Required frontmatter — main `<Engagement>.md`:** `client:` (wikilinked), `description:`, `status: active | complete`.
**Required frontmatter — companion files (`context.md`, `timeline.md`, `decisions.md`, `people.md`):** `description:`.

**Main `<Engagement>.md` structure:** durable strategic content — thesis, emerging recommendations, phase narrative, background context. **Not** the timeline or current-state content (those live in companion files).

**`context.md` shape:**
- Sections: `## This week's priorities`, `## Active concerns / risks`, `## Watching`, `## Recently resolved`.
- Lead with a `*Last refreshed: [[YYYY-MM-DD]]*` line.
- Items move out of `## Recently resolved` into `timeline.md` or `decisions.md` as they age past current-week relevance.

**`timeline.md` row format:**
```
| YYYY-MM-DD | **<headline>.** <prose summary with [[wikilinks]] to people, decisions, detail notes>. See [[YYYY-MM-DD]]. |
```

**`decisions.md` shape:**
- `## Open questions` — sub-bulleted by topic (strategic, technical, process etc.).
- `## Resolved decisions` — table: `| Date | Decision | Notes |`.

**Engagement-scoped glossary — what belongs there:**
- ✅ Project codenames, internal tools, tier/stream names ([[workflow-tier]], [[safety-tier]]), engagement-coined acronyms ([[MVR]]).
- ❌ Cross-engagement terms (those stay in top-level `glossary/`): general concepts ([[RAG]], [[SDLC]], [[DORA metrics]]), org-wide tools/products ([[Manhattan]], [[FDC]], [[Apigee]]), broad initiatives ([[WDF]]).
- Heuristic: if a future engagement might also use the term, keep it global. If it dies when the engagement ends, scope it.

**Cross-references:** link out to detail notes for verbatim content; link out to person notes for who's involved; cite the daily at the end of each `timeline.md` row.

**Wikilink resolution from outside the engagement directory:** Obsidian resolves `[[term]]` by filename across the whole vault. From outside, link engagement-scoped content with the bare term (e.g. `[[workflow-tier]]`) as long as the filename is unique. If two engagements have files with the same name (e.g. both have `context.md`), use path-prefix form: `[[DSO2/context]]`.

### Org notes

Files in `orgs/<Org>.md`.

**Required frontmatter:** `relationship: employer | client | partner | vendor`, `description:`.

**Body:** lead with what the org does; note the relationship with Will / ClearPoint where relevant; link to engagements, people, and key projects.

**When to create:** any organisation referenced from another vault entity, even if only as someone's employer — it's the link target that enables graph traversal.

### Glossary entries

Files in `glossary/<term>.md`.

**Required frontmatter:** `full:` (expanded form; empty string if not an abbreviation), `description:`.

**Body:** 1–3 sentence definition; 2–4 context bullets (key relationships, where used, who owns it); links to related entries, engagements, and people.

**When to create:** abbreviations/acronyms used more than once; tools/standards relevant to ongoing engagements; terms-of-art with non-obvious meaning.

**Cross-link from usage:** the wikilink-every-mention rule means glossary entries get linked wherever the term appears. Entries should also link back to engagements/people that originated or use them — bidirectional traversal.

### Misc notes

Files in `misc/<topic>.md`.

**Required frontmatter:** `description:`.

**When to use:** reference-shaped content not tied to a specific day; standalone topics that have outgrown a detail note; lookups, framings, or playbooks cited from other notes.

**Linking rule:** misc notes **must be linked from at least one other page** — they are not orphan documents. If a misc note has no inbound links, either delete it, link it from the relevant entity, or promote to a more specific category.

---

## Setup & Troubleshooting

If you encounter errors accessing the vault, run the setup checker:
`~/.agents/skills/obsidian/scripts/check_setup.sh`

If `$OBSIDIAN_VAULT` is not set, advise the user to add `export OBSIDIAN_VAULT="/path/to/your/vault"` to their shell profile (`~/.bashrc` or `~/.zshrc`).
