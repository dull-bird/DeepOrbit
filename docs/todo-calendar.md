# Tasks and calendar

Use DeepOrbit tasks when you want task data to remain editable and syncable as Markdown.

## Capture

```bash
deeporbit --vault /path/to/vault todo add "Call Alice" --scheduled 2026-07-14 --due 2026-07-15
deeporbit --vault /path/to/vault todo add "Draft proposal" --project Proposal
```

Inbox capture goes to `00_Inbox/Todos.md`. `--today` writes to the current Daily Note. `--project` writes to the named project note.

## Review and complete

```bash
deeporbit --vault /path/to/vault agenda
deeporbit --vault /path/to/vault todo done <task-id>
```

Completion changes only the checkbox carrying the requested stable ID.

## Export calendar events

```bash
deeporbit --vault /path/to/vault calendar export
```

The generated `99_System/Calendar/DeepOrbit.ics` contains one all-day event per active dated task, a stable UID, and a display alarm. Import is a snapshot unless the calendar application supports refreshing a local subscription. DeepOrbit 2.0 does not modify Google Calendar, Apple Calendar, or Reminders accounts.
