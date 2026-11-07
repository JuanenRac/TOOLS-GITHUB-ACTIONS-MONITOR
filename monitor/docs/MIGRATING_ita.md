<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Aggiornare da una versione precedente alla 1.5.0

[English](MIGRATING.md) · [Español](MIGRATING_spa.md) · [Français](MIGRATING_fra.md) · **Italiano** · [Deutsch](MIGRATING_deu.md) · [简体中文](MIGRATING_zho.md) · [日本語](MIGRATING_jpn.md) · [Português](MIGRATING_por.md)

La versione 1.5.0 ha dato nomi inglesi a file, cartelle, script e a un'impostazione. Non si perde nulla: il monitor continua a LEGGERE i vecchi nomi, quindi puoi aggiornare prima e riordinare dopo.

## Passi

1. Ferma il monitor e decomprimi la nuova versione sulla vecchia cartella (conserva il tuo `actions_monitor.json`).
2. Guarda cosa cambierebbe: `python migrate_state.py` (simulazione, non cambia nulla).
3. Fallo: `python migrate_state.py --apply` copia i vecchi file ai nuovi nomi e conserva i vecchi; aggiungi `--move` per rinominarli. Ciò che esiste già non viene mai sovrascritto, e l'impostazione `parte_history_days` diventa `report_history_days` dopo aver salvato una copia di `actions_monitor.json`.
4. Avvia il monitor con `MONITOR_GITHUB_ACTIONS` (lo stesso avviatore di prima) e usa `BATCH_GITHUB_ACTIONS` per gli strumenti a lotti.
5. Elimina i vecchi avviatori che ti restano: `LOTE_GITHUB_ACTIONS.bat`, `.sh` e `.command`.

## Nomi vecchi e nuovi

| Prima della 1.5.0 | Dalla 1.5.0 |
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

`ci_red.json`, il suo schema e i file di `--export-status` non sono cambiati. La lingua è l'inglese finché non ne scegli un'altra nelle impostazioni.
