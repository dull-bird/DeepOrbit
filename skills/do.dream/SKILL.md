---
name: do.dream
description: Let the vault "dream" — an offline consolidation pass that self-organizes knowledge. Use when the user asks to consolidate, self-learn, dream, promote patterns to Wiki, find hidden connections, or when a cron job triggers the dreaming workflow.
---

# Dream — Vault Self-Consolidation

Dreaming is the vault's sleep cycle: without user input, review recent activity,
surface patterns, and prepare small consolidation proposals. The vault wakes up
smarter; the user only approves.

## Inputs (deterministic, collect all first)

```bash
deeporbit --vault . status                    # lifecycle state
deeporbit --vault . suggest                   # open issues
deeporbit --vault . index ensure              # fresh retrieval before searching
deeporbit --vault . profile show              # what matters to the user
find 00_Inbox 10_Diary 15_Writings 20_Projects 30_Research 60_Notes -name '*.md' -mtime -7
```

## Consolidation passes

Work through these in order; skip any that finds nothing.

1. **Pattern promotion (Zettelkasten layer).** Cluster the recent notes by
   theme. When 2+ notes independently circle the same concept, draft one atomic
   Wiki note (`40_Wiki/<Concept>.md`, `author: ai`, linked from both sources).
   Drafts are *proposals* — present them before writing.
2. **Hidden connections.** For each recent note, run
   `deeporbit --vault . rag "<its core claim>"` and list the top existing notes
   it should link to but doesn't. Propose the exact wikilinks.
3. **Lifecycle nudges.** Turn `suggest` output into decisions: which `done`
   items to archive, which dormant `active` items to pause, which stale
   `paused` item to revive. Reference real paths.
4. **Profile learning.** If recent activity reveals durable traits (recurring
   topics, preferred formats, working hours), record them:
   `deeporbit --vault . profile observe "<text>" --source agent`. This step
   writes immediately — it is append-only and source-tagged.
5. **Recipe gaps.** If the user repeatedly ran the same ad-hoc sequence this
   week, propose capturing it as `99_System/Recipes/<Name>.md`.

## Dream report

Write `10_Diary/dreams/YYYY-MM-DD.md` with `author: ai`:

```markdown
---
type: dream
author: ai
created: YYYY-MM-DD
---
# Dream YYYY-MM-DD

## Promotions proposed   (concept → sources)
## Connections proposed  (note → wikilinks)
## Lifecycle decisions   (path → archive/pause/resume)
## Profile observations  (recorded)
## Recipe proposals
```

Present the report and ask which proposals to apply. Human approval is the
wake-up gate: except for profile observations and the report itself, NOTHING is
written, moved, or linked without confirmation.

## Scheduling

Recommend once (if no cron job exists):

```bash
deeporbit --vault . cron add dream "Run the do.dream consolidation workflow" --every daily
```

The registry is device-local; the user wires it to their agent runtime's
scheduler or system cron (`deeporbit cron run-due` reports due jobs).

## Rules

- Read `deeporbit.json` for the interaction language; folder paths stay in English.
- Set `author: ai` on the dream report and any proposed note; `author: mixed` when substantially rewriting a human note.
- Dreaming is consolidation, not creation: never invent facts; every proposal must cite the vault paths it derives from.
- Keep the report short — it is a review artifact, not a second recap. `/do:recap` covers what happened; dreaming covers what it *means*.
