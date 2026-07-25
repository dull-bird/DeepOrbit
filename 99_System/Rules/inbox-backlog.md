---
name: inbox-backlog
when: 00_Inbox 中的笔记数超过 10
then: 在简报中建议用 do.parse-knowledge 消化，或对可立项的条目用 do.kickoff
---

# Inbox 积压

GTD 的 capture 只有在 clarify 环节跟上时才有价值；inbox 超过 10 条说明
捕捉速度持续快于消化速度，材料正在失去时效语境。数量由 CLI 预筛判定，
agent 负责判断积压的性质：素材类走 do.parse-knowledge 归置为持久笔记，
想法类挑可立项的用 do.kickoff 转成项目。不要建议用户"手动整理"——
给出可执行的技能路径。
