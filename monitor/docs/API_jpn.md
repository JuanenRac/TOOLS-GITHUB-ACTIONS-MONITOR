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
- 2つの独自ルートは、エラーを `{"error": "bad_request", "code": "api.bad_cursor", "message": "..."}` の形で返します。`error` と `code` は安定しており、`message` は `?lang=` の言語に従います。コードは api.bad_cursor、api.bad_limit、api.unknown_field、api.bad_profile, api.server_error。すべて読み取り専用で、`/api/v1/` の下に書き込みはありません。形は契約の `v1_endpoints` セクションで固定されており、`api.v1_enabled` をオンにしたモニターに対して `python tools/check_api_contract.py --v1` で確認できます。

## ストリーム

- `GET /api/ai/stream`（アラート）と `GET /api/live-events/stream`（Webhook のイベント、`live.sse.enabled`）はサーバー送信イベントで、読み取り専用、初期状態は無効です。[AI_ALERTS_jpn.md](AI_ALERTS_jpn.md) と [WEBHOOK_jpn.md](WEBHOOK_jpn.md) を参照してください。
- `POST /api/chatops/slack` と `POST /api/chatops/discord` は、チャットからの読み取り専用コマンドを受け取ります(既定ではオフ、`chatops.enabled`)。アクセストークンは使わず、プラットフォームの署名が証明です。有効な署名のないリクエストは、何も読まれる前に拒否されます。[CHATOPS_jpn.md](CHATOPS_jpn.md) を参照。
