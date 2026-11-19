<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](ANALYTICS_spa.md) | [🇫🇷 Français](ANALYTICS_fra.md) | [🇮🇹 Italiano](ANALYTICS_ita.md) | [🇩🇪 Deutsch](ANALYTICS_deu.md) | [🇨🇳 简体中文](ANALYTICS_zho.md) | [🇯🇵 日本語](ANALYTICS_jpn.md) | [🇵🇹 Português](ANALYTICS_por.md)

# Analytics, conditional reads and the lost connection

What the monitor learns from the runs it already reads, and how it saves quota and survives a network cut. Everything here is local; nothing is sent anywhere.

## Durations, queue time and steps

- `p50` and `p95` of the duration of the successful runs of each workflow; of the time a job waited before it started (created to started); and of each step of a workflow. A workflow shows figures once it has `analytics.min_samples` samples.
- Job and step times need the jobs of completed runs: up to `analytics.jobs_per_cycle` runs per cycle, each read once (0 reads none). The incoming webhook supplies them for free.
- They are exported as `ghamon_workflow_duration_seconds`, `ghamon_job_queue_seconds` and `ghamon_step_duration_seconds` (label `quantile` 0.5 / 0.95; needs `per_repo`) and in the Grafana JSON source (`durations`, `queue`). `slower` lists the workflows whose p50 is `analytics.slow_factor` times their usual one.


## Flaky workflows

A workflow that FAILED and then PASSED on the very same commit (or whose run needed another attempt) is labelled flaky: `ghamon_workflow_flaky_rate`. It is only a label: what counts as red does not change.


## Conditional reads (ETag)

- Each read of the run lists sends `If-None-Match`; GitHub answers `304 Not Modified` when nothing changed and that answer costs no quota. The header shows how many reads were saved and `ghamon_etag_saved_total` counts them. `cache.etag.enabled` and `cache.etag.ttl_hours` are in the Settings tab. Every entry belongs to the credential that read it (a short fingerprint of the token is part of the key, never the token), so a `304` never returns the body of another identity. A state that is still moving is always read in full: the jobs of a run, one run, the check suites and check runs (`cache.etag.skip_stateful`) and any list of runs whose last answer still had a run queued or in progress (`cache.etag.revalidate_active`). A refusal (404 or 403 that is not a rate limit) is remembered for `cache.negative_ttl_s` seconds. `/metrics` also counts the answers without ETag, the reads made in full on purpose and the refusals not repeated, and the brief for the AI tools has the signal quota.etag.
- The brief for the AI tools names schema.drift when GitHub sent a status or a conclusion the monitor does not know, or a run without a usable number: the unknown value is shown as it came and is never counted as red or as green.
- The cache is the local file `etag_cache.json` (never published); a broken file is just an empty cache.


## When the connection is lost

If every read of a cycle fails with a connection problem (not a login or a quota problem), the page keeps the last picture and shows a red banner `no connection since HH:MM`. Nothing raises; the monitor resumes by itself and writes an `offline` and an `online` event once each (they can be notified). `ghamon_offline` is 1 meanwhile.

## How long the history is kept

Besides `keep_days` of the analytics block, the days of the history older than `retention.analytics_days` (180 by default) are removed by the retention pass; the samples themselves are capped by `max_samples`. See [STORAGE.md](STORAGE.md).


## Time saved (an estimate)

Off by default (`productivity.enabled`). When it is on, the section shows, task by task, how many minutes a week the monitor saves, with the formula of [PRODUCTIVITY.md](PRODUCTIVITY.md): times a week x minutes each time without the monitor x the saving of the task.

- Two tasks are quantified. **Watching** (looking at the Actions tabs by hand and deciding what is red) takes the times a week and the minutes from your notes (`productivity.watch_times_per_week`, `productivity.watch_minutes_before`). **Triage** (finding the cause of a failed run) counts the failed runs the monitor has in view over `productivity.window_days` and takes the minutes from your notes (`productivity.triage_minutes_before`).
- The monitor cannot see what you did before it was installed. A task without those notes says **no data** and no number is made up. The total says no data too while every task lacks its notes.
- If you also noted the minutes with the monitor (`productivity.watch_minutes_after`, `productivity.triage_minutes_after`), the saving is measured from your notes: 1 - after / before. Otherwise it is the percentage in `productivity.saving_percent` (90 by default), and the table says **assumed (not measured)**.
- With `productivity.team_hours_per_week` the estimate also says what share of the working time the saved minutes are.
- Fixing a failure takes the same time with or without the monitor and is never counted. Only failed runs the monitor holds are counted: a very long list of runs may hold more failures than are shown.
- It is local and read only: no call to GitHub, nothing leaves the computer. It is in `/api/analytics` (`time_saved`), in the summary of the A12 panel and in the brief of the Summary tab for the AI tools.
