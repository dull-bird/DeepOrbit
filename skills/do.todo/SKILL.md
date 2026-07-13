---
name: do.todo
description: Capture, list, and complete portable Markdown tasks across a DeepOrbit vault. Use when the user says todo, task, reminder, add this to today, mark something done, or wants temporary daily tasks without depending on an external task service.
---

# Manage DeepOrbit Tasks

Use the local CLI so task IDs and dates remain deterministic:

```bash
deeporbit --vault "<vault-path>" todo add "<text>" [--today] [--project "<name>"] [--scheduled YYYY-MM-DD] [--due YYYY-MM-DD]
deeporbit --vault "<vault-path>" todo list
deeporbit --vault "<vault-path>" todo done <task-id>
```

Default capture goes to `00_Inbox/Todos.md`; `--today` targets today's Daily Note; `--project` targets `20_Projects/<name>.md`.

Tasks use standard Markdown checkboxes, `#task`, Tasks-compatible date markers, and a stable `^do-...` block ID. Do not rewrite unrelated text in the containing note. Tasks, Dataview, and Calendar plugins are optional presentation layers; never require them for task operations.
