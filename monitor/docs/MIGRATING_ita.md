<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Aggiornare da una versione precedente alla 1.5.0

[English](MIGRATING.md) · [Español](MIGRATING_spa.md) · [Français](MIGRATING_fra.md) · **Italiano** · [Deutsch](MIGRATING_deu.md) · [简体中文](MIGRATING_zho.md) · [日本語](MIGRATING_jpn.md) · [Português](MIGRATING_por.md)

La versione 1.5.0 ha dato nomi inglesi a file, cartelle, script e a un'impostazione. Non si perde nulla: il monitor continua a LEGGERE i vecchi nomi, quindi puoi aggiornare prima e riordinare dopo.

## Passi

1. Ferma il monitor e decomprimi la nuova versione sulla vecchia cartella (conserva il tuo `actions_monitor.json`).
2. Guarda cosa cambierebbe: `python migrate_state.py` (simulazione, non cambia nulla).
3. Fallo: `python migrate_state.py --apply` copia i vecchi file ai nuovi nomi e conserva i vecchi; aggiungi `--move` per rinominarli. Ciò che esiste già non viene mai sovrascritto, e l'impostazione `parte_history_days` diventa `report_history_days` dopo aver salvato una copia di `actions_monitor.json`.
4. Avvia il monitor con `MONITOR_GITHUB_ACTIONS` (lo stesso avviatore di prima) e usa `BATCH_GITHUB_ACTIONS` per gli strumenti a lotti.
5. Elimina i vecchi avviatori che ti restano: `LOTE_GITHUB_ACTIONS.bat`, `.sh` e `.command`.

## Nomi vecchi e nuovi

| Prima della 1.5.0 | Dalla 1.5.0 |
|---|---|
| `leer_parte.py` | `read_report.py` |
| `eventos.py`, `parte_history.py` | `events.py`, `report_history.py` |
| `LOTE_GITHUB_ACTIONS.*` | `BATCH_GITHUB_ACTIONS.*` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` |
| `PARTE_CENTINELA_*` | `SENTINEL_REPORT_*` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_*.json` | `<signed_dir>/batches/batch_*.json` |
| `parte_history_days` | `report_history_days` |
| `monitor_y_centinela` | `github_actions_monitor` |

`ci_red.json`, il suo schema e i file di `--export-status` non sono cambiati. La lingua è l'inglese finché non ne scegli un'altra nelle impostazioni.

# Da 1.5.x a 1.6.x

Non c'è nulla da convertire: il monitor continua a leggere il tuo `actions_monitor.json` e aggiunge le nuove chiavi, con valori sicuri, la prima volta che salvi dalle Impostazioni.

1. Ferma il monitor e decomprimi la nuova versione sulla vecchia cartella (conserva il tuo `actions_monitor.json` e i file di catalogo).
2. Avvialo come prima. Accanto compaiono nuovi file (`etag_cache.json`, `analytics_history.json`, `update_check.json`, `sentinel_history.json`); si possono eliminare in qualsiasi momento.
3. Facoltativo: `python actions_monitor.py --doctor` verifica l'installazione.

Cosa cambia: esiste l'**edizione lite** (`MONITOR_LITE_GITHUB_ACTIONS`, porta 8766, il suo `actions_monitor_lite.json`, senza sentinella); il **rosso su main** è una sola regola (l'ultimo run terminato di ogni workflow sul branch predefinito; i run annullati, saltati, neutri e scaduti non dicono nulla), quindi una cifra può differire dalla 1.5.x; la pagina Impostazioni inizia con la scheda **Di base**; notifiche, analitica, linter, eventi del webhook e assistente IA esistono e sono **spenti** finché non li attivi; scrivere su GitHub richiede ancora la tua conferma esplicita. Rich e Textual restano opzionali; Python 3.11 o successivo.

# Dalla 1.6.4 alla 1.6.5

Non c'è nulla da convertire. Ciò che ora si comporta in modo diverso, di proposito, perché ciò che non è provato non è più considerato sicuro:

