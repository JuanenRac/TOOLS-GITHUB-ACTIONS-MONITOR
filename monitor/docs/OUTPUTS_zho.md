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

对开关已关闭的路径发出的请求会得到 `404`。向仪表板提供同一文档的旧方式，即 `ci_red.json` 和 `bin/read_report.py --export-status`，保持不变：它是一项契约。

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
| `ghamon_score`, `ghamon_score_coverage`, `ghamon_score_scored` | | 账户评分（0 到 100，仅在有数值时存在）、有数据的权重所占比例，以及有数值时为 1（仅 Complete；见 SCORE.md） |
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

队列的每一行都有 `trust`:`verified`(已用公钥验证签名)、`unknown`(此处无法检查该格式:从不猜测)或 `failed`(已检查但不匹配)。哨兵标签页有签名筛选器,显示每类数量并标记各行(绿色、灰色或红色边)。在控制台:`py -3 bin/read_report.py --export-sign-queue FILE --sign-trust failed`。

## 在网络模式下

`/metrics` 和 `dashboard.json` 会列出你的仓库及其状态：它们不是公开页面。开启网络模式后，它们与其他端点一样需要访问令牌；如果完全不希望该清单可被访问，请关闭 `outputs.prometheus.enabled` / `outputs.dashboard.enabled`。

## 保存并打印标签页报告

页面顶部的栏(每个标签页都有)会为当前打开的标签页生成"一份"报告,并用同一份数据以四种方式输出,因此各种格式永远不会不一致:

- **保存报告** 会打开一个带有三个复选框的窗口:**TXT**(已勾选)、**PDF**(已勾选)和 **JSON**(未勾选:报告的数据,供其他工具使用)。确认后,浏览器的 **另存为** 窗口会按格式各打开一次,并给出建议文件名 `monitor-<标签页>-<日期>.<扩展名>` 和正确的文件类型(浏览器要求每个窗口点击一次,所以按钮会依次转到下一种格式)。没有该窗口的浏览器会直接下载文件,页面会告诉你文件去了哪里。
- **PDF**:监视器自行编写 PDF,不使用任何库,采用标准字体 Helvetica,适用于英语、西班牙语、德语、法语、意大利语和葡萄牙语(`GET /api/report/tab.pdf`,仅限本计算机;每次使用都会在操作日志中留下一行)。日语和中文需要这种方式生成的 PDF 所没有的字体,因此对它们,或当你在窗口中选择"浏览器"时,PDF 由浏览器的打印窗口生成:请在其中选择 **另存为 PDF**。页面会说明这一点;它绝不会生成字符乱码的 PDF。
- **打印** 显示同一份报告,没有菜单和栏(标题含标签页名称、日期和时间、监视器版本、主要数据、警报以及该标签页的表格),并打开打印窗口。
- 报告由 `GET /api/report/tab?tab=now&lang=zh` 提供(`&fmt=json`、`&fmt=txt` 或 `&fmt=options`),两个版本相同。

设置(设置 > 供其他工具使用的输出 > "保存并打印标签页报告"):`report_export.txt`、`report_export.pdf` 和 `report_export.json`(哪些复选框默认勾选:TXT 和 PDF 是,JSON 否)、`report_export.name`(建议文件名,默认 `monitor-{tab}-{date}`)、`report_export.paper`(`a4` 或 `letter`,默认 `a4`)以及 `report_export.pdf_path`(`auto`、`own` 或 `browser`,默认 `auto`)。

## 服务器指标：周期、读取队列、计费、runner 和直方图

除上面的指标外，`/metrics` 还会写出（未知的值会被省略）：

| 指标 | 标签 | 含义 |
|---|---|---|
| `ghamon_ticks_total`、`ghamon_tick_failures_total` | | 已完成的刷新周期数，以及以错误结束的周期数（计数器） |
| `ghamon_tick_last_seconds`、`ghamon_tick_phase_seconds`、`ghamon_tick_seconds` | `phase` | 上一个周期及其每个阶段的耗时，以及所有周期的直方图 |
| `ghamon_tick_last_ok_timestamp_seconds`、`ghamon_tick_reads_last` | | 上一个周期何时正常结束，以及它读取了多少个仓库 |
| `ghamon_read_retries_total` | | 因暂时原因失败并被重试的读取（计数器） |
| `ghamon_repos_circuit_open`、`ghamon_repos_read_failing`、`ghamon_repos_read_fail_streak_max` | | 因连续多次失败而等待下次读取的仓库（熔断）、最近一次读取失败的仓库、最长的连续失败次数 |
| `ghamon_read_queue_depth`、`ghamon_read_queue_allowed`、`ghamon_read_queue_oldest_wait_cycles`、`ghamon_read_queue_deferred_total`、`ghamon_read_queue_shed_cycles_total` | | 带背压的读取队列（仅在 `backpressure.enabled` 开启时） |
| `ghamon_billing_minutes_total`、`ghamon_billing_minutes_included`、`ghamon_billing_minutes_paid`、`ghamon_billing_sku_minutes`、`ghamon_billing_usd` | `sku`、`product` | 当月计费报告（仅在 `quota.billing_api` 开启时；抓取从不读取 GitHub，只写出周期最近保存的报告） |
| `ghamon_runners` | `state` | 空闲、忙碌和离线的自托管 runner（`runners.enabled`） |
| `ghamon_runner_up`、`ghamon_runner_busy` | `runner` | 按 runner 统计（`outputs.prometheus.per_runner`） |
| `ghamon_runner_kind_jobs_waiting`、`ghamon_runner_kind_oldest_wait_seconds` | `kind` | 按 runner 类型统计的未开始作业数和最久等待（`runners.model.enabled`） |

