<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](LITE_spa.md) | [🇫🇷 Français](LITE_fra.md) | [🇮🇹 Italiano](LITE_ita.md) | [🇩🇪 Deutsch](LITE_deu.md) | [🇨🇳 简体中文](LITE_zho.md) | [🇯🇵 日本語](LITE_jpn.md) | [🇵🇹 Português](LITE_por.md)

# The lite edition

A second, simpler product in the same package: the page of what is running and what failed, without the sentinel. It is for people who only want to watch their runs.

|  | Complete | Lite |
|---|---|---|
| Start | `MONITOR_GITHUB_ACTIONS` (`.bat` / `.sh` / `.command`) | `MONITOR_LITE_GITHUB_ACTIONS` (same three) |
| Port | 8765 | 8766 |
| Tabs | Now, Sentinel, Charts, Repositories, History, Settings | Now, Charts, Repositories, History, a short Settings |
| Header | all the tiles, readiness, signing | running, queued, failures and successes of 24 h, compute minutes, issues, red on main, repositories, allowance, connection |
| Sentinel (alerts, releases, signing queue, readiness, linter) | yes | no: it is not even imported |
| Analytics, notifications, webhook, AI, Prometheus / Grafana outputs | yes, off until you switch them on | no: those paths answer 404 |
| Configuration | `actions_monitor.json` | `actions_monitor_lite.json` (created on the first start; the sentinel is off in it) |
| State files | `etag_cache.json`, `analytics_history.json`... | the same names with the suffix `_lite` |

How to start it: `MONITOR_LITE_GITHUB_ACTIONS.bat` on Windows, `./MONITOR_LITE_GITHUB_ACTIONS.sh` on Linux, double-click `MONITOR_LITE_GITHUB_ACTIONS.command` on macOS, or `python bin/actions_monitor.py --lite` (also `MONITOR_MODE=lite`). It listens on `127.0.0.1:8766`, so the complete one can run at the same time.

The short Settings page has the account (`github_owner`), the repositories and ecosystems to watch (`repos`, `ecosystems`, `exclude`), the refresh time (`refresh_seconds`), the language and the theme. "Red on main" counts the workflows whose latest finished run failed. To get the sentinel and the rest later, just start the complete one: nothing has to be migrated. The first time it starts, `actions_monitor_lite.json` copies from `actions_monitor.json` (when that file exists) the account, the repositories and ecosystems to watch, the catalogue files and the language, and says so on the console; it never copies the sentinel, the AI, the webhook, the outputs or the notifications. Without such a file it watches all the ecosystems (`"ecosystems": "all"`). The browser remembers the theme separately for each port. The lite edition writes no `ci_red.json` and no signing queue and keeps its own state files; if you ever give both editions a `sentinel.ci_red_file`, do not point them at the same file.

## The command line

`python bin/monitor_cli.py status --lite`, `doctor --lite` and `health --lite` ask the lite monitor on port 8766 (see [CLI.md](CLI.md)); the commands that need accounts or sentinels are refused. The page has the status bar at its foot and the sortable tables too.

## Storage

The lite edition keeps plain files only: no database, no retention job, and none of the options of [STORAGE.md](STORAGE.md).
