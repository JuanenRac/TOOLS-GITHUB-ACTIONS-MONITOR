<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](FLEET_APIS.md) | [🇪🇸 Español](FLEET_APIS_spa.md) | [🇫🇷 Français](FLEET_APIS_fra.md) | [🇮🇹 Italiano](FLEET_APIS_ita.md) | [🇩🇪 Deutsch](FLEET_APIS_deu.md) | [🇨🇳 简体中文](FLEET_APIS_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](FLEET_APIS_por.md)

# 役割とグループ別のフリート、読み取り API とデモサイト

## 役割とグループ

フリートタブの末尾に、各グループ（エコシステム）の最悪状態と専用画面 `/g/<キー>` へのリンク、ワークフローの役割ごとの列（`fleet.roles`）を表示します。未読取は `不明` で、正常扱いしません。

## 無効化

`fleet.disabled` には名前、パターン、`group:<キー>` を指定できます。再起動せず次のサイクルから読み取りを止めます。Complete と Full 版。

## 読み取り API

`GET /api/fleet/columns` `GET /api/fleet/group?slug=` `GET /api/cctray.xml` `GET /api/cctray.json` `GET /api/security/secrets` `GET /api/security/code-scanning`。すべて読み取り専用で、他と同じアクセス確認を行います。バージョン付き API が有効なら `/api/v1/` でも利用できます。`fleet.cctray` は CCTray フィード、`fleet.security_api` はリポジトリごとのシークレットとコードのアラート件数（シークレット自体は含まず、読めなかった対象は明記）を提供します。どちらも既定はオフ。

## レポートのダイジェスト

レポートと AI ブリーフに `report_digest`（事実、モニターの版、ルールの版、判定の SHA-256）が付きます。同じ値なら同じ内容です。署名ではありません。

## デモサイト

デモの静的コピー（架空データ、ログインも操作もなく、外部への要求もなし）と、Pyodide でブラウザ内で動くワークフロー検査（何も送信しません）を作ります。

```
python tools/make_public_demo.py demo-site
```

*Demo site* ワークフローは成果物として保持します。公開はリポジトリ所有者の別の判断で、自動では公開しません。ブラウザ検査は公開サイトでは未検証です。

## すべての設定

`fleet.disabled` `fleet.roles` `fleet.cctray` `fleet.security_api`
