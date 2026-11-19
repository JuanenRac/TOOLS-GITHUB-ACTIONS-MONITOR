<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](API.md) | [🇪🇸 Español](API_spa.md) | [🇫🇷 Français](API_fra.md) | [🇮🇹 Italiano](API_ita.md) | [🇩🇪 Deutsch](API_deu.md) | [🇨🇳 简体中文](API_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](API_por.md)

# クライアント向け API

スクリプト、壁掛け画面、モバイルクライアントが頼れる内容です。2.0.0 から読み取り用エンドポイントは固定されます。契約にあるキーは名前と型を保ち、新しいキーは増えることがあり、新しいメジャーバージョンなしに何かが削除・変更されることはありません。

## 問い合わせ

- 通常モードでは API は `127.0.0.1` でログインなしに応答します。ネットワークモードでは全リクエストがヘッダー `X-Monitor-Access` にアクセストークンを付けます（またはセッション Cookie、または一度だけ `POST /api/access`）。チームモードではスクリプトは `POST /api/auth/login` でログインします。
- エンドポイントが知らないクエリの語は無視されます。応答は UTF-8 の JSON です。Markdown の要約とストリームは除きます。

## エラー

- エラーは JSON `{"error": "語"}` で、`code` が付くこともあります。`401 access` はトークンが無い・誤り、`403 forbidden` は許可された場所からのリクエストでないこと（見知らぬ `Host` も含む）、`404` はこの版にそのパスが無いこと（簡易版は完全版にしか無いものに 404 を返します）、`429` はアドレスがロックされているか待ち受けが満杯であることを表します。
- 拒否された書き込みは何も変えません。書き込みは契約に含まれません。

## 契約

- `docs/schemas/api_contract.json` は、各版の読み取りエンドポイントのキーと型、およびエラーコードを列挙します。読み取れるが固定されていないルート（ストリーム、テキスト、他のツール向けのエクスポート）は同じファイルの `unfrozen` に理由つきで列挙されています。実行・リポジトリ・割り当てを返す `/api/data` は固定されています。 キーはリストの要素にまで及びます。ファイル内で `[{...}]` と書かれたリストはその要素を記述し(先頭の 3 つを検査)、`/api/data` の実行・リポジトリ・割り当て、`/api/alerts` のアラート、`/api/auth/me` は、検査が失敗せずに変わることはありません。
- `python tools/check_api_contract.py` は動作中のモニターをこれに照らして検査し（`--lite`、`--url`、`--token-file`）、`CONTRACT=PASS` または `CONTRACT=FAIL` を出力します。モニターやクライアントを更新するたびに実行してください。

## 読み取りAPI v1(既定は自動)

