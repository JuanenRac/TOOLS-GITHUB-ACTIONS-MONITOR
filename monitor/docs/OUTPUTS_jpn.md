<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](OUTPUTS.md) | [🇪🇸 Español](OUTPUTS_spa.md) | [🇫🇷 Français](OUTPUTS_fra.md) | [🇮🇹 Italiano](OUTPUTS_ita.md) | [🇩🇪 Deutsch](OUTPUTS_deu.md) | [🇨🇳 简体中文](OUTPUTS_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](OUTPUTS_por.md)

# 他のツール向けの出力

任意の出力が 3 つあり、**すべて既定でオフ**です。設定タブ（「他のツール向けの出力」グループ）または `actions_monitor.json` でオンにします。

```json
"outputs": {"prometheus": {"enabled": false, "per_repo": true}, "json": {"enabled": false}, "dashboard": {"enabled": false}}
```

これらは同じ Web サーバーから、`127.0.0.1` のみで提供され、ほかと同じ `Host` / `Origin` のチェックが行われ、**トークンは不要**です。モニターがすでに保持している状態を読み取るため、スクレイプやダッシュボードの更新で GitHub API のクォータは消費されません。オン・オフの切り替えは即座に反映されます（再起動不要）。

| パス | 形式 | スイッチ |
|---|---|---|
| `/metrics` | Prometheus テキスト、バージョン 0.0.4 | `outputs.prometheus.enabled`（`per_repo` でリポジトリごとの系列を追加） |
| `/api/outputs/grafana.json` | Grafana の「Infinity」/ JSON データソース向けの JSON テーブル | `outputs.json.enabled` |
| `/api/outputs/dashboard.json` | ステータスダッシュボード向けの `ci_red.json` のドキュメント（スキーマ 2、CI_RED_SCHEMA_jpn.md を参照） | `outputs.dashboard.enabled` |

スイッチがオフのパスへのリクエストには `404` が返ります。同じドキュメントをダッシュボードに渡す従来の方法である `ci_red.json` と `bin/read_report.py --export-status` は変更されません。これは契約です。

## Prometheus メトリクス

名前はすべて `ghamon_` で始まります。ゲージのみです。不明な値は**省略**され、0 として書き込まれることはありません。

| メトリクス | ラベル | 意味 |
|---|---|---|
| `ghamon_info` | `version` | 常に 1 |
| `ghamon_snapshot_complete` | | センチネルのスナップショットが完全なら 1、読み込み中または縮約されている間は 0 |
| `ghamon_red_workflows`、`ghamon_red_repos` | | デフォルトブランチで最後に完了した実行が赤のワークフロー（リポジトリ） |
| `ghamon_ecosystem_red_workflows` | `ecosystem` | 上記をエコシステムごとに集計したもの |
| `ghamon_repo_red_workflows` | `repo`, `ecosystem` | リポジトリごと（`per_repo` が必要） |
| `ghamon_workflow_red_streak` | `repo`, `workflow`, `ecosystem` | 連続した赤の実行回数（`per_repo` が必要） |
| `ghamon_workflow_red_hours` | `repo`, `workflow`, `ecosystem` | 赤になってからの経過時間（`per_repo` が必要） |
| `ghamon_pending_sign`、`ghamon_pending_sign_repos`、`ghamon_pending_sign_hours_max` | | ローカルでの署名または公開を待っているビルドのうち、しきい値を超えたもの |
| `ghamon_repo_pending_sign_hours` | `repo`, `ecosystem` | リポジトリの最長の待ち時間（`per_repo` が必要） |
| `ghamon_surface_paused`、`ghamon_surface_paused_remaining`、`ghamon_surface_paused_needed` | | サーフェスチェック（A10）が GitHub のクォータを待っている間は 1。残りのクォータと必要なクォータも示す |
| `ghamon_api_rate_remaining`、`ghamon_api_rate_limit` | | GitHub API の許容量 |
| `ghamon_score`, `ghamon_score_coverage`, `ghamon_score_scored` | | アカウントのスコア（0〜100、数値があるときだけ）、データのある重みの割合、数値があるとき 1（Complete のみ。SCORE.md を参照） |
| `ghamon_sentinel_calls_last_hour`、`ghamon_sentinel_budget_per_hour` | | センチネルの API 呼び出し数とその予算 |
| `ghamon_repos_watched`、`ghamon_runs_active`、`ghamon_runs_stuck`、`ghamon_runs_failing`、`ghamon_issues_open`、`ghamon_quota_paused` | | 「今」タブのライブの数値 |

