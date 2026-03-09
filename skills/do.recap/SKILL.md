---
name: do.recap
description: Automatically summarize all newly added or modified Markdown files within a given time period (default target directories 00-90), generating a periodic recap report.
---

# Knowledge Recap Skill

## Objective

When the user invokes `/do:recap <time range / natural language description>`, you need to:
1. Parse the time range provided by the user (e.g., "this week", "past three days", "last month", etc.).
2. In the specified knowledge base root directory, find all **newly created or modified Markdown (`.md`) files** within that time period.
3. Strictly follow the directory filtering conditions: **Only include directories starting with `00` to `90`. Forcibly exclude `[system_folder]` and any other irrelevant or system-generated hidden directories (such as `.git`, `.obsidian`, `.gemini`, etc.)**.
4. Read the latest content of these filtered files.
5. Generate a structured periodic recap report analyzing the user's core focuses, achieved results, and cross-domain knowledge threads.

## Workflow

### 1. Time Parsing & File Search

- Accurately understand the user's natural language time intent (e.g., today, last 7 days, October 2023, etc.). Calculate the start and end points based on the current time.
- Use your command-line tools (such as `fd` combined with system time, or use file search related tools directly) to initiate a search starting from the user's workspace directory as the root.
- **Strict Filtering Rules (CRITICAL)**:
  - Must match relative paths for directories starting with `00` to `90`. If the file is not under these directories, ignore it.
  - Absolutely exclude any path containing `[system_folder]`.
  - Exclude all non-`.md` files.

### 2. Content Reading & Analysis

- Iterate through and read the content of all files matching the conditions. If there is an extremely large number of files, or if a single file is very long, please extract the core content or the first few hundred lines to grasp the main idea of the article.
- Extract the core theme, category (based on the directory it resides in, such as `[diary_folder]`, `[projects_folder]`, `[wiki_folder]`, etc.), and main conclusions of each note.

### 3. Generate Summary Report

The report needs to have exceptionally high personal review value; it should not just be a list, but rather provide deep insights. Please use the following Markdown template.

#### Analysis Requirements:
- Identify the user's **2-3 core themes of focus** during this time period.
- Extract potential connections from the independent notes, and attempt to describe the "knowledge thread" of this period in one paragraph.
- Discover knowledge blind spots or directions for deeper exploration.

#### Format Template:

```markdown
---
type: recap_report
title: "Knowledge Recap: <Time Period Description>"
date: YYYY-MM-DD
tags:
  - Recap
  - Review
---

# <Time Period Description> Knowledge Review & Outcomes

> Core Insight: Profoundly summarize the focus of your work and the evolution of your thoughts during this period in one paragraph.

## 1. Core Themes & Trajectory

- **Core Theme A**: What research was done in what direction, and what conclusions were reached.
- **Core Theme B**: What research was done in what direction, and what conclusions were reached.

## 2. Detailed Output

Categorize by directory structure or project, and list the newly added/modified notes during this period along with a one-sentence summary for each:

### 📁 <Category One, e.g., 20_Projects or a specific project name>
- [[<Note Filename 1>]]：<One-sentence summary of the core value of this note>
- [[<Note Filename 2>]]：<One-sentence summary of the core value of this note>

### 📁 <Category Two, e.g., 40_Knowledge Base>
- [[<Note Filename 3>]]：<One-sentence summary of the core value of this note>

## 3. Next Steps & Reflection

(Based on the newly added documents you have read, point out potential gaps or disconnections, and pose 1-2 fundamental questions to guide the user into deeper thinking and open up the next phase of research.)
```

## 4. Report Output

You can display this generated analysis report to the user, or save it directly to a folder such as `[diary_folder]` or a corresponding Periodic Review folder based on the user's instructions.
