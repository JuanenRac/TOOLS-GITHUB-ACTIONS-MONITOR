<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AUDIT_LOG.md) | [🇪🇸 Español](AUDIT_LOG_spa.md) | [🇫🇷 Français](AUDIT_LOG_fra.md) | [🇮🇹 Italiano](AUDIT_LOG_ita.md) | [🇩🇪 Deutsch](AUDIT_LOG_deu.md) | [🇨🇳 简体中文](AUDIT_LOG_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](AUDIT_LOG_por.md)

# 操作ログ

Complete のみ、初期状態はオンです。アクセスの監査（ログイン、ロック、拒否）とは別に、モニターは **操作** のログを保持します。誰が、いつ、どのアカウントで何を変更したかです。設定の変更、サイレンスとその解除、ユーザー・パスワード・通知設定・認証情報の変更が対象です。1 件ごとに 1 行の JSON として `logs/audit_actions.jsonl` に追記され、書き換えられることはありません。

## 1 行の内容

`at`、`action`（`settings_change` や `alert_mute` のような単純な語）、`user`、`role`、`account`、`target`（設定名やアラートコードなどの短い識別子）、`result`（`ok`、`denied`、`error`）、必要に応じて `details`。**値や秘密は決して書かれません**。設定の変更では設定の名前のみを書き、値は書きません。名前が秘密らしく見えるキー（token、password、key、cookie、authorization、session など）は除外され、すべてのテキストは AI 向けのメモと同じ方法でクリーニングされ、200 文字に切り詰められます。

## ハッシュの連鎖

各行は `prev`（直前の行のハッシュ）と `hash`（その行自身と `prev` のハッシュ）を持ちます。後から変更・削除・挿入された行は連鎖を壊し、`GET /api/audit-log` がその位置（`chain.broken_at`）を示します。`audit_log.max_mb` を超えると古い部分は `audit_actions.jsonl.1` として保持され、連鎖は新しいファイルで続きます。連鎖は改ざんを示しますが、ファイルにアクセスできる人が全体を削除することは防げません。重要な場所にコピーを保管してください。

## 読める人

管理者（チームモードがない場合はコンピューターの前にいる人）。メンテナーは `audit_log.maintainers_can_read` がオンのときだけ読めます。それ以外の人は読めません。`GET /api/audit-log` は直近 200 行と連鎖の状態を返します。Lite にはありません。

## 設定

設定、センチネルタブ、ブロック **操作ログ**：`audit_log.enabled`（オン）、`audit_log.max_mb`（10）、`audit_log.maintainers_can_read`（オフ）。
