<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_TEAM.md) | [🇪🇸 Español](COMPLETE_TEAM_spa.md) | [🇫🇷 Français](COMPLETE_TEAM_fra.md) | [🇮🇹 Italiano](COMPLETE_TEAM_ita.md) | [🇩🇪 Deutsch](COMPLETE_TEAM_deu.md) | [🇨🇳 简体中文](COMPLETE_TEAM_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](COMPLETE_TEAM_por.md)

# チームで使う完全版

複数の人が同じモニターを読み、それぞれがログインとロールを持ちます。初期状態では無効（`auth.enabled`）で、簡易版にはありません。オプションの全一覧は [ADVANCED_jpn.md](ADVANCED_jpn.md) の「チームモード」の節にあります。

## 最初の手順

- `auth.enabled` を有効にしても、最初の管理者ができるまでは何も変わりません。モニターを動かしているパソコンで作成します（`/login` ページ、または `python -m github_actions_monitor.security.auth_cli create-admin`）。ネットワークモードでは管理者がいないとモニターは起動しません。
- ネットワーク越しでは HTTPS か VPN を使ってください。そうしないとセッション Cookie とパスワードが平文で流れます。

## ロール

- `viewer` は読み取り、`maintainer` は作業モードの変更に加え、モニターのパソコンからだけアラートのミュートと確認ができ、`admin` は設定とユーザーの変更もできます。
- 各ユーザーには割り当てられたアカウントだけが見えます（管理者は全部）。他のアカウントは 403 `account_scope` を返します。

## セッションとパスワード

- ブラウザは Cookie `monitor_session` と CSRF トークンを受け取ります。スクリプトは `POST /api/auth/login` でログインし、`auth.allow_bearer` が有効なときだけ `Authorization: Bearer` を送ります。
- パスワードはソルト付きハッシュで保存され、`auth.min_length` 文字が必要です。`auth.max_failed_logins` 回間違えると、そのユーザーは `auth.lockout_minutes` 分ロックされます。

## 誰が何をしたか

- 操作ログは誰が何を変えたかを記録します（[AUDIT_LOG_jpn.md](AUDIT_LOG_jpn.md)）。maintainer が読めるのは `audit_log.maintainers_can_read` が有効なときだけです。
- チームの健全性とアカウントごとのスコアは [HEALTH_jpn.md](HEALTH_jpn.md) と [SCORE_jpn.md](SCORE_jpn.md) にあります。常時動かすサーバーについては [COMPLETE_SERVICE_jpn.md](COMPLETE_SERVICE_jpn.md) を読んでください。
