---
name: do.todo
description: Capture, refine, split, and report portable Markdown tasks with natural-language time parsing. Use when the user says todo, 待办, task, reminder, 提醒, "记一下", "add this", "remind me to...", states any time-bound intention ("今晚七点…", "明天上午…", "每周五…"), dumps a rough list to clean up, asks to break a big task into steps, or wants a progress summary — no slash command required, no external task service.
---

# Manage DeepOrbit Tasks

Use the local CLI so task IDs, dates, and rewrites stay deterministic:

```bash
deeporbit --vault "<vault-path>" todo add "<text>" [--today] [--project "<name>"] \
    [--scheduled YYYY-MM-DD] [--due YYYY-MM-DD] [--time HH:MM] \
    [--priority highest|high|medium|low|lowest] [--recur "<rule>"] [--parent <line-or-id>]
deeporbit --vault "<vault-path>" todo list [--view flat|board|timeline|progress] [--md]
deeporbit --vault "<vault-path>" todo set <id> [--status todo|doing|done|cancelled] \
    [--due YYYY-MM-DD] [--time HH:MM] [--priority <p>] [--recur "<rule>"]
deeporbit --vault "<vault-path>" todo attach <id> <file>
deeporbit --vault "<vault-path>" todo done <id>
```

Default capture goes to `00_Inbox/Todos.md`; `--today` targets today's Daily Note; `--project` targets `20_Projects/<name>.md`. Do not rewrite unrelated text in the containing note. Tasks, Dataview, and Calendar plugins are optional presentation layers; never require them for task operations.

## Capture with natural language

`todo add` parses Chinese and English time expressions out of the text (today/tonight/tomorrow, 上午/晚上 N点, N天后, 周X/每周X, X月X日, in 3 days, 7pm, every Friday, …) and returns the structured result as JSON. **Echo it back for confirmation** before moving on:

```
$ deeporbit todo add "今晚七点跟丽丽吃饭"
→ {"text": "跟丽丽吃饭", "due": "2026-07-25", "time": "19:00", ...}
已录入：跟丽丽吃饭 📅 2026-07-25 ⏰ 19:00
```

When the CLI parser cannot express the semantics, decompose the request yourself and pass explicit flags:

- "提前一小时提醒我" → parse the due time, subtract one hour, pass it as `--time` explicitly.
- "周五之前，最重要的事" → `--due <friday> --priority highest`.
- `#tag` and `!1 !2 !3` priority shorthands are recognized inline.

## Split big tasks

Turn a large task into a parent line plus indented subtasks (CLI `--parent`, or indented checkbox lines in Markdown). Order the subtasks with `⛔ <id>` dependencies when a step blocks another. Progress is derived automatically as `[n/m]` — never hand-write percentages.

## Polish rough input

Convert colloquial dumps ("那个啥，下周之前得把评审材料弄完，还要约会议室") into concrete, actionable tasks, preserving the original meaning. If an item is an idea or thought rather than a commitment, suggest moving it to `30_Research` instead of capturing it as a task.

## Report

Combine `deeporbit agenda` (overdue / today / upcoming / unscheduled) with `todo list --view progress` (per-project n/m and completion rate) and summarize in natural language. Use `--md` when the chat renders Markdown tables.

## Attachments

`todo attach <id> <file>` copies the file into `90_Attachments/` (timestamped on conflict) and appends `![[...]]` to the task line. When the user pastes an image for a task, save it to `90_Attachments/` first, then attach.

## Link tasks to the vault

Reference projects with `#project/<name>` inline or `--project <name>` to file the task into the project note; `[[note name]]` wikilinks inside task text stay live in Obsidian.

## Reminders

The first time the user asks to be reminded at a time ("提醒我", "到点叫我"), guide them through `deeporbit remind install` (see the do.remind skill). Reminders fire only for tasks carrying both `📅` and `⏰`.
