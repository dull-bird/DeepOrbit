# Vault 目录布局：可配置目录、状态分文件夹与骨架检查

DeepOrbit 的目录结构由**逻辑名**驱动：代码和 agent 只认 `inbox`、`projects`
这类逻辑名，实际文件夹名以 vault 根目录 `deeporbit.json` 的 `directories`
段为准。改目录名不会破坏任何功能——CLI、索引、生命周期、suggest 全部通过
同一张映射解析路径。

## 逻辑目录表

`src/deeporbit/config.py` 的 `DIRECTORIES` 是唯一的默认映射：

| 逻辑名 | 默认目录 | 用途 |
|--------|----------|------|
| `inbox` | `00_Inbox` | 快速捕获、默认 `Todos.md` |
| `diary` | `10_Diary` | Daily Notes 与短期上下文 |
| `writings` | `15_Writings` | 用户亲笔写作 |
| `projects` | `20_Projects` | 项目（状态分文件夹，见下） |
| `research` | `30_Research` | 研究与领域（状态分文件夹，见下） |
| `wiki` | `40_Wiki` | 原子、可复用概念 |
| `resources` | `50_Resources` | 策展的外部资料 |
| `notes` | `60_Notes` | 摘要与原始知识捕获 |
| `family` | `70_Family` | 家庭与个人生活记录 |
| `plans` | `90_Plans` | 可评审的执行计划与检查点 |
| `system` | `99_System` | 模板、Bases、提示词、日历导出、归档 |

`index_dirs`（本地搜索索引的扫描范围）缺省从这张表派生，无需单独维护。

## 自定义目录名：`directories` 部分覆盖

`deeporbit.json` 顶层的 `directories` 段可以覆盖**任意一部分**逻辑名，
缺省项继续使用默认值：

```json
{
  "schema_version": 2,
  "language": "zh-CN",
  "directories": {
    "inbox": "00_收件箱",
    "projects": "20_项目"
  }
}
```

上例只改了 inbox 和 projects，其余九个逻辑名仍是默认目录。所有 CLI 命令
（`status` / `todo` / `rag` / `pause` / `archive` …）立即使用新名字，
无需重启或重建索引。

## init 收养规则

`deeporbit --vault . init` 幂等。对每一个逻辑名：

1. **配置目录已存在** → 不动。
2. **配置目录不存在，但对应的默认目录存在且非空** → 把默认目录
   **rename 收养**为配置名（例如已有 `00_Inbox/`、配置改成 `00_收件箱`
   时，`init` 直接改名），结果记入 `InitResult.adopted`（`"old -> new"`
   列表）。这就是"改目录名绝不会出错"的保证：先改 `deeporbit.json`，
   再跑一次 `init` 即完成迁移。
3. **配置目录和默认目录同时存在** → 判定冲突，写入 `InitResult.conflicts`，
   不合并、不覆盖，由人工裁决。
4. 旧的本地化目录（如 `50_Resources/新闻`、`99_System/提示词`）仍按内置
   `MIGRATIONS` 表安全合并，冲突同样只报告不覆盖。

## 状态分文件夹约定（projects / research）

`projects` 和 `research` 两个区内部按工作项状态再分一层：

```
20_Projects/
├── BigProj/            ← active：留在区根部
├── Paused/             ← paused 项目归这里
│   └── SideQuest/
└── Archived/           ← archived 项目归这里（平铺）
    └── OldProj/
```

- **frontmatter 的 `status` 字段永远是真相源**；`Paused/`、`Archived/`
  只是物理整理，方便人眼扫库。移动时 CLI 会同步写回 frontmatter，两者
  不会背离。
- `pause` 一个 projects/research 下的条目 → 笔记连同同名 assets 文件夹
  一起移入 `<区>/Paused/`；`resume` → 移回区根部。其他区的
  pause/resume 只改 frontmatter，不移动。
- `archive` 一个 projects/research 下的条目 → 移入 `<区>/Archived/`
  （平铺，盖上 `status: archived` 与日期）；其他区的归档行为不变，
  仍进 `99_System/Archive/<Bucket>/<YYYY>/`。
- `done` 从不移动——完成但尚未归档的条目留在原地，由你决定何时归档。
- 目标位置已有同名条目 → 报错，绝不覆盖。
- 手动拖过文件导致位置和 `status` 不一致时，`deeporbit --vault . organize`
  按 frontmatter 生成归位计划（dry-run 默认只打印），确认后
  `organize --apply` 执行；冲突只报告不覆盖。
- 不建 `Active/` 文件夹——active 就是区根部，少一层无意义的嵌套。

## 骨架检查（doctor）

骨架 = 11 个顶层目录（按配置名解析）+ `projects`、`research` 各自的
`Paused/`、`Archived/` 二级目录。`init` 创建骨架，`doctor` 校验骨架：

```bash
deeporbit --vault . doctor            # 诊断报告，退出码恒为 0
deeporbit --vault . doctor --strict   # 骨架缺失或根目录有违规条目时退出码 1
```

`doctor` 的 JSON 输出含两个骨架字段：

- `skeleton_missing`：缺失的骨架目录（相对路径，如 `"20_Projects/Paused"`）。
  跑一次 `init` 即可补齐。
- `skeleton_violations`：vault 根目录下不在白名单内的条目名。白名单 =
  11 个骨架顶层目录（按配置名）+ `deeporbit.json` + `DeepOrbitPrompt.md*`
  + `CLAUDE.md` + `AGENTS.md` + 所有点开头的条目（`.obsidian`、`.git`、
  `.trash`、`.DS_Store` …）。其余任何文件/文件夹出现在根目录即违规，
  按 `do.organize` 的流程处理（询问后移入对应区或 `trash` 可恢复删除）。

`--strict` 的退出码让骨架检查可以进 CI 或 cron：违规即非零。

## 零 token 的 cron 守护

骨架检查本身是确定性 CLI，**不消耗任何 LLM token**。注册一个每日任务，
只在 `doctor --strict` 真的报违规时才唤醒 agent 整理：

```bash
deeporbit cron add skeleton-check \
  "运行 deeporbit doctor --strict，有违规时按 do.organize 契约整理" \
  --every daily
```

平时 `cron run-due` 评估这条指令时，`doctor --strict` 退出码为 0 就没有
任何事可做，agent 立即沉默收尾；只有退出码非零（骨架缺失或根目录违规）
才进入 do.organize 的提议-批准流程。守护成本≈0，卫生问题不过夜。
