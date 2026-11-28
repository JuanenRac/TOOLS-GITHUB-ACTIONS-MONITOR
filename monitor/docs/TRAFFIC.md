<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](TRAFFIC_spa.md) | [🇫🇷 Français](TRAFFIC_fra.md) | [🇮🇹 Italiano](TRAFFIC_ita.md) | [🇩🇪 Deutsch](TRAFFIC_deu.md) | [🇨🇳 简体中文](TRAFFIC_zho.md) | [🇯🇵 日本語](TRAFFIC_jpn.md) | [🇵🇹 Português](TRAFFIC_por.md)

# Downloads and traffic

A history, kept on this computer, of how often the files of your releases are downloaded and of the visits and clones of the repositories you choose. GitHub keeps visits and clones for 14 days only and gives no history of the downloads, so what is not saved is lost. Complete edition; off by default.

## Switching it on

Switch on `traffic.enabled` (Settings > Downloads and traffic) and write the repositories in `traffic.repos`, one per line: a name (of the account you watch) or owner/name, at most 50. With an empty list nothing is read. The panel appears in the Repositories tab.

## What is read, and what it costs

Only GET requests, after a cycle: each chosen repository at most once a day (UTC), `traffic.repos_per_cycle` of them per cycle. One repository costs from one to five requests of your GitHub allowance (releases, up to 300 of them; visits; clones). If the allowance is over, it stops and tries again later. `traffic.views_clones` switches the visits and clones off. Air-gapped installations read nothing. It also waits while the connection is lost, while the first reading is under way, and while no more than twice `min_rate_remaining` requests are left.

## Permissions

Visits and clones are only given to a token with push access to the repository. Without it the panel says so for that repository; it is not an error and the downloads are still saved.

## What the figures mean

Download counts are anonymous, include robots and mirrors, and do not count the "Source code" archives that GitHub adds to a release. New downloads compare one read with the one before, only for the files that are still there. A day that was not read is a gap, never a zero.

## Export and privacy

The panel exports two CSV files: one line per repository and day, and one line per release file and day on which its count changed. `monitor_cli.py traffic export` prints the first one. Days older than `traffic.keep_days` are deleted. The history stays in the data folder of this computer; nothing is sent anywhere.