スクレイプジョブの例：

```yaml
scrape_configs:
  - job_name: github-actions-monitor
    scrape_interval: 30s
    static_configs:
      - targets: ["127.0.0.1:8765"]
```

## Grafana

`docs/grafana/monitor_dashboard.json` はインポート可能なダッシュボード（Grafana 10 以降）です。赤のワークフロー、署名待ちのビルド、残りの許容量、A10 の状態、スナップショットが完全かどうか、停滞した実行を表示するスタットパネル、エコシステム別の赤のワークフローの棒グラフ、最長の赤の連続と署名待ちのグラフ、そして Infinity データソースで `/api/outputs/grafana.json` から読み取る 2 つのテーブル（`root_selector` は `red` と `pending_sign`）で構成されています。インポート時に Grafana は Prometheus と Infinity のデータソースを尋ねます。モニターが 8765 以外を使っている場合は、2 つのテーブルの URL のポートを変更してください。Grafana は同じマシン上で動作している必要があります（出力は 127.0.0.1 でのみ応答します）。

## 類似プロジェクトから得たアイデア

GitHub Actions 向けの他のツールの仕組みを調べて、いくつかのアイデアを得ました。それらのコードや文章は一切使用していません。Prometheus メトリクスのエクスポーターからは、実行のステータスを数値とラベルで表すこと、エクスポートするラベルの選択、設定可能なポートと間隔を取り入れました。Webhook で更新される TV ダッシュボードからは、フィルター付きでリポジトリごとに 1 つのステータスを大きく表示する点を取り入れました。ターミナル監視ツールからは、リポジトリのすべてのワークフローが終了するまで一度に表示する点を取り入れました。アラートルール付きの Webhook ダッシュボードからは、通知する前にリポジトリ・ブランチ・ワークフローで絞り込む点を取り入れました。ここでは、同じアイデアが `per_repo`（系列の選択）、赤のワークフロー 1 件につき 1 行の JSON ソース、ライブの「今」タブ、そしてページ内のフィルター付きイベントファイルとして現れています。

## 最小の Grafana ボード

`docs/grafana/red_by_ecosystem.json` は 1 パネルのボードで、エコシステム別の赤のワークフローを表示します(クエリ `ghamon_ecosystem_red_workflows`、凡例 `{{ecosystem}}`)。インポートして Prometheus のデータソースを選んでください。このリポジトリのテストが、使用するメトリクスとラベルが `/metrics` で実際に配信されることを確認します。

## 信頼度別の署名キュー

キューの各行には `trust` があります。`verified`(公開鍵で署名を検証済み)、`unknown`(ここでは形式を検証できない:推測はしません)、`failed`(検証したが一致しない)。センチネルタブには署名フィルターがあり、種類ごとの件数を表示し、行に印(緑・灰・赤の縁)を付けます。コンソールからは `py -3 bin/read_report.py --export-sign-queue FILE --sign-trust failed`。

## ネットワークモードでは

`/metrics` と `dashboard.json` はリポジトリとその状態を一覧にするため、公開ページではありません。ネットワークモードがオンのときは、他のエンドポイントと同じくアクセストークンが必要です。その一覧に到達できないようにしたい場合は `outputs.prometheus.enabled` / `outputs.dashboard.enabled` をオフにしてください。

## タブのレポートの保存と印刷

ページ上部のバー(すべてのタブにあります)は、開いているタブの「ひとつの」レポートを作り、同じデータから 4 通りの方法で出力します。そのため形式ごとに内容が食い違うことはありません。

