# Skill 生态调研（2026-07-24）

> 调研目的：为 DeepOrbit 技能升级寻找已被验证的设计模式。来源均为各项目
> GitHub 仓库页 / REST 元数据（stars、license、维护状态截至调研日）。
> 「可借鉴点」为工程推断；license 标为 Other 的项目不应在未读完整
> LICENSE 前直接复制代码。

## A. Agent Skills 集合

### obra/superpowers — 260k★, MIT, 活跃
<https://github.com/obra/superpowers>

把 agent 工作约束为：需求澄清 → 分段设计 → 用户确认 → 可执行计划 →
subagent 驱动开发 → 测试与审查。强调真正的 red/green TDD。

**可借鉴**：do.kickoff/do.research/do.todo 统一为「意图澄清—可审阅计划—
执行—验证」；do.research/do.dream 加用户批准门；90_Plans 做成可恢复的
plan-scoped 工作区。

### kepano/obsidian-skills — 43k★, MIT, 活跃
<https://github.com/kepano/obsidian-skills>

按格式拆分技能（obsidian-markdown、bases、json-canvas、obsidian-cli、
defuddle），渐进加载，坚持开放格式。

**可借鉴**：do.note-summary/do.research 输出严格可移植 Markdown +
properties + wikilinks；加 defuddle 式网页清理阶段降噪声。

### anthropics/skills — 164k★, Apache-2.0（部分 source-available）
<https://github.com/anthropics/skills>

自包含目录 + SKILL.md（YAML name/description + 指令），运行时动态加载。

**可借鉴**：为 do.* 统一 metadata（触发条件、输入/输出、权限、可写路径、
验证）；长方法拆进 references，SKILL.md 只留路由。

### wshobson/agents — 38k★, MIT, 活跃
<https://github.com/wshobson/agents>

plugin 即安装/隔离边界；一个 source-of-truth 生成多 harness 适配物；
plugin-eval 分 static / LLM judge / Monte Carlo 三层。

**可借鉴**：`deeporbit skill validate`（结构、触发、输出、回归样例）。

## B. 开源 NotebookLM 类

### lfnovo/open-notebook — 36k★, MIT
<https://github.com/lfnovo/open-notebook>

多模态 ingest（PDF/视频/音频/网页）、18+ provider、全文+向量检索、
多人播客。README 自认 citations 仍弱（"basic references"）。

**可借鉴**：统一 source manifest；播客作为研究输出 recipe；引用必须
记录来源、段落/页码与生成时间 —— 不复制其引用弱点。

### MODSetter/SurfSense — 15k★, License: Other
<https://github.com/MODSetter/SurfSense>

REST/MCP typed connectors（Reddit/YouTube/IG/TikTok/Maps/Search/Amazon/
web crawl）、hybrid RAG cited answers、scheduled agents、watch local
folder（可指向 Obsidian）。

**可借鉴**：「连接器→规范化文档→引用片段→输出」统一接口；do.research
做成可调度 recipe；MCP/REST connector adapter，但权威内容落到 Markdown。

### khoj-ai/khoj — 36k★, AGPL-3.0
<https://github.com/khoj-ai/khoj>

个人第二大脑：语义检索、custom agents、定时 automation、personal
newsletter/通知、多端入口。

**可借鉴**：do.daily 借「自动化+通知」模式但输出仍为 Diary Markdown；
do.mentor 读 profile 与历史行为反馈。

### onyx-dot-app/onyx — 31k★, CE MIT
<https://github.com/onyx-dot-app/onyx>

50+ connectors、agentic hybrid RAG、deep research、MCP actions；
Standard/Lite 分层。

**可借鉴**：index/rag 区分 Lite（SQLite FTS）与增强模式（语义、reranker）；
connector 权限边界与引用审计。

## C. PKM AI

### brianpetro/obsidian-smart-connections — 5.3k★, License: Other
<https://github.com/brianpetro/obsidian-smart-connections>

本地 embedding、零 API key、离线优先；Connections view 动态显示相关
笔记，可拖拽建链、隐藏噪声、暂停刷新。

**可借鉴**：do.dream 做「候选连接→用户确认→写 wikilink」而非自动污染
图谱；rag 输出相似度及证据片段。

## D. RSS→LLM 每日新闻

### lebenf/prima_pagina — 早期项目, AGPL-3.0
<https://github.com/lebenf/prima_pagina>

RSS 聚合去重、LLM 分类、全文抽取 health tracking、按投票排序的
daily press digest、virtual feeds。

**可借鉴**：feed/source 配置、抽取健康度、digest 每条反链原文 URL。

### Alionkissadeer/ai-daily-news — 个人项目, MIT
<https://github.com/Alionkissadeer/ai-daily-news>

URL→标题→摘要三级去重、recency+权重打分、中英 digest、GitHub Actions
daily cron、Podcastfy/TTS、多渠道发布。

**可借鉴**：三级去重与半衰期 scoring；发布渠道做成 recipe，不耦合进核心。

## 采纳建议（按优先级）

1. **P0 — do.research / do.note-summary：citation-grounding contract。**
   每条事实绑定 canonical URL、抓取时间、段落定位、摘录 hash 与本地
   note；输出区分事实、推断、建议。
2. **P0 — CLI ingest/index：统一 Source→Extractor→Normalizer→Chunk→
   Index→Citation 管线。** SQLite FTS 为 Lite 基线，embedding/reranker
   为可选派生层，派生索引不进 vault。
3. **P0 — do.daily：RSS 输入、三级去重、时间衰减与反馈排序。**
   每篇摘要保留原文链接；发布渠道走 recipe/cron（已落地 Daily News
   recipe 的骨架）。
4. **P1 — do.dream：「候选连接/晋升/降级」工作流**，用户批准后写入，
   避免自动制造图谱噪声。
5. **P1 — do.recap：author-aware + lifecycle-aware 汇总。** 人类笔记
   权重高于 `author: ai`，输出「完成、阻塞、决定、待跟进」四类。
6. **P1 — do.mentor：成长反馈闭环。** 读 profile、任务行为、引用质量；
   稳定事实仅经 profile 命令显式确认，观察带时间/source（已部分落地）。
7. **P2 — skills/recipes/CLI eval：** 每个 do.* 声明触发器、权限、
   输入输出 schema 与验证样例；静态检查 + 少量回归。
8. **P2 — 多媒体输出：** transcript/podcast 作为派生 artifact，保留
   脚本、引用和模型/时间元数据，可复现、可删除。
