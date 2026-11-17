<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](SCORE_spa.md) | [🇫🇷 Français](SCORE_fra.md) | [🇮🇹 Italiano](SCORE_ita.md) | [🇩🇪 Deutsch](SCORE_deu.md) | [🇨🇳 简体中文](SCORE_zho.md) | [🇯🇵 日本語](SCORE_jpn.md) | [🇵🇹 Português](SCORE_por.md)

# The score of an account

A number from 0 to 100, a letter from A to E and a trend, for each account, made only from what the monitor already knows (the finished runs and the alerts of the collaboration sentinel). It is in the Complete edition; Lite has no score.

## What it is made of

A weighted sum of five parts, each one from 0 to 100. A part is 100 at its **good** limit, 0 at its **bad** limit and linear in between. The weights and the limits are settings.

| Part | Weight | What it measures | Good | Bad |
|---|---|---|---|---|
| Reliability | 30 | share of the finished runs that succeed (cancelled and skipped runs do not count) | 98 % | 50 % |
| Speed | 15 | 95th percentile of the duration of the successful runs | 10 min | 60 min |
| Recovery | 15 | median time from the first failure of a workflow to its next success; a workflow that is still red counts the time it has been red so far | 30 min | 24 h |
| Collaboration | 15 | median time an alert of the collaboration sentinel stays open until it is gone | 2 days | 14 days |
| Security | 25 | the points that the open findings of the Security sentinel take off 100 (only while that sentinel is on) | 0 points | 100 points |

The letter is A from 90, B from 80, C from 70, D from 55 and E below. The trend compares the score with the window just before it: up, down or flat (a change smaller than `score.trend_flat` points is flat).

## When there is no number

The score never shows a number it cannot stand behind. The answer always carries its `state`, its `coverage` and its `data_quality`:

- **calibrating**: the account has been watched for less than `score.calibrating_hours` (24 by default). No number, no letter.
- **insufficient_data**: fewer than `score.min_runs` finished runs in the window (20 by default), or the parts that have data weigh less than `score.min_coverage` of the total (half by default). No number.
- **scored**: a number, a letter and a trend. A part without data is left out and the others are rescaled; that lowers the `coverage` (for example 0.85 when the collaboration sentinel is off). It is never counted as 0 and never as 100.

Security is a part like the others, but it only has data while the Security sentinel is on and has looked at enough repositories. Without it the answer says `complete: false` and lists `security` under `missing_parts`, and the other parts are rescaled, so the number is never read as an all clear. GitHub gives no history of the findings, so the security part is the same in the window and in the one before it: the trend shows what the CI and the collaboration did. The weights are 30, 15, 15, 15 and 25 by default. A window with runs and no failure at all has nothing to recover: its recovery part is full, as a fact and not as a gap.

A workflow that is still red at the end of the window is not forgotten: the recovery part counts the time it has been red so far, a lower bound that grows while the red lasts, so a failure that nobody fixes lowers the number more every hour. A fixed failure counts its real time. A re-run of a run counts as one more execution of the workflow, so the failed first attempt and the green second one are both seen. If you update from an earlier version, the numbers of an account with a workflow in red can be lower than before. When no part has any data the answer is `insufficient_data` with the reason `no_data`. The ledger keeps at most 20000 runs: when it had to drop runs that belong to the current window, `data_quality.truncated` is true and `truncated` is among the reasons, so a success rate that sees only part of the window is not read as complete. In `GET /api/score/global` an account whose snapshot is stale is left out of the mean and counted in `accounts_stale`, and `/metrics` does not export `ghamon_score` for a stale snapshot.

A failure that crosses the edge of the window is not forgotten either: the recovery part counts the stretch of the red that falls inside the window (the window before counted its own stretch, so no day is counted twice), and the ledger keeps the last failure of a workflow nobody has fixed for as long as the rule of the red still shows it (`ci.red_age_days`). In the same way an alert of the collaboration sentinel that is still open at the end of the window counts with the time it has been open so far, a lower bound, so leaving alerts unresolved lowers the collaboration part instead of leaving it without data. If you update from an earlier version, the numbers can be lower than before.

