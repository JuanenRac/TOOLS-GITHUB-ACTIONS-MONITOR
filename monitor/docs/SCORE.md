<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](SCORE_spa.md) | [🇫🇷 Français](SCORE_fra.md) | [🇮🇹 Italiano](SCORE_ita.md) | [🇩🇪 Deutsch](SCORE_deu.md) | [🇨🇳 简体中文](SCORE_zho.md) | [🇯🇵 日本語](SCORE_jpn.md) | [🇵🇹 Português](SCORE_por.md)

# The score of an account

A number from 0 to 100, a letter from A to E and a trend, for each account, made only from what the monitor already knows (the finished runs and the alerts of the collaboration sentinel). It is in the Complete edition; Lite has no score.

## What it is made of

A weighted sum of four parts, each one from 0 to 100. A part is 100 at its **good** limit, 0 at its **bad** limit and linear in between. The weights and the limits are settings.

| Part | Weight | What it measures | Good | Bad |
|---|---|---|---|---|
| Reliability | 40 | share of the finished runs that succeed (cancelled and skipped runs do not count) | 98 % | 50 % |
| Speed | 20 | 95th percentile of the duration of the successful runs | 10 min | 60 min |
| Recovery | 20 | median time from the first failure of a workflow to its next success | 30 min | 24 h |
| Collaboration | 20 | median time an alert of the collaboration sentinel stays open until it is gone | 2 days | 14 days |

The letter is A from 90, B from 80, C from 70, D from 55 and E below. The trend compares the score with the window just before it: up, down or flat (a change smaller than `score.trend_flat` points is flat).

## When there is no number

The score never shows a number it cannot stand behind. The answer always carries its `state`, its `coverage` and its `data_quality`:

- **calibrating**: the account has been watched for less than `score.calibrating_hours` (24 by default). No number, no letter.
- **insufficient_data**: fewer than `score.min_runs` finished runs in the window (20 by default), or the parts that have data weigh less than `score.min_coverage` of the total (half by default). No number.
- **scored**: a number, a letter and a trend. A part without data is left out and the others are rescaled; that lowers the `coverage` (for example 0.8 when the collaboration sentinel is off). It is never counted as 0 and never as 100.

Security is not a part yet. Until it is, every answer says `complete: false` and lists `security` under `missing_parts`, so a score of 85 is never read as "all clear".

## The window

The window is the number of days of runs the score looks at: `score.window_days`, 7 by default, chosen by the user for each account. The window just before it, of the same length, gives the trend. The monitor keeps a small ledger of the finished runs it has seen, so the window can be longer than the list of latest runs the page shows. A snapshot is saved once an hour and kept as long as the history of the analytics (`retention.analytics_days`).

## By repository and by account

Each account has its own score. Its detail breaks it down by repository (the CI parts only, the worst first). There is no single number for the whole installation.

## The API

`GET /api/score` answers the latest snapshot of the account: `state`, `score`, `letter`, `trend`, `parts`, `coverage`, `data_quality`, `complete`, `missing_parts`, `repos`, `age_seconds` and `stale` (true when the snapshot is more than three hours old). `GET /api/score/history` answers the points over time, oldest first (`?hours=` back from now, 90 days at most, and `?limit=`, 2000 at most). A missing number is `null`, never 0. In the team mode anybody who may see the account may read its score; the weights and the limits are settings and only an administrator changes them.

## The settings

In the Settings page, Sentinel sub-tab, blocks Account score, Score weights and Score letters: `score.enabled`, `score.window_days`, `score.calibrating_hours`, `score.min_runs`, `score.min_coverage`, `score.trend_flat`, `score.weights.reliability`, `score.weights.speed`, `score.weights.recovery`, `score.weights.collaboration`, `score.grades.A` to `score.grades.D`, `score.alert.enabled`, `score.alert.drop_points` and `score.alert.notify_external` (off by default). The good and bad limits of every part are read from the file, under `score.limits` (see the example file); they are not edited in the page.
