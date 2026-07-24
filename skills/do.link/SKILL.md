---
name: do.link
description: Connect the current workspace to an existing DeepOrbit Obsidian vault elsewhere on disk and run its workflows by natural language. Use when the user wants to link or register a vault path, work on a vault outside the current directory, or triggers vault actions (daily plan, recap, research, todo, agenda, search, rag, note capture, translation…) while the current folder is not the vault.
---

# Link a DeepOrbit Vault

A DeepOrbit vault is self-contained: `deeporbit init` materializes every workflow into `99_System/DeepOrbit/skills/` plus a `skills-index.json` trigger index. This skill is the only one an external workspace needs to install — it registers vaults, resolves which one to use, and routes natural-language requests to the workflows stored inside the vault.

Recommended system-level install:

```bash
npx skills add dull-bird/DeepOrbit --skill do.link --global --agent '*' --yes
```

Do not install the entire DeepOrbit skill pack into every project by default. The vault copy under `99_System/DeepOrbit/skills/` is the project-level workflow catalog after `deeporbit init --source <repo>`.

If the `deeporbit` executable is unavailable, run `PYTHONPATH=<repo>/src python -m deeporbit …` instead.

## 1. Link

```bash
deeporbit link add <name> <vault-path> --description "<what this vault is for>"
deeporbit link route "<natural-language request>"
```

Always establish a description at link time: ask the user what the vault is for (work projects, personal research, a specific client…) and pass it as `--description` (default source is `user`). If the user skips it, derive an initial one yourself from `deeporbit.json`, the folder structure, and a skim of recent notes, and save it with `--source agent`.

`deeporbit link route` is the machine-level helper for ambiguous cases. Use the request text to pick the best vault from the registry, then route the rest of the work through `--vault @name`.

Manage links:

```bash
deeporbit link list                                # all links, markers, descriptions, default
deeporbit link default <name>                      # set the default vault
deeporbit link describe <name> "<text>" [--source agent]
deeporbit link remove <name>
```

The registry is device-local (`~/.config/deeporbit/links.json`); it never syncs with the vault.

## 2. Route to the right vault

A machine may have several linked vaults. Choose the target by matching the user's request against each link's `name` and `description` — that is what descriptions are for:

- Request clearly matches one vault's purpose (e.g. a work task vs. a work vault) → use it and state the choice.
- Only one link, or a default exists and nothing contradicts it → use it.
- Genuinely ambiguous → ask once, then remember the choice for the session.

Pass the vault to every CLI call as `--vault @<name>` (or the absolute path).

## 3. Route the request

1. Read `<vault>/99_System/DeepOrbit/skills-index.json` and match the user's intent to a workflow by its `description`.
2. Read that workflow's `<vault>/99_System/DeepOrbit/skills/<name>/SKILL.md` — including its `reference/` or `scripts/` files when the skill points to them. The vault copy is the source of truth, version-pinned to that vault.
3. Execute the workflow with `<vault>` as the workspace root: all file reads/writes use absolute paths inside `<vault>`; all CLI calls pass `--vault @<name>`.
4. Vault has no materialized skills (initialized before this feature) → fall back to `<vault>/DeepOrbitPrompt.md` plus direct `deeporbit --vault @<name> <command>` calls, and suggest running `do.init` to materialize the workflows.

## 4. Keep descriptions learning

Descriptions should get sharper with use:

- After workflows that reveal what a vault actually holds (recap, research, organize), refine its description and save it via `deeporbit link describe <name> "<text>" --source agent`.
- NEVER overwrite a description whose `description_source` is `user` without explicit user confirmation — propose the refined wording instead.
- When the user asks to update a vault's purpose, save with the default `--source user`.
- Better routing is the goal: a description should name the vault's domain, audience, and what belongs there versus other linked vaults.

## Guardrails

- NEVER write outside the linked vault; the only external writes are the device-local link registry and the vault's local indexes under the OS cache directory.
- Always state which vault handled the request.
- Do not treat the current directory as a vault unless the user explicitly says so.