A repository is not healthy because it has nothing to show. Each watched repository is *active* (a run of its own newer than `ci.inactive_days` days), *dormant* (it has never run anything of its own) or *inactive* (its newest run is older than that): dormant and inactive repositories are neither green nor red and are counted apart (`activity` of the snapshot, the figures `dormant` and `inactive_repos`, the tooltip of the chip), so an account with hundreds of forks does not show a score made of nothing. A repository the monitor could not read is *unknown*, never dormant. `ci.dormant_repos` turns the counting off.

## The window

The window is the number of days of runs the score looks at: `score.window_days`, 7 by default, chosen by the user for each account. The window just before it, of the same length, gives the trend. The monitor keeps a small ledger of the finished runs it has seen, so the window can be longer than the list of latest runs the page shows. A snapshot is saved once an hour and kept as long as the history of the analytics (`retention.analytics_days`).

## By repository and by account

Each account has its own score. Its detail breaks it down by repository (the CI parts only, the worst first). There is no single number for the whole installation. Only for information, `GET /api/score/global` of the supervisor gives the mean of the scored accounts the asker may see, weighted by their repositories with a number, always with how many accounts are in it; an account without a number is listed and left out.

## On the page

A chip in the header, next to the readiness chips, shows the score: the number, the letter, an arrow with the change against the window before and a small line with the last days. Its colour follows the letter (A and B green, C amber, D and E red). While there is no number it is neutral and says why (calibrating, not enough data). A star after the letter means that a part is not counted yet (today, security): a high number is then not an all clear. Hovering over it shows the coverage, the parts with their weights and the weakest repository. The chip is not shown in Lite, nor when the score is off (`score.enabled`). While it calibrates the chip says how long is left of `score.calibrating_hours` (`data_quality.calibrating_hours` in the answer of the API), with a bar and the day and hour when the number will appear; with not enough data it says which condition fails (runs or coverage), and the hover also says why a part is not counted (a sentinel that is off, that has not finished its first sweep or that has read too few repositories).

## For other tools

The metrics (`/metrics`, when the Prometheus output is on) carry three series without labels: `ghamon_score_scored` (1 when the account has a number), `ghamon_score_coverage` (the share of the weights with data, from 0 to 1) and `ghamon_score` (the number, only while there is one: it is never exported as 0 when there is none). The MCP server has a read-only tool `get_score` with the answer of the API. `--demo` shows an invented score and writes nothing. The example Grafana dashboard (`docs/grafana/monitor_dashboard.json`) has a Score panel and a Score over time panel.

## The API

`GET /api/score` answers the latest snapshot of the account: `state`, `score`, `letter`, `trend`, `parts`, `coverage`, `data_quality`, `complete`, `missing_parts`, `repos`, `age_seconds` and `stale` (true when the snapshot is more than three hours old). `GET /api/score/history` answers the points over time, oldest first (`?hours=` back from now, 90 days at most, and `?limit=`, 2000 at most). A missing number is `null`, never 0. In the team mode anybody who may see the account may read its score; the weights and the limits are settings and only an administrator changes them.

## The alert on a drop

When the score falls by `score.alert.drop_points` points (10 by default) or more against the window before, or goes down to a lower letter, the Alerts tab shows the alert `score.dropped` (a warning; critical when the letter is E), with the old and the new score. It stays while the snapshot shows the drop and goes when the score recovers, and it can be silenced like any other alert. It is on for the panel by default. It goes out through the external notification channels (event `score_dropped`) only if `score.alert.notify_external` is on, which is off by default, and only the moment it appears. `score.alert.enabled` switches the alert off.

## The settings

In the Settings page, Sentinel sub-tab, blocks Account score, Score weights and Score letters: `score.enabled`, `score.window_days`, `score.calibrating_hours`, `score.min_runs`, `score.min_coverage`, `score.trend_flat`, `score.weights.reliability`, `score.weights.speed`, `score.weights.recovery`, `score.weights.collaboration`, `score.weights.security`, `score.grades.A` to `score.grades.D`, `score.alert.enabled`, `score.alert.drop_points` and `score.alert.notify_external` (off by default). The good and bad limits of every part are read from the file, under `score.limits` (see the example file); they are not edited in the page.
