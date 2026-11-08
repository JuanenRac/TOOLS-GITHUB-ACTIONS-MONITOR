<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Actualizar desde una versión anterior a la 1.5.0

[English](MIGRATING.md) · **Español** · [Français](MIGRATING_fra.md) · [Italiano](MIGRATING_ita.md) · [Deutsch](MIGRATING_deu.md) · [简体中文](MIGRATING_zho.md) · [日本語](MIGRATING_jpn.md) · [Português](MIGRATING_por.md)

La versión 1.5.0 puso nombres en inglés a ficheros, carpetas, scripts y un ajuste. No se pierde nada: el monitor sigue LEYENDO los nombres antiguos, así que puedes actualizar primero y ordenar después.

## Pasos

1. Para el monitor y descomprime la versión nueva sobre la carpeta antigua (conserva tu `actions_monitor.json`).
2. Mira qué cambiaría: `python migrate_state.py` (simulación, no cambia nada).
3. Hazlo: `python migrate_state.py --apply` copia los ficheros antiguos a los nombres nuevos y conserva los antiguos; añade `--move` para renombrarlos en su lugar. Nunca se sobrescribe lo que ya existe, y el ajuste `parte_history_days` pasa a `report_history_days` tras guardar una copia de `actions_monitor.json`.
4. Arranca el monitor con `MONITOR_GITHUB_ACTIONS` (el mismo lanzador de siempre) y usa `BATCH_GITHUB_ACTIONS` para las herramientas por lotes.
5. Borra los lanzadores antiguos que te queden: `LOTE_GITHUB_ACTIONS.bat`, `.sh` y `.command`.

## Nombres antiguos y nuevos

| Antes de la 1.5.0 | Desde la 1.5.0 |
|---|---|
| `leer_parte.py` | `read_report.py` |
| `eventos.py`, `parte_history.py` | `events.py`, `report_history.py` |
| `LOTE_GITHUB_ACTIONS.*` | `BATCH_GITHUB_ACTIONS.*` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` |
| `PARTE_CENTINELA_*` | `SENTINEL_REPORT_*` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_*.json` | `<signed_dir>/batches/batch_*.json` |
| `parte_history_days` | `report_history_days` |
| `monitor_y_centinela` | `github_actions_monitor` |

`ci_red.json`, su esquema y los ficheros de `--export-status` no cambiaron. El idioma es el inglés hasta que elijas otro en Ajustes.

# De 1.5.x a 1.6.x

No hay nada que convertir: el monitor sigue leyendo tu `actions_monitor.json` y añade las claves nuevas, con valores seguros, la primera vez que guardas desde Ajustes.

1. Detén el monitor y descomprime la versión nueva sobre la carpeta antigua (conserva tu `actions_monitor.json` y tus archivos de catálogo).
2. Arráncalo como antes. Junto a él aparecen archivos nuevos (`etag_cache.json`, `analytics_history.json`, `update_check.json`, `sentinel_history.json`); se pueden borrar en cualquier momento.
3. Opcional: `python actions_monitor.py --doctor` comprueba la instalación.

Qué cambia: existe la **edición lite** (`MONITOR_LITE_GITHUB_ACTIONS`, puerto 8766, su propio `actions_monitor_lite.json`, sin centinela); el **rojo en main** es una sola regla (el último run terminado de cada workflow en la rama por defecto; los runs cancelados, omitidos, neutrales y caducados no dicen nada), así que una cifra puede diferir de la 1.5.x; la página de Ajustes tiene primero una pestaña **Básico**; las notificaciones, la analítica, el linter, los eventos del webhook y el asistente de IA existen y están **apagados** hasta que los actives; escribir en GitHub sigue exigiendo tu confirmación explícita. Rich y Textual siguen siendo opcionales; Python 3.11 o superior.
