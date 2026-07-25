# 研究引用（todo 系统 + 主动参谋系统）

2026-07 两轮重设计用到的论文与一手资料。每条注明它支撑了什么决策。
设计推理见 [todo-system.md](todo-system.md) 与 [proactive-companion.md](proactive-companion.md)。

## 论文（arXiv / 会议）

| 论文 | 链接 | 支撑的决策 |
|---|---|---|
| What is the Best Process Model Representation?（Mermaid 对 LLM 最优，token 省 >90%） | https://arxiv.org/html/2507.11356v1 | 技能关系图用 mermaid 注入 prompt |
| Graph-of-Skills（技能依赖图检索：reward +25.55%，token −56.72%） | https://arxiv.org/html/2604.05333v3 | 技能间依赖边不是装饰，是路由资产 |
| Tool Graph Retriever | https://arxiv.org/html/2508.05152v1 | 同上（佐证） |
| Dynamic Tool Dependency Retrieval (DTDR) | https://arxiv.org/html/2512.17052v1 | 同上（佐证） |
| SkillGraph: Graph Foundation Priors | https://arxiv.org/pdf/2604.19793 | 同上（佐证） |
| 主动性帮助触发威胁感（proactivity backlash） | https://arxiv.org/html/2509.09309v2 | heartbeat 默认沉默、propose-approve |
| 差的主动建议比没有更糟 | https://arxiv.org/html/2502.18658v4 | 同上；HEARTBEAT_OK 抑制 |
| IFTTT vs Zapier：TAP 框架与 event/state 混淆 | https://ar5iv.labs.arxiv.org/html/1709.02788 | WHEN 规则写状态谓词不写事件 |
| CHI'19 TAP 用户研究 | https://dl.acm.org/doi/10.1145/3300782 | 同上（佐证） |
| Table Meets LLM（Sui et al., WSDM'24，宽表退化） | https://arxiv.org/abs/2305.13062 | 技能关系用图边列表而非大表格 |
| Fitz, Kushlev et al. 2019：通知批处理降低压力（田野实验） | https://www.kushlev.com/s/2019-Fitz-Batching.pdf | nudge 并入早晚批次，实时只留硬截止 |
| Ohly 2023：通知与幸福感元分析 | https://pmc.ncbi.nlm.nih.gov/articles/PMC10244611/ | 同上（佐证） |
| Amershi et al. 2019：Guidelines for Human-AI Interaction（G4 定时服务） | https://www.microsoft.com/en-us/research/publication/guidelines-for-human-ai-interaction/ | 低打扰、易拒绝、可关闭 |

## 系统工程与平台文档

| 资料 | 链接 | 支撑的决策 |
|---|---|---|
| todo.txt 官方格式规范 | https://github.com/todotxt/todo.txt | 一行一任务、行内属性、单文件够用 |
| todo.txt 社区扩展键（due:/rec:/t:） | https://todotxt.in/blog/todo-txt-format-complete-guide | 字段集选择 |
| Taskwarrior 文档（状态机、urgency、模板-克隆周期任务） | https://taskwarrior.org/docs/ | 周期任务语义、排序弱信号思想 |
| org-mode 手册（DEADLINE vs SCHEDULED、三种 repeater） | https://orgmode.org/manual/ | 📅 与 ⏳ 语义分离、when done 递归 |
| Obsidian Tasks 插件文档（emoji 格式、不支持时刻、查询语言、show tree） | https://github.com/obsidian-tasks-group/obsidian-tasks/tree/main/docs | 行内字段兼容集；⏰ 用 Reminder 插件约定补时刻 |
| Obsidian 论坛：Bases 不读文件正文任务（topic 103074） | https://forum.obsidian.md/t/103074 | 否决 Bases 任务表格路线 |
| Tasks 查询结果渲染嵌入图片修复（issue #3151 / PR #3498） | https://github.com/obsidian-tasks-group/obsidian-tasks/issues/3151 | 附件放心用 `![[...]]` |
| Obsidian 官方帮助：Attachments | https://github.com/obsidianmd/obsidian-help/blob/master/en/Editing%20and%20formatting/Attachments.md | 90_Attachments 约定 |
| JioNLP（中文时间解析，本机实测全过） | https://github.com/dongrixinyu/JioNLP | 中文 NL 选型（可选增强） |
| dateparser（实测 1.4.1 中文几乎全部失败） | https://pypi.org/project/dateparser/ | 否决其作为主解析器 |
| parsedatetime（英文实测通过） | https://github.com/bear/parsedatetime | 英文模式参照 |
| duckling（需 Haskell 运行时，排除） | https://github.com/facebook/duckling | 零依赖约束下的排除项 |
| Vikunja Quick Add Magic（抽取式 NL 录入范本） | https://vikunja.io/help/quick-add-magic/ | 抽取式解析 + 回显确认 |
| Todoist 日期语法帮助 | https://www.todoist.com/help/articles/introduction-to-dates-and-time-q7VobO | NL 覆盖面对标 |
| TickTick 中文智能识别 / 多次提醒 | https://help.dida365.com/tips/6427419485019308032/ | 中文 NL 与提醒对标 |
| alerter（macOS 可交互通知） | https://github.com/vjeantet/alerter | 提醒投递层（完成/稍后写回） |
| launchd 睡眠补触发 vs cron 静默跳过 | https://apple.stackexchange.com/questions/57412 等 | 调度层选 launchd |
| 订阅 ICS 的 VALARM 被客户端忽略（SO 实证） | https://cloud.tencent.com/developer/ask/sof/108455297 | ICS 只做可见性不做触发 |
| RFC 9074（VALARM 扩展，实现不一致佐证） | https://www.rfc-editor.org/rfc/rfc9074.html | 同上 |
| OpenClaw Heartbeat 调度指南 | https://sfailabs.com/guides/openclaw-heartbeat-scheduling | do.heartbeat 巡检模式原型 |
| Heartbeat vs Cron 职责分离 | https://www.clawnify.com/resources/heartbeat-vs-cron-openclaw-guide-2026 | cron/heartbeat 分工 |
| OpenClaw proactive-messages（静默调度 + suppression） | https://lobehub.com/en/skills/openclaw-skills-proactive-messaging | 频率控制三件套 |
| Khoj Automations（声明式 cron 自动化） | https://docs.khoj.dev/features/automations/ | 用户显式声明的主动行为 |
| NudgeRank（画像驱动 nudge，打开率 4%→13.1%） | https://www.themoonlight.io/en/review/nudgerank-digital-algorithmic-nudging-for-personalized-health | 反馈环（轻量计数版） |
| Super Productivity / GTD Weekly Review 指南 | https://super-productivity.com/blog/gtd-weekly-review-guide/ | stalled 检测与周回顾 recipe |
| LifeOS for Obsidian（PARA + Periodic + AI 模板） | https://github.com/quanru/obsidian-example-lifeos | vault 仪表盘组织参照 |
| Copilot for Obsidian（AI 读 vault 含图片） | https://github.com/logancyang/obsidian-copilot | 附件+AI 组合可行性 |
| TaskForge（Tasks 语法 + 移动通知分层形态） | https://taskforge.md/ | 存储层/体验层分离参照 |
| Obsidian-Tasks-Calendar（Dataview 日历视图） | https://github.com/702573N/Obsidian-Tasks-Calendar | 日历视图选项 |
| remind(1)（Unix 老牌提醒工具） | https://dianne.skoll.ca/projects/remind/ | 日期表达式语言参照 |
| tasks.org / todoman+vdirsyncer（CalDAV 任务生态） | https://tasks.org/ | ICS/VTODO 生态边界 |
