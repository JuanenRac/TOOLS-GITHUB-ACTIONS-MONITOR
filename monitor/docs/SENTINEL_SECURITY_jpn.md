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

リポジトリとシグナルごとに 1 件のアラートがあり、詳細に重大度別の件数が入ります。各シグナルはオフにでき（`sentinels.security.signals.<シグナル>.enabled`）、Dependabot とコードスキャンには別の最小重大度も設定できます。アーカイブされたリポジトリには、それ以上の問い合わせをしません。

## 確認できなかったこと

GitHub がリポジトリに対して応答しない情報源（そこで機能がオフ、またはログインに読む権限がない：403、404）は、アラートでも健全の証明でもありません。状態の `unavailable` に、対象のリポジトリ数とともに一覧され、ページにも表示されます。唯一の例外はデフォルトブランチの保護です。保護のないブランチに対して GitHub は 404 を返し、それが指摘になります。そこでの 403 は単に読み取れないという意味です。

減点に効く情報源（Dependabot、コードスキャン、シークレット）の大半が読めないときは、レベルは `ok` ではなく `unknown` になり、スコアのセキュリティ部分は 100 として数えられる代わりに除外されます。状態には `sources_readable` と `sources_total` が表示されます。アラートが開いている間に情報源が応答しなくなった場合、そのアラートは 1 週間残り（`unread_since` が付きます）、修正済みとして通知されることはありません。読み取りが失敗し続けるリポジトリは、次の試行まで 5 分、30 分、その後は 6 時間待つので、壊れた少数のリポジトリがラウンド全体を使い切ることはありません。

各センチネルは自分の**ライフサイクル**を示すようになりました：`healthy`（正常）、`degraded`（低下：一部の読み取りが失敗、情報源が読めない、または最初の巡回が終わっていない）、`paused`（GitHub の上限待ちで一時停止）、`error`（失敗し、まだ何も読めていない）、`off`（オフ）。「アラートなし」が意味を持つのは、ライフサイクルが `healthy` のときだけです。

## コスト

1 回の巡回では最大 `sentinels.security.max_repos_per_tick` 件（既定は 5）のリポジトリを読みます。最後に見てから最も時間が経ったものを先に、未解決のアラートがあるものは少し早めに読み、`sentinels.security.refresh_seconds` 秒ごと（既定は 30 分）に 1 サイクルです。各リポジトリは最大 7 回の読み取りで、ほとんどが条件付きなので、変化のないリポジトリは上限を消費しません。CODEOWNERS ファイルは、求められた場合でも 1 日に 1 回までしか探しません。残りの上限が `sentinels.security.min_rate_remaining` を下回る間、センチネルは一時停止します。状態（`security_state.json`）は未解決のアラートを保持するので、再起動しても再通知されず、リポジトリを初めて見たときにはイベントを書きません。

## 指摘ごとに持ち主は 1 つ

すでにセキュリティの数値を表示していたセンチネルタブのパネル（リポジトリ別のアラート、古いアラート、Dependabot と CodeQL のカバレッジ、Dependabot のプルリクエスト）はパネルのままです。これらのシグナルに関するアラートタブのアラートは、このセンチネルからのみ出るので、二重に出ることはありません。 各ワークフローファイルの内容（コミットに固定されていないアクション、`write-all`、権限ブロックなし、チェックアウト付き `pull_request_target`）は[サプライチェーン監視](SENTINEL_SUPPLY_jpn.md)の担当です。`security.workflow_write` はリポジトリの設定なのでここに残ります。

## イベントと通知

新しい指摘はイベント `security_new`、解消した指摘は `security_fixed` としてフィードに書かれ、通知チャネルがそこに接続されています。どちらも通知設定で選べる種類で、ユーザーごとの設定にも「セキュリティ」の項目があります。リポジトリを初めて見たときは何も通知しません。

## 設定

設定ページの「センチネル」サブタブの「セキュリティ」ブロック：`sentinels.security.enabled`、`sentinels.security.refresh_seconds`、`sentinels.security.max_repos_per_tick`、`sentinels.security.min_rate_remaining`、`sentinels.security.repos`、`sentinels.security.signals.dependabot.enabled`、`sentinels.security.signals.dependabot.min_severity`、`sentinels.security.signals.code_scanning.enabled`、`sentinels.security.signals.code_scanning.min_severity`、`sentinels.security.signals.secret.enabled`、`sentinels.security.signals.branch.enabled`、`sentinels.security.signals.workflow.enabled`、`sentinels.security.signals.codeowners.enabled`。各指摘がスコアのセキュリティ要素から引く点数（`sentinels.security.penalty`）はファイルから読み込まれます。サンプルファイルを参照してください。