- **Lotti**: `finalize` propone alla firma solo un'esecuzione il cui lotto REGISTRA di essere stata costruita sul commit verificato. Un lotto scritto da una versione precedente indica `needs_review`. Per usarlo comunque: `finalize --accept-legacy` rilegge l'esecuzione da GitHub, la accetta solo se il suo commit è quello registrato e chiede la parola LEGACY prima di ogni firma. Oppure rilancia la build.
- **CI verde** significa che i file di workflow obbligatori sono passati su quel commit (predefinito `ci.yml`; `dispatch.required_ci`, `dispatch.required_ci_repos`, `dispatch.required_ci_profiles`), che nulla è fallito né attende approvazione e che l'elenco delle esecuzioni è completo. Un repository il cui file di CI ha un altro nome deve indicarlo in `dispatch.required_ci`.
- **Un `git fetch` fallito** (niente rete, niente credenziali) ferma l'avvio di quel repository.
- **targets.json**: `tool` deve essere un semplice nome di file (senza cartelle né `..`) nella cartella degli strumenti; `extra` ammette solo coppie `-f chiave=valore` (non `dry_run` né `ref`); `finalize_flags` solo opzioni lunghe come `--bench`. Un catalogo non conforme viene rifiutato con il motivo.
- **Notifiche**: `max_per_hour` conta i messaggi (uno per canale), non gli eventi.
- **Webhook**: ogni richiesta richiede `X-GitHub-Delivery` (GitHub lo invia sempre); un id ripetuto viene ignorato; il proprietario di `full_name` deve essere l'account osservato.
- **act**: un clone che è un collegamento a un'altra cartella viene rifiutato (`act.allow_symlinks` lo consente).
- **Modalità rete**: solo indirizzi IPv4; l'indirizzo mostrato è quello su cui il server ascolta; `GET /api/sentinel/parte.txt?save=1` non scrive più (la copia è un POST con il token monouso).
- Il token GitHub conservato non viene più messo nell'ambiente del processo: lo riceve solo `gh`.
- Il test che decomprime lo zip in una cartella pulita non fa più parte della batteria ordinaria; `make_release.py` lo esegue come fase a sé.

# Dalla 1.6.5 alla 1.6.6

Non c'è nulla da convertire. Cosa si comporta diversamente, di proposito:

- **Modalità rete su HTTPS**: le modifiche fatte dalla pagina ora funzionano; l'`Origin` deve avere lo schema della sessione e la porta del monitor. Dietro un proxy mantieni la porta del monitor nell'indirizzo, altrimenti il controllo lo rifiuta.
- **Modalità rete**: ogni impostazione che lo schema contrassegna `secure` si cambia solo dal computer stesso (prima: solo `listen.`, `github_token.`, `act.`, `github_actions.`). Uno script su un altro computer che cambiava `webhook.*`, `notify.*` e simili ora riceve 403 `local_only`.
- **act**: dopo Stop l'esecuzione è libera subito; un avvio immediato non risponde più `busy`.
- File nuovi accanto al monitor: `degraded.json` e `degraded_lite.json` (i contatori dei guasti ingoiati); si possono eliminare in qualsiasi momento.
- Il registro delle modifiche (Aiuto > Registro delle modifiche) è tradotto: un file `docs/CHANGELOG_<lingua>.md` per lingua.

# Dalla 1.6.6 alla 1.6.7

Non c'è nulla da convertire. Cosa si comporta diversamente, di proposito:

- **Modalità rete dietro un proxy HTTPS sulla porta 443**: nuova impostazione `listen.proxy_public_host` (vuota per impostazione predefinita; se la lasci così non cambia nulla). Inserisci lì il nome host pubblico del proxy quando inoltra `Host` e `Origin` senza porta; quell'unico nome viene allora accettato così com'è, solo mentre la modalità rete è attiva e la sessione è HTTPS. Si cambia solo dal computer stesso. Dietro un proxy che mantiene la porta non cambia nulla.
- Il registro delle modifiche (Aiuto > Registro delle modifiche) è ora tradotto per la 1.6.7 e la 1.6.5 nelle altre sette lingue; le voci più vecchie mostrano ancora il testo inglese sotto un avviso tradotto.

# Dalla 1.6.7 alla 1.6.8

Non c'è nulla da convertire e nessuna impostazione cambia.

- Novità nel repository (non nel pacchetto): `python tools/manual_check_live.py proxy HOST [PORTA] [CONNETTI]` verifica il tuo vero proxy HTTPS sulla porta 443 rispetto a `listen.proxy_public_host`; imposta prima `MONITOR_ACCESS_TOKEN`, viene letto e mai stampato.
- Il registro delle modifiche (Aiuto > Registro delle modifiche) è ora tradotto nelle altre sette lingue dalla 1.6.8 alla 1.6.3.

# Dalla 1.6.8 alla 1.7.0

