# Todo Dashboard

> [!note] 依赖 Tasks 社区插件
> 本页的查询块需要安装 [Tasks](https://publish.obsidian.md/tasks/) 社区插件才能渲染。
> 没有插件时退回 CLI：`deeporbit --vault . agenda`（逾期/今天/未来/未排期）与
> `deeporbit --vault . todo list --view progress --md`（项目进度）。
> `show tree` 保留子任务层级；进度 `[n/m]` 由父任务自动推导，不要手填。

## Overdue

```tasks
not done
due before today
show tree
sort by due
```

## Today

```tasks
not done
due today
show tree
sort by priority
```

## Upcoming 7 days

```tasks
not done
due after today
due before in 8 days
show tree
group by due
sort by due
```

## All tasks by folder

```tasks
not done
show tree
group by folder
sort by due
```

## Inbox unscheduled

```tasks
not done
path includes 00_Inbox
no due date
no scheduled date
show tree
sort by created
```
