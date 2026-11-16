<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_INDIVIDUAL.md) | [🇪🇸 Español](COMPLETE_INDIVIDUAL_spa.md) | [🇫🇷 Français](COMPLETE_INDIVIDUAL_fra.md) | [🇮🇹 Italiano](COMPLETE_INDIVIDUAL_ita.md) | [🇩🇪 Deutsch](COMPLETE_INDIVIDUAL_deu.md) | [🇨🇳 简体中文](COMPLETE_INDIVIDUAL_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](COMPLETE_INDIVIDUAL_por.md)

# 一人で使う完全版

自分のパソコンで完全版を動かすのが、モニターの通常の使い方です。利用者は一人、GitHub アカウントは一つ、ログインは不要で、ページは `127.0.0.1` でだけ開きます。実行状況を見るだけでよい人向けの簡易版は [LITE_jpn.md](LITE_jpn.md) です。

## はじめに

- `gh auth login` で一度 GitHub にサインインし、`MONITOR_GITHUB_ACTIONS`（`.bat`、`.sh`、`.command`）を起動します。ページはポート 8765（`ports.complete`）で開きます。
- 設定で監視するリポジトリとエコシステムを選びます。最初の 5 分間は [FIRST_STEPS_jpn.md](FIRST_STEPS_jpn.md) にあります。

## 得られるもの

- 三つの番人（CI は有効、Collab と Security はオンにするまで無効）と、自分のパソコンからミュートできるアラートの一覧。
- アカウントのスコア、各リポジトリの健全性、定期レポート（初期状態は無効）、実行した操作のログ（初期状態は有効、`audit_log.enabled`）。
- 通常・高速・ターボの作業モード（[MODES_jpn.md](MODES_jpn.md)）と、枠が少ないときの低モード（[QUOTA_jpn.md](QUOTA_jpn.md)）。

## このパソコンだけで使う

- `auth.enabled` が無効（初期状態）ならユーザーはおらず、覚えることもありません。複数人で使うときだけチームモードを有効にします（[COMPLETE_TEAM_jpn.md](COMPLETE_TEAM_jpn.md)）。
- `listen.network` は初期状態で無効です。ページと API は `127.0.0.1` にしか応答しません。常時動かすには [COMPLETE_SERVICE_jpn.md](COMPLETE_SERVICE_jpn.md) を読んでください。

## 毎日の使い方

- `python bin/monitor_cli.py status`、`doctor`、`health` は動作中のモニターに問い合わせます（[CLI_jpn.md](CLI_jpn.md)）。更新するときは [MIGRATING_jpn.md](MIGRATING_jpn.md) を読んでください。
- 自分のスクリプトから API を読めます。変わらないと約束されている内容は [API_jpn.md](API_jpn.md) にあります。
