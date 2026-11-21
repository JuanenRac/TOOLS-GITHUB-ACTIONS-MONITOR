<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](API_V1.md) | [🇪🇸 Español](API_V1_spa.md) | [🇫🇷 Français](API_V1_fra.md) | [🇮🇹 Italiano](API_V1_ita.md) | [🇩🇪 Deutsch](API_V1_deu.md) | [🇨🇳 简体中文](API_V1_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](API_V1_por.md)

# 読み取り API v1 をステップごとに

モニターの読み取り API に対するクライアント(スクリプト、ウォールスクリーン、モバイルアプリ、AI ツール)を書く人のためのガイドです。各ルートのリファレンスはモニター自身が配信する OpenAPI ドキュメントで、契約のルール(何が凍結され、何が増えうるか)は [API_jpn.md](API_jpn.md) にあります。ここでは、テストがモニターに対して実行するコマンドとともに、たどる順序を示します。

## 1. API は開いていますか

モニターがサービスとして動いているとき(チームモードのアカウント、Docker イメージ、systemd ユニット)は、プレフィックス `/api/v1/` は自動で応答します。1台のコンピューターで1人が使う場合は閉じたままで 404 を返します。決めるのは設定 `api.v1_enabled`(`auto`、`on`、`off`)です。クライアントはまず自分が誰かを尋ねます。そこでの `404` は API が閉じているという意味で、クライアントが間違っているわけではありません。

## 2. 身元を示す

ネットワークモードを使わず同じコンピューターから呼ぶ場合、トークンは不要です。ネットワークモードでは、すべてのリクエストがヘッダー `X-Monitor-Access` にアクセストークンを付けます。履歴に残るコマンドラインに現れないよう、ここではファイルから読み込んでいます。チームモードではスクリプトが `POST /api/auth/login` でログインします。この API のクライアントに必要なのは読み取りのトークンだけで、プレフィックスの下に書き込みはありません。

## 3. コマンド

順に、自分が誰かと契約のバージョン(`/api/v1/me`)、凍結された全ルートの説明(`/api/v1/openapi.json`)、ページ分割されたリポジトリ(`state`、`ecosystem`、`q` で絞り込み、`limit`、より短い行にする `fields` または `profile=compact`、前のページの `next_cursor` を渡す `cursor`(`null` になるまで))、gzip 圧縮された応答、そして旧 API のうちプレフィックスでも同じ応答を返す2つのルートです。

```
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/me
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/openapi.json -o openapi.json
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?state=bad&limit=20&profile=compact"
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?fields=repo,state,risk&limit=5"
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=50&cursor=THE_NEXT_CURSOR"
curl -s --compressed -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=100"
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/health
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/alerts
```

## 4. エラー

独自ルートのエラーは3つのキーを持つ JSON オブジェクトです。`error` と `code` は安定していてプログラム向け、`message` は `?lang=` の言語に従い人間向けです。コードは api.bad_cursor、api.bad_limit、api.unknown_field、api.bad_profile、api.server_error です。エラーを含むプレフィックスのすべての応答に、ヘッダー `X-API-Version: 1` が付きます。 すべてのエラーには `help` も付きます。次の手順と読むべきガイドを同じ言語で一文にしたものです (コードによっては無く、無視するプログラムも何も失いません)。

```
curl -s -i -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=0"
```

ヘッダーの後の応答は次のとおりです `{"error": "bad_request", "code": "api.bad_limit", "message": "..."}`.

## 5. コマンドラインと AI ツールからも同じように

3つの入口が同じドキュメントを返し、テストがそれらを比較します。上記の HTTP、コマンドライン(`python bin/monitor_cli.py api me`、`api openapi`、`api contract-check`。`--json` で応答をデータとして取得)、そして MCP サーバー(`python bin/mcp_server.py`、読み取り専用:ツール `api_me`、`api_openapi`、`api_contract_check`)です。

## 6. 頼る前にサーバーを確認する

`python tools/api_contract_suite.py --url URL --token-file token.txt` は、サーバーが配信するドキュメントを検査内容の記述として使い、検査ごとに1行と `API_CONTRACT=PASS` または `API_CONTRACT=FAIL` を出力します。`python tools/check_api_contract.py --v1` は同じスイートを実行し、さらに応答を凍結された契約と比較します。モニターまたはクライアントを更新するたびにどちらかを実行してください。モニターの CI はサービスモードのデモに対してこのスイートを実行します。
