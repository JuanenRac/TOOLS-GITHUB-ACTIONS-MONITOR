<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LITE.md) | **🇪🇸 Español** | [🇫🇷 Français](LITE_fra.md) | [🇮🇹 Italiano](LITE_ita.md) | [🇩🇪 Deutsch](LITE_deu.md) | [🇨🇳 简体中文](LITE_zho.md) | [🇯🇵 日本語](LITE_jpn.md) | [🇵🇹 Português](LITE_por.md)

# La edición lite

Un segundo producto, más sencillo, en el mismo paquete: la página de lo que corre y lo que falla, sin el centinela. Es para quien solo quiere vigilar sus runs.

|  | Completa | Lite |
|---|---|---|
| Arranque | `MONITOR_GITHUB_ACTIONS` (`.bat` / `.sh` / `.command`) | `MONITOR_LITE_GITHUB_ACTIONS` (los mismos tres) |
| Puerto | 8765 | 8766 |
| Pestañas | Ahora, Centinela, Gráficas, Repositorios, Historial, Configuración | Ahora, Gráficas, Repositorios, Historial, una Configuración corta |
| Cabecera | todos los recuadros, preparación, firma | en curso, en cola, fallos y éxitos de 24 h, minutos de cómputo, issues, rojos en main, repositorios, cuota, conexión |
| Centinela (alertas, releases, cola de firma, preparación, linter) | sí | no: ni siquiera se importa |
| Analítica, notificaciones, webhook, IA, salidas Prometheus / Grafana | sí, apagadas hasta que las actives | no: esas rutas responden 404 |
| Configuración | `actions_monitor.json` | `actions_monitor_lite.json` (se crea en el primer arranque; el centinela va apagado) |
| Archivos de estado | `etag_cache.json`, `analytics_history.json`... | los mismos nombres con el sufijo `_lite` |

Cómo arrancarla: `MONITOR_LITE_GITHUB_ACTIONS.bat` en Windows, `./MONITOR_LITE_GITHUB_ACTIONS.sh` en Linux, doble clic en `MONITOR_LITE_GITHUB_ACTIONS.command` en macOS, o `python actions_monitor.py --lite` (también `MONITOR_MODE=lite`). Escucha en `127.0.0.1:8766`, así que la completa puede correr a la vez.

La Configuración corta tiene la cuenta (`github_owner`), los repositorios y ecosistemas a vigilar (`repos`, `ecosystems`, `exclude`), el tiempo de refresco (`refresh_seconds`), el idioma y el tema. «Rojos en main» cuenta los workflows cuyo último run terminado falló. Para tener después el centinela y lo demás, arranca la completa: no hay nada que migrar. La primera vez que arranca, `actions_monitor_lite.json` copia de `actions_monitor.json` (si existe) la cuenta, los repositorios y ecosistemas a vigilar, los archivos de catálogo y el idioma, y lo dice en la consola; nunca copia el centinela, la IA, el webhook, las salidas ni las notificaciones. Sin ese archivo vigila todos los ecosistemas (`"ecosystems": "all"`). El navegador recuerda el tema por separado para cada puerto. La edición lite no escribe `ci_red.json` ni cola de firma y guarda sus propios archivos de estado; si alguna vez das a ambas ediciones un `sentinel.ci_red_file`, no las apuntes al mismo archivo.
