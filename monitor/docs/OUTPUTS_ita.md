<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](OUTPUTS.md) | [🇪🇸 Español](OUTPUTS_spa.md) | [🇫🇷 Français](OUTPUTS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](OUTPUTS_deu.md) | [🇨🇳 简体中文](OUTPUTS_zho.md) | [🇯🇵 日本語](OUTPUTS_jpn.md) | [🇵🇹 Português](OUTPUTS_por.md)

# Uscite per altri strumenti

Tre uscite opzionali, **tutte disattivate per impostazione predefinita**, che si attivano nella scheda Impostazioni (gruppo «Uscite per altri strumenti») o in `actions_monitor.json`:

```json
"outputs": {"prometheus": {"enabled": false, "per_repo": true}, "json": {"enabled": false}, "dashboard": {"enabled": false}}
```

Sono servite dallo stesso server web, solo su `127.0.0.1`, con gli stessi controlli `Host` / `Origin` del resto, e **non richiedono alcun token**. Leggono lo stato che il monitor già possiede, quindi uno
scrape o l'aggiornamento di una dashboard non consuma quota delle API di GitHub. Attivarle o disattivarle ha effetto immediato (senza riavvio).

| Percorso | Formato | Interruttore |
|---|---|---|
| `/metrics` | Testo Prometheus, versione 0.0.4 | `outputs.prometheus.enabled` (`per_repo` aggiunge le serie per repository) |
| `/api/outputs/grafana.json` | Tabelle JSON per l'origine dati «Infinity» / JSON di Grafana | `outputs.json.enabled` |
| `/api/outputs/dashboard.json` | il documento di `ci_red.json` (schema 2, vedi CI_RED_SCHEMA_ita.md) per una dashboard di stato | `outputs.dashboard.enabled` |

Una richiesta a un percorso il cui interruttore è disattivato riceve `404`. Il modo precedente di fornire lo stesso documento a una dashboard, `ci_red.json` e `bin/read_report.py --export-status`, resta invariato: è un contratto.

## Metriche Prometheus

Tutti i nomi iniziano con `ghamon_`. Solo gauge. Un valore sconosciuto viene **omesso**, mai scritto come 0.

| Metrica | Etichette | Significato |
|---|---|---|
| `ghamon_info` | `version` | sempre 1 |
| `ghamon_snapshot_complete` | | 1 quando lo snapshot della sentinella è completo, 0 mentre si carica o è ridotto |
| `ghamon_red_workflows`, `ghamon_red_repos` | | workflow (repository) la cui ultima esecuzione completata sul ramo predefinito è rossa |
| `ghamon_ecosystem_red_workflows` | `ecosystem` | lo stesso per ecosistema |
| `ghamon_repo_red_workflows` | `repo`, `ecosystem` | per repository (richiede `per_repo`) |
| `ghamon_workflow_red_streak` | `repo`, `workflow`, `ecosystem` | esecuzioni rosse consecutive (richiede `per_repo`) |
| `ghamon_workflow_red_hours` | `repo`, `workflow`, `ecosystem` | ore trascorse da quando è diventato rosso (richiede `per_repo`) |
| `ghamon_pending_sign`, `ghamon_pending_sign_repos`, `ghamon_pending_sign_hours_max` | | build in attesa della firma o della pubblicazione locale, oltre la soglia |
| `ghamon_repo_pending_sign_hours` | `repo`, `ecosystem` | l'attesa più lunga di un repository (richiede `per_repo`) |
| `ghamon_surface_paused`, `ghamon_surface_paused_remaining`, `ghamon_surface_paused_needed` | | 1 finché i controlli di superficie (A10) attendono quota di GitHub, con la quota residua e quella necessaria |
| `ghamon_api_rate_remaining`, `ghamon_api_rate_limit` | | la quota delle API di GitHub |
| `ghamon_score`, `ghamon_score_coverage`, `ghamon_score_scored` | | il punteggio dell'account (da 0 a 100, solo quando ha un numero), la quota dei suoi pesi con dati e 1 quando ha un numero (solo Complete; vedi SCORE.md) |
| `ghamon_sentinel_calls_last_hour`, `ghamon_sentinel_budget_per_hour` | | le chiamate API della sentinella rispetto al suo budget |
| `ghamon_repos_watched`, `ghamon_runs_active`, `ghamon_runs_stuck`, `ghamon_runs_failing`, `ghamon_issues_open`, `ghamon_quota_paused` | | i numeri in tempo reale della scheda Adesso |

