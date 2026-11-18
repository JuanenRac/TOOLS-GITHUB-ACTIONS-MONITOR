<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](COMPARE_spa.md) | [🇫🇷 Français](COMPARE_fra.md) | [🇮🇹 Italiano](COMPARE_ita.md) | [🇩🇪 Deutsch](COMPARE_deu.md) | [🇨🇳 简体中文](COMPARE_zho.md) | [🇯🇵 日本語](COMPARE_jpn.md) | [🇵🇹 Português](COMPARE_por.md)

# Comparing periods

How did we do this week compared with last week? The comparison answers that with what the monitor already holds (the ledger of finished runs and alerts, and the hourly snapshots of the score). It reads nothing from GitHub, writes nothing, needs no AI and invents nothing. It exists in the Complete edition only and is **off** until you switch on `compare.enabled`.

## The two periods

- **Period**: the last 7 days (or 30, or any number up to 90), or an exact range with `from` and `to`.
- **Baseline**: `previous` (the period of the same length right before, the default), `year_ago` (the same dates one year earlier) or `custom` (`base_from` and `base_to`).
- **Days**: `all`, `workdays` or `weekend`. The filter is applied to every figure. The day of a moment is its day in the time zone of `display.timezone`; the workdays are `compare.workdays` (Monday = 1 to Sunday = 7, Monday to Friday by default). Bank holidays are not known: a holiday counts as the weekday it falls on.

Putting workdays and weekends together hides things (a failure that only happens on Saturdays weighs little in a week of mixed data), which is why the filter exists.

## The figures

| Figure | How it is worked out | Better when |
|---|---|---|
| `red_rate` | failed runs / (successful + failed runs) that started in the period | lower |
| `duration_p50` | median seconds of the successful runs | lower |
| `resolution` | median time from opening to closing of the alerts of the collaboration sentinel that closed in the period | lower |
| `score_mean` | mean score of the hourly snapshots that had a number | higher |
| `score_coverage` | mean share of the score that had data | higher |

Each figure travels with `now`, `base`, `delta`, a `direction` (`better`, `worse`, `same`) and its `state`. Cancelled, skipped and unfinished runs count neither way.

## When there is no figure

The comparison never shows a number it cannot stand behind: a missing figure is `null`, never 0 or 100.

- `insufficient_data`: fewer finished runs than `compare.min_runs_per_window`, fewer resolved alerts than `compare.min_resolved` or fewer snapshots than `compare.min_snapshots` in one of the two periods. The answer says which period and why (`missing`).
- `baseline_unavailable`: the period to compare against is not reliable. The reason is `history_too_short` (the monitor has watched less than `compare.min_days_of_history` days), `before_history` (that period is older than the data kept) or `no_history`. The figures of the current period are still shown.
- `calibrating`: the monitor has not watched for `score.calibrating_hours` yet. Nothing is compared.
- `off`: `compare.enabled` is off.

`data_quality` carries the runs counted in each period and `truncated` when the ledger had to drop old runs. `coverage` is the share of the figures that could be compared.

## What changed

Besides the figures: the repositories that got worse or better (change in their share of failed runs, only repositories with at least `compare.min_repo_runs` runs in both periods), the workflows that started failing and the ones that stopped failing, and the number of alerts opened in the period and still open at its end. Each list has at most `compare.top_changes` rows, ordered by the size of the change and then by name. The ledger keeps no repository for the alerts of the collaboration sentinel, so they appear as counts, never by name.

## How far back it reaches

The comparison reads the ledger of the score. While `compare.enabled` is on, the ledger keeps two periods of `compare.default_window_days` (at least 15 days) instead of the two windows of the score; it is never older than the monitor, so a new installation cannot compare 30 days against 30 days until it has 60 days of history. The doctor of the retention of events is not involved.

## The API

`GET /api/compare?window=7&days=workdays&baseline=previous` (also `from`, `to`, `base_from`, `base_to`). It answers `state`, `windows`, `metrics`, `changes`, `alerts`, `coverage` and `data_quality`. `format=ndjson` or `format=csv` give one row per figure. A request that makes no sense is a 400 with a stable `code`: `bad_range` (from after to, longer than 90 days, in the future), `bad_window`, `bad_days`, `bad_baseline` or `bad_format`. A viewer may read it; it serves the account of the process, never another one. With the read API v1 on it is also served under the prefix `/api/v1/`. It is not in the Lite edition.

## The command line

`monitor_cli.py compare [--window 7|30d] [--days all|workdays|weekend] [--baseline previous|year_ago] [--format table|json|ndjson|csv]`. Exit codes: 0 everything compared; 4 a figure has too little data, there is no baseline or the comparison is off; 5 with `--fail-on` when a figure got worse. `score --compare` keeps comparing the score with the history of its window.

## On the page

The Charts tab shows the section "Compare periods" when the comparison is on: a selector of period, days and baseline, one line per figure with its change, the alerts and the lists of changes.

## The settings

Settings, Sentinel tab, block Comparison of periods: `compare.enabled`, `compare.default_window_days`, `compare.default_days_filter`, `compare.workdays`, `compare.min_runs_per_window`, `compare.min_days_of_history`, `compare.min_resolved`, `compare.min_snapshots`, `compare.min_repo_runs`, `compare.top_changes`, `compare.include_in_report` and `compare.cache_seconds`. An answer is kept for `compare.cache_seconds` seconds and then computed again.
