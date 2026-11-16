<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](HEALTH_spa.md) | [🇫🇷 Français](HEALTH_fra.md) | [🇮🇹 Italiano](HEALTH_ita.md) | [🇩🇪 Deutsch](HEALTH_deu.md) | [🇨🇳 简体中文](HEALTH_zho.md) | [🇯🇵 日本語](HEALTH_jpn.md) | [🇵🇹 Português](HEALTH_por.md)

# The health of a repository and of the team

Complete only. Two read-only views, made from what the monitor already holds (runs, red and stuck workflows, the open alerts of every sentinel and the readiness of the releases). They never call GitHub.

## What a repository's health is made of

| Part | What it says |
|---|---|
| CI | successes and failures of the last 24 hours, the workflows that are red now, the runs that are stuck |
| Alerts | every open alert of the CI, Collab and Security sentinels, by sentinel and by level |
| Release | the row of the readiness of the releases, when the repository has one |
| Activity | when the last run started and how many runs there were in 7 days |
| What looked at it | the lifecycle of each sentinel: healthy, degraded, paused, error or off |

The state is **bad** (a red workflow, or an alert of level critical or error), **warning** (a warning alert or a stuck run), **OK**, or **not seen** (nothing to judge by). A repository that no sentinel looked at, or that a sentinel could not read, is never shown as OK: it says "not fully seen by" and lists who. The risk is the number the ranking sorts by: every red workflow (30), stuck run (10), critical alert (25), error (10), warning (3) and info (1) adds points, the same for every repository. When every sentinel is in error, paused or degraded (or all are off and nothing has run for a week) a quiet repository is shown as not seen, never as OK, and its row in the ranking is marked with an asterisk and lists the sentinels that could not read it (`not_fully_seen`; the totals count them too).

## Where to see it

- The **Team** tab: the ranking (the repositories that need a person first), the totals, the numbers by ecosystem and by sentinel, and three filters: ecosystem, least severity and a piece of the name. Click a repository for its detail.
- Deep links for wall screens: `?view=team&chrome=0`, `?view=repos&chrome=0` and `?view=repo&repo=owner/name&chrome=0`.
- The API: `GET /api/team/health?ecosystem=&severity=&q=&label=` and `GET /api/repos/<owner>/<repo>/health`. Both need the permission to see the account; the answers carry `schema: 1`. An unknown repository answers 404 with `code: repo_unknown`.
- The Lite edition keeps its simple view of runs and has neither the tab nor the routes.

## Thousands of repositories and a clock set back

The team health groups the runs, red workflows, running runs and alerts by repository once, so the cost grows with the amount of data and not with repositories times runs; asking for one repository builds only its view.

A saved moment that lies in the future (a computer without a battery clock that starts with an old date, or a clock corrected by hand) is not believed: the score, the purge of old data and the scheduled reports are due at once and write a good moment, instead of waiting until the old clock is reached.

## The fleet view (hundreds of repositories)

The **Team** tab has a second section, *Fleet*, for accounts with hundreds of repositories. It groups the repositories (`fleet.group_by`: ecosystem, label, state or none), orders each group (`fleet.sort`: risk, name, last run or state) and draws `fleet.page_size` rows at a time (50 by default) with Previous and Next. The page gets every row once from `GET /api/team/fleet?ecosystem=&severity=&q=&label=&group=&sort=&saved=` (read only, at most 5,000 rows, `truncated` says when it was cut) and only draws one page, so the size of the account does not slow it down.

A *label* is a pattern of repository names: `fleet.labels` takes lines such as `team-*=backend`; the first pattern that fits gives the label, and grouping by label is how organisations or teams are told apart in one monitor. `fleet.saved_filters` takes lines such as `attention=bad||backend|` (name, least severity, ecosystem, label, text; any part after the name may be empty) and shows them as ready-made filters. The ranking above the fleet is unchanged.
