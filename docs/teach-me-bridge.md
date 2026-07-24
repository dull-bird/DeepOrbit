# Teach Me 联动：Vault 知识导入与来源标注

DeepOrbit 管理知识库；[teach-me](https://github.com/dull-bird/teach-me-skill)
把工作沉淀为学习者画像和知识树。两者通过 **带来源标注的导出** 联动：

```
DeepOrbit vault ──teach-me export──▶ staging ──import──▶ teach-me vault
                                              │
                                              └─ origin 块（kind/source_path/
                                                 vault_name/import_id）随每条
                                                 capture/assess 写入
```

## 用法

```bash
# 默认导出 40_Wiki、60_Notes、30_Research
deeporbit --vault . teach-me export

# 追加手写笔记与项目；70_Family 永远需要显式指定
deeporbit --vault . teach-me export --dirs 40_Wiki 60_Notes 30_Research 15_Writings
```

脚本解析顺序：`--script` → `$TEACH_ME_SCRIPT` → 常见安装位置
（`~/.claude/skills/teach-me/…`、`~/.agents/…`、`~/.codex/…`、`~/.omp/…`）。

导出返回 JSON：`origin`（来源标注块）、`prompt_for_ai`（蒸馏指令）、
`deeporbit.exported_notes`。agent 按 `prompt_for_ai` 把知识点写入 teach-me
的 `capture`/`assess`，**原样透传 origin 块**。

## 不混淆的保证

| 层 | 标注 |
|----|------|
| 笔记 frontmatter | `origin: import`、`imported_from`、`origin_source_path`、`import_id`（保留 `type: teach-me/*`，再导入过滤不受影响） |
| 概念状态 / 知识树节点 | `origin` 块，first-wins：后来的学习事件永不覆盖 |
| teach-me 配置 | `linked_vaults` 记录来源 vault |

只读区（如 `60_Notes/微信读书`）与 `70_Family` 默认不导出；导出只读
vault，不写入任何内容。重复导入安全：teach-me 跳过自己的笔记并按标题合并。

技能入口：`/do:teach-me`。要求 teach-me-skill ≥ 1a8b9e2。
