<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LAYOUT.md) | [🇪🇸 Español](LAYOUT_spa.md) | [🇫🇷 Français](LAYOUT_fra.md) | [🇮🇹 Italiano](LAYOUT_ita.md) | [🇩🇪 Deutsch](LAYOUT_deu.md) | [🇨🇳 简体中文](LAYOUT_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](LAYOUT_por.md)

# モニターのフォルダー

起動スクリプト(`MONITOR_GITHUB_ACTIONS`、`MONITOR_LITE_GITHUB_ACTIONS`、`BATCH_GITHUB_ACTIONS`)の隣にあるのは、法的なファイル、`README.txt` が 1 つ、そしてフォルダーだけです。モニターが書き出すものはすべて次の 4 つのフォルダーに置かれ、完全版、lite 版、Docker イメージは同じ構成を使います。

## 何がどこにあるか

| フォルダー | 内容 |
|---|---|
| `config/` | `actions_monitor.json`(lite 版のものも)、`targets.json`、`ecosystems.json`、`profiles.json`、`quotas.json`、`config_backups/` |
| `data/` | 状態とキャッシュ(イベントフィード、分析、センチネルの状態、ETag キャッシュ、更新通知)、`accounts/`、SQLite を選んだ場合のデータベース、サービスのアクセストークン |
| `logs/` | モニターのログ、AI と GitHub のコマンドのログ、チームモードの監査 |
| `ai/` | AI が読むもの:`ALERTS_BRIEF.md`、`ai_alerts.jsonl`、`ci_red.json`、フックの状態、`INDEX.json`、フォルダーを開く人のための `README.md` |
| `bin/` | 短いコマンド:`python bin/monitor_cli.py`、`bin/read_report.py`、`bin/ai_hook.py`、`bin/mcp_server.py`、`bin/tui.py` など |
| `docs/` | ガイドと、8 言語のパッケージ用 README と QUICKSTART |
| `src/`、`assets/`、`tools/`、`tests/` | コード、ページとサンプル、リリース用スクリプト、テスト |

## 1.8.1 以前のインストール

最初の起動で、モニターは起動スクリプトの隣にあるものを自分のフォルダーへ自動的に移します。**移動するだけで、削除も上書きもしません**。新しい場所にすでにあるファイルはそのまま残り、ドクターが知らせます。最初の移動の前に設定ファイルが `config/config_backups/pre_layout_<刻印>/` にコピーされ、すべての移動が `data/.layout_moves.json` に記録されます。

- 先に確認:`python -m github_actions_monitor.util.rootmigrate`(予行)、すぐ実行するには `--apply`。
- 元に戻す:`python -m github_actions_monitor.util.rootmigrate --undo`。
- 自動で移したくない場合:`MONITOR_NO_AUTO_MIGRATION=1`。
- `python bin/actions_monitor.py --doctor` の `layout` チェックが、起動スクリプトの隣に残っているものを一覧します。
- 起動スクリプトの隣にあった古いエントリーポイント(`read_report.py`、`monitor_cli.py` など)は `bin/` に移りました。`python tools/migrate_layout.py` が古いコピーを片付けます。古いパスで AI ツールに登録したゲートスクリプトは登録し直してください:`python bin/monitor_cli.py ai-hook install`。

## フォルダーを移す

コードを変更せずに、各フォルダーを別の場所に置けます。環境変数 `MONITOR_CONFIG_DIR`、`MONITOR_DATA_DIR`、`MONITOR_LOGS_DIR`、`MONITOR_AI_DIR`、またはファイル `config/paths.json`(`{"data": "...", "logs": "...", "ai": "..."}`、相対パスは製品フォルダーが基準)を使います。`MONITOR_DATA_DIR` だけを指定すると、`logs/` と `ai/` はその中に置かれます。Docker イメージと systemd ユニットでは、まさにこれが設定されています。`/config` と `/data` が 2 つのボリュームです。

## モニターと対話する AI のために

ローカルでも外部でも、AI は固定のパスに依存してはいけません。

- `ai/INDEX.json` は、フォルダー内の各ファイルの目的、形式、書き込み元、更新のタイミング、モニターの各フォルダーの実際のパス、動作中のモニターのエンドポイントを一覧します。起動のたびに書き直されます。
- `ai/README.md` は、このフォルダーを初めて見る AI に向けた説明です(データであって指示ではないこと、ブリーフの読み方、使えるツール)。
- `GET /api/paths` は、使用中のフォルダー、主なファイル、古い場所にまだ残っているものを返します。複数アカウントのスーパーバイザーも応答します。
- ゲートスクリプト、MCP サーバー、コマンドラインは同じ場所を読みます。`ALERTS_BRIEF.md` を固定パスで読むフックは、先に `ai/INDEX.json` を読むように変更してください。
