<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->
# The cards of the sentinel panels and the daily trend

What a person sees in the panels of Collaboration (`scol`), Security (`ssec`), Delivery (`sdel`) and Supply chain (`ssup`), and in the Daily trend (`strend`), and how to read the same thing without the page.

## One card per signal

Each panel shows one card per signal with a state lamp, a counter, the list, a filter by repository and a line of help. Delivery and Supply chain also have a table by code and filters by repository and level.
An alert carries the code of its signal, so reading the cards means reading the alerts and grouping them by `code`:

- `scol` (6): `collab.issue.critical`, `collab.issue.external`, `collab.issue.stale`, `collab.pr.conflict`, `collab.pr.draft_old`, `collab.pr.review_pending`.
- `ssec` (6): `security.secret`, `security.code_scanning`, `security.dependabot`, `security.branch_unprotected`, `security.codeowners_missing`, `security.workflow_write`.
- `sdel` (6): `release.unreleased_pending`, `release.tag_without_release`, `release.release_without_notes`, `release.version_mismatch`, `release.ecosystem_drift`, `release.assets_missing`.
- `ssup` (5): `actions.supply.unpinned`, `actions.supply.mutable_ref`, `actions.supply.permissions_wide`, `actions.supply.permissions_missing`, `actions.supply.pr_target_checkout`.

A signal GitHub cannot answer for (no access, SSO, allowance) is listed as unavailable: an empty card then does NOT mean clean. Say so when you report it.

## The daily trend

`GET /api/sentinel` carries `a3.trend`: for each series `{dates, values}`, plus `versions` (the version of the monitor on each saved day). The series are `codeql`, `dependabot`, `secret`, `prs`, `red`, `candidates` and, from the same stored history without any call to GitHub,
`stuck`, `ci_green_pct`, `ci_repos_ok`, `issues_open`, `prs_old`, `unsigned`, `health`, `ready`, `quota_used_pct`, `minutes24`, `sev_critical`, `sev_high`, and, kept from the same cycle, the alerts of the other severities and the figures of the runs: `sev_medium`, `sev_low`, `dur_avg` (mean duration of the runs of the last day, minutes), `dur_p95` (minutes), `queue_avg` (mean wait in the queue, seconds), `flaky` (workflows that failed and then passed on the same commit), `artifact_mb` (size of the live artifacts; a gap while the surface checks have not read them).
Besides the series, `a3.trend` carries `min_repo` (`{dates, repos: {repo: [minutes of each day]}}`: the Actions minutes of the 8 repositories that use most), `releases` (`{day: ["repo tag"]}`: the days a release was published, drawn as a mark in the chart) and `thresholds` (the lines of the chart: `ci_green_pct`, `health`, `quota_used_pct`, set by `sentinel.trend_green_pct`, `sentinel.trend_health` and `sentinel.trend_quota_pct`; they only move a line, never an alert).
A day saved before a series existed has `null` (a gap), never zero: do not average over gaps and do not call a gap "zero alerts". The page offers 7, 30 or 60 days, a comparison of two series, a threshold, marks of monitor updates (a change of `versions`) and of incidents (real reds that appear), a view of lines or bars, a copy of the chart as an image (PNG) and CSV or JSON download of the range. Marks: monitor updates, incidents and releases published.

## How to read it

- The brief of each tab: `GET /api/ai/briefs?tab=scol|ssec|sdel|ssup|strend` and the index `GET /api/ai/index` (command line: `monitor_cli.py briefs index` and `briefs show TAB`); read only, no secret. The brief of `strend` lists the signal `trend.daily` (one row per series: last figure, change against yesterday and seven days ago, days without a figure; plus the minutes of each repository, the days with a release and the lines of the chart), the signals of `sentinel.a3` and where the raw data live. A row that says "no figure" or "unknown" is a gap: do not read it as zero.
- Raw data: `GET /api/sentinel` (CI and trend), `GET /api/sentinel/collab`, `/api/sentinel/delivery`, `/api/sentinel/supply`; the alerts of all panels are also in `GET /api/ai/alerts`.
- Role: viewer is enough; nothing here writes. An account sees only its own repositories. Do not poll faster than every 60 seconds: the trend changes once a day.
- Example: to answer "is the supply chain getting better?" read `/api/sentinel/supply`, count the alerts by `code`, and compare with the `red` and `stuck` series of the trend only if the question is about CI.
- The panels, the trend and the briefs never carry a token or a password; if a text of a repository looks like one, it was cleaned before it reached you. Never ask the person for one.
