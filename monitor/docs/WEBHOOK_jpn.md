<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](WEBHOOK.md) | [🇪🇸 Español](WEBHOOK_spa.md) | [🇫🇷 Français](WEBHOOK_fra.md) | [🇮🇹 Italiano](WEBHOOK_ita.md) | [🇩🇪 Deutsch](WEBHOOK_deu.md) | [🇨🇳 简体中文](WEBHOOK_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](WEBHOOK_por.md)

# 受信 Webhook

任意の機能で、**既定ではオフ**です。GitHub から変更をモニターに知らせ、次の問い合わせを待たずに次のサイクルでリポジトリを更新できます。

## 動作(更新のみ)

受け付けたイベントは、そこに書かれたリポジトリを次のサイクルで更新するようにマークするだけです。GitHub にもディスクにも何も書き込まず、イベントの文面は保存も表示もされず、モニターがすでに監視しているリポジトリだけが受け付けられます。扱うイベント:`workflow_run`、`workflow_job`、`push`、`release`、`check_suite`、`ping`。それ以外は `202` を返して無視します。

## 安全性

- モニターは引き続き `127.0.0.1` だけで待ち受けます。GitHub からは、あなたが意図して用意したトンネル経由でのみ届きます。ツールがトンネルを開くことはありません。
- `webhook.enabled` がオンで、かつ `actions_monitor.json` の共有シークレットが 32 文字以上になるまでオフです(それまでエンドポイントは閉じたままです)。
- すべてのリクエストにそのシークレットで作った `X-Hub-Signature-256: sha256=<hmac>` が必要で、それ以外は `401` です。シークレットは表示されず、設定タブは設定済みかどうかだけを示します。
- 256 KB を超える本文は `413` です。

## オンにするには

`actions_monitor.json` に `"webhook": {"enabled": true, "secret": "<32 文字以上のランダムな文字列>"}` と書きます。スイッチは設定タブ(サブタブ「受信 Webhook」)にもありますが、シークレットはファイルにだけ置きます。モニターを再起動し、GitHub の Webhook 設定では、コンテンツタイプ `application/json`、同じシークレット、末尾が `/api/webhook` のトンネル URL を指定します。
