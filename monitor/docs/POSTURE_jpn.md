<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](POSTURE.md) | [🇪🇸 Español](POSTURE_spa.md) | [🇫🇷 Français](POSTURE_fra.md) | [🇮🇹 Italiano](POSTURE_ita.md) | [🇩🇪 Deutsch](POSTURE_deu.md) | [🇨🇳 简体中文](POSTURE_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](POSTURE_por.md)

# リポジトリと組織のセキュリティ体制

リポジトリと組織の保護状況を読み取り専用で確認します。Webhook、Actionsの設定、スキャン、ブランチ、デプロイキー、シークレットの経過日数、アプリ、リリース。GitHubは一切変更しません。CompleteとFull版。既定はオフ。

## 有効化

`posture.enabled` をオンにします(設定 > セキュリティ体制)。1サイクルで少数のリポジトリ(`posture.repos_per_cycle`)を、各 `posture.refresh_hours` に1回まで読みます。GitHubの利用枠を消費します。`posture.org_checks` で組織も確認します。

## 確認内容

各指摘にはOWASP CI/CDトップ10とCISソフトウェアサプライチェーンガイドでの位置を示します。対応表は読むための手がかりで、認証ではありません。

| 領域 | 識別子 |
|---|---|
| Webhook配信 | webhook.no_secret webhook.plain_http webhook.tls_off |
| Actionsの設定 | actions.token_write actions.approves_prs actions.all_allowed actions.sha_not_required actions.fork_approval |
| コードと依存関係 | scan.no_code scan.no_credentials scan.no_push_protection scan.no_dependency_alerts repo.no_policy repo.no_update_tool |
| ブランチ | branch.unprotected branch.no_review branch.bypass branch.release_unprotected branch.merged_unreviewed |
| 鍵とシークレット | deploy.write deploy.old stored.old |
| 組織 | org.no_two_factor org.default_write org.public_creation org.app_broad org.settings_changed org.pat_broad |
| ランナー | runner.not_hardened runner.coverage_lost |
| リリース | release.asset_replaced release.asset_removed release.tag_moved release.outside_window |

## 正直な網羅性

GitHubが拒否・無応答のものは**未確認**と表示し、正常とは扱いません。その領域の以前の指摘は残ります。多くの設定には管理者の読み取り権限が必要で、レポートはグループごとの権限と拒否されたものを示します。Webhookはホスト名のみ、シークレットは名前と日付のみ保存します。リリースは以前の状態と比較するため、初回は記録のみです。アーカイブとフォークは対象外です。

## 基準とオプション

`posture.profile` は basic か strict。`posture.types` はパターンに種別(`standard`、`library`、`internal`、`sandbox`)と基準を割り当て、`posture.skip` で項目を除外します。`posture.release_branches` は保護すべきブランチのパターン。`posture.deploy_max_days` と `posture.stored_max_days` は期限です。指定した場合のみ: `posture.audit_log`(組織の監査ログ、GitHub Enterprise)、`posture.review_sample`(承認なしのマージ)、`posture.runner_runs`(実際に実行された強化ステップ)。`posture.releases` は差し替えとタグ移動を監視し、`posture.release_window` は公開時間帯を定めます。

## 表示場所

センチネルのセキュリティタブに指摘、各リポジトリの成熟度、日ごとの履歴、権限を表示します。`posture.alerts` で各指摘をアラートに出し、ミュートできます。API: `GET /api/posture`。コマンドライン:

```
posture status
posture matrix
posture check --repo-name my-repo
posture report
```

## 制限

未対応：書き込み用の2つ目の GitHub App（読み取りと書き込みは2つの App に分かれていません）。`org.pat_broad` には個人アクセストークンの権限を持つ GitHub App が必要で、個人トークンでは未確認になります。組織の確認は架空の応答でのみテストしています。

## 準拠レポートと権限

`posture report`（および `GET /api/posture` の `compliance`）は、指摘を OWASP の CI/CD リスク10項目と対応する CIS の節に照らして示します。指摘あり、指摘なし、一部のみ読取、未確認の区分と、各リスクの意味の短い説明、1週間前との傾向を出します。読解の補助であり認証ではありません。CIS の節番号は公式文書と照合していません。`original.weak`（`posture.upstream`、既定はオフ）は、公開元にセキュリティポリシーや更新ツールがないフォークを記録します。権限の表は各グループを解放する GitHub App の権限と、App 設定時は付与の有無を示します。
