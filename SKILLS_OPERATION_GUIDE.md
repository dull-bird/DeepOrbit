# 技能开发指南（贡献者）

> 本指南面向**修改 DeepOrbit 本身**的人。普通用户安装请看 [README](README.md) 的 Quick Start。

## 单一事实来源

所有技能的唯一源头是仓库里的 `skills/` 目录，**全是真实文件**（不再有软链接）：

```
skills/
├── do.ask/
│   └── SKILL.md
├── do.pdf-to-markdown/
│   ├── SKILL.md
│   └── scripts/            # 捆绑脚本（可执行助手）
│       └── extract_images.py
└── ...（共 26 个 do.* 技能）
```

> ⚠️ 不要提交 `.agents/`、`.claude/skills/`、`.cursor/`、`.roo/` 等**各工具安装目录**，也不要提交
> `skills-lock.json`。它们是**消费者**运行 `npx skills add` 时自动生成的产物，已在 `.gitignore` 中忽略。

## 编辑技能

直接用编辑器修改 `skills/do.<name>/SKILL.md`。约定：

- frontmatter 必须有 `name` 和 `description`，`name` 必须等于目录名（`do.<name>`）。
- `description` 是触发信号，写清楚**何时该用**，而不仅是它是什么。
- `SKILL.md` 保持精简；长参考/示例拆到同目录的独立文件并链接过去（渐进式披露）。
- 可执行助手放在该技能的 `scripts/` 下。

## 本地测试（让 Claude Code 加载你的改动）

在仓库目录下用通用安装器把技能链接进当前项目（开发模式，软链接会实时反映你的编辑）：

```bash
npx skills add .            # 从当前仓库安装到本项目
# 或装到用户级，供任意项目使用：
npx skills add . --global
```

改完后重启 Claude Code（或重新运行 `/skills`）即可加载最新版本。
因为安装的是软链接，编辑 `skills/` 下的源文件会直接生效，无需手动复制。

运行仓库契约验证前，请先安装开发依赖：

```bash
python3 -m pip install -e '.[dev]'
```

## 添加新技能

1. 在 `skills/` 下新建 `do.<new-skill>/SKILL.md`，按上面的约定填写 frontmatter。
2. 如有脚本，放进 `skills/do.<new-skill>/scripts/`。
3. 按 [AGENTS.md](AGENTS.md) 的「Skill & command sync」规则，更新 `README.md` 和 `README_CN.md`
   的技能计数、思维导图和速查表（中英文都要改）。

## 验证

```bash
# 一次检查技能、命令配对、manifest 和 README 计数
python scripts/validate_repo.py

# 列出全部技能
ls -d skills/do.*/ | sort

# 检查 frontmatter name 与目录名是否一致
for d in skills/do.*/; do n=$(basename "$d"); \
  fm=$(awk '/^name:/{print $2; exit}' "$d/SKILL.md"); \
  [ "$n" != "$fm" ] && echo "MISMATCH: $n vs $fm"; done

# 检查带脚本的技能
ls -R skills/do.pdf-to-markdown/
```
