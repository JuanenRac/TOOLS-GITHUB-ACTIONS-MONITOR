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

スイッチがオフのパスへのリクエストには `404` が返ります。同じドキュメントをダッシュボードに渡す従来の方法である `ci_red.json` と `read_report.py --export-status` は変更されません。これは契約です。

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
