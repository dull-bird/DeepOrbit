# Multi-vault routing and memory draft

## Problem
DeepOrbit already treats a vault as the authoritative workspace, but a machine can host multiple vaults. If routing is vague, agents will:

- write to the wrong vault
- read the wrong memory namespace
- mix work, personal, research, and client context
- lose the ability to explain which vault handled a request

The system needs a clear boundary between:

- machine-level routing metadata
- vault-level authoritative content
- session-level ephemeral context

## Goals

1. Support multiple linked vaults on one machine.
2. Route each request to one vault deterministically.
3. Keep memory and retrieval isolated by vault by default.
4. Allow a shared connector or runtime install once per machine.
5. Make the chosen vault visible and auditable.

## Non-goals

- Do not create a global shared memory pool across vaults.
- Do not merge indexes from multiple vaults by default.
- Do not make a runtime-specific engine the source of truth.
- Do not require re-installing the full skill pack into every workspace.

## Proposed model

### 1. Machine-level registry
Keep a device-local registry at `~/.config/deeporbit/links.json`.

Each entry should store:

- `name`
- `path`
- `description`
- `description_source` (`user` or `agent`)
- `last_used_at` or similar routing metadata
- optional tags such as `work`, `personal`, `lab`, `archive`

The registry only answers: “which vault should handle this request?”
It should not store vault content.

### 2. Vault-level autonomy
Each linked vault remains self-contained:

- `DeepOrbitPrompt.md`
- `99_System/DeepOrbit/skills/`
- `99_System/DeepOrbit/skills-index.json`
- `99_System/DeepOrbit/repo/`
- vault-local indexes, caches, recap outputs, and cron state

Vaults do not share derived state unless the user explicitly opts in.

### 3. Session-level pinning
Once a session selects a vault, that choice should stay fixed until the user changes it.
This prevents a work conversation from drifting into a personal vault mid-stream.

## Routing precedence

1. Explicit `--vault @name`
2. Explicit absolute vault path
3. Semantic match against link descriptions
4. Default vault
5. Ask once if still ambiguous

The request should always resolve to exactly one vault before any write.

## Memory boundaries

### Default behavior
- Capture observations only into the selected vault.
- Keep retrieval scoped to the selected vault.
- Keep per-vault lifecycle, recap, and consolidation separate.

### Optional behavior
If the user wants a cross-vault overview, expose it as a separate read-only command or report.
That output must label the source vault on every hit.

### Hard rule
Never silently copy facts from one vault into another.

## What to borrow from agentmemory

### Borrow
- hook-driven auto-capture
- memory lifecycle / decay / consolidation
- hybrid retrieval (lexical + vector + graph)
- replay / audit trail
- `doctor` / diagnostics flow
- transcript import for existing history

### Do not borrow
- a central memory service as the default truth layer
- runtime lock-in to a single engine
- unbounded global recall across vaults

## Suggested implementation shape

```mermaid
flowchart LR
  U[User request] --> R[Resolve vault]
  R -->|@name / path / description / default| V[Selected vault]
  V --> L[Load vault-local prompt + skills]
  L --> A[Run workflow]
  A --> I[Update vault-local indexes]
  A --> M[Update machine registry metadata]
```

## File responsibilities

### Existing files that already match the model
- `src/deeporbit/links.py` — machine-local vault registry
- `src/deeporbit/cli.py` — `--vault @name` resolution and routing
- `skills/do.link/SKILL.md` — routing rules and description learning
- `src/deeporbit/vault.py` — vault initialization and materialization
- `src/deeporbit/schema.py` — machine-readable CLI surface

### Files that may need future adjustments
- link registry metadata if richer routing hints are needed
- any per-vault index/cache naming if global and local caches overlap
- any memory or recap command that should explicitly scope to the selected vault

## Suggested contract additions

### `deeporbit link add`
- validate vault initialization state
- record a useful description at creation time
- preserve user-authored descriptions unless the user explicitly changes them

### `deeporbit link list`
- show name, path, description, and default state
- help the agent choose a vault by purpose

### `deeporbit --vault @name ...`
- resolve through the registry before filesystem access
- fail clearly if the link is missing or ambiguous

### `deeporbit doctor`
- report whether the registry exists
- report whether the selected vault is initialized
- report whether the vault has materialized workflows
- report whether runtime prompt loading is available

## Proposed per-vault policy

| Scope | Stored where | Shared across vaults? |
|---|---|---|
| Registry entries | machine config | yes |
| Vault content | vault | no |
| Workflow catalog | vault | no |
| Local index/cache | vault or cache dir keyed by vault | no |
| Default selection | machine config | yes |
| Session pin | runtime memory only | no |

## Risks

### 1. Description drift
If descriptions get stale, routing gets worse.

Mitigation:
- let agents refine `agent`-authored descriptions after successful work
- never overwrite `user` descriptions without confirmation

### 2. Cross-vault contamination
If a global memory layer is too eager, facts leak between vaults.

Mitigation:
- default to per-vault namespaces
- require explicit opt-in for any cross-vault read

### 3. Ambiguous links
If several vaults share similar descriptions, routing becomes guessy.

Mitigation:
- ask once and remember the answer for the session
- encourage sharper descriptions during `link add`

### 4. Over-centralization
If the registry grows too clever, it starts becoming a second knowledge base.

Mitigation:
- keep the registry small
- keep content in vaults
- keep derived state local

## Rollout sketch

### Phase 1: Routing
- tighten vault descriptions
- confirm default-vault behavior
- standardize `@name` resolution messages

### Phase 2: Isolation
- verify all derived state stays vault-local
- ensure indexes and recap outputs are namespaced
- confirm session pinning behavior

### Phase 3: Memory improvements
- add hook-driven capture if needed
- add lifecycle / decay / consolidation rules
- add replay or audit support

### Phase 4: Optional cross-vault view
- build a read-only overview surface
- label all results by vault
- keep opt-in explicit

## Acceptance criteria

- A machine can have multiple linked vaults.
- The agent can pick the correct vault from name, description, or default.
- A session can stay pinned to one vault.
- Writes stay within the selected vault.
- Derived state remains isolated by vault unless explicitly shared.
- The system can explain which vault handled a request.

## Summary
The right shape for DeepOrbit is:

- **machine-level routing**
- **vault-level autonomy**
- **session-level pinning**
- **no default global memory merge**

That keeps the system local-first and avoids the classic multi-vault failure mode: context bleed.
