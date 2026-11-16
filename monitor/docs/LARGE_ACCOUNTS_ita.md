<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LARGE_ACCOUNTS.md) | [🇪🇸 Español](LARGE_ACCOUNTS_spa.md) | [🇫🇷 Français](LARGE_ACCOUNTS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](LARGE_ACCOUNTS_deu.md) | [🇨🇳 简体中文](LARGE_ACCOUNTS_zho.md) | [🇯🇵 日本語](LARGE_ACCOUNTS_jpn.md) | [🇵🇹 Português](LARGE_ACCOUNTS_por.md)

# Account grandi: centinaia di repository

Un account con centinaia di repository, molti fork o più organizzazioni consuma in fretta la quota dell'API. Questa è una ricetta, nell'ordine che fa risparmiare di più; ogni impostazione è nella scheda Impostazioni.

1. **Parti da un profilo.** Impostazioni > Base > Profilo: *Organizzazione open source* fissa gran parte di quanto segue con un clic (poi puoi cambiare ogni impostazione).
2. **Controlla ciò che è mantenuto.** `discovery.fork_policy` = `auto` tiene solo i fork con una CI propria (il tipo di account decide la finestra, `discovery.fork_ci_days`); `discovery.fork_checks_per_pass` distribuisce le domande su più elenchi. `discovery.skip_archived` è attivo di default. `exclude` ed `ecosystems` restringono l'elenco per nome.
3. **Chiedi meno.** `cold_runs_per_repo` e `cold_refresh_seconds` fissano quanto costano i repository tranquilli; `runs_per_repo` e `refresh_seconds` fanno lo stesso per quelli attivi. `network.etag` rende gratuite le letture ripetute quando nulla è cambiato e la modalità Bassa (`modes.auto_low`) rallenta tutto da sola quando la quota scarseggia.
4. **Dai un budget alla Sentinella.** `sentinel.budget_per_hour`, `sentinel.max_calls_per_tick` e `sentinel.hygiene_seconds` (l'igiene è una richiesta per repository ogni sei ore di default; allungala) limitano ciò che spendono i controlli A3-A6.
5. **Aggiungi una seconda quota.** `github_app.share_reads` lascia che una GitHub App risponda a parte delle letture con la propria quota.
6. **Non affogare nel rumore.** Il controllo di igiene (`sentinel.hygiene.ruleset_mode` = `effective`, `sentinel.hygiene.skip`), quelli sui file delle release (`sentinel.surface.checks.release_assets.allow_empty`) e `sentinel.bots_apart` evitano che si accumulino controlli che non riguardano i tuoi repository.

La scheda Quota mostra cosa resta a ogni fonte e quanto spende il monitor stesso.
