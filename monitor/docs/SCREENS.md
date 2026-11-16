<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](SCREENS_spa.md) | [🇫🇷 Français](SCREENS_fra.md) | [🇮🇹 Italiano](SCREENS_ita.md) | [🇩🇪 Deutsch](SCREENS_deu.md) | [🇨🇳 简体中文](SCREENS_zho.md) | [🇯🇵 日本語](SCREENS_jpn.md) | [🇵🇹 Português](SCREENS_por.md)

# Screens, sizes and orientation

The page adapts to the size of its window, from a phone to 4K, upright or turned, and one monitor can serve several screens, each one showing the tabs you choose. Nothing is polled twice: every screen reads the same state.

## Addresses

- `/` - the whole page.
- `/screen/1`, `/screen/2`, `/screen/3` - the tabs set for that screen (`ui.screen1_tabs` ...). Open each one in a window of its own monitor or TV.
- `?orient=portrait` or `?orient=landscape` forces the layout of one window; `?tabs=now,charts` and `?rotate=30` set the tabs and the seconds between them for one window.

## Settings

| Setting | What it does |
|---|---|
| `ui.orientation` | auto follows the window; portrait stacks the panels in one column; landscape keeps the side-by-side layout. |
| `ui.rotate_seconds` | 0 = off. Seconds between the tabs of a screen that has more than one. |
| `ui.screen1_tabs` | Tabs of /screen/1, comma separated: now, al, rep, les, sent, charts, repos, hist, cfg. Empty = all. |
| `ui.screen1_orientation` | auto, portrait or landscape for /screen/1 only. |
| `ui.screen2_tabs` | Tabs of /screen/2. |
| `ui.screen2_orientation` | Orientation of /screen/2. |
| `ui.screen3_tabs` | Tabs of /screen/3. |
| `ui.screen3_orientation` | Orientation of /screen/3. |
| `ui.now_sort` | Order of Happening now for who has not chosen one: ecosystem, severity, age, newest, repo, event or state. |
| `ui.alerts_sort` | Order of the Alerts tab for who has not chosen: server, severity, streak, class, age, newest, repo, origin or state. |

## Order of the lists

The section **Happening now** of the first tab is sorted by ecosystem, with a heading for each one. The list above the section changes it: ecosystem, severity (stuck first, then runs with a failed job, then running, then queued), age (longest running first), newest first, repository, trigger (push, pull_request, schedule...) and state (running before queued). The choice is remembered for each person: in the team mode the server keeps it with the user (`GET` and `POST /api/auth/me/view`, so it follows the user to another browser), otherwise this browser does. Until someone chooses, the order is `ui.now_sort` of the configuration file (ecosystem when it is missing or wrong). The buttons **Expand all** and **Collapse all** next to the list unfold or fold every repository of the section at once, in any order, and the choice is remembered for each person in the same place and survives a refresh (a repository you open or close by hand afterwards keeps your choice).

The list of the **Alerts** tab keeps the order the monitor sends unless a person chooses another with the list above it: severity (critical, error, warning, info), the longest streak of failures in a row first, class (an error or critical alert is real and goes before the ones to watch), the oldest first, the newest first, repository, origin (the sentinel that raised it) and state (open before silenced). It is remembered the same way, and until someone chooses, `ui.alerts_sort` of the configuration file applies (`server` when it is missing or wrong).

## Sizes tested

A browser test opens the page in each of these sizes, goes through every tab and fails on a sideways scroll or a text that leaves its box. Windows of 2400 px or more get a larger type (and 3200 px a larger one still) instead of a stretched layout; a window taller than wide stacks the panels.

| Size | Kind |
|---|---|
| 1920x1080 | Full HD |
| 2560x1080 | 21:9 |
| 3440x1440 | 21:9 |
| 5120x1440 | 32:9 |
| 3840x2160 | 4K |
| 1080x1920 | Full HD |
| 2160x3840 | 4K |
| 768x1024 | tablet |
| 390x844 | phone |

## Recipe for a desk with two or three screens

1. On the computer that runs the monitor, set `ui.screen1_tabs` to `now,al`, `ui.screen2_tabs` to `charts,repos` and, for a turned monitor, `ui.screen2_orientation` to `portrait`.
2. Open `http://this-computer:8765/screen/1` in a window on the first monitor and `/screen/2` on the second; press F11 for full screen. From another computer, use the network mode with its access token.
3. For a wall screen nobody touches, give it several tabs and set `ui.rotate_seconds` to 20-30.

## Pictures

The tab Now in four sizes, with invented data (4K, a 21:9 monitor, a turned monitor, a phone):

![4K 3840x2160](../../docs/screenshots/web_size_4k_light.png)

![ultrawide 3440x1440](../../docs/screenshots/web_size_ultrawide_light.png)

![turned 1080x1920](../../docs/screenshots/web_size_portrait_light.png)

![phone 390x844](../../docs/screenshots/web_size_phone_light.png)