- **レポートを保存** は 3 つのチェックボックスのあるウィンドウを開きます。**TXT**(オン)、**PDF**(オン)、**JSON**(オフ。他のツール向けのレポートのデータ)。確定すると、形式ごとに 1 回ずつブラウザーの **名前を付けて保存** ウィンドウが、提案名 `monitor-<タブ>-<日付>.<拡張子>` と適切なファイルの種類で開きます(ブラウザーはウィンドウごとにクリックを求めるため、ボタンは次の形式へ進みます)。このウィンドウがないブラウザーではファイルをダウンロードし、保存先をページが知らせます。
- **PDF**: モニター自身がライブラリなし・標準フォント Helvetica で PDF を書き出します。対象は英語、スペイン語、ドイツ語、フランス語、イタリア語、ポルトガル語です(`GET /api/report/tab.pdf`、このコンピューターからのみ。使用のたびに操作ログに 1 行残ります)。日本語と中国語にはこの方法の PDF が持たないフォントが必要なため、これらの言語、またはウィンドウで「ブラウザー」を選んだ場合は、ブラウザーの印刷ウィンドウで PDF を作成します。そこで **PDF として保存** を選んでください。ページがそのことを表示し、文字化けした PDF は決して書き出しません。
- **印刷** は、メニューやバーのない同じレポート(タブ名のタイトル、日時、モニターのバージョン、主な数値、アラート、タブの表)を表示し、印刷ウィンドウを開きます。
- レポートは `GET /api/report/tab?tab=now&lang=ja`(`&fmt=json`、`&fmt=txt`、`&fmt=options`)で提供され、2 つのエディションで同じです。

設定(設定 > 他のツール向け出力 > 「タブのレポートの保存と印刷」): `report_export.txt`、`report_export.pdf`、`report_export.json`(最初にオンになるチェックボックス。TXT と PDF はオン、JSON はオフ)、`report_export.name`(提案名。既定は `monitor-{tab}-{date}`)、`report_export.paper`(`a4` または `letter`。既定は `a4`)、`report_export.pdf_path`(`auto`、`own`、`browser`。既定は `auto`)。

## サーバーのメトリクス：サイクル、読み取りキュー、課金、ランナー、ヒストグラム

上のゲージに加えて、`/metrics` は次を書き出します（不明な値は省略されます）。

| メトリクス | ラベル | 意味 |
|---|---|---|
| `ghamon_ticks_total`、`ghamon_tick_failures_total` | | 完了した更新サイクルと、エラーで終わったサイクル（カウンター） |
| `ghamon_tick_last_seconds`、`ghamon_tick_phase_seconds`、`ghamon_tick_seconds` | `phase` | 直近サイクルと各フェーズの所要時間、および全サイクルのヒストグラム |
| `ghamon_tick_last_ok_timestamp_seconds`、`ghamon_tick_reads_last` | | 直近のサイクルが正常終了した時刻と、読み取ったリポジトリ数 |
| `ghamon_read_retries_total` | | 一時的な理由で失敗し再試行された読み取り（カウンター） |
| `ghamon_repos_circuit_open`、`ghamon_repos_read_failing`、`ghamon_repos_read_fail_streak_max` | | 連続して失敗したため次の読み取りまで待つリポジトリ（サーキット）、直近の読み取りが失敗したリポジトリ、最長の連続失敗数 |
| `ghamon_read_queue_depth`、`ghamon_read_queue_allowed`、`ghamon_read_queue_oldest_wait_cycles`、`ghamon_read_queue_deferred_total`、`ghamon_read_queue_shed_cycles_total` | | バックプレッシャー付きの読み取りキュー（`backpressure.enabled` がオンのときのみ） |
| `ghamon_billing_minutes_total`、`ghamon_billing_minutes_included`、`ghamon_billing_minutes_paid`、`ghamon_billing_sku_minutes`、`ghamon_billing_usd` | `sku`、`product` | 当月の課金レポート（`quota.billing_api` がオンのときのみ。スクレイプは GitHub を読まず、サイクルが保持する最新のレポートを書き出します） |
| `ghamon_runners` | `state` | アイドル、実行中、オフラインのセルフホストランナー（`runners.enabled`） |
| `ghamon_runner_up`、`ghamon_runner_busy` | `runner` | ランナーごと（`outputs.prometheus.per_runner`） |
| `ghamon_runner_kind_jobs_waiting`、`ghamon_runner_kind_oldest_wait_seconds` | `kind` | ランナー種別ごとの未開始ジョブと最長待ち時間（`runners.model.enabled`） |

`outputs.prometheus.histograms` をオンにし（Webhook がジョブイベントを受け取っている場合）、署名付きの `workflow_job` と `workflow_run` イベントからメモリ上で作る**ヒストグラム**も書き出します。

