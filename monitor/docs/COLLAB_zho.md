<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COLLAB.md) | [🇪🇸 Español](COLLAB_spa.md) | [🇫🇷 Français](COLLAB_fra.md) | [🇮🇹 Italiano](COLLAB_ita.md) | [🇩🇪 Deutsch](COLLAB_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](COLLAB_jpn.md) | [🇵🇹 Português](COLLAB_por.md)

# Collab 哨兵：Issue 与拉取请求

在 CI 哨兵旁边的第二个哨兵。它查看你仓库中**未关闭的 Issue 和拉取请求**，告诉你哪些需要人来处理：被遗忘的 Issue、严重标签、没人做的评审、永远不结束的草稿、一直存在的冲突。它有自己的周期，从不改变 CI 哨兵的判断，也**从不向 GitHub 写入任何内容**。它属于完整版；精简版不会加载它。

## 开启

默认关闭。设置 > 哨兵 > Issue 与拉取请求，或在 `actions_monitor.json` 中设置：

```
"sentinels": {"collab": {"enabled": true, "refresh_seconds": 600, "max_repos_per_tick": 10, "repos": "all",
  "rules": {"issue_stale_days": 14, "issue_critical_labels": ["security", "critical"], "pr_review_pending_days": 3,
            "pr_draft_max_days": 30, "pr_conflict_days": 7, "watch_external_comments": false, "ignore_labels": ["monitor:ignore"]}}}
```

`repos` 可以是 `"all"`、仓库列表，或 `{"ecosystems": [...]}`。

## 规则（稳定的代码）

| 代码 | 级别 | 条件 |
|---|---|---|
| `collab.issue.stale` | 警告 | 未关闭的 Issue 在 `issue_stale_days` 天内没有任何活动 |
| `collab.issue.critical` | 错误 | 未关闭的 Issue 带有 `issue_critical_labels` 中的标签，无论多久 |
| `collab.issue.external` | 警告 | （仅在启用 `watch_external_comments` 时）团队外的人提出的 Issue，一天后仍无人回复 |
| `collab.pr.review_pending` | 警告 | 已请求评审的拉取请求等待了 `pr_review_pending_days` 天 |
| `collab.pr.draft_old` | 信息 | 草稿拉取请求已开启 `pr_draft_max_days` 天 |
| `collab.pr.conflict` | 警告 | 拉取请求存在冲突已达 `pr_conflict_days` 天 |

机器人不计入。默认值故意放得很慢：在许多团队里，草稿等上几个月是正常的。

## 开销

每一轮最多读取 `max_repos_per_tick` 个仓库，每个仓库两次条件请求（没有变化的仓库不消耗配额），每轮最多读取六个拉取请求详情。配额低于 `min_rate_remaining` 时暂停。状态保存在 `collab_state.json`（多账户时在该账户的文件夹内），所以重启不会重复通知。

## 减少噪音：忽略与静音

- **忽略标签**：在 **GitHub 上**给 Issue 或拉取请求加上 `ignore_labels` 中的标签（默认 `monitor:ignore`），Collab 就不再为它发警报。监视器自己从不写标签。
- **在监视器中静音**：在“警报”标签页中，每个警报都有按钮，可将该警报、其规则或整个哨兵静音 `alerts.mute_hours` 小时（默认 24，范围 1 到 720）。静音会自动到期，随时可以恢复，标签页还保留一份简短历史，记录静音了什么、到何时。这只是此监视器内部的一条记录,GitHub 上不会有任何变化。在网络模式下,静音只能在运行监视器的那台计算机上设置(和解除)(`this_computer`);网络中的客户端能看到静音但不能更改。在后续版本拥有自己的用户之前,这一点保持不变。单条警报的静音也可以持续到“该项目发生变化为止”(`POST /api/alerts/mute` 请求中的 `until_change`):当 issue 或拉取请求的 `updated_at` 变化,或小时数结束时(以先到者为准)立即结束。

## 在哪里查看

- **警报**标签页：所有哨兵合在一个列表，可按来源（CI、Collab）和级别筛选，也可按需显示已静音的。
- 哨兵标签页：*Issue 与拉取请求*层。
- `GET /api/alerts?sentinel=collab&level=&muted=show|hide|only` 和 `GET /api/sentinel/collab`；事件用 `GET /api/events?sentinel=collab&since=`（`collab_new`、`collab_fixed`，选择后通知渠道也会发送；见 NOTIFICATIONS）。

## 限制

每个仓库只读取最近更新的前 100 个未关闭 Issue 和前 100 个未关闭拉取请求。Collab 不提出建议也不执行任何操作；针对 Issue 和拉取请求的操作属于以后的版本。
