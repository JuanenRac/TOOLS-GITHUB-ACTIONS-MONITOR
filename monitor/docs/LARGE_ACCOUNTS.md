<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](LARGE_ACCOUNTS_spa.md) | [🇫🇷 Français](LARGE_ACCOUNTS_fra.md) | [🇮🇹 Italiano](LARGE_ACCOUNTS_ita.md) | [🇩🇪 Deutsch](LARGE_ACCOUNTS_deu.md) | [🇨🇳 简体中文](LARGE_ACCOUNTS_zho.md) | [🇯🇵 日本語](LARGE_ACCOUNTS_jpn.md) | [🇵🇹 Português](LARGE_ACCOUNTS_por.md)

# Large accounts: hundreds of repositories

An account with hundreds of repositories, many forks or several organisations spends the allowance of the API quickly. This is a recipe, in the order that saves most; every setting is in the Settings tab.

1. **Start from a profile.** Settings > Basic > Profile: *Open-source organisation* sets most of what follows in one click (you can change each setting afterwards).
2. **Watch what is maintained.** `discovery.fork_policy` = `auto` keeps only the forks that have a CI of their own (the kind of account decides the window, `discovery.fork_ci_days`); `discovery.fork_checks_per_pass` spreads the questions over several listings. `discovery.skip_archived` is on by default. `exclude` and `ecosystems` narrow the list by name. A listing of the account that comes back empty, or with fewer than `discovery.min_keep_pct` percent of the last good one, is not believed: the last good listing is kept, the listing is read again in five minutes and the brief for the AI tools has the signal repos.listing. `discovery.hide` also takes `public` (and `private`, `fork`, `empty`); the Basic tab counts what each rule left out, so nothing left out by a filter is read as clean.
3. **Ask for less.** `cold_runs_per_repo` and `cold_refresh_seconds` set how much the quiet repositories cost; `runs_per_repo` and `refresh_seconds` do the same for the hot ones. `network.etag` makes the repeated reads free when nothing changed, and the Low mode (`modes.auto_low`) slows everything down by itself when the allowance runs low.
4. **Give the Sentinel a budget.** `sentinel.budget_per_hour`, `sentinel.max_calls_per_tick` and `sentinel.hygiene_seconds` (hygiene is one request per repository every six hours by default; make it longer) bound what the checks of A3-A6 spend.
5. **Add a second allowance.** `github_app.share_reads` lets a GitHub App answer part of the reads with its own allowance.
6. **Do not drown in noise.** The hygiene check (`sentinel.hygiene.ruleset_mode` = `effective`, `sentinel.hygiene.skip`), the release file checks (`sentinel.surface.checks.release_assets.allow_empty`) and `sentinel.bots_apart` stop the checks that do not apply to your repositories from piling up.

The Quota tab shows what each source has left and how much of it the monitor itself spends.

The follow-up of the originals of forks (`upstream.enabled`) says in its panel how long one pass over all the forks takes at the pace of `upstream.requests_per_hour` and `upstream.forks_per_request`; when that is longer than `upstream.refresh_hours` the follow-up never rests (727 forks at 8 a request and 6 requests an hour take 15.2 hours). The requests of the last hour are kept when the monitor restarts, so a restart does not give the allowance back.

The calls of one tick of the Sentinel (`sentinel.max_calls_per_tick`) are one count for all its stages, and a repository whose reads fail three times in a row is left alone for 30 seconds, doubling up to 10 minutes, while the others are read.

The Fleet tab also has an optional box by [role of workflow and group, with a screen for each group](FLEET_APIS.md).

## Queue of reads, limits and one read for everybody

- **Backpressure** (`backpressure.enabled`, off by default): the reads of a cycle go through one bounded queue (red repositories first, then hot ones, never read ones and the oldest read). `backpressure.max_reads_per_cycle` sets a fixed number (0 = none); when a cycle lasts more than `backpressure.shed_percent` percent of the pause between cycles the allowed number is cut in half (never under `backpressure.min_reads`) and it grows back by a tenth after each fast cycle. What waits keeps its last picture and goes first in the next cycle. `/metrics` shows `ghamon_read_queue_*`.
- **Limits and the doctor**: `monitor_cli.py doctor` has a check `capacity` that compares the setup with its ceilings (calls an hour against the allowance and against `sampling.api_budget_per_hour`, the memory of the held runs against `limits.memory_mb`, the repositories against `discover_limit`) and warns from `limits.warn_percent`. `/metrics` shows the live ones as `ghamon_limit_used_percent{limit=...}` (events kept, streams, read queue, series of the histograms).
- **One read for everybody** (`refresh.share_by_workflow`, off by default): when the cycle, a page, a wall screen or an API client ask for the jobs of the same run at the same moment, the first reads from GitHub and the others take its answer, valid `refresh.share_seconds` seconds. `/metrics` counts the reads spared (`ghamon_shared_reads_spared_total`).
