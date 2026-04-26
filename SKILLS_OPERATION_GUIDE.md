# 技能开发操作指南

## 目录结构

```
# 源码（你的工作区）
/Users/lilei/Documents/work/repos/DeepOrbit/
├── skills/
│   ├── do.archive/
│   │   └── SKILL.md
│   ├── do.arxiv-translator/
│   │   └── SKILL.md
│   ├── do.pdf-to-markdown/
│   │   ├── SKILL.md
│   │   └── scripts/              # 有捆绑脚本
│   │       └── extract_images_pdfplumber.py
│   └── ...（共 22 个 do.* 技能）

# 运行环境（Claude Code 实际读取的位置）
/Users/lilei/.claude/skills/
├── do.archive/
│   └── SKILL.md
├── do.arxiv-translator/
│   └── SKILL.md
├── do.pdf-to-markdown/
│   └── SKILL.md                  # ⚠️ 缺少 scripts/ 目录
└── ...（共 22 个 do.* 技能）
```

## 注意事项

- **repo 里真实有捆绑脚本的技能**：`do.pdf-to-markdown/scripts/`、`do.ghost-link-fixer/scripts/`
- **已安装的技能缺少这些脚本目录**，复制时需要补全
- **技能更新后必须重启 Claude Code**（或重新运行 `/skills`）才能生效

---

## 日常操作流程

### 1. 在编辑器中修改 SKILL.md

用 VS Code（或其他编辑器）打开 repo，直接编辑 `skills/do.xxx/SKILL.md` 文件。

### 2. 同步到 Claude Code 技能目录

每次修改后运行：

```bash
# 复制到 ~/.claude/skills/
cp -r /Users/lilei/Documents/work/repos/DeepOrbit/skills/* /Users/lilei/.claude/skills/
```

这条命令直接覆盖目标目录下的技能文件夹，包括脚本等捆绑资源。

## # 3. 重启 Claude Code

关闭当前会话重新打开，/skills 命令会加载最新版本。

---

## 首次补齐遗漏的脚本目录

目前有两个技能缺少捆绑脚本，运行一次补齐：

```bash
cp -r /Users/lilei/Documents/work/repos/DeepOrbit/skills /tmp/deeporbit_skills
cp -r /tmp/deeporbit_skills/do.pdf-to-markdown /Users/lilei/.claude/skills/do.pdf-to-markdown
cp -r /tmp/deeporbit_skills/do.ghost-link-fixer /Users/lilei/.claude/skills/do.ghost-link-fixer
```

---

## 添加新技能

在 repo 的 `skills/` 下创建新目录，例如 `skills/do.new-skill/SKILL.md`，然后执行上述同步命令即可。

---

## 验证安装

```bash
# 检查技能文件完整性
ls /Users/lilei/.claude/skills/ | grep "do\." | sort

# 检查某个技能是否包含脚本等捆绑资源
ls -R /Users/lilei/.claude/skills/do.pdf-to-markdown/

# 检查技能数量
ls -d /Users/lilei/.claude/skills/do.*/ | wc -l
```
