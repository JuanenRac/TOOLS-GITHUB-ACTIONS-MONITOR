<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCORE.md) | [🇪🇸 Español](SCORE_spa.md) | [🇫🇷 Français](SCORE_fra.md) | [🇮🇹 Italiano](SCORE_ita.md) | [🇩🇪 Deutsch](SCORE_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](SCORE_jpn.md) | [🇵🇹 Português](SCORE_por.md)

# 账户评分

为每个账户给出一个 0 到 100 的数值、一个 A 到 E 的等级和一个趋势，仅依据监视器已掌握的信息（已完成的运行和协作哨兵的告警）。它属于 Complete 版；Lite 没有评分。

## 评分由什么组成

五个部分的加权和，每部分为 0 到 100。每个部分在其**良好**界限为 100，在其**较差**界限为 0，两者之间线性变化。权重和界限都是设置项。

| 部分 | 权重 | 衡量内容 | 良好 | 较差 |
|---|---|---|---|---|
| 可靠性 | 30 | 已完成运行中成功的比例（已取消和已跳过的不计） | 98 % | 50 % |
| 速度 | 15 | 成功运行耗时的第 95 百分位 | 10 分钟 | 60 分钟 |
| 恢复 | 15 | 工作流从首次失败到下一次成功的中位时间；仍为红色的工作流按其迄今为止处于红色的时间计算 | 30 分钟 | 24 小时 |
| 协作 | 15 | 协作哨兵的告警从出现到消失所保持打开的中位时间 | 2 天 | 14 天 |
| 安全 | 25 | 安全哨兵未处理的发现从 100 中扣除的点数（仅在该哨兵开启时） | 0 点 | 100 点 |

等级为：90 起为 A，80 起为 B，70 起为 C，55 起为 D，低于此为 E。趋势将评分与紧邻其前的窗口比较：上升、下降或持平（变化小于 `score.trend_flat` 点即为持平）。

## 没有数值的情况

评分从不显示它无法支撑的数值。回答总是带有 `state`、`coverage` 和 `data_quality`：

- **calibrating**（校准中）：账户被监视的时间不足 `score.calibrating_hours`（默认 24）。没有数值，也没有等级。
- **insufficient_data**（数据不足）：窗口内已完成的运行少于 `score.min_runs`（默认 20），或有数据的部分权重不足总权重的 `score.min_coverage`（默认一半）。没有数值。
- **scored**（已评分）：有数值、等级和趋势。没有数据的部分被舍去，其余部分重新缩放；这会降低 `coverage`（例如协作哨兵关闭时为 0.85）。它从不按 0 或 100 计算。

安全与其他部分一样，但只有在安全哨兵开启并已查看足够多的仓库时才有数据。没有它时，回答会写明 `complete: false`，并在 `missing_parts` 中列出 `security`，其他部分会重新缩放，因此该数值绝不会被理解为“一切正常”。GitHub 不提供发现项的历史，所以安全部分在窗口和其前一个窗口中相同：趋势显示的是 CI 和协作所做的变化。默认权重为 30、15、15、15 和 25。有运行而完全没有失败的窗口没有需要恢复的内容：其恢复部分为满分，这是事实而不是空缺。

窗口结束时仍为红色的工作流不会被遗忘：恢复部分按其迄今处于红色的时间计算，这是一个下限，红色持续多久就增长多久，因此无人修复的失败会让数值每小时降得更多。已修复的失败按其实际时间计算。一次运行的重新运行算作该工作流的又一次执行，因此失败的第一次尝试和绿色的第二次尝试都会被看到。如果从早期版本更新，有红色工作流的账户的数值可能比以前低。 当没有任何部分有数据时，回答为 `insufficient_data`，原因为 `no_data`。台账最多保留 20000 次运行：当不得不丢弃属于当前窗口的运行时，`data_quality.truncated` 为 true，且原因中包含 `truncated`，以免只看到窗口一部分的成功率被误认为完整。在 `GET /api/score/global` 中，快照已过期的账户会被排除在平均值之外并计入 `accounts_stale`，`/metrics` 不会导出过期快照的 `ghamon_score`。

