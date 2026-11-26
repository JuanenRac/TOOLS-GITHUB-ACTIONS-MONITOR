<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI.md) | [🇪🇸 Español](CLI_spa.md) | [🇫🇷 Français](CLI_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](CLI_deu.md) | [🇨🇳 简体中文](CLI_zho.md) | [🇯🇵 日本語](CLI_jpn.md) | [🇵🇹 Português](CLI_por.md)

# La riga di comando come client del monitor

`python bin/monitor_cli.py COMANDO` chiede al monitor in esecuzione ciò che sa (un `GET` su `127.0.0.1`, o sull'indirizzo di `--url` / `MONITOR_URL`) e lo stampa. Non ripete il lavoro della pagina verso GitHub, non scrive mai su GitHub e non cambia nessuna impostazione. Gli strumenti precedenti (`bin/read_report.py`, `--doctor`, `bin/gha_dispatch_all.py`) continuano a funzionare come prima.

## Comandi

| Comando | Cosa mostra | Lite |
|---|---|---|
| `status` | versione, edizione, account, repository, cosa gira e cosa fallisce, la quota | sì |
| `health` (o `check`) | un controllo rapido prima di leggere qualcosa di pesante: il monitor è raggiungibile, accetta questo client, l'accesso GitHub dell'account risponde? | sì |
| `doctor` | i controlli di `--doctor` per questa installazione (il monitor non deve essere in esecuzione) | sì |
| `backup` | il backup completo dell'installazione (il monitor non deve essere in esecuzione): `backup create [FILE] [--account ID]`, `verify FILE [--deep]`, `restore FILE [--account ID] [--to-dir CARTELLA] [--force]`, `status`, `list`; `--encrypt` con `--key-env NOME` lo cifra (libreria opzionale); vedi [OPS_ita.md](OPS_ita.md) | no |
| `accounts` | gli account del supervisore (solo con più account) | no |
| `alerts` | gli avvisi di tutte le sentinelle in un elenco: `--sentinel ci\|collab\|security\|supply\|delivery`, `--level info\|warning\|error`, `--muted show\|hide\|only`; `--since 90m|24h|7d|2w` elenca quelli che sono stati aperti in un momento di quel periodo, anche i chiusi (dalla cronologia che il monitor tiene mentre funziona; un avviso conta come chiuso dopo dieci minuti di assenza) | no |
| `proposals` | le azioni proposte dall'IA (`ai.actions.enabled`): `proposals list`, `show ID`, `approve ID`, `reject ID`, `execute ID` (un id può essere abbreviato). `approve` e `reject` registrano solo la decisione; `execute` la esegue dalla stessa porta della pagina e richiede `ai.actions.execute`, e con `ai.actions.require_approval` prima un'approvazione. Approvare, rifiutare ed eseguire si può solo da questo computer | no |
| `score` | il punteggio dell'account: numero, lettera, tendenza, parti, copertura e scomposizione per repository; `--compare` lo confronta con lo storico della finestra | no |
| `compare` | questo periodo rispetto al precedente: le cifre con variazione e direzione, chi peggiora o migliora; `--window 7\|30d`, `--days all\|workdays\|weekend`, `--baseline previous\|year_ago`, `--format table\|json\|ndjson\|csv`; uscita 4 se una cifra ha pochi dati, 5 con `--fail-on` se una peggiora; `--format csv` con un altro comando è un uso errato (uscita 1) | no |
| `api` | l'API di lettura per i client: `api openapi` stampa il documento OpenAPI di ogni rotta congelata (reindirizzalo a un file), `api me` dice chi il monitor crede sia questo client (modalità, utente, ruolo, cosa può fare la sessione, versione del contratto); un monitor con `api.v1_enabled` chiuso lo dice; `api contract-check` lancia contro di esso la suite di contratto per i client (uscita 4 se una verifica fallisce) | no |
| `team` | la salute dei repository in classifica, prima quelli che richiedono una persona; `--severity warn\|bad` tiene i peggiori e `--repo owner/name` dà il dettaglio di uno | no |
| `live` | lo stato del ricevitore del webhook e gli ultimi eventi | no |
| `ai` | `ai models [--refresh]` elenca i modelli del provider IA con i dati di ciascuno; `ai test --provider NOME --model NOME` ne prova uno con un testo sintetico (latenza, token, costo stimato); `ai doctor` dice perché un'IA non risponde, senza stampare una chiave | no |
| `lessons` | ciò che gli errori di questa CI hanno insegnato: `lessons list`, `lessons brief --repo NOME` (da leggere prima di un push), `lessons failures`, `lessons close` | no |
| `briefs` | i brief delle schede che leggono gli strumenti di IA: `briefs index`, `briefs show SCHEDA`, `briefs all` | sì |
| `docs` | le guide di questa versione, lette dall'installazione (senza monitor): `docs list` le nomina con il titolo, `docs show NOME` ne stampa una nella lingua di `--lang` | no |
| `screens` | il menu Schermi della pagina: `screens list` (ogni tipo di schermo e se può essere aperto) e `screens urls` (gli indirizzi completi, pronti per un comando chiosco) | no |
| `keyring` | le chiavi pubbliche che possono firmare: `keyring list`, `add` (`--key-id`, `--public-key`, `--key-scope`, `--expires`), `revoke --key-id`, `verify --document FILE`; senza monitor, le chiavi private sono rifiutate | no |
| `verify-release` | una cartella di file di release scaricati, controllata senza rete con SHA256SUMS e la firma: `verify-release --folder DIR`; uscita 4 se non sono affidabili Inoltre `--installed` (questa installazione contro la distinta), `--attestations`, `--fetch` (serve `ops.verify_release.fetch`); `doctor --verify-release DIR` controlla l'installazione; `keyring check-rotation --document FILE` controlla l'annuncio di una nuova chiave. | no |
| `toolbox` | i piccoli strumenti dell'operatore che funzionano su questo computer, senza monitor in esecuzione: `toolbox limits [N]` (la configurazione rispetto ai suoi massimali), `toolbox workspaces` (gli spazi di lavoro e quello in uso), `toolbox ledger [--force]` (il registro delle notifiche già inviate; `--force` lo dimentica), `toolbox summary` (gli eventi per tipo, repository e giorno) e `toolbox export-events FILE` (gli eventi come jsonl, csv, parquet o duckdb secondo la fine del nome; parquet e duckdb richiedono il loro pacchetto, il file deve essere nuovo) | no |
| `credential` | un altro accesso a GitHub per un account mentre tutto gira: `credential replace\|reload [--account ID] [--new-token-file FILE\|-]`; non stampa mai un token | no |
| `install-skill` | copia una skill del monitor (`internal` o `external`) nella cartella da cui uno strumento di IA legge le sue skill: `install-skill external --dest CARTELLA`; il monitor non deve essere in esecuzione | no |
| `gh-token` | stampa un token di installazione di un'ora della GitHub App perché le letture di uno strumento consumino la quota dell'App (solo con `github_app.share_reads` attivo); eseguilo senza `--json` | no |
| `watch` | la stessa lettura, ancora e ancora (`watch status\|alerts`, `--interval`, `--once`, `--exit-on-change`); vedi [CLI_OPERATOR_ita.md](CLI_OPERATOR_ita.md) | no |
| `completions` | lo script di completamento per `bash`, `zsh`, `fish` o `powershell`, scritto dal parser reale (si limita a stampare) | no |
| `kiosk` | l'indirizzo del monitor per una TV o una parete (`ops`, `team`, `release`, `quiet`); vedi [KIOSK_ita.md](KIOSK_ita.md) | no |
| `metrics` | le cifre come righe `nome=valore` per cron e la posta; con `--if-problem` non scrive nulla quando va tutto bene; vedi [CLI_OPERATOR.md](CLI_OPERATOR.md) | no |

Opzioni di tutti i comandi: `--json` (la risposta come un documento JSON: `{"ok", "exit", "data"}`), `--account ID`, `--url URL`, `--lite` (porta 8766), `--timeout SECONDI` (da 1 a 60), `--lang CODICE`. In modalità di rete metti il token di accesso nella variabile d'ambiente `MONITOR_ACCESS_TOKEN`, quella che legge il monitor stesso (`MONITOR_TOKEN` è accettata come alias; `--token TOKEN` è l'ultima risorsa, perché un'opzione compare nell'elenco dei processi). L'ordine: `MONITOR_ACCESS_TOKEN`, poi `MONITOR_TOKEN`, poi `--token`. Viaggia nell'intestazione `X-Monitor-Access`, mai nell'indirizzo e mai a schermo. Un `--url` in `http` non cifrato verso un altro computer stampa un avviso su stderr (il token e le risposte viaggerebbero in chiaro): usa `https` fuori da una rete che controlli.

