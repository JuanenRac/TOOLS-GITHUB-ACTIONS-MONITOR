<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_SUPPLY.md) | [🇪🇸 Español](SENTINEL_SUPPLY_spa.md) | [🇫🇷 Français](SENTINEL_SUPPLY_fra.md) | [🇮🇹 Italiano](SENTINEL_SUPPLY_ita.md) | [🇩🇪 Deutsch](SENTINEL_SUPPLY_deu.md) | [🇨🇳 简体中文](SENTINEL_SUPPLY_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](SENTINEL_SUPPLY_por.md)

# サプライチェーン監視

CI、コラボ、セキュリティに続く4つ目の監視です。GitHub には何も書き込まず、API を通じて（クローン不要で）各リポジトリのワークフローファイル（`.github/workflows`）を読み取り、移動したタグや第三者がリポジトリのトークンとコードで動作できてしまう箇所を知らせます。結果は「アラート」タブのアラート（発生元: サプライチェーン）になります。Complete 版にあり、既定ではオフです（`sentinels.supply.enabled`）。Lite には監視がありません。

メニューのセンチネルグループに専用の項目 **サプライチェーンセンチネル** (アドレス `#sentinel-supply`) があり、センチネルがオンの間だけ表示されます。各リポジトリの未解決の指摘、サイクルの状態、読み取れなかったものを 1 つのパネルに表示し、項目のバッジはエラーの数を示します。

## 知らせる内容

| シグナル | アラート | レベル | 既定でオン |
|---|---|---|---|
| アクションや再利用可能ワークフローの `uses:` が完全なコミット SHA に固定されていない（所有者がタグを移動できる） | `actions.supply.unpinned` | warning | はい |
| `uses:` が自動的に動くブランチ（`@main`、`@master` など）を指している: タグより悪い | `actions.supply.mutable_ref` | warning | はい |
| `permissions: write-all` を持つワークフロー | `actions.supply.permissions_wide` | warning | はい |
| `permissions:` ブロックがないワークフロー（トークンはより広い既定の権限を受け取る） | `actions.supply.permissions_missing` | warning | はい |
| `pull_request_target` とプルリクエストのコードのチェックアウトの組み合わせ | `actions.supply.pr_target_checkout` | error | はい |

リポジトリとシグナルごとに1件のアラートが出て、詳細に指摘の件数、該当ファイル、少数の例（アクション名）が入ります。各シグナルはオフにでき（`sentinels.supply.signals.<シグナル>.enabled`）、別のレベル（`info`、`warning`、`error`、`critical`）にもできます。同じリポジトリのワークフローを指す `uses:` は第三者ではないので除外されます。

## 唯一の情報源

独自のルールはありません。指摘はワークフローのリンター（`bin/lint_workflows.py`、「監視」タブやコマンドラインと同じもの）から来ます。ここで有効なのは `unpinned_uses`、`permissions`、`pr_target` だけで、他のルールはオフのままです。特にファイル内に書かれた秘密情報を探すルールはオフなので、**秘密情報の値は読み取られず、保存も表示もされません**。`lint.own_owners` と `lint.unpinned_own` の設定は自分のアカウントのアクションの扱いを引き続き決め、ワークフロー内のコメント `# monitor-lint: ignore ルール` でその場で指摘を抑えられます。

## 指摘ごとに持ち主は1つ

`security.workflow_write`（セキュリティ監視）はリポジトリの既定の権限という GitHub の設定です。ここのシグナルは各ワークフローファイルの内容に関するものなので、同じリポジトリが両方から同じ指摘を出すことはありません。「監視」タブの lint パネルはパネルのままで、これらのシグナルに関する「アラート」タブのアラートはここからだけ出ます。

## 確認できなかったもの

ワークフローが読めないリポジトリ（アクセス権なし、SSO 未承認、API 枠の使い切り、ファイルが多すぎるフォルダ）はアラート**ではなく**、健全という証明**でもありません**。状態の `unavailable` に理由と件数付きで載り、確認した対象の大半が読めなかった場合、レベル `ok` は `unknown` と表示されます。アラートのあるリポジトリが応答しなくなっても、アラートは1週間残り（`unread_since` が付く）、解決済みとして通知されることはありません。`.github/workflows` フォルダのないリポジトリは読み取られ、報告するものがないだけです。読み取りが失敗し続けるリポジトリは、5分、30分、その後6時間待ってから再試行します。

