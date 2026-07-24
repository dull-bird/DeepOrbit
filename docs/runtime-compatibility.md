# Runtime compatibility reference

## Shared contract

All runtimes consume `skills/do.*/SKILL.md`. The `description` triggers automatic selection; the body specifies the workflow. Paired files in `commands/do/` provide native command compatibility where supported.

## Kimi Code

`kimi.plugin.json` registers repository Skills, commands, MCP, and fail-open hooks. The experimental Goal can mirror a long workflow, but its Markdown checkpoint remains authoritative.

The CLI fallback needs no plugin registry:

```bash
kimi --skills-dir /path/to/DeepOrbit/skills
```

## Gemini and Antigravity

`gemini-extension.json` registers context and MCP. Gemini command TOML files and hook configuration are included. Plan Mode and the task tracker can mirror workflow progress.

For local development, link the checked-out repository (Gemini validates this manifest):

```bash
gemini extensions link /path/to/DeepOrbit
```

## OpenClaw

Install Skills into a workspace `.agents/skills` root or use the repository as an external skill source. Native Goal is appropriate for one durable session objective; it is not a replacement for recurring tasks or Markdown checkpoints.

The portable installation is a plain directory copy or symlink—one folder per
skill—rather than an OpenClaw-specific package:

```bash
mkdir -p .agents/skills
cp -R /path/to/DeepOrbit/skills/do.* .agents/skills/
```

## Claude Code

Claude Code reads project `CLAUDE.md` files automatically. This repository's
`CLAUDE.md` imports `DeepOrbitPrompt.md`, so the canonical context is loaded
without relying on plugin installation.

When the plugin is enabled, `hooks/hooks.json` also injects the same context on
session startup, resume, and compaction, and marks the local index dirty after
`Write`, `Edit`, or `Bash`.

## OMP

OMP discovers native TypeScript hooks under `.omp/hooks/pre/*.ts`. This
repository's `.omp/hooks/pre/deeporbit.ts` injects `DeepOrbitPrompt.md` through
the `before_agent_start` event. OMP also supports explicit `--hook` and
`--append-system-prompt` overrides.

## Codex

Codex reads the repository `AGENTS.md` automatically. Full DeepOrbit context is
added by either `.codex/hooks/hooks.json` for a trusted checkout or the
plugin's `.codex-plugin/hooks/hooks.json` when the plugin is enabled and its
hooks are trusted.

- `SessionStart` emits the full `DeepOrbitPrompt.md` content plus vault status
  through `hookSpecificOutput.additionalContext`.
- `PostToolUse` marks `cache/dirty` after write/edit/shell actions and emits a
  short created/modified/deleted file summary for tracked note files, so the
  next local CLI run can refresh and the agent sees what changed.

Codex plugin hook commands resolve from `${PLUGIN_ROOT}`; checkout hooks resolve
from the Git root, so neither depends on the current working directory.

## Fallback behavior

When a runtime lacks commands, invoke the Skill by name or natural language.
When it lacks MCP, invoke the local CLI. When it lacks automatic prompt loading,
read `DeepOrbitPrompt.md` at session start and continue from Markdown checkpoints.

