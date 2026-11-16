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
| `ui.screen1_tabs` | Tabs of /screen/1, comma separated: now, al, sent, charts, repos, hist, cfg. Empty = all. |
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

## Wall screens: overview, right now and sentinels

Three pages for a monitor or a TV that nobody touches. They have no side menu and no navigation, show everything in one view with big type, animate what is alive and make failures blink softly. They only read: no button changes anything, and they never call GitHub (they show what the monitor already holds).

| Address | What it shows |
|---|---|
| `/screen/overview` | Score ring and letter; the fleet (green, red, stuck, waiting); the last 24 hours and 7 days as area charts; a heat map of repositories by hour; what has been red the longest; runners and minutes; the latest events; the GitHub allowance as a gauge. |
| `/screen/now` | What is happening this minute: running runs with progress and duration, the queue, runs waiting for approval, recent failures, merges and releases, releases due and a live line of the last two hours. |
| `/screen/sentinels` | One card for each sentinel (A1 to A12) with its level, open findings, whether its sources can be read, the last sweep and a ring that follows the sweep; an animated radar that marks what is wrong and the alerts by severity. |

### Parameters of the address

One address for each monitor. A parameter can make a window quieter or smaller than the settings allow, never louder.

| Parameter | Effect |
|---|---|
| `?monitor=1` to `9` | The number shown next to the title. |
| `?theme=dark`, `light` or `contrast` | Colours; contrast is white on black, for a screen seen from far away. |
| `?density=compact`, `normal` or `large` | Size of the type. `?scale=1.5` enlarges everything (0.5 to 3). |
| `?refresh=10` | Seconds between updates (5 to 120). |
| `?lang=de` | Language (en, es, de, fr, it, ja, zh, pt). |
| `?rotate=30` | The window turns by itself through overview, right now and sentinels every 30 seconds (at least 5; 0 = no rotation). |
| `?blink=off` | Failures keep a fixed glow instead of blinking. It cannot turn on what `screens.blink` keeps off. |
| `?sound=on` | A short beep for a new failure, only if `screens.sound` allows it. Off by default. |

### Settings of the wall screens

| Setting | What it does |
|---|---|
| `screens.enabled` | Turns the three pages on. Off: every address answers 404. |
| `screens.default_theme` | dark (default), light or contrast. |
| `screens.default_density` | compact, normal (default) or large. |
| `screens.refresh_seconds` | Seconds between updates of a window (10 by default). The pages read the monitor, never GitHub, so a short time costs no allowance. |
| `screens.rotate_seconds` | 0 (default) = no rotation; above 5, one window turns through the three pages. |
| `screens.blink` | Failures blink softly (on by default). |
| `screens.blink_calm_minutes` | Minutes after which a failure that nobody attended to keeps a fixed glow instead of blinking (30 by default; 0 = it blinks until solved). |
| `screens.sound` | A beep for a new failure (off by default). |
| `screens.burn_in_protection` | Moves everything a few pixels every minute (on by default). |
| `screens.night_dim` | Dims the screens between `screens.night_dim_from_hour` (22) and `screens.night_dim_to_hour` (7); off by default. |
| `screens.show_repo_names` | all, public (default: private repositories appear as private-1, private-2...) or none (every name is hidden). Use public or none for a screen that other people can see. |

### What they show and what they hide

The data come from `/api/screens/data?screen=overview` (or `now`, `sentinels`): a closed list of fields built from the last cycle, the snapshot of the sentinels, the alerts and the score. It never contains a link, a commit title, a job name, a user name or a path of this computer, and the workflow names of hidden repositories are hidden too. In the network mode the pages need the same access token as the rest of the monitor, and the answer is read only.

### How they behave

- Failures blink less than twice a second (never a strobe); a new failure makes a single flash; a failure nobody attended to for `screens.blink_calm_minutes` keeps a fixed glow. With the system setting for less motion, or `?blink=off`, nothing blinks and nothing moves. A failure is never shown by colour alone: it carries a symbol and a word.
- When the monitor does not answer, the page says so, dims and tries again after 5, 10, 20... seconds (up to 60).
- A screen that is always on is protected from burn-in: everything moves a few pixels every minute and the page can dim at night.

### Setting up several monitors

1. Choose one address for each monitor, for example `/screen/overview?monitor=1`, `/screen/now?monitor=2` and `/screen/sentinels?monitor=3`; or open one window with `?rotate=20`.
2. Open each one in Chrome or Edge in kiosk mode: `msedge --kiosk "http://this-computer:8765/screen/now?monitor=2" --edge-kiosk-type=fullscreen` or `chrome --kiosk "http://this-computer:8765/screen/now?monitor=2"`; with `--app=ADDRESS` instead of `--kiosk` the window has no bars. Without kiosk mode, the discreet button at the foot of the page asks for full screen.
3. From another computer use the network mode: the access token of a viewer is enough, because these pages never write.

## Pictures

The tab Now in four sizes, with invented data (4K, a 21:9 monitor, a turned monitor, a phone):

![4K 3840x2160](../../docs/screenshots/web_size_4k_light.png)

![ultrawide 3440x1440](../../docs/screenshots/web_size_ultrawide_light.png)

![turned 1080x1920](../../docs/screenshots/web_size_portrait_light.png)

![phone 390x844](../../docs/screenshots/web_size_phone_light.png)
