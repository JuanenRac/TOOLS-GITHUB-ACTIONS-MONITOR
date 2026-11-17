<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LARGE_ACCOUNTS.md) | [🇪🇸 Español](LARGE_ACCOUNTS_spa.md) | [🇫🇷 Français](LARGE_ACCOUNTS_fra.md) | [🇮🇹 Italiano](LARGE_ACCOUNTS_ita.md) | [🇩🇪 Deutsch](LARGE_ACCOUNTS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](LARGE_ACCOUNTS_jpn.md) | [🇵🇹 Português](LARGE_ACCOUNTS_por.md)

# 大型账户：数百个仓库

拥有数百个仓库、大量 fork 或多个组织的账户会很快用完 API 配额。下面是按节省效果排序的做法；所有设置都在“设置”标签页。

1. **先选一个配置档案。** 设置 > 基本 > 配置档案：*开源组织* 一键设定下面大部分内容（之后仍可逐项修改）。
2. **只监视在维护的。** `discovery.fork_policy` = `auto` 只保留有自己 CI 的 fork（账户类型决定时间窗口，`discovery.fork_ci_days`）；`discovery.fork_checks_per_pass` 把询问分摊到多次列表中。`discovery.skip_archived` 默认开启。`exclude` 和 `ecosystems` 按名称缩小列表。
3. **少问。** `cold_runs_per_repo` 和 `cold_refresh_seconds` 决定安静仓库的开销；`runs_per_repo` 和 `refresh_seconds` 决定活跃仓库的开销。`network.etag` 让无变化时的重复读取免费，低速模式（`modes.auto_low`）会在配额不足时自动放慢。
4. **给哨兵一个预算。** `sentinel.budget_per_hour`、`sentinel.max_calls_per_tick` 和 `sentinel.hygiene_seconds`（卫生检查默认每六小时对每个仓库发一次请求；可调长）限制 A3-A6 检查的花费。
5. **增加第二份配额。** `github_app.share_reads` 让 GitHub App 用自己的配额回答一部分读取。
6. **别淹没在噪音里。** 卫生检查（`sentinel.hygiene.ruleset_mode` = `effective`、`sentinel.hygiene.skip`）、发布文件检查（`sentinel.surface.checks.release_assets.allow_empty`）和 `sentinel.bots_apart` 可避免不适用于你仓库的检查堆积。

“配额”标签页显示各来源剩余多少，以及监视器自身花费多少。

对 fork 原仓库的跟踪(`upstream.enabled`)会在面板中说明,按 `upstream.requests_per_hour` 和 `upstream.forks_per_request` 的速度遍历所有 fork 需要多久;若超过 `upstream.refresh_hours`,跟踪就永远不会休息(727 个 fork、每次 8 个、每小时 6 次请求需要 15.2 小时)。最近一小时的请求在重启后会保留,因此重启不会归还配额。
