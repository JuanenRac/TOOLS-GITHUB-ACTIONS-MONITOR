<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI.md) | **🇪🇸 Español** | [🇫🇷 Français](CLI_fra.md) | [🇮🇹 Italiano](CLI_ita.md) | [🇩🇪 Deutsch](CLI_deu.md) | [🇨🇳 简体中文](CLI_zho.md) | [🇯🇵 日本語](CLI_jpn.md) | [🇵🇹 Português](CLI_por.md)

# La línea de comandos como cliente del monitor

`python monitor_cli.py COMANDO` pregunta al monitor en marcha lo que sabe (un `GET` en `127.0.0.1`, o en la dirección de `--url` / `MONITOR_URL`) y lo imprime. No repite el trabajo de la página contra GitHub, nunca escribe en GitHub y no cambia ningún ajuste. Las herramientas anteriores (`read_report.py`, `--doctor`, `gha_dispatch_all.py`) siguen funcionando igual.

## Comandos

| Comando | Qué muestra | Lite |
|---|---|---|
| `status` | versión, edición, cuenta, repositorios, qué corre y qué falla, la cuota | sí |
| `health` (o `check`) | una comprobación rápida antes de leer nada pesado: ¿se alcanza el monitor?, ¿acepta a este cliente?, ¿responde el acceso de GitHub de la cuenta? | sí |
| `doctor` | las comprobaciones de `--doctor` de esta instalación (el monitor no tiene que estar en marcha) | sí |
| `accounts` | las cuentas del supervisor (solo con varias cuentas) | no |
| `alerts` | las alertas de todos los centinelas en una lista: `--sentinel ci\|collab`, `--level info\|warning\|error`, `--muted show\|hide\|only` | no |
| `live` | el estado del receptor del webhook y los últimos eventos | no |

Opciones de todos los comandos: `--json` (la respuesta como un documento JSON: `{"ok", "exit", "data"}`), `--account ID`, `--url URL`, `--lite` (puerto 8766), `--timeout SEGUNDOS` (de 1 a 60), `--lang CÓDIGO`. En el modo red pon el token de acceso en la variable de entorno `MONITOR_ACCESS_TOKEN`, la que lee el propio monitor (`MONITOR_TOKEN` se acepta como alias; `--token TOKEN` es el último recurso, porque una opción se ve en la lista de procesos). El orden es: `MONITOR_ACCESS_TOKEN`, luego `MONITOR_TOKEN`, luego `--token`. Viaja en la cabecera `X-Monitor-Access`, nunca en la dirección ni en pantalla. Un `--url` con `http` sin cifrar hacia otro ordenador imprime un aviso por stderr (el token y las respuestas viajarían sin cifrar): usa `https` fuera de una red que controles.

Las horas escritas para las personas (la línea `Last read`, los silencios, el registro, los partes, las notificaciones) usan la zona de este ordenador y la nombran, con la hora UTC al lado (`11:43:07 CET (10:43:07 UTC)`). Elige otra zona con `display.timezone` (`local`, `utc` o un nombre como `Europe/Madrid`; la variable de entorno `MONITOR_TIMEZONE` manda sobre el archivo). `--json` conserva UTC y añade `updated_local`.

## Códigos de salida (estables)

| Código | Significado |
|---|---|
| 0 | todo bien |
| 1 | uso incorrecto del comando (también `--lite` con un comando que necesita la edición completa) |
| 2 | no se alcanza el monitor |
| 3 | el monitor rechaza a este cliente, o el acceso de GitHub de la cuenta falló o caducó (un problema de credencial, no una cuota agotada) |
| 4 | el monitor responde pero está degradado: sin conexión, cuota agotada, aún sin datos, un endpoint que no tiene, o una respuesta que no es JSON |
| 5 | `alerts --fail-on NIVEL` encontró una alerta abierta de ese nivel o peor (una alerta silenciada no cuenta) |

## Ejemplos

```
python monitor_cli.py health && python monitor_cli.py alerts --fail-on error
python monitor_cli.py alerts --sentinel collab --level warning --json
python monitor_cli.py status --account org-acme
MONITOR_URL=http://192.168.0.20:8765 MONITOR_ACCESS_TOKEN=... python monitor_cli.py health --json
```

`health` distingue tres cosas: el monitor no responde (2), el acceso de GitHub falla (3), y la cuota se agotó o no se alcanza GitHub (4); un monitor que no ha terminado su primera lectura lo dice (4) en vez de mostrar cifras vacías.

## La edición lite

`python monitor_cli.py status --lite`, `doctor --lite` y `health --lite` hablan con el puerto 8766. Los comandos que necesitan cuentas, centinelas o el receptor del webhook se rechazan con el código de salida 1. La edición lite no tiene cuentas ni API de alertas.
