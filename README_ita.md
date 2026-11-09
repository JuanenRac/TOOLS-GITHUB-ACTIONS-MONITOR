<p align="center">
  <img src="images/GITHUB_ACTIONS_MONITOR_BANNER.svg" alt="GitHub Actions Monitor" width="100%">
</p>

# GitHub Actions Monitor

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <b>🇮🇹 Italiano</b> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

<p align="center">
  <a href="https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases/latest"><img src="https://img.shields.io/github/v/release/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR?label=version&color=2EE6A6" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL-3.0-or-later">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Dependencies-none-2EE6A6.svg" alt="No dependencies">
  <img src="https://img.shields.io/badge/Languages-8-FFB300.svg" alt="8 languages">
</p>

> Controlla i workflow di tutti i tuoi repository e ti dice, su una pagina locale, cosa è rosso, cosa è bloccato e cosa ti aspetta.

**GitHub Actions Monitor** è un piccolo programma che gira sul tuo computer. Chiede a GitHub, con il tuo accesso `gh`, le ultime esecuzioni di ogni workflow dei tuoi repository, decide cosa è davvero rosso, segnala ciò che conta (sicurezza, igiene, versioni pronte, quota) e mostra tutto su una pagina web che solo il tuo computer può aprire. Richiede solo Python e `gh`, non memorizza mai un token e, per impostazione predefinita, legge soltanto.

## In breve

| | |
|---|---|
| **Versione** | **1.7.1** · [tutte le release](https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases) |
| **Richiede** | Python 3.11+ e la CLI di GitHub (`gh auth login`); nient'altro (la vista console usa il pacchetto facoltativo `rich`) |
| **Si apre** | su una pagina di `127.0.0.1` soltanto, in otto lingue |
| **Scrive su GitHub** | mai da solo: solo i comandi a lotti che avvii con un `--go` esplicito |
| **Esporta** | `ci_red.json`, metriche Prometheus e JSON per Grafana (tutto spento finché non lo accendi) |

## Schermate

### La pagina

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_now_light.png"><img src="docs/screenshots/web_now_dark.png" alt="Adesso" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_light.png"><img src="docs/screenshots/web_sentinel_dark.png" alt="Sentinella" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_queue_light.png"><img src="docs/screenshots/web_sentinel_queue_dark.png" alt="Coda di firma (prima il più urgente)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_analytics_light.png"><img src="docs/screenshots/web_sentinel_analytics_dark.png" alt="A12 · Analisi: durate, tempo in coda, passi e workflow instabili" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_charts_light.png"><img src="docs/screenshots/web_charts_dark.png" alt="Grafici" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_repositories_light.png"><img src="docs/screenshots/web_repositories_dark.png" alt="Repository" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_history_light.png"><img src="docs/screenshots/web_history_dark.png" alt="Cronologia" width="92%"></picture></p>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_about_light.png"><img src="docs/screenshots/web_about_dark.png" alt="Informazioni" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_help_light.png"><img src="docs/screenshots/web_help_dark.png" alt="Guida, con ricerca e offline" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_basic_light.png"><img src="docs/screenshots/web_settings_basic_dark.png" alt="Impostazioni · Di base: piano, quote e rilevamento" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_network_now_light.png"><img src="docs/screenshots/web_network_now_dark.png" alt="La modalità rete: la barra rossa persistente" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_network_settings_light.png"><img src="docs/screenshots/web_network_settings_dark.png" alt="Impostazioni · la modalità rete con il suo avviso e il nome del proxy HTTPS" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_accounts_all_light.png"><img src="docs/screenshots/web_accounts_all_dark.png" alt="Tutti gli account: una scheda per account" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_accounts_one_light.png"><img src="docs/screenshots/web_accounts_one_dark.png" alt="La pagina di un account, con il selettore" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_accounts_live_light.png"><img src="docs/screenshots/web_accounts_live_dark.png" alt="Vista Live: il ricevitore webhook e la modalità di lavoro" width="92%"></picture></p>

