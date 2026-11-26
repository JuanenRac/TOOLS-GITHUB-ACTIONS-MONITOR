<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COLLABORATION.md) | [🇪🇸 Español](COLLABORATION_spa.md) | [🇫🇷 Français](COLLABORATION_fra.md) | [🇮🇹 Italiano](COLLABORATION_ita.md) | [🇩🇪 Deutsch](COLLABORATION_deu.md) | [🇨🇳 简体中文](COLLABORATION_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](COLLABORATION_por.md)

# 共同作業の表示と任意の操作

誰かを待っているものの表示と、許可するまでオフのままのいくつかの GitHub 操作です。Complete と Full 版。

## 有効化

`actions.enabled`（設定 > 共同作業）をオンにします。実行の表示はモニターが既に読んでいる内容から作り、プルリクエスト、アラート、ワークフローは1サイクルに少数のリポジトリずつ読みます（`actions.repos_per_cycle`、`actions.refresh_hours`）。ボックスはセンチネル領域の共同作業タブの末尾にあります。

## 表示

人の対応待ち（環境の承認、フォークのワークフロー、対応が必要）とランナー待ちを分けます。レーン（ワークフローとブランチ）ごとの最新実行。赤は `actions.dismiss_days` 日だけ保留でき（その実行のみ）、戻せます。未マージのプルリクエストはマージ可能、ベースより遅れ、対応が必要、不明に分類し、ボットの更新は作者・ブランチ・ラベルで判別します。`actions.hide_workflows` でワークフローを隠します。重大・高の依存関係アラートがあるリポジトリと最古の経過日数、読めなかったリポジトリを名前で示します。`actions.dismissed_alerts` で却下者を表示し、`actions.dismiss_allowed` にない人の却下はアラートになります。

## GitHub への書き込み

`github_actions.enabled` がオンで、操作が `github_actions.allowed` にあり、送信内容を示す計画を確認した場合だけ書き込みます。新しい操作：`update_branch`, `approve_fork`, `approve_deployment`, `force_cancel`, `enable_workflow`, `dispatch`。表示は提案のみです：失敗したボット更新、遅れたブランチ、長時間の待機や実行（`actions.queued_hours`、`actions.stuck_hours`）、`actions.cancel_policy` に一致する実行、非アクティブで無効化されたワークフロー（`actions.inactive_workflows`）。手動ワークフローのフォームは入力を読み取って検査します。`actions.forks_help` はフォーク実行の作者の事実を示し、判定はしません。

## 唯一の自動操作

`actions.auto_rerun`（既定はオフ）は、開始できなかった、または時間切れの実行の失敗ジョブを同じ検査のもとで1回だけ再実行します。2回目は行わず、再び失敗するとアラートになります。

## 自己ホストランナーのフック

`actions.runner_hooks` を有効にすると、このコンピューター上のランナーのフックがジョブの開始と終了を記録します。

```
# ACTIONS_RUNNER_HOOK_JOB_STARTED
python /path/to/monitor/bin/monitor_cli.py runner-hook started
```

終了には ACTIONS_RUNNER_HOOK_JOB_COMPLETED と `completed` を使います。別のコンピューターのランナーは対象外です。

## API とコマンドライン

`GET /api/actions/state`, `GET /api/actions/dispatch-form`, `GET /api/actions/environments`, `GET /api/actions/fork-facts`, `POST /api/actions/plan`, `POST /api/actions/dismiss`。

```
python bin/monitor_cli.py actions status
python bin/monitor_cli.py actions proposals
python bin/monitor_cli.py runner-hook started
python bin/monitor_cli.py runner-hook completed
```

## 未検証

読み取りと書き込みは架空の応答でのみテストしています。新しい操作は実際のリポジトリで実行していません。

## すべての設定

`actions.enabled` `actions.repos_per_cycle` `actions.refresh_hours` `actions.dismiss_days` `actions.hide_workflows` `actions.bot_authors` `actions.bot_branches` `actions.bot_labels` `actions.dismissed_alerts` `actions.dismiss_allowed` `actions.auto_rerun` `actions.cancel_policy` `actions.queued_hours` `actions.stuck_hours` `actions.forks_help` `actions.inactive_workflows` `actions.runner_hooks`
