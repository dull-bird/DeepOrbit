# DeepOrbit

![DeepOrbit Banner](deeporbit.png)

> **一个连接大语言模型与 Obsidian 的 AI Agent 系统，自动化深度研究与个人知识管理。**

[**English**](README.md)

DeepOrbit 将你的 [Obsidian](https://obsidian.md/) 知识库变成 AI 驱动的研究引擎。它通过专用的 Agent 技能（基于 Gemini CLI / Claude Code）自动完成深度研究、论文翻译、内容策展和知识库维护 —— 让你专注于思考，而非整理。

> [!IMPORTANT]
> **需要安装 Obsidian。** DeepOrbit 的文件夹结构、双链系统和模板都依赖本地 Obsidian 知识库。

🙏 **致谢**：DeepOrbit 深受 [OrbitOS (MarsWang42)](https://github.com/MarsWang42/OrbitOS) 启发。感谢其在知识库架构和 Agent 驱动工作流方面的创新理念。

---

## 工作原理

```mermaid
flowchart TD
    A["🧠 你"] -->|想法、URL、PDF| B["⚙️ DeepOrbit Agent"]
    B -->|选择技能| C["🧩 技能包"]
    C -->|写入笔记| D["📂 Obsidian 知识库"]
    D -->|双链关联| A
```

你向 DeepOrbit 提供原始输入 —— 一个 arXiv 链接、一个 PDF、一个灵感、一个 URL。Agent 引擎会将请求路由到合适的**技能**，该技能负责处理、翻译、摘要或结构化内容，并将结果直接保存到你的 Obsidian 知识库中，附带完整的元数据和双链。

---

## 快速开始

### 前置要求

| 工具 | 必需？ | 说明 |
|------|--------|------|
| [Obsidian](https://obsidian.md/) | ✅ 是 | 知识库管理 |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) 或 [Claude Code (有限支持)](https://docs.anthropic.com/en/docs/claude-code) | ✅ 是 | Agent 运行时 |
| `ralph` | **必需** | 用于 `/do:pdf-to-markdown` 和 `/do:translate-markdown` |
| `xelatex` | 可选 | 用于 `/do:arxiv-translator` |

### 三步安装

```bash
# 1. 克隆仓库
git clone https://github.com/dull-bird/DeepOrbit.git

# 2. 在你的 Obsidian 知识库中运行初始化
# Windows (PowerShell):
& "$env:USERPROFILE\.gemini\extensions\deeporbit\scripts\init_deeporbit_prompt.ps1" "C:\你的\知识库\路径"

# macOS/Linux (Bash):
bash ~/.gemini/extensions/deeporbit/scripts/init_deeporbit_prompt.sh ~/你的/知识库/路径

# 3. 在 Gemini CLI 中初始化
/do:init ~/你的/知识库/路径
/memory refresh
```

初始化脚本（或 `/do:init` 命令）会自动：
- 将 `DeepOrbitPrompt.md` 和 `deeporbit.json` 复制到你的知识库
- 创建所有知识库文件夹（见下方结构）
- 将 `DeepOrbitPrompt.md` 注入 `.gemini/settings.json`

### 语言配置

编辑知识库根目录下的 `deeporbit.json` 设置 AI 的交互语言：

```json
{ "language": "zh-CN" }
```

> **注意：** 文件夹路径始终保持英文以确保稳定性。只有 AI 的回复和生成的笔记内容会遵循此语言设置。

---

## 知识库结构

```mermaid
flowchart TD
    V["📦 你的 Obsidian 知识库"] --> A["00_Inbox<br/><i>快速捕获</i>"]
    V --> B["10_Diary<br/><i>每日日志</i>"]
    V --> C["20_Projects<br/><i>活跃项目</i>"]
    V --> D["30_Research<br/><i>深度研究</i>"]
    V --> E["40_Wiki<br/><i>原子概念</i>"]
    V --> F["50_Resources<br/><i>简报、产品发布、新闻</i>"]
    V --> G["60_Notes<br/><i>摘要与捕获</i>"]
    V --> H["90_Plans<br/><i>执行计划</i>"]
    V --> I["99_System<br/><i>模板、提示词、归档</i>"]

    style V fill:#1a1a2e,stroke:#16213e,color:#e0e0e0
    style A fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style B fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style C fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style D fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style E fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style F fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style G fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style H fill:#0f3460,stroke:#16213e,color:#e0e0e0
    style I fill:#0f3460,stroke:#16213e,color:#e0e0e0
```

---

## 技能一览

DeepOrbit 内置 **24 个预配置 AI 技能**，分为两大类：

### 🌐 通用技能(无需 Obsidian)

这些技能独立运作, 不依赖 Obsidian 知识库。

```mermaid
mindmap
  root((通用技能))
    🧠 思考
      /do:ask
      /do:brainstorm
    📚 学术
      /do:arxiv-translator
    📄 文档处理
      /do:pdf-to-markdown
      /do:translate-markdown
    ⚙️ 图表
      do.mermaid
```

### 📂 Obsidian 技能(需要知识库)

这些技能依赖 DeepOrbit 知识库的文件夹结构。

```mermaid
mindmap
  root((Obsidian 技能))
    🧠 日常与规划
      /do:daily
      /do:kickoff
    🔬 研究与知识
      /do:research
      /do:parse-knowledge
      /do:note-summary
      /do:recap
    📰 内容策展
      /do:ai-newsletters
      /do:ai-products
      /do:ai-research-digest
    📚 学术工具
      /do:arxiv-translator
    📄 文档处理
      /do:pdf-to-markdown
      /do:translate-markdown
    🔧 知识库维护
      /do:fix-links
      /do:archive
      /do:organize
      /do:refresh-prompt
    ⚙️ Obsidian 集成
      do.obsidian-markdown
      do.obsidian-bases
      do.json-canvas
```

### 技能速查表

| 命令 | 功能 |
|------|------|
| `/do:daily` | 晨间规划：回顾昨日、获取新闻、创建今日笔记 |
| `/do:kickoff` | 将收件箱中的想法转化为结构化项目（双 Agent 工作流） |
| `/do:research` | 深入研究某个主题 → 生成研究笔记 + Wiki 条目（双 Agent 工作流） |
| `/do:ask` | 快速问答，无需繁重的笔记流程 |
| `/do:brainstorm` | 交互式苏格拉底式头脑风暴伙伴 |
| `/do:note-summary` | 自动抓取 URL/文件/论文 → 结构化摘要 + 知识库双链归档 |
| `/do:parse-knowledge` | 将非结构化文本转化为知识库就绪的研究笔记 + Wiki 条目 |
| `/do:recap` | 指定时间范围的知识库活动周期性回顾报告 |
| `/do:arxiv-translator` | 下载 arXiv 论文 → 翻译 LaTeX → 编译 PDF |
| `/do:pdf-to-markdown` | PDF → Markdown, 完整性清单 + 图像提取 |
| `/do:translate-markdown` | 逐 section 翻译 Markdown, 术语一致性校验 |
| `/do:ai-newsletters` | 每日 AI 新闻简报摘要（基于 RSS） |
| `/do:ai-products` | AI 产品发布摘要（Product Hunt、HN、GitHub、Techmeme） |
| `/do:ai-research-digest` | AI 研究摘要（来自机器之心） |
| `/do:fix-links` | 扫描知识库中的失效双链 → 自动生成 Wiki 笔记 |
| `/do:archive` | 归档已完成的项目和已处理的收件箱条目 |
| `/do:organize` | 深度知识库重组: 根目录清理 + 分类修复 + 孤立笔记 + 元数据 |
| `/do:refresh-prompt` | 安全更新 DeepOrbitPrompt.md, diff 对比 + 合并选项 |

---

## 核心工作流示例

### 🌅 晨间流程

```mermaid
flowchart TD
    A["运行 /do:daily"] --> B["回顾昨日日记"]
    B --> C["知识回顾：过去 24 小时有什么变化？"]
    C --> D["设定今日目标"]
    D --> E["从 ## News sources 获取新闻"]
    E --> F["在 50_Resources/Newsletters/ 生成摘要"]
    F --> G["创建今日日记：10_Diary/YYYY-MM-DD.md"]
```

### 💡 想法 → 项目

```mermaid
flowchart TD
    A["00_Inbox 中的想法"] -->|"/do:kickoff"| B["规划 Agent<br/>在 90_Plans/ 创建计划"]
    B -->|"用户审阅"| C["执行 Agent<br/>在 20_Projects/ 创建项目"]
    C --> D["收件箱条目归档至 99_System/Archive/"]
```

### 📄 学术论文处理流程

```mermaid
flowchart TD
    A["arXiv URL"] --> B["/do:arxiv-translator"]
    B --> C["下载 LaTeX 源码"]
    C --> D["翻译为目标语言"]
    D --> E["使用 xelatex 编译"]
    E --> F["翻译后的 PDF 就绪"]
```

### 📝 自动化摘要与归档

```mermaid
flowchart TD
    A["输入：URL / PDF / 论文标题"] --> B["/do:note-summary"]
    B --> C{识别类型}
    C -->|URL| D["web_fetch 获取原文"]
    C -->|PDF| E["read_file 视觉解析"]
    C -->|标题| F["Search 溯源全文"]
    D & E & F --> G["第一性原理拆解 + 结构化摘要"]
    G --> H["自动存入 60_Notes/相应分类/"]
    H --> I["创建 Wiki 双链关联"]
```

---

## 理念

> 一切围绕你运转。让知识保持流动，让 AI Agent 承担解析、翻译、摘要和维护知识结构完整性的重任。
