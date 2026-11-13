<p align="center">
  <img src="images/GITHUB_ACTIONS_MONITOR_BANNER.svg" alt="GitHub Actions Monitor" width="100%">
</p>

# GitHub Actions Monitor

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <b>🇨🇳 简体中文</b> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

<p align="center">
  <a href="https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases/latest"><img src="https://img.shields.io/github/v/release/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR?label=version&color=2EE6A6" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL-3.0-or-later">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Dependencies-none-2EE6A6.svg" alt="No dependencies">
  <img src="https://img.shields.io/badge/Languages-8-FFB300.svg" alt="8 languages">
</p>

> 监视你所有仓库的工作流，并在一个本地页面上告诉你：哪些是红的、哪些卡住了、哪些在等你处理。

**GitHub Actions Monitor** 是运行在你自己电脑上的小程序。它通过你自己的 `gh` 登录向 GitHub 查询仓库中每个工作流的最近运行，判断哪些真正是红的，提醒重要事项（安全、卫生、可发布的版本、配额），并把一切显示在只有你的机器能打开的网页上。它只需要 Python 和 `gh`，从不保存令牌，默认只读取。

## 概览

| | |
|---|---|
| **版本** | **1.7.7** · [所有发布](https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases) |
| **需要** | Python 3.11+ 和 GitHub CLI（`gh auth login`）；不需要其他东西(终端视图使用可选的 `rich` 包) |
| **打开** | 仅在 `127.0.0.1` 上的页面，支持八种语言 |
| **写入 GitHub** | 绝不自行写入：只有你用明确的 `--go` 运行的批处理命令才会 |
| **导出** | `ci_red.json`、Prometheus 指标和 Grafana 用 JSON（开启前全部关闭） |

<!-- glance:begin -->

**今日实测** (v1.7.7)

| | |
|---|---|
| **成熟度** | functional |
| **测试** | 1252 个测试方法(`python -m unittest discover -s monitor/tests`) |
| **设置** | 287 个设置,均有帮助 |
| **语言** | 8 种(英语、西班牙语、德语、法语、意大利语、日语、中文和葡萄牙语) |
| **CI 测试平台** | ubuntu, windows, macos,Python 3.11, 3.13 |

## 项目状态

每一行是本仓库的一个部分,指示灯表示它今天的进度:测试和 CI 能证明的、以及真正运行过的,而不是计划中的。

🟢 已完成并验证 · 🟡 可用,有已知限制 · 🟠 部分完成或尚未验证 · 🔴 未完成或不能用

| 范围 | 状态 | 含义 |
|---|---|---|
| 监视器与页面 | 🟢 | 每天在真实账户上运行;测试在 CI 的三个系统上运行。 |
| 哨兵(A1..A13) | 🟢 | 每天在真实账户上运行;其级别和行用固定数据测试。 |
| 通知 | 🟡 | 已针对模拟服务器测试;并非每个渠道都在真实服务上试过。 |
| AI 工具连接与 MCP | 🟡 | 信息流、状态、事件流、钩子和 MCP 工具已用真实服务器和模拟客户端测试;尚无独立用户使用过。 |
| Lite 版 | 🟡 | 已在 CI 中测试,与完整版共用通道和设置;迄今实际使用较少。 |
| GitHub App、中央面板和节省模式 | 🟠 | 新功能:已用模拟服务器和文件测试;尚未长时间对真实服务运行。 |
| Linux 和 macOS | 🟠 | 仅在 CI 中测试;日常使用在 Windows 上。 |

<!-- glance:end -->

## 截图

