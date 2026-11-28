<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LARGE_ACCOUNTS.md) | [🇪🇸 Español](LARGE_ACCOUNTS_spa.md) | [🇫🇷 Français](LARGE_ACCOUNTS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](LARGE_ACCOUNTS_deu.md) | [🇨🇳 简体中文](LARGE_ACCOUNTS_zho.md) | [🇯🇵 日本語](LARGE_ACCOUNTS_jpn.md) | [🇵🇹 Português](LARGE_ACCOUNTS_por.md)

# Account grandi: centinaia di repository

Un account con centinaia di repository, molti fork o più organizzazioni consuma in fretta la quota dell'API. Questa è una ricetta, nell'ordine che fa risparmiare di più; ogni impostazione è nella scheda Impostazioni.

1. **Parti da un profilo.** Impostazioni > Base > Profilo: *Organizzazione open source* fissa gran parte di quanto segue con un clic (poi puoi cambiare ogni impostazione).
2. **Controlla ciò che è mantenuto.** `discovery.fork_policy` = `auto` tiene solo i fork con una CI propria (il tipo di account decide la finestra, `discovery.fork_ci_days`); `discovery.fork_checks_per_pass` distribuisce le domande su più elenchi. `discovery.skip_archived` è attivo di default. `exclude` ed `ecosystems` restringono l'elenco per nome. Un elenco dell'account che arriva vuoto, o con meno del `discovery.min_keep_pct` per cento dell'ultimo buono, non viene creduto: si conserva l'ultimo elenco buono, lo si rilegge tra cinque minuti e il brief per gli strumenti di IA ha il segnale repos.listing. `discovery.hide` accetta anche `public` (e `private`, `fork`, `empty`); la scheda Di base conta ciò che ogni regola ha escluso, così nulla di escluso da un filtro viene letto come pulito.
3. **Chiedi meno.** `cold_runs_per_repo` e `cold_refresh_seconds` fissano quanto costano i repository tranquilli; `runs_per_repo` e `refresh_seconds` fanno lo stesso per quelli attivi. `network.etag` rende gratuite le letture ripetute quando nulla è cambiato e la modalità Bassa (`modes.auto_low`) rallenta tutto da sola quando la quota scarseggia.
4. **Dai un budget alla Sentinella.** `sentinel.budget_per_hour`, `sentinel.max_calls_per_tick` e `sentinel.hygiene_seconds` (l'igiene è una richiesta per repository ogni sei ore di default; allungala) limitano ciò che spendono i controlli A3-A6.
5. **Aggiungi una seconda quota.** `github_app.share_reads` lascia che una GitHub App risponda a parte delle letture con la propria quota.
6. **Non affogare nel rumore.** Il controllo di igiene (`sentinel.hygiene.ruleset_mode` = `effective`, `sentinel.hygiene.skip`), quelli sui file delle release (`sentinel.surface.checks.release_assets.allow_empty`) e `sentinel.bots_apart` evitano che si accumulino controlli che non riguardano i tuoi repository.

La scheda Quota mostra cosa resta a ogni fonte e quanto spende il monitor stesso.

Il seguito degli originali dei fork (`upstream.enabled`) dice nel suo pannello quanto dura un giro di tutti i fork al ritmo di `upstream.requests_per_hour` e `upstream.forks_per_request`; quando è più di `upstream.refresh_hours` il seguito non riposa mai (727 fork a 8 per richiesta e 6 richieste all'ora richiedono 15,2 ore). Le richieste dell'ultima ora si conservano al riavvio, quindi un riavvio non restituisce la quota.

Le chiamate di un tick della Sentinella (`sentinel.max_calls_per_tick`) sono un solo conteggio per tutte le sue fasi, e un repository le cui letture falliscono tre volte di seguito viene lasciato in pace 30 secondi, raddoppiando fino a 10 minuti, mentre si leggono gli altri.

La scheda Flotta ha anche un riquadro facoltativo per [ruolo del workflow e gruppo, con uno schermo per ogni gruppo](FLEET_APIS_ita.md).

## Coda di letture, limiti e una lettura per tutti

- **Contropressione** (`backpressure.enabled`, spenta per impostazione predefinita): le letture di un ciclo passano per una coda limitata (prima i repository con un workflow rosso, poi i caldi, i mai letti e i letti da più tempo). `backpressure.max_reads_per_cycle` fissa un numero (0 = nessuno); quando un ciclo dura più del `backpressure.shed_percent` per cento della pausa tra i cicli, il numero consentito si dimezza (mai sotto `backpressure.min_reads`) e ricresce di un decimo dopo ogni ciclo veloce. Ciò che aspetta mantiene la sua ultima immagine e passa per primo nel ciclo successivo. `/metrics` mostra `ghamon_read_queue_*`.
- **Limiti e il doctor**: `monitor_cli.py doctor` ha un controllo `capacity` che confronta la configurazione con i suoi massimali (chiamate all'ora rispetto alla quota e a `sampling.api_budget_per_hour`, la memoria delle esecuzioni conservate rispetto a `limits.memory_mb`, i repository rispetto a `discover_limit`) e avvisa da `limits.warn_percent`. `/metrics` mostra quelli in corso come `ghamon_limit_used_percent{limit=...}` (eventi conservati, flussi, coda di letture, serie degli istogrammi).
- **Una lettura per tutti** (`refresh.share_by_workflow`, spenta per impostazione predefinita): quando il ciclo, una pagina, uno schermo a muro o un client dell'API chiedono i job della stessa esecuzione nello stesso momento, il primo legge da GitHub e gli altri prendono la sua risposta, valida `refresh.share_seconds` secondi. `/metrics` conta le letture risparmiate (`ghamon_shared_reads_spared_total`).
