<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CHATOPS.md) | [🇪🇸 Español](CHATOPS_spa.md) | [🇫🇷 Français](CHATOPS_fra.md) | [🇮🇹 Italiano](CHATOPS_ita.md) | [🇩🇪 Deutsch](CHATOPS_deu.md) | [🇨🇳 简体中文](CHATOPS_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](CHATOPS_por.md)

# チャットコマンド(Slack と Discord)

任意の機能で、**既定ではオフ**です。Slack または Discord のチャンネルから、モニターに短い状況(赤のリポジトリ数、未解決のアラート、キュー、スコア)を尋ねられます。**読み取り専用**です。

## できること(そして決してしないこと)

- コマンドは固定のリストです: `help`、`status`、`alerts`、`red`、`queue`、`score`。それ以外には「そのコマンドは分かりません」と返ります。`chatops.allowed_words` でリストを狭めることしかできません。
- コマンドは、モニターがすでに持っているもの(直近のサイクル、アラート、スコア)を読むだけです。GitHub に書き込まず、アクションを実行せず、設定を変更せず、シークレットを読みません。そのためのコマンドは存在せず、チャットから追加することもできません。
- 返信は質問した本人にだけ見え、誰もメンションせず、リンクは 1 種類だけです。`chatops.links` がオン(既定)のとき、名前がそのまま表示されているリポジトリの隣に、そのアドレス(`https://<ホスト>/<オーナー>/<リポジトリ>`、検証済み)を付けます。GitHub 由来のテキスト(リポジトリ名やワークフロー名)は、整形・短縮され、プラットフォーム向けにエスケープされます。
- モニターに届いたコマンドはすべて、アクションの記録(`chatops_command`)に 1 行残ります。残るのはチャットの ID であり、リクエストの本文ではありません。

## 安全性

- `chatops.enabled` とプラットフォームのスイッチ(`chatops.slack.enabled`、`chatops.discord.enabled`)がオンで、**かつ**証明が環境にあるまで、オフのままです。設定に保存されるのは変数の名前(`chatops.slack.signing_secret_env`、`chatops.discord.public_key_env`)だけで、値は保存されません。値は書き込まれず、表示も記録もされません。
- Slack: すべてのリクエストに `X-Slack-Signature: v0=<hmac>`(署名シークレットで作った `v0:<タイムスタンプ>:<本文>` の HMAC-SHA256)が必要で、`X-Slack-Request-Timestamp` は `chatops.max_age_seconds`(最大 5 分)より古くてはいけません。比較は署名の内容にかかわらず同じ時間で行われます。
- Discord: すべてのリクエストに `X-Signature-Ed25519` と `X-Signature-Timestamp` が必要です。タイムスタンプと本文を連結したものの Ed25519 署名を、アプリの公開鍵で検証します(RFC 8032、標準ライブラリ。検証なしには何も受け付けません)。
- 不正・古い・未来の署名には `401` を返し、本文は一切見ません。一度受け付けた署名は二度と受け付けません。16 KB を超える本文には `413` を返します。1 つのアドレスから 1 分間に 120 リクエストまで受け付けます。
- **リストは必須です**: `chatops.allowed_teams`、`chatops.allowed_channels`、`chatops.allowed_users`。どれも埋めていなければコマンドは実行されません(設定を完了できるよう、プラットフォームのチャレンジには応答します)。項目のあるリストには、リクエストのチーム・チャンネル・ユーザーが含まれていなければなりません。
- 1 分あたりの上限: `chatops.rate_per_user_per_minute`、`chatops.rate_per_channel_per_minute`、`chatops.rate_per_minute`。応答は 3 秒以内に返す必要があります。モニターはメモリから答え、遅くなる場合は処理中であることを伝えます。
- 2 つのルート(`/api/chatops/slack`、`/api/chatops/discord`)は、ネットワークモードのアクセストークンを要求しません。プラットフォームはそれを送れないためで、受信 Webhook と同様に署名が証明になります。ネットワークモードを開かない限り、モニターは `127.0.0.1` のみで待ち受けます。プラットフォームから到達できるのは、あなたが意図して用意した HTTPS アドレス(トンネルやリバースプロキシ。ツールが開くことはありません)経由だけです。そこで公開するのは `/api/chatops/` だけにしてください。

## コマンド