### 页面

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_now_light.png"><img src="docs/screenshots/web_now_dark.png" alt="当前" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_alerts_light.png"><img src="docs/screenshots/web_alerts_dark.png" alt="警报：所有哨兵合在一个列表，带本地静音" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_light.png"><img src="docs/screenshots/web_sentinel_dark.png" alt="哨兵" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_queue_light.png"><img src="docs/screenshots/web_sentinel_queue_dark.png" alt="签名队列（最紧急的在前）" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_analytics_light.png"><img src="docs/screenshots/web_sentinel_analytics_dark.png" alt="A12 · 分析:时长、排队时间、步骤与不稳定的工作流" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_charts_light.png"><img src="docs/screenshots/web_charts_dark.png" alt="图表" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_repositories_light.png"><img src="docs/screenshots/web_repositories_dark.png" alt="仓库" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_history_light.png"><img src="docs/screenshots/web_history_dark.png" alt="历史" width="92%"></picture></p>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_about_light.png"><img src="docs/screenshots/web_about_dark.png" alt="关于" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_help_light.png"><img src="docs/screenshots/web_help_dark.png" alt="帮助，可搜索且可离线使用" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_basic_light.png"><img src="docs/screenshots/web_settings_basic_dark.png" alt="设置 · 基本：套餐、配额与发现" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_network_now_light.png"><img src="docs/screenshots/web_network_now_dark.png" alt="网络模式:持久的红色横幅" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_network_notices_light.png"><img src="docs/screenshots/web_network_notices_dark.png" alt="底部栏：最重要的提示和显示全部提示的窗口" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_network_settings_light.png"><img src="docs/screenshots/web_network_settings_dark.png" alt="设置 · 网络模式的警告和 HTTPS 代理名称" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_accounts_all_light.png"><img src="docs/screenshots/web_accounts_all_dark.png" alt="所有账户：每个账户一张卡片" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_accounts_one_light.png"><img src="docs/screenshots/web_accounts_one_dark.png" alt="带切换器的单个账户页面" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_accounts_live_light.png"><img src="docs/screenshots/web_accounts_live_dark.png" alt="实时视图：webhook 接收器和工作模式" width="92%"></picture></p>

<details><summary><b>设置(逐个子标签页)</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_interface_light.png"><img src="docs/screenshots/web_settings_interface_dark.png" alt="设置 · 此浏览器" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_general_light.png"><img src="docs/screenshots/web_settings_general_dark.png" alt="设置 · 常规" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_polling_light.png"><img src="docs/screenshots/web_settings_polling_dark.png" alt="设置 · 刷新与限制" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_cache_light.png"><img src="docs/screenshots/web_settings_cache_dark.png" alt="设置 · 读取与缓存" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_sentinel_light.png"><img src="docs/screenshots/web_settings_sentinel_dark.png" alt="设置 · 哨兵" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_surface_light.png"><img src="docs/screenshots/web_settings_surface_dark.png" alt="设置 · 表面检查(A10)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_readiness_light.png"><img src="docs/screenshots/web_settings_readiness_dark.png" alt="设置 · 就绪度(A11)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_paths_light.png"><img src="docs/screenshots/web_settings_paths_dark.png" alt="设置 · 文件夹与文件" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_outputs_light.png"><img src="docs/screenshots/web_settings_outputs_dark.png" alt="设置 · 供其他工具使用的输出" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_ai_light.png"><img src="docs/screenshots/web_settings_ai_dark.png" alt="设置 · 哨兵使用的外部 AI" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_webhook_light.png"><img src="docs/screenshots/web_settings_webhook_dark.png" alt="设置 · 入站 Webhook" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_notify_light.png"><img src="docs/screenshots/web_settings_notify_dark.png" alt="设置 · 通知" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_analytics_light.png"><img src="docs/screenshots/web_settings_analytics_dark.png" alt="设置 · 分析" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_lint_light.png"><img src="docs/screenshots/web_settings_lint_dark.png" alt="设置 · 工作流检查器" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_console_light.png"><img src="docs/screenshots/web_settings_console_dark.png" alt="设置 · 终端视图" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_advanced_light.png"><img src="docs/screenshots/web_settings_advanced_dark.png" alt="设置 · 高级(可选)" width="92%"></picture></p>

