<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ANALYTICS.md) | [🇪🇸 Español](ANALYTICS_spa.md) | [🇫🇷 Français](ANALYTICS_fra.md) | [🇮🇹 Italiano](ANALYTICS_ita.md) | [🇩🇪 Deutsch](ANALYTICS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](ANALYTICS_jpn.md) | [🇵🇹 Português](ANALYTICS_por.md)

# 分析、条件读取与连接丢失

监视器从已读取的运行中学到什么,如何节省配额,以及如何在断网时存活。一切都在本地;不会向任何地方发送内容。

## 时长、排队时间与步骤

- 每个工作流成功运行时长的 `p50` 和 `p95`;作业开始前等待的时间(从创建到开始);以及工作流每个步骤的 `p50` 和 `p95`。工作流有 `analytics.min_samples` 个样本后才显示数据。
- 作业和步骤的时间需要已完成运行的作业:每个周期最多读取 `analytics.jobs_per_cycle` 个运行,每个只读一次(0 表示不读)。入站 Webhook 可免费提供这些数据。
- 它们以 `ghamon_workflow_duration_seconds`、`ghamon_job_queue_seconds` 和 `ghamon_step_duration_seconds` 导出(标签 `quantile` 0.5 / 0.95;需要 `per_repo`),也在 Grafana JSON 数据源中(`durations`、`queue`)。`slower` 列出 p50 达到平时 `analytics.slow_factor` 倍的工作流。


## 不稳定的工作流(flaky)

在同一提交上先失败后通过(或其运行需要再次尝试)的工作流会被标记为不稳定:`ghamon_workflow_flaky_rate`。这只是标签:什么算“红色”不会改变。


## 条件读取(ETag)

- 每次读取运行列表都会发送 `If-None-Match`;没有变化时 GitHub 返回 `304 Not Modified`,该响应不消耗配额。页眉显示节省了多少次读取,`ghamon_etag_saved_total` 对其计数。`cache.etag.enabled` 和 `cache.etag.ttl_hours` 在设置标签页中。
- 缓存是本地文件 `etag_cache.json`(从不发布);损坏的文件只会变成空缓存。


## 连接丢失时

如果某个周期的所有读取都因连接问题(而非登录或配额问题)失败,页面会保留最后的画面并显示红色横幅“自 HH:MM 起无连接”。不会抛出异常;监视器会自动恢复,并各写入一次 `offline` 和 `online` 事件(可被通知)。期间 `ghamon_offline` 为 1。

## 历史保留多久

除了分析区块里的 `keep_days`,保留任务还会删除早于 `retention.analytics_days`(默认 180)的历史日期;样本数量本身由 `max_samples` 限制。详见 [STORAGE_zho.md](STORAGE_zho.md)。
