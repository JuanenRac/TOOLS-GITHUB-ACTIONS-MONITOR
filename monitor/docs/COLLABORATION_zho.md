<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COLLABORATION.md) | [🇪🇸 Español](COLLABORATION_spa.md) | [🇫🇷 Français](COLLABORATION_fra.md) | [🇮🇹 Italiano](COLLABORATION_ita.md) | [🇩🇪 Deutsch](COLLABORATION_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](COLLABORATION_jpn.md) | [🇵🇹 Português](COLLABORATION_por.md)

# 协作视图与可选操作

显示等待他人处理的内容，以及若干在你允许之前保持关闭的 GitHub 操作。Complete 与 Full 版本。

## 开启

开启 `actions.enabled`（设置 > 协作）。运行视图来自监视器已读取的数据；拉取请求、告警和工作流每个周期读取少量仓库（`actions.repos_per_cycle`、`actions.refresh_hours`）。该区块位于哨兵区域协作标签页的末尾。

## 视图

等待人工（环境审批、分叉工作流、需要操作）与等待运行器分开显示。每个通道（工作流与分支）的最新运行；红色运行可搁置 `actions.dismiss_days` 天（仅该次运行）并可恢复。未关闭的拉取请求分为可合并、落后、需处理、未知，机器人更新按作者、分支或标签识别；`actions.hide_workflows` 按名称隐藏工作流。存在严重或高危依赖告警的仓库及最早告警的天数，并按名称列出未读取的仓库。开启 `actions.dismissed_alerts` 后显示谁忽略了告警；不在 `actions.dismiss_allowed` 中的人忽略会触发告警。

## 写入 GitHub

只有当 `github_actions.enabled` 开启、操作位于 `github_actions.allowed` 且你确认显示完整发送内容的计划时才写入。新操作：`update_branch`, `approve_fork`, `approve_deployment`, `force_cancel`, `enable_workflow`, `dispatch`。视图只做提议：检查失败的机器人更新、落后的分支、排队或运行过久的运行（`actions.queued_hours`、`actions.stuck_hours`）、匹配 `actions.cancel_policy` 的运行、因不活跃停用的工作流（`actions.inactive_workflows`）。手动工作流表单会读取并校验输入。开启 `actions.forks_help` 时显示分叉运行作者的事实信息，不给结论。

## 唯一的自动操作

`actions.auto_rerun`（默认关闭）会在同样的检查下，将未能启动或超时运行的失败任务重跑一次。绝不重试第二次；若再次失败则触发告警。

## 自托管运行器钩子

开启 `actions.runner_hooks` 后，本机运行器的钩子记录任务开始与结束：

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

`actions.enabled` `actions.repos_per_cycle` `actions.refresh_hours` `actions.dismiss_days` `actions.hide_workflows` `actions.bot_authors` `actions.bot_branches` `actions.bot_labels` `actions.dismissed_alerts` `actions.dismiss_allowed` `actions.auto_rerun` `actions.cancel_policy` `actions.queued_hours` `actions.stuck_hours` `actions.forks_help` `actions.inactive_workflows` `actions.runner_hooks`
