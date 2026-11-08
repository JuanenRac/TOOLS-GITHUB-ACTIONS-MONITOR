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
