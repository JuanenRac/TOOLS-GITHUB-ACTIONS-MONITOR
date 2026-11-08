<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ANALYTICS.md) | [🇪🇸 Español](ANALYTICS_spa.md) | [🇫🇷 Français](ANALYTICS_fra.md) | [🇮🇹 Italiano](ANALYTICS_ita.md) | [🇩🇪 Deutsch](ANALYTICS_deu.md) | [🇨🇳 简体中文](ANALYTICS_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](ANALYTICS_por.md)

# 分析、条件付き読み取り、接続の喪失

モニターがすでに読んでいる実行から何を学ぶか、割り当てをどう節約し、ネットワーク断をどう乗り切るか。すべてローカルで、どこにも送信されません。

## 所要時間・待ち時間・ステップ

- 各ワークフローの成功した実行の所要時間、ジョブが開始前に待った時間(作成から開始まで)、ワークフローの各ステップの `p50` と `p95`。`analytics.min_samples` 件のサンプルが集まると数値を表示します。
- ジョブとステップの時間には完了した実行のジョブが必要です。1 周期に最大 `analytics.jobs_per_cycle` 件、各実行は 1 回だけ読みます(0 なら読みません)。受信 Webhook なら無料で得られます。
- `ghamon_workflow_duration_seconds`、`ghamon_job_queue_seconds`、`ghamon_step_duration_seconds`(ラベル `quantile` 0.5 / 0.95。`per_repo` が必要)と Grafana の JSON ソース(`durations`、`queue`)に出力されます。`slower` は p50 が通常の `analytics.slow_factor` 倍に達したワークフローを列挙します。


## 不安定なワークフロー(flaky)

同じコミットで失敗した後に成功した(または再試行が必要だった)ワークフローは不安定とラベル付けされます:`ghamon_workflow_flaky_rate`。ラベルにすぎず、何が赤かは変わりません。


## 条件付き読み取り(ETag)

- 実行リストの各読み取りは `If-None-Match` を送ります。変更がなければ GitHub は `304 Not Modified` を返し、割り当てを消費しません。ヘッダーに節約した読み取りの数が表示され、`ghamon_etag_saved_total` が数えます。`cache.etag.enabled` と `cache.etag.ttl_hours` は設定タブにあります。
- キャッシュはローカルファイル `etag_cache.json`(公開されません)。壊れたファイルは単に空のキャッシュになります。


## 接続が失われたとき

1 周期のすべての読み取りが接続の問題(ログインや割り当てではなく)で失敗すると、ページは最後の状態を保ち、赤いバナー「HH:MM から接続なし」を表示します。例外は発生せず、モニターは自動で再開し、`offline` と `online` のイベントを 1 回ずつ書きます(通知可能)。その間 `ghamon_offline` は 1 です。
