<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](SENTINEL_SECURITY_spa.md) | [🇫🇷 Français](SENTINEL_SECURITY_fra.md) | [🇮🇹 Italiano](SENTINEL_SECURITY_ita.md) | [🇩🇪 Deutsch](SENTINEL_SECURITY_deu.md) | [🇨🇳 简体中文](SENTINEL_SECURITY_zho.md) | [🇯🇵 日本語](SENTINEL_SECURITY_jpn.md) | [🇵🇹 Português](SENTINEL_SECURITY_por.md)

# The Security sentinel

The third sentinel, next to the CI one and Collab. It reads, without writing anything to GitHub, what GitHub itself says is open or missing about the security of each repository, and turns it into alerts of the Alerts tab (origin Security). It is in the Complete edition, off by default (`sentinels.security.enabled`); Lite has no sentinels.

## What it reads and what it flags

| Signal | Alert | Level | On by default |
|---|---|---|---|
| Open Dependabot alerts at or above `min_severity` (high by default) | `security.dependabot` | critical if any is critical, error if any is high, else warning | yes |
| Open code scanning alerts at or above `min_severity` | `security.code_scanning` | the same | yes |
| Open secret scanning alerts | `security.secret` | always critical (a secret found by GitHub is a secret that is out) | yes |
| The default branch has no protection | `security.branch_unprotected` | warning | yes |
| The workflows get write permission by default | `security.workflow_write` | warning | yes |
| There is no CODEOWNERS file | `security.codeowners_missing` | info | no |
| A run that matters (a push to the default branch, a manual run, a `pull_request_target` run) that the monitor had seen was deleted | `security.runs_deleted` | error | no |

**Deleted runs** (`security.runs_deleted`, off by default): after a leak of secrets, deleting the run that printed them is the usual way to remove the trace, and GitHub leaves no visible record of it. With `sentinels.security.signals.runs_deleted.enabled` the sentinel keeps a short private list of the runs that matter it has seen and, when one is no longer in the list of runs, asks for that single run: an explicit 404 is a deletion; a refusal (403), a network error or a 5xx never counts. A run older than `sentinels.security.signals.runs_deleted.check_window_days` (14) is not asked for (the retention of the account may have purged it) and a deletion that was noticed stays as an alert for the same number of days. At most `sentinels.security.signals.runs_deleted.max_checks` (50) single runs are asked for per repository and round. The alert names the workflow, who started it and the branch, never any content of the run.

There is one alert per repository and signal, with the counts by severity in its details. Each signal can be switched off (`sentinels.security.signals.<signal>.enabled`) and, for Dependabot and code scanning, given another least severity. An archived repository is not asked for anything else.

## What it could not check

A source that GitHub does not answer for a repository (the feature is off there, or the login may not read it: 403, 404) is **not** an alert and is **not** a clean bill of health. It is listed in the status under `unavailable`, with how many repositories it concerns, and the page says it. The one exception is the protection of the default branch: GitHub answers 404 for a branch that has none, and that is the finding; a 403 there is only unreadable.

When most of what weighs in the penalty (Dependabot, code scanning, secrets) cannot be read, the level is `unknown`, not `ok`, and the security part of the score is left out instead of counting as 100; the status shows `sources_readable` and `sources_total`. If a source stops answering while an alert is open, the alert stays for a week (marked `unread_since`) and is never announced as fixed. A repository whose reads keep failing waits 5 minutes, 30 minutes and then 6 hours before the next try, so a few broken repositories never use up the whole round.

A source that the plan of the account does not have (branch protection or code scanning of a private repository on the free plan: GitHub answers that the feature needs another plan) is told apart from a refusal and from a feature that is off: the page and `unavailable_why` of the status say `N/A (plan)`, `N/A (no access)` or `N/A (off)`. With `sentinels.security.plan_na` on (the default) the sources of the first kind are left out of the readable count and of the coverage of the score and are counted apart as `sources_na_plan`; none of the three is a finding and none is a clean bill of health, so a sentinel whose plan has none of what weighs is `unknown` and gives the score no security part. With it off they count as sources that could not be read.

Every sentinel now tells its **lifecycle**: `healthy`, `degraded` (some reads fail, a source cannot be read, or it has not finished its first look), `paused` (waiting for the GitHub allowance), `error` (it fails and has read nothing yet) or `off`. "No alerts" only means something when the lifecycle is `healthy`.

## Cost

A round reads at most `sentinels.security.max_repos_per_tick` repositories (5 by default), the ones looked at longest ago first and the ones with an open alert a little sooner, a cycle every `sentinels.security.refresh_seconds` (30 minutes by default). Each repository costs at most seven reads, almost all of them conditional, so a repository that did not change costs no allowance; the CODEOWNERS file, when asked for, is looked for at most once a day. The sentinel pauses while the allowance left is below `sentinels.security.min_rate_remaining`. Its state (`security_state.json`) keeps the open alerts, so a restart announces nothing again, and the first look at a repository writes no event. A round also stops starting new repositories after `sentinels.security.deadline_s` seconds (30 by default; 0 = no ceiling): the ones not reached wait for the next round and the status lists them by name as `unchecked` (with `round_cut`) instead of counting them as zero alerts.

## One owner for each finding

The panels of the Sentinel tab that already showed security figures (alerts by repository, aged alerts, coverage of Dependabot and CodeQL, Dependabot pull requests) stay as panels. The alerts of the Alerts tab about these signals come only from this sentinel, so nothing is raised twice. The content of each workflow file (actions not pinned to a commit, `write-all`, no permissions block, `pull_request_target` with a checkout) belongs to the [Supply chain sentinel](SENTINEL_SUPPLY.md); `security.workflow_write` stays here because it is a setting of the repository.

## Events and notifications

A new finding writes the event `security_new` and a closed one `security_fixed` to the feed, with the notification channels hung on it; both are kinds the person can ask for in the notification settings, and the per-user preferences have a Security box. Nothing is announced the first time a repository is looked at.

## The settings

In the Settings page, Sentinel sub-tab, block Security: `sentinels.security.enabled`, `sentinels.security.refresh_seconds`, `sentinels.security.max_repos_per_tick`, `sentinels.security.min_rate_remaining`, `sentinels.security.repos`, `sentinels.security.plan_na`, `sentinels.security.signals.dependabot.enabled`, `sentinels.security.signals.dependabot.min_severity`, `sentinels.security.signals.code_scanning.enabled`, `sentinels.security.signals.code_scanning.min_severity`, `sentinels.security.signals.secret.enabled`, `sentinels.security.signals.branch.enabled`, `sentinels.security.signals.workflow.enabled` and `sentinels.security.signals.codeowners.enabled`, `sentinels.security.signals.runs_deleted.enabled`, `sentinels.security.signals.runs_deleted.check_window_days`, `sentinels.security.signals.runs_deleted.max_checks`. The points each finding takes off the security part of the score (`sentinels.security.penalty`) are read from the file; see the example file.

## Branch protection by ruleset

A default branch counts as protected when it has the classic branch protection **or** an active ruleset (GitHub answers 404 to the classic endpoint for a repository protected only by a ruleset, so the sentinel also reads the `protected` flag of the branch and the active rules of the branch). `signals.branch.require` can list rule types (for example `pull_request`, `required_status_checks`) that the rules must have; a protected branch that lacks one is flagged with the missing ones. The default is an empty list: any protection is enough. A repository that could not be read because the call timed out is listed with its cause (`timeout`, `rate`, `network`, `error`) under `errors` and `error_kinds` of the status; it is never a finding.
