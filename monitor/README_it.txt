Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE

MONITOR DI GITHUB ACTIONS + SENTINELLA (versione 1.7.7)
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

CRONOLOGIA DELLE MODIFICHE
  Tutte le versioni, dalla più recente alla più vecchia, sono in CHANGELOG.md (in otto lingue in docs/CHANGELOG_*.md, e nella pagina: Guida > Registro delle modifiche).

GUIDA, INFORMAZIONI E VERIFICHE (1.6.4)
---------------------------------------
La pagina ha un pulsante Guida (? rotondo) e uno Informazioni (i); da console: --help-topics, --help-search, --about e --doctor; --demo mostra la pagina con dati inventati. L'edizione lite parte con un proprio banner e titolo di finestra (LITE, porta 8766, senza sentinella); la completa indica COMPLETE, porta 8765, sentinella attiva. L'avviso di nuova versione si può spegnere (Impostazioni > Di base).
