<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# 1.5.0 より前のバージョンからの更新

[English](MIGRATING.md) · [Español](MIGRATING_spa.md) · [Français](MIGRATING_fra.md) · [Italiano](MIGRATING_ita.md) · [Deutsch](MIGRATING_deu.md) · [简体中文](MIGRATING_zho.md) · **日本語** · [Português](MIGRATING_por.md)

バージョン 1.5.0 で、ファイル、フォルダー、スクリプト、1つの設定に英語の名前が付きました。失われるものはありません。モニターは古い名前も引き続き読み込むので、先に更新して、あとで整理できます。

## 手順

1. モニターを停止し、新しいバージョンを古いフォルダーの上に展開します（`actions_monitor.json` は残します）。
2. 何が変わるかを確認します：`python bin/migrate_state.py`（ドライラン。何も変更しません）。
3. 実行します：`python bin/migrate_state.py --apply` は古いファイルを新しい名前にコピーし、古いファイルは残します。`--move` を付けると代わりに名前を変更します。既にあるものは上書きされず、設定 `parte_history_days` は `actions_monitor.json` のコピーを保存した後に `report_history_days` になります。
4. モニターは `MONITOR_GITHUB_ACTIONS`（これまでと同じランチャー）で起動し、バッチツールには `BATCH_GITHUB_ACTIONS` を使います。
5. 残っている古いランチャーを削除します：`LOTE_GITHUB_ACTIONS.bat`、`.sh`、`.command`。

## 旧名と新名

| 1.5.0 より前 | 1.5.0 以降 |
|---|---|
| `leer_parte.py` | `bin/read_report.py` |
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
3. 任意: `python bin/actions_monitor.py --doctor` でインストールを確認できます。

変わる点: **lite 版**が加わりました（`MONITOR_LITE_GITHUB_ACTIONS`、ポート 8766、専用の `actions_monitor_lite.json`、センチネルなし）。**main で赤**は1つの規則になりました（各ワークフローの既定ブランチで最後に完了した run。取り消し・スキップ・neutral・stale は判定に影響しません）。そのため数値が 1.5.x と異なる場合があります。設定ページは先頭に**基本**タブがあります。通知、分析、リンター、webhook イベント、AI アシスタントはありますが、有効にするまで**オフ**です。GitHub への書き込みには引き続き明示的な確認が必要です。Rich と Textual は任意で、Python 3.11 以上が必要です。

# 1.6.4 から 1.6.5 へ

変換が必要なものはありません。意図的に動作が変わった点は次のとおりです（証明されていないものを安全とみなさなくなったためです）。

- **バッチ**: `finalize` は、確認したコミットでビルドされたことをバッチが「記録している」実行だけを署名に提示します。古いバージョンのバッチは `needs_review` になります。それでも使う場合は `finalize --accept-legacy`：GitHub から実行を再取得し、コミットが記録と一致したときだけ受け入れ、署名のたびに LEGACY の入力を求めます。またはビルドをやり直してください。
- **CI が緑**とは、必須のワークフローファイルがそのコミットで成功し（既定は `ci.yml`、`dispatch.required_ci`、`dispatch.required_ci_repos`、`dispatch.required_ci_profiles`）、失敗や承認待ちがなく、実行一覧が完全であることです。CI ファイルの名前が異なるリポジトリは `dispatch.required_ci` に名前を書いてください。
- **`git fetch` の失敗**（ネットワークなし、認証情報なし）は、そのリポジトリの起動を止めます。
- **targets.json**: `tool` はツールフォルダー内の単純なファイル名（フォルダーや `..` なし）、`extra` は `-f key=value` の組のみ（`dry_run` と `ref` は不可）、`finalize_flags` は `--bench` のような長いオプションのみ。条件を満たさないカタログは理由付きで拒否されます。
- **通知**: `max_per_hour` はイベントではなくメッセージ（チャンネルごとに 1 つ）を数えます。
- **Webhook**: すべてのリクエストに `X-GitHub-Delivery` が必要（GitHub は常に送ります）。重複した ID は無視され、`full_name` の所有者は監視中のアカウントでなければなりません。
- **act**: 別のフォルダーへのリンクであるクローンは拒否されます（`act.allow_symlinks` で許可）。
- **ネットワークモード**: IPv4 アドレスのみ。表示されるアドレスはサーバーが待ち受けているものです。`GET /api/sentinel/parte.txt?save=1` はもう書き込みません（コピーは一回限りトークン付きの POST です）。
- 保存した GitHub トークンはプロセスの環境に置かれなくなりました。受け取るのは `gh` だけです。
- zip をクリーンなフォルダーに展開するテストは通常のテスト一式から外れ、`make_release.py` が独立した段階として実行します。

