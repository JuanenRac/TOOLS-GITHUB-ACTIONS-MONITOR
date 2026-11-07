<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SETTINGS.md) | [🇪🇸 Español](SETTINGS_spa.md) | [🇫🇷 Français](SETTINGS_fra.md) | [🇮🇹 Italiano](SETTINGS_ita.md) | [🇩🇪 Deutsch](SETTINGS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](SETTINGS_jpn.md) | [🇵🇹 Português](SETTINGS_por.md)

# 设置选项卡

设置选项卡（标题栏或选项卡栏中的齿轮图标）可直接在页面上修改 `actions_monitor.json` 中的值，无需手动编辑该文件。
该选项卡使用页面的八种语言编写，外观与页面其余部分保持一致。

## 可以修改的内容

仅限 `settings_api.py` 列表（即模式）中的键。每个键都有类型和取值范围，页面会说明某项修改需要**重启**监视器（循环只读取一次配置），还是**立即生效**。

| 分组 | 键 |
|---|---|
| 此浏览器 | 页面语言、主题（自动 / 浅色 / 深色）、“当前”选项卡的紧凑视图。这些设置保存在浏览器中，而不是文件中。 |
| 常规 | `language`（工具的默认语言）、`github_owner`、`mode`（`full` / `lite`）、`ecosystems`、`exclude`、`report_history_days` |
| 刷新与限制 | `refresh_seconds`、`cold_refresh_seconds`、`issues_refresh_seconds`、`discover_refresh_seconds`、`stuck_minutes`、`runs_per_repo`、`cold_runs_per_repo`、`hot_hours`、`max_workers`、`min_rate_remaining` |
| 哨兵 | `sentinel.enabled`、各个周期、API 预算、候选项、过期拉取请求和待签名项的阈值、`sentinel.require_verified_signature`、A2 的查询 |
| 表面检查（A10） | `sentinel.surface.enabled`、其周期、每个周期的仓库数、余量系数以及占预算的比例 |
| 就绪度（A11） | `sentinel.readiness.enabled`、`min_coverage`、`warn_below` |
| 文件夹与文件 | `workspace_root`、`signed_dir`、`audit_dir`、`ecosystems_file`、`targets_file`、`profiles_file`、`tools_dir`、`sentinel.ci_red_file`、`sentinel.ci_red_audit_copy` |
| 面向其他工具的输出 | `outputs.prometheus.enabled`、`outputs.prometheus.per_repo`、`outputs.json.enabled`、`outputs.dashboard.enabled`（参见 OUTPUTS_zho.md） |

## 永远无法在页面上修改或查看的内容

令牌、机密、签名密钥、Webhook 机密、哨兵可以运行的命令（`sentinel.notify_command`）、AI 设置以及其他工具的任何键：它们**不在模式中**，因此页面既不显示也不写入这些内容，提到其中任何一项的请求都会被拒绝。文件中的其他所有键都会原样保留。

## 保存的工作方式

1. 只发送发生变化的值，形式为 `POST /api/settings`，带有 `Content-Type: application/json`，请求体最大 16 KB。
2. 每个值都会按其类型和范围进行检查；只要有一个值无效，整个请求就会被拒绝，且不会写入任何内容。路径必须是不含控制字符的文本，不能是
   网络（UNC）路径，也不能位于 `D:` 盘。
3. 先前的文件会被复制到 `config_backups/actions_monitor-<time>.json`（保留最近十份副本）。
4. 新文件先写入临时文件，再移动覆盖旧文件（原子操作），因此崩溃也不会留下写了一半的文件。不是有效 JSON 的文件绝不会被页面覆盖。
5. 页面会说明哪些已保存的值需要重启，并一直显示横幅，直到您重启为止。

## 谁可以发出请求

只有同一台机器上的页面：服务器监听 `127.0.0.1`，并拒绝 `Host` 或 `Origin` 不是其自身地址的请求（与其他所有端点的检查相同）。
来自其他站点的表单无法访问它，因为请求必须是 JSON。

## 1.5.0 之前

工具的语言过去由系统语言决定；现在它们以英语启动，语言是一项设置（此处为 `language`、`MONITOR_LANG` 或 `--lang`）。
`parte_history_days` 现在是 `report_history_days`（旧名称仍会被读取）。
