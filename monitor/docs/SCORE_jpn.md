<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCORE.md) | [🇪🇸 Español](SCORE_spa.md) | [🇫🇷 Français](SCORE_fra.md) | [🇮🇹 Italiano](SCORE_ita.md) | [🇩🇪 Deutsch](SCORE_deu.md) | [🇨🇳 简体中文](SCORE_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](SCORE_por.md)

# アカウントのスコア

各アカウントについて、0〜100 の数値、A〜E の文字評価、傾向を示します。モニターがすでに把握している情報（完了した実行と、コラボレーションの番人のアラート）だけから作られます。Complete エディションにあり、Lite にはスコアがありません。

## 何でできているか

4 つの要素の加重和で、各要素は 0〜100 です。要素は **良好** の限度で 100、**不良** の限度で 0 となり、その間は直線的に変わります。重みと限度は設定です。

| 要素 | 重み | 測るもの | 良好 | 不良 |
|---|---|---|---|---|
| 信頼性 | 40 | 完了した実行のうち成功した割合（キャンセルとスキップは数えません） | 98 % | 50 % |
| 速度 | 20 | 成功した実行の所要時間の95パーセンタイル | 10 分 | 60 分 |
| 復旧 | 20 | ワークフローの最初の失敗から次の成功までの時間の中央値 | 30 分 | 24 時間 |
| コラボレーション | 20 | コラボレーションの番人のアラートが解消するまで開いている時間の中央値 | 2 日 | 14 日 |

文字評価は 90 以上が A、80 以上が B、70 以上が C、55 以上が D、それ未満が E です。傾向は、直前の期間とスコアを比べて、上昇、下降、横ばいで示します（`score.trend_flat` 点より小さい変化は横ばいです）。

## 数値が出ないとき

スコアは、裏付けのない数値を決して表示しません。回答には常に `state`、`coverage`、`data_quality` が付きます。

- **calibrating**（較正中）：アカウントを監視した時間が `score.calibrating_hours`（既定は 24）に満たない場合。数値も文字評価もありません。
- **insufficient_data**（データ不足）：期間内に完了した実行が `score.min_runs`（既定は 20）より少ない場合、またはデータのある要素の重みが合計の `score.min_coverage`（既定は半分）に満たない場合。数値はありません。
- **scored**（採点済み）：数値、文字評価、傾向があります。データのない要素は除かれ、残りが再スケールされます。これにより `coverage` が下がります（たとえばコラボレーションの番人がオフなら 0.8）。0 としても 100 としても数えません。

セキュリティはまだ要素ではありません。それまでは、すべての回答が `complete: false` と言い、`missing_parts` に `security` を挙げるため、85 点が「すべて問題なし」と読まれることはありません。

## 期間

期間とは、スコアが見る実行の日数のことです。`score.window_days`（既定は 7）で、ユーザーがアカウントごとに選びます。その直前の同じ長さの期間が傾向を与えます。モニターは見た完了済みの実行の小さな台帳を持っているため、期間はページが表示する最新の実行の一覧より長くできます。スナップショットは 1 時間ごとに保存され、分析履歴と同じ期間（`retention.analytics_days`）保持されます。

## リポジトリ別とアカウント別

各アカウントに独自のスコアがあります。詳細ではリポジトリ別に内訳を示します（CI の要素のみ、悪いものが先）。インストール全体の単一の数値はありません。

## API

`GET /api/score` はアカウントの最新のスナップショットを返します：`state`、`score`、`letter`、`trend`、`parts`、`coverage`、`data_quality`、`complete`、`missing_parts`、`repos`、`age_seconds`、`stale`（スナップショットが 3 時間より古いと真）。`GET /api/score/history` は時間に沿った点を古い順に返します（`?hours=` は現在からさかのぼる時間で最大 90 日、`?limit=` は最大 2000）。ない数値は `null` で、0 ではありません。チームモードでは、そのアカウントを見られる人はスコアを読めます。重みと限度は設定で、変更できるのは管理者だけです。

## 設定

設定ページの「番人」サブタブにある「アカウントのスコア」「スコアの重み」「スコアの文字評価」の各ブロック：`score.enabled`、`score.window_days`、`score.calibrating_hours`、`score.min_runs`、`score.min_coverage`、`score.trend_flat`、`score.weights.reliability`、`score.weights.speed`、`score.weights.recovery`、`score.weights.collaboration`、`score.grades.A` から `score.grades.D`、`score.alert.enabled`、`score.alert.drop_points`、`score.alert.notify_external`（既定はオフ）。各要素の良好と不良の限度はファイルの `score.limits` から読み込まれます（サンプルファイルを参照）。ページでは編集しません。