- `api.v1_enabled` を設定します(設定、詳細、読み取りAPI v1)。`auto`(既定)は、モニターがサービスとして動いているとき(チームモードのアカウント、Dockerイメージ、systemdユニット)に応答し、1台のコンピューターで1人が使うときは閉じたままです。`on` は常に、`off` は応答しません(以前の true と false は on と off に当たります)。応答するとき、すべての読み取りルートが `/api/v1/` でも提供されます(例:`/api/v1/alerts`)。応答とロールは同じで、ヘッダー `X-API-Version: 1` が付きます。閉じている間、ライト版、および他のバージョン番号に対しては、このプレフィックスは404を返します。
- `/api/v1/me`:誰が尋ねているか。`mode`(`individual` または `team`)、`authenticated`、`user`、チームセッションの `role` と `accounts`(なければ null)、セッションができること(`capabilities`:`read`、`write`、`admin`、`v1_write`。プレフィックスは読み取り専用なので `v1_write` は常に false)、一覧の `limits`、モニターのバージョン、そして契約のバージョン(`contract`、`1.0`。キーが増えるたびに上がり、キーが消えることはありません)。
- `/api/v1/repos`:モニターが監視しているリポジトリを1行ずつ(`repo`、`ecosystem`、`state`、`risk`、`runs_24h`、`failures_24h`、`red_workflows`、`stuck_runs`、`alerts`、`last_run_at`)。フィルターは `state`、`ecosystem`、`q`。`limit`(既定は `api.default_limit`、最大 `api.max_limit`)、`cursor`(前のページの `next_cursor`。署名付きで `api.cursor_ttl_seconds` のあいだ有効)、短い行にするための `fields=a,b` または `profile=compact`。クライアントが受け入れる場合、応答は gzip で圧縮されます。
- `/api/v1/openapi.json`:固定された読み取りAPI全体の OpenAPI 3 の記述。契約(`docs/schemas/api_contract.json`)から生成され、手で書かれることはありません。固定された各ルートが約束するキーと型、`x-lite`(ライト版の応答)、`x-local-only` を含みます。契約で固定されていないルートは実験的で、`/api/v1/` では404を返し、文書にも載りません。`api.experimental_routes` をオンにすると載り(`x-experimental` 付き)ます。`/api/` の従来のルートは決して変わりません。`python bin/monitor_cli.py api openapi` で取得できます。
- クライアントを書く人のためのステップごとのガイド(コマンドを順に、エラーも): [API_V1_jpn.md](API_V1_jpn.md)。
- `python tools/api_contract_suite.py` は外部クライアント向けの契約スイートです(標準ライブラリのみ、読み取りのみ)。サーバーのアドレス(`--url`)と読み取り用トークン(`--token-file`)を渡すと、サーバーが提供する文書を検査内容の記述として使い、パラメーター不要の各ルートの形、ヘッダー `X-API-Version`、エラーの封筒と安定したコード、ページとカーソル、`fields` と `profile=compact`、gzip、プレフィックス配下に何も書き込めないことを確認します。検査ごとに1行と `API_CONTRACT=PASS` または `API_CONTRACT=FAIL` を出力し(`--json` で1つの文書)、終了コードは 0、1、2(応答なし)です。`python bin/monitor_cli.py api contract-check` はコマンドラインのモニターに対して実行します。
- 同じ3つは MCP サーバー(`python bin/mcp_server.py`、読み取り専用、フラグ不要)のツールでもあります。`api_me`(モニターがクライアントを誰とみなすか)、`api_openapi`(ドキュメント、または `path` で1つのルート)、`api_contract_check`(契約スイート、応答は `{ok, checks, failed, rows}`)。HTTP、コマンドライン(`api me`、`api openapi`、`api contract-check`)、MCP は同じドキュメントを返し、テストが比較します。プレフィックスが閉じている間は、ツールが1行でそう伝えます。
- 2つの独自ルートは、エラーを `{"error": "bad_request", "code": "api.bad_cursor", "message": "..."}` の形で返します。`error` と `code` は安定しており、`message` は `?lang=` の言語に従います。コードは api.bad_cursor、api.bad_limit、api.unknown_field、api.bad_profile, api.server_error。すべて読み取り専用で、`/api/v1/` の下に書き込みはありません。形は契約の `v1_endpoints` セクションで固定されており、`api.v1_enabled` をオンにしたモニターに対して `python tools/check_api_contract.py --v1` で確認できます。

### curl の例

トークンはネットワークモードのアクセストークンです(またはチームモードのセッションを使います)。ネットワークモードでなければ、同じコンピューターからはトークンは不要です。クライアントは `next_cursor` が `null` になるまでたどり、最初に `/api/v1/me` を読んで契約のバージョンとセッションができることを確認します。

```
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/me
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?state=bad&limit=20&profile=compact"
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/openapi.json -o openapi.json
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=50&cursor=THE_NEXT_CURSOR"
```

## ストリーム

- `GET /api/ai/stream`（アラート）と `GET /api/live-events/stream`（Webhook のイベント、`live.sse.enabled`）はサーバー送信イベントで、読み取り専用、初期状態は無効です。[AI_ALERTS_jpn.md](AI_ALERTS_jpn.md) と [WEBHOOK_jpn.md](WEBHOOK_jpn.md) を参照してください。
- `POST /api/chatops/slack` と `POST /api/chatops/discord` は、チャットからの読み取り専用コマンドを受け取ります(既定ではオフ、`chatops.enabled`)。アクセストークンは使わず、プラットフォームの署名が証明です。有効な署名のないリクエストは、何も読まれる前に拒否されます。[CHATOPS_jpn.md](CHATOPS_jpn.md) を参照。

## ページのその他のルート

これらのルートは、ページとこのコンピューターのツールのためのものです。固定された契約には含まれず、バージョン間で変わることがあります。POST は何かを変更します。「このコンピューター」とは、モニターを実行しているコンピューターだけが使えるという意味です。

