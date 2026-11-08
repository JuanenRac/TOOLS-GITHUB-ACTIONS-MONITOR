<p align="center">
  <img src="images/GITHUB_ACTIONS_MONITOR_BANNER.svg" alt="GitHub Actions Monitor" width="100%">
</p>

# GitHub Actions Monitor

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <b>🇪🇸 Español</b> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

<p align="center">
  <a href="https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases/latest"><img src="https://img.shields.io/github/v/release/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR?label=version&color=2EE6A6" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL-3.0-or-later">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Dependencies-none-2EE6A6.svg" alt="No dependencies">
  <img src="https://img.shields.io/badge/Languages-8-FFB300.svg" alt="8 languages">
</p>

> Vigila los workflows de todos tus repositorios y te dice, en una página local, qué está en rojo, qué está atascado y qué te espera.

**GitHub Actions Monitor** es un programa pequeño que se ejecuta en tu propio ordenador. Pregunta a GitHub, con tu propio acceso de `gh`, por las últimas ejecuciones de cada workflow de tus repositorios, decide qué está de verdad en rojo, avisa de lo importante (seguridad, higiene, versiones listas para publicar, cuota) y lo muestra en una página web que solo abre tu equipo. No necesita más que Python y `gh`, nunca guarda un token y, por defecto, solo lee.

## De un vistazo

| | |
|---|---|
| **Versión** | **1.6.0** · [todas las versiones](https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases) |
| **Necesita** | Python 3.11+ y la CLI de GitHub (`gh auth login`); nada más (la vista de consola usa el paquete opcional `rich`) |
| **Se abre** | en una página de `127.0.0.1` solamente, en ocho idiomas |
| **Escribe en GitHub** | nunca por sí solo: solo las órdenes por lotes que lances con un `--go` explícito |
| **Exporta** | `ci_red.json`, métricas Prometheus y JSON para Grafana (todo apagado hasta que lo actives) |

## Capturas

### La página

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_now_light.png"><img src="docs/screenshots/web_now_dark.png" alt="Ahora" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_light.png"><img src="docs/screenshots/web_sentinel_dark.png" alt="Centinela" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_queue_light.png"><img src="docs/screenshots/web_sentinel_queue_dark.png" alt="Cola de firma (lo más urgente primero)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_analytics_light.png"><img src="docs/screenshots/web_sentinel_analytics_dark.png" alt="A12 · Analítica: duraciones, tiempo en cola, pasos y workflows inestables" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_charts_light.png"><img src="docs/screenshots/web_charts_dark.png" alt="Gráficas" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_repositories_light.png"><img src="docs/screenshots/web_repositories_dark.png" alt="Repositorios" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_history_light.png"><img src="docs/screenshots/web_history_dark.png" alt="Historial" width="92%"></picture></p>

<details><summary><b>Configuración, subpestaña a subpestaña</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_interface_light.png"><img src="docs/screenshots/web_settings_interface_dark.png" alt="Configuración · Este navegador" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_general_light.png"><img src="docs/screenshots/web_settings_general_dark.png" alt="Configuración · General" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_polling_light.png"><img src="docs/screenshots/web_settings_polling_dark.png" alt="Configuración · Actualización y límites" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_cache_light.png"><img src="docs/screenshots/web_settings_cache_dark.png" alt="Configuración · Lecturas y caché" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_sentinel_light.png"><img src="docs/screenshots/web_settings_sentinel_dark.png" alt="Configuración · Centinela" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_surface_light.png"><img src="docs/screenshots/web_settings_surface_dark.png" alt="Configuración · Comprobaciones de superficie (A10)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_readiness_light.png"><img src="docs/screenshots/web_settings_readiness_dark.png" alt="Configuración · Preparación (A11)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_paths_light.png"><img src="docs/screenshots/web_settings_paths_dark.png" alt="Configuración · Carpetas y ficheros" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_outputs_light.png"><img src="docs/screenshots/web_settings_outputs_dark.png" alt="Configuración · Salidas para otras herramientas" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_ai_light.png"><img src="docs/screenshots/web_settings_ai_dark.png" alt="Configuración · IA externa para el centinela" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_webhook_light.png"><img src="docs/screenshots/web_settings_webhook_dark.png" alt="Configuración · Webhook de entrada" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_notify_light.png"><img src="docs/screenshots/web_settings_notify_dark.png" alt="Configuración · Notificaciones" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_analytics_light.png"><img src="docs/screenshots/web_settings_analytics_dark.png" alt="Configuración · Analítica" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_lint_light.png"><img src="docs/screenshots/web_settings_lint_dark.png" alt="Configuración · Linter de workflows" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_console_light.png"><img src="docs/screenshots/web_settings_console_dark.png" alt="Configuración · Vista de consola" width="92%"></picture></p>

</details>

