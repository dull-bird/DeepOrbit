# OpenClaw Human Loop: daily records across synced devices

This opt-in [example](../examples/human-loop/) composes DeepOrbit Recipes with
OpenClaw's scheduler. It adds no core configuration keys, model clients, or new
skills. The user writes the daily record; the agent prepares and reflects in a
separate directory. Only one explicitly designated device schedules reminders.
The example starts **disabled**, has no owner, and contains no live delivery route.

## Install the portable parts

Use Python 3.10+ on macOS or Linux. The helper uses the standard library and the
system IANA timezone database. A Python installation without that database needs
`tzdata`; unavailable timezones fail closed. Hardware binding is implemented for
macOS and Linux, not Windows.

Keep executable code and local bindings outside the synced vault. From this
repository, copy `examples/human-loop/human_loop.py` to
`~/.local/share/deeporbit-human-loop/human_loop.py`. Copy these **data** files
into an initialized vault. Adapt the helper’s data paths to the configured
directories, except for the recipe location described below:

| Example file | Vault destination |
| --- | --- |
| `human-loop.example.json` | `99_System/DeepOrbit/human-loop.json` |
| `DailyCheckIn.md` | `99_System/Templates/HumanLoop.md` |
| `Protocol.md` | `99_System/DeepOrbit/HumanLoop.md` |
| `Recipe.md` | `99_System/Recipes/HumanLoop.md` |

Use `deeporbit --vault "<vault>" about` to inspect directory semantics. The
standalone helper accepts both legacy string directory paths and schema-v3
`{path: ...}` entries. Extension paths remain vault-relative; update them when
renaming directories. Current core recipe discovery uses the fixed
`99_System/Recipes` directory; keep `Recipe.md` there even when the configured
system directory has another name. Do not insert extension fields into
`deeporbit.json`.

Set the extension's `vault_id` to the existing vault ID, choose timezone, finite
trial dates, times and allowed weekdays with the user, and leave `enabled: false`.
The sample dates are deliberately inactive examples. Times must be exact `HH:MM`;
weekdays use Python numbering (Monday=0, Sunday=6).

Bind each device with its own path. Begin with secondary role if no scheduling
owner has been selected:

```bash
python3 ~/.local/share/deeporbit-human-loop/human_loop.py bind \
  --vault "<this device's vault path>" --role secondary
```

`bind` prints the device-local configuration path, creates it exclusively, and
never changes the shared owner. The local configuration holds role, absolute
vault path, random `device_id`, and a hardware hash. Do not copy or sync it.
To designate a primary, set **that device's local** role to `primary`, set the
shared `scheduler_owner` to its `device_id`, and enable the shared extension only
after validating the intended scheduler. This owner value is durable configuration,
not a synced lock or lease; copied local bindings fail the hardware check.

```bash
python3 ~/.local/share/deeporbit-human-loop/human_loop.py \
  --config "<local binding.json>" status
python3 ~/.local/share/deeporbit-human-loop/human_loop.py \
  --config "<local binding.json>" prepare --mode morning --dry-run --date YYYY-MM-DD
deeporbit --vault "<vault>" recipe run "Human Loop"
```

Replace `YYYY-MM-DD` with a date within the configured trial. Preview ignores the
time window but still checks owner, role, hardware, trial, weekday and enablement;
it writes nothing. A date override without `--dry-run` is refused.

## Register one scheduler

The example recipe has no `schedule` field. Register it in OpenClaw only, rather
than creating a second DeepOrbit cron or launchd reminder. Confirm the user's
private channel and destination, then use an explicit timezone and stable
`--declaration-key` containing the vault ID and mode. Inspect existing jobs first;
update a matching declaration instead of creating another job.

For the sample configuration:

| Mode | Cron | Effective window |
| --- | --- | --- |
| morning | `0 9 * * *` | 09:00–09:25 |
| evening | `0 20 * * 1,2,3,4,5,6` | 20:00–20:30, Monday–Saturday |
| weekly | `0 20 * * 0` | 20:00–20:30, Sunday instead of evening |

Adapt all three expressions if the shared schedule changes. Cron uses Sunday=0,
unlike the helper's weekday numbering. Do not run the same cadence from both Macs.

