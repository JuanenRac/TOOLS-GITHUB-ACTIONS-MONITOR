<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPARE.md) | [🇪🇸 Español](COMPARE_spa.md) | [🇫🇷 Français](COMPARE_fra.md) | [🇮🇹 Italiano](COMPARE_ita.md) | [🇩🇪 Deutsch](COMPARE_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](COMPARE_jpn.md) | [🇵🇹 Português](COMPARE_por.md)

# 对比时段

这一周和上一周相比如何？对比用监控器已经保存的数据回答这个问题（已完成运行与告警的台账，以及评分的每小时快照）。它不会从 GitHub 读取任何内容，不写入任何内容，不需要 AI，也不会编造任何数据。它仅存在于 Complete 版，并且在你开启 `compare.enabled` 之前保持**关闭**。

## 两个时段

- **时段**：最近 7 天（或 30 天，或不超过 90 的任意天数），也可以用 `from` 和 `to` 指定精确范围。
- **基准**：`previous`（紧邻其前、长度相同的时段，默认）、`year_ago`（一年前的相同日期）或 `custom`（`base_from` 和 `base_to`）。
- **日期**：`all`、`workdays` 或 `weekend`。该过滤器作用于每个数值。某个时刻属于哪一天，按 `display.timezone` 的时区计算；工作日由 `compare.workdays` 决定（周一 = 1 到周日 = 7，默认周一至周五）。不识别法定节假日：节假日按其所在的星期几计算。

把工作日和周末混在一起会掩盖问题（只在周六出现的故障，在混合数据的一周里分量很小），这就是设置过滤器的原因。

## 数值

| 数值 | 计算方式 | 何时更好 |
|---|---|---|
| `red_rate` | 在时段内开始的运行中，失败数 /（成功数 + 失败数） | 越低越好 |
| `duration_p50` | 成功运行耗时（秒）的中位数 | 越低越好 |
| `resolution` | 协作哨兵在时段内关闭的告警，从打开到关闭的时间中位数 | 越低越好 |
| `score_mean` | 有评分的每小时快照的平均评分 | 越高越好 |
| `score_coverage` | 评分中有数据部分的平均占比 | 越高越好 |

每个数值都带有 `now`、`base`、`delta`、`direction`（`better`、`worse`、`same`）和 `state`。已取消、已跳过和未完成的运行不计入任何一方。

## 没有数值时

对比从不显示它无法担保的数字：缺失的数值是 `null`，绝不是 0 或 100。

- `insufficient_data`：两个时段之一中，已完成运行少于 `compare.min_runs_per_window`，已解决告警少于 `compare.min_resolved`，或快照少于 `compare.min_snapshots`。响应会说明是哪个时段以及原因（`missing`）。
- `baseline_unavailable`：用于对比的基准时段不可靠。原因是 `history_too_short`（监控器监视的时间不足 `compare.min_days_of_history` 天）、`before_history`（该时段早于已保存的数据）或 `no_history`。当前时段的数值仍会显示。
- `calibrating`：监控器还没有监视满 `score.calibrating_hours` 小时，不进行任何对比。
- `off`：`compare.enabled` 已关闭。

`data_quality` 包含每个时段统计的运行数，以及台账不得不丢弃旧运行时的 `truncated`。`coverage` 是能够完成对比的数值所占的比例。

## 发生了什么变化

除数值外，还有：变差或变好的仓库（其失败运行占比的变化，仅限两个时段都至少有 `compare.min_repo_runs` 次运行的仓库）、开始失败的工作流和不再失败的工作流，以及在时段内打开、到时段结束时仍未关闭的告警数量。每个列表最多 `compare.top_changes` 行，按变化幅度排序，其次按名称。台账不保存协作哨兵告警所属的仓库，因此它们只以数量出现，不会按名称列出。

## 能回溯多远

对比读取评分的台账。只要 `compare.enabled` 处于开启状态，台账就会保留两个长度为 `compare.default_window_days` 的时段（至少 15 天），而不是评分的两个窗口；它不会比监控器本身更早，所以新安装的实例要有 60 天的历史，才能把 30 天与 30 天对比。

## API

`GET /api/compare?window=7&days=workdays&baseline=previous`（还可使用 `from`、`to`、`base_from`、`base_to`）。响应包含 `state`、`windows`、`metrics`、`changes`、`alerts`、`coverage` 和 `data_quality`。`format=ndjson` 或 `format=csv` 会为每个数值输出一行。无意义的请求会返回 400 以及稳定的 `code`：`bad_range`（from 晚于 to、超过 90 天、在未来）、`bad_window`、`bad_days`、`bad_baseline` 或 `bad_format`。查看者可以读取；它只提供该进程所服务的账户，绝不提供其他账户。开启读取 API v1 后，也可通过前缀 `/api/v1/` 访问。Lite 版中没有它。

## 命令行

`monitor_cli.py compare [--window 7|30d] [--days all|workdays|weekend] [--baseline previous|year_ago] [--format table|json|ndjson|csv]`。退出码：0 表示全部完成对比；4 表示某个数值数据不足、没有基准或对比已关闭；5 表示使用 `--fail-on` 时某个数值变差。`score --compare` 仍然把评分与其窗口的历史进行对比。

## 页面上

对比开启后，“图表”标签页会显示“对比时段”部分：时段、日期和基准的选择器，每个数值一行及其变化，以及告警和变化列表。

## 设置

设置，哨兵标签，“时段对比”区块：`compare.enabled`、`compare.default_window_days`、`compare.default_days_filter`、`compare.workdays`、`compare.min_runs_per_window`、`compare.min_days_of_history`、`compare.min_resolved`、`compare.min_snapshots`、`compare.min_repo_runs`、`compare.top_changes`、`compare.include_in_report` 和 `compare.cache_seconds`。结果会保留 `compare.cache_seconds` 秒，之后重新计算。
