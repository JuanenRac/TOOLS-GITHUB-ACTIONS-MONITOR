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

- `docs/schemas/api_contract.json` は、各版の読み取りエンドポイントのキーと型、およびエラーコードを列挙します。読み取れるが固定されていないルート（ストリーム、テキスト、他のツール向けのエクスポート）は同じファイルの `unfrozen` に理由つきで列挙されています。実行・リポジトリ・割り当てを返す `/api/data` は固定されています。
- `python tools/check_api_contract.py` は動作中のモニターをこれに照らして検査し（`--lite`、`--url`、`--token-file`）、`CONTRACT=PASS` または `CONTRACT=FAIL` を出力します。モニターやクライアントを更新するたびに実行してください。

## ストリーム

- `GET /api/ai/stream`（アラート）と `GET /api/live-events/stream`（Webhook のイベント、`live.sse.enabled`）はサーバー送信イベントで、読み取り専用、初期状態は無効です。[AI_ALERTS_jpn.md](AI_ALERTS_jpn.md) と [WEBHOOK_jpn.md](WEBHOOK_jpn.md) を参照してください。