OpenClaw 2026.9.6 provides native condition scripts that can run the deterministic
guard before a model call. See its [schedule/trigger documentation](https://docs.openclaw.ai/automation/cron-jobs/schedules).
An example **morning gate** is below; substitute locally bound, properly shell-quoted
paths. The condition script is copied into the registered job, not watched as a
live file:

```javascript
const r = await exec({
  command: "python3 '<local helper.py>' --config '<local binding.json>' gate --mode morning",
  timeoutSeconds: 15,
});
if (r.status !== "completed") throw Error("Human Loop gate did not finish");
if (r.exitCode === 3) {
  json({ fire: false });
} else if (r.exitCode !== 0) {
  throw Error("Human Loop runtime or vault unavailable");
} else {
  const g = JSON.parse(r.aggregated);
  const slot = g.date + ":" + g.mode;
  json({
    fire: g.allowed === true && trigger.state?.slot !== slot,
    state: { slot },
  });
}
```

Successful fired occurrences persist the slot in OpenClaw's **device-local**
trigger state. Intentional quiet evaluations skip the model. Configuration/runtime
errors should throw rather than masquerade as silence; do not parse a nonzero
exec result as plain JSON because native exec can append exit-status text.

Register initially disabled, using flags supported by the installed version:

```bash
openclaw cron add --name human-loop-morning \
  --declaration-key "human-loop:<vault-id>:morning" \
  --cron '0 9 * * *' --tz Asia/Hong_Kong --exact --disabled \
  --agent '<agent-id>' --session isolated --light-context \
  --tools exec,read,write --trigger-script '<local morning gate.js>' \
  --message '<instruction to prepare, read the configured protocol, and execute morning mode>' \
  --announce --channel '<private channel>' --to '<verified personal destination>'
```

The real payload instruction must start by running `prepare --mode morning` with
the same local helper/config, inspect `status/exitCode/aggregated`, and stop with
`NO_REPLY` on an intentional refusal. Never use preview to bypass the guard.
Then follow only the helper's validated `reference_paths`, `recent_days` and
`agent_path`. Give evening/weekly jobs the corresponding mode and gate. Cap
execution duration and tool scope. Keep final chat text generic: private details
stay in notes and the scheduler sends only the final reminder once. Review the
[payload](https://docs.openclaw.ai/automation/cron-jobs/payloads) and
[delivery](https://docs.openclaw.ai/automation/cron-jobs/delivery) contracts for the
installed version; flags and script runtimes can change.

Forced `cron run` bypasses a native trigger, making the payload's second guard
mandatory. Use a no-delivery diagnostic to verify actual Gateway file access and
native exec result shapes before enabling, and verify a generic delivery only
with an approved personal recipient. Do not claim end-to-end delivery from
registration or helper unit tests alone.

## Record ownership and receipt

Morning preparation exclusively creates a missing shell. It never changes an
existing daily file. Template tokens include `{{date}}`, `{{previous_date}}`,
`{{weekday}}`, `{{daily_dir}}` and `{{agent_dir}}`. The configured fields between
`human-loop:user:start/end` are the only source for feedback receipt. Obsidian
wikilinks can be valid evidence pointers. Helper stdout contains metadata, never
field values or the hardware identifier.

| State | Meaning |
| --- | --- |
| missing | No daily file is visible locally |
| awaiting | User fields are empty or placeholders |
| partial | Some fields are filled, including a two-minute record |
| recorded | All five configured fields have values |

These states do **not** prove learning or completion. `unknown`, no result, and
rest can be honest answers. Agent output, an empty shell, silence, and file
existence must not substitute for the person's own input. The sample protocol
keeps morning/evening short, replaces the weekly day's evening check, and requires
one independent user answer before an explanation.

This is a specifically authorized recipe, not permission for ordinary
`do.heartbeat` to write notes. A semantic WHEN rule can refer to missing user
feedback, but the core heartbeat gate does not implement this example's predicate.
Avoid duplicate reminders from that route.

## Sync, access and failure handling

- Sync Markdown, the template, protocol, recipe and extension settings. Keep local
  bindings, recipient addresses, OpenClaw storage, locks and indexes outside the vault.
- When the primary has not received another device's update, say it has not seen
  the record yet. Never conclude that the user did nothing. The agent preserves
  the user's file, but filesystem sync still cannot guarantee conflict-free
  simultaneous editing; wait for sync before switching devices.
- To move scheduling: stop the old jobs, change shared owner and the new local role,
  verify sync, then enable on the new device. There is no automatic failover.
- A sleeping/offline machine cannot notify. Missed windows and expired trials
  refuse scheduled work; resume from today's actual record, without invented logs.
- Verify file access from the **Gateway process**, not just the installing shell.
  macOS background services can need separate authorization for iCloud-protected
  files. Ask the user at the permission step; do not alter TCC or silently grant
  broader disk access. If access is blocked, keep jobs disabled and document the gap.
- Record operational errors. Native alert cooldowns are per job; a model's generic
  error reply can still count as a successful turn. A successful run is not proof
  that a record exists or that delivery succeeded.
- Shared `enabled: false` pauses work once synced to the primary. Immediate local
  pause disables its jobs. Expiry stops model calls without extending the trial.

## Verify the optional example

```bash
python3 -m unittest discover -s examples/human-loop -p 'test_*.py' -v
PYTHONPATH=src python3 -m unittest discover -s tests -p test_human_loop.py -v
```

Tests use isolated temporary vaults and no messages, models or live schedulers.
They cover one-owner/multiple-device behavior, copied binding refusal, path and
symlink boundaries, renamed directories, trial/window limits, exclusive shell
creation, multiline/placeholder receipt, and preserving existing user bytes.
They run with the repository's normal unittest discovery as well.