| メトリクス | ラベル | 意味 |
|---|---|---|
| `ghamon_job_wait_seconds` | `runner_group`、`label` | ジョブのキュー待ち時間（**ジョブごとに 1 回**） |
| `ghamon_job_run_seconds` | `runner_group`、`label`、`conclusion` | 完了したジョブの所要時間 |
| `ghamon_workflow_run_seconds` | `conclusion` | 完了した実行の所要時間 |
| `ghamon_jobs_total` | `label`、`conclusion` | 完了したジョブ数（カウンター） |
| `ghamon_runner_jobs_waiting`、`ghamon_runner_oldest_wait_seconds` | `label` | 現在のランナー需要：キューにあり未開始のジョブと最長待ち時間 |

`outputs.prometheus.histogram_max_series`（既定 200）は各ヒストグラムの系列数を制限し、超えた分はラベル値 `other` にまとめられます。`outputs.prometheus.per_runner` をオンにすると、セルフホストランナーごとに `ghamon_runner_jobs_total`、`ghamon_runner_jobs_failed_total`、`ghamon_runner_busy_seconds_total` が追加されます（`GET /api/runners/model` の `per_runner` にも出ます）。

## オブザーバビリティパック：アラートルール、Alertmanager、OnCall、n8n

`docs/grafana/` には 2 つのダッシュボードのほかに、コピーして調整するパックがあります。

- `ghamon_alert_rules.yml`：Prometheus（vmalert も可）用のルールと PromQL。モニターが応答しない、赤いワークフローと連続失敗、利用枠や課金が上限に近い、サイクルが遅い・止まっている、サーキット中のリポジトリ、読み取りの待ちが長すぎる、ランナーを待つジョブ（`histogram_quantile(0.95, sum by (le, label) (rate(ghamon_job_wait_seconds_bucket[30m])))`）、オフラインのランナー、空きランナーのない需要。
- `alertmanager.example.yml`：重大度別に 3 つの受信先（既定の Webhook、Grafana OnCall、n8n）へ振り分けるルート。すべてのアドレスは `https://example.invalid/...` で、自分のものを書くまで何も送信されません。ファイルに秘密情報を書かないでください。
- `n8n_ghamon_alerts.json`：Alertmanager の Webhook を受け取りアラートごとに 1 件のメッセージを作る n8n のワークフロー。最後のノードは、チャット、メール、チケットのノードに置き換えるまで何もしません。
- `prometheus.example.yml` と `docker-compose.observability.yml` は、パックを試すためにモニターのコンピューター上で Prometheus、Alertmanager、Grafana を起動します（コンテナーはホストのネットワークを共有し、ポートは `127.0.0.1` にあり、Grafana のパスワードはファイルではなくシェルから渡します）。
## モニターが接続する先と、SIEM へのイベント

- **ネットワーク接続先の一覧**：`monitor_cli.py doctor --egress`（`--json` も可）は、現在の設定が接続しうるホストごとに、用途、接続先になる設定、ブロックされたときに失敗することを一覧します：`api.github.com`、`github.com` と `objects.githubusercontent.com`（更新）、`raw.githubusercontent.com`（`lint.anonymous_public`）、ntfy、Telegram、チャットの Webhook、選んだ AI プロバイダー、OTLP コレクター、SIEM の送信先。`airgapped` では何も使われません。テストが、この一覧をコードに現れるホストと一致させます。
- **SIEM**（オフ）：ファイルの `siem.sinks` に送信先を並べ、使うものには `enabled: true` を付けます：`elasticsearch`（bulk）、`splunk_hec`、`loki`、`sentinel`（Log Analytics、共有キーで署名）、`bigquery`（`insertAll`）、`http`（JSON 行）。トークンやキーは `token_env` が示す環境変数から読み、ファイルからは読みません。各送信先は `from_minutes`（5）、`levels`、`repos_filter` で絞り込みます。イベントのフィールドは固定（トークンやログ本文は含みません）。プライベートアドレスの受信先は `allow_private` がない限り拒否されます。受信先が停止している間、イベントは `siem.queue_max`（500）のキューで待ち、古いものから破棄されます。オフラインモードでは何も送られません。