<details><summary><b>Impostazioni, sotto-scheda per sotto-scheda</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_interface_light.png"><img src="docs/screenshots/web_settings_interface_dark.png" alt="Impostazioni · Questo browser" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_general_light.png"><img src="docs/screenshots/web_settings_general_dark.png" alt="Impostazioni · Generale" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_polling_light.png"><img src="docs/screenshots/web_settings_polling_dark.png" alt="Impostazioni · Aggiornamento e limiti" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_cache_light.png"><img src="docs/screenshots/web_settings_cache_dark.png" alt="Impostazioni · Letture e cache" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_sentinel_light.png"><img src="docs/screenshots/web_settings_sentinel_dark.png" alt="Impostazioni · Sentinella" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_surface_light.png"><img src="docs/screenshots/web_settings_surface_dark.png" alt="Impostazioni · Controlli di superficie (A10)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_readiness_light.png"><img src="docs/screenshots/web_settings_readiness_dark.png" alt="Impostazioni · Preparazione (A11)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_paths_light.png"><img src="docs/screenshots/web_settings_paths_dark.png" alt="Impostazioni · Cartelle e file" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_outputs_light.png"><img src="docs/screenshots/web_settings_outputs_dark.png" alt="Impostazioni · Uscite per altri strumenti" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_ai_light.png"><img src="docs/screenshots/web_settings_ai_dark.png" alt="Impostazioni · IA esterna per la sentinella" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_webhook_light.png"><img src="docs/screenshots/web_settings_webhook_dark.png" alt="Impostazioni · Webhook in ingresso" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_notify_light.png"><img src="docs/screenshots/web_settings_notify_dark.png" alt="Impostazioni · Notifiche" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_analytics_light.png"><img src="docs/screenshots/web_settings_analytics_dark.png" alt="Impostazioni · Analisi" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_lint_light.png"><img src="docs/screenshots/web_settings_lint_dark.png" alt="Impostazioni · Linter dei workflow" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_console_light.png"><img src="docs/screenshots/web_settings_console_dark.png" alt="Impostazioni · Vista da console" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_advanced_light.png"><img src="docs/screenshots/web_settings_advanced_dark.png" alt="Impostazioni · Avanzate (opzionali)" width="92%"></picture></p>

</details>

<details><summary><b>Strumenti da console</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_read_report_light.png"><img src="docs/screenshots/console_read_report_dark.png" alt="read_report.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_migrate_state_light.png"><img src="docs/screenshots/console_migrate_state_dark.png" alt="migrate_state.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_plan_light.png"><img src="docs/screenshots/console_plan_dark.png" alt="gha_dispatch_all.py plan" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_lint_light.png"><img src="docs/screenshots/console_lint_dark.png" alt="lint_workflows.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_tui_light.png"><img src="docs/screenshots/console_tui_dark.png" alt="tui.py" width="92%"></picture></p>

</details>

<details><summary><b>L'edizione lite</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_now_light.png"><img src="docs/screenshots/web_lite_now_dark.png" alt="lite · Adesso" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_charts_light.png"><img src="docs/screenshots/web_lite_charts_dark.png" alt="lite · Grafici" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_history_light.png"><img src="docs/screenshots/web_lite_history_dark.png" alt="lite · Cronologia" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_settings_light.png"><img src="docs/screenshots/web_lite_settings_dark.png" alt="lite · Impostazioni" width="92%"></picture></p>

</details>

Ogni immagine segue il tema chiaro o scuro della tua pagina GitHub.

*Dati dimostrativi: i repository e i nomi nelle immagini sono inventati.*

## Cosa fa