<details><summary><b>Herramientas de consola</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_read_report_light.png"><img src="docs/screenshots/console_read_report_dark.png" alt="read_report.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_migrate_state_light.png"><img src="docs/screenshots/console_migrate_state_dark.png" alt="migrate_state.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_plan_light.png"><img src="docs/screenshots/console_plan_dark.png" alt="gha_dispatch_all.py plan" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_lint_light.png"><img src="docs/screenshots/console_lint_dark.png" alt="lint_workflows.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_tui_light.png"><img src="docs/screenshots/console_tui_dark.png" alt="tui.py" width="92%"></picture></p>

</details>

Cada imagen sigue el tema claro u oscuro de tu página de GitHub.

*Datos de demostración: los repositorios y nombres de las imágenes son inventados.*

## Qué hace

- **Rojo o no, con una sola regla**: la última ejecución terminada de cada workflow en la rama por defecto. Las ejecuciones canceladas u omitidas nunca tapan un fallo anterior.
- **Centinela**: alertas de seguridad, higiene de repositorios, pull requests antiguas, versiones listas para publicar, compilaciones pendientes de firma y un parte en lenguaje llano.
- **Página de ajustes**: cambia rutas, intervalos, cuotas e interruptores desde el navegador; solo una lista fija de claves, validadas, con copia de seguridad antes de cada guardado.
- **Gráficas e historial**: minutos de cómputo, fallos y éxitos con barras animadas y un historial diario (respeta el movimiento reducido).
- **Ocho idiomas** (en, es, de, fr, it, ja, zh, pt) con el inglés como base; se cambia en Ajustes.
- **Salidas para paneles**: `ci_red.json`, un punto de acceso Prometheus y una fuente JSON para Grafana, con un panel de Grafana importable.
- **Herramientas por lotes**: planifican y lanzan muchas compilaciones a la vez; nada se lanza sin `--go`.

## Arquitectura

<p align="center"><img src="images/architecture.svg" alt="Arquitectura" width="100%"></p>

## Inicio rápido

