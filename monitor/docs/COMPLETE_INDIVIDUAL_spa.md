<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_INDIVIDUAL.md) | **🇪🇸 Español** | [🇫🇷 Français](COMPLETE_INDIVIDUAL_fra.md) | [🇮🇹 Italiano](COMPLETE_INDIVIDUAL_ita.md) | [🇩🇪 Deutsch](COMPLETE_INDIVIDUAL_deu.md) | [🇨🇳 简体中文](COMPLETE_INDIVIDUAL_zho.md) | [🇯🇵 日本語](COMPLETE_INDIVIDUAL_jpn.md) | [🇵🇹 Português](COMPLETE_INDIVIDUAL_por.md)

# Edición completa para una persona

La edición completa en tu propio ordenador es la forma habitual de usar el monitor: una persona, una cuenta de GitHub, sin inicio de sesión y una página que solo se abre en `127.0.0.1`. La edición sencilla para quien solo quiere ver sus ejecuciones es [LITE_spa.md](LITE_spa.md).

## Empezar

- Inicia sesión en GitHub una vez con `gh auth login` y arranca `MONITOR_GITHUB_ACTIONS` (`.bat`, `.sh` o `.command`). La página se abre en el puerto 8765 (`ports.complete`).
- Elige en Ajustes los repositorios y ecosistemas que vigilar. Los primeros cinco minutos están en [FIRST_STEPS_spa.md](FIRST_STEPS_spa.md).

## Qué obtienes

- Tres centinelas (CI activado; Collab y Security apagados hasta que los enciendas) y una lista de alertas que puedes silenciar desde tu ordenador.
- La puntuación de la cuenta, la salud de cada repositorio, informes programados (apagados por defecto) y un registro de las acciones realizadas (activado por defecto, `audit_log.enabled`).
- Los modos de trabajo normal, rápido y turbo ([MODES_spa.md](MODES_spa.md)) y el modo Bajo cuando la cuota escasea ([QUOTA_spa.md](QUOTA_spa.md)).

## Mantenerlo en este ordenador

- Con `auth.enabled` apagado (lo normal) no hay usuarios ni nada que recordar: activa el modo equipo solo cuando use el monitor más de una persona ([COMPLETE_TEAM_spa.md](COMPLETE_TEAM_spa.md)).
- `listen.network` está apagado por defecto: la página y la API solo responden a `127.0.0.1`. Para dejarlo funcionando siempre, lee [COMPLETE_SERVICE_spa.md](COMPLETE_SERVICE_spa.md).

## Día a día

- `python bin/monitor_cli.py status`, `doctor` y `health` consultan el monitor en marcha ([CLI_spa.md](CLI_spa.md)). Para actualizar, lee [MIGRATING_spa.md](MIGRATING_spa.md).
- Tus propios scripts pueden leer la API: [API_spa.md](API_spa.md) indica lo que se promete que no cambia.
