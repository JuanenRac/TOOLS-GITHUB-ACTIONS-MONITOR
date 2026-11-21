<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_SECURITY.md) | [🇪🇸 Español](SENTINEL_SECURITY_spa.md) | [🇫🇷 Français](SENTINEL_SECURITY_fra.md) | [🇮🇹 Italiano](SENTINEL_SECURITY_ita.md) | [🇩🇪 Deutsch](SENTINEL_SECURITY_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](SENTINEL_SECURITY_jpn.md) | [🇵🇹 Português](SENTINEL_SECURITY_por.md)

# 安全哨兵

第三个哨兵，与 CI 哨兵和协作哨兵并列。它只读地获取 GitHub 自己对每个仓库安全方面未处理或缺失内容的说法，不向 GitHub 写入任何内容，并把它变成告警标签页中的告警（来源为“安全”）。它属于 Complete 版，默认关闭（`sentinels.security.enabled`）；Lite 没有哨兵。

## 读取什么、提示什么

| 信号 | 告警 | 级别 | 默认开启 |
|---|---|---|---|
| 严重程度达到 `min_severity` 及以上的未处理 Dependabot 告警（默认 high） | `security.dependabot` | 有严重的为 critical，有高的为 error，否则为警告 | 是 |
| 严重程度达到 `min_severity` 及以上的未处理代码扫描告警 | `security.code_scanning` | 同上 | 是 |
| 未处理的密钥扫描告警 | `security.secret` | 始终为 critical（GitHub 发现的密钥就是已泄露的密钥） | 是 |
| 默认分支没有保护 | `security.branch_unprotected` | 警告 | 是 |
| 工作流默认获得写入权限 | `security.workflow_write` | 警告 | 是 |
| 没有 CODEOWNERS 文件 | `security.codeowners_missing` | 提示 | 否 |
| 监视器见过的重要运行(推送到默认分支、手动运行、`pull_request_target` 运行)被删除 | `security.runs_deleted` | error | 否 |

**被删除的运行**(`security.runs_deleted`,默认关闭):密钥泄露后,删除打印出密钥的那次运行是清除痕迹的常见做法,而 GitHub 不留下可见记录。开启 `sentinels.security.signals.runs_deleted.enabled` 后,哨兵会保存一份简短的私有列表,记录它见过的重要运行;当某次运行不再出现在运行列表中时,就单独查询这一次运行:明确的 404 才算删除;拒绝(403)、网络错误或 5xx 从不计入。比 `sentinels.security.signals.runs_deleted.check_window_days`(14)更早的运行不再查询(账户的保留策略可能已将其清除),已发现的删除会以同样的天数保留为提醒。每个仓库每轮最多单独查询 `sentinels.security.signals.runs_deleted.max_checks`(50)次运行。提醒会写出工作流、触发者和分支,绝不包含运行的任何内容。

每个仓库每个信号一个告警，详情中带有按严重程度的计数。每个信号都可以关闭（`sentinels.security.signals.<信号>.enabled`），Dependabot 和代码扫描还可以设置不同的最低严重程度。已归档的仓库不再请求其他内容。

## 它无法检查的内容

GitHub 对某个仓库不回应的来源（该功能在那里是关闭的，或登录无权读取：403、404）**不是**告警，也**不是**健康证明。它会列在状态的 `unavailable` 下，并给出涉及的仓库数，页面也会说明。唯一的例外是默认分支的保护：GitHub 对没有保护的分支返回 404，这就是发现；那里的 403 只表示无法读取。

当计入扣分的大部分来源（Dependabot、代码扫描、密钥）无法读取时，级别为 `unknown` 而不是 `ok`，评分的安全部分会被排除，而不是按 100 计；状态会显示 `sources_readable` 和 `sources_total`。如果某个来源在告警未关闭时不再响应，该告警会保留一周（标有 `unread_since`），并且绝不会被宣布为已修复。读取持续失败的仓库会等待 5 分钟、30 分钟、然后 6 小时再重试，因此少数损坏的仓库不会耗尽整个轮次。