- **Rosso o no, con una sola regola**: l'ultima esecuzione terminata di ogni workflow sul ramo predefinito. Le esecuzioni annullate o saltate non nascondono mai un errore precedente.
- **Sentinella**: avvisi di sicurezza, igiene dei repository, pull request vecchie, versioni pronte da pubblicare, build in attesa di firma e un rapporto in linguaggio semplice.
- **Pagina delle impostazioni**: cambia percorsi, intervalli, quote e interruttori dal browser; solo un elenco fisso di chiavi validate, con copia di sicurezza prima di ogni salvataggio.
- **Grafici e storico**: minuti di calcolo, errori e successi con barre animate e uno storico giornaliero (rispetta il movimento ridotto).
- **Otto lingue** (en, es, de, fr, it, ja, zh, pt) con l'inglese come base; si cambia nelle impostazioni.
- **Uscite per dashboard**: `ci_red.json`, un endpoint Prometheus e una fonte JSON per Grafana, con una dashboard Grafana importabile.
- **Strumenti a lotti**: pianificano e avviano molte build insieme; nulla parte senza `--go`.
- **Informazioni e Guida nella pagina**: il pulsante **i** mostra versione, edizione, collegamenti, file, stato di salute e un pulsante che copia le informazioni per l'assistenza; il pulsante **?** (o il tasto `?`) apre tutta la documentazione, con ricerca e nella tua lingua, senza Internet. La console ha `--about` e `--help-topics`, e un'applicazione interattiva da terminale a schede (`textual` opzionale).
- **Avviso di nuova versione**: un badge discreto quando esce una versione più recente; legge la pagina pubblica dei rilasci una volta al giorno, non installa mai nulla e si può spegnere (sempre spento in un'installazione isolata).
- **Quote per ogni account**: piano, minuti fatturabili (i repository pubblici non costano), quota dell'API letta dalle intestazioni di GitHub, concorrenza e job vicini al limite di 6 ore; le cifre stanno in un file modificabile.

## Architettura

<p align="center"><img src="images/architecture.svg" alt="Architettura" width="100%"></p>

## Inizia da qui: quale edizione?

| Se vuoi... | Avvio | Porta |
|---|---|---|
| vedere cosa gira e cosa fallisce, nient'altro (**inizia da qui**) | `MONITOR_LITE_GITHUB_ACTIONS` | 8766 |
| tutto l'account sorvegliato per te: avvisi, release, firma, prontezza, analitica | `MONITOR_GITHUB_ACTIONS` (con la [sentinella](monitor/docs/SENTINEL_ita.md)) | 8765 |

La finestra della console indica quale gira, nel titolo e nella prima riga. Ancora un dubbio? `python actions_monitor.py --demo` apre la pagina con dati inventati e `--doctor` verifica la tua installazione. [I tuoi primi cinque minuti](monitor/docs/FIRST_STEPS_ita.md)

## Avvio rapido

1. Installa Python 3.11 o successivo e la [CLI di GitHub](https://cli.github.com/), poi esegui `gh auth login`.
2. Scarica questo repository (o lo zip dell'ultima release) e apri la cartella `monitor`.
3. Avvialo: Windows `MONITOR_GITHUB_ACTIONS.bat`, Linux `./MONITOR_GITHUB_ACTIONS.sh`, macOS doppio clic su `MONITOR_GITHUB_ACTIONS.command`, oppure `python actions_monitor.py` ovunque.
4. Apri l'indirizzo stampato (`http://127.0.0.1:<porta>`). Al primo avvio crea `actions_monitor.json` dall'esempio.
5. Apri **Impostazioni** per indicare il tuo account GitHub, gli ecosistemi (gruppi di repository per prefisso del nome) e il resto.

> Aggiorni da una versione precedente alla 1.5.0? [`monitor/docs/MIGRATING_ita.md`](monitor/docs/MIGRATING_ita.md)

## L'edizione lite

Un secondo prodotto, più semplice, nello stesso pacchetto: la pagina di ciò che è in corso e di ciò che fallisce, senza la sentinella. Per chi vuole solo osservare i propri run.

|  | Completa | Lite |
|---|---|---|
| Avvio | `MONITOR_GITHUB_ACTIONS` (`.bat` / `.sh` / `.command`) | `MONITOR_LITE_GITHUB_ACTIONS` (gli stessi tre) |
| Porta | 8765 | 8766 |
| Schede | Adesso, Sentinella, Grafici, Repository, Cronologia, Impostazioni | Adesso, Grafici, Repository, Cronologia, Impostazioni brevi |
| Intestazione | tutte le tessere, prontezza, firma | in corso, in coda, fallimenti e successi di 24 h, minuti di calcolo, issue, rossi su main, repository, quota, connessione |
| Sentinella (avvisi, release, coda di firma, prontezza, linter) | sì | no: non viene nemmeno importata |
| Analisi, notifiche, webhook, IA, uscite Prometheus / Grafana | sì, spente finché non le attivi | no: quei percorsi rispondono 404 |
| Configurazione | `actions_monitor.json` | `actions_monitor_lite.json` (creato al primo avvio; la sentinella vi è spenta) |
| File di stato | `etag_cache.json`, `analytics_history.json`... | gli stessi nomi con il suffisso `_lite` |

[`monitor/docs/LITE_ita.md`](monitor/docs/LITE_ita.md)

## Impostazioni

Tutto vive in `actions_monitor.json` (creato da `actions_monitor.example.json`). La scheda **Impostazioni** lo modifica in modo sicuro; token e segreti non vengono mai mostrati né salvati. Ecosistemi, obiettivi di build e profili a lotti sono file separati che indichi tu (`ecosystems_file`, `targets_file`, `profiles_file`); sono inclusi modelli neutri `*.example.json`. Riferimento completo: [`monitor/docs/SETTINGS_ita.md`](monitor/docs/SETTINGS_ita.md).

## Uscite per Grafana e dashboard

Tutto spento per impostazione predefinita, solo locale (`127.0.0.1`) e senza token aggiuntivi. Attivandolo nelle impostazioni ottieni `/metrics` (formato Prometheus), `/api/outputs/grafana.json` e `/api/outputs/dashboard.json`, più una dashboard Grafana importabile in [`monitor/docs/grafana`](monitor/docs/grafana). Dettagli: [`monitor/docs/OUTPUTS_ita.md`](monitor/docs/OUTPUTS_ita.md). Il formato di `ci_red.json`: [`monitor/docs/CI_RED_SCHEMA_ita.md`](monitor/docs/CI_RED_SCHEMA_ita.md).

## Sicurezza

- Ascolta solo su `127.0.0.1` e rifiuta le richieste il cui `Host` o `Origin` non è locale. Non associarlo mai a `0.0.0.0`: non ha login.
- Non memorizza alcun token: usa il tuo `gh` (a meno che tu non attivi il token opzionale del monitor in Impostazioni > Avanzate).
- Non scrive nulla su GitHub da solo. Solo `dispatch --go`, `dispatch --real` e `finalize --execute` scrivono, e solo quando li avvii tu.
- **Analisi**: p50 / p95 della durata, del tempo in coda e di ogni passo di ogni workflow, workflow instabili (falliti e poi passati sullo stesso commit) e workflow diventati più lenti; esportati in Prometheus e Grafana.
- **Risparmia quota e sopravvive a un'interruzione**: letture condizionali (un 304 non costa nulla) e una modalità ultima immagine con avviso offline che riprende da sola.
- **Webhook in ingresso e notifiche**: eventi firmati aggiornano un repository in tempo reale; messaggi facoltativi a Telegram, Discord, Slack, Matrix, MQTT o un indirizzo locale (mai una scrittura su GitHub).
- **Linter dei workflow e vista console**: `lint_workflows.py` controlla `.github/workflows` prima del push; `tui.py` (facoltativo, con `rich`) mostra una griglia in tempo reale nella console.
- **Assistente IA (spento per impostazione predefinita)**: riassunti, classificazione e spiegazioni con Ollama, un servizio compatibile OpenAI, Anthropic o `gh copilot`; solo comandi di un elenco chiuso, eseguiti solo dopo aver confermato ciascuno.
- La pagina delle impostazioni scrive un elenco fisso di chiavi validate, dopo aver salvato una copia di sicurezza.

## Test

Non richiedono rete né pacchetti aggiuntivi:

```
python -m unittest discover -s monitor/tests
```

## Struttura del repository

<p align="center"><img src="images/repository-structure.svg" alt="Struttura del repository" width="100%"></p>

```
TOOLS-GITHUB-ACTIONS-MONITOR/
├── monitor/                             il programma
├── docs/                                architettura, schermate, roadmap
├── tools/                               immagini, guide e demo
├── deploy/                              esempio di container
├── images/                              banner e immagini
├── .github/                             CI e moduli
├── CHANGELOG.md                         modifiche per versione
├── LICENSE NOTICE AUTHORS               licenze e autore
├── CONTRIBUTING.md SECURITY.md          contribuire, segnalare
├── SUPPORT.md CODE_OF_CONDUCT.md        supporto e condotta
└── monitor/
    ├── actions_monitor.py               server locale
    ├── actions_monitor.html             la pagina web
    ├── MONITOR_LITE_GITHUB_ACTIONS.*    l'edizione lite
    ├── sentinel_local.py                avvisi e rapporto
    ├── surface.py readiness.py          controlli, preparazione
    ├── settings_api.py outputs.py       impostazioni, metriche
    ├── signstate.py sigverify.py        firma: stato, verifica
    ├── read_report.py                   rapporto da terminale
    ├── gha_dispatch_all.py              build a lotti
    ├── events.py report_history.py      eventi e storico
    ├── ci_red.py export_status.py       file per altri
    ├── etagcache.py resilience.py       letture condizionali
    ├── analytics.py lint_workflows.py   durate, flaky, linter
    ├── notifiers.py ai_actions.py       notifiche, elenco chiuso IA
    ├── tui.py migrate_state.py          vista console, migrazione
    ├── about.py  helpdocs.py            pannelli Informazioni e Guida
    ├── quota.py  quotas.json            piano, minuti e quote
    ├── modes.py  updatecheck.py         modalità di lavoro, avviso di versione
    ├── doctor.py  demo_mode.py          --doctor e --demo
    ├── discovery.py  banner.py          rilevamento, banner di edizione
    ├── tui_textual.py                   terminale interattivo
    ├── i18n.py locales/                 otto lingue
    ├── toolconfig.py workspace.py       impostazioni, cloni
    ├── tests/                           test offline
    └── docs/                            guide, schemi, Grafana
```

## Documentazione

- [`monitor/docs/SETTINGS_ita.md`](monitor/docs/SETTINGS_ita.md): tutte le impostazioni
- [`monitor/docs/OUTPUTS_ita.md`](monitor/docs/OUTPUTS_ita.md): metriche, Grafana ed esportazioni
- [`monitor/docs/CI_RED_SCHEMA_ita.md`](monitor/docs/CI_RED_SCHEMA_ita.md): il formato di ci_red.json
- [`monitor/docs/CI_RED_BRIDGE_ita.md`](monitor/docs/CI_RED_BRIDGE_ita.md): portare ci_red.json in una dashboard
- [`monitor/docs/WEBHOOK_ita.md`](monitor/docs/WEBHOOK_ita.md): il webhook in ingresso
- [`monitor/docs/LITE_ita.md`](monitor/docs/LITE_ita.md): L'edizione lite
- [`monitor/docs/NOTIFICATIONS_ita.md`](monitor/docs/NOTIFICATIONS_ita.md): notifiche e contratto degli adattatori
- [`monitor/docs/AI_ita.md`](monitor/docs/AI_ita.md): l'assistente IA: provider, sicurezza e azioni
- [`monitor/docs/ANALYTICS_ita.md`](monitor/docs/ANALYTICS_ita.md): analisi, letture condizionali e connessione persa
- [`monitor/docs/CONSOLE_TOOLS_ita.md`](monitor/docs/CONSOLE_TOOLS_ita.md): il linter dei workflow e la vista console
- [`monitor/docs/DEPLOYMENT_ita.md`](monitor/docs/DEPLOYMENT_ita.md): eseguirlo come servizio, dietro un proxy, permessi
- [`monitor/QUICKSTART_it.txt`](monitor/QUICKSTART_it.txt): primi passi, in otto lingue
- [`monitor/docs/FIRST_STEPS_ita.md`](monitor/docs/FIRST_STEPS_ita.md): i tuoi primi cinque minuti
- [`monitor/docs/SENTINEL_ita.md`](monitor/docs/SENTINEL_ita.md): la sentinella e i suoi controlli A1-A13
- [`monitor/docs/QUOTAS_ita.md`](monitor/docs/QUOTAS_ita.md): quote e piani di GitHub
- [`monitor/docs/MODES_ita.md`](monitor/docs/MODES_ita.md): modalità di lavoro: normale, veloce e turbo

## Contribuire

Leggi [CONTRIBUTING.md](CONTRIBUTING.md). Segnala bug e idee con i moduli delle issue; i problemi di sicurezza come descritto in [SECURITY.md](SECURITY.md).

## Autore

Scritto da **JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## Licenza

Il codice è GPL-3.0-or-later; la documentazione è CC BY-SA 4.0. Vedi [LICENSE](LICENSE) e [NOTICE](NOTICE).
