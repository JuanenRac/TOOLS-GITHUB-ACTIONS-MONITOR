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
