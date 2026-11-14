<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](FIRST_STEPS_spa.md) | [🇫🇷 Français](FIRST_STEPS_fra.md) | [🇮🇹 Italiano](FIRST_STEPS_ita.md) | [🇩🇪 Deutsch](FIRST_STEPS_deu.md) | [🇨🇳 简体中文](FIRST_STEPS_zho.md) | [🇯🇵 日本語](FIRST_STEPS_jpn.md) | [🇵🇹 Português](FIRST_STEPS_por.md)

# Your first five minutes

**1. Install the two things it needs.** Python 3.11 or newer and the GitHub CLI (`gh`). Then log in once: `gh auth login`. The monitor never stores a token: it asks `gh` (unless you switch on the optional token of the monitor in Settings > Advanced).

**2. Check everything with one command.** `python bin/actions_monitor.py --doctor` tells you, for each problem, the exact command that fixes it. Want to look around first? `python bin/actions_monitor.py --demo` opens the page with invented data: no `gh`, no login, no network.

**3. Start it.** Double-click `MONITOR_LITE_GITHUB_ACTIONS` for the simple edition (port 8766) or `MONITOR_GITHUB_ACTIONS` for the complete one with the sentinel (port 8765). The console window says which edition it is, in its title and in the first line.

**4. Follow the three steps of the welcome.** The first time, the page explains what it does, shows what it found in your account and points to the basic settings. Nothing is hidden by default: repositories that no group claims appear as *Unclassified*.

**5. Know where help is.** The round **?** button (or the key `?`) opens the Help; the **i** button opens About with your version, files and a button that copies the information for support (it carries no secret). In the console: `--help-topics`, `--help-search WORDS`, `--about`.

**Good to know.** If you use a plan with private repositories, choose it in Settings > Basic to see your quotas ([Quotas and plans](QUOTAS.md)). The sentinel is explained in [The sentinel](SENTINEL.md). The tool only reads GitHub; it writes only after you confirm.