</details>

<details><summary><b>控制台工具</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_read_report_light.png"><img src="docs/screenshots/console_read_report_dark.png" alt="read_report.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_migrate_state_light.png"><img src="docs/screenshots/console_migrate_state_dark.png" alt="migrate_state.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_plan_light.png"><img src="docs/screenshots/console_plan_dark.png" alt="gha_dispatch_all.py plan" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_lint_light.png"><img src="docs/screenshots/console_lint_dark.png" alt="lint_workflows.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_tui_light.png"><img src="docs/screenshots/console_tui_dark.png" alt="tui.py" width="92%"></picture></p>

</details>

<details><summary><b>lite 版</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_now_light.png"><img src="docs/screenshots/web_lite_now_dark.png" alt="lite · 当前" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_charts_light.png"><img src="docs/screenshots/web_lite_charts_dark.png" alt="lite · 图表" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_history_light.png"><img src="docs/screenshots/web_lite_history_dark.png" alt="lite · 历史" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_settings_light.png"><img src="docs/screenshots/web_lite_settings_dark.png" alt="lite · 设置" width="92%"></picture></p>

</details>

每张图片都会跟随你 GitHub 页面的浅色或深色主题。

*演示数据：图片中的仓库和名称均为虚构。*

## 功能

- **是否为红，只用一条规则**：默认分支上每个工作流最后一次已结束的运行。已取消或已跳过的运行不会掩盖之前的失败。
- **哨兵**：安全警报、仓库卫生、陈旧的拉取请求、可发布的版本、等待签名的构建，以及通俗易懂的报告。
- **Collab 哨兵与统一警报列表**：需要人来处理的未关闭 Issue 和拉取请求（被遗忘的、严重的、等待评审的、陈旧草稿、冲突），只读且按自己的周期运行；“警报”标签页把所有哨兵汇总成一个列表，可按来源筛选，并提供会自行结束的本地静音。
- **状态栏、全屏与可排序的表格**：页面底部显示最重要的提示（以及显示全部提示的窗口）、连接、配额、最近一次读取、模式、地址和时钟；全屏按钮；“仓库”和“历史”可按一列或多列排序，并可自选列。
- **作为客户端的命令行**：`monitor_cli.py`（`status`、`health`、`alerts`、`accounts`、`live`、`doctor`）读取运行中监视器给出的信息，支持 `--json` 和稳定的退出码；从不向 GitHub 写入。
- **设置页面**：在浏览器中修改路径、间隔、配额和开关；只有固定且经过验证的键，每次保存前都会备份。
- **图表与历史**：计算分钟数、失败和成功，配有动画条形图和每日历史（尊重“减少动态效果”设置）。
- **八种语言**（en、es、de、fr、it、ja、zh、pt），以英语为基础；在设置中切换。
- **面向仪表板的输出**：`ci_red.json`、Prometheus 端点和 Grafana 用 JSON 数据源，并附带可导入的 Grafana 仪表板。
- **批处理工具**：一次计划并触发多个构建；没有 `--go` 就不会触发任何东西。
- **页面内的“关于”和“帮助”**：**i** 按钮显示版本、版本类型、链接、文件、运行状况和复制支持信息的按钮；**?** 按钮（或 `?` 键）可离线打开全部文档，支持搜索并使用你的语言。控制台提供 `--about` 和 `--help-topics`，以及分标签页的交互式终端应用（可选 `textual`）。
- **新版本提示**：发布较新版本时显示低调的徽章；它每天只读取一次公开发布页，从不安装任何内容，可以关闭（隔离网络安装中始终关闭）。
- **适用于任何账户的配额**：套餐、计费分钟数（公开仓库不计费）、从 GitHub 响应头读取的 API 配额、并发数，以及接近 6 小时上限的作业；数字保存在可编辑的文件中。

## 架构

<p align="center"><img src="images/architecture.svg" alt="架构" width="100%"></p>

