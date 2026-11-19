<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](SENTINEL_spa.md) | [🇫🇷 Français](SENTINEL_fra.md) | [🇮🇹 Italiano](SENTINEL_ita.md) | [🇩🇪 Deutsch](SENTINEL_deu.md) | [🇨🇳 简体中文](SENTINEL_zho.md) | [🇯🇵 日本語](SENTINEL_jpn.md) | [🇵🇹 Português](SENTINEL_por.md)

# The sentinel and its checks A1-A13

The **sentinel** is the second half of the complete edition. The *monitor* shows what is running and what failed right now; the *sentinel* looks at the whole account every few minutes and answers a different question: **what needs a person**. It reads GitHub (never writes to it), keeps a short history on this computer and turns everything it finds into thirteen numbered checks, **A1 to A13**, one traffic light each.

**The lite edition does not include it.** `MONITOR_LITE_GITHUB_ACTIONS` (port 8766) has no sentinel: the module is not even imported and its endpoints answer 404. The complete edition (`MONITOR_GITHUB_ACTIONS`, port 8765) starts it by itself; switch it off with `sentinel.enabled` (Settings > Sentinel). Both editions use the same rule for "red on main" (A2), so their figures agree.

The **Daily trend** (address `#sentinel-trend`) has a menu entry of its own: one small curve for each signal (code scanning, Dependabot, secrets, pull requests, red, candidates) with its last value. The summary of the sentinel keeps only its own panels and a button that opens it.

The panels of **Collaboration**, **Security**, **Delivery** and **Supply chain** show one card per signal (6, 6, 6 and 5), each with its counter, its list, a filter by repository and a line of help; Delivery and Supply chain add a table by code and a filter by repository and level. The **Daily trend** shows 25 series from the history the sentinel already keeps (no call to GitHub): each card gives the value now, the change against yesterday and 7 days ago and a small curve; press one to see it large, choose 7, 30 or 60 days, compare it with a second series, switch the lines in the legend, read the value of a day in the tooltip (also with the arrow keys), see the threshold and the marks of updates and incidents, and download the range as CSV or JSON. A day saved before a series existed shows a gap, never a zero. Seven more series come from what the cycle already reads (mean and p95 duration of the runs, mean wait in the queue, flaky workflows, size of the artifacts, medium and low alerts), the Actions minutes of each of the repositories that use most are drawn day by day, a mark shows the days a release was published, and the lines of the chart are settings (`sentinel.trend_green_pct`, `sentinel.trend_health`, `sentinel.trend_quota_pct`). Choose lines or bars, copy the chart as an image, and the brief of the tab (`strend`) carries every series in its signal `trend.daily`.

The **Daily trend** (address `#sentinel-trend`) has a menu entry of its own: one small curve for each signal (code scanning, Dependabot, secrets, pull requests, red, candidates) with its last value. The summary of the sentinel keeps only its own panels and a button that opens it.

**Yesterday vs today** (address `#sentinel-yesterday`) has a menu entry of its own too, so the report of the sentinel takes the whole page: what appeared since the last saved report, what was solved and what stays, for the red workflows and the pending signatures.

## How it starts and what it costs

It starts with the complete monitor and runs in the same process, in its own thread, with its own budget of GitHub calls (`sentinel.budget_per_hour`, 600 by default, and `sentinel.max_calls_per_tick`). When the allowance of GitHub is below `sentinel.min_rate_remaining` it stops asking and the page says it is paused for quota. Nothing it does writes to GitHub.

## Files it writes (in the folders of the monitor, never published)

| File | What it holds |
|---|---|
| `ci_red.json` | schema 2: for each repository the workflows that are red and the hours a release waits for its signature. A stable contract for other tools, see `CI_RED_SCHEMA.md` and `CI_RED_BRIDGE.md`. Where: `sentinel.ci_red_file`. |
| `sentinel_history.json` | the daily totals (alerts, red, candidates) used for the trends and for "new since yesterday". |
| `sentinel_cache.json` | the last answers of the slow reads, so a restart does not ask everything again. |
| `events_monitor.jsonl`, `events_state.json` | the event feed (what turned red, what was fixed) with a stable `code` per event. |
| `SENTINEL_REPORT_*.txt` | the daily report, saved in the audit folder when it exists. |

