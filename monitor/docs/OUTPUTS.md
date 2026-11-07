<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Outputs for other tools

Three optional outputs, **all off by default**, switched on in the Settings tab (group "Outputs for other tools") or in `actions_monitor.json`:

```json
"outputs": {"prometheus": {"enabled": false, "per_repo": true}, "json": {"enabled": false}, "dashboard": {"enabled": false}}
```

They are served by the same web server, only on `127.0.0.1`, with the same `Host` / `Origin` checks as the rest, and **need no token**. They read the state the monitor already holds, so a
scrape or a refresh of a dashboard costs no GitHub API quota. Switching them on or off applies at once (no restart).

| Path | Format | Switch |
|---|---|---|
| `/metrics` | Prometheus text, version 0.0.4 | `outputs.prometheus.enabled` (`per_repo` adds the series per repository) |
| `/api/outputs/grafana.json` | JSON tables for the Grafana "Infinity" / JSON data source | `outputs.json.enabled` |
| `/api/outputs/dashboard.json` | the document of `ci_red.json` (schema 2, see CI_RED_SCHEMA.md) for a status dashboard | `outputs.dashboard.enabled` |

A request to a path whose switch is off gets `404`. The older way of giving the same document to a dashboard, `ci_red.json` and `read_report.py --export-status`, is unchanged: it is a contract.

## Prometheus metrics

Every name starts with `ghamon_`. Gauges only. A value that is not known is **left out**, never written as 0.

| Metric | Labels | Meaning |
|---|---|---|
| `ghamon_info` | `version` | always 1 |
| `ghamon_snapshot_complete` | | 1 when the sentinel snapshot is complete, 0 while it loads or is reduced |
| `ghamon_red_workflows`, `ghamon_red_repos` | | workflows (repositories) whose last completed run on the default branch is red |
| `ghamon_ecosystem_red_workflows` | `ecosystem` | the same by ecosystem |
| `ghamon_repo_red_workflows` | `repo`, `ecosystem` | per repository (needs `per_repo`) |
| `ghamon_workflow_red_streak` | `repo`, `workflow`, `ecosystem` | consecutive red runs (needs `per_repo`) |
| `ghamon_workflow_red_hours` | `repo`, `workflow`, `ecosystem` | hours since it turned red (needs `per_repo`) |
| `ghamon_pending_sign`, `ghamon_pending_sign_repos`, `ghamon_pending_sign_hours_max` | | builds waiting for the local signature or publication, over the threshold |
| `ghamon_repo_pending_sign_hours` | `repo`, `ecosystem` | the longest wait of a repository (needs `per_repo`) |
| `ghamon_surface_paused`, `ghamon_surface_paused_remaining`, `ghamon_surface_paused_needed` | | 1 while the surface checks (A10) wait for GitHub quota, with the allowance left and needed |
| `ghamon_api_rate_remaining`, `ghamon_api_rate_limit` | | the GitHub API allowance |
| `ghamon_sentinel_calls_last_hour`, `ghamon_sentinel_budget_per_hour` | | the API calls of the sentinel against its budget |
| `ghamon_repos_watched`, `ghamon_runs_active`, `ghamon_runs_stuck`, `ghamon_runs_failing`, `ghamon_issues_open`, `ghamon_quota_paused` | | the live figures of the Now tab |

A scrape job:

```yaml
scrape_configs:
  - job_name: github-actions-monitor
    scrape_interval: 30s
    static_configs:
      - targets: ["127.0.0.1:8765"]
```

## Grafana

`docs/grafana/monitor_dashboard.json` is an importable dashboard (Grafana 10 or newer): stat panels for the red workflows, the builds waiting for a signature, the allowance left, the
state of A10, whether the snapshot is complete and the stuck runs; a bar chart of red workflows by ecosystem; a chart of the longest red streak and signature wait; and two tables read
from `/api/outputs/grafana.json` with the Infinity data source (`root_selector` `red` and `pending_sign`). On import Grafana asks for the Prometheus and the Infinity data sources; change
the port in the URL of the two tables if the monitor does not use 8765. Grafana must run on the same machine (the outputs answer only on 127.0.0.1).

## Ideas taken from similar projects

Reading what other tools do for GitHub Actions gave some ideas; none of their code or texts is used. From an exporter of Prometheus metrics: the status of a run as a number plus labels, the
choice of which labels to export, and a configurable port and interval. From a TV dashboard fed by webhooks: one status per repository with filters, shown large. From a terminal watcher: all the
workflows of a repository at once until they finish. From a webhook dashboard with alert rules: filters by repository, branch and workflow before alerting. Here the same ideas show up as
`per_repo` (choose the series), the JSON source with one row per red workflow, the live Now tab and the events file with filters in the page.
