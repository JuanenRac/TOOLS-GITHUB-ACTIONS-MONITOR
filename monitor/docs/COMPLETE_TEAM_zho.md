<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_TEAM.md) | [🇪🇸 Español](COMPLETE_TEAM_spa.md) | [🇫🇷 Français](COMPLETE_TEAM_fra.md) | [🇮🇹 Italiano](COMPLETE_TEAM_ita.md) | [🇩🇪 Deutsch](COMPLETE_TEAM_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](COMPLETE_TEAM_jpn.md) | [🇵🇹 Português](COMPLETE_TEAM_por.md)

# 面向团队的完整版

多人读取同一个监视器，每人有各自的登录和角色。默认关闭（`auth.enabled`），简易版没有此功能。完整选项见 [ADVANCED_zho.md](ADVANCED_zho.md) 的“团队模式”一节。

## 第一步

- 开启 `auth.enabled` 后，在第一个管理员出现之前一切照旧：请在运行监视器的电脑上创建它（页面 `/login` 或 `python -m github_actions_monitor.security.auth_cli create-admin`）。在网络模式下，没有管理员时监视器不会启动。
- 在网络上请使用 HTTPS 或 VPN：否则会话 Cookie 和密码会以明文传输。

## 角色

- `viewer` 只读；`maintainer` 还能更改工作模式，并且仅在监视器所在电脑上静音和确认警报；`admin` 还能更改设置和用户。
- 每个用户只能看到分配给他的账户（管理员可看到全部）；其他账户返回 403 `account_scope`。

## 会话与密码

- 浏览器会得到 Cookie `monitor_session` 和一个 CSRF 令牌；脚本通过 `POST /api/auth/login` 登录，仅当 `auth.allow_bearer` 开启时才发送 `Authorization: Bearer`。
- 密码以加盐哈希保存，至少 `auth.min_length` 个字符；输错 `auth.max_failed_logins` 次后，该用户被锁定 `auth.lockout_minutes` 分钟。

## 谁做了什么

- 操作日志记录谁更改了什么（[AUDIT_LOG_zho.md](AUDIT_LOG_zho.md)）；只有 `audit_log.maintainers_can_read` 开启时，maintainer 才能读取。
- 团队健康状况和各账户评分见 [HEALTH_zho.md](HEALTH_zho.md) 和 [SCORE_zho.md](SCORE_zho.md)；对于一直开着的服务器，请阅读 [COMPLETE_SERVICE_zho.md](COMPLETE_SERVICE_zho.md)。
