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

# From 1.5.x to 1.6.x

Nothing you have has to be converted: the monitor keeps reading your `actions_monitor.json` and adds the new keys, with safe defaults, the first time you save from Settings.

1. Stop the monitor and unzip the new version over the old folder (keep your `actions_monitor.json` and your catalogue files).
2. Start it as before. New files appear next to it (`etag_cache.json`, `analytics_history.json`, `update_check.json`, `sentinel_history.json`); they can be deleted at any time.
3. Optional: `python actions_monitor.py --doctor` checks the installation.

What is different: the **lite edition** exists (`MONITOR_LITE_GITHUB_ACTIONS`, port 8766, its own `actions_monitor_lite.json`, no sentinel); **red on main** is one rule (the last finished run of each workflow on the default branch; cancelled, skipped, neutral and stale runs say nothing), so a figure may differ from 1.5.x; the Settings page has a **Basic** tab first; notifications, analytics, the linter, the webhook events and the AI assistant exist and are **off** until you switch them on; writing to GitHub still needs your explicit confirmation. Rich and Textual stay optional; Python 3.11 or newer.