Ogni comando accetta anche `--format text|table|plain|json|ndjson` (`--json` è `--format json`); vedi [CLI_OPERATOR_ita.md](CLI_OPERATOR_ita.md).

La riga di comando è un client dell'API di lettura per i client: le rotte che il contratto congela (`docs/schemas/api_contract.json`) vengono richieste prima su `/api/v1/` e, se il monitor risponde 404 (l'API è chiusa, `api.v1_enabled`), si richiede la vecchia rotta e non si riprova il prefisso. Il documento è lo stesso per entrambe le vie, quindi l'output di nessun comando cambia. `cli.prefer_v1` (attivo per impostazione predefinita) lo disattiva e la variabile `MONITOR_CLI_PREFER_V1` (`0` o `1`) prevale. Le rotte che il contratto non congela si richiedono sempre alla vecchia maniera.

Gli orari scritti per le persone (la riga `Last read`, i silenziamenti, il registro, i rapporti, le notifiche) usano il fuso di questo computer e lo nominano, con l'ora UTC accanto (`11:43:07 CET (10:43:07 UTC)`). Un altro fuso si sceglie con `display.timezone` (`local`, `utc` o un nome come `Europe/Madrid`; la variabile d'ambiente `MONITOR_TIMEZONE` prevale sul file). `--json` mantiene UTC e aggiunge `updated_local`.