## How to read it

Each check has one of five levels: **ok** (nothing to do), **info** (worth knowing), **warn** (look at it soon), **bad** (act now) and **unknown** (it could not be checked yet: **unknown is never shown as green**). The report on top of the tab sums them up in a few lines; the details open per check. A repository you filtered out of the monitor is not checked.

Every lamp has a shape as well as a colour (a tick for ok, an exclamation mark for warn, a cross for bad, an *i* for info and a question mark for unknown), so the level never depends on the colour alone. Hover a lamp, or reach it with the keyboard, to read its level in words and what it was before it changed. The lamps breathe at a pace that follows their level, a lamp that changes plays one short transition, and when your system asks for reduced motion nothing moves at all.

## The checks

| Check | What it checks and the exact rule | Where to configure | Level and what to do |
|---|---|---|---|
| **A1** | **Builds.** A run that is in progress or queued for longer than the limit is *stuck*. Open issues labelled `build-failed` or `build-stuck` are listed too. Runs of the event `dynamic` (Dependabot internals) are ignored. Each row says why it waits (for a runner, for an approval, its runner is offline, or a long build); `ci.stuck.*` can learn the limit of each workflow or fix one per workflow or runner label. A run that has been queued for more than `ci.stuck.ghost_days` days (default 7, first attempt only, switch `ci.stuck.ghost_enabled`) is a *ghost queue*: GitHub never starts it, so it is not queued, not stuck and gives no alarm; it is counted and listed apart (`a1.ghosts`) and gives one information notice per repository (`ci.ghost_queue`). | `stuck_minutes` | **bad** if anything is stuck or an issue is open. Open the run, cancel or re-run it; close the issue when it is fixed. |
| **A2** | **Red CI.** For each workflow file, the LAST COMPLETED run on the DEFAULT branch: it is red when it failed (`failure`, `timed_out`, `startup_failure`). Runs that are `cancelled`, `skipped`, `neutral` or `stale`, runs in progress and runs of other branches say nothing and never hide an older red. Only runs of `push`, `schedule`, `workflow_dispatch`, `merge_group`, `workflow_run` and `repository_dispatch` decide (`ci.red_events`): a pull request, a comment or an issue never does, and neither does a pull request from a fork whose branch is also called `main` (`ci.count_fork_runs`). A chained workflow (`workflow_run`, `repository_dispatch`) decides only on the default branch and when it does not come from a fork. A run that waits for an approval (`action_required`, or a job held by an environment) is *awaiting approval*, neither red nor queued. A workflow that has not run for `ci.inactive_days` days is *inactive*, not red for ever. A failure in the merge queue shows as `(merge queue)`; `ci.extra_branches` adds maintenance branches and `ci.automation_counts` decides whether triage and bot workflows count. *Streak* = consecutive reds. When a repository's run list is as long as the sample asked for, a workflow may hide beyond it: the sentinel asks GitHub for the last run of each such workflow. With `ci.group.reusable` the red workflows that call the same reusable workflow are shown as one shared cause and notified once; with `ci.failed_jobs` a red run says which of its jobs failed, grouped by platform. The workflows GitHub makes for itself (paths that start with `dynamic/`: Dependabot updates, the dependency graph, the default CodeQL, Copilot review and agent) have no file: they are never red CI and never *inactive*; a failing Dependabot update is listed apart as a warning and the others as information (`a2.services`). A red that nobody attends to *ages*: when the failing run is older than `ci.red_age_days` days (30 by default, switch `ci.red_ages`) and nothing newer of the events that decide has run, the workflow is shown as inactive, not red. | `runs_per_repo`, `cold_runs_per_repo`, `sentinel.a2_full_sample_unknown`, `sentinel.a2_resolve_max_calls_per_tick`, `sentinel.a2_resolve_ttl_seconds` | **bad** if any workflow is red; **unknown** (never green) when a repository has no run data or a workflow could not be resolved. Fix the workflow or re-run it; the lite edition shows the same figure, marked approximate because it guesses the default branch.failing Dependabot update also becomes an alert of its own with medium severity (`ci.dependabot_failed`, switch `ci.dependabot_alerts`, on by default), one per repository; a failing Copilot workflow can become a notice (`ci.copilot_activity`, switch `ci.copilot_alerts`, off by default). Both can be silenced like any alert. A  |
| **A3** | **Security alerts.** Open CodeQL alerts, Dependabot alerts and secret-scanning alerts per repository, with the severity, and how many are new since the last day of the history. | `sentinel.alerts_hot_seconds`, `sentinel.alerts_cold_seconds` | **bad** for any secret alert or critical/high alert; **warn** for any other; **unknown** while loading. Rotate a leaked secret first; then update or dismiss the rest. |
| **A4** | **Dependabot pull requests.** Open PRs by Dependabot with their age, a *major* version jump and a merge conflict; other people's PRs are only counted. Renovate counts like Dependabot (`sentinel.dependency_bots`). | `sentinel.stale_pr_days` (7), `sentinel.dependency_bots`, `sentinel.bots_apart` | **warn** if one is a major jump or conflicts; **info** if there are only PRs. Merge the green ones; rebase or close the conflicting ones. |
| **A5** | **Releases.** (a) *Candidate*: at least `candidate_min_entries` entries under `[Unreleased]` in the CHANGELOG and the last release older than `candidate_days` (or none). (b) A *green build* of a release workflow newer than the last release. (c) *Waiting for a signature*: a green build older than `pending_sign_hours` that is not signed and published; a signature counts only if it verifies against the public key of the ecosystem. | `sentinel.candidate_days` (2), `sentinel.candidate_min_entries` (1), `sentinel.skip_candidate_prefixes`, `sentinel.pending_sign_hours` (24), `sentinel.require_verified_signature` | **warn** with a candidate or a pending signature; **info** with green builds not yet released. Cut the release or sign the build. |
| **A6** | **Hygiene.** Per repository: the ruleset `protect-main` is ACTIVE, the label `dependencies` exists, the required files exist (by default README, LICENSE, CHANGELOG, SECURITY), SHA pinning is required, `allowed_actions` is `selected`, and no scheduled workflow was disabled by GitHub. The name of the ruleset is a setting (`sentinel.hygiene.ruleset_names`, patterns allowed); in `effective` mode the default branch counts as protected when GitHub reports a rule or a protection for it, whatever the ruleset is called; a licence file with another name (LICENSE-MIT, COPYING) counts, and the community profile and the account's `.github` repository can be counted too. What the token cannot know (no admin rights) is shown as *not evaluable*: never green and never a warning. In `effective` mode three public answers are joined (the rules of the rulesets, `protected` and the classic `protection` of the branch): a repository protected only in the classic way is protected, and an empty list of rules is never "no protection" by itself; each row of A6 says what protects the branch (`ruleset`, `classic`, `both`, `none`) or nothing when GitHub did not answer. `effective` is the default of `sentinel.hygiene.ruleset_mode`; `name` brings back the old rule of one ruleset with a given name. A fork is judged here (and in the lint of workflows and in the score) only when it has a CI of its own, that is a push, pull request, manual or merge queue run of its own in the last `ci.fork_own_ci_days` days (switch `ci.forks_need_own_ci`); a copied schedule does not count. The other forks are listed apart (`a6.forks_idle`) and not judged. With `upstream.enabled` (off by default) it also follows the original repository of each fork: the state of its checks and its latest release, and with `upstream.notify` the information notices `ci.upstream_red` and `ci.upstream_release`. | `sentinel.required_files`, `sentinel.hygiene_seconds`, `sentinel.hygiene.ruleset_mode`, `sentinel.hygiene.ruleset_names`, `sentinel.hygiene.skip`, `sentinel.hygiene.community_fallback`, `upstream.enabled`, `upstream.notify` | **warn** if any repository has a problem; **info** while some are not checked yet. Each problem names the fix. |
| **A7** | **Usage.** Actions minutes of the last 24 hours and 7 days per repository and ecosystem, the API allowance left, and the *budget* per ecosystem: **ok** below 80 %, **warn** from 80 %, **over** from 100 % of the ceiling. | `sentinel.min_rate_remaining` (800), `sentinel.minutes_budget`, `sentinel.minutes_budget_period` (7d) | **warn** if the allowance is under the limit or a budget reaches 80 %. Slow the refresh or trim long workflows. |
| **A8** | **Rounds.** Reads the audit and round files of the audit folder (the patterns of `sentinel.audit_files`) and shows their state. Empty if there is no audit folder. | `sentinel.audit_files.*`, `audit_dir` | **info** only. Nothing to do. |
| **A9** | **Roadmaps.** Whether the GitHub Projects boards of the ecosystems are *alive*: reconciled in the last 8 days and not older than their definitions. Needs the `read:project` scope of `gh`; without it the tab works from the definitions and says what is missing. | (fixed: 8 days) | **warn** if a board is stale or was never reconciled; **unknown** when not configured. |
| **A10** | **Surface of Actions and releases.** Twenty-five read-only checks on the clones and a few cold calls, listed in the table below. Each has a switch and, when it makes sense, a threshold. | `sentinel.surface.*` | Per check, see below. Paused when the allowance is low (the report says so). |
| **A11** | **Release readiness, ecosystem health and pins.** Readiness per repository (entries, CI, version, build, signing, next step); a health score 0-100 per ecosystem that subtracts weighted penalties for red, stuck, secrets, high alerts, alerts, stale PRs, unsigned builds and hygiene; and the dependency pins that are behind. A score is shown only when `min_coverage` of the repositories have data. A repository with no workflow at all (a clone without workflow files and no run) is not applicable: it does not lower the coverage and is listed apart; a group below the minimum shows "not enough data" with how many repositories have data and which ones lack it. | `sentinel.readiness.*` (`warn_below` 70, `min_coverage` 0.5) | **warn** when a score is below `warn_below`; **info** with repositories behind; **unknown** with too little data. |
| **A12** | **Analytics.** p50 / p95 of the duration of each workflow, of the queue time of its jobs and of each step; workflows slower than usual (`analytics.slow_factor`); *flaky* workflows (failed then passed on the same commit). Only a label: it never changes what counts as red. Times are measured on the latest attempt of a run: the first try of a re-run is never used (a re-run does not report days of queue or hundreds of days of duration; an unknown wait is left empty), and a retry after an approval is not flaky (`ci.rerun_timing` also asks GitHub for the real duration of finished re-runs). | `analytics.*` | No traffic light of its own. Look at the slower and flaky ones first. |
| **A13** | **Workflow linter.** Static rules on the local clones (and, with `lint.source` set to `auto` or `sparse`, on the files of the repositories without a clone, read from GitHub: a few calls a cycle inside the budget, a file whose SHA did not change is not read again; what cannot be read or checked is listed as *not evaluable* with its reason, such as SSO not authorised, no scope or no clone): `unpinned_uses`, `permissions`, `secrets_in_clear`, `injection`, `pr_target`. Each finding has a level (info / warning / error); a comment `# monitor-lint: ignore RULE reason` or `lint.ignore` silences one. | `lint.*` | Colour of the worst finding. Fix the errors first; the page filters by level. |

