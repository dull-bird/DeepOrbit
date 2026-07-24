# 每日新闻摘要自动化

链路：**cron 到点 → 抓取原文 → agent 逐源解析 → 日记摘要 → 重建索引**。

## 一次性设置

```bash
# 1. 注册每日任务（设备本地注册表）
deeporbit cron add daily-news "Run recipe Daily News" --every daily

# 2. 配好执行 agent（可选，但推荐）
deeporbit --vault . agent configure omp

# 3. 把 run-due 接到运行时调度器或系统 cron，例如每小时检查一次：
#    deeporbit --vault . cron run-due --agent
```

## Daily News recipe 步骤

`99_System/Recipes/Daily News.md`（`deeporbit --vault . recipe run "Daily News"`
可查看解析后的执行计划）：

1. 确保今天的日记有 `## News sources` 小节（缺省从
   `99_System/Templates/News_sources_default.md` 拷贝）。
2. `bash scripts/fetch_news_sources.sh <今天日记> 50_Resources/Newsletters/<今天>/raw`
   —— 确定性抓取，原文落盘。
3. `do.daily` 的 News 小节：逐个 raw 文件校验（防幻觉：抓取失败就写
   "Fetch failed or content invalid"）、抽取 4–6 条、写成
   `50_Resources/Newsletters/<今天>/<来源>.md`，链接必须指向具体文章。
4. 日记顶部追加 3–5 行「今日要闻」，然后 `deeporbit --vault . index`。

## 设计要点

- 抓取是确定性的（脚本），解析是 agent 判断（防幻觉规则在 do.daily）。
- `cron run-due --agent` 输出可直接交给配置好的 agent CLI 执行——
  print 模式给完整 argv，acp/rpc 给启动说明。
- 新闻原文和摘要都是普通 Markdown，进索引、可被 rag 检索。
