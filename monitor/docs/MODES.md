<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](MODES_spa.md) | [🇫🇷 Français](MODES_fra.md) | [🇮🇹 Italiano](MODES_ita.md) | [🇩🇪 Deutsch](MODES_deu.md) | [🇨🇳 简体中文](MODES_zho.md) | [🇯🇵 日本語](MODES_jpn.md) | [🇵🇹 Português](MODES_por.md)

# Working modes: normal, fast and turbo

When you want to watch something closer for a while (an hour, say) you can switch the monitor to a faster mode even if it spends the allowance of the API sooner. The selector with the gauge icon is in the header; in the console use `--mode fast` or `--mode turbo` with `--mode-minutes 60`.

| Mode | What changes | Default values |
|---|---|---|
| **normal** | nothing: your own configuration | yours |
| **fast** | refresh, cold refresh, runs per repository, hot window | 30 s, 300 s, 30 runs, 6 h |
| **turbo** | the same, more | 15 s, 90 s, 50 runs, 12 h |

The presets are the block `modes` of `actions_monitor.json` (`modes.fast`, `modes.turbo`, `modes.default_minutes`, `modes.start`); edit them to taste. A preset never makes a value slower or smaller than what you set yourself, and nothing goes under 10 seconds, to keep clear of the secondary limits of GitHub (after one the monitor waits at least a minute and then longer).

**Before it starts**, the page shows the worst-case calls an hour of the mode, what the cache usually saves (a conditional read answered `304` does not count against the primary allowance) and how long the allowance left would last. **It goes back to normal by itself** when the time is up (the header counts it down) and when the allowance left falls under `min_rate_remaining`; a notice says why and the console prints it. **Without a login GitHub only gives 60 calls an hour**, so fast and turbo are disabled with the reason (run `gh auth login`).

Changing the mode is a local setting: it needs the one-use token of the page like any other change, it lives only in memory (a restart is normal unless you write `modes.start` yourself) and it sends nothing anywhere. It works in both editions; the sentinel of the complete edition keeps its own intervals and its own budget of calls (`sentinel.budget_per_hour`), documented in [the sentinel](SENTINEL.md). The console banner and the status lines name the active mode.

## Low mode (extreme saving of the allowance)

The opposite of fast and turbo, for when many tools (agents, AI tools, scripts) spend the same 5000 calls an hour of the account. In `low` the monitor reads only the hot repositories (a run in progress, a red workflow) every 4 minutes, the rest every 30 minutes, with short run lists and only 2 hours of "hot"; the allowance (`rate_limit`, free) is still read in every cycle. It is always allowed (it spends less), it never leaves by itself when chosen by hand, and every figure keeps the time of its last reading in the bar at the foot, so an old figure does not look new; the brief and `/api/ai/state` say `working mode low` with the age of the data.

`modes.auto_low` (on by default): when the calls left fall under `modes.auto_low_enter` (1000) the monitor goes to Low by itself and comes back to normal when they pass `modes.auto_low_exit` (2500) or the allowance renews; the two numbers are different on purpose so it does not flap. The values of Low live in `modes.low` of the configuration file (`refresh_seconds`, `cold_refresh_seconds`, `runs_per_repo`, `hot_hours`); a slower setting of yours is never made faster. Red alerts already read stay on the list while Low is active.
