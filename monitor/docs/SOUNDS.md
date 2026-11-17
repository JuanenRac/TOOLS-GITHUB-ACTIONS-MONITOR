<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](SOUNDS_spa.md) | [🇫🇷 Français](SOUNDS_fra.md) | [🇮🇹 Italiano](SOUNDS_ita.md) | [🇩🇪 Deutsch](SOUNDS_deu.md) | [🇨🇳 简体中文](SOUNDS_zho.md) | [🇯🇵 日本語](SOUNDS_jpn.md) | [🇵🇹 Português](SOUNDS_por.md)

# Sounds

The page makes its own sounds with the Web Audio API, one for each kind of event, so you can tell by ear what happened without looking. There are no audio files: the tones are made in the browser, offline, and nothing is sent anywhere. Every sound has a visual notice as well (the tiles, the tabs, the chips); the sound never replaces it.

| Kind | When it sounds | The sound |
|---|---|---|
| Red | A workflow that was not red turns red (a new failure). | Two rising tones, the classic "bing bing". |
| Security or serious | A new alert of the security sentinel, a serious (error or critical) alert of the collaboration sentinel, or an account that has gone blind. | Three low pulses. |
| Stuck | A build that is stuck, a ghost queue, or a problem with the runners. | One long falling slide. |
| Score | The score of the fleet drops (`score.dropped`). | Three falling notes. |
| Connection | The connection to GitHub, or of this page with the monitor, is lost. | Two low, long notes. |
| Warning | A new alert of level warning (a pending signature, a stale issue, a pull request that waits). | Two equal middle tones. |
| Solved | A red workflow turns green, or a serious alert disappears. | Three rising notes. |
| Report | One of the optional reports shows a finding that was not there before. | Two soft chimes, high then lower. |
| Lesson | The lessons of the failures show a new category, or one that starts to repeat or to apply. | Three quick high notes. |
| Notice | A new alert of level info (the release of the original of a fork, for instance). | One soft ping. |

## Why a browser may stay silent, and what the page does

- A browser lets a page make sound only after you have clicked, touched or pressed a key on it. Until then the bar shows the notice "Sound blocked by the browser: click here to turn it on". The first click anywhere unlocks it.
- What happened while the sound was blocked is kept (for at most ten minutes) and plays at the first chance: the click, the page coming back to the front or the next check every two seconds. Nothing is lost between two looks; what is older than ten minutes is old news and is not announced.
- The first look of the page only remembers what is already there; a reload within a few hours remembers it as well, so a failure that came while the page was closed is new.
- A tab in the background keeps its sound as long as the browser keeps the page awake; some browsers pause hidden tabs after a while. The wall screens and the page are best left in a visible window.

## No spam

- A kind that has just sounded waits `sound.cooldown_seconds` (30 s by default) before it sounds again.
- Several kinds in one look make one burst: at most three patterns, the most serious first; the rest wait for the next burst. Two bursts are never on top of each other.
- A silenced alert (Alerts tab) never sounds.

## Settings (Settings, Sound)

All of them are in the configuration file and in the Settings tab; the volume, the theme and the switches take effect at once.

| Setting | What it does |
|---|---|
| `sound.enabled` | Main switch of all the sounds of the page. |
| `sound.on_new_red`, `sound.on_connection_lost`, `sound.on_warning`, `sound.on_resolved`, `sound.on_report`, `sound.on_lesson`, `sound.on_sentinel`, `sound.on_stuck`, `sound.on_score_drop`, `sound.on_info` | One switch per kind (all on by default). |
| `sound.theme` | `classic` (clear tones) or `soft` (lower, rounder, slower tones). Each kind keeps its rhythm in both. |
| `sound.volume` | 1 to 100, moderate by default. |
| `sound.cooldown_seconds` | Pause between two sounds of the same kind. |
| `sound.quiet_enabled`, `sound.quiet_from_hour`, `sound.quiet_to_hour` | Quiet hours (off by default): between the two hours of this computer nothing sounds; they may cross midnight. |
| `sound.server_beep` | Off by default. A beep of this computer for a new red when no page is open (local only). |

## Try each sound

In Settings, Interface, the button "Test sound" plays the classic bing bing and one button per kind plays that kind with the volume and the theme of the settings. The chip "Sound" of the bar at the foot mutes everything in this browser.

## Wall screens

The screens of the wall (`/screen/...`) use the same sounds, the same theme, volume, switches and quiet hours. They are off by default: `screens.sound` must be on and the window needs `?sound=on`. A screen nobody touches cannot get the click the browser asks for: start the browser of the screen with its "allow audio without a gesture" option (in Chromium, `--autoplay-policy=no-user-gesture-required`) or click the window once.

## Where it is stored

The mute chip is remembered by each browser; what the page knows from its last look is kept in the browser as well. Nothing about sounds is sent to a server.