1. Instala Python 3.11 o superior y la [CLI de GitHub](https://cli.github.com/), y ejecuta `gh auth login`.
2. Descarga este repositorio (o el zip de la última release) y abre la carpeta `monitor`.
3. Arráncalo: en Windows `MONITOR_GITHUB_ACTIONS.bat`, en Linux `./MONITOR_GITHUB_ACTIONS.sh`, en macOS doble clic en `MONITOR_GITHUB_ACTIONS.command`, o `python actions_monitor.py` en cualquier sistema.
4. Abre la dirección que imprime (`http://127.0.0.1:<puerto>`). En el primer arranque crea `actions_monitor.json` a partir del ejemplo.
5. Abre **Ajustes** para indicar tu cuenta de GitHub, los ecosistemas (grupos de repositorios por prefijo de nombre) y lo demás.

> ¿Actualizas desde una versión anterior a la 1.5.0? [`monitor/docs/MIGRATING_spa.md`](monitor/docs/MIGRATING_spa.md)

## Ajustes

Todo vive en `actions_monitor.json` (se crea desde `actions_monitor.example.json`). La pestaña **Ajustes** lo edita con seguridad; los tokens y secretos nunca se muestran ni se guardan. Los ecosistemas, los objetivos de compilación y los perfiles de lotes son ficheros aparte a los que apuntas (`ecosystems_file`, `targets_file`, `profiles_file`); se incluyen plantillas neutras `*.example.json`. Referencia completa: [`monitor/docs/SETTINGS_spa.md`](monitor/docs/SETTINGS_spa.md).

## Salidas para Grafana y paneles

Todo apagado por defecto, solo local (`127.0.0.1`) y sin token adicional. Al activarlo en Ajustes obtienes `/metrics` (formato Prometheus), `/api/outputs/grafana.json` y `/api/outputs/dashboard.json`, además de un panel de Grafana importable en [`monitor/docs/grafana`](monitor/docs/grafana). Detalles: [`monitor/docs/OUTPUTS_spa.md`](monitor/docs/OUTPUTS_spa.md). El formato de `ci_red.json`: [`monitor/docs/CI_RED_SCHEMA_spa.md`](monitor/docs/CI_RED_SCHEMA_spa.md).

## Seguridad

- Escucha solo en `127.0.0.1` y rechaza las peticiones cuyo `Host` u `Origin` no sean locales. No lo enlaces nunca a `0.0.0.0`: no tiene inicio de sesión.
- No guarda ningún token: usa tu propio `gh`.
- No escribe nada en GitHub por sí solo. Solo `dispatch --go`, `dispatch --real` y `finalize --execute` escriben, y únicamente cuando tú los lanzas.
- **Analítica**: p50 / p95 de la duración, del tiempo en cola y de cada paso de cada workflow, workflows inestables (fallan y luego pasan en el mismo commit) y workflows que se han vuelto más lentos; exportado a Prometheus y Grafana.
- **Ahorra cuota y sobrevive a un corte**: lecturas condicionales (un 304 no cuesta nada) y un modo de última imagen con aviso de sin conexión que se reanuda solo.
- **Webhook de entrada y notificaciones**: eventos firmados actualizan un repositorio en tiempo real; mensajes opcionales a Telegram, Discord, Slack, Matrix, MQTT o una dirección local (nunca una escritura en GitHub).
- **Linter de workflows y vista de consola**: `lint_workflows.py` revisa `.github/workflows` antes de subir; `tui.py` (opcional, con `rich`) muestra una cuadrícula en vivo en la consola.
- **Asistente de IA (apagado por defecto)**: resúmenes, triaje y explicaciones con Ollama, un servicio compatible con OpenAI, Anthropic o `gh copilot`; solo comandos de una lista cerrada, que se ejecutan únicamente tras confirmar cada uno.
- La página de ajustes escribe una lista fija de claves, validadas, tras guardar una copia de seguridad.

## Pruebas

No necesitan red ni paquetes adicionales:

```
python -m unittest discover -s monitor/tests
```

## Estructura del repositorio

<p align="center"><img src="images/repository-structure.svg" alt="Estructura del repositorio" width="100%"></p>

```
TOOLS-GITHUB-ACTIONS-MONITOR/
├── monitor/                             el programa
├── docs/                                arquitectura, capturas, hoja de ruta
├── tools/                               dibujos, guías y demo
├── images/                              banner y dibujos
├── .github/                             CI y formularios
├── CHANGELOG.md                         cambios por versión
├── LICENSE NOTICE AUTHORS               licencias y autoría
├── CONTRIBUTING.md SECURITY.md          cómo ayudar, informar
├── SUPPORT.md CODE_OF_CONDUCT.md        soporte y conducta
└── monitor/
    ├── actions_monitor.py               servidor local
    ├── actions_monitor.html             la página web
    ├── sentinel_local.py                alertas y parte
    ├── surface.py readiness.py          comprobaciones, preparación
    ├── settings_api.py outputs.py       ajustes, métricas
    ├── signstate.py sigverify.py        firma: estado y control
    ├── read_report.py                   el parte en terminal
    ├── gha_dispatch_all.py              compilaciones por lotes
    ├── events.py report_history.py      eventos e historial
    ├── ci_red.py export_status.py       ficheros para otros
    ├── etagcache.py resilience.py       lecturas condicionales, conexión
    ├── analytics.py lint_workflows.py   duraciones, flaky, linter
    ├── notifiers.py ai_actions.py       notificaciones, lista cerrada IA
    ├── tui.py migrate_state.py          vista de consola, migración
    ├── i18n.py locales/                 ocho idiomas
    ├── toolconfig.py workspace.py       ajustes y clones
    ├── tests/                           tests sin red
    └── docs/                            guías, esquemas, Grafana
```

## Documentación

- [`monitor/docs/SETTINGS_spa.md`](monitor/docs/SETTINGS_spa.md): todos los ajustes
- [`monitor/docs/OUTPUTS_spa.md`](monitor/docs/OUTPUTS_spa.md): métricas, Grafana y exportaciones
- [`monitor/docs/CI_RED_SCHEMA_spa.md`](monitor/docs/CI_RED_SCHEMA_spa.md): el formato de ci_red.json
- [`monitor/docs/CI_RED_BRIDGE_spa.md`](monitor/docs/CI_RED_BRIDGE_spa.md): llevar ci_red.json a un panel
- [`monitor/docs/WEBHOOK_spa.md`](monitor/docs/WEBHOOK_spa.md): el webhook de entrada
- [`monitor/docs/NOTIFICATIONS_spa.md`](monitor/docs/NOTIFICATIONS_spa.md): notificaciones y el contrato de los adaptadores
- [`monitor/docs/AI_spa.md`](monitor/docs/AI_spa.md): el asistente de IA: proveedores, seguridad y acciones
- [`monitor/docs/ANALYTICS_spa.md`](monitor/docs/ANALYTICS_spa.md): analítica, lecturas condicionales y conexión perdida
- [`monitor/docs/CONSOLE_TOOLS_spa.md`](monitor/docs/CONSOLE_TOOLS_spa.md): el linter de workflows y la vista de consola
- [`monitor/docs/DEPLOYMENT_spa.md`](monitor/docs/DEPLOYMENT_spa.md): ejecutarlo como servicio, tras un proxy, permisos
- [`monitor/QUICKSTART_es.txt`](monitor/QUICKSTART_es.txt): primeros pasos, en ocho idiomas

## Contribuir

Lee [CONTRIBUTING.md](CONTRIBUTING.md). Informa de fallos e ideas con los formularios de incidencias; los problemas de seguridad, como se describe en [SECURITY.md](SECURITY.md).

## Autoría

Escrito por **JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## Licencia

El código es GPL-3.0-or-later; la documentación es CC BY-SA 4.0. Consulta [LICENSE](LICENSE) y [NOTICE](NOTICE).
