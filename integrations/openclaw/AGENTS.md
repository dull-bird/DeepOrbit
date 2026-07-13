# DeepOrbit on OpenClaw

Load DeepOrbit Skills from the repository `skills/` directory or install them into the workspace `.agents/skills` root. Keep Markdown checkpoint files authoritative. When a workflow is long-running, attach its objective to the native OpenClaw Goal but resume work from the first unchecked checkpoint after restarts.

Register `mcp/deeporbit_rag/server.py` only when Python MCP dependencies are available. Without MCP, call the `deeporbit` CLI or follow the Skill's direct Markdown fallback.

Hooks are optional optimizations. A session hook may run `deeporbit doctor`; a file-change hook may mark local retrieval state dirty. Do not automatically commit, push, or rewrite notes from a hook.
