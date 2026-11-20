<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_SECURITY.md) | [🇪🇸 Español](SENTINEL_SECURITY_spa.md) | [🇫🇷 Français](SENTINEL_SECURITY_fra.md) | [🇮🇹 Italiano](SENTINEL_SECURITY_ita.md) | [🇩🇪 Deutsch](SENTINEL_SECURITY_deu.md) | [🇨🇳 简体中文](SENTINEL_SECURITY_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](SENTINEL_SECURITY_por.md)

# セキュリティセンチネル

CI センチネル、コラボレーションセンチネルに続く 3 つ目のセンチネルです。GitHub に何も書き込まずに、各リポジトリのセキュリティについて GitHub 自身が未解決または不足していると報告している内容を読み取り、アラートタブのアラート（由来：セキュリティ）にします。Complete エディションにあり、既定ではオフです（`sentinels.security.enabled`）。Lite にはセンチネルがありません。

## 何を読み、何を指摘するか

| シグナル | アラート | レベル | 既定でオン |
|---|---|---|---|
| 重大度が `min_severity` 以上の未解決の Dependabot アラート（既定は high） | `security.dependabot` | 1 件でも critical なら critical、high なら error、それ以外は警告 | はい |
| 重大度が `min_severity` 以上の未解決のコードスキャンアラート | `security.code_scanning` | 同じ | はい |
| 未解決のシークレットスキャンのアラート | `security.secret` | 常に critical（GitHub が見つけたシークレットは漏えいしたシークレットです） | はい |
| デフォルトブランチに保護がない | `security.branch_unprotected` | 警告 | はい |
| ワークフローに既定で書き込み権限が与えられている | `security.workflow_write` | 警告 | はい |
| CODEOWNERS ファイルがない | `security.codeowners_missing` | 情報 | いいえ |
| 監視ツールが確認した重要な run(既定ブランチへの push、手動実行、`pull_request_target` の run)が削除された | `security.runs_deleted` | error | いいえ |

**削除された run**(`security.runs_deleted`、既定はオフ): シークレットが漏えいした後、それを出力した run を削除するのが痕跡を消す典型的な方法で、GitHub には目に見える記録が残りません。`sentinels.security.signals.runs_deleted.enabled` をオンにすると、センチネルは確認した重要な run の短い非公開リストを保持し、run の一覧から消えたものがあれば、その 1 件だけを問い合わせます。明示的な 404 は削除とみなし、拒否(403)、ネットワークエラー、5xx は数えません。`sentinels.security.signals.runs_deleted.check_window_days`(14)より古い run は問い合わせず(アカウントの保持期間で消えた可能性があるため)、検出した削除は同じ日数だけ通知として残ります。リポジトリ・ラウンドごとに問い合わせる単独の run は最大 `sentinels.security.signals.runs_deleted.max_checks`(50)件です。通知にはワークフロー名、実行者、ブランチが入り、run の内容は入りません。

リポジトリとシグナルごとに 1 件のアラートがあり、詳細に重大度別の件数が入ります。各シグナルはオフにでき（`sentinels.security.signals.<シグナル>.enabled`）、Dependabot とコードスキャンには別の最小重大度も設定できます。アーカイブされたリポジトリには、それ以上の問い合わせをしません。

## 確認できなかったこと

GitHub がリポジトリに対して応答しない情報源（そこで機能がオフ、またはログインに読む権限がない：403、404）は、アラートでも健全の証明でもありません。状態の `unavailable` に、対象のリポジトリ数とともに一覧され、ページにも表示されます。唯一の例外はデフォルトブランチの保護です。保護のないブランチに対して GitHub は 404 を返し、それが指摘になります。そこでの 403 は単に読み取れないという意味です。

減点に効く情報源（Dependabot、コードスキャン、シークレット）の大半が読めないときは、レベルは `ok` ではなく `unknown` になり、スコアのセキュリティ部分は 100 として数えられる代わりに除外されます。状態には `sources_readable` と `sources_total` が表示されます。アラートが開いている間に情報源が応答しなくなった場合、そのアラートは 1 週間残り（`unread_since` が付きます）、修正済みとして通知されることはありません。読み取りが失敗し続けるリポジトリは、次の試行まで 5 分、30 分、その後は 6 時間待つので、壊れた少数のリポジトリがラウンド全体を使い切ることはありません。

アカウントのプランにないソース(無料プランの非公開リポジトリのブランチ保護やコードスキャン。GitHub は別のプランが必要と答えます)は、拒否やオフの機能と区別されます。ページと状態の `unavailable_why` に `N/A(プラン)`、`N/A(アクセスなし)`、`N/A(オフ)` と表示されます。`sentinels.security.plan_na` がオン(既定)のとき、1 つ目の種類のソースは読み取り可能数とスコアのカバレッジから除外され、`sources_na_plan` として別に数えられます。3 つのどれも検出事項ではなく、問題なしの証拠でもありません。減点に効くものがプランにまったくない監視は `unknown` になり、スコアにセキュリティの部分は付きません。オフのときは読み取れなかったソースとして数えます。

