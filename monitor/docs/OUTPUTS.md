<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](OUTPUTS_spa.md) | [🇫🇷 Français](OUTPUTS_fra.md) | [🇮🇹 Italiano](OUTPUTS_ita.md) | [🇩🇪 Deutsch](OUTPUTS_deu.md) | [🇨🇳 简体中文](OUTPUTS_zho.md) | [🇯🇵 日本語](OUTPUTS_jpn.md) | [🇵🇹 Português](OUTPUTS_por.md)

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

A request to a path whose switch is off gets `404`. The older way of giving the same document to a dashboard, `ci_red.json` and `bin/read_report.py --export-status`, is unchanged: it is a contract.

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
| `ghamon_score`, `ghamon_score_coverage`, `ghamon_score_scored` | | the score of the account (0 to 100, only while it has a number), the share of its weights with data and 1 when it has a number (Complete only; see SCORE.md) |
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

## The minimal Grafana board

`docs/grafana/red_by_ecosystem.json` is a one-panel board: red workflows by ecosystem (query `ghamon_ecosystem_red_workflows`, legend `{{ecosystem}}`). Import it and pick your Prometheus data source. A test of this repository checks that the metric and the label it uses are really served by `/metrics`.

## The signing queue by trust

Each row of the queue has a `trust`: `verified` (the signature was checked against the public key), `unknown` (the format cannot be checked here: never a guess) or `failed` (it was checked and does not match). The Sentinel tab has a Signature filter with the count of each kind and marks the rows (green, grey or red edge). From the console: `py -3 bin/read_report.py --export-sign-queue FILE --sign-trust failed`.

## In the network mode

`/metrics` and `dashboard.json` list your repositories and their state: they are not public pages. With the network mode on they need the access token like every other endpoint; switch off `outputs.prometheus.enabled` / `outputs.dashboard.enabled` if you do not want that inventory to be reachable at all.

## Save and print the report of a tab

The bar at the top of the page (on every tab) makes ONE report of the tab that is open and draws it four ways from the same data, so the formats never differ:

- **Save the report** opens a window with three boxes: **TXT** (marked), **PDF** (marked) and **JSON** (not marked: the data of the report, for other tools). After you accept, the **Save as** window of the browser opens once per format, with the suggested name `monitor-<tab>-<date>.<extension>` and the right file type (the browser wants one click per window, so the button goes on to the next format). A browser without that window downloads the file and the page tells you where it went.
- **PDF**: the monitor writes the PDF itself, with no library and the standard Helvetica font, for English, Spanish, German, French, Italian and Portuguese (`GET /api/report/tab.pdf`, only from this computer; every use leaves a line in the log of actions). Japanese and Chinese need fonts that a PDF written this way does not have, so for them, or when you choose "The browser" in the window, the PDF comes from the print window of the browser: choose **Save as PDF** there. The page says so; it never writes a PDF with broken characters.
- **Print** shows the same report without menus or bars (title with the name of the tab, date and time, version of the monitor, main figures, alerts and the tables of the tab) and opens the print window.
- The report is served by `GET /api/report/tab?tab=now&lang=en` (`&fmt=json`, `&fmt=txt` or `&fmt=options`), the same in both editions.

Settings (Settings > Outputs for other tools > "Save and print the report of a tab"): `report_export.txt`, `report_export.pdf` and `report_export.json` (which boxes start marked: TXT and PDF yes, JSON no), `report_export.name` (suggested name, default `monitor-{tab}-{date}`), `report_export.paper` (`a4` or `letter`, default `a4`) and `report_export.pdf_path` (`auto`, `own` or `browser`, default `auto`).

## Metrics of the server: cycle, queue of reads, billing, runners and histograms

Besides the gauges above, `/metrics` writes (a value that is not known is left out):

