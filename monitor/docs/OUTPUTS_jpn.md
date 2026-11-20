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