## The checks of A10

All of them are read-only suggestions for a person; the monitor never closes an issue, merges a pull request or publishes a release. Switch one off with `sentinel.surface.checks.<name>.enabled`.

| Check | What it looks for | Default |
|---|---|---|
| `workflows_disabled` | Workflows disabled by hand | on |
| `dead_schedule` | Schedules with no runs | on · days=14 |
| `unpinned_uses` | uses: not pinned by SHA | on |
| `broad_permissions` | Overly broad permissions (write-all) | on |
| `pr_target` | pull_request_target with a checkout of the PR | on |
| `stuck_concurrency` | Stuck concurrency (queued runs of the same workflow) | on · minutes=60 |
| `matrix_os` | Failures on only one system of the matrix | on · max_per_tick=4 |
| `artifacts` | Artifact cost | on · max_mb=500, retention_days=30 |
| `required_checks` | Required checks that are red or missing | on |
| `commit_state` | State of the last commit: every check and status, from every app | off · include_other_apps, include_statuses |
| `release_assets` | Incomplete published releases | on · recent_days=30, required, require_sha256, require_signature, allow_empty (a release without files is fine) |
| `tag_vs_version` | Tag against the version of the manifest | on · prefixes (`sentinel.surface.checks.tag_vs_version.prefixes`), prerelease_ok |
| `tag_vs_version` | Release tag vs manifest/CHANGELOG version | on |
| `packages` | GitHub Packages | on |
| `drafts` | Forgotten drafts and pre-releases | on · days=14 |
| `security_aged` | Critical/high alerts by age (repository ranking) | on · days=30 |
| `coverage` | Security coverage (CodeQL / Dependabot) | on |
| `secret_resolved` | Secret scanning: open vs resolved | on |
| `dependabot_priority` | Dependabot by priority | on |
| `issue_close` | Issues that could be closed (suggestion only) | on |
| `milestones` | Overdue milestones per ecosystem | on |
| `pr_human` | Aged human pull requests | on · days=7 |
| `pr_workflow_touch` | PRs that touch workflows or CODEOWNERS (priority) | on |
| `merge_queue` | Merge queue: approved with green CI | on |
| `maturity` | Manifest maturity vs evidence | on |
| `parity` | Broken 8-language README parity | on |
| `attestation` | Build attestations | on · max_per_tick=3 |

