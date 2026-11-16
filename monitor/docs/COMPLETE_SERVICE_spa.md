<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_SERVICE.md) | **🇪🇸 Español** | [🇫🇷 Français](COMPLETE_SERVICE_fra.md) | [🇮🇹 Italiano](COMPLETE_SERVICE_ita.md) | [🇩🇪 Deutsch](COMPLETE_SERVICE_deu.md) | [🇨🇳 简体中文](COMPLETE_SERVICE_zho.md) | [🇯🇵 日本語](COMPLETE_SERVICE_jpn.md) | [🇵🇹 Português](COMPLETE_SERVICE_por.md)

# Edición completa como servicio

Para un monitor que funciona siempre en un servidor o en un contenedor y que leen otras personas u otros programas. Es un resumen de las decisiones; los detalles, los comandos y la tabla de variables están en [DEPLOYMENT_spa.md](DEPLOYMENT_spa.md).

## Cómo escucha

- De tres maneras: solo este ordenador (lo normal, sin inicio de sesión), la red (`listen.network` activado, `listen.host` y el token de acceso en cada petición) o detrás de un proxy (`listen.proxy_public_host`, `listen.secure_cookie` o `listen.trusted_proxy`).
- Pon HTTPS (un certificado o un proxy) o una VPN delante del modo de red: con HTTP sin cifrar el token y las contraseñas viajan en claro.

## Cómo ejecutarlo

- La imagen oficial, Docker Compose con un proxy opcional o una instalación clásica con systemd; todas arrancan `python -m github_actions_monitor.service` sin navegador.
- Los puertos son 8765 para la edición completa y 8766 para la lite (`ports.complete`, `ports.lite`).

## Vigilarlo

- `GET /api/health` no llama a GitHub; `GET /api/health?deep=1` responde 503 cuando un ciclo de actualización está atascado, y `python -m github_actions_monitor.cli.healthcheck` hace esa llamada para un contenedor o un gestor de servicios.
- Cuando GitHub revoca el acceso, sustituye la credencial desde la línea de comandos, con el endpoint de administración o con `SIGHUP`; reiniciar no arregla un acceso perdido.

## Durante meses

- Elige ficheros o SQLite y la retención en [STORAGE_spa.md](STORAGE_spa.md), haz una copia de seguridad antes de cada actualización y lee [MIGRATING_spa.md](MIGRATING_spa.md).
- Con personas que inician sesión, el modo equipo está descrito en [COMPLETE_TEAM_spa.md](COMPLETE_TEAM_spa.md); el contrato en el que pueden confiar los programas está en [API_spa.md](API_spa.md).
