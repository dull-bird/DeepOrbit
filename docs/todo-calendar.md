# Tasks and calendar

Use DeepOrbit tasks when you want task data to remain editable and syncable as Markdown. The design rationale (storage format, research behind each choice) lives in [Todo system design](todo-system.md); this page is the operator's guide.

## Task format

One line per task, Tasks-plugin emoji fields, everything optional except the text:

```markdown
- [ ] 跟丽丽吃饭 📅 2026-07-25 ⏰ 19:00 ➕ 2026-07-24 ^do-20260724a1
- [ ] 准备季度评审 🔺 📅 2026-07-28 #project/工作 ^do-20260724b2
  - [ ] 整理数据 📅 2026-07-26 ^do-20260724c3
- [ ] 每周五写周报 🔁 every week on Friday 📅 2026-07-31 ^do-20260724e5
```

| Field | Syntax | Notes |
|---|---|---|
| Status | `[ ]` `[x]` `[/]` `[-]` | todo / done / doing / cancelled |
| Priority | `🔺⏫🔼🔽⏬` | highest / high / medium / low / lowest |
| Due | `📅 YYYY-MM-DD` | deadline day |
| Time | `⏰ HH:MM` | exact reminder point, combined with `📅` |
| Scheduled | `⏳ YYYY-MM-DD` | planned start day, separate from due |
| Created | `➕ YYYY-MM-DD` | written automatically on add |
| Done | `✅ YYYY-MM-DD` | written automatically on done |
| Recurrence | `🔁 every …` / `… when done` | strict schedule / from completion |
| Project | `#project/name` or `[[note]]` | links the task into vault projects |
| Depends | `⛔ <id>` | blocked-by, used when splitting tasks |
| Attachment | `![[90_Attachments/…]]` | renders inline in Obsidian |
| ID | `^do-<id>` | stable block ID for done/attach/remind |

Bare checkbox lines without any fields parse fine (legacy ID synthesized); completing one backfills `✅` and a block ID automatically.

## Capture with natural language

```bash
deeporbit --vault /path/to/vault todo add "今晚七点跟丽丽吃饭"
# → {"text": "跟丽丽吃饭", "due": "2026-07-25", "time": "19:00", ...}
deeporbit --vault /path/to/vault todo add "每周五写周报"        # → 🔁 recurrence
deeporbit --vault /path/to/vault todo add "Draft proposal" --project Proposal --priority high
deeporbit --vault /path/to/vault todo add "整理数据" --parent ^do-20260724b2
```

Chinese and English time expressions (今天/明晚/N天后/每周X/in 3 days/7pm/every Friday) are stripped from the text by a zero-dependency parser; explicit flags override parsing. Inbox capture goes to `00_Inbox/Todos.md`; `--today` writes to the current Daily Note; `--project` writes to the named project note.

## Review, update, complete

```bash
deeporbit --vault /path/to/vault agenda
deeporbit --vault /path/to/vault todo list --view progress --md
deeporbit --vault /path/to/vault todo set <id> --status doing --due 2026-07-28
deeporbit --vault /path/to/vault todo attach <id> ~/Desktop/report.pdf
deeporbit --vault /path/to/vault todo done <id>
```

Views: `flat` (default JSON), `board` (by status), `timeline` (overdue → today → future), `progress` (per-project n/m plus subtask counts). Completion changes only the checkbox carrying the requested stable ID.

## Reminders

```bash
brew install alerter                                  # optional: interactive notifications
deeporbit --vault /path/to/vault remind install       # launchd polls every minute
```

A launchd agent runs `deeporbit remind check --deliver` every minute (missed runs fire after sleep/wake) and notifies for tasks where `📅` is today and `⏰` has passed. With alerter, [完成] marks the task done and [稍后] snoozes 10 minutes; without it a plain osascript banner shows. Delivery state lives at `~/.config/deeporbit/reminders.json` and is idempotent. There is no uninstall subcommand — the install output prints the `launchctl unload` command and plist path.

For reminders that need an agent to do work (not just notify), schedule a one-shot job instead: `deeporbit cron add <name> "<instruction>" --at 2026-07-25T19:00` — it fires once and auto-disables.

Privacy: notification banners include the task text.

## Obsidian dashboard

`99_System/Todo Dashboard.md` (seeded by `deeporbit init`) renders Overdue / Today / Upcoming 7 days / all tasks grouped by folder / unscheduled Inbox items with Tasks-plugin query blocks; `show tree` keeps subtask hierarchy. The plugin is optional — without it, `deeporbit agenda` and `todo list --view progress` cover the same ground.

## Export calendar events

```bash
deeporbit --vault /path/to/vault calendar export
```

`99_System/Calendar/DeepOrbit.ics` contains one event per active dated task with a stable UID. Tasks with `⏰` export as one-hour timed events with a VALARM 10 minutes before start; date-only tasks stay all-day with a 09:00 display alarm. Import is a snapshot, and subscribed-calendar VALARMs are ignored by mainstream clients — treat the ICS as calendar visibility, not a reminder mechanism. DeepOrbit does not modify Google Calendar, Apple Calendar, or Reminders accounts.
