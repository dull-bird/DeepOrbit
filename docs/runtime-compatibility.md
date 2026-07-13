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

## Codex

The repository includes `.codex-plugin/plugin.json`, Skills, MCP, and hooks. Standalone filesystem Skills remain the most portable installation path across Codex surfaces.

For a checkout without a configured marketplace, expose the same source folders in
the workspace or user Skill directory. The plugin manifest is for Codex plugin
installations; it is not required to read or execute the portable Skills.

## Fallback behavior

When a runtime lacks commands, invoke the Skill by name or natural language. When it lacks MCP, invoke the local CLI. When it lacks Goal or hooks, continue from the checkpoint file.
