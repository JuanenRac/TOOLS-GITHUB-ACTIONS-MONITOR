<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](COMPLETE_TEAM_spa.md) | [🇫🇷 Français](COMPLETE_TEAM_fra.md) | [🇮🇹 Italiano](COMPLETE_TEAM_ita.md) | [🇩🇪 Deutsch](COMPLETE_TEAM_deu.md) | [🇨🇳 简体中文](COMPLETE_TEAM_zho.md) | [🇯🇵 日本語](COMPLETE_TEAM_jpn.md) | [🇵🇹 Português](COMPLETE_TEAM_por.md)

# Complete edition for a team

Several people read the same monitor, each with a login and a role. It is off by default (`auth.enabled`) and the lite edition never has it. The full list of options is in the section Team mode of [ADVANCED.md](ADVANCED.md).

## First steps

- With `auth.enabled` on, nothing changes until the first administrator exists: create it on the computer that runs the monitor (the page `/login` or `python -m github_actions_monitor.security.auth_cli create-admin`). In the network mode the monitor does not start without one.
- Over a network use HTTPS or a VPN: the session cookie and the passwords would travel in clear otherwise.

## Roles

- `viewer` reads; `maintainer` also changes the working mode and, from the computer of the monitor only, silences and acknowledges alerts; `admin` also changes settings and users.
- Each user sees only the accounts assigned to them (an administrator sees all); another account answers 403 `account_scope`.

## Sessions and passwords

- The browser gets the cookie `monitor_session` and a CSRF token; a script logs in with `POST /api/auth/login` and, only if `auth.allow_bearer` is on, sends `Authorization: Bearer`.
- Passwords are kept as a salted hash and need `auth.min_length` characters; after `auth.max_failed_logins` wrong ones the user is locked for `auth.lockout_minutes`.

## Who did what

- The log of actions records who changed what ([AUDIT_LOG.md](AUDIT_LOG.md)); a maintainer reads it only when `audit_log.maintainers_can_read` is on.
- The health of the team and the score per account are in [HEALTH.md](HEALTH.md) and [SCORE.md](SCORE.md); for a server that stays on, read [COMPLETE_SERVICE.md](COMPLETE_SERVICE.md).
