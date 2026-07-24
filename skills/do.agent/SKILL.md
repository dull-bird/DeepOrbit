---
name: do.agent
description: Detect agent CLIs installed on this machine (omp, claude, gemini, codex), let the user pick one for DeepOrbit to hand execution to, and show the current configuration. Use when the user wants to connect/configure an agent CLI, asks which agents are available, mentions ACP/RPC/-p mode handoff, or asks to see the current agent status.
---

# Agent — Local Agent CLI Configuration

DeepOrbit prepares context (prompts, vault state, cron instructions) and hands
execution to an agent CLI on the machine. This skill detects what is
installed, asks the user to choose, persists the choice in `deeporbit.json`
(`agent:` section), and reports status.

## Modes

| Mode | Meaning | Best for |
|------|---------|----------|
| `acp` | Agent Client Protocol over stdio, streaming | dashboard chat, interactive runs |
| `rpc` | NDJSON RPC (omp only: `omp --mode rpc`) | programmatic pipelines |
| `print` | one-shot `-p` / `exec` | cron jobs, batch handoff |

## Workflow

1. **Detect:**

   ```bash
   deeporbit --vault . agent detect [--versions]
   ```

   Lists every known agent (omp, claude, gemini, codex), whether it is
   installed, where, and which modes it supports.

2. **Ask the user which agent to use.** Use the runtime's native ask form
   (e.g. an interactive question with one option per *installed* agent).
   Present name, description, and supported modes. Recommend the agent that
   supports `acp` when the user wants the dashboard assistant; `print` for
   pure automation. If only one agent is installed, confirm instead of asking.

3. **Configure:**

   ```bash
   deeporbit --vault . agent configure <name> [--mode acp|rpc|print]
   ```

   Omitting `--mode` picks the preferred one automatically (`acp` > `rpc` >
   `print`). The choice is validated (installed + mode supported) and saved to
   `deeporbit.json` — it syncs with the vault as a preference; detection
   always runs live.

4. **Status:**

   ```bash
   deeporbit --vault . agent status
   ```

   Shows the configured agent, whether it is actually available on this
   machine (`available: false` means the config synced to a machine without
   that CLI — suggest re-configuring), and the full detection table.

## Where the configuration is used

- `deeporbit --vault . serve` — the dashboard assistant connects through the
  configured agent's ACP mode when `--agent auto` (the default).
- `deeporbit --vault . cron run-due` — due-job instructions are meant to be
  handed to the configured agent; `agent status` shows the exact `argv`.
- The dashboard's 助手 view has an Agent 配置 panel that calls the same
  `/api/agent/config` endpoints.

## Guardrails

- NEVER configure an agent that detection says is not installed — tell the
  user how to install it instead.
- The `agent:` section in `deeporbit.json` is a preference, not machine
  state; never treat it as proof the CLI exists — always check `available`.
- `agent clear` removes the configuration; the dashboard then falls back to
  auto-detection order (omp → claude → gemini).