账户套餐中没有的来源(免费套餐下私有仓库的分支保护或代码扫描:GitHub 回答该功能需要其他套餐)会与被拒绝和功能关闭区分开:页面和状态中的 `unavailable_why` 显示 `N/A(套餐)`、`N/A(无权限)` 或 `N/A(未开启)`。`sentinels.security.plan_na` 开启(默认)时,第一类来源不计入可读数量和评分的覆盖率,而是单独计为 `sources_na_plan`;这三种情况都不是发现项,也不代表没有问题;若套餐中没有任何计入扣分的内容,哨兵为 `unknown`,评分不含安全部分。关闭时,它们按无法读取的来源计算。

现在每个哨兵都会给出自己的**生命周期**：`healthy`（正常）、`degraded`（降级：部分读取失败、某个来源无法读取，或尚未完成第一轮）、`paused`（暂停，等待 GitHub 额度）、`error`（出错且尚未读到任何内容）或 `off`（关闭）。只有生命周期为 `healthy` 时，“没有告警”才有意义。

## 成本

每轮最多读取 `sentinels.security.max_repos_per_tick` 个仓库（默认 5 个），先读很久没看的，有未处理告警的稍早一些，每 `sentinels.security.refresh_seconds` 秒一个周期（默认 30 分钟）。每个仓库最多七次读取，几乎都是条件读取，所以未变化的仓库不消耗额度；CODEOWNERS 文件在需要时每天最多查找一次。剩余额度低于 `sentinels.security.min_rate_remaining` 时哨兵会暂停。其状态（`security_state.json`）保存未处理的告警，因此重启不会重复通知，第一次查看某个仓库时也不写事件。 一轮在 `sentinels.security.deadline_s` 秒后(默认 30;0 = 无上限)也不再开始新的仓库:没轮到的等待下一轮,状态会把它们按名称列为 `unchecked`(并带有 `round_cut`),而不是算作零告警。

## 每个发现只有一个负责者

安全相关数字原本就在哨兵标签页中显示的面板（按仓库的告警、过期告警、Dependabot 和 CodeQL 的覆盖率、Dependabot 拉取请求）仍然是面板。告警标签页中关于这些信号的告警只来自这个哨兵，因此不会重复触发。 每个工作流文件的内容（未固定到提交的 Action、`write-all`、没有权限块、带检出的 `pull_request_target`）归[供应链哨兵](SENTINEL_SUPPLY_zho.md)负责；`security.workflow_write` 留在这里，因为它是仓库的设置。

## 事件和通知

新的发现会向事件流写入事件 `security_new`，已关闭的发现写入 `security_fixed`，通知渠道挂在事件流上；这两种类型都可以在通知设置中选择，按用户的偏好中也有“安全”选项。第一次查看某个仓库时不会通知。

## 设置

在设置页面的“哨兵”子标签中，“安全”区块：`sentinels.security.enabled`、`sentinels.security.refresh_seconds`、`sentinels.security.max_repos_per_tick`、`sentinels.security.min_rate_remaining`、`sentinels.security.repos`, `sentinels.security.plan_na`、`sentinels.security.signals.dependabot.enabled`、`sentinels.security.signals.dependabot.min_severity`、`sentinels.security.signals.code_scanning.enabled`、`sentinels.security.signals.code_scanning.min_severity`、`sentinels.security.signals.secret.enabled`、`sentinels.security.signals.branch.enabled`、`sentinels.security.signals.workflow.enabled` 和 `sentinels.security.signals.codeowners.enabled`, `sentinels.security.signals.runs_deleted.enabled`, `sentinels.security.signals.runs_deleted.check_window_days`, `sentinels.security.signals.runs_deleted.max_checks`。每个发现从评分的安全部分扣除的点数（`sentinels.security.penalty`）从文件中读取；见示例文件。

## 通过规则集的分支保护

默认分支只要有经典分支保护**或**有效的规则集，就视为受保护（仅由规则集保护的仓库在经典端点上返回 404，所以哨兵还会读取分支的 `protected` 标志和分支的有效规则）。`signals.branch.require` 可列出规则必须具备的规则类型（例如 `pull_request`、`required_status_checks`）；已保护但缺少其中某项的分支会连同缺少项一起提示。默认列表为空：任何保护都足够。因调用超时而无法读取的仓库会连同原因（`timeout`、`rate`、`network`、`error`）列在状态的 `errors` 和 `error_kinds` 中，绝不算作发现。