## 从这里开始：选哪个版本？

| 如果你想... | 启动 | 端口 |
|---|---|---|
| 只看什么在运行、什么失败了（**从这里开始**） | `MONITOR_LITE_GITHUB_ACTIONS` | 8766 |
| 让整个账户被替你监视：警报、发布、签名、就绪度、分析 | `MONITOR_GITHUB_ACTIONS`（含[哨兵](monitor/docs/SENTINEL_zho.md)） | 8765 |

控制台窗口的标题和第一行会说明正在运行哪一个。还拿不准？`python actions_monitor.py --demo` 用虚构数据打开页面，`--doctor` 检查你的安装。[你的前五分钟](monitor/docs/FIRST_STEPS_zho.md)

## 快速开始

1. 安装 Python 3.11 或更新版本和 [GitHub CLI](https://cli.github.com/)，然后运行 `gh auth login`。
2. 下载本仓库（或最新发布的 zip），打开 `monitor` 文件夹。
3. 启动：Windows 运行 `MONITOR_GITHUB_ACTIONS.bat`，Linux 运行 `./MONITOR_GITHUB_ACTIONS.sh`，macOS 双击 `MONITOR_GITHUB_ACTIONS.command`，或在任何系统运行 `python actions_monitor.py`。
4. 打开它打印的地址（`http://127.0.0.1:<端口>`）。首次启动时会根据示例创建 `actions_monitor.json`。
5. 打开 **设置**，填写你的 GitHub 账号、生态系统（按名称前缀分组的仓库）和其他内容。

> 从 1.5.0 之前的版本更新？ [`monitor/docs/MIGRATING_zho.md`](monitor/docs/MIGRATING_zho.md)

## lite 版

同一软件包里的第二个、更简单的产品:显示正在运行和失败内容的页面,没有哨兵。适合只想看自己运行情况的人。

|  | 完整版 | lite 版 |
|---|---|---|
| 启动 | `MONITOR_GITHUB_ACTIONS`(`.bat` / `.sh` / `.command`) | `MONITOR_LITE_GITHUB_ACTIONS`(同样三个) |
| 端口 | 8765 | 8766 |
| 标签页 | 现在、哨兵、图表、仓库、历史、设置 | 现在、图表、仓库、历史、简短设置 |
| 页眉 | 所有磁贴、就绪、签名 | 运行中、排队、24 小时的失败与成功、计算分钟、issue、main 上的红色、仓库、配额、连接 |
| 哨兵(警报、发布、签名队列、就绪、检查器) | 有 | 无:甚至不会被导入 |
| 分析、通知、Webhook、AI、Prometheus / Grafana 输出 | 有,开启前默认关闭 | 无:这些路径返回 404 |
| 配置 | `actions_monitor.json` | `actions_monitor_lite.json`(首次启动时创建;其中哨兵为关闭) |
| 状态文件 | `etag_cache.json`、`analytics_history.json` 等 | 同名文件加后缀 `_lite` |

[`monitor/docs/LITE_zho.md`](monitor/docs/LITE_zho.md)

## 设置

一切都在 `actions_monitor.json` 中（由 `actions_monitor.example.json` 创建）。**设置** 标签页可安全地编辑它；令牌和机密绝不会显示或保存。生态系统、构建目标和批处理配置是你指定的独立文件（`ecosystems_file`、`targets_file`、`profiles_file`）；附带中性的 `*.example.json` 模板。完整参考：[`monitor/docs/SETTINGS_zho.md`](monitor/docs/SETTINGS_zho.md)。

## 面向 Grafana 和仪表板的输出

默认全部关闭，仅限本地（`127.0.0.1`），无需额外令牌。在设置中启用后可使用 `/metrics`（Prometheus 格式）、`/api/outputs/grafana.json` 和 `/api/outputs/dashboard.json`，并在 [`monitor/docs/grafana`](monitor/docs/grafana) 提供可导入的 Grafana 仪表板。详情：[`monitor/docs/OUTPUTS_zho.md`](monitor/docs/OUTPUTS_zho.md)。`ci_red.json` 的格式：[`monitor/docs/CI_RED_SCHEMA_zho.md`](monitor/docs/CI_RED_SCHEMA_zho.md)。

## 安全

- 它只监听 `127.0.0.1`，并拒绝 `Host` 或 `Origin` 不是本地的请求。切勿绑定到 `0.0.0.0`：它没有登录。
- 它不保存任何令牌：使用你自己的 `gh`（除非你在“设置 > 高级”中开启监视器的可选令牌）。
- 它不会自行向 GitHub 写入任何内容。只有 `dispatch --go`、`dispatch --real` 和 `finalize --execute` 会写入，且仅在你运行它们时。
- **分析**:每个工作流的时长、排队时间和每个步骤的 p50 / p95,不稳定的工作流(在同一提交上先失败后通过)以及变慢的工作流;导出到 Prometheus 和 Grafana。
- **节省配额并能应对断网**:条件读取(304 不消耗任何配额)以及带离线横幅、可自动恢复的“最后画面”模式。
- **入站 Webhook 与通知**:已签名的事件实时更新仓库;可选地向 Telegram、Discord、Slack、Matrix、MQTT 或本地地址发送消息(绝不写入 GitHub)。
- **工作流检查器与终端视图**:`lint_workflows.py` 在推送前检查 `.github/workflows`;`tui.py`(可选,使用 `rich`)在控制台中显示实时表格。
- **AI 助手(默认关闭)**:用 Ollama、OpenAI 兼容服务、Anthropic 或 `gh copilot` 做总结、分类和解释;命令只来自封闭列表,且每一条都要经你确认后才会执行。
- 设置页面在保存备份副本之后，才会写入固定且经过验证的键。

## 测试

不需要网络，也不需要额外的包：

```
python -m unittest discover -s monitor/tests
```

## 仓库结构

<p align="center"><img src="images/repository-structure.svg" alt="仓库结构" width="100%"></p>

```
TOOLS-GITHUB-ACTIONS-MONITOR/
├── monitor/                                  程序本体
├── docs/                                     架构、截图、路线图
├── tools/                                    图片、指南与演示
├── deploy/                                   容器示例
├── images/                                   横幅图和图片
├── .github/                                  CI 和议题表单
├── CHANGELOG.md                              各版本变更
├── LICENSE NOTICE AUTHORS                    许可证和作者
├── CONTRIBUTING.md SECURITY.md               参与方式、报告
├── SUPPORT.md CODE_OF_CONDUCT.md             支持和行为准则
└── monitor/
    ├── actions_monitor.py                    本地服务器
    ├── actions_monitor.html                  网页
    ├── MONITOR_LITE_GITHUB_ACTIONS.*         lite 版(无哨兵)
    ├── sentinel_local.py                     警报与报告
    ├── sentinel_collab.py  alert_center.py   Issue 哨兵与警报
    ├── surface.py readiness.py               检查与发布就绪
    ├── settings_api.py outputs.py            设置与指标
    ├── signstate.py sigverify.py             签名状态与验证
    ├── monitor_cli.py                        客户端命令行
    ├── read_report.py                        终端报告
    ├── gha_dispatch_all.py                   批量构建
    ├── events.py report_history.py           事件与历史
    ├── ci_red.py export_status.py            供其他工具读取
    ├── etagcache.py resilience.py            条件读取与连接
    ├── analytics.py lint_workflows.py        时长、不稳定、检查器
    ├── notifiers.py ai_actions.py            通知与 AI 封闭列表
    ├── tui.py migrate_state.py               终端视图与迁移
    ├── about.py  helpdocs.py                 关于与帮助面板
    ├── quota.py  quotas.json                 套餐、分钟数与配额
    ├── modes.py  updatecheck.py              工作模式、版本提示
    ├── doctor.py  demo_mode.py               --doctor 与 --demo
    ├── discovery.py  banner.py               发现、版本横幅
    ├── tui_textual.py                        交互式终端
    ├── i18n.py locales/                      八种语言
    ├── toolconfig.py workspace.py            设置与克隆
    ├── tests/                                离线测试
    └── docs/                                 指南、模式、Grafana
```

## 文档

- [`monitor/docs/SETTINGS_zho.md`](monitor/docs/SETTINGS_zho.md): 所有设置
- [`monitor/docs/OUTPUTS_zho.md`](monitor/docs/OUTPUTS_zho.md): 指标、Grafana 和导出
- [`monitor/docs/CI_RED_SCHEMA_zho.md`](monitor/docs/CI_RED_SCHEMA_zho.md): ci_red.json 的格式
- [`monitor/docs/CI_RED_BRIDGE_zho.md`](monitor/docs/CI_RED_BRIDGE_zho.md): 把 ci_red.json 带到仪表板
- [`monitor/docs/WEBHOOK_zho.md`](monitor/docs/WEBHOOK_zho.md): 入站 Webhook
- [`monitor/docs/LITE_zho.md`](monitor/docs/LITE_zho.md): lite 版
- [`monitor/docs/NOTIFICATIONS_zho.md`](monitor/docs/NOTIFICATIONS_zho.md): 通知与适配器约定
- [`monitor/docs/AI_zho.md`](monitor/docs/AI_zho.md): AI 助手:提供方、安全与操作
- [`monitor/docs/ANALYTICS_zho.md`](monitor/docs/ANALYTICS_zho.md): 分析、条件读取与连接丢失
- [`monitor/docs/CONSOLE_TOOLS_zho.md`](monitor/docs/CONSOLE_TOOLS_zho.md): 工作流检查器与终端视图
- [`monitor/docs/DEPLOYMENT_zho.md`](monitor/docs/DEPLOYMENT_zho.md): 作为服务运行、反向代理之后、权限
- [`monitor/QUICKSTART_zh.txt`](monitor/QUICKSTART_zh.txt): 入门步骤（八种语言）
- [`monitor/docs/FIRST_STEPS_zho.md`](monitor/docs/FIRST_STEPS_zho.md)：你的前五分钟
- [`monitor/docs/SENTINEL_zho.md`](monitor/docs/SENTINEL_zho.md)：哨兵及其检查 A1-A13
- [`monitor/docs/COLLAB_zho.md`](monitor/docs/COLLAB_zho.md)：Collab 哨兵、警报标签页与静音
- [`monitor/docs/CLI_zho.md`](monitor/docs/CLI_zho.md)：作为监视器客户端的命令行
- [`monitor/docs/ACCOUNTS_zho.md`](monitor/docs/ACCOUNTS_zho.md)：多个账户，每个账户一个进程
- [`monitor/docs/QUOTAS_zho.md`](monitor/docs/QUOTAS_zho.md)：GitHub 的配额与套餐
- [`monitor/docs/MODES_zho.md`](monitor/docs/MODES_zho.md)：工作模式：普通、快速和极速
- [`monitor/docs/AI_CONNECTION_zho.md`](monitor/docs/AI_CONNECTION_zho.md): 连接 AI 工具:监视器说的一切,以信号形式出现在简报、端点、MCP 工具和钩子中
- [`monitor/docs/QUOTA_zho.md`](monitor/docs/QUOTA_zho.md): 更多配额,更少消耗:节省模式、中央面板、GitHub App 以及如何共享配额

## 参与贡献

请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。用议题表单报告缺陷和想法；安全问题请按 [SECURITY.md](SECURITY.md) 中的说明报告。

## 作者

作者：**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 许可证

代码采用 GPL-3.0-or-later；文档采用 CC BY-SA 4.0。参见 [LICENSE](LICENSE) 和 [NOTICE](NOTICE)。