## Where everything is configured

Every threshold above is a setting of the **Sentinel**, **Surface checks (A10)**, **Readiness (A11)**, **Folders and files**, **Analytics** and **Workflow linter** tabs of the Settings page, and a key of `actions_monitor.json`. The full list with its ranges is in `SETTINGS.md`. The Help panel and `--help-topics sentinel` show this page offline.

## The second sentinel and the list of alerts

Besides this sentinel (CI), the complete edition has the **Collab sentinel**, which watches open issues and pull requests on a clock of its own and never writes to GitHub: [COLLAB.md](COLLAB.md). The **Alerts** tab puts the alerts of both in one list, with a filter by origin and level and local silences that end by themselves (`alerts.mute_hours`); `GET /api/alerts` serves the same list.

## The menu on the left: groups and sentinels

The menu has five groups with a title each (they fold, and the monitor remembers which): *Watch* (Now, Alerts, Charts), *Sentinels* (Summary, CI sentinel, Collab sentinel, Security sentinel), *Team* (Team health, Fleet, Repositories), *Reports and learning* (Reports, Scheduled reports, Lessons, History) and *System* (Settings). Every entry has its own address: `#team-health`, `#fleet`, `#team-reports`, `#reports`, `#lessons`, `#sentinel`, `#sentinel-ci`, `#sentinel-collab` and `#sentinel-security` (also `?view=` with the same words). The old addresses (`#team`, `#sent`, `#alerts/reports`, `#team/fleet`...) open the right panel.

The three sentinels can be switched on or off (`sentinel.enabled`, `sentinels.collab.enabled`, `sentinels.security.enabled`). The menu entry of a sentinel is there only while it is on, and the group *Sentinels* disappears when none is; the page follows the state at its next refresh. An address of a sentinel that is off still opens its panel, which says it is off and has a button that opens its switch in Settings. The panels A1 to A13 belong to the CI sentinel; the badge of each entry counts only the alerts of its own sentinel.
