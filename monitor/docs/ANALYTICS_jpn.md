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

- 実行リストの各読み取りは `If-None-Match` を送ります。変更がなければ GitHub は `304 Not Modified` を返し、割り当てを消費しません。ヘッダーに節約した読み取りの数が表示され、`ghamon_etag_saved_total` が数えます。`cache.etag.enabled` と `cache.etag.ttl_hours` は設定タブにあります。 各エントリはそれを読んだ認証情報に属します(キーにはトークンの短いフィンガープリントが含まれ、トークン自体は含まれません)。そのため `304` が別の ID の内容を返すことはありません。まだ動いている状態は常に全件読みます:実行のジョブ、単一の実行、チェックスイートとチェックラン(`cache.etag.skip_stateful`)、そして前回の答えに待機中または実行中の実行があった実行一覧(`cache.etag.revalidate_active`)。拒否(レート制限ではない 404 または 403)は `cache.negative_ttl_s` 秒間記憶されます。`/metrics` は ETag のない答え、意図して全件読んだ回数、繰り返さなかった拒否も数え、AI ツール向けブリーフにはシグナル quota.etag があります。
- GitHub がモニターの知らない状態や結論、または使える番号のない実行を送ってきたとき、AI ツール向けブリーフに schema.drift が出ます。未知の値は届いたまま表示され、赤や緑として数えられることはありません。
- キャッシュはローカルファイル `etag_cache.json`(公開されません)。壊れたファイルは単に空のキャッシュになります。


## 接続が失われたとき

1 周期のすべての読み取りが接続の問題(ログインや割り当てではなく)で失敗すると、ページは最後の状態を保ち、赤いバナー「HH:MM から接続なし」を表示します。例外は発生せず、モニターは自動で再開し、`offline` と `online` のイベントを 1 回ずつ書きます(通知可能)。その間 `ghamon_offline` は 1 です。

## 履歴を保持する期間

分析ブロックの `keep_days` に加えて、保持の処理が `retention.analytics_days`(既定は180)より古い履歴の日を削除します。サンプル自体の数は `max_samples` で制限されます。詳しくは [STORAGE_jpn.md](STORAGE_jpn.md) をご覧ください。


## 節約できた時間(推定)

既定ではオフです(`productivity.enabled`)。オンにすると、このセクションに、モニターが毎週何分節約するかが作業ごとに表示されます。式は [PRODUCTIVITY_jpn.md](PRODUCTIVITY_jpn.md) のとおりで、週あたりの回数 x モニターなしの 1 回あたりの分数 x その作業の節約率です。

- 数値化するのは 2 つの作業です。**監視**(Actions のタブを手で見て何が赤いかを判断する)は、週あたりの回数と分数をあなたのメモから取ります(`productivity.watch_times_per_week`、`productivity.watch_minutes_before`)。**原因調査**(失敗した実行の原因を見つける)は、`productivity.window_days` の間にモニターが把握している失敗した実行を数え、分数をあなたのメモから取ります(`productivity.triage_minutes_before`)。
- モニターは、導入前にあなたが何をしていたかを知ることができません。これらのメモがない作業は **データなし** と表示し、数値を作り出すことはありません。すべての作業にメモがない間は、合計も「データなし」です。
- モニターありの分数も書いた場合(`productivity.watch_minutes_after`、`productivity.triage_minutes_after`)、節約はあなたのメモから 1 - 後 / 前 として測定します。書いていない場合は `productivity.saving_percent`(既定 90)の割合を使い、表には **仮定(未測定)** と表示されます。
- `productivity.team_hours_per_week` を書くと、節約した分が労働時間のどれだけに当たるかも推定に表示されます。
- 失敗の修正にかかる時間はモニターの有無で変わらないため、数えません。数えるのはモニターが保持している失敗した実行だけで、実行一覧が非常に長いと、表示より多くの失敗がある場合があります。
- ローカルで読み取り専用です。GitHub への呼び出しはなく、何もコンピューターの外に出ません。`/api/analytics`(`time_saved`)、A12 パネルの要約、AI ツール向けの概要タブのブリーフにあります。
