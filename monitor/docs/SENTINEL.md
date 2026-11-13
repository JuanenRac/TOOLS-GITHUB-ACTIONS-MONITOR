<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](SENTINEL_spa.md) | [🇫🇷 Français](SENTINEL_fra.md) | [🇮🇹 Italiano](SENTINEL_ita.md) | [🇩🇪 Deutsch](SENTINEL_deu.md) | [🇨🇳 简体中文](SENTINEL_zho.md) | [🇯🇵 日本語](SENTINEL_jpn.md) | [🇵🇹 Português](SENTINEL_por.md)

# The sentinel and its checks A1-A13

The **sentinel** is the second half of the complete edition. The *monitor* shows what is running and what failed right now; the *sentinel* looks at the whole account every few minutes and answers a different question: **what needs a person**. It reads GitHub (never writes to it), keeps a short history on this computer and turns everything it finds into thirteen numbered checks, **A1 to A13**, one traffic light each.

**The lite edition does not include it.** `MONITOR_LITE_GITHUB_ACTIONS` (port 8766) has no sentinel: the module is not even imported and its endpoints answer 404. The complete edition (`MONITOR_GITHUB_ACTIONS`, port 8765) starts it by itself; switch it off with `sentinel.enabled` (Settings > Sentinel). Both editions use the same rule for "red on main" (A2), so their figures agree.

## How it starts and what it costs

It starts with the complete monitor and runs in the same process, in its own thread, with its own budget of GitHub calls (`sentinel.budget_per_hour`, 600 by default, and `sentinel.max_calls_per_tick`). When the allowance of GitHub is below `sentinel.min_rate_remaining` it stops asking and the page says it is paused for quota. Nothing it does writes to GitHub.

## Files it writes (next to the monitor, never published)

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
| **A1** | **Builds.** A run that is in progress or queued for longer than the limit is *stuck*. Open issues labelled `build-failed` or `build-stuck` are listed too. Runs of the event `dynamic` (Dependabot internals) are ignored. | `stuck_minutes` | **bad** if anything is stuck or an issue is open. Open the run, cancel or re-run it; close the issue when it is fixed. |
| **A2** | **Red CI.** For each workflow file, the LAST COMPLETED run on the DEFAULT branch: it is red when it failed (`failure`, `timed_out`, `startup_failure`, `action_required`). Runs that are `cancelled`, `skipped`, `neutral` or `stale`, runs in progress and runs of other branches say nothing and never hide an older red. *Streak* = consecutive reds. When a repository's run list is as long as the sample asked for, a workflow may hide beyond it: the sentinel asks GitHub for the last run of each such workflow. | `runs_per_repo`, `cold_runs_per_repo`, `sentinel.a2_full_sample_unknown`, `sentinel.a2_resolve_max_calls_per_tick`, `sentinel.a2_resolve_ttl_seconds` | **bad** if any workflow is red; **unknown** (never green) when a repository has no run data or a workflow could not be resolved. Fix the workflow or re-run it; the lite edition shows the same figure, marked approximate because it guesses the default branch. |
| **A3** | **Security alerts.** Open CodeQL alerts, Dependabot alerts and secret-scanning alerts per repository, with the severity, and how many are new since the last day of the history. | `sentinel.alerts_hot_seconds`, `sentinel.alerts_cold_seconds` | **bad** for any secret alert or critical/high alert; **warn** for any other; **unknown** while loading. Rotate a leaked secret first; then update or dismiss the rest. |
| **A4** | **Dependabot pull requests.** Open PRs by Dependabot with their age, a *major* version jump and a merge conflict; other people's PRs are only counted. | `sentinel.stale_pr_days` (7) | **warn** if one is a major jump or conflicts; **info** if there are only PRs. Merge the green ones; rebase or close the conflicting ones. |
| **A5** | **Releases.** (a) *Candidate*: at least `candidate_min_entries` entries under `[Unreleased]` in the CHANGELOG and the last release older than `candidate_days` (or none). (b) A *green build* of a release workflow newer than the last release. (c) *Waiting for a signature*: a green build older than `pending_sign_hours` that is not signed and published; a signature counts only if it verifies against the public key of the ecosystem. | `sentinel.candidate_days` (2), `sentinel.candidate_min_entries` (1), `sentinel.skip_candidate_prefixes`, `sentinel.pending_sign_hours` (24), `sentinel.require_verified_signature` | **warn** with a candidate or a pending signature; **info** with green builds not yet released. Cut the release or sign the build. |
| **A6** | **Hygiene.** Per repository: the ruleset `protect-main` is ACTIVE, the label `dependencies` exists, the required files exist (by default README, LICENSE, CHANGELOG, SECURITY), SHA pinning is required, `allowed_actions` is `selected`, and no scheduled workflow was disabled by GitHub. | `sentinel.required_files`, `sentinel.hygiene_seconds` | **warn** if any repository has a problem; **info** while some are not checked yet. Each problem names the fix. |
| **A7** | **Usage.** Actions minutes of the last 24 hours and 7 days per repository and ecosystem, the API allowance left, and the *budget* per ecosystem: **ok** below 80 %, **warn** from 80 %, **over** from 100 % of the ceiling. | `sentinel.min_rate_remaining` (800), `sentinel.minutes_budget`, `sentinel.minutes_budget_period` (7d) | **warn** if the allowance is under the limit or a budget reaches 80 %. Slow the refresh or trim long workflows. |
| **A8** | **Rounds.** Reads the audit and round files of the audit folder (the patterns of `sentinel.audit_files`) and shows their state. Empty if there is no audit folder. | `sentinel.audit_files.*`, `audit_dir` | **info** only. Nothing to do. |
| **A9** | **Roadmaps.** Whether the GitHub Projects boards of the ecosystems are *alive*: reconciled in the last 8 days and not older than their definitions. Needs the `read:project` scope of `gh`; without it the tab works from the definitions and says what is missing. | (fixed: 8 days) | **warn** if a board is stale or was never reconciled; **unknown** when not configured. |
| **A10** | **Surface of Actions and releases.** Twenty-five read-only checks on the clones and a few cold calls, listed in the table below. Each has a switch and, when it makes sense, a threshold. | `sentinel.surface.*` | Per check, see below. Paused when the allowance is low (the report says so). |
| **A11** | **Release readiness, ecosystem health and pins.** Readiness per repository (entries, CI, version, build, signing, next step); a health score 0-100 per ecosystem that subtracts weighted penalties for red, stuck, secrets, high alerts, alerts, stale PRs, unsigned builds and hygiene; and the dependency pins that are behind. A score is shown only when `min_coverage` of the repositories have data. | `sentinel.readiness.*` (`warn_below` 70, `min_coverage` 0.5) | **warn** when a score is below `warn_below`; **info** with repositories behind; **unknown** with too little data. |
| **A12** | **Analytics.** p50 / p95 of the duration of each workflow, of the queue time of its jobs and of each step; workflows slower than usual (`analytics.slow_factor`); *flaky* workflows (failed then passed on the same commit). Only a label: it never changes what counts as red. | `analytics.*` | No traffic light of its own. Look at the slower and flaky ones first. |
| **A13** | **Workflow linter.** Static rules on the local clones: `unpinned_uses`, `permissions`, `secrets_in_clear`, `injection`, `pr_target`. Each finding has a level (info / warning / error); a comment `# monitor-lint: ignore RULE reason` or `lint.ignore` silences one. | `lint.*` | Colour of the worst finding. Fix the errors first; the page filters by level. |

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
| `release_assets` | Incomplete published releases | on · recent_days=30, required |
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
