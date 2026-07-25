# DeepOrbit Todo 系统设计（2026-07 重设计）

调研基础：todo.txt / Taskwarrior / org-mode / Obsidian Tasks 插件 / Bases / Dataview /
Vikunja / Super Productivity / Todoist / TickTick / Things / MS To Do / LifeOS /
jionlp、dateparser、parsedatetime 实测 / macOS launchd·alerter·osascript / 飞书多维表格。
结论均有来源，见文末。

## 核心架构：一份数据，N 个视图

飞书多维表格的精髓不是视图多，而是**数据只有一份，视图只是查询渲染**。
DeepOrbit 的 todo 系统按四层组织：

```
存储层   00_Inbox/Todos.md（单文件默认捕获点）+ 项目笔记/Daily Note 中的任务行
         一行一任务，Tasks 插件 emoji 行内字段，纯 Markdown，git 可 diff
解析层   src/deeporbit/tasks.py —— 确定性解析/写回，唯一真相源读取器
智能层   skills/do.todo —— agent 负责 NL 理解、拆解、润色、汇报、建议
视图层   Obsidian Tasks 查询块仪表盘 + CLI 多视图输出 + dashboard server
提醒层   launchd 轮询 + alerter/osascript 本地通知 + cron 一次性任务 + ICS 导出
```

关键调研结论（决定设计的硬约束）：

1. **Bases 看不到文件内的 checkbox 任务行**（Obsidian 创始人论坛确认，topic 103074
   至今是未实现的 feature request）。任务行可视化必须走 Tasks 查询块 / CLI 渲染，
   Bases 只用于笔记级实体（项目、领域）。→ 否决"用 Bases 做任务表格"的路线。
2. **Tasks emoji 日期不支持时刻**（官方文档明确，discussion #607/#668）。
   "今晚七点"的时刻用 obsidian-reminder 插件的 `⏰ YYYY-MM-DD HH:mm` 约定承载。
3. **订阅 ICS 的 VALARM 被主流客户端忽略**（Outlook / Mac Calendar / Google
   Calendar 均不触发）。ICS 是"日历可见性"导出，不是提醒触发机制。
   Web Push 需要公网 + 厂商 push service，本地不可行，否决。
4. **macOS 提醒可靠性分水岭是 launchd**：睡眠错过的任务唤醒时补触发；cron 静默
   跳过（Apple 已弃用 cron）。→ 调度用 launchd，投递用 alerter/osascript。
5. **中文 NL 时间解析实测**（Python 3.14，2026-07-25）：dateparser 中文几乎全部
   失败；jionlp 全部通过（含"每周五"周期、模糊区间）但依赖 numpy+jiojio 过重。
   → 零依赖自实现中文正则为基础，jionlp 作可选增强。
6. **Tasks 查询结果可以渲染嵌入图片**（issue #3151，2025-07 PR #3498 修复）。
   → 附件/图片放心用 `![[...]]`。

## 存储格式（Tasks 插件兼容 + ⏰ 扩展）

```markdown
- [ ] 跟丽丽吃饭 📅 2026-07-25 ⏰ 19:00 ➕ 2026-07-24 ^do-20260724a1
- [ ] 准备季度评审 🔺 📅 2026-07-28 #project/工作 ^do-20260724b2
  - [ ] 整理数据 📅 2026-07-26 ^do-20260724c3
  - [x] 约会议室 ✅ 2026-07-24 ^do-20260724d4
- [ ] 每周五写周报 🔁 every week on Friday 📅 2026-07-31 ^do-20260724e5
- [ ] 换药 🔁 every 30 days when done 📅 2026-08-10 ^do-20260724f6
- [ ] 体检报告解读 ![[90_Attachments/20260725-体检报告.pdf]] 📅 2026-07-30 ^do-20260724g7
```

字段集（全部可选，正文唯一必填）：

| 字段 | 语法 | 说明 |
|---|---|---|
| 状态 | `[ ]` `[x]` `[/]` `[-]` | todo / done / doing / cancelled |
| 优先级 | `🔺⏫🔼🔽⏬` | highest/high/medium/low/lowest |
| 截止 | `📅 YYYY-MM-DD` | due |
| 时刻 | `⏰ HH:MM` | 与 📅 组合成精确提醒点（Tasks 不支持时刻的补充约定） |
| 计划 | `⏳ YYYY-MM-DD` | scheduled，计划开工日（org 语义，与 due 分离） |
| 创建 | `➕ YYYY-MM-DD` | created，add 时自动写入 |
| 完成 | `✅ YYYY-MM-DD` | done 时自动写入 |
| 重复 | `🔁 every ...` / `... when done` | strict / from-completion（org `.+` 语义） |
| 项目 | `#project/名称` 或 `[[项目笔记]]` | 关联 vault 其他项目 |
| 依赖 | `⛔ id` | 被阻塞（自动拆解的子任务排序用） |
| 附件 | `![[90_Attachments/...]]` | 图片/文件，Obsidian 内联渲染 |
| ID | `^do-<id>` | 稳定块 ID，done/attach/remind 的寻址锚 |
| 子任务 | 缩进 checkbox | 进度由父任务推导 [n/m]，不手填百分比 |

**零迁移承诺**：裸 checkbox 行（用户现有 todo.md 的写法）直接被解析，
无 ID 行合成 `legacy-<file>-<line>` ID；`done` 时自动补 ✅ 和块 ID。

