<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Atualizar a partir de uma versão anterior à 1.5.0

[English](MIGRATING.md) · [Español](MIGRATING_spa.md) · [Français](MIGRATING_fra.md) · [Italiano](MIGRATING_ita.md) · [Deutsch](MIGRATING_deu.md) · [简体中文](MIGRATING_zho.md) · [日本語](MIGRATING_jpn.md) · **Português**

A versão 1.5.0 deu nomes em inglês a ficheiros, pastas, scripts e a uma definição. Não se perde nada: o monitor continua a LER os nomes antigos, por isso pode atualizar primeiro e arrumar depois.

## Passos

1. Pare o monitor e descomprima a versão nova sobre a pasta antiga (mantenha o seu `actions_monitor.json`).
2. Veja o que mudaria: `python migrate_state.py` (simulação, não altera nada).
3. Faça-o: `python migrate_state.py --apply` copia os ficheiros antigos para os nomes novos e mantém os antigos; acrescente `--move` para os renomear. Nunca se substitui o que já existe, e a definição `parte_history_days` passa a `report_history_days` depois de guardar uma cópia de `actions_monitor.json`.
4. Arranque o monitor com `MONITOR_GITHUB_ACTIONS` (o mesmo lançador de sempre) e use `BATCH_GITHUB_ACTIONS` para as ferramentas por lotes.
5. Apague os lançadores antigos que ainda tenha: `LOTE_GITHUB_ACTIONS.bat`, `.sh` e `.command`.

## Nomes antigos e novos

| Antes da 1.5.0 | Desde a 1.5.0 |
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

`ci_red.json`, o seu esquema e os ficheiros de `--export-status` não mudaram. O idioma é o inglês até escolher outro nas definições.
