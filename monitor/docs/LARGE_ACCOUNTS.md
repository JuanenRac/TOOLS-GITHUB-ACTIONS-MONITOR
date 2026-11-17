<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](LARGE_ACCOUNTS_spa.md) | [🇫🇷 Français](LARGE_ACCOUNTS_fra.md) | [🇮🇹 Italiano](LARGE_ACCOUNTS_ita.md) | [🇩🇪 Deutsch](LARGE_ACCOUNTS_deu.md) | [🇨🇳 简体中文](LARGE_ACCOUNTS_zho.md) | [🇯🇵 日本語](LARGE_ACCOUNTS_jpn.md) | [🇵🇹 Português](LARGE_ACCOUNTS_por.md)

# Large accounts: hundreds of repositories

An account with hundreds of repositories, many forks or several organisations spends the allowance of the API quickly. This is a recipe, in the order that saves most; every setting is in the Settings tab.

1. **Start from a profile.** Settings > Basic > Profile: *Open-source organisation* sets most of what follows in one click (you can change each setting afterwards).
2. **Watch what is maintained.** `discovery.fork_policy` = `auto` keeps only the forks that have a CI of their own (the kind of account decides the window, `discovery.fork_ci_days`); `discovery.fork_checks_per_pass` spreads the questions over several listings. `discovery.skip_archived` is on by default. `exclude` and `ecosystems` narrow the list by name.
3. **Ask for less.** `cold_runs_per_repo` and `cold_refresh_seconds` set how much the quiet repositories cost; `runs_per_repo` and `refresh_seconds` do the same for the hot ones. `network.etag` makes the repeated reads free when nothing changed, and the Low mode (`modes.auto_low`) slows everything down by itself when the allowance runs low.
4. **Give the Sentinel a budget.** `sentinel.budget_per_hour`, `sentinel.max_calls_per_tick` and `sentinel.hygiene_seconds` (hygiene is one request per repository every six hours by default; make it longer) bound what the checks of A3-A6 spend.
5. **Add a second allowance.** `github_app.share_reads` lets a GitHub App answer part of the reads with its own allowance.
6. **Do not drown in noise.** The hygiene check (`sentinel.hygiene.ruleset_mode` = `effective`, `sentinel.hygiene.skip`), the release file checks (`sentinel.surface.checks.release_assets.allow_empty`) and `sentinel.bots_apart` stop the checks that do not apply to your repositories from piling up.

The Quota tab shows what each source has left and how much of it the monitor itself spends.

The follow-up of the originals of forks (`upstream.enabled`) says in its panel how long one pass over all the forks takes at the pace of `upstream.requests_per_hour` and `upstream.forks_per_request`; when that is longer than `upstream.refresh_hours` the follow-up never rests (727 forks at 8 a request and 6 requests an hour take 15.2 hours). The requests of the last hour are kept when the monitor restarts, so a restart does not give the allowance back.
