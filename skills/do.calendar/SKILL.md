---
name: do.calendar
description: Export dated DeepOrbit Markdown tasks to a portable iCalendar file. Use when the user asks to link tasks to a calendar, export ICS, add reminders, or view due and scheduled tasks in Apple, Google, Outlook, or another calendar app.
---

# Export a Calendar

Run:

```bash
deeporbit --vault "<vault-path>" calendar export
```

The default output is `99_System/Calendar/DeepOrbit.ics`. Each active dated task becomes an all-day event with a stable UID and a display alarm. Re-exporting is deterministic.

Explain that importing an ICS file is normally a snapshot. Automatic calendar updates require the calendar client to subscribe to a refreshed file or a future WebCal service. Do not claim two-way sync and do not request OAuth credentials.