Un job di scrape:

```yaml
scrape_configs:
  - job_name: github-actions-monitor
    scrape_interval: 30s
    static_configs:
      - targets: ["127.0.0.1:8765"]
```

## Grafana

`docs/grafana/monitor_dashboard.json` è una dashboard importabile (Grafana 10 o successivo): pannelli di statistica per i workflow rossi, le build in attesa di firma, la quota residua, lo
stato di A10, se lo snapshot è completo e le esecuzioni bloccate; un grafico a barre dei workflow rossi per ecosistema; un grafico della serie rossa più lunga e dell'attesa di firma; e due tabelle lette
da `/api/outputs/grafana.json` con l'origine dati Infinity (`root_selector` `red` e `pending_sign`). All'importazione Grafana chiede le origini dati Prometheus e Infinity; cambia
la porta nell'URL delle due tabelle se il monitor non usa la 8765. Grafana deve essere eseguito sulla stessa macchina (le uscite rispondono solo su 127.0.0.1).

## Idee tratte da progetti simili

Leggere che cosa fanno altri strumenti per GitHub Actions ha dato alcune idee; non viene usato nulla del loro codice né dei loro testi. Da un esportatore di metriche Prometheus: lo stato di un'esecuzione come numero più etichette, la
scelta di quali etichette esportare e una porta e un intervallo configurabili. Da una dashboard per TV alimentata da webhook: uno stato per repository con filtri, mostrato in grande. Da un osservatore da terminale: tutti i
workflow di un repository insieme fino alla loro conclusione. Da una dashboard di webhook con regole di allerta: filtri per repository, ramo e workflow prima di avvisare. Qui le stesse idee compaiono come
`per_repo` (scegliere le serie), l'origine JSON con una riga per workflow rosso, la scheda Adesso in tempo reale e il file degli eventi con filtri nella pagina.

## Il pannello Grafana minimo

`docs/grafana/red_by_ecosystem.json` è una board con un solo pannello: workflow rossi per ecosistema (query `ghamon_ecosystem_red_workflows`, legenda `{{ecosystem}}`). Importala e scegli la tua fonte Prometheus. Un test di questo repository verifica che la metrica e l'etichetta usate siano davvero servite da `/metrics`.

## La coda di firma per affidabilità

Ogni riga della coda ha un `trust`: `verified` (firma verificata con la chiave pubblica), `unknown` (il formato qui non si può verificare: mai indovinato) o `failed` (verificata e non corrisponde). La scheda Sentinella ha un filtro Firma con il numero di ciascun tipo e segna le righe (bordo verde, grigio o rosso). Da console: `py -3 bin/read_report.py --export-sign-queue FILE --sign-trust failed`.

## In modalità rete

`/metrics` e `dashboard.json` elencano i tuoi repository e il loro stato: non sono pagine pubbliche. Con la modalità rete attiva richiedono il token di accesso come ogni altro endpoint; spegni `outputs.prometheus.enabled` / `outputs.dashboard.enabled` se non vuoi che quell'inventario sia raggiungibile affatto.

## Salvare e stampare il rapporto di una scheda

La barra in alto nella pagina (in ogni scheda) crea UN rapporto della scheda aperta e lo disegna in quattro modi dagli stessi dati, così i formati non differiscono mai:

- **Salva il rapporto** apre una finestra con tre caselle: **TXT** (selezionata), **PDF** (selezionata) e **JSON** (non selezionata: i dati del rapporto, per altri strumenti). Dopo la conferma si apre la finestra **Salva con nome** del browser una volta per formato, con il nome suggerito `monitor-<scheda>-<data>.<estensione>` e il tipo di file giusto (il browser vuole un clic per finestra, quindi il pulsante passa al formato successivo). Un browser senza quella finestra scarica il file e la pagina dice dove è finito.
- **PDF**: il monitor scrive da sé il PDF, senza librerie e con il carattere standard Helvetica, per inglese, spagnolo, tedesco, francese, italiano e portoghese (`GET /api/report/tab.pdf`, solo da questo computer; ogni uso lascia una riga nel registro delle azioni). Giapponese e cinese richiedono caratteri che un PDF scritto così non ha; per loro, o se nella finestra scegli «Il browser», il PDF viene dalla finestra di stampa del browser: scegli lì **Salva come PDF**. La pagina lo dice; non scrive mai un PDF con caratteri rotti.
- **Stampa** mostra lo stesso rapporto senza menu né barre (titolo con il nome della scheda, data e ora, versione del monitor, cifre principali, avvisi e tabelle della scheda) e apre la finestra di stampa.
- Il rapporto è servito da `GET /api/report/tab?tab=now&lang=it` (`&fmt=json`, `&fmt=txt` oppure `&fmt=options`), uguale nelle due edizioni.

Impostazioni (Impostazioni > Uscite per altri strumenti > «Salvare e stampare il rapporto di una scheda»): `report_export.txt`, `report_export.pdf` e `report_export.json` (quali caselle partono selezionate: TXT e PDF sì, JSON no), `report_export.name` (nome suggerito, predefinito `monitor-{tab}-{date}`), `report_export.paper` (`a4` o `letter`, predefinito `a4`) e `report_export.pdf_path` (`auto`, `own` o `browser`, predefinito `auto`).

## Metriche del server: ciclo, coda di letture, fatturazione, runner e istogrammi

Oltre ai valori sopra, `/metrics` scrive (un valore non noto viene omesso):

