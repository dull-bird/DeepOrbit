---
type: template
author: ai
---
# {{date}} — Human Loop

Write one question before starting. In the evening, add what you actually did,
what you can explain yourself, tomorrow's first step, and a short life note.
Unknown, no result, and rest are valid answers. Empty fields are not completion.

## My own record

<!-- human-loop:user:start -->
- Main question:
- Personal action and result:
- My understanding and remaining question:
- Tomorrow first step:
- Life feedback:
<!-- human-loop:user:end -->

A two-minute version is enough: one true fact and one small action for tomorrow.
Life feedback can mention sleep, meals, movement, and energy only if you want to.
Do not put confidential work artifacts or sensitive identifiers in this record.

## Agent files

The agent preserves this file and writes separate reports:

- [[{{agent_dir}}/{{date}}-morning]]
- [[{{agent_dir}}/{{date}}-evening]]
- [[{{agent_dir}}/{{date}}-weekly]]

A missing report link is normal until that mode has run. These links, an empty
shell, or an agent summary do not establish that I learned or finished anything.