## Codici di uscita (stabili)

| Codice | Significato |
|---|---|
| 0 | tutto a posto |
| 1 | uso errato del comando (anche `--lite` con un comando che richiede l'edizione completa) |
| 2 | il monitor non è raggiungibile |
| 3 | il monitor rifiuta questo client, oppure l'accesso GitHub dell'account è fallito o scaduto (un problema di credenziale, non una quota esaurita) |
| 4 | il monitor risponde ma è degradato: offline, quota esaurita, ancora senza dati, un endpoint che non ha, o una risposta che non è JSON |
| 5 | `alerts --fail-on LIVELLO` ha trovato un avviso aperto di quel livello o peggiore (uno silenziato non conta) |
| 6 | `watch --exit-on-change` ha visto un cambiamento (solo quando si dà quell'opzione); vedi [CLI_OPERATOR_ita.md](CLI_OPERATOR_ita.md) |

Ogni errore porta un `help`: una frase con il passo successivo, che spesso nomina la guida da leggere (`docs show FIRST_STEPS`). Nel formato testo è l'ultima riga, che inizia con `aiuto:`; con `--json` è il campo `help` accanto a `error`: `{"ok": false, "exit": 2, "error": "...", "help": "..."}`.

## Esempi

```
python bin/monitor_cli.py health && python bin/monitor_cli.py alerts --fail-on error
python bin/monitor_cli.py alerts --sentinel collab --level warning --json
python bin/monitor_cli.py status --account org-acme
MONITOR_URL=http://192.168.0.20:8765 MONITOR_ACCESS_TOKEN=... python bin/monitor_cli.py health --json
```

`health` distingue tre cose: il monitor non risponde (2), l'accesso a GitHub fallisce (3) e la quota è esaurita o GitHub non è raggiungibile (4); un monitor che non ha finito la prima lettura lo dice (4) invece di mostrare cifre vuote.

## L'edizione lite

`python bin/monitor_cli.py status --lite`, `doctor --lite` e `health --lite` parlano con la porta 8766. I comandi che richiedono account, sentinelle o il ricevitore del webhook vengono rifiutati con il codice di uscita 1. L'edizione lite non ha account né API degli avvisi.

## `ai-hook`: dire a uno strumento di IA cosa vede il monitor

`python bin/monitor_cli.py ai-hook install|status|uninstall [--assistant|--cursor|--generic] [--scope project|user] [--project-dir DIR] [--dry-run] [--json]` non richiede un monitor in esecuzione. Aggiunge, mostra o rimuove lo script di collegamento `bin/ai_hook.py` nelle impostazioni degli hook di uno strumento di IA (vedi la guida agli avvisi per IA): il file di impostazioni viene unito, si conserva una copia e la risposta di `--json` è ASCII puro. `status` è l'azione predefinita.

## Il token di accesso nella riga di comando

In modalità di rete il token si legge da `MONITOR_ACCESS_TOKEN`, poi `MONITOR_TOKEN`, poi dalla prima riga di `--token-file FILE` (tieni quel file leggibile solo da te: su un sistema con modi di file il comando avvisa se altri possono leggerlo) e infine da `--token`, che compare nell'elenco dei processi e per questo stampa un avviso su stderr.

## Gli strumenti di archiviazione

`python tools/migrate_storage.py` sposta lo stato tra file e SQLite, e `python tools/backup_storage.py` crea, verifica e ripristina copie dell'uno o dell'altro (entrambi sono descritti in [STORAGE_ita.md](STORAGE_ita.md)). `--doctor` ha due controlli per essi: l'archiviazione e la conservazione.

## Il dispatcher a lotti: gli input di un workflow

`python bin/gha_dispatch_all.py plan --inputs` elenca inoltre, sotto ogni obiettivo, gli input che il suo workflow richiede quando viene avviato a mano (nome, tipo, obbligatorio o facoltativo, valore predefinito, opzioni di una scelta e descrizione). Sono letti dal file del workflow in `origin/main` del clone con `git show`: non si avvia nulla, non si invia nulla e `gh` non viene chiamato. `--json` aggiunge a ogni riga un elenco `inputs`; vale `null` quando il file non è in `origin/main` o usa una forma che il lettore non conosce (lo stile a flusso `inputs: {…}`), e `[]` quando il workflow non richiede input.

## Backup e il doctor

`backup` e `doctor` lavorano sulle cartelle dell'installazione, quindi non richiedono un monitor in esecuzione. `doctor` esce con `0` quando tutto va bene (anche con avvisi), `1` quando un controllo è fallito, `3` quando ci sono solo avvisi e `--strict` (o `ops.doctor.strict_exit`) è attivo, e `4` quando il doctor stesso non è riuscito a partire; sono i codici del doctor, gli altri comandi mantengono i codici di uscita qui sopra. `backup` esce con `0` quando ha finito e `1` quando viene rifiutato o il pacchetto non supera la verifica. La guida [OPS_ita.md](OPS_ita.md) contiene i controlli, il ripristino e il backup pianificato. Il doctor ha anche `compare_window` (il confronto di due periodi può guardare indietro di due finestre con la cronologia che richiede e conserva) e `etag` (la quota di letture condizionali risposte con 304 nel monitor che gira qui, e se le risposte di GitHub arrivano senza ETag).