| コマンド | 返答 |
| --- | --- |
| `help` | コマンドの一覧 |
| `status` | 赤・停滞・待機・緑・アイドルのリポジトリ数と、未解決のアラート |
| `alerts` | 未解決のアラート(レベル、コード、リポジトリ)。最大 `chatops.max_rows` 行 |
| `red` | 赤のワークフローと赤になってからの時間。最大 `chatops.max_rows` 行 |
| `queue` | 実行中、待機中、承認待ち、24 時間の使用分数 |
| `score` | スコア、そのランク文字、変化 |

`chatops.show_repo_names` が名前の扱いを決めます: `all`(非公開リポジトリを含むすべての名前)、`public`(既定。非公開リポジトリは `private-N` と表示され、そのワークフロー名は出ません)、`none`。**`all` のリスク:** 非公開リポジトリとワークフローの名前が、リストで許可したすべてのチャンネルとユーザーに届きます。そのためリストは必須で、項目のあるリストはすべて一致する必要があります(チーム・チャンネル・ユーザーが同時に)。チャンネルが、それらの名前を知ってよい人たちより広い場合は、`public`(既定)のままにするか `none` を選んでください。

## Slack の手順

1. api.slack.com/apps > Create New App > From scratch を開き、名前を付けてワークスペースを選びます。
2. Slash Commands > Create New Command: コマンド `/monitor`、**Request URL** は `https://<公開アドレス>/api/chatops/slack`、短い説明を入力します。ボットのスコープは不要です。
3. Basic Information > App Credentials > **Signing Secret** をコピーし、ファイルではなく環境経由でモニターに渡します。モニターを起動する前に PowerShell で `$env:MONITOR_SLACK_SIGNING_SECRET = "<signing secret>"`、シェルでは `export MONITOR_SLACK_SIGNING_SECRET=...`、サービスやコンテナでは環境エントリまたはシークレットファイルを使います。
4. アプリをワークスペースにインストールします(Install App)。
5. リストを埋めます: チーム ID(`T` で始まる)、チャンネル ID(チャンネルの詳細の下部: `C...`)、メンバー ID(プロフィール > Copy member ID: `U...`)。設定 > チャットコマンドに入力するか、`actions_monitor.json` に `"chatops": {"allowed_channels": ["C0123456789"]}` と書きます。
6. チャットコマンドと Slack をオンにして、モニターを再起動します。

## Discord の手順

1. discord.com/developers/applications > New Application を開き、General Information の **Public Key**(16 進 64 文字)をコピーして、環境経由でモニターに渡します: PowerShell では `$env:MONITOR_DISCORD_PUBLIC_KEY = "<公開鍵>"`、シェルでは `export MONITOR_DISCORD_PUBLIC_KEY=...`。
2. リストを埋め、チャットコマンドと Discord をオンにして(設定 > チャットコマンド)、モニターを再起動します。次の手順より**前に**行ってください。アドレスを保存すると Discord が署名付きのテストを送り、モニターが応答しないと拒否されます。
3. General Information > **Interactions Endpoint URL**: `https://<公開アドレス>/api/chatops/discord` を入力して Save します。
4. 自分のツール(Discord API、`POST /applications/<アプリケーション ID>/commands`)で、次の本文を使ってコマンドを一度だけ登録します:

```json
{
  "name": "monitor",
  "description": "Read only status of the GitHub Actions Monitor",
  "type": 1,
  "options": [{"name": "command", "description": "help, status, alerts, red, queue or score", "type": 3, "required": false,
               "choices": [{"name": "help", "value": "help"}, {"name": "status", "value": "status"}, {"name": "alerts", "value": "alerts"}, {"name": "red", "value": "red"}, {"name": "queue", "value": "queue"}, {"name": "score", "value": "score"}]}]
}
```

5. スコープ `applications.commands` だけでアプリを招待します(OAuth2 > URL Generator)。ボットの権限は不要です。ID: Discord で開発者モード(詳細設定)をオンにし、サーバー・チャンネル・自分のユーザーで「ID をコピー」を使います。

## 試す

許可したチャンネルで `/monitor help`(Slack)または `/monitor command:status`(Discord)と入力します。その他の応答:

| 表示 | 意味 |
| --- | --- |
| 何も出ない、または「応答しませんでした」 | アドレスに到達できない、モニターがオフ、または `401` を返した(シークレットや鍵が違う、または時計が 5 分以上ずれている) |
| 「このコマンドはここでは使えません。」 | チーム・チャンネル・ユーザーがリストにない |
| 「コマンドが多すぎます。」 | 1 分あたりの 3 つの上限のどれか |
| 「モニターはまだ GitHub を読み込んでいません。」 | 最初のサイクルが終わっていない |
