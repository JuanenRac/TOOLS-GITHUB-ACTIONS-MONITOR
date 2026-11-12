<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COLLAB.md) | [🇪🇸 Español](COLLAB_spa.md) | [🇫🇷 Français](COLLAB_fra.md) | [🇮🇹 Italiano](COLLAB_ita.md) | [🇩🇪 Deutsch](COLLAB_deu.md) | [🇨🇳 简体中文](COLLAB_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](COLLAB_por.md)

# Collab 番人：Issue とプルリクエスト

CI 番人の隣にある 2 つ目の番人です。リポジトリの**未解決の Issue とプルリクエスト**を見て、人の手が必要なものを知らせます。放置された Issue、重大なラベル、誰もしないレビュー、終わらない下書き、残り続けるコンフリクトなどです。独自の周期で動き、CI 番人の判断を変えることはなく、**GitHub には一切書き込みません**。完全版の機能で、Lite 版は読み込みません。

## 有効にする

初期状態ではオフです。設定 > 番人 > Issue とプルリクエスト、または `actions_monitor.json` で設定します。

```
"sentinels": {"collab": {"enabled": true, "refresh_seconds": 600, "max_repos_per_tick": 10, "repos": "all",
  "rules": {"issue_stale_days": 14, "issue_critical_labels": ["security", "critical"], "pr_review_pending_days": 3,
            "pr_draft_max_days": 30, "pr_conflict_days": 7, "watch_external_comments": false, "ignore_labels": ["monitor:ignore"]}}}
```

`repos` は `"all"`、リポジトリの一覧、または `{"ecosystems": [...]}` です。

## ルール（安定したコード）

| コード | レベル | 条件 |
|---|---|---|
| `collab.issue.stale` | 警告 | 未解決の Issue が `issue_stale_days` の間動いていない |
| `collab.issue.critical` | エラー | 未解決の Issue に `issue_critical_labels` のラベルが付いている（経過日数に関係なく） |
| `collab.issue.external` | 警告 | （`watch_external_comments` が有効なときのみ）チーム外の人の Issue に 1 日経っても誰も返信していない |
| `collab.pr.review_pending` | 警告 | レビュー依頼中のプルリクエストが `pr_review_pending_days` の間待たされている |
| `collab.pr.draft_old` | 情報 | 下書きのプルリクエストが `pr_draft_max_days` の間開いたまま |
| `collab.pr.conflict` | 警告 | プルリクエストが `pr_conflict_days` の間コンフリクトしている |

ボットは対象外です。初期値は意図的にゆったりしています。数か月待つ下書きは多くのチームで普通だからです。

## コスト

1 回の巡回で読むのは最大 `max_repos_per_tick` 個のリポジトリで、各 2 回の条件付きリクエスト（変化のないリポジトリは割り当てを消費しません）と、1 回あたり最大 6 件のプルリクエスト詳細です。割り当てが `min_rate_remaining` を下回る間は停止します。状態は `collab_state.json` に保存され（複数アカウントではそのアカウントのフォルダ内）、再起動しても同じ通知を繰り返しません。

## ノイズを減らす：無視とミュート

- **無視ラベル**：Issue やプルリクエストに、**GitHub 上で** `ignore_labels` のラベル（初期値は `monitor:ignore`）を付けると、Collab はそれに対するアラートを出しません。モニター自身がラベルを書くことはありません。
- **モニター内のミュート**：アラートタブで、各アラートに「このアラート」「そのルール」「番人全体」を `alerts.mute_hours` 時間（初期値 24、1〜720）ミュートするボタンがあります。自動で期限が切れ、いつでも元に戻せ、何をいつまでミュートしたかの短い履歴がタブに残ります。これはこのモニターのメモで、GitHub 上では何も変わりません。ネットワークモードでは、ミュートはモニターが動いているコンピューターからのみ設定・解除できます(`this_computer`)。ネットワーク上のクライアントはミュートを見られますが変更できません。これは後の版が独自のユーザーを持つまで続きます。1 件のアラートのミュートは「項目が変わるまで」にもできます(`POST /api/alerts/mute` のリクエストの `until_change`)。issue またはプルリクエストの `updated_at` が変わった時点、または指定時間が終わった時点の、早い方で終了します。

## 見る場所

- **アラート**タブ：すべての番人を 1 つの一覧にまとめ、由来（CI、Collab）とレベルで絞り込めます。ミュート中のものは希望すれば表示されます。
- 番人タブ：*Issue とプルリクエスト*の層。
- `GET /api/alerts?sentinel=collab&level=&muted=show|hide|only` と `GET /api/sentinel/collab`。イベントは `GET /api/events?sentinel=collab&since=`（`collab_new`、`collab_fixed`。通知チャンネルで選ぶと送信されます。NOTIFICATIONS を参照）。

## 制限

リポジトリごとに読むのは、最近更新された順の未解決 Issue 100 件と未解決プルリクエスト 100 件までです。Collab は何も提案せず、何も実行しません。Issue やプルリクエストへの操作は後の版で扱います。
