---
name: do.teach-me
description: Export DeepOrbit vault knowledge into the user's Teach Me learner vault with provenance tagging. Use when the user wants to import/sync vault knowledge into teach-me, grow their knowledge tree from existing notes, or asks about 联动 teach-me / 导入知识库 / learner portrait from vault content.
---

# Teach Me — Vault Knowledge Export

DeepOrbit and [teach-me](https://github.com/dull-bird/teach-me-skill) are
siblings: DeepOrbit manages the knowledge vault; teach-me turns work into a
learner portrait and knowledge tree. This skill exports vault knowledge into
teach-me **with provenance** — imported notes carry an `origin` block so they
never mix with knowledge teach-me accumulates natively.

## Workflow

1. **Check teach-me is installed.** The bridge needs `teach_me.py`. Resolution
   order: `--script` flag → `$TEACH_ME_SCRIPT` → common install locations
   (`~/.claude/skills/teach-me/…`, `~/.agents/…`, `~/.codex/…`, `~/.omp/…`).
   If missing, tell the user to install teach-me-skill first.

2. **Confirm scope with the user.** Default export dirs are knowledge-only:
   `40_Wiki`, `60_Notes`, `30_Research`. Opt-in additions: `15_Writings`,
   `20_Projects`. `70_Family` is private — export it only on explicit request.
   Read-only zones (e.g. `60_Notes/微信读书`) are always skipped: the upstream
   sync owns them.

3. **Run the export:**

   ```bash
   deeporbit --vault . teach-me export [--dirs 40_Wiki 60_Notes 30_Research 15_Writings]
   ```

   The command stages the notes, runs `teach_me.py import --source obsidian`,
   and returns JSON: `origin` (provenance block), `prompt_for_ai`
   (distillation instructions), `deeporbit.exported_notes`, and teach-me's
   `note_paths`/`text_preview`.

4. **Distill into teach-me.** Follow `prompt_for_ai`: for each important
   knowledge point, call teach-me's `capture` or `assess` — and pass the
   `origin` object **verbatim at the top level** of every payload. This is
   what keeps imported knowledge distinguishable (note frontmatter gets
   `origin: import`, `imported_from`, `import_id`; concept state and
   knowledge-tree nodes store the block; provenance is first-wins).

5. **Report.** Summarize: how many notes were exported, which dirs, the
   `import_id`, and how many knowledge points were captured/assessed. Suggest
   a re-export cadence (e.g. monthly, or after big research pushes) — repeat
   imports are safe because teach-me skips its own `type: teach-me/*` notes
   and merges concepts by title.

## Guardrails

- NEVER drop the `origin` block from capture/assess payloads after an export.
- NEVER export read-only zones or `70_Family` unless the user explicitly asks.
- The export reads the vault; it writes nothing into it.
