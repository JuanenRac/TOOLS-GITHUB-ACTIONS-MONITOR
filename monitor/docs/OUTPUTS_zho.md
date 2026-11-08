<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](OUTPUTS.md) | [🇪🇸 Español](OUTPUTS_spa.md) | [🇫🇷 Français](OUTPUTS_fra.md) | [🇮🇹 Italiano](OUTPUTS_ita.md) | [🇩🇪 Deutsch](OUTPUTS_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](OUTPUTS_jpn.md) | [🇵🇹 Português](OUTPUTS_por.md)

# 面向其他工具的输出

三种可选输出，**默认全部关闭**，可在设置选项卡（“面向其他工具的输出”分组）或 `actions_monitor.json` 中开启：

```json
"outputs": {"prometheus": {"enabled": false, "per_repo": true}, "json": {"enabled": false}, "dashboard": {"enabled": false}}
```

它们由同一个 Web 服务器提供，仅在 `127.0.0.1` 上，使用与其余部分相同的 `Host` / `Origin` 检查，且**不需要令牌**。它们读取监视器已持有的状态，因此一次抓取或一次仪表板刷新不会消耗任何 GitHub API 配额。开启或关闭会立即生效（无需重启）。

| 路径 | 格式 | 开关 |
|---|---|---|
| `/metrics` | Prometheus 文本，版本 0.0.4 | `outputs.prometheus.enabled`（`per_repo` 会增加按仓库划分的序列） |
| `/api/outputs/grafana.json` | 适用于 Grafana “Infinity” / JSON 数据源的 JSON 表格 | `outputs.json.enabled` |
| `/api/outputs/dashboard.json` | 面向状态仪表板的 `ci_red.json` 文档（模式 2，参见 CI_RED_SCHEMA_zho.md） | `outputs.dashboard.enabled` |

对开关已关闭的路径发出的请求会得到 `404`。向仪表板提供同一文档的旧方式，即 `ci_red.json` 和 `read_report.py --export-status`，保持不变：它是一项契约。

## Prometheus 指标

所有名称均以 `ghamon_` 开头。仅有仪表（gauge）类型。未知的值会被**省略**，绝不会写成 0。

| 指标 | 标签 | 含义 |
|---|---|---|
| `ghamon_info` | `version` | 始终为 1 |
| `ghamon_snapshot_complete` | | 哨兵快照完整时为 1，加载期间或被精简时为 0 |
| `ghamon_red_workflows`、`ghamon_red_repos` | | 默认分支上最近一次完成的运行为红色的工作流（仓库） |
| `ghamon_ecosystem_red_workflows` | `ecosystem` | 同上，按生态系统统计 |
| `ghamon_repo_red_workflows` | `repo`, `ecosystem` | 按仓库统计（需要 `per_repo`） |
| `ghamon_workflow_red_streak` | `repo`, `workflow`, `ecosystem` | 连续红色运行的次数（需要 `per_repo`） |
| `ghamon_workflow_red_hours` | `repo`, `workflow`, `ecosystem` | 自变红以来的小时数（需要 `per_repo`） |
| `ghamon_pending_sign`、`ghamon_pending_sign_repos`、`ghamon_pending_sign_hours_max` | | 等待本地签名或发布且超过阈值的构建 |
| `ghamon_repo_pending_sign_hours` | `repo`, `ecosystem` | 某个仓库最长的等待时间（需要 `per_repo`） |
| `ghamon_surface_paused`、`ghamon_surface_paused_remaining`、`ghamon_surface_paused_needed` | | 表面检查（A10）等待 GitHub 配额期间为 1，同时给出剩余配额和所需配额 |
| `ghamon_api_rate_remaining`、`ghamon_api_rate_limit` | | GitHub API 的配额 |
| `ghamon_sentinel_calls_last_hour`、`ghamon_sentinel_budget_per_hour` | | 哨兵的 API 调用次数及其预算 |
| `ghamon_repos_watched`、`ghamon_runs_active`、`ghamon_runs_stuck`、`ghamon_runs_failing`、`ghamon_issues_open`、`ghamon_quota_paused` | | “当前”选项卡的实时数据 |

一个抓取任务示例：

```yaml
scrape_configs:
  - job_name: github-actions-monitor
    scrape_interval: 30s
    static_configs:
      - targets: ["127.0.0.1:8765"]
```

## Grafana

`docs/grafana/monitor_dashboard.json` 是一个可导入的仪表板（Grafana 10 或更高版本）：包含红色工作流、等待签名的构建、剩余配额、A10 的状态、快照是否完整以及卡住的运行的统计面板；按生态系统划分的红色工作流条形图；最长红色连续次数和签名等待时间的图表；以及两个通过 Infinity 数据源从 `/api/outputs/grafana.json` 读取的表格（`root_selector` 分别为 `red` 和 `pending_sign`）。导入时 Grafana 会要求选择 Prometheus 和 Infinity 数据源；如果监视器没有使用 8765 端口，请修改这两个表格 URL 中的端口。Grafana 必须与监视器运行在同一台机器上（这些输出仅在 127.0.0.1 上响应）。

## 借鉴自类似项目的想法

阅读其他 GitHub Actions 工具的做法带来了一些想法；不使用它们的任何代码或文字。来自一个 Prometheus 指标导出器：把运行的状态表示为数字加标签、选择导出哪些标签，以及可配置的端口和间隔。来自一个由 Webhook 驱动的电视仪表板：每个仓库一个状态，带过滤器，以大字号显示。来自一个终端监视器：一次性显示某个仓库的所有工作流，直到它们结束。来自一个带告警规则的 Webhook 仪表板：在告警之前按仓库、分支和工作流进行过滤。在这里，同样的想法体现为 `per_repo`（选择序列）、每个红色工作流一行的 JSON 数据源、实时的“当前”选项卡，以及页面中带过滤器的事件文件。

## 最小 Grafana 面板

`docs/grafana/red_by_ecosystem.json` 是只含一个图表的面板:按生态系统统计的红色工作流(查询 `ghamon_ecosystem_red_workflows`,图例 `{{ecosystem}}`)。导入后选择你的 Prometheus 数据源。本仓库的测试会检查它使用的指标和标签确实由 `/metrics` 提供。

## 按可信度划分的签名队列

队列的每一行都有 `trust`:`verified`(已用公钥验证签名)、`unknown`(此处无法检查该格式:从不猜测)或 `failed`(已检查但不匹配)。哨兵标签页有签名筛选器,显示每类数量并标记各行(绿色、灰色或红色边)。在控制台:`py -3 read_report.py --export-sign-queue FILE --sign-trust failed`。

## 在网络模式下

`/metrics` 和 `dashboard.json` 会列出你的仓库及其状态：它们不是公开页面。开启网络模式后，它们与其他端点一样需要访问令牌；如果完全不希望该清单可被访问，请关闭 `outputs.prometheus.enabled` / `outputs.dashboard.enabled`。
