<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](WEBHOOK.md) | [🇪🇸 Español](WEBHOOK_spa.md) | [🇫🇷 Français](WEBHOOK_fra.md) | [🇮🇹 Italiano](WEBHOOK_ita.md) | [🇩🇪 Deutsch](WEBHOOK_deu.md) | [🇨🇳 简体中文](WEBHOOK_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](WEBHOOK_por.md)

# 受信 Webhook

任意の機能で、**既定ではオフ**です。GitHub から変更をモニターに知らせ、次の問い合わせを待たずに次のサイクルでリポジトリを更新できます。

## 動作(更新のみ)

受け付けたイベントは、そこに書かれたリポジトリを次のサイクルで更新するようにマークするだけです。GitHub にもディスクにも何も書き込まず、イベントの文面は保存も表示もされず、モニターがすでに監視しているリポジトリだけが受け付けられます。扱うイベント:`workflow_run`、`workflow_job`、`push`、`release`、`check_run`, `check_suite`、`ping`。それ以外は `202` を返して無視します。

## 安全性

- モニターは引き続き `127.0.0.1` だけで待ち受けます。GitHub は、あなたが意図して用意したトンネル経由でのみ到達できます。ツールが自らトンネルを開くことはありません。
- `webhook.enabled` がオンで、**かつ** 共有シークレット（32 文字以上）が `webhook.secret_env` で指定した環境変数に入るまでオフのままです（既定は `MONITOR_WEBHOOK_SECRET`。`MONITOR_WEBHOOK_SECRET_FILE` で、コンテナのシークレットのように 1 行目がシークレットのファイルを指定することもできます）。シークレットは `actions_monitor.json` に書かれず、表示も記録もされず、モニターが起動するプログラムにも引き継がれません。設定タブは定義済みかどうかだけを示します。従来の方法（ファイル内の `secret`）は `webhook.allow_config_secret` が true のときだけ読まれ、使用中はライブ表示が警告します。
- すべてのリクエストに、そのシークレットで作られ一定時間で比較される `X-Hub-Signature-256: sha256=<hmac>` が必要です。それ以外は `401` となり、署名を確認するまで内容は一切見られません。
- 256 KB を超える本文は、何かを計算する前に `413` になります。
- 一覧は閉じています。処理されるのは `workflow_run`、`workflow_job`、`check_run`、`push`、`release`、`check_suite`、`ping` だけで、イベントから保持されるのは検証済みの短いフィールドだけです（コミットメッセージや自由文は保持しません）。それ以外は `202` を返して破棄します。

## オンにするには

1. 32 文字以上のランダムなシークレットを作ります。例：`python -c "import secrets; print(secrets.token_hex(32))"`。
2. ファイルではなく環境経由でモニターに渡します。モニターを起動する前に PowerShell で `$env:MONITOR_WEBHOOK_SECRET = "<シークレット>"`、シェルでは `export MONITOR_WEBHOOK_SECRET=...`、サービスでは `Environment=` または `EnvironmentFile=`（自分だけが読めるファイル）、コンテナでは `-e` または `MONITOR_WEBHOOK_SECRET_FILE` で指定するシークレットファイルを使います。
3. 受信をオンにして（設定 > 受信 Webhook > 受信オン、または `actions_monitor.json` に `"webhook": {"enabled": true}`）、モニターを再起動します。
4. アドレスに到達できるようにします。GitHub は `127.0.0.1` に届きません。意図して用意したトンネル（`/api/webhook` で終わる HTTPS アドレス）を使うか、このコンピューターでは `gh webhook forward` で `http://127.0.0.1:ポート/api/webhook` へ転送します（コマンドラインに書かずに同じシークレットを渡す方法は GitHub CLI のドキュメントを参照）。
5. GitHub でリポジトリ（または組織）> Settings > Webhooks > Add webhook を開きます。**Payload URL**：`/api/webhook` で終わるトンネルのアドレス。**Content type**：`application/json`。**Secret**：同じシークレット。**SSL verification**：有効。**Events**：「Let me select individual events」を選び、Workflow runs と Workflow jobs、必要に応じて Check runs、Pushes、Releases。**Active**：オン。組織の Webhook 1 つでその全リポジトリをカバーでき、モニターは監視していないものを無視します。
6. 確認：GitHub の Recent deliveries で最初の `ping` が `200` になること。モニターのライブ表示には、受信オン、カウンター、カバレッジが表示されます。

## リアルタイムイベント

