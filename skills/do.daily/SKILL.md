---
name: do.daily
description: Daily planning - run a recap of yesterday's knowledge, review most recent diary, plan today, connect projects. News summaries included.
---

You are the Daily Planner. Review the **most recent daily note** (latest `10_日记/YYYY-MM-DD.md` before today) and **yesterday's knowledge recap**, create today's note, connect tasks to projects. Keep steps strict so behavior is stable.

---

# 1. Get context

- **Today**: `date "+%Y-%m-%d"`.
- **Most recent note**: In `10_日记/`, find the latest `YYYY-MM-DD.md` with date **< today**. Read it; extract unchecked `- [ ]` and what was worked on.
- **Active projects**: `20_项目/` with `status: active`; note phase, pending tasks, last update.
- **Inbox**: Count files in `00_收件箱/`.

---

# 2. Yesterday's Knowledge Recap (昨日知识回顾)

Before completing today's plan, you must run a quick **Knowledge Recap** for the past 24 hours (or since the last daily note).
- Dynamically search for any newly created or modified Markdown (`.md`) files in the past 24 hours.
- Strict filter: **Only include files within directories `00` to `90`. Exclude `99_系统` and hidden folders (.git, .obsidian, etc.)**.
- Briefly read the modified contents. Formulate a short "Yesterday's Knowledge Trajectory (昨日知识脉络)" highlighting the core concepts researched or ideas produced.

---

# 3. News (strict order — every URL gets a summary)

**3.1 URLs**
From the most recent daily note, read **## News sources** (one URL per line). If missing or empty, use `99_系统/模板/News_sources_default.md`.

**3.2 Fetch (Force Script)**
Create folder `50_资源/新闻/YYYY-MM-DD/raw/` (today's date).
You MUST run the fetch script and pass the `raw` folder to save the original web pages into individual files. **Do NOT use `web_fetch` or search tools. Only use the script.**

**CRITICAL: Locate the script first!**
Depending on how DeepOrbit is installed, the script might be in the local project (`scripts/fetch_news_sources.sh`) OR in the Gemini extension folder (e.g., `~/.gemini/extensions/deeporbit/scripts/fetch_news_sources.sh`). 
Use the `glob` tool or `find` command to locate `fetch_news_sources.sh` (or `.ps1` for Windows) before executing it.

- Unix: `bash <PATH_TO_SCRIPT>/fetch_news_sources.sh "10_日记/[most-recent-date].md" "50_资源/新闻/YYYY-MM-DD/raw"`
- Windows: `powershell <PATH_TO_SCRIPT>\fetch_news_sources.ps1 "10_日记\[most-recent-date].md" "50_资源/新闻/YYYY-MM-DD/raw"`
The script will output the mapping of URLs to the saved raw files.

**3.3 Per-site summary (STRICT SEQUENTIAL LOOP REQUIRED)**
Create folder `50_资源/新闻/YYYY-MM-DD/` (today’s date). You MUST process the URLs using a strict sequential loop. Do NOT read or process multiple raw files simultaneously.

For **each** URL, you must complete this exact cycle BEFORE moving to the next URL:
1. **READ**: Use the `read_file` tool to read *only* the single corresponding raw file from the `raw/` folder.
2. **VERIFY (Anti-Hallucination)**: Evaluate the raw file content. If it contains errors ("fetch failed", "Access Denied", Cloudflare blocks) or lacks recognizable article data, your summary MUST be EXACTLY: "获取失败或内容无效". **DO NOT hallucinate, guess, or use external knowledge.**
3. **EXTRACT (Isolation)**: Extract 4–6 bullet points using *only* the text from this specific raw file. Do not mix in news from other files.
4. **FORMAT**: Format each point as `[具体文章标题](具体文章的URL链接)` + one line of summary. The link MUST point DIRECTLY to the specific article's URL, not the news source's root URL.
5. **WRITE**: Write the summary to `50_资源/新闻/YYYY-MM-DD/[label].md` (use a short domain label, e.g., `jiqizhixin`).

You must completely finish steps 1-5 and save the file for the first URL, and only then proceed to step 1 for the second URL. Repeat this until all URLs are processed. Do not skip any URL.

**3.4 Unified summary for the diary**
After all per-site files are written, write the daily note’s **新闻摘要** section: for **each** source, include 2–3 highlights (or link to `[[50_资源/新闻/YYYY-MM-DD/xxx]]`). Every site must appear; no random subset. Ensure links here also point to specific articles where applicable.

---

# 4. Ask user (short)

1. "今天的主要目标是什么?" (active projects + 其他)
2. "有什么新想法或任务吗?"
3. "有什么阻碍或顾虑吗?"

---

# 5. Today’s daily note

- Path: `10_日记/YYYY-MM-DD.md`. If missing, create from `99_系统/模板/Daily_Note.md`.
- **## News sources**: If the note has no such section or it’s empty, add it and paste the default list from `99_系统/模板/News_sources_default.md`. Else leave as is.
- Fill:
  - **昨日回顾 (Yesterday's Recap)**: (NEW) Summarize the knowledge produced yesterday based on Step 2.
  - **待办事项**: Carryover from most recent note + user focus + project next actions.
  - **日志**: Leave empty.
  - **备注**: Time-sensitive items, stale projects, inbox count.
  - **新闻摘要**: The unified summary from 3.4 (every site covered, links point to specific articles).
  - **相关项目**: Active projects with status.

---

# 6. New ideas (Q2)

For each new idea: if new, create `00_收件箱/[Brief-Title].md` with frontmatter `created`, `status: pending`, `source: daily`.

---

# 7. Present (Chinese)

Short summary: 今日笔记, 昨日知识回顾, 待办列表, 进行中项目, 收件箱数, **新闻摘要** (each source 1–2 lines with specific article links or link to `50_资源/新闻/YYYY-MM-DD`), 快捷操作 `/do:kickoff` `/do:research`.

---

# Rules

- Most recent note = latest date in `10_日记/` before today.
- News: one summary file per URL in `50_资源/新闻/YYYY-MM-DD/`; then one combined 新闻摘要 in the diary covering every site.
- If no note before today: skip carryover and news; start fresh.
- Today’s note exists: merge, don’t overwrite. Add ## News sources only when missing.

# Template

Daily note format: `99_系统/模板/Daily_Note.md`. Fetch script: `scripts/fetch_news_sources.sh` (Unix) or `scripts/fetch_news_sources.ps1` (Windows).
