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
| **需要** | Python 3.11+ 和 GitHub CLI（`gh auth login`）；不需要其他东西 |
| **打开** | 仅在 `127.0.0.1` 上的页面，支持八种语言 |
| **写入 GitHub** | 绝不自行写入：只有你用明确的 `--go` 运行的批处理命令才会 |
| **导出** | `ci_red.json`、Prometheus 指标和 Grafana 用 JSON（开启前全部关闭） |

## 截图

<p align="center"><img src="docs/screenshots/monitor_now_dark.png" alt="Now" width="92%"></p>
<p align="center"><img src="docs/screenshots/monitor_sentinel_dark.png" alt="Sentinel" width="92%"></p>
<p align="center"><img src="docs/screenshots/monitor_charts_dark.png" alt="Charts" width="92%"></p>
<p align="center"><img src="docs/screenshots/monitor_settings_light.png" alt="Settings" width="92%"></p>

*演示数据：图片中的仓库和名称均为虚构。*

## 功能

- **是否为红，只用一条规则**：默认分支上每个工作流最后一次已结束的运行。已取消或已跳过的运行不会掩盖之前的失败。
- **哨兵**：安全警报、仓库卫生、陈旧的拉取请求、可发布的版本、等待签名的构建，以及通俗易懂的报告。
- **设置页面**：在浏览器中修改路径、间隔、配额和开关；只有固定且经过验证的键，每次保存前都会备份。
- **图表与历史**：计算分钟数、失败和成功，配有动画条形图和每日历史（尊重“减少动态效果”设置）。
- **八种语言**（en、es、de、fr、it、ja、zh、pt），以英语为基础；在设置中切换。
- **面向仪表板的输出**：`ci_red.json`、Prometheus 端点和 Grafana 用 JSON 数据源，并附带可导入的 Grafana 仪表板。
- **批处理工具**：一次计划并触发多个构建；没有 `--go` 就不会触发任何东西。

## 架构

<p align="center"><img src="images/architecture.svg" alt="架构" width="100%"></p>

## 快速开始

1. 安装 Python 3.11 或更新版本和 [GitHub CLI](https://cli.github.com/)，然后运行 `gh auth login`。
2. 下载本仓库（或最新发布的 zip），打开 `monitor` 文件夹。
3. 启动：Windows 运行 `MONITOR_GITHUB_ACTIONS.bat`，Linux 运行 `./MONITOR_GITHUB_ACTIONS.sh`，macOS 双击 `MONITOR_GITHUB_ACTIONS.command`，或在任何系统运行 `python actions_monitor.py`。
4. 打开它打印的地址（`http://127.0.0.1:<端口>`）。首次启动时会根据示例创建 `actions_monitor.json`。
5. 打开 **设置**，填写你的 GitHub 账号、生态系统（按名称前缀分组的仓库）和其他内容。

## 设置

一切都在 `actions_monitor.json` 中（由 `actions_monitor.example.json` 创建）。**设置** 标签页可安全地编辑它；令牌和机密绝不会显示或保存。生态系统、构建目标和批处理配置是你指定的独立文件（`ecosystems_file`、`targets_file`、`profiles_file`）；附带中性的 `*.example.json` 模板。完整参考：[`monitor/docs/SETTINGS_zho.md`](monitor/docs/SETTINGS_zho.md)。

## 面向 Grafana 和仪表板的输出

默认全部关闭，仅限本地（`127.0.0.1`），无需额外令牌。在设置中启用后可使用 `/metrics`（Prometheus 格式）、`/api/outputs/grafana.json` 和 `/api/outputs/dashboard.json`，并在 [`monitor/docs/grafana`](monitor/docs/grafana) 提供可导入的 Grafana 仪表板。详情：[`monitor/docs/OUTPUTS_zho.md`](monitor/docs/OUTPUTS_zho.md)。`ci_red.json` 的格式：[`monitor/docs/CI_RED_SCHEMA_zho.md`](monitor/docs/CI_RED_SCHEMA_zho.md)。

## 安全

- 它只监听 `127.0.0.1`，并拒绝 `Host` 或 `Origin` 不是本地的请求。切勿绑定到 `0.0.0.0`：它没有登录。
- 它不保存任何令牌：使用你自己的 `gh`。
- 它不会自行向 GitHub 写入任何内容。只有 `dispatch --go`、`dispatch --real` 和 `finalize --execute` 会写入，且仅在你运行它们时。
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
├── monitor/                          程序本体
├── docs/                             架构、截图
├── tools/                            图片生成器
├── images/                           横幅图和图片
├── .github/                          CI 和议题表单
├── CHANGELOG.md                      各版本变更
├── LICENSE NOTICE AUTHORS            许可证和作者
├── CONTRIBUTING.md SECURITY.md       参与方式、报告
├── SUPPORT.md CODE_OF_CONDUCT.md     支持和行为准则
└── monitor/
    ├── actions_monitor.py            本地服务器
    ├── actions_monitor.html          网页
    ├── sentinel_local.py             警报与报告
    ├── surface.py readiness.py       检查与发布就绪
    ├── settings_api.py outputs.py    设置与指标
    ├── signstate.py sigverify.py     签名状态与验证
    ├── read_report.py                终端报告
    ├── gha_dispatch_all.py           批量构建
    ├── events.py report_history.py   事件与历史
    ├── ci_red.py export_status.py    供其他工具读取
    ├── i18n.py locales/              八种语言
    ├── toolconfig.py workspace.py    设置与克隆
    ├── tests/                        离线测试
    └── docs/                         设置与 Grafana
```

## 文档

- [`monitor/docs/SETTINGS_zho.md`](monitor/docs/SETTINGS_zho.md): 所有设置
- [`monitor/docs/OUTPUTS_zho.md`](monitor/docs/OUTPUTS_zho.md): 指标、Grafana 和导出
- [`monitor/docs/CI_RED_SCHEMA_zho.md`](monitor/docs/CI_RED_SCHEMA_zho.md): ci_red.json 的格式
- [`monitor/docs/CI_RED_BRIDGE_zho.md`](monitor/docs/CI_RED_BRIDGE_zho.md): 把 ci_red.json 带到仪表板
- [`monitor/QUICKSTART_zh.txt`](monitor/QUICKSTART_zh.txt): 入门步骤（八种语言）

## 参与贡献

请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。用议题表单报告缺陷和想法；安全问题请按 [SECURITY.md](SECURITY.md) 中的说明报告。

## 作者

作者：**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## 许可证

代码采用 GPL-3.0-or-later；文档采用 CC BY-SA 4.0。参见 [LICENSE](LICENSE) 和 [NOTICE](NOTICE)。
