---
name: do.research
description: Plan and execute checkpointed deep research for technologies, concepts, papers, or complex questions. Use when the user asks for deep research, a literature review, evidence synthesis, or a durable research note in their DeepOrbit vault.
---

# Deep Research

Produce evidence-backed research while preserving progress in a Markdown plan. Runtime-native goals, trackers, or subagents may accelerate the work but are never required.

## 1. Establish context

1. Run `deeporbit --vault "<vault>" rag "<topic>"` to find related notes. If the CLI is unavailable, inspect `20_Projects`, `30_Research`, and `40_Wiki` directly.
2. Read `99_System/Prompts/Research_Sources.md` when it exists.
3. Identify the question, intended depth, existing knowledge, related project, and output language from `deeporbit.json`.
4. Ask only for choices that materially change the research.

## 2. Create a checkpoint plan

Write `90_Plans/Plan_YYYY-MM-DD_Research_<Topic>.md`:

```markdown
---
deeporbit_workflow: 1
workflow_id: research-<date>-<slug>
status: active
topic: <topic>
---

# Research Plan: <Topic>

## Goal
<Decision or understanding this work must enable>

## Existing knowledge
- Related notes: [[...]]
- Related project: [[...]]

## Checklist
- [ ] Search primary and official sources
- [ ] Search independent secondary sources
- [ ] Compare claims and record contradictions
- [ ] Draft the main research note
- [ ] Extract durable atomic concepts
- [ ] Verify citations, links, and completeness
```

Let the user review the plan when the scope is broad, expensive, or ambiguous. Otherwise continue.

## 3. Execute with checkpoints

- Work through the checklist in dependency order and mark each item immediately after it succeeds.
- Continue in the same turn while context and tool limits allow.
- If interrupted, reread the plan and resume at the first unchecked item.
- When the runtime exposes a Goal or Task Tracker, attach the plan's goal to it. Never store the only copy of progress in runtime state.
- Do not use external self-invocation extensions, headless loops, or completion-promise polling.

Prefer primary sources. For current facts, browse and cite. Record sources beside supported claims and state uncertainty or disagreement explicitly.

## 4. Write durable outputs

- Main note: `30_Research/<Area>/<Topic>/<Topic>.md`
- Atomic concepts: `40_Wiki/<Category>/<Concept>.md`
- Supporting files: `30_Research/<Area>/<Topic>/assets/`

Use frontmatter at line 1 with `type`, `created`, `area`, `tags`, and `status`. Put related links in a final `## Related Reading` section, not frontmatter. Keep atomic concepts focused.

## 5. Verify and finish

Before setting the plan to `status: complete`:

- Every checklist item is checked.
- Major claims have working sources.
- Contradictions and limitations are visible.
- Output files exist at the planned paths.
- Wikilinks resolve or are intentionally marked as future concepts.

- Set `author: ai` in frontmatter for every note you create; switch to `author: mixed` when substantially rewriting a human-authored note. Authorship lives in frontmatter only — never add visible badges.
Link the result from today's Daily Note. Open the main note using `do.obsidian-open`; inability to launch Obsidian is non-fatal.
