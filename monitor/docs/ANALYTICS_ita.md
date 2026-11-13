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

- Ogni lettura degli elenchi di run invia `If-None-Match`; GitHub risponde `304 Not Modified` quando nulla è cambiato e quella risposta non costa quota. L'intestazione mostra quante letture sono state risparmiate e `ghamon_etag_saved_total` le conta. `cache.etag.enabled` e `cache.etag.ttl_hours` sono nella scheda Impostazioni.
- La cache è il file locale `etag_cache.json` (mai pubblicato); un file rotto è semplicemente una cache vuota.


## Quando la connessione si perde

Se tutte le letture di un ciclo falliscono per un problema di connessione (non di login né di quota), la pagina conserva l'ultima immagine e mostra un avviso rosso `nessuna connessione dalle HH:MM`. Nulla solleva eccezioni; il monitor riprende da solo e scrive un evento `offline` e uno `online`, una volta ciascuno (si possono notificare). Nel frattempo `ghamon_offline` vale 1.

## Per quanto tempo si conserva lo storico

Oltre a `keep_days` del blocco delle analisi, il passaggio di conservazione rimuove i giorni dello storico più vecchi di `retention.analytics_days` (180 per impostazione predefinita); i campioni stessi sono limitati da `max_samples`. Vedi [STORAGE_ita.md](STORAGE_ita.md).