开启 `outputs.prometheus.histograms`（并且 webhook 正在接收作业事件）后，还会写出在内存中用已签名的 `workflow_job` 和 `workflow_run` 事件构建的**直方图**：

| 指标 | 标签 | 含义 |
|---|---|---|
| `ghamon_job_wait_seconds` | `runner_group`、`label` | 作业的排队时间，**每个作业只计一次** |
| `ghamon_job_run_seconds` | `runner_group`、`label`、`conclusion` | 已结束作业的时长 |
| `ghamon_workflow_run_seconds` | `conclusion` | 已结束运行的时长 |
| `ghamon_jobs_total` | `label`、`conclusion` | 已结束的作业数（计数器） |
| `ghamon_runner_jobs_waiting`、`ghamon_runner_oldest_wait_seconds` | `label` | 当前对 runner 的需求：已排队未开始的作业数和最久等待 |

`outputs.prometheus.histogram_max_series`（默认 200）限制每个直方图的序列数：超出的序列计入标签值 `other`。开启 `outputs.prometheus.per_runner` 后，会为每个自托管 runner 增加 `ghamon_runner_jobs_total`、`ghamon_runner_jobs_failed_total` 和 `ghamon_runner_busy_seconds_total`（也出现在 `GET /api/runners/model` 的 `per_runner` 中）。

## 可观测性包：告警规则、Alertmanager、OnCall 和 n8n

`docs/grafana/` 除两个仪表盘外，还带有一个可复制并改写的包：

- `ghamon_alert_rules.yml`：用于 Prometheus（也可用 vmalert）的规则及其 PromQL：监视器不响应、红色工作流及连续失败、配额和计费接近上限、周期缓慢或停滞、处于熔断中的仓库、等待过久的读取、等待 runner 的作业（`histogram_quantile(0.95, sum by (le, label) (rate(ghamon_job_wait_seconds_bucket[30m])))`）、离线的 runner，以及没有空闲 runner 的需求。
- `alertmanager.example.yml`：按严重程度路由到三个接收端（默认 webhook、Grafana OnCall 和 n8n）。所有地址都是 `https://example.invalid/...`：在你填上自己的地址之前不会发送任何内容，文件里也不应放任何密钥。
- `n8n_ghamon_alerts.json`：一个 n8n 工作流，接收 Alertmanager 的 webhook 并为每条告警写一条消息；它的最后一个节点什么也不做，直到你换成自己的聊天、邮件或工单节点。
- `prometheus.example.yml` 和 `docker-compose.observability.yml` 在监视器所在的计算机上启动 Prometheus、Alertmanager 和 Grafana，用于试用该包（容器共享主机网络，端口在 `127.0.0.1` 上，Grafana 密码来自你的 shell，绝不来自文件）。
## 监视器会访问哪里，以及发送到 SIEM 的事件

- **网络目标表**：`monitor_cli.py doctor --egress`（也可加 `--json`）列出当前配置可能访问的每个主机、用途、使其成为目标的设置，以及被阻止时会失败的内容：`api.github.com`、`github.com`、`objects.githubusercontent.com` 和 `release-assets.githubusercontent.com`（更新）、`raw.githubusercontent.com`（`lint.anonymous_public`）、ntfy、Telegram、聊天 Webhook、你选择的 AI 提供商、OTLP 收集器和 SIEM 目标。启用 `airgapped` 时不使用任何一个。测试保证该表与代码中出现的主机一致。
- **SIEM**（关闭）：文件中的 `siem.sinks` 列出各目标，要使用的需设 `enabled: true`：`elasticsearch`（bulk）、`splunk_hec`、`loki`、`sentinel`（Log Analytics，用共享密钥签名）、`bigquery`（`insertAll`）或 `http`（JSON 行）。令牌或密钥从 `token_env` 指定的环境变量读取，绝不从文件读取。每个目标用 `from_minutes`（5）、`levels` 和 `repos_filter` 过滤；事件的字段是固定的（没有令牌和日志文本）；私有地址上的接收端会被拒绝，除非该目标设有 `allow_private`；接收端宕机时，事件在 `siem.queue_max`（500）的队列中等待，最旧的先被丢弃。离线模式下不发送任何内容。