## NL 录入（抽取式， Vikunja Quick Add Magic 模式）

`deeporbit todo add` 内置零依赖解析器（`nltime.py`），从文本中剥离时间片：

- 今天/今晚/明天/明晚/后天/大后天
- 上午/早上/中午/下午/晚上/今晚 + N点 / N点半 / N点N分 / HH:MM
- N天后 / N小时后 / N分钟后
- 周X/星期X/下周X（最近未来一次）
- 每周X / 每隔N天 / 每天（→ 🔁 recurrence）
- X月X日 / X月X号
- ISO 日期与日期时间
- 英文：today / tonight / tomorrow / next Friday / every Friday / in 3 days / 7pm

可选增强：安装 `jionlp` 后自动启用（`pip install jionlp`，覆盖更长尾的中文表达）。
优先级速记 `!1 !2 !3`（→ ⏫🔼🔽），`#tag` 直接识别。
复杂语义（"提前一小时提醒我"、"改成下周"）由 agent 在 do.todo skill 中处理并
**回显确认**（Vikunja/Todoist 的输入高亮同款交互）：

```
$ deeporbit todo add "今晚七点跟丽丽吃饭"
→ {"text": "跟丽丽吃饭", "due": "2026-07-25", "time": "19:00", ...}
```

## 提醒层（调度/投递分离）

```
launchd（每分钟 StartInterval，睡眠唤醒补触发）
  └─ deeporbit remind check --deliver
       ├─ 到期判定：📅 = today 且 ⏰ ≤ now 且未完成且未提醒过
       ├─ alerter（brew 装，可选）：交互通知 [完成] [稍后 10 分钟]
       │    动作写回：完成 → todo done；稍后 → 状态文件 snooze
       └─ 无 alerter：osascript display notification（零依赖横幅）
状态：~/.config/deeporbit/reminders.json（已提醒/snooze 记录，幂等）
安装：deeporbit remind install → 写 ~/Library/LaunchAgents/com.deeporbit.remind.plist
```

- **cron 一次性任务**：`deeporbit cron add <name> <instruction> --at 2026-07-25T19:00`
  —— 单次触发后自动 disable（保留审计记录，不删）。回应"agent 定时任务解决提醒"
  的路线：agent 工作流提醒（如"提醒我写周报并先给我草稿"）走 cron at。
- **ICS 导出升级**：带 ⏰ 的任务导出为 timed event（DTSTART/DTEND 1 小时）+
  VALARM；无时刻仍为全天事件。定位：日历可见性，不依赖其提醒。

## 视图层

**Obsidian 内**（`99_System/Todo Dashboard.md` 模板，Tasks 查询块）：
Overdue / Today / Upcoming 7d / 按 folder 分组 / Inbox 未排期，`show tree` 保留
子任务层级。Bases 不承担任务行视图（官方限制），继续管项目/笔记级实体。

**CLI/agent**（`deeporbit todo list --view ...`）：
- `board`：按 status 分列（todo/doing/done）
- `timeline`：按日期分组的时间线（overdue → today → 未来）
- `progress`：按项目聚合 n/m + 完成率 + 子任务进度
- 默认 JSON（agent 消费），`--md` 输出 Markdown 表格（OpenClaw 里直接渲染表单）

## 智能层（do.todo skill 行为契约）

agent 收到自然语言时：
1. **录入**：调 `todo add`（CLI 解析时间），复杂语义 agent 自行拆解后显式传字段；
   回显结构化结果让用户确认。
2. **拆解**：大任务 → 父任务 + 缩进子任务行（带 ⛔ 依赖），进度自动 [n/m]。
3. **润色**：口语化长段（用户 inbox 现状痛点）→ 可执行任务，保留原意，
   想法类内容建议转 30_Research 而非任务。
4. **汇报**：`agenda` + `todo list --view progress` → 自然语言进度总结。
5. **关联**：`#project/x` 或 `[[项目笔记]]`；`--project` 落项目笔记。
6. **建议**：结合 suggest，对 overdue / 长期 unscheduled 给出处置建议。

## 用户 vault 迁移（一次性，建议性）

1. `00_Inbox/todo.md` 内容并入 `00_Inbox/Todos.md`（裸 checkbox 已被解析，
   物理合并后删除旧文件，消除多载体）。
2. 归档 `99_System/Task Dashboard.md`、`系统配置/Git and OB Task List.md`。
3. 安装提醒：`brew install alerter`（可选）+ `deeporbit remind install`。

## 调研来源（节选）

- todo.txt 规范 github.com/todotxt/todo.txt；Taskwarrior docs taskwarrior.org；
  org-mode 手册（DEADLINE vs SCHEDULED、三种 repeater 语义）
- Tasks 插件官方文档（emoji 格式、不支持时刻、查询语言、show tree）；
  Bases 任务行不可见：Obsidian 论坛 topic 103074
- jionlp github.com/dongrixinyu/JioNLP（本机实测 1.5.29 中文全过）；
  dateparser 1.4.1 中文实测失败；parsedatetime 英文可用
- launchd vs cron：睡眠补触发差异；alerter github.com/vjeantet/alerter
- 订阅 ICS VALARM 被忽略：Stack Overflow 108455297；RFC 9074 实现不一致
- Vikunja Quick Add Magic vikunja.io/help/quick-add-magic；
  飞书多维表格视图体系；LifeOS github.com/quanru/obsidian-example-lifeos
