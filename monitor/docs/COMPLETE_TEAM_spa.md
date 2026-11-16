<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_TEAM.md) | **🇪🇸 Español** | [🇫🇷 Français](COMPLETE_TEAM_fra.md) | [🇮🇹 Italiano](COMPLETE_TEAM_ita.md) | [🇩🇪 Deutsch](COMPLETE_TEAM_deu.md) | [🇨🇳 简体中文](COMPLETE_TEAM_zho.md) | [🇯🇵 日本語](COMPLETE_TEAM_jpn.md) | [🇵🇹 Português](COMPLETE_TEAM_por.md)

# Edición completa para un equipo

Varias personas leen el mismo monitor, cada una con su inicio de sesión y su rol. Está apagado por defecto (`auth.enabled`) y la edición lite nunca lo tiene. La lista completa de opciones está en la sección Modo equipo de [ADVANCED_spa.md](ADVANCED_spa.md).

## Primeros pasos

- Con `auth.enabled` activado, nada cambia hasta que existe el primer administrador: créalo en el ordenador que ejecuta el monitor (la página `/login` o `python -m github_actions_monitor.security.auth_cli create-admin`). En el modo de red el monitor no arranca sin uno.
- En una red usa HTTPS o una VPN: si no, la cookie de sesión y las contraseñas viajarían en claro.

## Roles

- `viewer` lee; `maintainer` además cambia el modo de trabajo y, solo desde el ordenador del monitor, silencia y reconoce alertas; `admin` además cambia ajustes y usuarios.
- Cada usuario ve solo las cuentas que se le asignan (un administrador ve todas); otra cuenta responde 403 `account_scope`.

## Sesiones y contraseñas

- El navegador recibe la cookie `monitor_session` y un token CSRF; un script inicia sesión con `POST /api/auth/login` y, solo si `auth.allow_bearer` está activado, envía `Authorization: Bearer`.
- Las contraseñas se guardan con un hash con sal y necesitan `auth.min_length` caracteres; tras `auth.max_failed_logins` errores el usuario queda bloqueado `auth.lockout_minutes`.

## Quién hizo qué

- El registro de acciones anota quién cambió qué ([AUDIT_LOG_spa.md](AUDIT_LOG_spa.md)); un maintainer solo lo lee si `audit_log.maintainers_can_read` está activado.
- La salud del equipo y la puntuación por cuenta están en [HEALTH_spa.md](HEALTH_spa.md) y [SCORE_spa.md](SCORE_spa.md); para un servidor que no se apaga, lee [COMPLETE_SERVICE_spa.md](COMPLETE_SERVICE_spa.md).
