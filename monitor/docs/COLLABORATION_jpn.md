<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COLLABORATION.md) | [🇪🇸 Español](COLLABORATION_spa.md) | [🇫🇷 Français](COLLABORATION_fra.md) | [🇮🇹 Italiano](COLLABORATION_ita.md) | [🇩🇪 Deutsch](COLLABORATION_deu.md) | [🇨🇳 简体中文](COLLABORATION_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](COLLABORATION_por.md)

# 共同作業の表示と任意の操作

誰かを待っているものの表示と、許可するまでオフのままのいくつかの GitHub 操作です。Complete と Full 版。

## 有効化

`teamwork.enabled`（設定 > 共同作業）をオンにします。実行の表示はモニターが既に読んでいる内容から作り、プルリクエスト、アラート、ワークフローは1サイクルに少数のリポジトリずつ読みます（`teamwork.repos_per_cycle`、`teamwork.refresh_hours`）。ボックスはセンチネル領域の共同作業タブの末尾にあります。

## 表示

人の対応待ち（環境の承認、フォークのワークフロー、対応が必要）とランナー待ちを分けます。レーン（ワークフローとブランチ）ごとの最新実行。赤は `teamwork.dismiss_days` 日だけ保留でき（その実行のみ）、戻せます。未マージのプルリクエストはマージ可能、ベースより遅れ、対応が必要、不明に分類し、ボットの更新は作者・ブランチ・ラベルで判別します。`teamwork.hide_workflows` でワークフローを隠します。重大・高の依存関係アラートがあるリポジトリと最古の経過日数、読めなかったリポジトリを名前で示します。`teamwork.dismissed_alerts` で却下者を表示し、`teamwork.dismiss_allowed` にない人の却下はアラートになります。

## GitHub への書き込み

`github_actions.enabled` がオンで、操作が `github_actions.allowed` にあり、送信内容を示す計画を確認した場合だけ書き込みます。新しい操作：`update_branch`, `approve_fork`, `approve_deployment`, `force_cancel`, `enable_workflow`, `dispatch`。表示は提案のみです：失敗したボット更新、遅れたブランチ、長時間の待機や実行（`teamwork.queued_hours`、`teamwork.stuck_hours`）、`teamwork.cancel_policy` に一致する実行、非アクティブで無効化されたワークフロー（`teamwork.inactive_workflows`）。手動ワークフローのフォームは入力を読み取って検査します。`teamwork.forks_help` はフォーク実行の作者の事実を示し、判定はしません。

## 唯一の自動操作

`teamwork.auto_rerun`（既定はオフ）は、開始できなかった、または時間切れの実行の失敗ジョブを同じ検査のもとで1回だけ再実行します。2回目は行わず、再び失敗するとアラートになります。

## スケジュールを維持する

GitHub は 60 日間活動のない公開リポジトリのスケジュール実行ワークフローを停止します。`teamwork.keep_alive_days`（0 = オフ。例: 45）を設定すると、その期間 push がなく、スケジュールで実行されたワークフローがある公開リポジトリが、残り日数とともに `enable_workflow` の提案として表示されます。ほかの提案と同じく、確認するまで何も送られません。有効なワークフローを有効化すると日数が数え直されることは GitHub の文書にはなく、実際のリポジトリでは試していません。確実な方法は新しいコミットです。

## 自己ホストランナーのフック

`teamwork.runner_hooks` を有効にすると、このコンピューター上のランナーのフックがジョブの開始と終了を記録します。

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

`teamwork.enabled` `teamwork.repos_per_cycle` `teamwork.refresh_hours` `teamwork.dismiss_days` `teamwork.hide_workflows` `teamwork.bot_authors` `teamwork.bot_branches` `teamwork.bot_labels` `teamwork.dismissed_alerts` `teamwork.dismiss_allowed` `teamwork.auto_rerun` `teamwork.cancel_policy` `teamwork.queued_hours` `teamwork.stuck_hours` `teamwork.forks_help` `teamwork.inactive_workflows` `teamwork.keep_alive_days` `teamwork.runner_hooks`
