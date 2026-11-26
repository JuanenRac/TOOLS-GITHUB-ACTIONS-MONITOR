<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](EXTERNAL_CI.md) | [🇪🇸 Español](EXTERNAL_CI_spa.md) | [🇫🇷 Français](EXTERNAL_CI_fra.md) | [🇮🇹 Italiano](EXTERNAL_CI_ita.md) | [🇩🇪 Deutsch](EXTERNAL_CI_deu.md) | [🇨🇳 简体中文](EXTERNAL_CI_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](EXTERNAL_CI_por.md)

# 外部CIソース(読み取り専用)

GitHubにミラーしたリポジトリは別の場所でビルドされることがあります。モニターはBuildbot、GitLab CI、Jenkins、Azure Pipelinesを読み取り、Actionsと同じように失敗を表示します。読み取り(GET)のみで、起動・取消・書き込みはしません。CompleteとFull版。既定はオフ。

## 設定

`external_ci.enabled` をオンにし、`external_ci.sources` にソースごとに1行書きます(設定 > 外部CI)。`repo` は結果を表示する名前です。

```
buildbot;repo=my-mirror;url=https://buildbot.example.org;builders=linux+docs
gitlab;repo=my-mirror;url=https://gitlab.example.org;project=group/app;token_env=MY_GITLAB_VALUE
jenkins;repo=my-mirror;url=https://jenkins.example.org;job=folder/app;branch=main
azure;repo=my-mirror;url=https://dev.azure.com/my-org;project=my-project
```

## 赤、正常、低下

Actionsと同様に、各ビルダー・パイプライン・ジョブのブランチ上で最後に完了したビルドで判定します。マージリクエストや取消・スキップ・不明の状態は判定しません。応答がない、内容が異なる、ビルダーがないサービスは**低下**となり、赤にはしません。以前の失敗は古い情報として残します。失敗は `ci.external.red`(レベル `external_ci.alert.level`)となり、Actionsの赤と同様に集計・通知・ミュートできます。`ci.external.degraded` は情報です。ミュートしてもセキュリティ警告は消えません。各ソースの読み取りは `external_ci.refresh_seconds`(300以上)に1回までで、`external_ci.breaker.failures` 回失敗すると間隔を延ばします。

## 安全性

接続時にアドレスを確認し、`external_ci.allow_private_targets` がオフならこのPC、プライベートネットワーク、クラウドメタデータを拒否します。リダイレクトや応答内のリンクは追いません。応答は `external_ci.max_bytes` と `external_ci.timeout_s` で制限します。認証情報は設定に書きません。`token_env` は環境変数の名前だけです(GitLab: 読み取りトークン、Jenkins: `user:token`、Azure: Build読み取りの個人トークン)。TLSなしで公開アドレスには送りません。GitHubの利用枠は使いません。オフラインモード(`airgapped`)では何も読みません。`doctor --egress` がホストを表示します。

## 失敗ビルドのログ

既定はオフ(`external_ci.logs.enabled`)。末尾のみを取得し、`external_ci.logs.max_kb` と `external_ci.logs.tail_lines` で制限、端末制御文字を除去して伏せ字処理し、`external_ci.logs.keep_hours` の間メモリに保持します。信頼できないテキストであり、AIへの指示にはしません。伏せ字処理はすべての秘密を認識できるわけではありません。

## テスト、状態、コマンドライン

設定 > 外部CI の**接続テスト**は保存せず1回読み取ります(`POST /api/external-ci/probe`)。センチネルのCIタブに各ソースが表示されます。`GET /api/external-ci/status` で同じ情報、`GET /api/external-ci/log` でログを取得します。コマンド: `external-ci list`、`external-ci status`(赤か低下があれば終了コード1)、`external-ci probe --source "行"`。

## 未検証

4つのアダプターは模擬サーバー(`tools/extci_fake_servers.py`)でのみ検証しています。JenkinsとAzure Pipelinesには**実験的**ラベル(`external_ci.experimental`)があり、`external_ci.jenkins.enabled` / `external_ci.azure.enabled` が必要です。別のアダプターは `integrations/external_ci/adapters.py` に関数 `(reader, source, cfg) -> (runs, missing)` を書き、`reader` 経由でのみ読み取ります。
