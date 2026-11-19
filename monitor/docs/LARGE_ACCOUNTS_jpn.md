<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LARGE_ACCOUNTS.md) | [🇪🇸 Español](LARGE_ACCOUNTS_spa.md) | [🇫🇷 Français](LARGE_ACCOUNTS_fra.md) | [🇮🇹 Italiano](LARGE_ACCOUNTS_ita.md) | [🇩🇪 Deutsch](LARGE_ACCOUNTS_deu.md) | [🇨🇳 简体中文](LARGE_ACCOUNTS_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](LARGE_ACCOUNTS_por.md)

# 大規模アカウント: 数百のリポジトリ

数百のリポジトリ、多数のフォーク、複数の組織があるアカウントは API の割り当てをすぐに使い切ります。以下は、効果の大きい順のレシピです。設定はすべて設定タブにあります。

1. **まずプロファイルを選ぶ。** 設定 > 基本 > プロファイル: *オープンソース組織* を選ぶと、以下の大半がワンクリックで設定されます（後から各設定を変更できます）。
2. **保守されているものを監視する。** `discovery.fork_policy` = `auto` は独自の CI があるフォークだけを残します（アカウントの種類が期間を決めます: `discovery.fork_ci_days`）。`discovery.fork_checks_per_pass` は問い合わせを複数回の一覧取得に分散します。`discovery.skip_archived` は既定でオンです。`exclude` と `ecosystems` で名前による絞り込みができます。 空のアカウント一覧、または前回の正常な一覧の `discovery.min_keep_pct` パーセント未満の一覧は信用されません。前回の正常な一覧を保ち、5 分後に再度読み、AI ツール向けブリーフにシグナル repos.listing が出ます。 `discovery.hide` は `public`(および `private`、`fork`、`empty`)も受け付けます。基本タブは各ルールが除外した数を数えるので、フィルターで除外されたものがクリーンとして読まれることはありません。
3. **問い合わせを減らす。** `cold_runs_per_repo` と `cold_refresh_seconds` は静かなリポジトリのコストを、`runs_per_repo` と `refresh_seconds` はアクティブなものを決めます。`network.etag` は変化がないときの繰り返しの読み取りを無料にし、低速モード（`modes.auto_low`）は割り当てが減ると自動で速度を落とします。
4. **センチネルに予算を与える。** `sentinel.budget_per_hour`、`sentinel.max_calls_per_tick`、`sentinel.hygiene_seconds`（衛生チェックは既定でリポジトリごとに6時間に1回のリクエストです。長くしてください）が A3〜A6 の消費を抑えます。
5. **2つ目の割り当てを加える。** `github_app.share_reads` で GitHub App が自分の割り当てで読み取りの一部に答えます。
6. **ノイズに埋もれない。** 衛生チェック（`sentinel.hygiene.ruleset_mode` = `effective`、`sentinel.hygiene.skip`）、リリースファイルの確認（`sentinel.surface.checks.release_assets.allow_empty`）、`sentinel.bots_apart` により、リポジトリに当てはまらないチェックが溜まるのを防ぎます。

割り当てタブには、各ソースの残りとモニター自身の消費量が表示されます。

フォークの元リポジトリの追跡(`upstream.enabled`)は、`upstream.requests_per_hour` と `upstream.forks_per_request` のペアですべてのフォークを一巡するのにかかる時間をパネルに表示します。これが `upstream.refresh_hours` より長いと追跡は休むことがありません(727 件のフォークを 1 回 8 件、1 時間 6 回で読むと 15.2 時間かかります)。直近 1 時間のリクエストは再起動後も保持されるため、再起動で割り当てが戻ることはありません。

センチネルの 1 ティック分の呼び出し(`sentinel.max_calls_per_tick`)は、すべての段階で 1 つの数として数えられます。読み取りが 3 回続けて失敗したリポジトリは 30 秒間(最大 10 分まで倍々で)放置され、その間にほかのリポジトリが読み取られます。
