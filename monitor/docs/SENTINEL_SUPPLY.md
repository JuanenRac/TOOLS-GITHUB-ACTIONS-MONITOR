<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](SENTINEL_SUPPLY_spa.md) | [🇫🇷 Français](SENTINEL_SUPPLY_fra.md) | [🇮🇹 Italiano](SENTINEL_SUPPLY_ita.md) | [🇩🇪 Deutsch](SENTINEL_SUPPLY_deu.md) | [🇨🇳 简体中文](SENTINEL_SUPPLY_zho.md) | [🇯🇵 日本語](SENTINEL_SUPPLY_jpn.md) | [🇵🇹 Português](SENTINEL_SUPPLY_por.md)

# The Supply chain sentinel

The fourth sentinel, next to the CI one, Collab and Security. It reads, without writing anything to GitHub, the workflow files of each repository (`.github/workflows`, through the API, no clone needed) and flags what lets a moved tag or an outsider act with the repository's token and code. It turns them into alerts of the Alerts tab (origin Supply chain). It is in the Complete edition, off by default (`sentinels.supply.enabled`); Lite has no sentinels.

## What it flags

| Signal | Alert | Level | On by default |
|---|---|---|---|
| A `uses:` of an action or reusable workflow not pinned to a full commit SHA (a tag can be moved by its owner) | `actions.supply.unpinned` | warning | yes |
| A `uses:` that follows a branch that moves by itself (`@main`, `@master`...): worse than a tag | `actions.supply.mutable_ref` | warning | yes |
| A workflow with `permissions: write-all` | `actions.supply.permissions_wide` | warning | yes |
| A workflow with no `permissions:` block (the token gets the broader default) | `actions.supply.permissions_missing` | warning | yes |
| `pull_request_target` together with a checkout of the pull request's code | `actions.supply.pr_target_checkout` | error | yes |

There is one alert per repository and signal, with the number of findings, the files where they are and a few examples (the name of an action) in its details. Each signal can be switched off (`sentinels.supply.signals.<signal>.enabled`) and given another level (`info`, `warning`, `error`, `critical`). A `uses:` of a workflow of the same repository is not a third party and is left out.

## One source of truth

There are no rules of its own: the findings come from the linter of workflows (`bin/lint_workflows.py`, the same one the Sentinel tab and the command line use), only `unpinned_uses`, `permissions` and `pr_target` are switched on here and every other rule stays off. In particular the rule that looks for secrets written in a file is off, so **the value of a secret is never read, stored or shown**. The `lint.own_owners` and `lint.unpinned_own` settings still decide how an action of your own account is treated, and a comment `# monitor-lint: ignore RULE` in a workflow silences a finding where it is.

## One owner for each finding

`security.workflow_write` (Security sentinel) is the default permission of the repository, a setting of GitHub; the signals here are about the content of each workflow file, so a repository never raises the same finding from both. The panel of the lint of the Sentinel tab stays as a panel; the alerts of the Alerts tab about these signals come only from here.

## What it could not check

A repository whose workflows cannot be read (no access, SSO not authorised, allowance spent, a folder with too many files) is **not** an alert and is **not** a clean bill of health. It is listed in the status under `unavailable`, with the reason and how many repositories, and a level `ok` is shown as `unknown` when most of what was looked at could not be read. If a repository stops answering while it has alerts, they stay for a week (marked `unread_since`) and are never announced as fixed. A repository without a `.github/workflows` folder is read and simply has nothing to report. A repository whose reads keep failing waits 5 minutes, 30 minutes and then 6 hours before the next try.

## Cost

A round reads at most `sentinels.supply.max_repos_per_tick` repositories (10 by default) and makes at most `sentinels.supply.max_calls_per_tick` calls (60): one to list the workflows of a repository and one more for each file that is new or changed, because a file whose SHA did not change is never read again. The ones read longest ago come first and the ones with an open alert a little sooner; a cycle every `sentinels.supply.refresh_seconds` (one hour by default). The sentinel pauses while the allowance left is below `sentinels.supply.min_rate_remaining`. Its state (`supply_state.json`) keeps the open alerts, so a restart announces nothing again, and the first look at a repository writes no event. `sentinels.supply.max_files_per_repo` limits the files read in one repository; a repository over the limit is read in part and counted as partial.

## Ignoring a finding

`sentinels.supply.ignore` takes patterns `repository:file:rule` (with `*` for any) that name the rule of the linter, for example `myrepo:release.yml:unpinned_uses`; note that `unpinned_uses` is the rule behind both `unpinned` and `mutable_ref`, and `permissions` is the one behind both permission signals. The same patterns of `lint.ignore` are not applied here.

## Events, notifications and the score

A new finding writes the event `security_new` and a closed one `security_fixed` (the event says `sentinel: supply` and the code of the alert), so the Security box of the per-user notification preferences and the channels decide who hears about it. Nothing is announced the first time a repository is looked at. The metrics carry `supply_alerts`, `supply_findings`, `supply_penalty` (informative: `sentinels.supply.penalty.per_finding`, 2, and `cap_per_repo`, 10, are read from the file), `supply_repos_checked`, `supply_repos_unreadable` and `supply_calls_last_hour`. The score does not use the penalty. The API answers `GET /api/sentinel/supply` and the Alerts tab and `monitor_cli.py alerts --sentinel supply` filter by it.

## The settings

In the Settings page, Sentinel sub-tab, block Supply chain: `sentinels.supply.enabled`, `sentinels.supply.refresh_seconds`, `sentinels.supply.max_repos_per_tick`, `sentinels.supply.max_calls_per_tick`, `sentinels.supply.max_files_per_repo`, `sentinels.supply.min_rate_remaining`, `sentinels.supply.repos`, `sentinels.supply.ignore`, `sentinels.supply.signals.unpinned.enabled`, `sentinels.supply.signals.unpinned.level`, `sentinels.supply.signals.mutable_ref.enabled`, `sentinels.supply.signals.mutable_ref.level`, `sentinels.supply.signals.permissions_wide.enabled`, `sentinels.supply.signals.permissions_wide.level`, `sentinels.supply.signals.permissions_missing.enabled`, `sentinels.supply.signals.permissions_missing.level`, `sentinels.supply.signals.pr_target_checkout.enabled`, `sentinels.supply.signals.pr_target_checkout.level`.

## What it does not do

It does not write to GitHub (no pull request, no label, no issue), does not propose the SHA of an action to pin and does not read the value of any secret.
