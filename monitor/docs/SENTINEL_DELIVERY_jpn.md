<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_DELIVERY.md) | [🇪🇸 Español](SENTINEL_DELIVERY_spa.md) | [🇫🇷 Français](SENTINEL_DELIVERY_fra.md) | [🇮🇹 Italiano](SENTINEL_DELIVERY_ita.md) | [🇩🇪 Deutsch](SENTINEL_DELIVERY_deu.md) | [🇨🇳 简体中文](SENTINEL_DELIVERY_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](SENTINEL_DELIVERY_por.md)

# 配信センチネル

CI、Collab、セキュリティ、サプライチェーンに続く5番目のセンチネルです。GitHubには何も書き込まずに、各リポジトリの最新リリース、最新タグ、CHANGELOG、指定したバージョンファイルを（APIで、クローンなしで）読み取り、ビルドされたのに配信されていないものを知らせます。結果はアラートタブ（由来: 配信）のアラートになります。Complete版にあり、既定ではオフです（`sentinels.delivery.enabled`）。Liteにはセンチネルがありません。

メニューのセンチネルグループに専用の項目 **配信センチネル** (アドレス `#sentinel-delivery`) があり、センチネルがオンの間だけ表示されます。各リポジトリの未解決の指摘、サイクルの状態、読み取れなかったものを 1 つのパネルに表示し、項目のバッジはエラーの数を示します。

## 知らせる内容

| シグナル | アラート | レベル | 既定でオン |
|---|---|---|---|
| CHANGELOGの`[Unreleased]`に項目があり、最新の公開リリースが`sentinels.delivery.unreleased_days`日（14）より古い | `release.unreleased_pending` | info | はい |
| 最新の公開リリースより新しいバージョンタグがあり、そのタグ自身のリリースがない（下書きは配信済みとは数えません） | `release.tag_without_release` | warning | はい |
| 最新の公開リリースの説明が空 | `release.release_without_notes` | info | はい |
| `version_files`に挙げたバージョンファイルとCHANGELOGの最初のバージョン見出しが、すべて同じバージョンを示していない（`1.2`と`1.2.0`は同じ） | `release.version_mismatch` | warning | はい |
| 共有契約を提供するリポジトリの最新リリースより古いバージョンをリポジトリが固定している（`sentinel.readiness.pins.sources`の固定表、種類`pin_table`） | `release.ecosystem_drift` | warning | はい |
| 最新の公開リリースに、`expected_assets`のパターン（例: `*.zip`、`SHA256SUMS*`）のいずれかに合うファイルがない | `release.assets_missing` | warning | はい |

アラートはリポジトリとシグナルごとに1件で、詳細に件数といくつかのタグ、パターン、バージョンが入ります。各シグナルはオフにでき（`sentinels.delivery.signals.<シグナル>.enabled`）、レベル（`info`、`warning`、`error`、`critical`）を変えられます。公開リリースが一つもないリポジトリは、リリースに関するシグナルの対象外です（リリースを使っていないため）。プレリリースと下書きは最新リリースとして扱いません。

## 指摘ごとに持ち主は一つ

センチネルタブの準備状況パネル（A11）は、ローカルのクローンから作るリポジトリごとの1行です。このセンチネルは、安定したID、ミュート、イベント、独自の周期を持つアラートを、クローンなしでAPI経由で作ります。リポジトリのワークフローに関するシグナルはサプライチェーンのセンチネルに、GitHubの設定に関するものはセキュリティに属し、同じものが二重に出ることはありません。ロードマップの任意プラグイン「Releases」は、このセンチネルに置き換わります。

## 確認できなかったもの

読み取れないリポジトリ（アクセスなし、SSO未承認、利用枠の枯渇、1つのリポジトリに必要な呼び出し数より少ない巡回）は、アラートでも異常なしでもありません。状態の`unavailable`に理由と件数つきで並び、見たものの大半が読めなかったときは、レベル`ok`は`unknown`と表示されます。アラートを持つリポジトリが応答しなくなると、アラートは1週間残り（`unread_since`の印つき）、解消済みとして通知されることはありません。存在しないファイル（そのパスにCHANGELOGがない、そのバージョンファイルがない）は単に無いものとして扱います。固定表は周期ごとに1回読みます。読めない固定表はアラートを保ったまま一覧に載ります。

## コスト

1回の巡回で読むのは最大`sentinels.delivery.max_repos_per_tick`個のリポジトリ（既定10）、呼び出しは最大`sentinels.delivery.max_calls_per_tick`回（60）です。リリースに1回、タグに1回、CHANGELOGに1回（複数のパスを挙げて最初のものがなければ増えます）、バージョンファイルごとに1回です。オフにしたシグナルは全く読みません。最も前に読んだものから先に、開いたアラートのあるものは少し早めに読みます。周期は`sentinels.delivery.refresh_seconds`ごと（既定1時間）です。条件付きリクエストはなく、コストは304応答ではなくこれらの設定で抑えられます。残りの利用枠が`sentinels.delivery.min_rate_remaining`を下回る間は一時停止します。状態（`delivery_state.json`）は開いているアラートを保つので、再起動しても何も再通知されず、リポジトリを初めて見たときにはイベントを書きません。

## イベント、通知、スコア

新しい指摘はイベント`delivery_new`、解消した指摘は`delivery_fixed`を書きます（イベントには`sentinel: delivery`とアラートのコードが入ります）。これらはリリースのファミリーに属するため、選べるのはメンテナーと管理者だけで、ユーザーごとの通知設定でのセンチネル`ci`の選択が誰に届くかを決めます。既定のイベント一覧には入っていません。メトリクスには`delivery_alerts`、`delivery_unreleased_repos`、`delivery_unreleased_days_max`、`delivery_repos_checked`、`delivery_repos_unreadable`、`delivery_calls_last_hour`が入ります。スコアには使われません。APIは`GET /api/sentinel/delivery`に答え、アラートタブと`monitor_cli.py alerts --sentinel delivery`でこれによる絞り込みができます。

## 設定

設定ページのセンチネルサブタブ、配信ブロック: `sentinels.delivery.enabled`, `sentinels.delivery.refresh_seconds`, `sentinels.delivery.max_repos_per_tick`, `sentinels.delivery.max_calls_per_tick`, `sentinels.delivery.min_rate_remaining`, `sentinels.delivery.repos`, `sentinels.delivery.unreleased_days`, `sentinels.delivery.unreleased_min_entries`, `sentinels.delivery.changelog_paths`, `sentinels.delivery.version_files`, `sentinels.delivery.expected_assets`, `sentinels.delivery.signals.unreleased_pending.enabled`, `sentinels.delivery.signals.unreleased_pending.level`, `sentinels.delivery.signals.tag_without_release.enabled`, `sentinels.delivery.signals.tag_without_release.level`, `sentinels.delivery.signals.release_without_notes.enabled`, `sentinels.delivery.signals.release_without_notes.level`, `sentinels.delivery.signals.version_mismatch.enabled`, `sentinels.delivery.signals.version_mismatch.level`, `sentinels.delivery.signals.ecosystem_drift.enabled`, `sentinels.delivery.signals.ecosystem_drift.level`, `sentinels.delivery.signals.assets_missing.enabled`, `sentinels.delivery.signals.assets_missing.level`.

## しないこと

GitHubには何も書き込みません（タグ、リリース、ラベル、プルリクエスト、イシューなし）。何も公開も署名もせず、アラートから提案を作ることもなく、CHANGELOGと指定したバージョンファイル以外のファイルの内容は読みません。
