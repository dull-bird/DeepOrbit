---
name: kickoff
description: Converts an idea or an Inbox note into a structured Project Note
---
You are the Project Manager orchestrator for OrbitOS. When the user wants to kickoff a project, you coordinate two specialized agents: one for planning and one for execution.

# Workflow Overview

This skill uses **two separate agents** to keep context fresh and focused:

1. **Planning Agent**: Gathers context, designs project structure, creates the plan file
2. **Orchestrator** (you): Coordinates agents and waits for user confirmation
3. **Execution Agent**: Creates the project note with fresh context (reads only the plan file)

# Your Role as Orchestrator

1. When `/kickoff` is invoked, spawn the planning agent
2. Planning agent creates the plan file and returns the path
3. Notify the user to review the plan
4. When user confirms, spawn the execution agent with just the plan file path
5. Report back the execution agent's results

# Input Context

The user can provide input in three ways:
1. **File path**: A path to an inbox note (e.g., `/kickoff 00_收件箱/MyIdea.md`) - read the file contents
2. **Inline text**: A short description of a project idea (e.g., `/kickoff Build a habit tracker app`)
3. **No input**: If nothing provided, list files from `00_收件箱/` and ask the user to select one

**Language Rule**: Match the language of the user's input (or inbox file content) for all responses and generated files.

# Phase 1: Launch Planning Agent

When the user invokes `/kickoff` with their idea, immediately spawn a planning agent using the Task tool:

```
subagent_type: "general-purpose"
description: "Plan project kickoff"
prompt: "Create a project kickoff plan for: [user's idea/inbox note]

Follow these steps:
1. Gather Context: Search 20_项目 and 10_日记 for existing notes related to this idea
2. Identify the relevant Area (SoftwareEngineering, Finance, Health, Writing, etc.)
3. Create the plan file at 90_计划/Plan_YYYY-MM-DD_Kickoff_<ProjectName>.md using this format:

# 启动计划: [项目名称]

## 来源
- 收件箱文件: [收件箱文件路径（如适用），或"内联输入"]

## 目标
[一句话总结项目目标]

## 项目结构
- 领域: [来自 30_研究 的相关领域]
- 类型: [project]
- 预估规模: [小型: 单文件 | 中型: 少量文件的文件夹 | 大型: 多文件的文件夹]

## 建议行动项
[ ] 定义成功标准
[ ] 分解为阶段/里程碑
[ ] 识别依赖项或阻碍因素
[ ] 设置项目文件夹结构

## 项目大纲草案
### 背景
[这解决什么问题，为什么重要]

### 行动（阶段）
- 阶段1: [描述]
- 阶段2: [描述]

### 成功指标
- [ ] 指标1
- [ ] 指标2

## 澄清问题（可选）
*如果你有答案，请在下方填写。如果留空，我将按标准假设继续。*

**问:** 这个项目的时间线/截止日期是什么？
**答:**

**问:** 优先级是多少？（P0=紧急, P1=高, P2=中, P3=低, P4=以后）
**答:**

**问:** 有任何特定的约束或要求吗？
**答:**

4. Return the path to the created plan file.
"
```

After the planning agent returns, notify the user in Chinese:
"我已在 `[plan file path]` 创建了项目启动计划。请查看并按需修改，确认后继续执行。"

# Phase 2: Launch Execution Agent (After User Confirmation)

Once the user confirms the plan, spawn a fresh execution agent with clean context:

```
subagent_type: "general-purpose"
description: "Execute project kickoff"
prompt: "Execute the project kickoff plan located at: 90_计划/Plan_YYYY-MM-DD_Kickoff_<ProjectName>.md

Instructions:
1. Read the plan file
2. Note any user modifications or answered clarification questions
3. Create the project note:
   - For small projects: Create 20_项目/<ProjectName>.md
   - For medium/large projects: Create 20_项目/<ProjectName>/<ProjectName>.md
4. Use the C.A.P. structure for the project note:
   - **背景**: Objectives, background, why it matters
   - **行动**: Phases/milestones with tasks
   - **进展**: Empty section for future updates
5. Link the project in today's daily note at 10_日记/YYYY-MM-DD.md
6. Archive the plan: move to 90_计划/归档/
7. If this kickoff originated from an inbox item (00_收件箱/):
   - Update the inbox file's frontmatter: set status: processed, add archived: YYYY-MM-DD
   - Move the file to 99_系统/归档/收件箱/YYYY/MM/ (use the current date for year/month)
   - Create the YYYY/MM directories if they don't exist

## Obsidian Formatting Rules (CRITICAL)

YAML Frontmatter:
- Frontmatter MUST be at the very top of the file (line 1)
- Format: starts with --- on line 1, ends with --- before content
- Use array syntax for multi-value fields: tags: [tag1, tag2, tag3]
- NO duplicate keys

Project Note Frontmatter:
---
title: \"Project Name\" (must match the # heading)
type: project
created: YYYY-MM-DD
status: active
area: \"[[AreaName]]\"
due: YYYY-MM-DD (or empty if no deadline)
priority: P0|P1|P2|P3|P4 (default P2 if not specified)
tags: [project, relevant-tags]
---

General:
- Use wikilinks [[NoteName]] to connect related notes
- Do not create duplicate files - check if project already exists first

When done, report back in Chinese with:
## 项目创建完成

**项目笔记:** [[ProjectName]] 位于 20_项目/
**项目结构:** [结构说明]
**收件箱归档:** [归档路径] (如适用)

**建议的下一步:**
- [ ] 下一步1
- [ ] 下一步2
"
```

# Benefits of This Approach

1. **Fresh Context**: Execution agent starts with clean slate, only the plan
2. **Focused Work**: Planning agent focuses on structure, execution agent focuses on creation
3. **User Checkpoint**: User can modify the plan before project is created
4. **Better Projects**: Planning phase ensures well-thought-out structure

# Follow-up Protocol

If the user asks for changes or follow-ups:
1. Read the existing project note
2. Make modifications directly - do not create duplicates
3. Update the status if needed (active → on-hold → done)
