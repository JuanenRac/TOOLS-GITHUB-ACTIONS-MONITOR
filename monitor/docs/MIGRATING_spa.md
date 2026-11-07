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
