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

### 1. 安装可移植 Skills

```bash
npx skills add dull-bird/DeepOrbit
```

也可以克隆仓库并安装确定性的 Python Core：

```bash
git clone https://github.com/dull-bird/DeepOrbit.git
cd DeepOrbit
python3 -m pip install -e .
```

### 2. 初始化知识库

```bash
deeporbit --vault ~/Documents/MyVault init
deeporbit --vault ~/Documents/MyVault doctor
```

初始化可重复执行。已有笔记和自定义提示词不会被覆盖。旧中文目录只在安全时合并；冲突会被报告，并保留两份文件。

### 3. 开始使用

```bash
deeporbit --vault ~/Documents/MyVault todo add "阅读论文" --today --due 2026-07-15
deeporbit --vault ~/Documents/MyVault agenda
deeporbit --vault ~/Documents/MyVault rag "指数跟踪"
deeporbit --vault ~/Documents/MyVault calendar export
deeporbit --vault ~/Documents/MyVault open 10_Diary/2026-07-15.md
```

也可以直接对 Agent 说：「研究指数跟踪」「把这件事加到今天」「有哪些逾期任务？」或「查找我以前关于 RAG 的笔记」。

## 运行时兼容性

| 运行时 | 可移植 Skills | 原生包 | 命令 | MCP | 可选 Hooks | 长任务增强 |
|---|---:|---|---:|---:|---:|---|
| Kimi Code | 是 | `kimi.plugin.json` | 是 | 是 | 是 | 实验 Goal + checkpoints |
| OpenClaw | 是 | 工作区 `.agents/skills` | 自然语言 | 是 | 是 | 原生 Goal + checkpoints |
| Gemini / Antigravity | 是 | `gemini-extension.json` | 是 | 是 | 是 | Plan/Tracker + checkpoints |
| Codex | 是 | `.codex-plugin/plugin.json` | 是 | 是 | 是 | Thread Goal + checkpoints |
| 其他 Agent Skills 运行时 | 是 | — | 视运行时而定 | 可选 | — | Markdown checkpoints |

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

DeepOrbit 2.0 内置 **26 个 `do.*` 技能**。`skills/` 是唯一事实来源；每个技能都有配对的 Markdown 与 Gemini TOML 命令。

| 技能 | 用途 |
|---|---|
| `do.init` | 安全初始化或升级知识库 |
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
