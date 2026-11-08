<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# 1.5.0 より前のバージョンからの更新

[English](MIGRATING.md) · [Español](MIGRATING_spa.md) · [Français](MIGRATING_fra.md) · [Italiano](MIGRATING_ita.md) · [Deutsch](MIGRATING_deu.md) · [简体中文](MIGRATING_zho.md) · **日本語** · [Português](MIGRATING_por.md)

バージョン 1.5.0 で、ファイル、フォルダー、スクリプト、1つの設定に英語の名前が付きました。失われるものはありません。モニターは古い名前も引き続き読み込むので、先に更新して、あとで整理できます。

## 手順

1. モニターを停止し、新しいバージョンを古いフォルダーの上に展開します（`actions_monitor.json` は残します）。
2. 何が変わるかを確認します：`python migrate_state.py`（ドライラン。何も変更しません）。
3. 実行します：`python migrate_state.py --apply` は古いファイルを新しい名前にコピーし、古いファイルは残します。`--move` を付けると代わりに名前を変更します。既にあるものは上書きされず、設定 `parte_history_days` は `actions_monitor.json` のコピーを保存した後に `report_history_days` になります。
4. モニターは `MONITOR_GITHUB_ACTIONS`（これまでと同じランチャー）で起動し、バッチツールには `BATCH_GITHUB_ACTIONS` を使います。
5. 残っている古いランチャーを削除します：`LOTE_GITHUB_ACTIONS.bat`、`.sh`、`.command`。

## 旧名と新名

| 1.5.0 より前 | 1.5.0 以降 |
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

`ci_red.json`、そのスキーマ、`--export-status` のファイルは変わっていません。言語は、設定で別の言語を選ぶまで英語です。

# 1.5.x から 1.6.x へ

変換が必要なものはありません。モニターは `actions_monitor.json` をそのまま読み続け、設定から初めて保存したときに安全な既定値で新しいキーを追加します。

1. モニターを止め、新しいバージョンを古いフォルダーの上に展開します（`actions_monitor.json` とカタログファイルは残します）。
2. 今までどおり起動します。隣に新しいファイル（`etag_cache.json`、`analytics_history.json`、`update_check.json`、`sentinel_history.json`）が作られます。いつでも削除できます。
3. 任意: `python actions_monitor.py --doctor` でインストールを確認できます。

変わる点: **lite 版**が加わりました（`MONITOR_LITE_GITHUB_ACTIONS`、ポート 8766、専用の `actions_monitor_lite.json`、センチネルなし）。**main で赤**は1つの規則になりました（各ワークフローの既定ブランチで最後に完了した run。取り消し・スキップ・neutral・stale は判定に影響しません）。そのため数値が 1.5.x と異なる場合があります。設定ページは先頭に**基本**タブがあります。通知、分析、リンター、webhook イベント、AI アシスタントはありますが、有効にするまで**オフ**です。GitHub への書き込みには引き続き明示的な確認が必要です。Rich と Textual は任意で、Python 3.11 以上が必要です。
