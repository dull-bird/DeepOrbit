---
name: do.agenda
description: Build a current agenda from DeepOrbit Markdown tasks. Use when the user asks what to do today, what is overdue, what is upcoming, for a task review, or for a daily planning summary across Inbox, Diary, and Projects.
---

# Build an Agenda

Run:

```bash
deeporbit --vault "<vault-path>" agenda
```

Present the returned groups in this order: overdue, today, upcoming, unscheduled. Omit the completed group unless the user asks for a review. Preserve task IDs so the user can complete an item through `do.todo`.

Tasks may carry richer fields — surface them when present:

- `⏰ HH:MM` — an exact time within the due day; order today's timed tasks by it and mention times explicitly in summaries.
- Priority (`🔺⏫🔼🔽⏬`) — list high-priority items first within a group.
- `🔁 every …` — recurring tasks reappear after completion; never treat them as one-off.
- Subtasks — report parent progress as `[n/m]` (derived, see `deeporbit todo list --view progress`); do not flatten subtasks away when the user asks about a project.

When used from `do.daily`, include the agenda without duplicating the same checkbox into the Daily Note. The original Markdown task remains the source of truth.
