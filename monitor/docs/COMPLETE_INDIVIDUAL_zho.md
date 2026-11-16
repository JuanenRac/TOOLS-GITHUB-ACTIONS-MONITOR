<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_INDIVIDUAL.md) | [🇪🇸 Español](COMPLETE_INDIVIDUAL_spa.md) | [🇫🇷 Français](COMPLETE_INDIVIDUAL_fra.md) | [🇮🇹 Italiano](COMPLETE_INDIVIDUAL_ita.md) | [🇩🇪 Deutsch](COMPLETE_INDIVIDUAL_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](COMPLETE_INDIVIDUAL_jpn.md) | [🇵🇹 Português](COMPLETE_INDIVIDUAL_por.md)

# 面向个人的完整版

在自己的电脑上运行完整版是使用监视器的常规方式：一个人、一个 GitHub 账户、无需登录，页面只在 `127.0.0.1` 上打开。只想查看运行情况的人可以使用简易版 [LITE_zho.md](LITE_zho.md)。

## 开始

- 先用 `gh auth login` 登录一次 GitHub，然后启动 `MONITOR_GITHUB_ACTIONS`（`.bat`、`.sh` 或 `.command`）。页面在 8765 端口打开（`ports.complete`）。
- 在“设置”中选择要监视的仓库和生态系统。最初五分钟见 [FIRST_STEPS_zho.md](FIRST_STEPS_zho.md)。

## 你能得到什么

- 三个哨兵（CI 默认开启；Collab 和 Security 在你打开之前保持关闭）和一份可在本机静音的警报列表。
- 账户评分、每个仓库的健康状况、定时报告（默认关闭）以及已执行操作的日志（默认开启，`audit_log.enabled`）。
- 正常、快速和涡轮三种工作模式（[MODES_zho.md](MODES_zho.md)），以及额度紧张时的低额度模式（[QUOTA_zho.md](QUOTA_zho.md)）。

## 只留在这台电脑上

- `auth.enabled` 关闭（默认）时没有用户，也无需记住任何东西：只有多人使用监视器时才开启团队模式（[COMPLETE_TEAM_zho.md](COMPLETE_TEAM_zho.md)）。
- `listen.network` 默认关闭：页面和 API 只响应 `127.0.0.1`。若要让它一直运行，请阅读 [COMPLETE_SERVICE_zho.md](COMPLETE_SERVICE_zho.md)。

## 日常使用

- `python bin/monitor_cli.py status`、`doctor` 和 `health` 会询问正在运行的监视器（[CLI_zho.md](CLI_zho.md)）。升级请阅读 [MIGRATING_zho.md](MIGRATING_zho.md)。
- 你自己的脚本可以读取 API：[API_zho.md](API_zho.md) 列出了承诺不会改变的内容。
