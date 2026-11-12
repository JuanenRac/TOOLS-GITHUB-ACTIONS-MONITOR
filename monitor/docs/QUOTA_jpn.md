<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](QUOTA.md) | [🇪🇸 Español](QUOTA_spa.md) | [🇫🇷 Français](QUOTA_fra.md) | [🇮🇹 Italiano](QUOTA_ita.md) | [🇩🇪 Deutsch](QUOTA_deu.md) | [🇨🇳 简体中文](QUOTA_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](QUOTA_por.md)

# クォータを増やし、消費を減らす

GitHub はアカウントごとに**API 呼び出しの限られたクォータ**を与え、それを使うすべてのツールで共有します。このガイドでは仕組みと、モニターが消費を減らすすべての方法を説明します。

## クォータの仕組み
- **REST**:ユーザーあたり 1 時間 5000 回(ログインなしは 60 回)。**GraphQL** には別のクォータがあります。Actions のワークフローの `GITHUB_TOKEN` にも独自のクォータがあります。**GitHub App** にはあなたのものとは別の独自クォータがあり、インストールされたリポジトリが多いほど増えます(130 リポジトリで 1 時間あたり約 10 000 回)。
- 数えられるもの・数えられないもの:`304 Not Modified`(ETag)を返す条件付き読み取りは数えられません。`rate_limit` の取得は無料です。`git push`、`git fetch`、`git clone` は API を使いません。

## モニターが節約する方法
1. **条件付き読み取り**(ETag と `304`):`cache.etag.enabled`(既定でオン)。節約できた読み取り数をページに表示します。
2. **節約モード**:アクティブなリポジトリだけを 4 分ごと、その他を 30 分ごと。`modes.auto_low`(オン)は残り 1000 回未満で入り、2500 回超または更新で戻ります。プリセットは `modes.low`。バーに数値が古い可能性とその経過時間が表示されます。
3. **ベースラインとしての中央パネル**:`central.source`(`off`、`git`、`http`)は、ワークフローが独自のトークンで更新するプロフィールリポジトリの `data/sentinel.json` を読みます。あなたのクォータは消費しません。`central.max_age_minutes`(120)より古いと「遅延」とされ、信頼されません。
4. **クォータ切れは 1 つの通知に**:更新まで読み取りを止め、ページは「クォータは HH:MM まで使い切り」と 1 回だけ表示し(リポジトリごとのエラーではなく)、自動で再開します。
5. **読み取り用の GitHub App**(`github_app.*`)、下記。
GraphQL はワークフローの run には使いません。提供されていないためです。

## GitHub App の手順
1. GitHub で *Settings*、*Developer settings*、*GitHub Apps*、*New GitHub App*。Webhook は不要。**読み取り専用**の権限:Actions、Checks、Code scanning alerts、Commit statuses、Contents、Dependabot alerts、Issues、Pull requests、Secret scanning alerts、Metadata。
2. *Generate a private key* で、`.pem` を**どのリポジトリの外**にも置き、自分だけが読めるようにします。
3. *Install App* でアカウントの監視したい全リポジトリにインストールします。
4. モニターで `github_app.enabled` をオン、`github_app.app_id`(App の番号)と `github_app.key_path`(鍵の**パスのみ**)を設定します。`github_app.installation_id` は空で構いません。
5. `GET /api/github-app/status`(このコンピューターのみ)で確認します。App の名前、インストール、付与された権限、クォータを表示し、鍵やトークンは表示しません。doctor は `openssl`、鍵ファイル、その権限を確認します。

セキュリティ:モニターは鍵を読み取ったり、コピー、表示、記録したりしません。パスを `openssl` に渡し、最長 10 分の JWT に署名させます。インストールトークンは 1 時間有効でメモリに保持され、5 分前に更新されます。**読み取りだけ**がこれを使い、書き込みとアクションはあなたのトークンを使い続けます。App が失敗したり権限が足りない場合は、あなたのトークンで読み取りをやり直します。ページには 2 つのクォータが表示されます。

## 複数のツールが同じクォータを共有するとき
アカウントのすべてのツールが同じ 1 時間 5000 回を消費します。良いパターン:数分間の**共有キャッシュ**を持つ小さな `gh` ラッパー、**予約分**(残りが約 1000 回未満なら緊急以外は呼び出しを拒否)、新鮮なデータが必要な作業は**更新の直後**に行うこと、そして `gh run watch` は使わないこと(ポーリングするため)。たとえば、各読み取りの応答をコマンド名の一時ファイルに保存して 120 秒間再利用し、他の呼び出しの前に `gh api rate_limit` を確認するラッパーです。

## してはいけないこと
制限を回避するために、同じユーザーの複数のアカウントや複数のトークンを使わないでください。GitHub の規約に反し、アカウントがブロックされる可能性があります。App、中央パネル、節約モードを使ってください。

## 設定
| 設定 | 既定 |
|---|---|
| `cache.etag.enabled` | オン |
| `modes.auto_low` / `modes.auto_low_enter` / `modes.auto_low_exit` | オン / 1000 / 2500 |
| `modes.low.*`(`refresh_seconds`、`cold_refresh_seconds`、`runs_per_repo`、`hot_hours`) | 240 / 1800 / 10 / 2 |
| `min_rate_remaining` | 800 |
| `central.source` / `central.max_age_minutes` | off / 120 |
| `github_app.enabled` / `github_app.app_id` / `github_app.key_path` / `github_app.installation_id` | off / 空 / 空 / 空 |

## トラブルシューティングと FAQ
- *「クォータは HH:MM まで使い切り」*:待ってください。モニターは自動で再開します。他のツールが消費している可能性があります。
- *数値が古い*:節約モードが有効です(選択または自動)。バーに表示されます。
- *App が動かない*:`/api/github-app/status` と doctor(openssl、鍵のパス、権限)を確認してください。
- *`git fetch` はクォータを消費しますか?* いいえ。[QUOTAS_jpn.md](QUOTAS_jpn.md)(プランと分)と [MODES_jpn.md](MODES_jpn.md) も参照してください。

## 「クォータ」タブと 2 つ目のアカウント
クォータに関することはすべて 1 か所にあります:*設定*の*クォータ*タブ。モード(`modes.auto_low`、`modes.auto_low_enter`、`modes.auto_low_exit`、`modes.low.*` の節約モードの値)、節約(`network.etag`、`cache.etag.enabled` と併用)、中央パネル(`central.source`、`central.max_age_minutes`)、GitHub App(`github_app.*`)、そして**読み取り用の 2 つ目のアカウント**をまとめています。タブのボタンは、各ソース(あなたのログイン、App、2 つ目のアカウント)のクォータと更新時刻を表示し、App と 2 つ目のアカウントをテストし、App に不足している権限を一覧し、推奨値または既定値を適用します。

2 つ目のアカウント(`extra_reader.enabled`、`extra_reader.file`)は読み取り専用で、そのファイングレイン トークンはリポジトリの外のテキストファイルにあり、あなただけが読めます。設定にはそのファイルの**パスだけ**が入ります。モニターは使用時にトークンを読み取り、メモリに保持し、保存・表示・記録は一切しません。読み取りは、各ソースの残り回数(無料の `rate_limit` 呼び出しの値から、その後の読み取りを引いた数)に応じて、あなたのログイン、App、2 つ目のアカウントに分散されます。拒否されたソースは 5 分間除外され、読み取りは次のソースでやり直されます。書き込みとアクションでは使いません。これはあなた自身のアカウント(たとえばリポジトリへの読み取りアクセスを持つ自分の 2 つ目のアカウント)用であり、他人のアカウントで制限を回避するためのものではありません。
