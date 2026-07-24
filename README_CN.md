# DeepOrbit

![DeepOrbit](deeporbit.png)

> 一个可在 Kimi Code、OpenClaw、Gemini/Antigravity、Codex 及其他 Agent Skills 运行时之间迁移的本地优先 Obsidian 知识系统。

[English](README.md) · [在线文档](https://dull-bird.github.io/DeepOrbit/) · [架构说明](docs/architecture.md)

DeepOrbit 将研究、项目、写作、待办和检索保存在普通本地文件中。Agent Skills 描述工作流；一个小型 Python Core 负责安全初始化、增量检索、稳定任务 ID 和日历导出等确定性操作。各运行时的 Goal、Hooks、插件与 MCP 用于增强体验，但不是系统正确性的必要条件。

## 为什么使用 DeepOrbit

- **可迁移**：同一套 `skills/` 可以被不同 Agent Skills 运行时读取。
- **本地优先**：Markdown 是唯一事实来源，不需要 DeepOrbit 云账号。
- **同步中立**：可使用 Git、Obsidian Sync 或任意文件同步；索引在每台电脑本地重建。
- **Obsidian 原生**：Properties、Bases、Graph、Backlinks、Daily Notes、Callouts 和 Canvas 脱离 Agent 仍然有用。
- **完整降级**：ChromaDB、MCP、Obsidian CLI、Tasks、Dataview、Calendar 都是可选组件。
- **可断点恢复**：长任务通过 Markdown checklist 恢复，不依赖外部自调用循环。

## 三分钟教程

### 1. 全局只安装连接器

DeepOrbit 推荐的跨项目安装方式是**全局只安装一个连接器 skill**：

```bash
npx skills add dull-bird/DeepOrbit --skill do.link --global --agent '*' --yes
```

然后在这台机器上安装一次确定性的 CLI：

```bash
git clone https://github.com/dull-bird/DeepOrbit.git ~/src/DeepOrbit
python3 -m pip install -e ~/src/DeepOrbit
deeporbit __schema
```

`deeporbit __schema` 会输出完整的机器可读 CLI 表面，供 agent 查看详细命令能力。
如果 checkout 中没有 `deeporbit` 可执行文件，可用：

```bash
PYTHONPATH=~/src/DeepOrbit/src python -m deeporbit __schema
```

### 2. 初始化或接手一个 vault

```bash
deeporbit --vault ~/Documents/MyVault init --source ~/src/DeepOrbit
deeporbit --vault ~/Documents/MyVault doctor
deeporbit link add main ~/Documents/MyVault --description "个人研究与写作"
```

初始化可重复执行。已有笔记和自定义提示词不会被覆盖。旧中文目录只在安全时合并；冲突会被报告，并保留两份文件。初始化会物化：

- 工作流 skills 到 `99_System/DeepOrbit/skills/`，并生成 `skills-index.json`；
- 系统模板、Bases、提示词和方法论指南到 `99_System/`；
- 精简后的可移植仓库包到 `99_System/DeepOrbit/repo/`。

这个包不是 Git checkout。它复制使用或交接 vault 所需的运行时表面（skills、commands、prompts、hooks、CLI 源码、MCP、docs、manifests），同时排除 `.git`、虚拟环境、缓存、构建产物、`node_modules` 和生成的 agent 安装目录。

### 3. 开始使用

```bash
deeporbit --vault ~/Documents/MyVault todo add "阅读论文" --today --due 2026-07-15
deeporbit --vault ~/Documents/MyVault agenda
deeporbit --vault ~/Documents/MyVault rag "指数跟踪"
deeporbit --vault ~/Documents/MyVault calendar export
deeporbit --vault ~/Documents/MyVault open 10_Diary/2026-07-15.md
```

也可以直接对 Agent 说：「研究指数跟踪」「把这件事加到今天」「有哪些逾期任务？」或「查找我以前关于 RAG 的笔记」。

## 从任意工作区连接知识库

不需要在每个项目里安装全部技能。只装 `do.link` 一个技能，注册一个或多个知识库，然后用自然语言把请求路由过去：

```bash
deeporbit link add main ~/Documents/MyVault --description "个人研究与写作"
deeporbit link add work ~/Documents/WorkVault --description "工作项目与客户资料"
deeporbit link list
deeporbit link route "准备客户评审"
deeporbit --vault @work todo add "准备评审" --today
deeporbit --vault @main rag "指数跟踪"
```

`link add` 会校验目标：`deeporbit` 报告目录是否已初始化，`obsidian_opened` 报告是否被 Obsidian 打开过（`.obsidian/app.json`）。描述驱动路由——有多个知识库时，Agent 会把你的请求与每个库的描述匹配来选择目标，`deeporbit link route` 是处理歧义请求的机器级辅助命令。注册表位于设备本地的 `~/.config/deeporbit/links.json`，不参与同步。

CLI 还实验性支持 [CLI Schema v1](https://github.com/cli-schema/cli-schema)：`deeporbit __schema` 输出整棵命令树的机器可读描述，供 Agent 工具消费。

## 工作流转、用户画像与作者标记

任何带 `status:` 字段的笔记都是一个工作项——不只是 `20_Projects`。所有流转都由 CLI 确定性执行，不依赖 Agent 记得移文件：

```bash
deeporbit --vault ~/Documents/MyVault status                              # 全库 active / paused / done / archived 总览
deeporbit --vault ~/Documents/MyVault pause 30_Research/Old-Thread.md     # 暂停但保持可见
deeporbit --vault ~/Documents/MyVault resume 30_Research/Old-Thread.md
deeporbit --vault ~/Documents/MyVault done 15_Writings/essay.md
deeporbit --vault ~/Documents/MyVault archive 20_Projects/BigProj         # 文件夹含资产一起归档，绝不覆盖
deeporbit --vault ~/Documents/MyVault trash 00_Inbox/stale.md             # 可恢复删除，进 .trash/
```

`99_System/Bases/Work Status.base` 是 active / paused / done / archived 的常驻看板。`99_System/Profile.md` 是知识库对你的画像：稳定事实用 `profile set` 维护，日常学到的用 `profile observe` 追加（带时间戳和来源标记，用户亲自写的事实不会被悄悄覆盖）。

由外部同步管理的目录（例如 [weread-vault](https://github.com/dull-bird/weread-vault) 导出的 `60_Notes/微信读书`）是**只读区**：`deeporbit init` 会通过同步 frontmatter 自动识别并写入 `deeporbit.json` 的 `readonly.directories`。生命周期 CLI 拒绝改动这些路径，`status` 会标记它们，建议引擎会跳过——这些笔记随便引用和链接，衍生分析写到自己的目录。

作者标记只是一个不可见的 frontmatter 字段，绝不用可见角标：Agent 创建笔记时**必须**写 `author: ai`，大幅改写人的笔记时改为 `author: mixed`。无标记即人写——用户永远不需要手动标记。阅读视图干干净净，Bases 却能区分 AI 产出和人写内容。

## 指导、节奏与可扩展性

- `deeporbit --vault ~/Documents/MyVault suggest` —— 从库状态推导的优先级建议（完成未归档、休眠项目、索引过期、画像为空…）。
- `/do:mentor` —— 教练而非助手：基于 `status` + `suggest` + 画像做诊断，一次只教一个方法切片（GTD 管承诺、PARA 管归档位置、卡片笔记管知识复利、原子习惯管节奏——边界研究见 [docs/methodology.md](docs/methodology.md)，已物化进每个 vault），最后只留一个下一步动作。
- `/do:dream` —— 知识库的离线“做梦”：把反复出现的主题提升为 Wiki 原子笔记、发现隐藏连接、推动生命周期决策、沉淀画像观察。它只提议，你来批准。
- `deeporbit cron add dream "Run the do.dream consolidation workflow" --every daily` —— 设备本地调度；`cron run-due --agent` 报告到期任务并包成已配置 agent CLI 的交接命令。
- `/do:agent` —— 探测本机已安装的 agent CLI（omp/claude/gemini/codex），用 ask 表单选择一个，把执行交给它（ACP/RPC/print）。见 [docs/agent-cli.md](docs/agent-cli.md)。
- `/do:teach-me` —— 把 vault 知识导出到 [teach-me](https://github.com/dull-bird/teach-me-skill)，附带 `origin` 来源标注块，导入的知识不会与 teach-me 自动积累的知识混淆。见 [docs/teach-me-bridge.md](docs/teach-me-bridge.md)。
- `deeporbit --vault . sync` —— 当前 vault 的 Git 同步（按需 pull / commit / push）。可直接运行，也可交给 `deeporbit cron`。

- **Recipe**（`99_System/Recipes/*.md`）是扩展点：声明式的 `cli:` / `skill:` / `note:` 步骤，把 DeepOrbit 和任意其他 skill 串联。`deeporbit --vault . recipe run "Weekly Review"` 将 recipe 解析为执行计划。优先写 recipe，而不是新增基础设施。

这些选择背后的工具调研（PDF/Markdown/HTML 处理器、Obsidian 插件生态、kepano 的 obsidian-skills 等社区项目）见 [docs/tooling-landscape.md](docs/tooling-landscape.md)；更广泛的技能生态与开源 NotebookLM 替代品调研见 [docs/skill-ecosystem-research.md](docs/skill-ecosystem-research.md)。可直接运行的示例库在 [examples/example-vault](examples/example-vault)，并镜像于 [dull-bird/deeporbit-example-vault](https://github.com/dull-bird/deeporbit-example-vault)。

## Obsidian 插件

`plugin/` 是一个轻量、无 LLM 的 Obsidian 伴侣插件：工作状态侧栏（active / paused / done / archived，一键流转，区分 AI/人写）加上 pause / resume / done / archive 命令，语义与 CLI 完全一致（同样绝不覆盖）。见 [plugin/README.md](plugin/README.md)。

## Web Dashboard

```bash
deeporbit --vault ~/Documents/MyVault serve --open        # http://127.0.0.1:8765
```

本地零依赖 dashboard（只监听 127.0.0.1）：状态卡片与休眠统计、14 周活跃热力图、优先级建议、全量工作项表格（一键暂停/恢复/完成/归档）、状态/作者/目录统计、全库检索、recipe 与 cron 总览——以及**通过 ACP 连接本地 agent 的助手面板**（自动探测 `omp acp`、`claude --acp`、`gemini --acp`，也可用 `--agent` 指定）。agent 的文件读取被限制在 vault 内，写请求一律拒绝。界面遵循 Apple 流体界面原则（半透明材质、按下即时反馈、reduced-motion 降级）。

## 运行时兼容性

| 运行时 | 可移植 Skills | 原生包 | 命令 | MCP | 可选 Hooks | 提示词/上下文加载 | 长任务增强 |
|---|---:|---|---:|---:|---:|---|---|
| Kimi Code | 是 | `kimi.plugin.json` | 是 | 是 | 是 | 运行时 Hook + 提示词文件 | 实验 Goal + checkpoints |
| OpenClaw | 是 | 工作区 `.agents/skills` | 自然语言 | 是 | 是 | 视运行时而定 | 原生 Goal + checkpoints |
| Gemini / Antigravity | 是 | `gemini-extension.json` | 是 | 是 | 是 | `contextFileName` + Hook | Plan/Tracker + checkpoints |
| Claude Code | 是 | `.claude-plugin/plugin.json` | 是 | 是 | 是 | `CLAUDE.md` 导入 `DeepOrbitPrompt.md` | Markdown checkpoints |
| Codex | 是 | `.codex-plugin/plugin.json` | Skills/自然语言 | 是 | 是 | 受信任的 `.codex/hooks` 或插件 Hook | Markdown checkpoints |
| OMP | 是 | — | 视运行时而定 | 可选 | 是 | 原生 `.omp/hooks/pre/deeporbit.ts` | Markdown checkpoints |
| 其他 Agent Skills 运行时 | 是 | — | 视运行时而定 | 可选 | — | 视运行时而定 | Markdown checkpoints |

运行时状态绝不是唯一进度来源。长工作流会在 `90_Plans/` 保存带勾选状态的计划，因此可在中断、重启或切换 Agent 后恢复。

## 同步与本地检索

只有笔记、模板、Bases 和 `deeporbit.json` 位于知识库内。机器本地索引位于系统缓存目录，并由稳定的 vault ID 标识。

```text
Git / Obsidian Sync             每台电脑
Markdown + deeporbit.json  -->  ~/.cache/deeporbit/<vault-id>/
                                  search.sqlite
                                  manifest.json
                                  可选 chromadb/
```

每次检索前都会检查新增、修改、重命名和删除文件。默认 SQLite FTS 不需要第三方依赖。可选语义检索：

```bash
python3 -m pip install -e '.[rag]'
deeporbit --vault ~/Documents/MyVault index ensure --semantic
deeporbit --vault ~/Documents/MyVault rag "概念性问题" --semantic
```

不要提交或同步向量数据库。参见[同步与 RAG](docs/sync-and-rag.md)。

## Obsidian 集成

DeepOrbit 在 `99_System/Bases/` 提供项目、研究、包含任务的笔记和知识健康四个原生 Base。

默认使用的 Obsidian 能力：

- Properties 提供统一 schema：`type`、`status`、`area`、`created`、`updated`、`tags`。
- Bases 提供可编辑的文件级仪表盘。
- Graph 与 Backlinks 展示知识关系和孤立笔记。
- Daily Notes 连接 agenda、recap 与当前工作。
- Canvas 只在空间表达确实有帮助时用于研究地图。

可选社区插件：

| 插件 | 增强能力 | 必需？ |
|---|---|---:|
| Tasks | 更丰富的任务查询与完成界面 | 否 |
| Dataview | 高级只读仪表盘 | 否 |
| Calendar | Daily Notes 日历导航 | 否 |

打开笔记时优先使用 Obsidian CLI；未安装时回退到 `obsidian://` URI，最后回退为显示绝对路径。

## 待办、Agenda 与日历

任务保持为可移植 Markdown：

```markdown
- [ ] 审阅 DeepOrbit 架构 #task ⏳ 2026-07-13 📅 2026-07-15 ^do-20260713120000-a1b2c3
```

稳定 block ID 用于精确完成任务和生成稳定的 iCalendar UID。ICS 导出是带提醒的本地快照，不声称支持 Google 或 Apple Calendar 双向同步。参见[待办与日历](docs/todo-calendar.md)。

## 技能一览

DeepOrbit 2.0 内置 **31 个 `do.*` 技能**。`skills/` 是唯一事实来源；每个技能都有配对的 Markdown 与 Gemini TOML 命令。

| 技能 | 用途 |
|---|---|
| `do.init` | 安全初始化或升级知识库 |
| `do.link` | 连接外部知识库并把请求路由到其中的工作流 |
| `do.mentor` | 方法、工具与 recipe 教练；诊断知识库健康度 |
| `do.dream` | 离线整理：主题提升、隐藏连接、生命周期推动 |
| `do.teach-me` | 把 vault 知识带来源标注导出到 teach-me |
| `do.agent` | 探测并配置本机 agent CLI（omp/claude/gemini/codex） |
| `do.daily` | 日常计划、回顾、新闻和项目上下文 |
| `do.todo` | 捕捉、列出和完成 Markdown 任务 |
| `do.agenda` | 汇总逾期、今天、未来和未排期任务 |
| `do.calendar` | 将带日期任务导出为 ICS |
| `do.kickoff` | 将想法转化为结构化项目 |
| `do.write` | 将原始想法整理为个人写作 |
| `do.research` | 可断点恢复的证据型深度研究 |
| `do.ask` | 轻量知识库问答 |
| `do.brainstorm` | 互动式想法探索 |
| `do.rag` | 自动刷新的本地检索 |
| `do.rag-index` | 检查和刷新词法或语义索引 |
| `do.search` | 快速词法和短语检索 |
| `do.note-summary` | 基于完整来源的摘要与收藏 |
| `do.parse-knowledge` | 将非结构化材料整理为持久笔记 |
| `do.recap` | 总结近期知识库变化 |
| `do.arxiv-translator` | 翻译并编译 arXiv LaTeX 源文件 |
| `do.pdf-to-markdown` | 可验证的高保真 PDF 转换 |
| `do.translate-markdown` | 完整且术语一致的 Markdown 翻译 |
| `do.translate` | 将文档翻译路由到合适工作流 |
| `do.mermaid` | 选择并创建合适的 Mermaid 图 |
| `do.fix-links` | 查找并修复幽灵双链 |
| `do.organize` | 分析并安全整理知识库 |
| `do.archive` | 归档已完成项目和已处理内容 |
| `do.refresh-prompt` | 合并上游提示词且保留用户定制 |
| `do.obsidian-open` | 通过 CLI、URI 或路径打开笔记 |

## MCP 工具

可选 MCP server 提供：

- `deeporbit_status`
- `rag_search`
- `rag_query`
- `task_agenda`

使用 `python3 -m pip install -e '.[mcp]'` 安装。没有 ChromaDB 时词法检索仍然可用。参见 [MCP 参考](mcp/README.md)。

## 开发

```bash
python3 -m pip install -e '.[dev]'
python3 -m unittest discover -s tests -v
python3 scripts/validate_repo.py
npm --prefix site install
npm --prefix site run build
```

`tests/fixture_vault.py` 会搭建一个“乱中有序”的示例知识库（active/paused/done 项目、旧中文目录、AI 与人写的笔记、LaTeX fixture）。集成测试套件驱动它跑通全流程：初始化与迁移、生命周期流转、归档、trash 保护、todo → agenda → calendar 链路、增/改/删时的索引同步、链接路由、用户画像维护和 LaTeX 拆分器。

CI 会验证 Python 行为、技能与命令、JSON manifests、Shell 语法、运行时 profiles 和 GitHub Pages 构建。修改技能或命令时，必须按 [AGENTS.md](AGENTS.md) 同步更新中英文 README。

## 文档地图

- 教程：[开始使用](docs/getting-started.md)
- How-to：[同步并重建 RAG](docs/sync-and-rag.md)
- How-to：[待办与日历](docs/todo-calendar.md)
- 参考：[运行时兼容性](docs/runtime-compatibility.md)
- 解释：[架构](docs/architecture.md)

## 致谢

DeepOrbit 受到 [OrbitOS](https://github.com/MarsWang42/OrbitOS) 启发，并吸收了可移植 Agent Skills 生态的设计思想。详见 [skills/ACKNOWLEDGMENTS.md](skills/ACKNOWLEDGMENTS.md)。

## 许可证

[MIT](LICENSE)
