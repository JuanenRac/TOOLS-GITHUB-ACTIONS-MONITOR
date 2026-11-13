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

- Each read of the run lists sends `If-None-Match`; GitHub answers `304 Not Modified` when nothing changed and that answer costs no quota. The header shows how many reads were saved and `ghamon_etag_saved_total` counts them. `cache.etag.enabled` and `cache.etag.ttl_hours` are in the Settings tab.
- The cache is the local file `etag_cache.json` (never published); a broken file is just an empty cache.


## When the connection is lost

If every read of a cycle fails with a connection problem (not a login or a quota problem), the page keeps the last picture and shows a red banner `no connection since HH:MM`. Nothing raises; the monitor resumes by itself and writes an `offline` and an `online` event once each (they can be notified). `ghamon_offline` is 1 meanwhile.

## How long the history is kept

Besides `keep_days` of the analytics block, the days of the history older than `retention.analytics_days` (180 by default) are removed by the retention pass; the samples themselves are capped by `max_samples`. See [STORAGE.md](STORAGE.md).
