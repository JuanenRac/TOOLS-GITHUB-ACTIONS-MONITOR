<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](COLLABORATION_spa.md) | [🇫🇷 Français](COLLABORATION_fra.md) | [🇮🇹 Italiano](COLLABORATION_ita.md) | [🇩🇪 Deutsch](COLLABORATION_deu.md) | [🇨🇳 简体中文](COLLABORATION_zho.md) | [🇯🇵 日本語](COLLABORATION_jpn.md) | [🇵🇹 Português](COLLABORATION_por.md)

# Collaboration views and optional actions

Views of what waits for somebody, and a few actions on GitHub that stay off until you allow them. Complete and Full editions.

## Turn it on

Set `actions.enabled` (Settings > Collaboration). The views of runs come from what the monitor already reads; pull requests, alerts and workflows are read a few repositories per cycle (`actions.repos_per_cycle`, `actions.refresh_hours`). The Collaboration box is at the end of the Collaboration tab of the Sentinel area.

## The views

Waiting for a person (environment approval, workflow of a fork, action required) apart from waiting for a runner. The newest run of each lane (workflow and branch); a red one can be set aside for `actions.dismiss_days` days, only that run, and restored. Open pull requests grouped as mergeable, behind the base, needs action or not known, with the updates of bots recognised by author, branch or label; `actions.hide_workflows` hides workflows by name. Repositories with critical or high dependency alerts with the age of the oldest, and the repositories NOT read, named. With `actions.dismissed_alerts`, who dismissed security alerts; a dismissal by somebody not in `actions.dismiss_allowed` raises an alert.

## Writing on GitHub

Nothing is written unless `github_actions.enabled` is on, the action is in `github_actions.allowed`, and you confirm the plan, which shows exactly what is sent. New actions: `update_branch`, `approve_fork`, `approve_deployment`, `force_cancel`, `enable_workflow`, `dispatch`. The views only PROPOSE: bot updates with failing checks, branches behind, runs queued or running too long (`actions.queued_hours`, `actions.stuck_hours`), runs that match `actions.cancel_policy`, workflows switched off for inactivity (`actions.inactive_workflows`). The form of a manual workflow reads its inputs and checks them. With `actions.forks_help`, facts about the author of a fork run (age of the account, merged changes here, workflow files touched); no verdict is given.

## The one automatic action

`actions.auto_rerun` (off) re-runs once the failed jobs of a run that did not start or timed out, through the same checks (it does nothing while the actions are off or `rerun_failed` is not allowed). It never tries a second time; if the run fails again an alert is raised.

## Hooks of self-hosted runners

With `actions.runner_hooks`, a hook of a runner on this computer records job start and end:

```
# ACTIONS_RUNNER_HOOK_JOB_STARTED
python /path/to/monitor/bin/monitor_cli.py runner-hook started
```

Use the variable ACTIONS_RUNNER_HOOK_JOB_COMPLETED with `completed` for the end. A runner on another computer is not covered.

## API and command line

`GET /api/actions/state`, `GET /api/actions/dispatch-form`, `GET /api/actions/environments`, `GET /api/actions/fork-facts`, `POST /api/actions/plan`, `POST /api/actions/dismiss`.

```
python bin/monitor_cli.py actions status
python bin/monitor_cli.py actions proposals
python bin/monitor_cli.py runner-hook started
python bin/monitor_cli.py runner-hook completed
```

## Not verified

The reads and the writes have been tested against made-up answers only; none of the new actions has been run on a real repository.

## All settings

`actions.enabled` `actions.repos_per_cycle` `actions.refresh_hours` `actions.dismiss_days` `actions.hide_workflows` `actions.bot_authors` `actions.bot_branches` `actions.bot_labels` `actions.dismissed_alerts` `actions.dismiss_allowed` `actions.auto_rerun` `actions.cancel_policy` `actions.queued_hours` `actions.stuck_hours` `actions.forks_help` `actions.inactive_workflows` `actions.runner_hooks`