## 窗口

窗口是评分所查看的运行天数：`score.window_days`，默认 7，由用户为每个账户选择。紧邻其前的、等长的窗口用于得出趋势。监视器保留一份已见过的已完成运行的小型账本，因此窗口可以比页面显示的最近运行列表更长。每小时保存一次快照，保存时长与分析历史相同（`retention.analytics_days`）。

## 按仓库和按账户

每个账户有自己的评分。其详情按仓库细分（仅 CI 部分，最差的在前）。整个安装没有单一的数值。 仅供参考，监督器的 `GET /api/score/global` 给出提问者可见的、已评分账户的平均值，按其有数值的仓库数加权，并始终注明纳入了多少个账户；没有数值的账户会被列出但不计入。

## 在页面上

页眉中、紧挨着就绪度标签的一个标签显示评分：数值、等级、与上一窗口相比变化的箭头，以及最近几天的小折线。其颜色随等级而定（A 和 B 为绿色，C 为琥珀色，D 和 E 为红色）。没有数值时它为中性色，并说明原因（校准中、数据不足）。等级后的星号表示有一个部分尚未计入（目前是安全性）：此时高分并不代表一切正常。鼠标悬停时显示覆盖率、各部分及其权重以及最弱的仓库。在 Lite 中或评分关闭（`score.enabled`）时不显示该标签。

## 供其他工具使用

指标（`/metrics`，在开启 Prometheus 输出时）带有三个无标签的序列：`ghamon_score_scored`（账户有数值时为 1）、`ghamon_score_coverage`（有数据的权重所占比例，0 到 1）和 `ghamon_score`（数值，仅在有数值时存在：没有数值时绝不会导出为 0）。MCP 服务器有一个只读工具 `get_score`，返回 API 的回答。`--demo` 显示一个虚构的评分，且不写入任何内容。 示例 Grafana 仪表盘（`docs/grafana/monitor_dashboard.json`）包含一个评分面板和一个评分随时间变化的面板。

## API

`GET /api/score` 返回账户的最新快照：`state`、`score`、`letter`、`trend`、`parts`、`coverage`、`data_quality`、`complete`、`missing_parts`、`repos`、`age_seconds` 和 `stale`（快照超过三小时则为真）。`GET /api/score/history` 返回随时间变化的点，最早的在前（`?hours=` 从现在向前，最多 90 天，`?limit=` 最多 2000）。缺失的数值为 `null`，绝不是 0。在团队模式下，能看到该账户的人都可以读取其评分；权重和界限是设置项，只有管理员可以更改。

## 评分下降告警

当评分与前一窗口相比下降 `score.alert.drop_points` 点（默认 10）或更多，或降到更低的等级时，告警标签页会显示告警 `score.dropped`（警告；等级为 E 时为严重），并给出旧评分和新评分。只要快照仍显示下降，它就一直存在，评分恢复后消失，并且可以像其他告警一样被静音。面板默认开启该告警。只有在 `score.alert.notify_external` 开启时（默认关闭），它才会通过外部通知渠道发出（事件 `score_dropped`），而且只在它出现的那一刻发送。`score.alert.enabled` 可关闭该告警。

## 设置

在设置页面的“哨兵”子标签中，“账户评分”“评分权重”和“评分等级”三个区块：`score.enabled`、`score.window_days`、`score.calibrating_hours`、`score.min_runs`、`score.min_coverage`、`score.trend_flat`、`score.weights.reliability`、`score.weights.speed`、`score.weights.recovery`、`score.weights.collaboration`, `score.weights.security`、`score.grades.A` 至 `score.grades.D`、`score.alert.enabled`、`score.alert.drop_points` 和 `score.alert.notify_external`（默认关闭）。每个部分的良好和较差界限从文件中读取，位于 `score.limits` 之下（见示例文件）；不在页面中编辑。
