<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LARGE_ACCOUNTS.md) | [🇪🇸 Español](LARGE_ACCOUNTS_spa.md) | [🇫🇷 Français](LARGE_ACCOUNTS_fra.md) | [🇮🇹 Italiano](LARGE_ACCOUNTS_ita.md) | [🇩🇪 Deutsch](LARGE_ACCOUNTS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](LARGE_ACCOUNTS_jpn.md) | [🇵🇹 Português](LARGE_ACCOUNTS_por.md)

# 大型账户：数百个仓库

拥有数百个仓库、大量 fork 或多个组织的账户会很快用完 API 配额。下面是按节省效果排序的做法；所有设置都在“设置”标签页。

1. **先选一个配置档案。** 设置 > 基本 > 配置档案：*开源组织* 一键设定下面大部分内容（之后仍可逐项修改）。
2. **只监视在维护的。** `discovery.fork_policy` = `auto` 只保留有自己 CI 的 fork（账户类型决定时间窗口，`discovery.fork_ci_days`）；`discovery.fork_checks_per_pass` 把询问分摊到多次列表中。`discovery.skip_archived` 默认开启。`exclude` 和 `ecosystems` 按名称缩小列表。 为空的账户列表,或不足上次正常列表 `discovery.min_keep_pct` 百分比的列表,不会被采信:保留上次正常列表,五分钟后重新读取,面向 AI 工具的简报中会出现信号 repos.listing。 `discovery.hide` 也接受 `public`(以及 `private`、`fork`、`empty`);基本标签页会统计每条规则排除的数量,因此被过滤器排除的内容不会被当作干净。
3. **少问。** `cold_runs_per_repo` 和 `cold_refresh_seconds` 决定安静仓库的开销；`runs_per_repo` 和 `refresh_seconds` 决定活跃仓库的开销。`network.etag` 让无变化时的重复读取免费，低速模式（`modes.auto_low`）会在配额不足时自动放慢。
4. **给哨兵一个预算。** `sentinel.budget_per_hour`、`sentinel.max_calls_per_tick` 和 `sentinel.hygiene_seconds`（卫生检查默认每六小时对每个仓库发一次请求；可调长）限制 A3-A6 检查的花费。
5. **增加第二份配额。** `github_app.share_reads` 让 GitHub App 用自己的配额回答一部分读取。
6. **别淹没在噪音里。** 卫生检查（`sentinel.hygiene.ruleset_mode` = `effective`、`sentinel.hygiene.skip`）、发布文件检查（`sentinel.surface.checks.release_assets.allow_empty`）和 `sentinel.bots_apart` 可避免不适用于你仓库的检查堆积。

“配额”标签页显示各来源剩余多少，以及监视器自身花费多少。

对 fork 原仓库的跟踪(`upstream.enabled`)会在面板中说明,按 `upstream.requests_per_hour` 和 `upstream.forks_per_request` 的速度遍历所有 fork 需要多久;若超过 `upstream.refresh_hours`,跟踪就永远不会休息(727 个 fork、每次 8 个、每小时 6 次请求需要 15.2 小时)。最近一小时的请求在重启后会保留,因此重启不会归还配额。

哨兵一次 tick 的调用(`sentinel.max_calls_per_tick`)对其所有阶段是同一个计数;读取连续失败三次的仓库会被搁置 30 秒(翻倍,最多 10 分钟),期间读取其他仓库。

机群标签页还有一个按[工作流角色和分组的可选区块，每个分组都有自己的屏幕](FLEET_APIS_zho.md)。

## 读取队列、限制和一次读取供大家共用

- **背压**（`backpressure.enabled`，默认关闭）：一个周期的读取经过一个有界队列（先是有红色工作流的仓库，然后是热点仓库、从未读取的仓库和最久未读取的）。`backpressure.max_reads_per_cycle` 设置固定数量（0 = 无）；当一个周期超过周期间隔的 `backpressure.shed_percent` 百分比时，允许的读取数减半（不低于 `backpressure.min_reads`），每个较快的周期之后恢复十分之一。等待的仓库保留最后的画面，并在下一个周期最先读取。`/metrics` 显示 `ghamon_read_queue_*`。
- **限制与 doctor**：`monitor_cli.py doctor` 有一个 `capacity` 检查，把配置与其上限比较（相对于配额和 `sampling.api_budget_per_hour` 的每小时调用数、相对于 `limits.memory_mb` 的已保存运行内存、相对于 `discover_limit` 的仓库数），从 `limits.warn_percent` 起警告。运行中的情况在 `/metrics` 中显示为 `ghamon_limit_used_percent{limit=...}`（保存的事件、流、读取队列、直方图序列）。
- **一次读取供大家共用**（`refresh.share_by_workflow`，默认关闭）：当周期、页面、墙屏或 API 客户端同时请求同一次运行的作业时，第一个从 GitHub 读取，其余的使用它的结果，有效 `refresh.share_seconds` 秒。`/metrics` 统计节省的读取次数（`ghamon_shared_reads_spared_total`）。
