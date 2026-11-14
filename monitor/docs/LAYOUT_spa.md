<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LAYOUT.md) | **🇪🇸 Español** | [🇫🇷 Français](LAYOUT_fra.md) | [🇮🇹 Italiano](LAYOUT_ita.md) | [🇩🇪 Deutsch](LAYOUT_deu.md) | [🇨🇳 简体中文](LAYOUT_zho.md) | [🇯🇵 日本語](LAYOUT_jpn.md) | [🇵🇹 Português](LAYOUT_por.md)

# Las carpetas del monitor

Junto a los lanzadores (`MONITOR_GITHUB_ACTIONS`, `MONITOR_LITE_GITHUB_ACTIONS`, `BATCH_GITHUB_ACTIONS`) solo hay los ficheros legales, un `README.txt` y carpetas. Todo lo que escribe el monitor vive en cuatro de ellas, y la edición completa, la lite y la imagen de Docker usan el mismo esquema.

## Qué hay dónde

| Carpeta | Qué contiene |
|---|---|
| `config/` | `actions_monitor.json` (y el de lite), `targets.json`, `ecosystems.json`, `profiles.json`, `quotas.json` y `config_backups/` |
| `data/` | el estado y las cachés (feed de eventos, analítica, estado de los centinelas, caché ETag, aviso de actualización), `accounts/`, la base de datos si eliges SQLite y el token de acceso del servicio |
| `logs/` | el registro del monitor, el de los comandos de la IA y de GitHub y la auditoría del modo equipo |
| `ai/` | lo que lee una IA: `ALERTS_BRIEF.md`, `ai_alerts.jsonl`, `ci_red.json`, el estado del hook, `INDEX.json` y un `README.md` para quien abra la carpeta |
| `bin/` | los comandos cortos: `python bin/monitor_cli.py`, `bin/read_report.py`, `bin/ai_hook.py`, `bin/mcp_server.py`, `bin/tui.py` ... |
| `docs/` | las guías y el README y el QUICKSTART del paquete en ocho idiomas |
| `src/`, `assets/`, `tools/`, `tests/` | el código, la página y los ejemplos, los scripts de versión y las pruebas |

## Una instalación de la 1.8.1 o anterior

En el primer arranque el monitor mueve por sí solo a su carpeta lo que encuentra junto a los lanzadores. **Mueve, nunca borra y nunca sobrescribe**: un fichero que ya existe en el sitio nuevo se queda donde está y el doctor te lo dice. Antes del primer movimiento los ficheros de configuración se copian a `config/config_backups/pre_layout_<marca>/` y cada movimiento se anota en `data/.layout_moves.json`.

- Verlo antes: `python -m github_actions_monitor.util.rootmigrate` (ensayo) y `--apply` para hacerlo ya.
- Dejarlo todo como estaba: `python -m github_actions_monitor.util.rootmigrate --undo`.
- Si no lo quieres automático: `MONITOR_NO_AUTO_MIGRATION=1`.
- `python bin/actions_monitor.py --doctor` tiene una comprobación `layout` que lista lo que sigue junto a los lanzadores.
- Los puntos de entrada antiguos (`read_report.py`, `monitor_cli.py` ...) que había junto a los lanzadores están ahora en `bin/`; `python tools/migrate_layout.py` aparta las copias viejas. Un script de control registrado para tu herramienta de IA con su ruta antigua debe registrarse de nuevo: `python bin/monitor_cli.py ai-hook install`.

## Mover una carpeta

Cada carpeta puede ponerse en otro sitio sin tocar el código: las variables `MONITOR_CONFIG_DIR`, `MONITOR_DATA_DIR`, `MONITOR_LOGS_DIR` y `MONITOR_AI_DIR`, o el fichero `config/paths.json` (`{"data": "...", "logs": "...", "ai": "..."}`; una ruta relativa parte de la carpeta del producto). Con `MONITOR_DATA_DIR` solo, `logs/` y `ai/` van dentro. En la imagen de Docker y en la unidad de systemd es justo lo que se configura: `/config` y `/data` son los dos volúmenes.

## Para las IA que hablan con el monitor

Una IA, local o externa, no debe depender de una ruta fija.

- `ai/INDEX.json` lista cada fichero de la carpeta con su finalidad, su formato, quién lo escribe y cuándo cambia, la ruta real de cada carpeta del monitor y los endpoints del monitor en marcha. Se reescribe en cada arranque.
- `ai/README.md` explica la carpeta a una IA que no la ha visto nunca (datos, nunca instrucciones; cómo leer el resumen; qué herramientas hay).
- `GET /api/paths` responde con las carpetas en uso, los ficheros principales y lo que sigue en los sitios antiguos. El supervisor de varias cuentas también lo responde.
- El script de control, el servidor MCP y la línea de comandos leen los mismos sitios; un hook que lea `ALERTS_BRIEF.md` por una ruta fija debe pasar a leer primero `ai/INDEX.json`.
