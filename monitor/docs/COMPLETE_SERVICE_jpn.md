<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_SERVICE.md) | [🇪🇸 Español](COMPLETE_SERVICE_spa.md) | [🇫🇷 Français](COMPLETE_SERVICE_fra.md) | [🇮🇹 Italiano](COMPLETE_SERVICE_ita.md) | [🇩🇪 Deutsch](COMPLETE_SERVICE_deu.md) | [🇨🇳 简体中文](COMPLETE_SERVICE_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](COMPLETE_SERVICE_por.md)

# サービスとしての完全版

サーバーやコンテナで常時動かし、他の人や他のプログラムが読むモニター向けです。ここでは選択肢の要約だけを示します。詳細、コマンド、変数の表は [DEPLOYMENT_jpn.md](DEPLOYMENT_jpn.md) にあります。

## 待ち受け方

- 三通りです。このパソコンだけ（初期状態、ログインなし）、ネットワーク（`listen.network` を有効にし、`listen.host` を指定し、全リクエストにアクセストークンを付ける）、またはプロキシの背後（`listen.proxy_public_host`、`listen.secure_cookie`、`listen.trusted_proxy`）。
- ネットワークモードの前には HTTPS（証明書またはプロキシ）か VPN を置いてください。平文の HTTP ではトークンとパスワードがそのまま流れます。

## 動かし方

- 公式イメージ、任意のプロキシ付き Docker Compose、または systemd による従来のインストール。いずれもブラウザなしで `python -m github_actions_monitor.service` を起動します。
- ポートは完全版が 8765、簡易版が 8766 です（`ports.complete`、`ports.lite`）。

## 見守る

- `GET /api/health` は GitHub を呼びません。更新サイクルが止まると `GET /api/health?deep=1` は 503 を返し、`python -m github_actions_monitor.cli.healthcheck` はコンテナやサービスマネージャーのためにその呼び出しを行います。
- GitHub がログインを失効させたら、コマンドライン、管理者用エンドポイント、または `SIGHUP` で資格情報を入れ替えます。再起動では失ったログインは直りません。

## 数か月の運用

- [STORAGE_jpn.md](STORAGE_jpn.md) でファイルか SQLite と保持期間を選び、更新の前にバックアップを取り、[MIGRATING_jpn.md](MIGRATING_jpn.md) を読んでください。
- ログインする人がいる場合のチームモードは [COMPLETE_TEAM_jpn.md](COMPLETE_TEAM_jpn.md)、プログラムが頼れる契約は [API_jpn.md](API_jpn.md) にあります。