各センチネルは自分の**ライフサイクル**を示すようになりました：`healthy`（正常）、`degraded`（低下：一部の読み取りが失敗、情報源が読めない、または最初の巡回が終わっていない）、`paused`（GitHub の上限待ちで一時停止）、`error`（失敗し、まだ何も読めていない）、`off`（オフ）。「アラートなし」が意味を持つのは、ライフサイクルが `healthy` のときだけです。

## コスト

1 回の巡回では最大 `sentinels.security.max_repos_per_tick` 件（既定は 5）のリポジトリを読みます。最後に見てから最も時間が経ったものを先に、未解決のアラートがあるものは少し早めに読み、`sentinels.security.refresh_seconds` 秒ごと（既定は 30 分）に 1 サイクルです。各リポジトリは最大 7 回の読み取りで、ほとんどが条件付きなので、変化のないリポジトリは上限を消費しません。CODEOWNERS ファイルは、求められた場合でも 1 日に 1 回までしか探しません。残りの上限が `sentinels.security.min_rate_remaining` を下回る間、センチネルは一時停止します。状態（`security_state.json`）は未解決のアラートを保持するので、再起動しても再通知されず、リポジトリを初めて見たときにはイベントを書きません。 ラウンドは `sentinels.security.deadline_s` 秒(既定 30、0 = 上限なし)を過ぎると新しいリポジトリを始めません。届かなかったものは次のラウンドを待ち、状態にはアラート 0 件ではなく `unchecked`(と `round_cut`)として名前付きで一覧されます。

## 指摘ごとに持ち主は 1 つ

すでにセキュリティの数値を表示していたセンチネルタブのパネル（リポジトリ別のアラート、古いアラート、Dependabot と CodeQL のカバレッジ、Dependabot のプルリクエスト）はパネルのままです。これらのシグナルに関するアラートタブのアラートは、このセンチネルからのみ出るので、二重に出ることはありません。 各ワークフローファイルの内容（コミットに固定されていないアクション、`write-all`、権限ブロックなし、チェックアウト付き `pull_request_target`）は[サプライチェーン監視](SENTINEL_SUPPLY_jpn.md)の担当です。`security.workflow_write` はリポジトリの設定なのでここに残ります。

## イベントと通知

新しい指摘はイベント `security_new`、解消した指摘は `security_fixed` としてフィードに書かれ、通知チャネルがそこに接続されています。どちらも通知設定で選べる種類で、ユーザーごとの設定にも「セキュリティ」の項目があります。リポジトリを初めて見たときは何も通知しません。

## 設定

設定ページの「センチネル」サブタブの「セキュリティ」ブロック：`sentinels.security.enabled`、`sentinels.security.refresh_seconds`、`sentinels.security.max_repos_per_tick`、`sentinels.security.min_rate_remaining`、`sentinels.security.repos`, `sentinels.security.plan_na`、`sentinels.security.signals.dependabot.enabled`、`sentinels.security.signals.dependabot.min_severity`、`sentinels.security.signals.code_scanning.enabled`、`sentinels.security.signals.code_scanning.min_severity`、`sentinels.security.signals.secret.enabled`、`sentinels.security.signals.branch.enabled`、`sentinels.security.signals.workflow.enabled`、`sentinels.security.signals.codeowners.enabled`, `sentinels.security.signals.runs_deleted.enabled`, `sentinels.security.signals.runs_deleted.check_window_days`, `sentinels.security.signals.runs_deleted.max_checks`。各指摘がスコアのセキュリティ要素から引く点数（`sentinels.security.penalty`）はファイルから読み込まれます。サンプルファイルを参照してください。

## ルールセットによるブランチ保護

デフォルトブランチは、クラシックなブランチ保護**または**有効なルールセットがあれば保護されているとみなします（ルールセットだけで保護されたリポジトリではクラシックのエンドポイントが 404 を返すため、センチネルはブランチの `protected` フラグと有効なルールも読みます）。`signals.branch.require` にはルールが備えるべき種類（例：`pull_request`、`required_status_checks`）を列挙でき、保護済みブランチに不足があれば不足分とともに通知されます。既定は空のリストで、どんな保護でも十分です。呼び出しがタイムアウトして読み取れなかったリポジトリは、原因（`timeout`、`rate`、`network`、`error`）とともに状態の `errors` と `error_kinds` に載り、検出事項にはなりません。
