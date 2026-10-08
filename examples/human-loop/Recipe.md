---
type: recipe
name: Human Loop
description: User-authored daily check-ins with separate agent reports and one designated scheduling device
author: ai
---
# Human Loop

No `schedule` field: use one external scheduler, not a duplicate DeepOrbit cron.

1. note: Read the configured Human Loop protocol and shared extension settings; confirm mode and trial dates.
2. note: Scheduled runs first use the device-local deterministic guard; do not invoke a model on intentional silence.
3. note: Read only the approved protocol, sources and seven dated check-ins returned by prepare.
4. note: Let the user record their own question, action/result, understanding, next step and optional life feedback.
5. note: Write agent preparation/reflection only in the separate Agent directory; never overwrite the user check-in.
6. note: On weekly mode replace the evening reminder, test one retained idea, and distinguish evidence from inference.
7. note: Deliver one generic reminder; treat missing local feedback as a possible sync gap and stop after trial expiry.
