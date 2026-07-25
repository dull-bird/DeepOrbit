---
name: stalled-project
when: active 项目 7 天无新活动，或无未完成 todo
then: 在简报中建议为该项目设下一步行动（do.todo），并询问是否暂停
---

# 项目停滞

active 项目要么靠持续推进存活，要么应该被显式暂停——悬在中间是最坏状态
（GTD stalled practice）。7 天无活动是确定性信号，CLI 预筛直接判天数；
"active 但没有任何未完成 todo"说明项目失去了下一步行动，同样算停滞。
处置：从项目笔记推导一个具体的下一步行动，用 do.todo 的 NL 录入提议给用户；
若用户认为该项目近期不动，建议改 `status: paused` 而不是继续挂着。