## コスト

1回の巡回で読むのは最大 `sentinels.supply.max_repos_per_tick` 個のリポジトリ（既定 10）、呼び出しは最大 `sentinels.supply.max_calls_per_tick` 回（60）です。リポジトリのワークフロー一覧に1回、新規または変更されたファイルごとに1回で、SHA が変わらないファイルは再読込しません。最後に読んでから最も長いものが先で、未解決のアラートがあるものは少し早めです。周期は `sentinels.supply.refresh_seconds` ごと（既定は1時間）。残りの API 枠が `sentinels.supply.min_rate_remaining` を下回る間は一時停止します。状態（`supply_state.json`）は未解決のアラートを保持するので、再起動しても再通知されず、リポジトリの最初の確認ではイベントを書きません。`sentinels.supply.max_files_per_repo` は1つのリポジトリで読むファイル数を制限し、超えたリポジトリは一部だけ読まれ、部分的として数えられます。 ラウンドは `sentinels.supply.deadline_s` 秒(既定 30、0 = 上限なし)を過ぎると新しいリポジトリを始めません。届かなかったものは次のラウンドを待ち、状態にはアラート 0 件ではなく `unchecked`(と `round_cut`)として名前付きで一覧されます。

`sentinels.supply.incremental`(既定はオフ)をオンにすると、ワークフローファイル(そのブロブ SHA)とルールが前回の正常な走査と同じリポジトリは再検査されず、通知もそのまま残ります。見ないことで通知が閉じられることはなく、ルール、無視リスト、プログラムのバージョンのいずれかが変わると全リポジトリが再検査されます。ステータスには変更のなかったリポジトリ数(`unchanged`)が表示されます。よく知っているリポジトリ向けの選択であり、継承される既定値ではありません。

## 指摘を無視する

`sentinels.supply.ignore` は、リンターのルール名を使った `リポジトリ:ファイル:ルール` のパターン（`*` は任意）を受け付けます。例: `myrepo:release.yml:unpinned_uses`。`unpinned_uses` は `unpinned` と `mutable_ref` の両方の背後にあるルールで、`permissions` は2つの権限シグナルの背後にあるルールです。`lint.ignore` のパターンはここには適用されません。

## イベント、通知、スコア

新しい指摘はイベント `security_new` を、解決したものは `security_fixed` を書きます（イベントには `sentinel: supply` とアラートのコードが入ります）。このため、各ユーザーの通知設定の「セキュリティ」欄とチャンネルが誰に知らせるかを決めます。リポジトリの最初の確認では何も通知しません。メトリクスには `supply_alerts`、`supply_findings`、`supply_penalty`（参考値: `sentinels.supply.penalty.per_finding`（2）と `cap_per_repo`（10）はファイルから読みます）、`supply_repos_checked`、`supply_repos_unreadable`、`supply_calls_last_hour` が入ります。スコアはこの減点を使いません。API は `GET /api/sentinel/supply` に応答し、「アラート」タブと `monitor_cli.py alerts --sentinel supply` はこれで絞り込めます。

## 設定

「設定」ページの「監視」サブタブ、「サプライチェーン」ブロック: `sentinels.supply.enabled`, `sentinels.supply.incremental`, `sentinels.supply.refresh_seconds`, `sentinels.supply.max_repos_per_tick`, `sentinels.supply.max_calls_per_tick`, `sentinels.supply.max_files_per_repo`, `sentinels.supply.min_rate_remaining`, `sentinels.supply.repos`, `sentinels.supply.ignore`, `sentinels.supply.signals.unpinned.enabled`, `sentinels.supply.signals.unpinned.level`, `sentinels.supply.signals.mutable_ref.enabled`, `sentinels.supply.signals.mutable_ref.level`, `sentinels.supply.signals.permissions_wide.enabled`, `sentinels.supply.signals.permissions_wide.level`, `sentinels.supply.signals.permissions_missing.enabled`, `sentinels.supply.signals.permissions_missing.level`, `sentinels.supply.signals.pr_target_checkout.enabled`, `sentinels.supply.signals.pr_target_checkout.level`.

## しないこと

GitHub には書き込まず（プルリクエスト、ラベル、イシューは作りません）、アクションを固定する SHA の提案もせず、秘密情報の値も読みません。
