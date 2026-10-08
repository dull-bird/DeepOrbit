---
type: protocol
author: ai
---
# Human Loop protocol

Use the configured finite trial and timezone. Ask the user to confirm reminder
hours, channel, and the single scheduling device before registering jobs. The
shared example starts disabled and has no scheduling owner.

The user writes `paths.daily_dir/YYYY-MM-DD.md` from either synced device. Morning
preparation creates only a missing shell. Never rewrite an existing user file.
Agent reports belong only in `paths.agent_dir/YYYY-MM-DD-{mode}.md`; read an
existing report before writing, and avoid repeated whole reports.

Read this protocol, a user-approved plan or source if explicitly configured,
and the seven dated check-ins listed by the helper. Do not search the whole
vault, import chats, read email or sensors, or silently update a profile. Do not
assume that missing feedback means failure: it may not have synced yet.

Morning: give one main question, one short action, and one expected result. Let
the user choose and write the final question. Rest and low-energy days may use
the two-minute version. Keep this separate from the full `do.daily` news flow.

Evening: ask what the user personally advanced, what they can independently
explain or still do not understand, and tomorrow's first step. Combine optional
life feedback into one line. If feedback is absent, record only the gap; never
fabricate personal progress, sleep, meals, or emotion. At most one follow-up
question, with the user answering before the agent gives the answer.

Weekly: replace that day's evening reminder. Review only dated user evidence,
state gaps, propose a small adjustment, and choose one question to test retained
understanding. A short record is valid; there is no character score or streak
penalty. Trial expiry stops scheduled work and does not authorize an extension.

`missing`, `awaiting`, `partial`, and `recorded` describe receipt of inputs, not
learning or task completion. Explicit user completion/rest can be recorded;
never infer it from file existence, silence, authorship metadata, or an AI report.
Generated shells/reports use `author: ai`; when the user substantially adds their
own writing the shell may be marked `mixed`. Feedback checks use only the marked
user block, irrespective of authorship metadata.

Private detail stays in the vault. Final chat reminders contain only generic
recording questions, date, and a note link. This is an output rule, not automatic
redaction: any configured remote model that reads the notes receives their
contents. `privacy_level` does not automatically protect arbitrary agent reads.
Keep record contents within the user's approved processing scope.

Only the bound primary device matching the shared owner runs scheduled work.
Sync is neither instantaneous nor a distributed lock. Avoid editing the same
file simultaneously on two devices; check sync before switching devices.
Do not copy local bindings, channel recipients, databases, locks, or indexes.

Check the deterministic gate before a model call and check `prepare` again in
payloads. Exit 3 is an intentional quiet refusal; exit 2 is an operational error.
Never bypass a scheduled guard using `--dry-run`. Forced OpenClaw manual runs
skip native triggers, so the second check is mandatory. Skip missed windows;
do not send delayed morning reminders or fabricate missed entries.

Report runtime/file/delivery errors honestly. A model's generic error reply may
be considered a successful turn by the runtime; do not use scheduler success as
proof of diary preparation. Native failure alerts have per-job cooldowns, not
a shared global daily limit. Never add repeated prompts after no response.

Normal DeepOrbit heartbeat remains read-only. This recipe is a separately
user-authorized daily workflow, not permission for a heartbeat to write notes.
