<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPARE.md) | [🇪🇸 Español](COMPARE_spa.md) | [🇫🇷 Français](COMPARE_fra.md) | [🇮🇹 Italiano](COMPARE_ita.md) | [🇩🇪 Deutsch](COMPARE_deu.md) | [🇨🇳 简体中文](COMPARE_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](COMPARE_por.md)

# 期間の比較

今週は先週と比べてどうだったか。比較は、モニターがすでに保持しているデータ（完了した実行とアラートの台帳、およびスコアの1時間ごとのスナップショット）でそれに答えます。GitHub からは何も読み込まず、何も書き込まず、AI も不要で、何も作り上げません。Complete エディションにのみ存在し、`compare.enabled` をオンにするまで**オフ**です。

## 2つの期間

- **期間**：直近7日間（または30日、90日までの任意の日数）、あるいは `from` と `to` による正確な範囲。
- **比較先**：`previous`（直前の同じ長さの期間。既定）、`year_ago`（1年前の同じ日付）、`custom`（`base_from` と `base_to`）。
- **曜日**：`all`、`workdays`、`weekend`。このフィルターはすべての数値に適用されます。ある時刻の曜日は `display.timezone` のタイムゾーンでの曜日です。平日は `compare.workdays`（月曜 = 1 から日曜 = 7、既定は月曜から金曜）。祝日は考慮されず、祝日はその日にあたる曜日として数えます。

平日と週末を混ぜると見えなくなるものがあります（土曜日にだけ起きる失敗は、混ざったデータの1週間ではほとんど目立ちません）。そのためにこのフィルターがあります。

## 数値

| 数値 | 計算方法 | 良い方向 |
|---|---|---|
| `red_rate` | 期間内に開始した実行のうち、失敗 /（成功 + 失敗） | 低いほど良い |
| `duration_p50` | 成功した実行の所要秒数の中央値 | 低いほど良い |
| `resolution` | 期間内に解決された共同作業センチネルのアラートについて、発生から解決までの時間の中央値 | 低いほど良い |
| `score_mean` | 数値があった1時間ごとのスナップショットの平均スコア | 高いほど良い |
| `score_coverage` | データがあったスコアの割合の平均 | 高いほど良い |

各数値には `now`、`base`、`delta`、`direction`（`better`、`worse`、`same`）、`state` が付きます。キャンセル、スキップ、未完了の実行はどちらにも数えません。

## 数値がないとき

比較は、裏付けられない数値を決して表示しません。欠けている数値は `null` であり、0 や 100 にはなりません。

- `insufficient_data`：2つの期間のどちらかで、完了した実行が `compare.min_runs_per_window` より少ない、解決済みアラートが `compare.min_resolved` より少ない、またはスナップショットが `compare.min_snapshots` より少ない場合。どの期間か、なぜかは応答（`missing`）に示されます。
- `baseline_unavailable`：比較先の期間が信頼できません。理由は `history_too_short`（モニターの監視が `compare.min_days_of_history` 日未満）、`before_history`（その期間が保存データより古い）、`no_history` のいずれかです。現在の期間の数値は引き続き表示されます。
- `calibrating`：モニターがまだ `score.calibrating_hours` 時間監視していません。何も比較しません。
- `off`：`compare.enabled` がオフです。

`data_quality` には各期間で数えた実行数と、台帳が古い実行を捨てざるを得なかったときの `truncated` が入ります。`coverage` は比較できた数値の割合です。

## 何が変わったか

数値に加えて、悪化または改善したリポジトリ（失敗した実行の割合の変化。両方の期間に少なくとも `compare.min_repo_runs` 回の実行があるリポジトリのみ）、失敗し始めたワークフローと失敗しなくなったワークフロー、期間内に発生して期間の終了時点でも未解決のアラート数を示します。各一覧は最大 `compare.top_changes` 行で、変化の大きさ、次に名前の順に並びます。台帳は共同作業センチネルのアラートのリポジトリを保持しないため、アラートは件数として表示され、名前では表示されません。

## どこまで遡れるか

比較はスコアの台帳を読みます。`compare.enabled` がオンの間、台帳はスコアの2つの期間ではなく、`compare.default_window_days`（少なくとも15日）の2期間分を保持します。モニター自身より古くなることはないため、新しいインストールでは60日分の履歴がたまるまで、30日と30日の比較はできません。

## API

`GET /api/compare?window=7&days=workdays&baseline=previous`（`from`、`to`、`base_from`、`base_to` も使えます）。`state`、`windows`、`metrics`、`changes`、`alerts`、`coverage`、`data_quality` を返します。`format=ndjson` または `format=csv` で数値ごとに1行が得られます。意味のないリクエストは、安定した `code` 付きの 400 になります：`bad_range`（from が to より後、90日を超える、未来）、`bad_window`、`bad_days`、`bad_baseline`、`bad_format`。閲覧者も読み取れます。処理しているプロセスのアカウントだけを返し、他のアカウントは返しません。読み取り API v1 がオンなら 接頭辞 `/api/v1/` の下でも提供されます。Lite エディションにはありません。

## コマンドライン

`monitor_cli.py compare [--window 7|30d] [--days all|workdays|weekend] [--baseline previous|year_ago] [--format table|json|ndjson|csv]`。終了コード：0 はすべて比較できた、4 は数値のデータ不足・比較先なし・比較がオフ、5 は `--fail-on` 指定時に数値が悪化した場合です。`score --compare` は引き続き、スコアをその期間の履歴と比較します。

## ページ上

比較がオンのとき、グラフタブに「期間を比較」セクションが表示されます。期間、曜日、比較先の選択、数値ごとの変化の行、アラート、変化の一覧が含まれます。

## 設定

設定、センチネルタブ、「期間の比較」ブロック：`compare.enabled`、`compare.default_window_days`、`compare.default_days_filter`、`compare.workdays`、`compare.min_runs_per_window`、`compare.min_days_of_history`、`compare.min_resolved`、`compare.min_snapshots`、`compare.min_repo_runs`、`compare.top_changes`、`compare.include_in_report`、`compare.cache_seconds`。回答は `compare.cache_seconds` 秒間保持され、その後に再計算されます。

## 大きなアカウントでの長い期間

`compare.progressive` をオンにすると（既定ではオフ）、`compare.progressive_days`（既定 7）より長い期間の比較には、まず直近の日数ですぐに応答し、応答にもそれが示されます（`partial`：求められた日数、表示した日数、残りは計算中であること）。全期間はバックグラウンドで完了し、次のリクエストやページの次回更新で返ります。`from` と `to` を指定したリクエストは分割されません。
