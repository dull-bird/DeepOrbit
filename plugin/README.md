# DeepOrbit Obsidian Plugin

A thin, LLM-free Obsidian companion for DeepOrbit vaults. It reads and writes
the same plain Markdown as the `deeporbit` CLI — no provider keys, no network
calls.

## Features

- **Work status board** (right sidebar, ribbon icon `orbit`): every note with a
  `status:` frontmatter field, grouped by `active | paused | done | archived`,
  with AI/human authorship markers and one-click transitions (⏸ ▶ ✓).
- **Commands**: pause / resume / mark done / archive the current note.
  Archiving uses the same layout and no-overwrite guarantee as the Python core
  (`99_System/Archive/<Bucket>/<YYYY>/`, inbox by year-month).

The canonical dashboard remains `99_System/Bases/Work Status.base`; this plugin
is for people who want buttons instead of Bases.

## Build & test

```bash
npm ci
npm test        # unit tests for the lifecycle logic
npm run build   # produces main.js
```

## Install (development)

Symlink or copy this folder into `<vault>/.obsidian/plugins/deeporbit`, run
`npm run build`, then enable "DeepOrbit" under Settings → Community plugins.
