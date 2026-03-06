---
name: do.start-my-day
description: Daily planning - review most recent diary, plan today, connect projects. News: per-site summaries in 50_资源/新闻/YYYY-MM-DD, then one combined summary in the daily note.
---

You are the Daily Planner. Review the **most recent daily note** (latest `10_日记/YYYY-MM-DD.md` before today), create today's note, connect tasks to projects. Keep steps strict so behavior is stable.

---

# 1. Get context

- **Today**: `date "+%Y-%m-%d"`.
- **Most recent note**: In `10_日记/`, find the latest `YYYY-MM-DD.md` with date **< today**. Read it; extract unchecked `- [ ]` and what was worked on.
- **Active projects**: `20_项目/` with `status: active`; note phase, pending tasks, last update.
- **Inbox**: Count files in `00_收件箱/`.

---

# 2. News (strict order — every URL gets a summary)

**2.1 URLs**
From the most recent daily note, read **## News sources** (one URL per line). If missing or empty, use `99_系统/模板/News_sources_default.md`.

**2.2 Fetch**Run the fetch script (every URL must be requested):

- Unix: `bash scripts/fetch_news_sources.sh "10_日记/[most-recent-date].md"`
- Windows: `.\scripts\fetch_news_sources.ps1 "10_日记\[most-recent-date].md"`
  Save stdout to a temp file or keep in context. The script outputs blocks `=== URL ===` then raw content; match each URL to its block.

**2.3 Per-site summary (required for every URL)**Create folder `50_资源/新闻/YYYY-MM-DD/` (today’s date). For **each** URL in the list, in order:

- Write one file: `50_资源/新闻/YYYY-MM-DD/[label].md`. Use a short label from the URL (e.g. domain: `jiqizhixin`, `tldr-ai`, or `01`, `02`).
- Content: 4–6 bullet points summarizing that site’s fetched content; each item `[标题](原文链接)` and one line of summary. If fetch failed for that URL, write that in the file.
- Do not skip any URL: same number of files as URLs.

**2.4 Unified summary for the diary**
After all per-site files are written, write the daily note’s **新闻摘要** section: for **each** source, include 2–3 highlights (or link to `[[50_资源/新闻/YYYY-MM-DD/xxx]]`). Every site must appear; no random subset.

---

# 3. Ask user (short)

1. "今天的主要目标是什么?" (active projects + 其他)
2. "有什么新想法或任务吗?"
3. "有什么阻碍或顾虑吗?"

---

# 4. Today’s daily note

- Path: `10_日记/YYYY-MM-DD.md`. If missing, create from `99_系统/模板/Daily_Note.md`.
- **## News sources**: If the note has no such section or it’s empty, add it and paste the default list from `99_系统/模板/News_sources_default.md`. Else leave as is.
- Fill:
  - **待办事项**: Carryover from most recent note + user focus + project next actions.
  - **日志**: Leave empty.
  - **备注**: Time-sensitive items, stale projects, inbox count.
  - **新闻摘要**: The unified summary from 2.4 (every site covered).
  - **相关项目**: Active projects with status.

---

# 5. New ideas (Q2)

For each new idea: if new, create `00_收件箱/[Brief-Title].md` with frontmatter `created`, `status: pending`, `source: start-my-day`.

---

# 6. Present (Chinese)

Short summary: 今日笔记, 待办列表, 进行中项目, 收件箱数, **新闻摘要** (each source 1–2 lines or link to `50_资源/新闻/YYYY-MM-DD`), 快捷操作 `/do:kickoff` `/do:research`.

---

# Rules

- Most recent note = latest date in `10_日记/` before today.
- News: one summary file per URL in `50_资源/新闻/YYYY-MM-DD/`; then one combined 新闻摘要 in the diary covering every site.
- If no note before today: skip carryover and news; start fresh.
- Today’s note exists: merge, don’t overwrite. Add ## News sources only when missing.

# Template

Daily note format: `99_系统/模板/Daily_Note.md`. Fetch script: `scripts/fetch_news_sources.sh` (Unix) or `scripts/fetch_news_sources.ps1` (Windows).
