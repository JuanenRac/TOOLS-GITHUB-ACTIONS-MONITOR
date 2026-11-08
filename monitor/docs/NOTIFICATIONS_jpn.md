<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](NOTIFICATIONS.md) | [🇪🇸 Español](NOTIFICATIONS_spa.md) | [🇫🇷 Français](NOTIFICATIONS_fra.md) | [🇮🇹 Italiano](NOTIFICATIONS_ita.md) | [🇩🇪 Deutsch](NOTIFICATIONS_deu.md) | [🇨🇳 简体中文](NOTIFICATIONS_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](NOTIFICATIONS_por.md)

# 通知

任意で**既定ではオフ**です。フィードのイベント(新しい赤、停止したビルド、署名待ちのビルド、接続の喪失、Webhook が伝えた失敗した実行)をチャットやデバイスに送れます。通知はリンク付きのメッセージにすぎず、GitHub 上で再実行・キャンセル・書き込みを行うことはありません。

## チャンネル

- `telegram`(ボット)、`discord` と `slack`(チャンネル Webhook)、`matrix`(ルーム)、`mqtt`(このコンピューター上のブローカー。ライトやビーコン用)、`http_local`(このコンピューター上のアドレスへの POST)。
- 各チャンネルには設定タブ(サブタブ「通知」)に個別のスイッチとテスト送信ボタンがあります。


## 安全性

- トークンや Webhook URL は設定に保存されません。環境変数の「名前」を設定し、値は送信の瞬間にだけ読み取られ、表示も記録もされません。
- `discord` は `discord.com` のみ、`slack` は `hooks.slack.com` のみ受け付け、`mqtt` と `http_local` は `127.0.0.1`、`localhost`、`[::1]` のみ受け付けます。
- コンピューターから出るメッセージは 1 時間に最大 `notify.max_per_hour` 件。送信に失敗しても数えて無視し、モニターは止まりません。


## アダプターの取り決め

- 一覧にないサービスへは、このコンピューター上に小さな受信プログラムを動かし、`http_local` をそこへ向けます。`Content-Type: application/json` の POST で次の本文を受け取ります:`{"kind": "red_new", "repo": "demo-repo", "text": "...", "url": "https://.../actions/runs/1"}`。
- `kind` は `red_new`、`red_fixed`、`stuck_new`、`pending_sign`、`release_due`、`rate_low`、`offline`、`online`、`alerts_up`、`workflow_failed` のいずれか。フィールドは追加のみです。2xx で応答してください。それ以外は失敗として数えます。
- `mqtt` は同じ JSON を `notify.channels.mqtt.topic` の QoS 0 メッセージのペイロードとして発行します。