| Metric | Labels | Meaning |
|---|---|---|
| `ghamon_ticks_total`, `ghamon_tick_failures_total` | | refresh cycles finished and cycles that ended with an error (counters) |
| `ghamon_tick_last_seconds`, `ghamon_tick_phase_seconds`, `ghamon_tick_seconds` | `phase` | duration of the last cycle, of each of its phases, and the histogram of all of them |
| `ghamon_tick_last_ok_timestamp_seconds`, `ghamon_tick_reads_last` | | when the last cycle ended well and how many repositories it read |
| `ghamon_read_retries_total` | | reads that failed for a passing reason and were repeated (counter) |
| `ghamon_repos_circuit_open`, `ghamon_repos_read_failing`, `ghamon_repos_read_fail_streak_max` | | repositories that wait before the next read because they failed several times in a row (the circuit), repositories whose last read failed, the longest streak |
| `ghamon_read_queue_depth`, `ghamon_read_queue_allowed`, `ghamon_read_queue_oldest_wait_cycles`, `ghamon_read_queue_deferred_total`, `ghamon_read_queue_shed_cycles_total` | | the queue of reads with backpressure (only while `backpressure.enabled` is on) |
| `ghamon_billing_minutes_total`, `ghamon_billing_minutes_included`, `ghamon_billing_minutes_paid`, `ghamon_billing_sku_minutes`, `ghamon_billing_usd` | `sku`, `product` | the billing report of the month (only while `quota.billing_api` is on; a scrape never reads GitHub, it writes the last report the cycle held) |
| `ghamon_runners` | `state` | self-hosted runners idle, busy and offline (`runners.enabled`) |
| `ghamon_runner_up`, `ghamon_runner_busy` | `runner` | per runner (`outputs.prometheus.per_runner`) |
| `ghamon_runner_kind_jobs_waiting`, `ghamon_runner_kind_oldest_wait_seconds` | `kind` | jobs not started and the oldest wait by kind of runner (`runners.model.enabled`) |

With `outputs.prometheus.histograms` on (and the webhook receiving job events) it also writes **histograms**, built in memory from the signed `workflow_job` and `workflow_run` events:

| Metric | Labels | Meaning |
|---|---|---|
| `ghamon_job_wait_seconds` | `runner_group`, `label` | time in the queue of a job, counted **once per job** |
| `ghamon_job_run_seconds` | `runner_group`, `label`, `conclusion` | duration of the jobs that finished |
| `ghamon_workflow_run_seconds` | `conclusion` | duration of the runs that finished |
| `ghamon_jobs_total` | `label`, `conclusion` | jobs that finished (counter) |
| `ghamon_runner_jobs_waiting`, `ghamon_runner_oldest_wait_seconds` | `label` | the demand for runners now: jobs queued and not started, and the oldest wait |

`outputs.prometheus.histogram_max_series` (200 by default) bounds the series of each histogram: the ones beyond it are counted under the label value `other`. With `outputs.prometheus.per_runner` on it adds, per self-hosted runner, `ghamon_runner_jobs_total`, `ghamon_runner_jobs_failed_total` and `ghamon_runner_busy_seconds_total` (also in `GET /api/runners/model` as `per_runner`).

## Observability pack: alert rules, Alertmanager, OnCall and n8n

`docs/grafana/` carries, besides the two dashboards, a pack you copy and adapt:

- `ghamon_alert_rules.yml`: rules for Prometheus (also vmalert) with their PromQL: a monitor that does not answer, red workflows and streaks, allowance and billing near their end, a cycle that is slow or stalled, repositories in the circuit, reads that wait too long, jobs that wait for a runner (`histogram_quantile(0.95, sum by (le, label) (rate(ghamon_job_wait_seconds_bucket[30m])))`), runners offline and demand with no idle runner.
- `alertmanager.example.yml`: routes by severity to three receivers (a default webhook, Grafana OnCall and n8n). Every address is `https://example.invalid/...`: nothing is sent until you write yours, and no secret belongs in the file.
- `n8n_ghamon_alerts.json`: an n8n workflow that receives the Alertmanager webhook and writes one message per alert; its last node does nothing until you put your chat, mail or ticket node there.
- `prometheus.example.yml` and `docker-compose.observability.yml` start Prometheus, Alertmanager and Grafana on the computer of the monitor to try the pack (the containers share the network of the host, the ports are on `127.0.0.1` and the Grafana password comes from your shell, never from the file).
## Where the monitor calls, and events towards a SIEM

- **Table of network destinations**: `monitor_cli.py doctor --egress` (also with `--json`) lists every host the CURRENT configuration can call, what it is for, the setting that makes it a destination and what fails if it is blocked: `api.github.com`, `github.com`, `objects.githubusercontent.com` and `release-assets.githubusercontent.com` (updates), `raw.githubusercontent.com` (`lint.anonymous_public`), ntfy, Telegram, the chat webhooks, the AI provider you chose, the OTLP collector and the SIEM sinks. With `airgapped` nothing is in use. A test keeps the table equal to the hosts named by the code.
- **SIEM** (off): `siem.sinks` in the file lists the destinations, each with `enabled: true` to be used: `elasticsearch` (bulk), `splunk_hec`, `loki`, `sentinel` (Log Analytics, signed with the shared key), `bigquery` (`insertAll`) or `http` (JSON lines). The token or key is read from the environment variable named by `token_env`, never from the file. Each sink filters with `from_minutes` (5), `levels` and `repos_filter`; the events have a closed list of fields (no token, no log text); a receiver on a private address is refused unless the sink has `allow_private`; when a receiver is down the events wait in a queue of `siem.queue_max` (500) and the oldest are dropped first. Nothing is sent in the offline mode.
