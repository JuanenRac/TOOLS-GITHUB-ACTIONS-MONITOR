<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LITE.md) | [🇪🇸 Español](LITE_spa.md) | [🇫🇷 Français](LITE_fra.md) | [🇮🇹 Italiano](LITE_ita.md) | [🇩🇪 Deutsch](LITE_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](LITE_jpn.md) | [🇵🇹 Português](LITE_por.md)

# lite 版

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

启动方式:Windows 用 `MONITOR_LITE_GITHUB_ACTIONS.bat`,Linux 用 `./MONITOR_LITE_GITHUB_ACTIONS.sh`,macOS 双击 `MONITOR_LITE_GITHUB_ACTIONS.command`,或 `python bin/actions_monitor.py --lite`(也可用 `MONITOR_MODE=lite`)。它监听 `127.0.0.1:8766`,所以完整版可以同时运行。

简短设置包含账户(`github_owner`)、要监视的仓库和生态系统(`repos`、`ecosystems`、`exclude`)、刷新时间(`refresh_seconds`)、语言和主题。“main 上的红色”统计最近一次完成的运行失败的工作流数量。以后想要哨兵等功能,直接启动完整版即可:无需迁移任何东西。 首次启动时,`actions_monitor_lite.json` 会从 `actions_monitor.json`(如果存在)复制账户、要监视的仓库和生态系统、目录文件以及语言,并在控制台说明;绝不会复制哨兵、AI、Webhook、输出或通知。没有该文件时,它监视所有生态系统(`"ecosystems": "all"`)。浏览器会按端口分别记住主题。 lite 版不写入 `ci_red.json` 和签名队列,并使用自己的状态文件;如果你给两个版本都设置了 `sentinel.ci_red_file`,请不要指向同一个文件。

## 命令行

`python bin/monitor_cli.py status --lite`、`doctor --lite` 和 `health --lite` 会查询端口 8766 上的精简版监视器（见 [CLI_zho.md](CLI_zho.md)）；需要账户或哨兵的命令会被拒绝。页面同样有底部状态栏和可排序的表格。

## 存储

精简版只使用普通文件:没有数据库,没有保留任务,也没有 [STORAGE_zho.md](STORAGE_zho.md) 中的任何选项。
