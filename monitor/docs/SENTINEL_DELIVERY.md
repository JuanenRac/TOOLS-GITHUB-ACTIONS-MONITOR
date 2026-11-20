<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](SENTINEL_DELIVERY_spa.md) | [🇫🇷 Français](SENTINEL_DELIVERY_fra.md) | [🇮🇹 Italiano](SENTINEL_DELIVERY_ita.md) | [🇩🇪 Deutsch](SENTINEL_DELIVERY_deu.md) | [🇨🇳 简体中文](SENTINEL_DELIVERY_zho.md) | [🇯🇵 日本語](SENTINEL_DELIVERY_jpn.md) | [🇵🇹 Português](SENTINEL_DELIVERY_por.md)

# The Delivery sentinel

The fifth sentinel, next to the CI one, Collab, Security and Supply chain. It reads, without writing anything to GitHub, the latest releases, the latest tags, the CHANGELOG and the version files you name of each repository (through the API, no clone needed) and flags what was built but not delivered. It turns them into alerts of the Alerts tab (origin Delivery). It is in the Complete edition, off by default (`sentinels.delivery.enabled`); Lite has no sentinels.

It has its own entry in the Sentinel group of the menu, **Delivery sentinel** (address `#sentinel-delivery`), shown while the sentinel is on: one panel with the open findings of each repository, the state of its cycle and what could not be read; the badge of the entry counts the errors.

## What it flags

| Signal | Alert | Level | On by default |
|---|---|---|---|
| The CHANGELOG has entries under `[Unreleased]` and the latest published release is older than `sentinels.delivery.unreleased_days` (14) | `release.unreleased_pending` | info | yes |
| A version tag newer than the latest published release that has no release of its own (a draft does not count as delivered) | `release.tag_without_release` | warning | yes |
| The latest published release has an empty description | `release.release_without_notes` | info | yes |
| The version files you list in `version_files` and the first versioned heading of the CHANGELOG do not all say the same version (`1.2` and `1.2.0` are the same) | `release.version_mismatch` | warning | yes |
| A repository pins an older version than the latest release of the repository that provides a shared contract (the pin tables of `sentinel.readiness.pins.sources`, kind `pin_table`) | `release.ecosystem_drift` | warning | yes |
| The latest published release has no file for one of the patterns of `expected_assets` (for example `*.zip`, `SHA256SUMS*`) | `release.assets_missing` | warning | yes |

There is one alert per repository and signal, with the numbers and a few tags, patterns or versions in its details. Each signal can be switched off (`sentinels.delivery.signals.<signal>.enabled`) and given another level (`info`, `warning`, `error`, `critical`). A repository with no published release at all is not judged by the signals about releases: it does not use them. Pre-releases and drafts are never taken as the latest release.

## One owner for each finding

The readiness panel of the Sentinel tab (A11) is one row per repository drawn from local clones; this sentinel produces alerts with a stable id, silences, events and its own cycle, read through the API with no clone. The signals about the workflows of a repository belong to the Supply chain sentinel and the ones about the settings of GitHub to Security: nothing is raised twice. The optional Releases plugin of the roadmap is replaced by this sentinel.

## What it could not check

A repository that cannot be read (no access, SSO not authorised, allowance spent, a round with fewer calls than one repository needs) is **not** an alert and is **not** a clean bill of health. It is listed in the status under `unavailable`, with the reason and how many, and a level `ok` is shown as `unknown` when most of what was looked at could not be read. If a repository stops answering while it has alerts, they stay for a week (marked `unread_since`) and are never announced as fixed. A file that does not exist (no CHANGELOG at that path, no such version file) is simply absent. The pin tables are read once per cycle; one that cannot be read keeps the alerts it had and is listed too.

## Cost

A round reads at most `sentinels.delivery.max_repos_per_tick` repositories (10 by default) and makes at most `sentinels.delivery.max_calls_per_tick` calls (60): one for the releases and one for the tags, one for the CHANGELOG (more if you list several paths and the first ones do not exist) and one for each version file. A signal that is switched off is not read at all. The ones read longest ago come first and the ones with an open alert a little sooner; a cycle every `sentinels.delivery.refresh_seconds` (one hour by default). There are no conditional requests: the cost is bounded by these settings, not by an answer 304. The sentinel pauses while the allowance left is below `sentinels.delivery.min_rate_remaining`. Its state (`delivery_state.json`) keeps the open alerts, so a restart announces nothing again, and the first look at a repository writes no event. A round also stops starting new repositories after `sentinels.delivery.deadline_s` seconds (30 by default; 0 = no ceiling): the ones not reached wait for the next round and the status lists them by name as `unchecked` (with `round_cut`) instead of counting them as zero alerts.

## Events, notifications and the score

A new finding writes the event `delivery_new` and a closed one `delivery_fixed` (the event says `sentinel: delivery` and the code of the alert). They belong to the family of releases, so only maintainers and administrators can choose them, and the choice of the `ci` sentinel in the per-user notification preferences decides who hears about them; they are in no default list of events. The metrics carry `delivery_alerts`, `delivery_unreleased_repos`, `delivery_unreleased_days_max`, `delivery_repos_checked`, `delivery_repos_unreadable` and `delivery_calls_last_hour`. The score does not use them. The API answers `GET /api/sentinel/delivery` and the Alerts tab and `monitor_cli.py alerts --sentinel delivery` filter by it.

## The settings

In the Settings page, Sentinel sub-tab, block Delivery: `sentinels.delivery.enabled`, `sentinels.delivery.refresh_seconds`, `sentinels.delivery.max_repos_per_tick`, `sentinels.delivery.max_calls_per_tick`, `sentinels.delivery.min_rate_remaining`, `sentinels.delivery.repos`, `sentinels.delivery.unreleased_days`, `sentinels.delivery.unreleased_min_entries`, `sentinels.delivery.changelog_paths`, `sentinels.delivery.version_files`, `sentinels.delivery.expected_assets`, `sentinels.delivery.signals.unreleased_pending.enabled`, `sentinels.delivery.signals.unreleased_pending.level`, `sentinels.delivery.signals.tag_without_release.enabled`, `sentinels.delivery.signals.tag_without_release.level`, `sentinels.delivery.signals.release_without_notes.enabled`, `sentinels.delivery.signals.release_without_notes.level`, `sentinels.delivery.signals.version_mismatch.enabled`, `sentinels.delivery.signals.version_mismatch.level`, `sentinels.delivery.signals.ecosystem_drift.enabled`, `sentinels.delivery.signals.ecosystem_drift.level`, `sentinels.delivery.signals.assets_missing.enabled`, `sentinels.delivery.signals.assets_missing.level`.

## What it does not do

It does not write to GitHub (no tag, release, label, pull request or issue), does not publish or sign anything, does not create proposals from its alerts and does not read the content of any file but the CHANGELOG and the version files you name.

## Ecosystem drift is information by default

`release.ecosystem_drift` compares the pin of each repository in the pin table of the provider (for example `registry/contract_pins.json` of the contract repository, the version each consumer was last checked against) with the latest published release of the provider. A repository that is behind is reported at level `info` by default, because the pins are brought up by the release train of the ecosystem and not by hand; `signals.ecosystem_drift.level` raises it. Reads that time out are listed under `unavailable` with the reason `timeout`.
