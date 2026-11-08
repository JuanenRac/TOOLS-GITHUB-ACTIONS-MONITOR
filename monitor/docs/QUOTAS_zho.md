<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](QUOTAS.md) | [🇪🇸 Español](QUOTAS_spa.md) | [🇫🇷 Français](QUOTAS_fra.md) | [🇮🇹 Italiano](QUOTAS_ita.md) | [🇩🇪 Deutsch](QUOTAS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](QUOTAS_jpn.md) | [🇵🇹 Português](QUOTAS_por.md)

# 配额与套餐

监视器会被各种类型的账户使用，因此不会预设任何一种。下面的数字保存在 `monitor/quotas.json` 中（编辑该文件即可在不发布新版本的情况下跟进 GitHub 的变化），并已对照 GitHub 的公开文档核对；它们会随时间变化，请作为起点，并查看文件中列出的页面。请在**设置 > 基本**中选择你的套餐（`account.plan`）；在其为*未知*时不显示任何配额数字。

## API 配额

| 登录方式 | 每小时调用次数 |
|---|---|
| 未登录 | 每个地址每小时 60 次 |
| 你自己的登录（`gh auth login`）或个人令牌 | 5,000 |
| 工作流的令牌（Actions 内） | 每个仓库 1,000（Enterprise Cloud 为 15,000） |
| Enterprise Cloud 上的应用 | 15,000 |
| 其他情况的 GitHub App | 5,000，随安装规模增长至最高 12,500 |

页面显示从 GitHub 响应头（`X-RateLimit-*`）读取的真实限额，绝不假定 5,000：这也让 GitHub Enterprise Server（`GH_HOST`）能正常工作。未登录（每小时 60 次）时会提示运行 `gh auth login`。另有*次级*限制（并发请求不超过 100 个以及突发）：GitHub 以此响应时，监视器至少等待一分钟，随后将等待时间加倍至最多五分钟，绝不连续猛攻。

## Actions 分钟数

| 套餐 | 每月包含（金额） | 折合 Linux 分钟 | 制品存储 |
|---|---|---|---|
| Free | $12 | 2,000 | 500 MB |
| Pro | $18 | 3,000 | 1 GB |
| Team | $18 | 3,000 | 2 GB |
| Enterprise Cloud | $300 | 50,000 | 50 GB |

**公开仓库在任何套餐下都不消耗分钟数**（自托管运行器也一样）；更大的运行器始终计费。1 分钟要乘以其系统的费率：Windows 约为 Linux 的 1.67 倍，macOS 约为 10.3 倍（`quotas.json` 中为每分钟费率：Linux $0.006、Windows $0.010、macOS $0.062）。监视器在**设置 > 基本 > 套餐与配额**中显示的是**估算**：最近 24 小时 run 的时长，向上取整到分钟，仅限私有仓库，使用你在 `quota.default_runner` 中假定的系统，并把一天的速度乘以当月天数。真实数字只来自可选开关 `quota.billing_api`（默认关闭、只读，需要有权查看账单的登录；遇到 403 或 404 时保留估算并明确说明）。当达到所含分钟数的 `quota.warn_percent`（75%）和 `quota.alert_percent`（90%）时，会通过通知每月各提醒一次。

## 并发与上限

| 套餐 | 同时运行的作业 | 其中 macOS |
|---|---|---|
| Free | 20 | 5 |
| Pro | 40 | 5 |
| Team | 60 | 5 |
| Enterprise | 500 | 50 |

面板把运行中和排队中的作业与你套餐的上限比较，达到 90% 或上限已满仍有作业等待时发出警告。GitHub 托管运行器上单个作业最长 6 小时（面板会列出超过其 80% 的作业），一次工作流 run 最长 35 天，矩阵最多 256 个作业。

## 未涵盖的内容

不跟踪额外分钟的单价、更大的运行器、已用存储、Codespaces 和 Packages；套餐表只是起点，macOS 的限额也会变化。以上内容尚未对真实的账单报告进行过测试：对 `usageItems` 的读取依据公开说明，失败时会静默退回估算。
