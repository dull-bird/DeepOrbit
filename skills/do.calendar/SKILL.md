---
name: do.calendar
description: Export dated DeepOrbit Markdown tasks to a portable iCalendar file. Use when the user asks to link tasks to a calendar, export ICS, or view due and scheduled tasks in Apple, Google, Outlook, or another calendar app.
---

# Export a Calendar

Run:

```bash
deeporbit --vault "<vault-path>" calendar export
```

The default output is `99_System/Calendar/DeepOrbit.ics`. Re-exporting is deterministic, with a stable UID per task.

- Tasks carrying `⏰ HH:MM` export as **timed events** (one-hour DTSTART/DTEND) with a VALARM 10 minutes before start.
- Date-only tasks stay **all-day events** with a 09:00 display alarm.
- Completed or cancelled tasks are excluded.

Set expectations honestly: importing an ICS file is a snapshot, and subscribed-calendar VALARMs are ignored by mainstream clients (Outlook, Apple Calendar, Google Calendar) — the ICS gives **calendar visibility, not reliable alerting**. For actual notifications, point the user to `deeporbit remind install` (do.remind). Automatic updates require the calendar client to subscribe to the refreshed file; do not claim two-way sync and do not request OAuth credentials.