| ルート | 働き |
| --- | --- |
| `/api/about` | 「このツールについて」パネル: バージョン、リンク、ファイル、状態、クレジット、更新のお知らせ。秘密は含みません。 |
| `/api/act/plan` | POST、このコンピューター。`act` でローカル実行すると何が起こるかを準備します。まだ何も実行されません。 |
| `/api/act/confirm` | POST、このコンピューター。計画の後に `act` でワークフローをこのコンピューター上で実行します。実行は記録されます。 |
| `/api/act/status` | 実行中のローカル実行の状態。 |
| `/api/act/stop` | POST、このコンピューター。ローカル実行を止めます。 |
| `/api/advanced` | 選んで有効にする機能の状態: ネットワーク、GitHub トークンの保管、GitHub 上の操作、ローカル実行、デモモード。トークンは含みません。 |
| `/api/ai/actions` | AI の操作の状態(ロック中かどうか)、その記録、AI の状態。 |
| `/api/ai/actions/confirm` | POST、このコンピューター。AI が提案した操作を、確認後に実行します。記録されます。 |
| `/api/ai/actions/unlock` | POST、このコンピューター。AI の操作のロックを一定時間だけ解除します。記録されます。 |
| `/api/ai/budget` | AI モデルごとの本日の呼び出し回数と推定コスト、上限、最近の失敗。プロバイダーには問い合わせません。 |
| `/api/ai/test` | POST、このコンピューター。設定済みの AI への接続を試します。何も変更しません。 |
| `/api/alerts/unmute` | POST。アラートのミュートを解除します。記録されます。 |
| `/api/analytics` | 実行の分析の要約: 所要時間、待ち行列、ステップ、不安定なテスト、遅い実行。 |
| `/api/discovery` | 検出が見つけたもの: アカウントと表示・非表示のリポジトリのボックス、最近のイベント、提案されたグループ、その設定、フォーク、組織。 |
| `/api/discovery/group` | POST。提案されたグループをエコシステムのファイルに追加し、ファイルのコピーを残します。 |
| `/api/gh-action/plan` | POST、このコンピューター。GitHub に送られる内容(再実行、キャンセル、ディスパッチ、マージ)を準備します。まだ何も送られません。 |
| `/api/gh-action/confirm` | POST、このコンピューター。確認後に、計画どおりの内容を GitHub に送ります。記録されます。 GitHub が拒否した場合、応答には `reason`(forbidden、not_found、method、conflict、invalid のいずれか)が付きます。 |
| `/api/github-token` | このコンピューターのみ。GitHub トークンの保管状態(方式と保存の有無)。値は決して返しません。 |
| `/api/help/search` | 単語でヘルプのトピックを検索し、一致したものを返します。 |
| `/api/help/topic` | ページの言語での、ヘルプのトピック 1 件(`id=`)の本文。 |
| `/api/help/topics` | ヘルプのトピックの一覧とそのタイトル。 |
| `/api/hot-only` | POST、このコンピューター。ページの「注目のみ」スイッチ。保存された状態は変更しません。 |
| `/api/mirror` | リポジトリのミラーの状態(既定ではオフ)。 |
| `/api/mode` | GET: 動作モード、各モードの見積り、残り時間。POST(このコンピューター): モードを変更します。 |
| `/api/notify/test` | POST。通知チャンネルの 1 つにテストメッセージを送ります。何も変更しません。 |
| `/api/quota-pool/status` | このコンピューターのみ。読み取りの各ソースの割り当てと GitHub App に足りないもの。キーやトークンは含みません。 |
| `/api/refresh-repos` | POST、このコンピューター。指定したリポジトリだけを更新し、赤のファイルを書き直します(`finalize --execute` が使います)。 |
| `/api/screens/logo` | GET: 組織のロゴ画像。POST: 新しいロゴを保存します(最大 1 MB、実際の形式で検査)。 |
| `/api/screens/logo/remove` | POST。組織のロゴを削除します。記録されます。 |
| `/api/sentinel/ai` | POST。アラートやビルドの説明を AI に求めます。リクエストは小さく、質問は先に秘密情報を取り除かれます。AI がオフの間は存在しません。 |
| `/api/sentinel/historial` | 昨日と今日の比較: 現れた・消えた赤と署名待ち。 |
| `/api/sentinel/parte/save` | POST。日次レポートのコピーを監査フォルダーに保存します。GET は決して書き込みません。 |
| `/api/sentinel/security` | GitHub がセキュリティについて未対応・不足としている内容(セキュリティ センチネル。既定ではオフ、読み取り専用)。 |
| `/api/session-token` | 次の設定変更用の使い捨てトークン。ページは書き込む直前にこれを要求します。 |
| `/api/statusbar` | ページ下部のバーが表示する内容: エディション、アドレス、アカウント、センチネル。秘密も GitHub への呼び出しもありません。 |
| `/api/welcome` | GET: 初回起動ガイドが完了しているか。POST(このコンピューター): 完了かどうかを記録します。 |
