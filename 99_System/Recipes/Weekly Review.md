---
type: recipe
name: Weekly Review
description: Weekly consolidation — survey lifecycle, archive finished work, recap, and let the vault dream
schedule: weekly
author: ai
---

# Weekly Review

Run every week (schedule with `deeporbit cron add weekly-review "Run recipe Weekly Review" --every weekly`).

1. cli: deeporbit --vault . status
2. cli: deeporbit --vault . suggest
3. skill: do.archive
4. skill: do.recap
5. skill: do.dream
6. note: Ask the user which paused item deserves reactivation next week, and record the answer via `profile observe` if it reveals a durable preference.
