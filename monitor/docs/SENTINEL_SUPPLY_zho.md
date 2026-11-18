<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_SUPPLY.md) | [🇪🇸 Español](SENTINEL_SUPPLY_spa.md) | [🇫🇷 Français](SENTINEL_SUPPLY_fra.md) | [🇮🇹 Italiano](SENTINEL_SUPPLY_ita.md) | [🇩🇪 Deutsch](SENTINEL_SUPPLY_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](SENTINEL_SUPPLY_jpn.md) | [🇵🇹 Português](SENTINEL_SUPPLY_por.md)

# 供应链哨兵

第四个哨兵，与 CI、协作和安全哨兵并列。它不向 GitHub 写入任何内容，通过 API（无需克隆）读取每个仓库的工作流文件（`.github/workflows`），并标出可让被移动的标签或外部人员借用仓库令牌和代码行事的地方，将其转为“警报”标签页中的警报（来源：供应链）。它属于完整版，默认关闭（`sentinels.supply.enabled`）；精简版没有哨兵。

它在菜单的哨兵组中有自己的入口 **供应链哨兵**（地址 `#sentinel-supply`），哨兵开启时显示：一个面板列出每个仓库的未解决发现、其周期的状态以及无法读取的内容；入口的徽标统计错误数。

## 它标出什么

| 信号 | 警报 | 级别 | 默认开启 |
|---|---|---|---|
| Action 或可复用工作流的 `uses:` 未固定到完整的提交 SHA（其所有者可以移动标签） | `actions.supply.unpinned` | warning | 是 |
| `uses:` 跟随会自行移动的分支（`@main`、`@master` 等）：比标签更糟 | `actions.supply.mutable_ref` | warning | 是 |
| 带有 `permissions: write-all` 的工作流 | `actions.supply.permissions_wide` | warning | 是 |
| 没有 `permissions:` 块的工作流（令牌获得更宽的默认权限） | `actions.supply.permissions_missing` | warning | 是 |
| `pull_request_target` 同时检出拉取请求的代码 | `actions.supply.pr_target_checkout` | error | 是 |

每个仓库和每个信号对应一条警报，详情中包含发现数量、所在文件和少量示例（Action 的名称）。每个信号都可以关闭（`sentinels.supply.signals.<信号>.enabled`）并设置其他级别（`info`、`warning`、`error`、`critical`）。指向同一仓库工作流的 `uses:` 不属于第三方，会被略过。

## 唯一的事实来源

它没有自己的规则：发现来自工作流检查器（`bin/lint_workflows.py`，与“哨兵”标签页和命令行使用的相同），这里只启用 `unpinned_uses`、`permissions` 和 `pr_target`，其余规则保持关闭。尤其是查找文件中明文密钥的规则是关闭的，因此**密钥的值从不被读取、保存或显示**。`lint.own_owners` 和 `lint.unpinned_own` 设置仍决定如何对待自己账户的 Action，工作流中的注释 `# monitor-lint: ignore 规则` 可就地静音一条发现。

## 每个发现只有一个归属

`security.workflow_write`（安全哨兵）是仓库的默认权限，属于 GitHub 的设置；这里的信号针对每个工作流文件的内容，因此同一个仓库不会从两边发出相同的发现。“哨兵”标签页的 lint 面板仍是面板；“警报”标签页中关于这些信号的警报只来自这里。

## 它无法检查什么

工作流无法读取的仓库（无权访问、SSO 未授权、额度用尽、文件夹文件过多）**不是**警报，也**不代表**健康。它会列在状态的 `unavailable` 下，附带原因和仓库数量；当所查看内容的大部分无法读取时，`ok` 级别会显示为 `unknown`。如果某个有警报的仓库不再响应，这些警报会保留一周（标记 `unread_since`），且绝不会被宣告为已修复。没有 `.github/workflows` 文件夹的仓库会被读取，只是没有可报告的内容。读取持续失败的仓库会先等 5 分钟、30 分钟，然后 6 小时再重试。

## 成本

每轮最多读取 `sentinels.supply.max_repos_per_tick` 个仓库（默认 10），最多进行 `sentinels.supply.max_calls_per_tick` 次调用（60）：列出一个仓库的工作流一次，每个新增或更改的文件再一次，因为 SHA 未变的文件不会再次读取。最久未读的优先，有未关闭警报的稍早一些；周期为每 `sentinels.supply.refresh_seconds`（默认一小时）。当剩余额度低于 `sentinels.supply.min_rate_remaining` 时哨兵暂停。其状态（`supply_state.json`）保存未关闭的警报，因此重启不会重复通知，对仓库的首次查看也不会写入事件。`sentinels.supply.max_files_per_repo` 限制在一个仓库中读取的文件数；超出的仓库只会被部分读取并计为部分。

## 忽略一条发现

`sentinels.supply.ignore` 接受 `仓库:文件:规则` 模式（`*` 表示任意），其中规则指检查器的规则，例如 `myrepo:release.yml:unpinned_uses`；注意 `unpinned_uses` 是 `unpinned` 和 `mutable_ref` 背后的规则，`permissions` 是两个权限信号背后的规则。`lint.ignore` 的模式在这里不适用。

## 事件、通知与评分

新发现写入事件 `security_new`，已关闭的写入 `security_fixed`（事件带有 `sentinel: supply` 和警报代码），因此每个用户通知偏好中的“安全”选项和各渠道决定谁会收到通知。首次查看某个仓库时不会通知。指标包含 `supply_alerts`、`supply_findings`、`supply_penalty`（仅供参考：`sentinels.supply.penalty.per_finding`（2）和 `cap_per_repo`（10）从文件读取）、`supply_repos_checked`、`supply_repos_unreadable` 和 `supply_calls_last_hour`。评分不使用该扣分。API 提供 `GET /api/sentinel/supply`，“警报”标签页和 `monitor_cli.py alerts --sentinel supply` 可按它过滤。

## 设置项

在“设置”页面的“哨兵”子标签、“供应链”块中：`sentinels.supply.enabled`, `sentinels.supply.refresh_seconds`, `sentinels.supply.max_repos_per_tick`, `sentinels.supply.max_calls_per_tick`, `sentinels.supply.max_files_per_repo`, `sentinels.supply.min_rate_remaining`, `sentinels.supply.repos`, `sentinels.supply.ignore`, `sentinels.supply.signals.unpinned.enabled`, `sentinels.supply.signals.unpinned.level`, `sentinels.supply.signals.mutable_ref.enabled`, `sentinels.supply.signals.mutable_ref.level`, `sentinels.supply.signals.permissions_wide.enabled`, `sentinels.supply.signals.permissions_wide.level`, `sentinels.supply.signals.permissions_missing.enabled`, `sentinels.supply.signals.permissions_missing.level`, `sentinels.supply.signals.pr_target_checkout.enabled`, `sentinels.supply.signals.pr_target_checkout.level`.

## 它不做什么

它不向 GitHub 写入（不创建拉取请求、标签或议题），不建议用于固定 Action 的 SHA，也不读取任何密钥的值。
