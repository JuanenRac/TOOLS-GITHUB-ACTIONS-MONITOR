<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Mise à jour depuis une version antérieure à la 1.5.0

[English](MIGRATING.md) · [Español](MIGRATING_spa.md) · **Français** · [Italiano](MIGRATING_ita.md) · [Deutsch](MIGRATING_deu.md) · [简体中文](MIGRATING_zho.md) · [日本語](MIGRATING_jpn.md) · [Português](MIGRATING_por.md)

La version 1.5.0 a donné des noms anglais aux fichiers, dossiers, scripts et à un réglage. Rien n'est perdu : le moniteur continue de LIRE les anciens noms, vous pouvez donc mettre à jour d'abord et ranger ensuite.

## Étapes

1. Arrêtez le moniteur et décompressez la nouvelle version sur l'ancien dossier (gardez votre `actions_monitor.json`).
2. Voyez ce qui changerait : `python migrate_state.py` (simulation, ne change rien).
3. Faites-le : `python migrate_state.py --apply` copie les anciens fichiers vers les nouveaux noms et garde les anciens ; ajoutez `--move` pour les renommer à la place. Rien d'existant n'est écrasé, et le réglage `parte_history_days` devient `report_history_days` après sauvegarde d'une copie de `actions_monitor.json`.
4. Démarrez le moniteur avec `MONITOR_GITHUB_ACTIONS` (le même lanceur qu'avant) et utilisez `BATCH_GITHUB_ACTIONS` pour les outils par lots.
5. Supprimez les anciens lanceurs qu'il vous reste : `LOTE_GITHUB_ACTIONS.bat`, `.sh` et `.command`.

## Anciens et nouveaux noms

| Avant la 1.5.0 | Depuis la 1.5.0 |
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

`ci_red.json`, son schéma et les fichiers de `--export-status` n'ont pas changé. La langue est l'anglais tant que vous n'en choisissez pas une autre dans les réglages.
