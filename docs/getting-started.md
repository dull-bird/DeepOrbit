# Getting started with DeepOrbit

This tutorial takes a new user from an empty folder to a working vault with local retrieval and tasks.

## Requirements

- Obsidian desktop
- Python 3.10 or newer
- One Agent Skills runtime

## Install

Install only the connector skill globally, then install the deterministic CLI
once on the machine:

```bash
npx skills add dull-bird/DeepOrbit --skill do.link --global --agent '*' --yes
git clone https://github.com/dull-bird/DeepOrbit.git ~/src/DeepOrbit
python3 -m pip install -e ~/src/DeepOrbit
deeporbit __schema
```

`deeporbit __schema` is the agent-readable command reference. A checkout can
also run the CLI without installation:

```bash
PYTHONPATH=~/src/DeepOrbit/src python -m deeporbit __schema
```

## Initialize and diagnose

```bash
deeporbit --vault ~/Documents/MyVault init --source ~/src/DeepOrbit
deeporbit --vault ~/Documents/MyVault doctor
deeporbit link add main ~/Documents/MyVault --description "Personal research and writing"
```

`init` is safe to re-run on an existing vault. It preserves notes and customized
system files, migrates legacy localized folders only when safe, materializes
workflow skills into `99_System/DeepOrbit/skills/`, and copies a curated
runtime bundle into `99_System/DeepOrbit/repo/` while excluding `.git`,
virtualenvs, caches, build outputs, `node_modules`, and generated agent install
directories.

Open the folder as an Obsidian vault. Enable the core Bases, Graph View, Backlinks, Daily Notes, and Canvas plugins. Community plugins are optional.

## Add knowledge and retrieve it

Create a Markdown note under `40_Wiki` or `30_Research`, then run:

```bash
deeporbit --vault ~/Documents/MyVault rag "a phrase from the note"
```

The first query creates a machine-local lexical index. Later queries update only changed files and remove deleted files.

## Add a task

```bash
deeporbit --vault ~/Documents/MyVault todo add "Try do.research" --today --due 2026-07-15
deeporbit --vault ~/Documents/MyVault agenda
```

You now have a portable task in Markdown. Install Obsidian Tasks for a richer UI, or continue using DeepOrbit without it.
