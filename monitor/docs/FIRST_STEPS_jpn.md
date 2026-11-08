<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](FIRST_STEPS.md) | [🇪🇸 Español](FIRST_STEPS_spa.md) | [🇫🇷 Français](FIRST_STEPS_fra.md) | [🇮🇹 Italiano](FIRST_STEPS_ita.md) | [🇩🇪 Deutsch](FIRST_STEPS_deu.md) | [🇨🇳 简体中文](FIRST_STEPS_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](FIRST_STEPS_por.md)

# 最初の5分間

**1. 必要なものを入れる。** Python 3.11 以上と GitHub CLI（`gh`）。その後一度ログインします: `gh auth login`。モニターはトークンを保存せず、`gh` に問い合わせます（設定 > 詳細設定でモニターの任意トークンをオンにした場合を除く）。

**2. 1つのコマンドで全部確認。** `python actions_monitor.py --doctor` は、問題ごとに直すための正確なコマンドを表示します。先に様子を見たい場合は `python actions_monitor.py --demo`。架空のデータでページが開き、`gh`・ログイン・ネットワークは不要です。

**3. 起動する。** シンプル版（ポート 8766）は `MONITOR_LITE_GITHUB_ACTIONS`、センチネル付きのフル版（ポート 8765）は `MONITOR_GITHUB_ACTIONS` をダブルクリックします。コンソールウィンドウのタイトルと1行目にどちらの版かが表示されます。

**4. ウェルカムの3ステップに従う。** 初回はページが動作の説明、アカウントで見つかった内容、基本設定への案内を表示します。既定では何も隠さず、どのグループにも属さないリポジトリは「未分類」として表示されます。

**5. ヘルプの場所を知る。** 丸い **?** ボタン（またはキー `?`）でヘルプ、**i** ボタンでバージョン情報が開き、バージョン、ファイル、サポート用情報をコピーするボタン（秘密情報は含まれません）があります。コンソールでは `--help-topics`、`--help-search 単語`、`--about`。

**知っておくとよいこと。** プライベートリポジトリのあるプランを使う場合は、設定 > 基本で選ぶとクォータが表示されます（[クォータとプラン](QUOTAS_jpn.md)）。センチネルについては [センチネル](SENTINEL_jpn.md) を参照してください。このツールは GitHub を読み取るだけで、確認した後にだけ書き込みます。
