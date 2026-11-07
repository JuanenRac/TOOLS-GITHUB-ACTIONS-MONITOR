<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SETTINGS.md) | [🇪🇸 Español](SETTINGS_spa.md) | [🇫🇷 Français](SETTINGS_fra.md) | [🇮🇹 Italiano](SETTINGS_ita.md) | [🇩🇪 Deutsch](SETTINGS_deu.md) | [🇨🇳 简体中文](SETTINGS_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](SETTINGS_por.md)

# 設定タブ

設定タブ（ヘッダーまたはタブバーの歯車アイコン）では、`actions_monitor.json` の値をページ上から変更できるため、ファイルを手作業で編集する必要はありません。
このタブはページの 8 つの言語で書かれており、ほかの部分と同じ外観になっています。

## 変更できるもの

`settings_api.py` の一覧（スキーマ）にあるキーのみです。各キーには型と範囲があり、変更にモニターの**再起動**が必要か（ループは設定を一度しか読み込みません）、**すぐに反映される**かがページに表示されます。

| グループ | キー |
|---|---|
| このブラウザー | ページの言語、テーマ（自動 / ライト / ダーク）、「今」タブの高密度表示。これらはファイルではなくブラウザーに保存されます。 |
| 全般 | `language`（ツールの既定言語）、`github_owner`、`mode`（`full` / `lite`）、`ecosystems`、`exclude`、`report_history_days` |
| 更新と上限 | `refresh_seconds`、`cold_refresh_seconds`、`issues_refresh_seconds`、`discover_refresh_seconds`、`stuck_minutes`、`runs_per_repo`、`cold_runs_per_repo`、`hot_hours`、`max_workers`、`min_rate_remaining` |
| センチネル | `sentinel.enabled`、各サイクル、API の予算、候補・古くなったプルリクエスト・保留中の署名のしきい値、`sentinel.require_verified_signature`、A2 の照会 |
| サーフェスチェック（A10） | `sentinel.surface.enabled`、そのサイクル、1 サイクルあたりのリポジトリ数、許容係数、予算に占める割合 |
| 準備状況（A11） | `sentinel.readiness.enabled`、`min_coverage`、`warn_below` |
| フォルダーとファイル | `workspace_root`、`signed_dir`、`audit_dir`、`ecosystems_file`、`targets_file`、`profiles_file`、`tools_dir`、`sentinel.ci_red_file`、`sentinel.ci_red_audit_copy` |
| 他のツール向けの出力 | `outputs.prometheus.enabled`、`outputs.prometheus.per_repo`、`outputs.json.enabled`、`outputs.dashboard.enabled`（OUTPUTS_jpn.md を参照） |
| センチネル用の外部 AI | `ai.provider`（`none` / `ollama` / `openai-compatible`）、`ai.model`、`ai.ollama_url`（このコンピューターのみ）、`ai.base_url`（https）、`ai.api_key_env`（キーを保持する環境変数の名前）、`ai.daily_limit`。キー自体は保存されません。既定ではオフで、外部サービスにはリポジトリのデータが送られます。 |

## ページから変更も閲覧もできないもの

トークン、シークレット、署名キー、Webhook のシークレット、センチネルが実行できるコマンド（`sentinel.notify_command`）、AI の API キー（設定できるのは環境変数の名前だけです）、ほかのツールのキーは、**スキーマに含まれていません**。そのためページはこれらを表示も書き込みもせず、いずれかを指定したリクエストは拒否されます。ファイルのそのほかのキーは、まったく元のまま保持されます。

## 保存の仕組み

1. 変更された値だけが、`Content-Type: application/json` で本文が最大 16 KB の `POST /api/settings` として送信されます。
2. すべての値は型と範囲に照らして検証されます。無効な値が 1 つでもあればリクエスト全体が拒否され、何も書き込まれません。パスは制御文字を含まないテキストでなければならず、
   ネットワーク（UNC）パスや `D:` ドライブ上のパスは認められません。
3. 変更前のファイルは `config_backups/actions_monitor-<time>.json` にコピーされます（直近 10 件のコピーが保持されます）。
4. 新しいファイルは一時ファイルに書き込まれてから古いファイルの上に移動される（アトミック）ため、クラッシュしても中途半端なファイルが残ることはありません。有効な JSON ではないファイルは、ページから上書きされることはありません。
5. 再起動が必要な保存済みの値がページに表示され、再起動するまでバナーが表示され続けます。

## リクエストできる者

同じマシンのページだけです。サーバーは `127.0.0.1` で待ち受け、`Host` または `Origin` が自身のアドレスでないリクエストを拒否します（ほかのすべてのエンドポイントと同じチェックです）。
リクエストは JSON でなければならないため、別サイトのフォームからは到達できません。

## 1.5.0 より前

ツールの言語はシステムの言語で決まっていましたが、現在は英語で起動し、言語は設定項目になっています（ここでは `language`、`MONITOR_LANG`、または `--lang`）。
`parte_history_days` は `report_history_days` になりました（古い名前も引き続き読み込まれます）。
