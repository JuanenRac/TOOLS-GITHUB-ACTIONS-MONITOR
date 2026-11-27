<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COLLABORATION.md) | [🇪🇸 Español](COLLABORATION_spa.md) | [🇫🇷 Français](COLLABORATION_fra.md) | [🇮🇹 Italiano](COLLABORATION_ita.md) | [🇩🇪 Deutsch](COLLABORATION_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](COLLABORATION_jpn.md) | [🇵🇹 Português](COLLABORATION_por.md)

# 协作视图与可选操作

显示等待他人处理的内容，以及若干在你允许之前保持关闭的 GitHub 操作。Complete 与 Full 版本。

## 开启

开启 `teamwork.enabled`（设置 > 协作）。运行视图来自监视器已读取的数据；拉取请求、告警和工作流每个周期读取少量仓库（`teamwork.repos_per_cycle`、`teamwork.refresh_hours`）。该区块位于哨兵区域协作标签页的末尾。

## 视图

等待人工（环境审批、分叉工作流、需要操作）与等待运行器分开显示。每个通道（工作流与分支）的最新运行；红色运行可搁置 `teamwork.dismiss_days` 天（仅该次运行）并可恢复。未关闭的拉取请求分为可合并、落后、需处理、未知，机器人更新按作者、分支或标签识别；`teamwork.hide_workflows` 按名称隐藏工作流。存在严重或高危依赖告警的仓库及最早告警的天数，并按名称列出未读取的仓库。开启 `teamwork.dismissed_alerts` 后显示谁忽略了告警；不在 `teamwork.dismiss_allowed` 中的人忽略会触发告警。

## 写入 GitHub

只有当 `github_actions.enabled` 开启、操作位于 `github_actions.allowed` 且你确认显示完整发送内容的计划时才写入。新操作：`update_branch`, `approve_fork`, `approve_deployment`, `force_cancel`, `enable_workflow`, `dispatch`。视图只做提议：检查失败的机器人更新、落后的分支、排队或运行过久的运行（`teamwork.queued_hours`、`teamwork.stuck_hours`）、匹配 `teamwork.cancel_policy` 的运行、因不活跃停用的工作流（`teamwork.inactive_workflows`）。手动工作流表单会读取并校验输入。开启 `teamwork.forks_help` 时显示分叉运行作者的事实信息，不给结论。部署一次只批准一个环境，确认框中写明其名称；当一次运行等待多个环境时，页面会询问是哪一个。

## 唯一的自动操作

`teamwork.auto_rerun`（默认关闭）会在同样的检查下，将未能启动或超时运行的失败任务重跑一次。绝不重试第二次；若再次失败则触发告警。

## 保持定时任务

公开仓库连续 60 天没有活动时，GitHub 会关闭其定时工作流。设置 `teamwork.keep_alive_days`（0 = 关闭；例如 45）后，这段时间内没有 push 且有按定时运行过的工作流的公开仓库，会以 `enable_workflow` 出现在建议中，并显示剩余天数。它和其他建议一样：在你确认之前不会发送任何内容。GitHub 没有说明启用一个已启用的工作流会重新计时，这一点也没有在真实仓库上试过：可靠的办法是提交一次新的 commit。

## 自托管运行器钩子

开启 `teamwork.runner_hooks` 后，本机运行器的钩子记录任务开始与结束：

```
# ACTIONS_RUNNER_HOOK_JOB_STARTED
python /path/to/monitor/bin/monitor_cli.py runner-hook started
```

结束时使用 ACTIONS_RUNNER_HOOK_JOB_COMPLETED 和 `completed`。其他电脑上的运行器不在范围内。

## API 与命令行

`GET /api/actions/state`, `GET /api/actions/dispatch-form`, `GET /api/actions/environments`, `GET /api/actions/fork-facts`, `POST /api/actions/plan`, `POST /api/actions/dismiss`。

```
python bin/monitor_cli.py actions status
python bin/monitor_cli.py actions proposals
python bin/monitor_cli.py runner-hook started
python bin/monitor_cli.py runner-hook completed
```

## 未验证

读取和写入仅用虚构应答测试过；新操作均未在真实仓库上执行。

## 全部设置

`teamwork.enabled` `teamwork.repos_per_cycle` `teamwork.refresh_hours` `teamwork.dismiss_days` `teamwork.hide_workflows` `teamwork.bot_authors` `teamwork.bot_branches` `teamwork.bot_labels` `teamwork.dismissed_alerts` `teamwork.dismiss_allowed` `teamwork.auto_rerun` `teamwork.cancel_policy` `teamwork.queued_hours` `teamwork.stuck_hours` `teamwork.forks_help` `teamwork.inactive_workflows` `teamwork.keep_alive_days` `teamwork.runner_hooks`
