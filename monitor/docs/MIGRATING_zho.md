<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# 从 1.5.0 之前的版本更新

[English](MIGRATING.md) · [Español](MIGRATING_spa.md) · [Français](MIGRATING_fra.md) · [Italiano](MIGRATING_ita.md) · [Deutsch](MIGRATING_deu.md) · **简体中文** · [日本語](MIGRATING_jpn.md) · [Português](MIGRATING_por.md)

1.5.0 版给文件、文件夹、脚本和一项设置起了英文名称。不会丢失任何内容：监视器仍会读取旧名称，所以你可以先更新，之后再整理。

## 步骤

1. 停止监视器，把新版本解压到旧文件夹上（保留你的 `actions_monitor.json`）。
2. 查看会发生什么变化：`python migrate_state.py`（演练，不会改动任何内容）。
3. 执行：`python migrate_state.py --apply` 把旧文件复制到新名称并保留旧文件；加上 `--move` 则改为重命名。已存在的内容绝不会被覆盖，设置 `parte_history_days` 会在保存 `actions_monitor.json` 的副本之后改为 `report_history_days`。
4. 用 `MONITOR_GITHUB_ACTIONS`（与以前相同的启动器）启动监视器，批处理工具使用 `BATCH_GITHUB_ACTIONS`。
5. 删除你可能还留着的旧启动器：`LOTE_GITHUB_ACTIONS.bat`、`.sh` 和 `.command`。

## 旧名称与新名称

| 1.5.0 之前 | 1.5.0 起 |
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

`ci_red.json`、它的模式和 `--export-status` 的文件没有变化。在你于设置中选择其他语言之前，语言为英语。
