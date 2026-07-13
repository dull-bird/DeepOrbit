# Getting started with DeepOrbit

This tutorial takes a new user from an empty folder to a working vault with local retrieval and tasks.

## Requirements

- Obsidian desktop
- Python 3.10 or newer
- One Agent Skills runtime

## Install

```bash
git clone https://github.com/dull-bird/DeepOrbit.git
cd DeepOrbit
python3 -m pip install -e .
```

Install the Skills with `npx skills add dull-bird/DeepOrbit`, or enable the native Kimi, Gemini, OpenClaw, or Codex package described in [runtime compatibility](runtime-compatibility.md).

## Initialize and diagnose

```bash
deeporbit --vault ~/Documents/MyVault init
deeporbit --vault ~/Documents/MyVault doctor
```

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
