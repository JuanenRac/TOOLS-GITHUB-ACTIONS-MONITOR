<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_SERVICE.md) | [🇪🇸 Español](COMPLETE_SERVICE_spa.md) | [🇫🇷 Français](COMPLETE_SERVICE_fra.md) | [🇮🇹 Italiano](COMPLETE_SERVICE_ita.md) | [🇩🇪 Deutsch](COMPLETE_SERVICE_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](COMPLETE_SERVICE_jpn.md) | [🇵🇹 Português](COMPLETE_SERVICE_por.md)

# 作为服务运行的完整版

适用于在服务器或容器中持续运行、由其他人或其他程序读取的监视器。这里只概述各种选择；细节、命令和变量表见 [DEPLOYMENT_zho.md](DEPLOYMENT_zho.md)。

## 如何监听

- 三种方式：仅本机（默认，无需登录）、网络（开启 `listen.network`，使用 `listen.host`，每个请求都带访问令牌）或在代理之后（`listen.proxy_public_host`、`listen.secure_cookie` 或 `listen.trusted_proxy`）。
- 请在网络模式前加上 HTTPS（证书或代理）或 VPN：使用普通 HTTP 时，令牌和密码会以明文传输。

## 如何运行

- 官方镜像、带可选代理的 Docker Compose，或使用 systemd 的传统安装；它们都会无浏览器地启动 `python -m github_actions_monitor.service`。
- 端口：完整版为 8765，简易版为 8766（`ports.complete`、`ports.lite`）。

## 盯住它

- `GET /api/health` 不会调用 GitHub；当某个刷新周期卡住时，`GET /api/health?deep=1` 返回 503，而 `python -m github_actions_monitor.cli.healthcheck` 为容器或服务管理器发出这个调用。
- 当 GitHub 撤销登录时，请通过命令行、管理员端点或 `SIGHUP` 替换凭据；重启无法修复丢失的登录。

## 运行数月

- 在 [STORAGE_zho.md](STORAGE_zho.md) 中选择文件或 SQLite 以及保留策略，每次升级前先备份，并阅读 [MIGRATING_zho.md](MIGRATING_zho.md)。
- 有人需要登录时，团队模式见 [COMPLETE_TEAM_zho.md](COMPLETE_TEAM_zho.md)；程序可以依赖的契约见 [API_zho.md](API_zho.md)。
