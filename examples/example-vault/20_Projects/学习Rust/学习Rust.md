---
type: project
status: active
area: "[[编程语言]]"
created: 2026-07-10
updated: 2026-07-23
tags: [project, rust]
---

# 学习 Rust

目标：两个月内能用 Rust 写一个小的 CLI 工具。

## 里程碑
1. 所有权 / 借用 / 生命周期（进行中）
2. 错误处理与迭代器
3. 实战：一个 Markdown 待办清单 CLI

## Tasks
- [ ] 完成《Rust 程序设计语言》第 4 章习题 #task ^do-20260710090000-rust01
- [ ] 用 clap 写第一版 todo CLI 骨架 #task ^do-20260710090000-rust02

## 笔记
所有权规则比预想直白：每个值有且只有一个所有者。真正难的是
生命周期标注何时必须显式写出 —— 见 [[Rust生命周期]]。
