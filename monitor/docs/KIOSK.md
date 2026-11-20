<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](KIOSK_spa.md) | [🇫🇷 Français](KIOSK_fra.md) | [🇮🇹 Italiano](KIOSK_ita.md) | [🇩🇪 Deutsch](KIOSK_deu.md) | [🇨🇳 简体中文](KIOSK_zho.md) | [🇯🇵 日本語](KIOSK_jpn.md) | [🇵🇹 Português](KIOSK_por.md)

# Kiosk: the monitor on a TV or a wall

The kiosk profile is the page of the monitor for a screen nobody touches: no header, no tabs, larger type and, if you want it, a high contrast and a rotation through a few tabs. It reuses what the page already knows (`?screen=`, `?tabs=`, `?rotate=`, `?chrome=0`; see [SCREENS.md](SCREENS.md)) and adds two parameters. It reads nothing from GitHub and writes nothing: it only decides how the page looks.

It is **off by default**. With `kiosk.enabled` off the page ignores `kiosk=1` in the address, so a link copied from somewhere else changes nothing.

## The address

`python bin/monitor_cli.py kiosk [PRESET] [--account ID]` prints it; it needs no running monitor. For example, `kiosk ops` prints:

```
http://127.0.0.1:8765/?screen=1&tabs=now,al,charts&chrome=0&kiosk=1&scale=150
```

| Parameter | Meaning |
|---|---|
| `kiosk=1` | turns the profile on (only when `kiosk.enabled` is on) |
| `scale=PERCENT` | the type size, from 100 to 400 (a value outside the range is brought into it) |
| `contrast=1` / `contrast=0` | high contrast on or off for this window (the setting `kiosk.high_contrast` is the default) |
| `rotate=SECONDS` | turn through the tabs of `tabs=` (the existing parameter; the command adds it only when the rotation is on) |
| `chrome=0`, `screen=`, `tabs=`, `account=` | the existing ones |

## Presets

| Preset | Tabs |
|---|---|
| `ops` | Now, Alerts, Charts |
| `team` | Alerts, Team health |
| `release` | Now, Repositories, Reports |
| `quiet` | Alerts only |

## Settings (Settings, Command line and Kiosk)

| Setting | Default | Meaning |
|---|---|---|
| `kiosk.enabled` | off | turns the profile on |
| `kiosk.font_scale_percent` | 150 | the type size, 100 to 400 |
| `kiosk.high_contrast` | off | black background and white lines |
| `kiosk.rotate_views` | off | a preset with several tabs changes tab by itself; off, the screen shows the first tab of the preset |
| `kiosk.rotate_seconds` | 30 | how long each tab stays (5 to 600) |

The size is applied with the zoom of the page, so every figure and every table grows together. A value outside its range is not an error: it is replaced by the default.
