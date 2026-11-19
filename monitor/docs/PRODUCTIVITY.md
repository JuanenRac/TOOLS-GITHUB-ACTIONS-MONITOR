<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](PRODUCTIVITY_spa.md) | [🇫🇷 Français](PRODUCTIVITY_fra.md) | [🇮🇹 Italiano](PRODUCTIVITY_ita.md) | [🇩🇪 Deutsch](PRODUCTIVITY_deu.md) | [🇨🇳 简体中文](PRODUCTIVITY_zho.md) | [🇯🇵 日本語](PRODUCTIVITY_jpn.md) | [🇵🇹 Português](PRODUCTIVITY_por.md)

# What the monitor saves: an estimate and how to measure it

This guide explains the figures in the README. They are an estimate made from a simple model, not a measurement taken on your repositories. Measure your own before relying on them.

## The figures

- About 85-95 % of the time spent watching CI and triaging failures.
- About 15-25 % of the overall productivity of a team, as a consequence of the first figure.

## How the estimate is built

Time saved in a week = the sum, over the tasks, of (times a week x minutes each time without the monitor) x the saving of that task. The tasks are watching every workflow, deciding what is really red, finding the cause of a failed run and learning of a failure in time. The estimate assumes:

1. There are many repositories with several workflows each, so looking at them by hand means opening many pages again and again.
2. Without the monitor, someone checks the Actions tabs by hand and reads each failed log to find the cause. With it, the page and the alerts already say which workflow is red and why.
3. Failures happen every week. A team with no failures has nothing to triage.
4. The saving covers only watching and triage. Fixing a failure takes the same time with or without the monitor, and it is not counted.

The two figures agree only if watching and triage take about 16-29 % of the working time of the team (0.15 / 0.95 to 0.25 / 0.85). If they take less in your team, the overall gain is lower.

## When it saves less

- A few repositories or a single workflow: there is little to watch.
- Nobody watches CI by hand today, or you already have alerts that name the cause.
- The alerts are not read. Reading them takes time too, and the saving disappears if they are ignored or silenced without a reason.

## How to measure it in your own use

1. Before: for one normal week, write down each time you look at CI by hand (minutes) and each failed run you triage (minutes until you know the cause).
2. After: repeat the same notes for a week with the monitor open. The score (time to recover) and the book of failures (trend over 24 hours and 7 days) show whether failures are closed faster.
3. For each group, the saving is 1 - after / before. Compare it with 85-95 %.
4. For the overall gain, divide the hours saved by the total hours worked in that week. Compare it with 15-25 %.

### Example with invented numbers

Someone spends 20 minutes a day looking at the Actions tabs (100 minutes in a five-day week) and triages 4 failed runs a week at 30 minutes each (120 minutes): 220 minutes in all. At 85-95 % saved, between 187 and 209 minutes are left free. These numbers are made up to show the calculation; use your own.
