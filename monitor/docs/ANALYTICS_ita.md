<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ANALYTICS.md) | [🇪🇸 Español](ANALYTICS_spa.md) | [🇫🇷 Français](ANALYTICS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](ANALYTICS_deu.md) | [🇨🇳 简体中文](ANALYTICS_zho.md) | [🇯🇵 日本語](ANALYTICS_jpn.md) | [🇵🇹 Português](ANALYTICS_por.md)

# Analisi, letture condizionali e connessione persa

Ciò che il monitor impara dai run che già legge, come risparmia quota e come sopravvive a un'interruzione di rete. Tutto è locale; nulla viene inviato altrove.

## Durate, tempo in coda e passi

- `p50` e `p95` della durata dei run riusciti di ogni workflow; del tempo che un job ha atteso prima di partire (creato a avviato); e di ogni passo di un workflow. Un workflow mostra cifre quando ha `analytics.min_samples` campioni.
- I tempi di job e passi richiedono i job dei run completati: fino a `analytics.jobs_per_cycle` run per ciclo, ciascuno letto una volta (0 non ne legge). Il webhook in ingresso li fornisce gratis.
- Si esportano come `ghamon_workflow_duration_seconds`, `ghamon_job_queue_seconds` e `ghamon_step_duration_seconds` (etichetta `quantile` 0.5 / 0.95; richiede `per_repo`) e nella fonte JSON di Grafana (`durations`, `queue`). `slower` elenca i workflow il cui p50 è `analytics.slow_factor` volte il solito.


## Workflow instabili (flaky)

Un workflow che è FALLITO e poi PASSATO sullo stesso commit (o il cui run ha richiesto un altro tentativo) è etichettato instabile: `ghamon_workflow_flaky_rate`. È solo un'etichetta: ciò che conta come rosso non cambia.


## Letture condizionali (ETag)

- Ogni lettura degli elenchi di run invia `If-None-Match`; GitHub risponde `304 Not Modified` quando nulla è cambiato e quella risposta non costa quota. L'intestazione mostra quante letture sono state risparmiate e `ghamon_etag_saved_total` le conta. `cache.etag.enabled` e `cache.etag.ttl_hours` sono nella scheda Impostazioni. Ogni voce appartiene alla credenziale che l'ha letta (una breve impronta del token fa parte della chiave, mai il token), quindi un `304` non restituisce mai il corpo di un'altra identità. Uno stato che si muove ancora si legge sempre intero: i job di un'esecuzione, una singola esecuzione, le suite e i controlli (`cache.etag.skip_stateful`) e ogni lista di esecuzioni la cui ultima risposta aveva ancora un'esecuzione in coda o in corso (`cache.etag.revalidate_active`). Un rifiuto (404 o 403 che non sia un limite di frequenza) si ricorda per `cache.negative_ttl_s` secondi. `/metrics` conta anche le risposte senza ETag, le letture intere fatte di proposito e i rifiuti non ripetuti, e il brief per gli strumenti di IA ha il segnale quota.etag.
- Il brief per gli strumenti di IA nomina schema.drift quando GitHub ha inviato uno stato o una conclusione che il monitor non conosce, o un'esecuzione senza numero utilizzabile: il valore sconosciuto è mostrato come è arrivato e non è mai contato come rosso o verde.
- La cache è il file locale `etag_cache.json` (mai pubblicato); un file rotto è semplicemente una cache vuota.


## Quando la connessione si perde

Se tutte le letture di un ciclo falliscono per un problema di connessione (non di login né di quota), la pagina conserva l'ultima immagine e mostra un avviso rosso `nessuna connessione dalle HH:MM`. Nulla solleva eccezioni; il monitor riprende da solo e scrive un evento `offline` e uno `online`, una volta ciascuno (si possono notificare). Nel frattempo `ghamon_offline` vale 1.

## Per quanto tempo si conserva lo storico

Oltre a `keep_days` del blocco delle analisi, il passaggio di conservazione rimuove i giorni dello storico più vecchi di `retention.analytics_days` (180 per impostazione predefinita); i campioni stessi sono limitati da `max_samples`. Vedi [STORAGE_ita.md](STORAGE_ita.md).


## Tempo risparmiato (una stima)

Disattivato per impostazione predefinita (`productivity.enabled`). Attivo, la sezione mostra, attività per attività, quanti minuti a settimana il monitor fa risparmiare, con la formula di [PRODUCTIVITY_ita.md](PRODUCTIVITY_ita.md): volte a settimana x minuti ogni volta senza il monitor x risparmio dell'attività.

- Si quantificano due attività. **Sorveglianza** (guardare a mano le schede Actions e decidere cosa è rosso) prende le volte a settimana e i minuti dalle tue note (`productivity.watch_times_per_week`, `productivity.watch_minutes_before`). **Diagnosi** (trovare la causa di un'esecuzione fallita) conta le esecuzioni fallite che il monitor ha in vista in `productivity.window_days` e prende i minuti dalle tue note (`productivity.triage_minutes_before`).
- Il monitor non può vedere cosa facevi prima di essere installato. Un'attività senza queste note dice **nessun dato** e nessun numero viene inventato. Anche il totale dice nessun dato finché a ogni attività mancano le note.
- Se hai annotato anche i minuti con il monitor (`productivity.watch_minutes_after`, `productivity.triage_minutes_after`), il risparmio è misurato dalle tue note: 1 - dopo / prima. Altrimenti è la percentuale di `productivity.saving_percent` (90 per impostazione predefinita) e la tabella dice **supposto (non misurato)**.
- Con `productivity.team_hours_per_week` la stima dice anche quale parte del tempo di lavoro sono i minuti risparmiati.
- Correggere un errore richiede lo stesso tempo con o senza il monitor e non viene mai contato. Si contano solo le esecuzioni fallite che il monitor possiede: un elenco di esecuzioni molto lungo può contenere più errori di quelli mostrati.
- Locale e di sola lettura: nessuna chiamata a GitHub, nulla lascia il computer. Si trova in `/api/analytics` (`time_saved`), nel riepilogo del pannello A12 e nel brief della scheda Riepilogo per gli strumenti di IA.