Non c'è nulla da convertire: senza una cartella `accounts/` il monitor funziona esattamente come prima.

- Gli **account multipli** sono facoltativi. Per usarli esegui `python actions_monitor.py --migrate-accounts` (una prova) e poi aggiungi `--apply` per copiare i tuoi file in `accounts/default/`; gli originali restano finché non li elimini. Aggiungi altri account come `accounts/<id>/actions_monitor.json`. Vedi `ACCOUNTS.md`.
- Con una cartella `accounts/`, `python actions_monitor.py` avvia un supervisore che esegue un monitor per account; `--account <id>` ne esegue solo uno. L'edizione lite non ha nulla di tutto questo.
- Novità: `?view=` e `?chrome=0` nell'indirizzo della pagina, `GET /api/accounts`, `GET /api/live-status` e un solo `POST /api/webhook` per tutti gli account.

# Dalla 1.7.x alla nuova struttura delle cartelle

Il codice ora vive in `src/github_actions_monitor/`, la pagina, i file di esempio e le lingue in `assets/`, e gli script di rilascio e di migrazione in `tools/`. Niente di ciò che usi cambia: i lanciatori (`MONITOR_GITHUB_ACTIONS`, `MONITOR_LITE_GITHUB_ACTIONS`, `BATCH_GITHUB_ACTIONS`) restano dove erano e aprono lo stesso indirizzo e la stessa porta, e i comandi di questa guida (`python read_report.py`, `python actions_monitor.py --doctor`, `python monitor_cli.py status` ...) continuano a funzionare, perché nella cartella del prodotto resta un piccolo file di ingresso con lo stesso nome. I lanciatori eseguono `python -m github_actions_monitor` (completo) e `python -m github_actions_monitor.lite` (lite) con `src/` nel percorso.

I tuoi dati non si spostano: `actions_monitor.json`, le cache, i log, `config_backups/`, `accounts/` e i tuoi file di catalogo restano nella cartella del prodotto accanto ai lanciatori, mai dentro `src/`. Gli esempi neutri e il `quotas.json` che viaggiano con il programma ora sono in `assets/examples/`; un tuo `quotas.json` accanto ai lanciatori ha ancora la precedenza.

## Passi

1. Ferma il monitor e decomprimi la nuova versione sulla vecchia cartella (conserva il tuo `actions_monitor.json`).
2. Avvialo come sempre. Funziona anche se non fai altro.
3. Per togliere i resti del vecchio layout piatto: `python tools/migrate_layout.py` (simulazione) e poi `python tools/migrate_layout.py --apply`. Copia i tuoi file di configurazione in `layout_backup_<marca>/config/` e sposta i vecchi moduli, la vecchia pagina, i vecchi esempi e la vecchia cartella `locales/` in `layout_backup_<marca>/old_code/`. Non si cancella nulla, non si sovrascrive nulla di esistente e i tuoi dati non vengono toccati. `python actions_monitor.py --doctor` avvisa finché restano vecchi file.
4. Un tuo script che importava un modulo con il vecchio nome piatto (`import read_report`) ora importa `github_actions_monitor.<pacchetto>.<modulo>` con `src/` nel percorso.

| Pacchetto | Contenuto |
|---|---|
| `app` | il server, le impostazioni, le modalità di lavoro, la configurazione condivisa |
| `accounts` | più account: registro, supervisore, processo figlio |
| `sentinels` | le sentinelle, il centro avvisi, i pannelli |
| `security` | guardia locale, segreti, webhook, conferma, guardia di rete, firme, file privati |
| `data_pipeline` | eventi, analitica, letture condizionali, rilevamento, quote, la regola del rosso su main |
| `integrations` | GitHub, notifiche, OpenTelemetry, mirror, runner, MCP, il feed e l'hook dell'IA |
| `cli` | gli strumenti da riga di comando |
| `ui` | Informazioni, documenti di aiuto, viste da terminale |
| `i18n`, `util` | le otto lingue; piccole utilità condivise |

## Spostare lo stato tra file e SQLite (1.8.0)

Per aggiornare non serve migrare nulla: i file restano il predefinito. Se vuoi lo stato in SQLite, `python tools/migrate_storage.py --from file --to sqlite` mostra cosa copierebbe (simulazione); aggiungi `--apply` per copiare e verificare. I tuoi file non vengono mai modificati né eliminati. Vedi [STORAGE_ita.md](STORAGE_ita.md).