- `webhook.record_events` がオン(既定)のとき、署名付きの `workflow_run` イベントはそのリポジトリの実行リストを GitHub を読まずに即座に更新します。ただしそのリポジトリは次のサイクルで改めて読み取られます(イベントは知らせ、読み取りが裏付けです)。配信は変更を即座に示しますが、読み取りの節約にはなりません。`workflow_job` イベントは分析用に待ち時間と各ステップの時間ももたらします。
- 保存されるのは検証済みの短いフィールド(ワークフロー、実行、状態、結論、ブランチ、短いコミット、実行へのリンク、所要時間)のみで、コミットメッセージは保存しません。ワークフロー、ブランチ、ジョブの名前は第三者が書いた最大 100 文字のテキストで、そのまま保存され、プレーンテキストとして表示されます。ステップ名は統計に入ります。最新の `webhook.live_events_keep` 件は `GET /api/live-events`(ページを開ける人:ネットワークモードではアクセストークン、チームモードではセッション)で読めます。
- 任意機能（既定ではオフ）：`live.sse.enabled` をオンにすると、`GET /api/live-events/stream` が同じイベントを受理した順にサーバー送信イベントとして送ります（`hello`、続いてイベントごとに 1 つの `live` フレーム。連番の `id` により `Last-Event-ID` または `?since=` で再開でき、保持用コメントと最後の `bye` が付きます）。読み取り専用で、ネットワークモードでは他のリクエストと同じくアクセストークンが必要です。接続数は最大 `live.sse.max_clients`、各接続は `live.sse.max_seconds` までです。Lite 版にはありません。
- 赤で終わった実行は、通知が有効なら `workflow_failed` も送ります。`webhook.record_events` をオフにすると、上で説明した更新のみのモードに戻ります。
- GitHub は `127.0.0.1` に届きません。`gh webhook forward`(GitHub CLI のドキュメント参照)か、意図して用意したトンネルで `http://127.0.0.1:PORT/api/webhook` へ転送してください。

## 時間上のカバレッジ

ライブ表示は、イベントが状態をどれだけの時間カバーしているかを示します。**イベントで把握中**（最後のイベントが `savings.webhook_window_minutes`（既定 60 分）より新しい）、**... の間イベントなし**（それより古い：静かなリポジトリ、またはトンネル切断）、**最初のイベントを待機中**のいずれかです。ポーリングは常にフォールバックです。届かなかった配信（モニター停止中、トンネル切断）は次のリポジトリ読み取りで補われるため、イベントは読み取りを減らしますが置き換えることはありません。同じ数値は `GET /api/live-status` の `coverage` と `secret_source`（`env`、`config`、`none`。シークレット自体は含みません）にもあります。

## うまくいかないとき

| 応答 | 意味 |
|---|---|
| `404` | 受信がオフ、または環境変数のシークレットがないか 32 文字未満です。 |
| `401` | 署名が一致しません。両側で同じシークレットを使い、Content type は `application/json` にします。 |
| `413` | 本文が 256 KB を超えています。 |
| `400` | 有効な `X-GitHub-Delivery` ID がないか、内容を解釈できません。 |
| `202` | 受理して無視：監視していないリポジトリ、一覧にないイベント、重複配信、または毎分の上限を超えたリポジトリ。 |
| `429` | 1 つのアドレスが 1 分間に 120 を超えるリクエストを送りました（ネットワークモード）。 |

## リプレイと大量送信

誰かが傍受した有効な署名付きリクエストを再送しても、応答はしますが処理はしません。すべての配信に `X-GitHub-Delivery` の ID が必要で、受理済みの ID は `webhook.replay_seconds`（既定 1 時間、メモリは上限あり）の間記憶され、重複には `202 {"duplicate": true}` を返します（GitHub の画面からの手動再配信は同じ ID を使うため、この期間内は無視されます）。1 つのリポジトリが 1 分間に引き起こせる受理イベントは最大 `webhook.max_per_minute` 件で、超過分は応答のみで無視されます。ペイロードに `full_name` がある場合、その所有者は監視中のアカウント（または `webhook.allowed_owners` の 1 つ）でなければなりません。ネットワークモードでは 1 つのアドレスから 1 分あたり 120 リクエストまで。受理したイベントの後、そのリポジトリの保存済み条件付き読み取りは破棄され、次のサイクルで再読み込みされるため、ライブイベントは常に GitHub と照合されます。

## ライブ表示のチェックリスト

1. `webhook.secret_env` で指定した環境変数に 32 文字以上のシークレットを入れ、Webhook を有効にします。
2. ポートを転送（`gh webhook forward`）するかトンネルを開き、`/api/webhook` で終わるそのアドレスを GitHub に設定します。
3. GitHub のテストイベント（Recent deliveries > Redeliver）を送り、`?view=live` に出るか確認します。
4. ヘッダーの割り当てに注意します。Webhook があれば周期は遅くて十分です。