# 1.6.5 から 1.6.6 へ

変換が必要なものはありません。意図的に動作が変わる点:

- **HTTPS のネットワークモード**: ページからの変更が動作するようになりました。`Origin` にはセッションのスキームとモニターのポートが必要です。プロキシの背後ではアドレスにモニターのポートを残してください。そうしないと検査で拒否されます。
- **ネットワークモード**: スキーマが `secure` とするすべての設定は、そのコンピューター自身からのみ変更できます(以前は `listen.`、`github_token.`、`act.`、`github_actions.` のみ)。別のコンピューターから `webhook.*` や `notify.*` などを変更していたスクリプトは 403 `local_only` を受け取ります。
- **act**: Stop の後は実行がすぐに解放され、直後の開始は `busy` を返しません。
- `data/` に新しいファイル `degraded.json` と `degraded_lite.json`(握りつぶした失敗のカウンター)ができます。いつでも削除できます。
- 変更履歴(ヘルプ > 変更履歴)が翻訳されました。言語ごとに `docs/CHANGELOG_<言語>.md` が1つあります。

# 1.6.6 から 1.6.7 へ

変換が必要なものはありません。意図的に動作が変わる点:

- **443 番ポートの HTTPS プロキシの背後でのネットワークモード**: 新しい設定 `listen.proxy_public_host`(既定は空。空のままなら何も変わりません)。プロキシが `Host` と `Origin` をポートなしで転送する場合は、そのプロキシの公開ホスト名を指定してください。その 1 つの名前だけが、ネットワークモードが有効でセッションが HTTPS の間に限り、そのまま受け付けられます。変更できるのはそのコンピューター自身からだけです。ポートを保持するプロキシの背後では何も変わりません。
- 変更履歴(ヘルプ > 変更履歴)は、1.6.7 と 1.6.5 について他の 7 言語に翻訳されました。それより古い項目は、翻訳済みの注記の下に引き続き英語で表示されます。

# 1.6.7 から 1.6.8 へ

変換が必要なものはなく、変わる設定もありません。

- リポジトリの新機能(パッケージには含まれません): `python tools/manual_check_live.py proxy ホスト [ポート] [接続先]` は、ポート 443 の実際の HTTPS プロキシを `listen.proxy_public_host` に照らして確認します。先に `MONITOR_ACCESS_TOKEN` を設定してください。読み取られるだけで、表示されることはありません。
- 変更履歴(ヘルプ > 変更履歴)は、1.6.8 から 1.6.3 まで他の 7 言語に翻訳されました。

# 1.6.8 から 1.7.0 へ

変換が必要なものはありません。`accounts/` フォルダーがなければ、モニターはこれまでとまったく同じように動作します。

- **複数のアカウント** は任意です。使うには `python bin/actions_monitor.py --migrate-accounts`（試験実行）を実行し、続けて `--apply` を付けてファイルを `accounts/default/` にコピーします。元のファイルは、あなたが削除するまで残ります。アカウントを追加するには `accounts/<id>/actions_monitor.json` を作ります。`ACCOUNTS.md` を参照してください。
- `accounts/` フォルダーがあると、`python bin/actions_monitor.py` はアカウントごとに 1 つのモニターを実行するスーパーバイザーを起動します。`--account <id>` は 1 つだけを実行します。lite 版にはこれらは一切ありません。
- 新機能: ページのアドレスでの `?view=` と `?chrome=0`、`GET /api/accounts`、`GET /api/live-status`、そしてすべてのアカウント向けの 1 つの `POST /api/webhook`。

