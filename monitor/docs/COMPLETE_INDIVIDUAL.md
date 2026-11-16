<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](COMPLETE_INDIVIDUAL_spa.md) | [🇫🇷 Français](COMPLETE_INDIVIDUAL_fra.md) | [🇮🇹 Italiano](COMPLETE_INDIVIDUAL_ita.md) | [🇩🇪 Deutsch](COMPLETE_INDIVIDUAL_deu.md) | [🇨🇳 简体中文](COMPLETE_INDIVIDUAL_zho.md) | [🇯🇵 日本語](COMPLETE_INDIVIDUAL_jpn.md) | [🇵🇹 Português](COMPLETE_INDIVIDUAL_por.md)

# Complete edition for one person

The complete edition on your own computer is the usual way to use the monitor: one person, one GitHub account, no login, a page that only opens on `127.0.0.1`. The simple edition for people who only want to see their runs is [LITE.md](LITE.md).

## Start

- Sign in to GitHub once with `gh auth login`, then start `MONITOR_GITHUB_ACTIONS` (`.bat`, `.sh` or `.command`). The page opens on port 8765 (`ports.complete`).
- Choose the repositories and ecosystems to watch in Settings. The first five minutes are in [FIRST_STEPS.md](FIRST_STEPS.md).

## What you get

- Three sentinels (CI on; Collab and Security off until you switch them on) and one list of alerts that you can silence from your own computer.
- The score of the account, the health of each repository, scheduled reports (off by default) and a log of the actions taken (on by default, `audit_log.enabled`).
- The working modes normal, fast and turbo ([MODES.md](MODES.md)) and Low mode when the allowance is short ([QUOTA.md](QUOTA.md)).

## Keep it on this computer

- With `auth.enabled` off (the default) there are no users and nothing to remember: turn the team mode on only when more than one person uses the monitor ([COMPLETE_TEAM.md](COMPLETE_TEAM.md)).
- `listen.network` is off by default: the page and the API answer only to `127.0.0.1`. To leave it running all the time, read [COMPLETE_SERVICE.md](COMPLETE_SERVICE.md).

## Day to day

- `python bin/monitor_cli.py status`, `doctor` and `health` ask the running monitor ([CLI.md](CLI.md)). To update, read [MIGRATING.md](MIGRATING.md).
- Your own scripts can read the API: [API.md](API.md) lists what is promised not to change.
