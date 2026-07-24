# DeepOrbit Example Vault

一个最小但完整的 DeepOrbit 知识库示例，用来演示：

- **目录模型**：`00_Inbox` → `99_System` 的保质期语义
- **工作生命周期**：`status: active | paused | done | archived`（见 [[学习Rust]]、[[向量数据库调研]]）
- **任务**：标准 Markdown checkbox + `^do-*` 块 ID（见 `00_Inbox/Todos.md`）
- **只读区**：`60_Notes/微信读书` 由 weread-vault 同步，不可编辑
- **新闻源**：`10_Diary/2026-07-23.md` 的 `## News sources` 小节
- **用户画像**：`99_System/Profile.md`

## 上手

```bash
# 在本目录中
deeporbit --vault . status      # 工作总览
deeporbit --vault . todo list   # 任务
deeporbit --vault . agenda      # 逾期/今天/即将到期
deeporbit --vault . suggest     # 建议
deeporbit --vault . serve       # 本地仪表盘
```

本 vault 用 Git 管理 —— 这正是 DeepOrbit 推荐的同步方式
（`deeporbit --vault . sync`）。远程镜像：
https://github.com/dull-bird/deeporbit-example-vault
