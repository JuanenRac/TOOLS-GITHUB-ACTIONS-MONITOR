<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCORE.md) | [🇪🇸 Español](SCORE_spa.md) | [🇫🇷 Français](SCORE_fra.md) | [🇮🇹 Italiano](SCORE_ita.md) | [🇩🇪 Deutsch](SCORE_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](SCORE_jpn.md) | [🇵🇹 Português](SCORE_por.md)

# 账户评分

为每个账户给出一个 0 到 100 的数值、一个 A 到 E 的等级和一个趋势，仅依据监视器已掌握的信息（已完成的运行和协作哨兵的告警）。它属于 Complete 版；Lite 没有评分。

## 评分由什么组成

四个部分的加权和，每部分为 0 到 100。每个部分在其**良好**界限为 100，在其**较差**界限为 0，两者之间线性变化。权重和界限都是设置项。

| 部分 | 权重 | 衡量内容 | 良好 | 较差 |
|---|---|---|---|---|
| 可靠性 | 40 | 已完成运行中成功的比例（已取消和已跳过的不计） | 98 % | 50 % |
| 速度 | 20 | 成功运行耗时的第 95 百分位 | 10 分钟 | 60 分钟 |
| 恢复 | 20 | 工作流从首次失败到下一次成功的中位时间 | 30 分钟 | 24 小时 |
| 协作 | 20 | 协作哨兵的告警从出现到消失所保持打开的中位时间 | 2 天 | 14 天 |

等级为：90 起为 A，80 起为 B，70 起为 C，55 起为 D，低于此为 E。趋势将评分与紧邻其前的窗口比较：上升、下降或持平（变化小于 `score.trend_flat` 点即为持平）。

## 没有数值的情况

评分从不显示它无法支撑的数值。回答总是带有 `state`、`coverage` 和 `data_quality`：

- **calibrating**（校准中）：账户被监视的时间不足 `score.calibrating_hours`（默认 24）。没有数值，也没有等级。
- **insufficient_data**（数据不足）：窗口内已完成的运行少于 `score.min_runs`（默认 20），或有数据的部分权重不足总权重的 `score.min_coverage`（默认一半）。没有数值。
- **scored**（已评分）：有数值、等级和趋势。没有数据的部分被舍去，其余部分重新缩放；这会降低 `coverage`（例如协作哨兵关闭时为 0.8）。它从不按 0 或 100 计算。

安全性目前还不是评分的组成部分。在此之前，每个回答都会写明 `complete: false`，并在 `missing_parts` 中列出 `security`，因此 85 分绝不会被理解为“一切正常”。

## 窗口

窗口是评分所查看的运行天数：`score.window_days`，默认 7，由用户为每个账户选择。紧邻其前的、等长的窗口用于得出趋势。监视器保留一份已见过的已完成运行的小型账本，因此窗口可以比页面显示的最近运行列表更长。每小时保存一次快照，保存时长与分析历史相同（`retention.analytics_days`）。

## 按仓库和按账户

每个账户有自己的评分。其详情按仓库细分（仅 CI 部分，最差的在前）。整个安装没有单一的数值。

## 在页面上

页眉中、紧挨着就绪度标签的一个标签显示评分：数值、等级、与上一窗口相比变化的箭头，以及最近几天的小折线。其颜色随等级而定（A 和 B 为绿色，C 为琥珀色，D 和 E 为红色）。没有数值时它为中性色，并说明原因（校准中、数据不足）。等级后的星号表示有一个部分尚未计入（目前是安全性）：此时高分并不代表一切正常。鼠标悬停时显示覆盖率、各部分及其权重以及最弱的仓库。在 Lite 中或评分关闭（`score.enabled`）时不显示该标签。

## API

`GET /api/score` 返回账户的最新快照：`state`、`score`、`letter`、`trend`、`parts`、`coverage`、`data_quality`、`complete`、`missing_parts`、`repos`、`age_seconds` 和 `stale`（快照超过三小时则为真）。`GET /api/score/history` 返回随时间变化的点，最早的在前（`?hours=` 从现在向前，最多 90 天，`?limit=` 最多 2000）。缺失的数值为 `null`，绝不是 0。在团队模式下，能看到该账户的人都可以读取其评分；权重和界限是设置项，只有管理员可以更改。

## 设置

在设置页面的“哨兵”子标签中，“账户评分”“评分权重”和“评分等级”三个区块：`score.enabled`、`score.window_days`、`score.calibrating_hours`、`score.min_runs`、`score.min_coverage`、`score.trend_flat`、`score.weights.reliability`、`score.weights.speed`、`score.weights.recovery`、`score.weights.collaboration`、`score.grades.A` 至 `score.grades.D`、`score.alert.enabled`、`score.alert.drop_points` 和 `score.alert.notify_external`（默认关闭）。每个部分的良好和较差界限从文件中读取，位于 `score.limits` 之下（见示例文件）；不在页面中编辑。
