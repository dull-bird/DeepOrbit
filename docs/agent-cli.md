# Agent CLI 集成

DeepOrbit 负责准备上下文（prompt、vault 状态、cron 指令），执行可以交给
机器上已安装的 agent CLI。

## 支持矩阵

| Agent | acp | rpc | print |
|-------|-----|-----|-------|
| omp | `omp acp` | `omp --mode rpc` | `omp -p` |
| claude | `claude --acp` | — | `claude -p` |
| gemini | `gemini --acp` | — | `gemini -p` |
| codex | — | — | `codex exec` |

## 命令

```bash
deeporbit --vault . agent detect [--versions]   # 探测本机 agent 与模式
deeporbit --vault . agent configure omp         # 保存选择（默认挑 acp>rpc>print）
deeporbit --vault . agent configure codex --mode print
deeporbit --vault . agent status                # 当前配置 + 实时探测
deeporbit --vault . agent clear                 # 清除配置
```

选择存入 `deeporbit.json` 的 `agent:` 段——它是**偏好**而非机器状态，会随
vault 同步；`status` 里的 `available: false` 表示配置同步到了一台没装该
CLI 的机器，重新 configure 即可。

## 消费方

- **仪表盘**：`deeporbit --vault . serve` 在 `--agent auto`（默认）时使用
  配置的 agent；助手视图有「Agent 配置」面板（`/api/agent/config`）。
- **Cron 交接**：`deeporbit --vault . cron run-due --agent` 把每个到期任务
  包成配置 agent 的交接命令（print 模式直接给 argv；acp/rpc 给启动说明）。

技能入口：`/do:agent` —— 自动探测并用 ask 表单请你选择。
