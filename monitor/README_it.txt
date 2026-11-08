Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE

MONITOR DI GITHUB ACTIONS + SENTINELLA (versione 1.6.4)
=======================================================
QUALE AVVIARE? (un nuovo utente decide in due minuti)
  COMPLETA  MONITOR_GITHUB_ACTIONS.*       la pagina con la sentinella (porta 8765): avvisi, coda di firma, analisi. Parti da qui se hai più repository.
  LITE      MONITOR_LITE_GITHUB_ACTIONS.*  la stessa pagina senza sentinella (porta 8766): cosa è rosso, bloccato o in corso. Più leggera; convive con la completa.
  BATCH     BATCH_GITHUB_ACTIONS.*         solo se firmi e pubblichi le tue build.
  TERMINALE python tui_textual.py (aggiungi --lite per l'edizione lite)   l'applicazione interattiva da terminale; tui.py --once stampa una schermata.
  CONTROLLO python actions_monitor.py --doctor (--json per gli script)   dice cosa manca e il comando esatto per sistemarlo.
  PROVA     python actions_monitor.py --demo   la pagina con dati inventati: senza gh, senza login, nulla di tuo viene toccato.

Requisiti: Python 3.11+ e GitHub CLI (`gh`) con l'accesso effettuato (gh auth login). Nient'altro: il nucleo non richiede pacchetti (la vista console, tui.py, usa il pacchetto facoltativo rich).
Passi rapidi per il primo utilizzo: QUICKSTART_it.txt.

AVVIO      Windows: MONITOR_GITHUB_ACTIONS.bat | Linux: ./MONITOR_GITHUB_ACTIONS.sh | macOS: doppio clic su MONITOR_GITHUB_ACTIONS.command
           (apre http://127.0.0.1:<porta>, solo in locale). Su qualsiasi sistema vale anche:  python3 actions_monitor.py  (Windows: py -3 actions_monitor.py)
BATCH      BATCH_GITHUB_ACTIONS.bat / .sh / .command  (gha_dispatch_all.py: plan, dispatch, status, finalize, hygiene). Facoltativo, per chi firma le proprie build in locale.
COSA NON FA MAI   Ascolta solo su 127.0.0.1 a meno che tu non attivi la modalità rete (Impostazioni > Avanzate: un indirizzo privato, un token di accesso per ogni richiesta, un avviso nella pagina). Non salva alcun token (lo chiede a `gh`) a meno che tu non attivi il token opzionale nell'archivio sicuro del sistema. Da solo non scrive nulla su GitHub: solo i comandi batch `dispatch --go`, `dispatch --real` e `finalize --execute` scrivono su GitHub (avviano workflow, creano la bozza non firmata, pubblicano), e solo quando li esegui tu.
           NON firma e NON pubblica nulla da solo: firmare e pubblicare sono comandi che esegui TU; il monitor li mostra solo come testo.
           Nessuna IA nel percorso critico; lo spiegatore facoltativo con IA è spento per impostazione predefinita.

LINGUA     8 lingue: en, es, de, fr, it, ja, zh, pt (portoghese del Portogallo). Parte in INGLESE: la lingua del sistema non decide. Scegline un'altra nella scheda IMPOSTAZIONI della pagina
           (icona dell'ingranaggio; il browser la ricorda), oppure con "language" in actions_monitor.json, con la variabile d'ambiente MONITOR_LANG o con --lang CODICE negli strumenti da riga di comando (prevale su tutto).
           Le righe lette dagli script (SKIP, DISPATCHED, READY, FAILED, Summary:, BUILD ONLY...) sono sempre in inglese.
CONFIG     actions_monitor.json (creato da actions_monitor.example.json al primo avvio). Chiavi utili: github_owner (vuoto = l'account di gh),
           language, ecosystems_file, targets_file, refresh_seconds, cold_refresh_seconds, max_workers, min_rate_remaining, sentinel.*
           ecosystems_file: raggruppa i repository per prefisso del nome (vedi ecosystems.example.json; "*" = tutti i repository). targets_file: catalogo delle build per
           gli strumenti di batch (vedi targets.example.json). profiles_file (profiles.example.json): profili di batch. Le chiavi che iniziano con "_" in questi file sono metadati.
WORKSPACE  FACOLTATIVO: una cartella con cloni locali dei tuoi repository (MONITOR_ROOT, "workspace_root" nel json, o una cartella superiore con un file .monitor-root).
           Senza, il monitor parte in MODALITÀ RIDOTTA e lo dice: solo ciò che dà l'API di GitHub (niente coda di firma locale, niente rapporto di audit, niente scansione del CHANGELOG).
           Con il workspace hai anche le release candidate, la coda di firma e gli strumenti di batch. Registri di firma: "signed_dir"; file di audit: "audit_dir".
TEST       py -3 -I -m unittest discover -s tests   (Linux/macOS: python3 -I -m unittest discover -s tests). Non richiedono la rete.
PROBLEMI   "API rate limit": la quota condivisa di gh (5000/ora) è esaurita; attendi il ripristino (gh api rate_limit) e alza refresh_seconds / abbassa max_workers.
           Il monitor si ferma all'avvio se gh non risponde. Un file di cache danneggiato viene ignorato; elimina sentinel_cache.json per ricominciare la cache.
           Riavvia il monitor dopo aver aggiornato il pacchetto (un processo in esecuzione conserva il codice vecchio).

STRUMENTI  read_report.py [--lang CODICE] [--json] [--export-status CARTELLA] [--export-sign-queue FILE]  stampa ciò che dice il monitor in esecuzione (locale, senza quota GitHub)
           gha_dispatch_all.py [--lang CODICE] plan|dispatch|status|finalize|hygiene    batch di build di GitHub Actions (sul tuo PC non si compila nulla)
           release_notes.py REPO [--since TAG] [--out FILE]    bozza di note di release dai commit (una proposta; non pubblica nulla)
           release_candidates.py    progetti con voci in CHANGELOG [Unreleased] e ultima release vecchia (sola lettura)
EVENTI     La sentinella scrive una riga JSON per ogni CAMBIAMENTO (nuovo rosso, CI ripristinata, build bloccato, nuovi avvisi...) in events_monitor.jsonl. Ogni riga ha un
           `code` stabile (mai dipendente dalla lingua), `kind`, `level`, `repo`, `args` e `text` (nella lingua configurata). `tail -F` la segue.
CI ROSSA   Un solo criterio: l'ULTIMO run terminato di ogni workflow sul branch predefinito. Rosso = failure, timed_out, startup_failure o action_required.
           cancelled, skipped, neutral e stale non contano.

NOVITÀ 1.5.1 (cronologia: CHANGELOG.md)
  - Scheda IMPOSTAZIONI: nuovo gruppo «IA esterna per la sentinella» (ai.provider none / ollama / openai-compatible, modello, indirizzo di Ollama (solo questo computer), un endpoint https, il NOME della variabile d'ambiente che contiene la chiave, chiamate al giorno). La chiave stessa non viene mai salvata. Spenta per impostazione predefinita; un servizio esterno riceve dati dei tuoi repository.
  - migrate_state.py: porta i file scritti prima della 1.5.0 ai nuovi nomi. `python migrate_state.py` è una simulazione; `--apply` copia (i vecchi restano), `--move` rinomina. Nulla viene sovrascritto. Una pagina in docs/MIGRATING.md, in 8 lingue.
  - Primo avvio senza file di catalogo propri: il monitor segnala che usa quelli di esempio (console), e `--init-catalog` crea copie modificabili di ecosystems.json, targets.json e profiles.json.
  - Python 3.11 o successivo (provato con 3.11 e 3.13, su Windows, Linux e macOS).

NOVITÀ 1.5.0 (cronologia: CHANGELOG.md)
  - Scheda IMPOSTAZIONI: modifica dalla pagina i valori di actions_monitor.json (elenco di chiavi consentite con tipo e intervallo, validate, copia in config_backups/ prima di ogni salvataggio, mai token né segreti; docs/SETTINGS.md).
  - Pulsanti in rilievo che si illuminano e si abbassano, icone SVG con nome e tooltip in 8 lingue, l'aspetto della dashboard di stato, barre e cifre animate (tutto si ferma con prefers-reduced-motion).
  - Uscite facoltative, spente per impostazione predefinita, solo su 127.0.0.1: /metrics (Prometheus), /api/outputs/grafana.json (Grafana JSON / Infinity), /api/outputs/dashboard.json (docs/OUTPUTS.md, dashboard di esempio in docs/grafana/).
  - Pacchetto neutro: i tuoi ecosistemi, obiettivi e profili stanno fuori (ecosystems_file, targets_file, profiles_file; tools_dir per gli strumenti di firma locali); inglese per impostazione predefinita; nomi di file e cartelle in inglese.
  AGGIORNANDO da 1.4.x: questi nomi sono cambiati (i vecchi si leggono ancora dove può esistere un file; si scrivono solo i nuovi):
  leer_parte.py -> read_report.py          eventos.py -> events.py          parte_history.py -> report_history.py
  LOTE_GITHUB_ACTIONS.bat/.sh/.command -> BATCH_GITHUB_ACTIONS.bat/.sh/.command
  eventos_monitor.jsonl -> events_monitor.jsonl          eventos_estado.json -> events_state.json
  PARTE_CENTINELA_DIA_<day>.* -> SENTINEL_REPORT_DAY_<day>.*     PARTE_CENTINELA_<time>.txt -> SENTINEL_REPORT_<time>.txt     CANDIDATAS_RELEASE.txt -> RELEASE_CANDIDATES.txt
  <signed_dir>/lotes/lote_<time>.json -> <signed_dir>/batches/batch_<time>.json     parte_history_days -> report_history_days     monitor_y_centinela.zip -> github_actions_monitor.zip
  sentinel.audit_files: names of the A8 audit files (neutral defaults RECONCILIATION_TOTAL_*.txt, ROUNDS_MAP_2*.txt, ROUNDS_MAP_EXTRA_*.txt)
  ci_red.json and --export-status: unchanged (a contract).

NOVITÀ 1.4.2 (cronologia: CHANGELOG.md)
  Quando A2 chiede l'ultimo run di un workflow nascosto, un run in corso o annullato non conta più come visto (potrebbe nascondere un rosso precedente): la Sentinella chiede gli
  ultimi run completati di quel workflow e usa il primo con una conclusione reale (cancelled e skipped sono ignorati). Se non ce n'è nessuno sul ramo predefinito, solo quel workflow resta non conclusivo.

NOVITÀ 1.4.1 (cronologia: CHANGELOG.md)
  A2 non dichiara più un intero repository non conclusivo solo perché il campione di esecuzioni è pieno: per ogni workflow del clone assente dal campione
  chiede a GitHub l'ultima esecuzione di quel solo workflow sul branch predefinito (sola lettura, stessa soglia di quota di A10, limitato da
  sentinel.a2_resolve_max_calls_per_tick, risposte conservate sentinel.a2_resolve_ttl_seconds). Il rosso conta come rosso; un workflow senza esecuzioni sul branch
  resta non conclusivo e il pannello lo nomina.

NOVITÀ 1.4.0 (cronologia: CHANGELOG.md)
  Pannello A11 "Prontezza": prontezza delle release per repository (CI del branch predefinito e il suo commit, versione sopra l'ultima release, build, firma, passo
  successivo), salute degli ecosistemi (punteggio solo da conteggi reali, trattenuto se pochi repository hanno dati) e versioni fissate indietro rispetto al fornitore
  (lette dai file di versione dei cloni locali, configurati in sentinel.readiness.pins.sources). Sola lettura; nulla viene stimato.

NOVITÀ 1.3.0 (cronologia: CHANGELOG.md)
  8 lingue nella pagina, nella riga di comando, negli eventi e nei rapporti; selettore di lingua; ecosistemi, target e account GitHub come dati (github_owner,
  ecosystems_file, targets_file); workspace facoltativo con una modalità ridotta onesta; paternità e GPL-3.0-or-later in ogni file; LICENSE, NOTICE, AUTHORS;
  README e QUICKSTART in 8 lingue.
LICENZA    GPL-3.0-or-later (vedi LICENSE e NOTICE). Copyright (C) 2026 JuanenRac (Electro Hobby 3D).

GUIDA, INFORMAZIONI E VERIFICHE (1.6.4)
---------------------------------------
La pagina ha un pulsante Guida (? rotondo) e uno Informazioni (i); da console: --help-topics, --help-search, --about e --doctor; --demo mostra la pagina con dati inventati. L'edizione lite parte con un proprio banner e titolo di finestra (LITE, porta 8766, senza sentinella); la completa indica COMPLETE, porta 8765, sentinella attiva. L'avviso di nuova versione si può spegnere (Impostazioni > Di base).
