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
