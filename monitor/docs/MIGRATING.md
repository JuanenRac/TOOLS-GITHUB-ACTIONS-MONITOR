<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Updating from a version before 1.5.0

**English** · [Español](MIGRATING_spa.md) · [Français](MIGRATING_fra.md) · [Italiano](MIGRATING_ita.md) · [Deutsch](MIGRATING_deu.md) · [简体中文](MIGRATING_zho.md) · [日本語](MIGRATING_jpn.md) · [Português](MIGRATING_por.md)

Version 1.5.0 gave English names to files, folders, scripts and one setting. Nothing is lost: the monitor still READS the old names, so you can update first and tidy up afterwards.

## Steps

1. Stop the monitor and unzip the new version over the old folder (keep your `actions_monitor.json`).
2. See what would change: `python migrate_state.py` (a dry run, it changes nothing).
3. Do it: `python migrate_state.py --apply` copies the old files to the new names and keeps the old ones; add `--move` to rename them instead. Nothing that already exists is overwritten, and the setting `parte_history_days` becomes `report_history_days` after saving a copy of `actions_monitor.json`.
4. Start the monitor with `MONITOR_GITHUB_ACTIONS` (the same launcher as before) and use `BATCH_GITHUB_ACTIONS` for the batch tools.
5. Delete the old launchers you may still have: `LOTE_GITHUB_ACTIONS.bat`, `.sh` and `.command`.

## Old and new names

| Before 1.5.0 | From 1.5.0 |
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

`ci_red.json`, its schema and the `--export-status` files did not change. The language is English until you choose another one in Settings.
