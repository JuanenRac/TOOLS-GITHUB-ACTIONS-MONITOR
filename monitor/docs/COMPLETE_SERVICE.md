<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](COMPLETE_SERVICE_spa.md) | [🇫🇷 Français](COMPLETE_SERVICE_fra.md) | [🇮🇹 Italiano](COMPLETE_SERVICE_ita.md) | [🇩🇪 Deutsch](COMPLETE_SERVICE_deu.md) | [🇨🇳 简体中文](COMPLETE_SERVICE_zho.md) | [🇯🇵 日本語](COMPLETE_SERVICE_jpn.md) | [🇵🇹 Português](COMPLETE_SERVICE_por.md)

# Complete edition as a service

For a monitor that runs all the time on a server or in a container and is read by other people or other programs. This is a summary of the choices; the details, the commands and the table of variables are in [DEPLOYMENT.md](DEPLOYMENT.md).

## How it listens

- Three ways: this computer only (the default, no login), the network (`listen.network` on, `listen.host`, and the access token on every request) or behind a proxy (`listen.proxy_public_host`, `listen.secure_cookie` or `listen.trusted_proxy`).
- Put HTTPS (a certificate or a proxy) or a VPN in front of the network mode: over plain HTTP the token and the passwords travel in clear.

## How to run it

- The official image, Docker Compose with an optional proxy, or a classic install with systemd; all of them start `python -m github_actions_monitor.service` without a browser.
- The ports are 8765 for the complete edition and 8766 for the lite one (`ports.complete`, `ports.lite`).

## Keep an eye on it

- `GET /api/health` makes no call to GitHub; `GET /api/health?deep=1` answers 503 when a refresh cycle is stuck, and `python -m github_actions_monitor.cli.healthcheck` makes that call for a container or a service manager.
- When GitHub revokes the login, replace the credential from the command line, with the administrator endpoint or with `SIGHUP`; a restart does not fix a lost login.

## For months

- Choose files or SQLite and the retention in [STORAGE.md](STORAGE.md), make a backup before every upgrade and read [MIGRATING.md](MIGRATING.md).
- With people who sign in, the team mode is described in [COMPLETE_TEAM.md](COMPLETE_TEAM.md); the contract that programs can rely on is in [API.md](API.md).
