---
name: do.remind
description: Install and explain DeepOrbit's local reminder delivery for timed Markdown tasks. Use when the user says "remind me", "提醒我", "到点叫我", "定时任务", mentions cron-based reminders, asks why a notification did not fire, or wants macOS notifications for tasks carrying a due date and time.
---

# Remind from Markdown Tasks

DeepOrbit reminders are local and private: a launchd job polls the vault every minute and delivers macOS notifications for due timed tasks. Nothing leaves the machine.

## When to use which mechanism

- **Pure time reminder** ("remind me at 7 to call Alice") → capture the task with `do.todo` (`📅` + `⏰`), then rely on `deeporbit remind`. This covers everything the user can read and complete themselves.
- **Reminder that needs agent work** ("at 5pm draft my weekly report and remind me") → schedule a one-shot agent job instead:

```bash
deeporbit cron add draft-weekly "Run do.daily and draft the weekly report" --at 2026-07-25T17:00
```

An `--at` job fires once, hands the instruction to the configured agent CLI, and auto-disables (kept for audit, not deleted).

## How delivery works

```
launchd (StartInterval 60, fires missed runs after sleep/wake)
  └─ deeporbit remind check --deliver
       ├─ due: 📅 = today, ⏰ ≤ now, task not done, not already delivered
       ├─ alerter (optional, `brew install alerter`): interactive notification
       │    [完成] marks the task done · [稍后] snoozes 10 minutes
       └─ fallback: osascript display notification (zero-dependency banner)
State: ~/.config/deeporbit/reminders.json (delivered / snoozed, idempotent)
```

Only tasks with both `📅 YYYY-MM-DD` and `⏰ HH:MM` trigger notifications; date-only tasks appear in the agenda but never pop up.

## Install and uninstall

```bash
deeporbit --vault "<vault-path>" remind install   # writes ~/Library/LaunchAgents/com.deeporbit.remind.plist and loads it
deeporbit --vault "<vault-path>" remind check --deliver   # manual run, useful for testing
```

There is no `remind uninstall`; the install output prints the exact `launchctl unload` command and plist path to remove it manually.

## Privacy note

Notification banners include the task text. On a shared or screen-recorded machine, keep sensitive wording out of task text or redact before capturing.