# 1.7.x から新しいフォルダ構成へ

コードは `src/github_actions_monitor/` に、ページ・サンプルファイル・言語は `assets/` に、リリースと移行のスクリプトは `tools/` に置かれるようになりました。普段使うものは何も変わりません。起動スクリプト(`MONITOR_GITHUB_ACTIONS`、`MONITOR_LITE_GITHUB_ACTIONS`、`BATCH_GITHUB_ACTIONS`)は同じ場所にあり、同じアドレスとポートを開きます。このガイドのコマンド(`python bin/read_report.py`、`python bin/actions_monitor.py --doctor`、`python bin/monitor_cli.py status` など)も、同じ名前の小さな入口ファイルが製品フォルダに残るため、そのまま動きます。起動スクリプトは `src/` をパスに加えて `python -m github_actions_monitor`(完全版)と `python -m github_actions_monitor.lite`(lite 版)を実行します。

データは移動しません。`actions_monitor.json`、キャッシュ、ログ、`config_backups/`、`accounts/`、独自のカタログファイルは、起動スクリプトの隣の製品フォルダに残り、`src/` の中には決して入りません。プログラムに同梱される中立のサンプルと `quotas.json` は `assets/examples/` に移りました。起動スクリプトの隣に自分の `quotas.json` を置けば、そちらが優先されます。

## 手順

1. モニターを止め、新しいバージョンを古いフォルダの上に展開します(`actions_monitor.json` は残します)。
2. いつもどおり起動します。ほかに何もしなくても動きます。
3. 古いフラット構成の残りを片付けるには、`python tools/migrate_layout.py`(ドライラン)を実行し、続けて `python tools/migrate_layout.py --apply` を実行します。設定ファイルを `layout_backup_<日時>/config/` にコピーし、古いモジュール・古いページ・古いサンプル・古い `locales/` フォルダを `layout_backup_<日時>/old_code/` に移動します。削除も上書きもせず、データには触れません。古いファイルが残っている間は `python bin/actions_monitor.py --doctor` が知らせます。
4. 古いフラットな名前でモジュールを import していた自作スクリプト(`import read_report`)は、`src/` をパスに加えて `github_actions_monitor.<パッケージ>.<モジュール>` を import します。

| パッケージ | 内容 |
|---|---|
| `app` | サーバー、設定、動作モード、共有設定 |
| `accounts` | 複数アカウント:レジストリ、スーパーバイザー、子プロセス |
| `sentinels` | センチネル、アラートセンター、パネル |
| `security` | ローカルガード、シークレット、Webhook、確認、ネットワークガード、署名、非公開ファイル |
| `data_pipeline` | イベント、分析、条件付き読み取り、検出、クォータ、main の赤の規則 |
| `integrations` | GitHub、通知、OpenTelemetry、ミラー、ランナー、MCP、AI のフィードとフック |
| `cli` | コマンドラインツール |
| `ui` | 情報、ヘルプ文書、ターミナル表示 |
| `i18n`、`util` | 8 言語、共有の小さな補助 |

## 状態をファイルとSQLiteの間で移す(1.8.0)

更新のために移行する必要はありません。既定は引き続きファイルです。状態をSQLiteに置きたい場合は、`python tools/migrate_storage.py --from file --to sqlite` でコピーされる内容を確認でき(ドライラン)、`--apply` を付けるとコピーして検証します。元のファイルは変更も削除もされません。詳しくは [STORAGE_jpn.md](STORAGE_jpn.md) をご覧ください。

# 1.7.9 から 1.8.0 へ

変換は不要です。1つの設定は対応が必要な場合があります。

- extra_reader.file がアカウントフォルダーの外を指しているため、2つ目のアカウントは使われません。トークンファイルをアカウントフォルダー(accounts/、または MONITOR_ACCOUNTS_DIR が指すフォルダー)に移してパスを extra_reader.file に残すか、設定 > クォータで extra_reader.any_folder をオンにしてください。
