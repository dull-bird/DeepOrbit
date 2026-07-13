---
name: do.kickoff
description: Convert an idea or Inbox note into a structured DeepOrbit project. Use when the user wants to start, scope, or turn an idea into a project with a reviewable plan and C.A.P. project note.
---

# Kick Off a Project

Keep the workflow portable. Use the current runtime's native Goal or Tracker when it
exists, but keep the Markdown plan as the durable source of truth. Do not require
subagents or an external self-invoking loop.

## 1. Resolve input and context

Accept an Inbox path, inline idea, or—when no input is given—offer the notes in
`00_Inbox/`. Read `deeporbit.json` for paths and language. Search related context with:

```bash
deeporbit --vault "<vault-path>" rag "<project subject>"
```

If semantic search is unavailable, use `deeporbit ... rag --lexical-only` or the
runtime's file search. Identify overlapping projects before creating a duplicate.

## 2. Write a reviewable plan

Create `90_Plans/Plan_YYYY-MM-DD_Kickoff_<ProjectName>.md` containing:

- source and one-sentence goal;
- related notes/projects and a merge recommendation when overlap is high;
- Area, estimated scale, constraints, phases, and success criteria;
- only the clarification questions that materially affect execution.

Open it with `do.obsidian-open` when available. Ask for confirmation before turning
the plan into a project note because this step can reorganize the user's Inbox.

## 3. Execute the confirmed plan

Create `20_Projects/<ProjectName>.md` for a small project or
`20_Projects/<ProjectName>/<ProjectName>.md` for a larger one. Use frontmatter:

```yaml
---
title: Project Name
type: project
created: YYYY-MM-DD
status: active
area: "[[AreaName]]"
due:
priority: P2
tags: [project]
---
```

Use C.A.P. sections: **Context**, **Actions**, and **Progress**. Link it from today's
Daily Note. Move the completed plan to `90_Plans/Archive/`. For an Inbox source, set
`status: processed` and `archived: YYYY-MM-DD`, then move it to
`99_System/Archive/Inbox/YYYY/MM/` without overwriting an existing file.

Report created and moved paths plus the next concrete action. Opening a note through
Obsidian is useful but never a condition for success.
