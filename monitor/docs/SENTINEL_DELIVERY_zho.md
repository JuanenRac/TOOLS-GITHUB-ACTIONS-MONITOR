<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_DELIVERY.md) | [🇪🇸 Español](SENTINEL_DELIVERY_spa.md) | [🇫🇷 Français](SENTINEL_DELIVERY_fra.md) | [🇮🇹 Italiano](SENTINEL_DELIVERY_ita.md) | [🇩🇪 Deutsch](SENTINEL_DELIVERY_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](SENTINEL_DELIVERY_jpn.md) | [🇵🇹 Português](SENTINEL_DELIVERY_por.md)

# 交付哨兵

第五个哨兵，与 CI、Collab、安全和供应链哨兵并列。它不向 GitHub 写入任何内容，只通过 API（无需克隆）读取每个仓库最新的发布、最新的标签、CHANGELOG 以及你指定的版本文件，并提示已构建但未交付的内容。结果变成警报页签中的警报（来源：交付）。它属于 Complete 版，默认关闭（`sentinels.delivery.enabled`）；Lite 没有哨兵。

它在菜单的哨兵组中有自己的入口 **交付哨兵**（地址 `#sentinel-delivery`），哨兵开启时显示：一个面板列出每个仓库的未解决发现、其周期的状态以及无法读取的内容；入口的徽标统计错误数。

## 它提示什么

| 信号 | 警报 | 级别 | 默认开启 |
|---|---|---|---|
| CHANGELOG 的 `[Unreleased]` 下有条目，而最新已发布版本已超过 `sentinels.delivery.unreleased_days` 天（14） | `release.unreleased_pending` | info | 是 |
| 有比最新已发布版本更新的版本标签，且该标签没有自己的发布（草稿不算已交付） | `release.tag_without_release` | warning | 是 |
| 最新已发布版本的说明为空 | `release.release_without_notes` | info | 是 |
| `version_files` 中列出的版本文件与 CHANGELOG 的第一个带版本号的标题声明的版本不全相同（`1.2` 与 `1.2.0` 视为相同） | `release.version_mismatch` | warning | 是 |
| 某仓库固定的版本低于提供共享契约的仓库的最新发布（`sentinel.readiness.pins.sources` 中类型为 `pin_table` 的固定表） | `release.ecosystem_drift` | warning | 是 |
| 最新已发布版本缺少与 `expected_assets` 中某个模式（例如 `*.zip`、`SHA256SUMS*`）匹配的文件 | `release.assets_missing` | warning | 是 |

每个仓库、每个信号一条警报，详情中带有数量以及一些标签、模式或版本。每个信号都可以关闭（`sentinels.delivery.signals.<信号>.enabled`），也可以改变级别（`info`、`warning`、`error`、`critical`）。完全没有已发布版本的仓库不会被关于发布的信号评判：它不使用发布。预发布和草稿永远不会被当作最新发布。

## 每个发现只有一个归属

哨兵页签的就绪度面板（A11）是基于本地克隆的每个仓库一行；这个哨兵则通过 API（无需克隆）产生带稳定标识、静音、事件和自有周期的警报。关于仓库工作流的信号属于供应链哨兵，关于 GitHub 设置的信号属于安全哨兵：不会重复发出。路线图中可选的“Releases”插件由这个哨兵取代。

## 它无法检查的内容

无法读取的仓库（无访问权限、SSO 未授权、额度用尽、一轮的调用次数少于一个仓库所需）**不是**警报，也**不是**一切正常。它会列在状态的 `unavailable` 下，附带原因和数量；当所查看的大部分无法读取时，级别 `ok` 会显示为 `unknown`。如果某个有警报的仓库不再应答，其警报会保留一周（标记 `unread_since`），并且绝不会被宣告为已解决。不存在的文件（该路径下没有 CHANGELOG、没有这个版本文件）只是视为缺失。固定表每个周期读取一次；读取不了的固定表保留原有警报，并同样列出。

## 成本

每轮最多读取 `sentinels.delivery.max_repos_per_tick` 个仓库（默认 10），最多进行 `sentinels.delivery.max_calls_per_tick` 次调用（60）：发布一次、标签一次、CHANGELOG 一次（如果你列了多个路径且前面的不存在则更多），每个版本文件一次。已关闭的信号完全不读取。最久未读取的优先，有未关闭警报的稍微提前；每 `sentinels.delivery.refresh_seconds` 一个周期（默认一小时）。没有条件请求：成本由这些设置限定，而不是靠 304 应答。当剩余额度低于 `sentinels.delivery.min_rate_remaining` 时哨兵暂停。它的状态（`delivery_state.json`）保存未关闭的警报，所以重启不会重复宣告任何内容，首次查看某个仓库也不会写入事件。 一轮在 `sentinels.delivery.deadline_s` 秒后(默认 30;0 = 无上限)也不再开始新的仓库:没轮到的等待下一轮,状态会把它们按名称列为 `unchecked`(并带有 `round_cut`),而不是算作零告警。

## 事件、通知与评分

新的发现写入事件 `delivery_new`，已关闭的写入 `delivery_fixed`（事件中包含 `sentinel: delivery` 和警报的代码）。它们属于发布类别，所以只有维护者和管理员可以选择，每位用户通知偏好中对哨兵 `ci` 的选择决定谁会收到；它们不在任何默认事件列表中。指标包含 `delivery_alerts`、`delivery_unreleased_repos`、`delivery_unreleased_days_max`、`delivery_repos_checked`、`delivery_repos_unreadable` 和 `delivery_calls_last_hour`。评分不使用它们。API 响应 `GET /api/sentinel/delivery`，警报页签和 `monitor_cli.py alerts --sentinel delivery` 可以按它过滤。

## 设置

在设置页面的哨兵子页签、交付区块中：`sentinels.delivery.enabled`, `sentinels.delivery.refresh_seconds`, `sentinels.delivery.max_repos_per_tick`, `sentinels.delivery.max_calls_per_tick`, `sentinels.delivery.min_rate_remaining`, `sentinels.delivery.repos`, `sentinels.delivery.unreleased_days`, `sentinels.delivery.unreleased_min_entries`, `sentinels.delivery.changelog_paths`, `sentinels.delivery.version_files`, `sentinels.delivery.expected_assets`, `sentinels.delivery.signals.unreleased_pending.enabled`, `sentinels.delivery.signals.unreleased_pending.level`, `sentinels.delivery.signals.tag_without_release.enabled`, `sentinels.delivery.signals.tag_without_release.level`, `sentinels.delivery.signals.release_without_notes.enabled`, `sentinels.delivery.signals.release_without_notes.level`, `sentinels.delivery.signals.version_mismatch.enabled`, `sentinels.delivery.signals.version_mismatch.level`, `sentinels.delivery.signals.ecosystem_drift.enabled`, `sentinels.delivery.signals.ecosystem_drift.level`, `sentinels.delivery.signals.assets_missing.enabled`, `sentinels.delivery.signals.assets_missing.level`.

## 它不做什么

它不向 GitHub 写入任何内容（没有标签、发布、标记、拉取请求或议题），不发布也不签名任何东西，不会根据警报创建提案，也不读取除 CHANGELOG 和你指定的版本文件之外任何文件的内容。