| Metrica | Etichette | Significato |
|---|---|---|
| `ghamon_ticks_total`, `ghamon_tick_failures_total` | | cicli di aggiornamento finiti e cicli terminati con errore (contatori) |
| `ghamon_tick_last_seconds`, `ghamon_tick_phase_seconds`, `ghamon_tick_seconds` | `phase` | durata dell'ultimo ciclo, di ognuna delle sue fasi e istogramma di tutti |
| `ghamon_tick_last_ok_timestamp_seconds`, `ghamon_tick_reads_last` | | quando l'ultimo ciclo è finito bene e quanti repository ha letto |
| `ghamon_read_retries_total` | | letture fallite per una causa passeggera e ripetute (contatore) |
| `ghamon_repos_circuit_open`, `ghamon_repos_read_failing`, `ghamon_repos_read_fail_streak_max` | | repository che aspettano prima della lettura successiva perché hanno fallito più volte di fila (il circuito), repository la cui ultima lettura è fallita, la serie più lunga |
| `ghamon_read_queue_depth`, `ghamon_read_queue_allowed`, `ghamon_read_queue_oldest_wait_cycles`, `ghamon_read_queue_deferred_total`, `ghamon_read_queue_shed_cycles_total` | | la coda di letture con contropressione (solo con `backpressure.enabled` attivo) |
| `ghamon_billing_minutes_total`, `ghamon_billing_minutes_included`, `ghamon_billing_minutes_paid`, `ghamon_billing_sku_minutes`, `ghamon_billing_usd` | `sku`, `product` | il rapporto di fatturazione del mese (solo con `quota.billing_api` attivo; uno scrape non legge mai GitHub, scrive l'ultimo rapporto tenuto dal ciclo) |
| `ghamon_runners` | `state` | runner self-hosted liberi, occupati e offline (`runners.enabled`) |
| `ghamon_runner_up`, `ghamon_runner_busy` | `runner` | per runner (`outputs.prometheus.per_runner`) |
| `ghamon_runner_kind_jobs_waiting`, `ghamon_runner_kind_oldest_wait_seconds` | `kind` | job non avviati e attesa più vecchia per tipo di runner (`runners.model.enabled`) |

Con `outputs.prometheus.histograms` attivo (e il webhook che riceve eventi dei job) scrive anche **istogrammi**, costruiti in memoria dagli eventi firmati `workflow_job` e `workflow_run`:

| Metrica | Etichette | Significato |
|---|---|---|
| `ghamon_job_wait_seconds` | `runner_group`, `label` | tempo in coda di un job, contato **una volta per job** |
| `ghamon_job_run_seconds` | `runner_group`, `label`, `conclusion` | durata dei job finiti |
| `ghamon_workflow_run_seconds` | `conclusion` | durata delle esecuzioni finite |
| `ghamon_jobs_total` | `label`, `conclusion` | job finiti (contatore) |
| `ghamon_runner_jobs_waiting`, `ghamon_runner_oldest_wait_seconds` | `label` | la domanda di runner adesso: job in coda non avviati e attesa più vecchia |

`outputs.prometheus.histogram_max_series` (200 per impostazione predefinita) limita le serie di ogni istogramma: quelle oltre il limite si contano sotto il valore di etichetta `other`. Con `outputs.prometheus.per_runner` attivo aggiunge, per ogni runner self-hosted, `ghamon_runner_jobs_total`, `ghamon_runner_jobs_failed_total` e `ghamon_runner_busy_seconds_total` (anche in `GET /api/runners/model` come `per_runner`).

## Pacchetto di osservabilità: regole di allarme, Alertmanager, OnCall e n8n

`docs/grafana/` contiene, oltre ai due pannelli, un pacchetto da copiare e adattare:

- `ghamon_alert_rules.yml`: regole per Prometheus (anche vmalert) con il loro PromQL: un monitor che non risponde, workflow rossi e serie, quota e fatturazione vicine alla fine, un ciclo lento o fermo, repository nel circuito, letture che aspettano troppo, job che aspettano un runner (`histogram_quantile(0.95, sum by (le, label) (rate(ghamon_job_wait_seconds_bucket[30m])))`), runner offline e domanda senza runner libero.
- `alertmanager.example.yml`: percorsi per gravità verso tre destinatari (un webhook predefinito, Grafana OnCall e n8n). Tutti gli indirizzi sono `https://example.invalid/...`: non si invia nulla finché non metti i tuoi, e nessun segreto va nel file.
- `n8n_ghamon_alerts.json`: un flusso n8n che riceve il webhook di Alertmanager e scrive un messaggio per allarme; il suo ultimo nodo non fa nulla finché non ci metti il tuo nodo di chat, posta o ticket.
- `prometheus.example.yml` e `docker-compose.observability.yml` avviano Prometheus, Alertmanager e Grafana sul computer del monitor per provare il pacchetto (i container condividono la rete dell'host, le porte sono su `127.0.0.1` e la password di Grafana viene dalla tua shell, mai dal file).
## Dove chiama il monitor, ed eventi verso un SIEM

- **Tabella delle destinazioni di rete**: `monitor_cli.py doctor --egress` (anche con `--json`) elenca ogni host che la configurazione ATTUALE può chiamare, a cosa serve, l'impostazione che lo rende una destinazione e cosa non funziona se è bloccato: `api.github.com`, `github.com` e `objects.githubusercontent.com` (aggiornamenti), `raw.githubusercontent.com` (`lint.anonymous_public`), ntfy, Telegram, i webhook di chat, il provider di IA scelto, il collettore OTLP e le destinazioni SIEM. Con `airgapped` nulla è in uso. Un test mantiene la tabella uguale agli host nominati dal codice.
- **SIEM** (disattivato): `siem.sinks` nel file elenca le destinazioni, ciascuna con `enabled: true` per essere usata: `elasticsearch` (bulk), `splunk_hec`, `loki`, `sentinel` (Log Analytics, firmato con la chiave condivisa), `bigquery` (`insertAll`) o `http` (righe JSON). Il token o la chiave si legge dalla variabile d'ambiente indicata da `token_env`, mai dal file. Ogni destinazione filtra con `from_minutes` (5), `levels` e `repos_filter`; gli eventi hanno un elenco chiuso di campi (niente token né testo di log); un ricevitore su un indirizzo privato viene rifiutato salvo `allow_private`; se un ricevitore è fermo gli eventi attendono in una coda di `siem.queue_max` (500) e i più vecchi vengono scartati per primi. In modalità offline non viene inviato nulla.
