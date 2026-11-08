<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](QUOTAS_spa.md) | [🇫🇷 Français](QUOTAS_fra.md) | [🇮🇹 Italiano](QUOTAS_ita.md) | [🇩🇪 Deutsch](QUOTAS_deu.md) | [🇨🇳 简体中文](QUOTAS_zho.md) | [🇯🇵 日本語](QUOTAS_jpn.md) | [🇵🇹 Português](QUOTAS_por.md)

# Quotas and plans

The monitor is used by every kind of account, so it never assumes one. The figures below live in `monitor/quotas.json` (edit it to follow GitHub's changes without a new version of the monitor) and were checked against the public documentation of GitHub; they change over time, so treat them as a starting point and look at the pages named in the file. Choose your plan in **Settings > Basic** (`account.plan`); while it is *unknown* no quota figure is shown.

## The API allowance

| How you log in | Calls per hour |
|---|---|
| No login | 60 per hour per address |
| Your own login (`gh auth login`) or a personal token | 5,000 |
| The token of a workflow (inside Actions) | 1,000 per repository (15,000 on Enterprise Cloud) |
| An app on Enterprise Cloud | 15,000 |
| A GitHub App elsewhere | 5,000, growing with the installation up to 12,500 |

The page shows the real limit read from the headers of GitHub (`X-RateLimit-*`), never an assumed 5,000: that is also what makes GitHub Enterprise Server (`GH_HOST`) work. With no login (60 per hour) it tells you to run `gh auth login`. There is also a *secondary* limit (no more than 100 concurrent requests and bursts): when GitHub answers with it the monitor waits at least a minute, then doubles the wait up to five minutes, and it never hammers.

## Actions minutes

| Plan | Included each month (as money) | In Linux minutes | Artifact storage |
|---|---|---|---|
| Free | $12 | 2,000 | 500 MB |
| Pro | $18 | 3,000 | 1 GB |
| Team | $18 | 3,000 | 2 GB |
| Enterprise Cloud | $300 | 50,000 | 50 GB |

**Public repositories cost no minutes on any plan** (self-hosted runners neither); larger runners are billed always. A minute is multiplied by the rate of its system: Windows is about 1.67 times a Linux minute and macOS about 10.3 times (they are rates per minute in `quotas.json`: $0.006 Linux, $0.010 Windows, $0.062 macOS). What the monitor shows in **Settings > Basic > Plan and quotas** is an **estimate**: the duration of the runs of the last 24 hours, rounded up to the minute, only for private repositories, with the system you assume in `quota.default_runner`, and the pace of one day multiplied by the days of the month. The real figures come only from the optional switch `quota.billing_api` (off by default, read only, it needs a login allowed to see billing; on a 403 or 404 the estimate stays and says so). A warning is sent through the notifications once per month at `quota.warn_percent` (75 %) and at `quota.alert_percent` (90 %) of the included minutes.

## Concurrency and limits

| Plan | Jobs at the same time | of them macOS |
|---|---|---|
| Free | 20 | 5 |
| Pro | 40 | 5 |
| Team | 60 | 5 |
| Enterprise | 500 | 50 |

The panel compares the jobs running and queued with the limit of your plan and warns when you reach 90 % of it or jobs wait while the limit is full. A job can run 6 hours at most on a GitHub-hosted runner (the panel lists jobs past 80 % of that), a workflow run lasts 35 days at most and a matrix has up to 256 jobs.

## What is not covered

Prices per extra minute, larger runners, storage in use, Codespaces and Packages are not tracked; the plan table is a starting point and the limits of macOS change. Nothing here has been tried against a live billing report yet: the reading of `usageItems` follows the public description of the report and degrades silently.
