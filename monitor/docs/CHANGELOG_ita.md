<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Registro delle modifiche

Versione dello strumento stesso (monitor + sentinella + strumenti batch), con il proprio semver. La fonte è il CHANGELOG.md in inglese; questo file ha le stesse versioni e sezioni.

## [1.7.0]

Più account nell'edizione completa, ciascuno un monitor a sé, e una pagina che li conosce. L'edizione lite non cambia: un account, e non mostra nemmeno le nuove opzioni.

### Aggiunto

- **Più account** (solo l'edizione completa). Una cartella `accounts/<id>/` per account (una persona o un'organizzazione) con il proprio `actions_monitor.json`, la propria cache, i propri eventi, analisi, stato della sentinella e registri; `accounts/global.json` è facoltativo (`default_account`, `enabled_accounts`) e `MONITOR_ACCOUNTS_DIR` sposta la cartella. L'id è formato da lettere minuscole, cifre, `_` e `-` (fino a 40), quindi è sempre un nome di cartella sicuro. Senza una cartella `accounts/` nulla cambia: un account, i suoi file accanto al codice.
- **Un supervisore** (`accounts_supervisor.py`): con una cartella `accounts/`, `python actions_monitor.py` avvia un piccolo processo sulla porta di sempre che esegue un monitor per account (`account_child.py`), ciascuno sulla propria porta di `127.0.0.1`. Un guasto, una risposta lenta o un limite di frequenza di un account non tocca mai un altro; un account caduto viene riavviato con un'attesa crescente (2, 5, 15, 30, 60, poi 120 secondi) e il riepilogo lo dichiara fermo nel frattempo. Non legge nulla da GitHub e non scrive nulla; fermarlo termina tutti i processi che ha avviato, anche su Windows.
- **L'API degli account**: `GET /api/accounts` (il riepilogo), `GET /api/accounts/<id>/status`, e ogni altra richiesta `/api/` va all'account indicato con `?account=<id>` o l'intestazione `X-Account-Id` (l'account predefinito senza nulla; un account sconosciuto dà 404). Le regole di accesso sono quelle di un monitor singolo, e il token monouso di una modifica si chiede allo stesso account a cui va la modifica.
- **Un webhook per tutti**: `POST /api/webhook` è un unico indirizzo per l'installazione; il supervisore legge solo il proprietario in `repository.full_name` e passa l'evento intatto all'account il cui `github_owner` è quel proprietario, che verifica la firma con il proprio segreto. Un proprietario che nessuno osserva riceve risposta e viene ignorato.
- **`--accounts`, `--account <id>` e `--migrate-accounts [--apply]`**: elencano gli account, eseguono solo uno come monitor ordinario e spostano il vecchio schema in `accounts/default/`. La migrazione è una prova salvo con `--apply`, non sposta né elimina mai gli originali, rifiuta una seconda esecuzione e non tocca i file dell'edizione lite.
- **La pagina con più account**: un selettore di account sotto l'intestazione e una voce **Tutti gli account** con una scheda per account (stato, repository, in esecuzione, in errore). Ogni finestra mantiene il proprio account e la propria vista, letti dall'indirizzo.
- **Viste per indirizzo** (`?view=now|alerts|charts|repos|settings|live` e `?chrome=0`, uno schermo senza pulsanti d'intestazione, schede né filtri per una parete o un secondo monitor). La vista **Live** mostra gli ultimi eventi inviati da GitHub, lo stato del ricevitore webhook (mai il segreto) e un selettore della modalità di lavoro. `GET /api/live-status` ne è la fonte.
- `tools/demo_accounts.py` per le immagini, la guida `ACCOUNTS.md` in otto lingue e test per ogni modifica (la suite è passata da 866 a 913).

### Modificato

- I file di stato di un monitor che è un account fra più stanno nella sua cartella tramite `state_dir()`; un monitor singolo li tiene accanto al codice, come sempre.
- Le immagini del README sono state rifatte e il README in otto lingue mostra gli account.

### Sicurezza

- Il supervisore e gli account ascoltano solo su `127.0.0.1` a meno che la modalità rete sia attiva. Il webhook non ha controllo dell'host né token di accesso (un tunnel cambia l'host) e la sua prova resta l'HMAC di GitHub; un cookie della sessione non viene mai passato a un account.

### Corretto

- La vista Live della 1.6.8 non aveva lo stato del ricevitore: con il webhook spento o con un segreto di meno di 32 caratteri non diceva nulla, e ora dice quale dei due.

## [1.6.8]

Il proxy HTTPS della 1.6.7 viene ora verificato contro un proxy reale, le immagini sono state rifatte e la cronologia delle modifiche è tradotta fino alla 1.6.3.

### Aggiunto

- `python tools/manual_check_live.py proxy HOST [PORTA] [CONNETTI]`: verifica, attraverso il tuo vero proxy HTTPS sulla porta 443, che la pagina venga ammessa (la sessione si apre con il token di accesso nel corpo e il cookie torna `Secure` e `HttpOnly`) e che tre richieste restino rifiutate (l'altro schema, un altro nome host, il nome con una porta). Legge il token di accesso da `MONITOR_ACCESS_TOKEN`, non lo stampa mai e, senza argomenti, dice cosa mettere in nginx o Caddy.
- `tools/demo_monitor.py --network` mostra la pagina come appare in modalità rete (la barra rossa persistente e, nelle Impostazioni, l'avviso per tutte le interfacce e il nuovo nome del proxy) per poterla fotografare; la demo continua ad ascoltare solo su `127.0.0.1`. `tools/make_screenshots.py` con esso scatta due nuove immagini: `web_network_now` e `web_network_settings`.
- Test che percorrono l'intera catena: un client su TLS reale, un reverse proxy che termina il TLS e inoltra `Host` e `Origin` senza porta, e dietro il vero monitor. Verificano che una modifica fatta dalla pagina raggiunga le impostazioni, che la stessa richiesta venga rifiutata senza `listen.proxy_public_host`, che uno schema, un nome o una porta sbagliati restino rifiutati, che la sessione si apra e il cookie sia `Secure`, e che il controllo a mano concordi con il proxy e non stampi mai il token (la suite è passata da 858 a 866).

### Modificato

- La cronologia delle modifiche (Aiuto > Registro delle modifiche) è tradotta nelle altre sette lingue dalla 1.6.8 alla 1.6.3 (la 1.6.7 e la 1.6.5 lo erano già); le voci precedenti alla 1.6.3 mantengono il testo inglese sotto un avviso tradotto.
- Le immagini del README sono state rifatte, 76 in tutto, e il README in otto lingue mostra la sotto-scheda Avanzate delle Impostazioni e le due immagini della modalità rete.
- `docs/MIGRATING.md` ha un blocco dalla 1.6.7 alla 1.6.8, e la roadmap in otto lingue elenca ciò che resta: le voci più vecchie della cronologia e i controlli che richiedono i tuoi servizi.

### Corretto

- La cronologia della 1.6.7 diceva che erano tradotte solo la 1.6.7 e la 1.6.5 e che il proxy era stato verificato solo con la guardia; questa versione traduce il resto fino alla 1.6.3 e verifica il proxy da un capo all'altro, come sopra.

## [1.6.7]

Un proxy HTTPS sulla porta 443 predefinita ora funziona con la modalità rete, e un'altra parte della cronologia delle modifiche è tradotta.

### Aggiunto

- `listen.proxy_public_host` (Impostazioni > Avanzate > Rete, vuoto per impostazione predefinita): il nome host pubblico di un proxy HTTPS sulla porta 443 predefinita che inoltra `Host` e `Origin` senza porta. Finora la guardia confrontava entrambi con la porta del monitor, quindi un proxy simile veniva rifiutato; quell'unico nome ora è accettato così com'è. Conta solo mentre la modalità rete è attiva e la sessione è HTTPS (TLS diretto o `listen.secure_cookie`), deve essere un semplice nome host (una porta, un percorso, un utente, uno spazio o un letterale IPv6 lo rendono vuoto), come ogni impostazione che lo schema contrassegna `secure` si cambia solo dal computer stesso, e la sua etichetta e il suo aiuto sono in otto lingue.
- Test per ogni modifica di questa versione (la suite è passata da 843 a 858 e il nuovo file verifica la guardia, il valore, lo schema e i testi).

### Sicurezza

- L'eccezione della guardia è la più stretta possibile: solo quel nome è accettato senza porta, mai un altro host senza porta, mai con HTTP semplice, e l'`Origin` deve portare lo stesso nome con lo schema `https` (un altro schema, una porta, un percorso, un utente o un host diverso restano rifiutati). Il nome del proxy non compare mai nello stato pubblico della guardia.

### Modificato

- La cronologia delle modifiche (Aiuto > Registro delle modifiche) è tradotta nelle altre sette lingue per la 1.6.7 e la 1.6.5 (la 1.6.6 lo era già); le voci più vecchie mantengono il testo inglese sotto un avviso tradotto e seguiranno, dalla più recente alla più vecchia.
- `docs/ADVANCED.md` (otto lingue) spiega il proxy sulla porta predefinita invece di dire che non è supportato, `docs/MIGRATING.md` ha un blocco dalla 1.6.6 alla 1.6.7, e la guida delle impostazioni e l'indice dell'Aiuto sono rigenerati.

## [1.6.6]

Correzioni della modalità rete e di `act`, i punti in sospeso della 1.6.5 e la cronologia delle modifiche in otto lingue.

### Aggiunto

- Una barra rossa persistente in cima alle Impostazioni quando la modalità rete è in ascolto su tutte le interfacce (`listen.host` = `0.0.0.0`), in otto lingue. Finora lo diceva solo `--doctor`.
- `POST /api/access` con `{"token": "..."}`: apre la sessione della modalità rete con il token di accesso nel corpo, così non resta mai in una barra degli indirizzi, in una cronologia o in un registro. Stessi controlli di ogni richiesta (host, origine, blocco dopo token errati, confronto a tempo costante); il cookie torna `HttpOnly`, `SameSite=Strict` e, con HTTPS, `Secure`. L'indirizzo con `?access=` della 1.6.5 continua a funzionare.
- Un contatore dei guasti che il monitor ingoia di proposito (`degraded.py`): una riga strutturata sulla console per ciascuno, un conteggio per origine in `degraded.json` accanto al monitor, il nuovo controllo `degraded` di `--doctor` e una riga «Errori ignorati» nel pannello Informazioni. Il comportamento non cambia: continuano a non fermare mai il monitor.
- La cronologia delle modifiche (Aiuto > Registro delle modifiche) ha ora un file di traduzione per lingua, `docs/CHANGELOG_<lingua>.md`, con le stesse versioni e sezioni della fonte inglese; `tools/make_help_index.py --check` e un test falliscono se una versione manca in una traduzione. Le voci non ancora tradotte lo dicono, nella lingua del lettore.
- Test per ogni modifica di questa versione (la suite è passata da 811 a 843).

### Corretto

- **La modalità rete su HTTPS era inutilizzabile dalla pagina.** La guardia di stessa origine accettava solo un'origine `http://`, quindi con TLS diretto o un proxy HTTPS (`listen.secure_cookie`) l'`Origin: https://...` del browser veniva rifiutata e ogni modifica (impostazioni, conferme) riceveva 403. Ora la guardia costruisce l'origine consentita con lo schema della sessione (https o http, mai entrambi), confronta host e porta esattamente e rifiuta un'origine malformata. Provato con un vero server TLS e un certificato creato dal test.
- `act`: Stop ora libera l'esecuzione, così l'avvio successivo non risponde più `busy` per sempre se il processo non termina; un worker in ritardo non tocca mai un'esecuzione più recente; la pipe di output e il timer vengono chiusi in ogni caso (fine normale, limite di tempo, Stop, errore imprevisto) e la suite non emette più `ResourceWarning`.
- `tools/make_screenshots.py` poteva terminare senza dire nulla: il browser gira senza pipe catturate e con un limite di tempo, si segnala l'assenza del browser o una demo che non parte, `MONITOR_BROWSER` indica un browser a mano e il codice di uscita è 1 se un'immagine non è stata fatta.

### Sicurezza

- In modalità rete, ogni impostazione che lo schema contrassegna `secure` può essere cambiata solo dal computer stesso, non più solo le quattro famiglie di prima (`listen.`, `github_token.`, `act.`, `github_actions.`): anche webhook, azioni dell'IA, notifiche, OpenTelemetry, mirror, runner, uscite e il resto. L'elenco è letto dallo schema, quindi una nuova impostazione sicura è coperta senza che nessuno la ricordi; un test le scorre tutte.

### Modificato

- Le immagini di Informazioni, Aiuto, Adesso, Base e Avanzate nel README e nelle guide sono rifatte.
- `docs/ADVANCED.md` (otto lingue): HTTPS con il tuo certificato o dietro un proxy, la regola dell'origine, la sessione aperta con POST e la barra di avviso.

## [1.6.5]

Una versione di integrità e sicurezza: nessuna grande funzione nuova. Ciò che non si può dimostrare non è più dato per sicuro.

### Aggiunto

- Nuove impostazioni, tutte con un valore predefinito prudente: `dispatch.required_ci` (e, nel file, `dispatch.required_ci_repos` e `dispatch.required_ci_profiles`), `act.allow_symlinks`, `listen.tls_cert_file`, `listen.tls_key_file`, `listen.secure_cookie`, `listen.max_failed_attempts`, `webhook.replay_seconds`, `webhook.max_per_minute`; la guida delle impostazioni viene rigenerata.
- `finalize --accept-legacy` per i batch scritti da una versione precedente, e i controlli `risks` e `backend` di `--doctor` (otto lingue).
- Test per ogni modifica di questa versione (la suite è passata da 729 a oltre 800).

### Sicurezza

- **Un commit verde richiede la CI obbligatoria.** `gha_dispatch_all.py` considera verde un commit solo quando i file di workflow obbligatori hanno avuto successo su di esso (`ci.yml` per impostazione predefinita; `dispatch.required_ci`, `dispatch.required_ci_repos`, `dispatch.required_ci_profiles`), nulla è fallito, scaduto o attende un'approvazione (`action_required` blocca come un fallimento), nulla è ancora in corso e l'elenco delle esecuzioni è completo (legge fino a cinque pagine; un elenco più lungo non è verde).
- **Un `git fetch` fallito ferma l'invio** di quel repository, i comandi git hanno un limite di tempo e gli id dei commit vengono verificati; un vecchio `origin/main` non è mai preso come prova.
- **Il catalogo non può uscire dalla sua cartella né cambiare l'invio.** `tool` deve essere un semplice nome di file che si trova nella cartella degli strumenti (anche i collegamenti che ne escono sono rifiutati); `extra` può contenere solo input di workflow `-f chiave=valore` (mai `dry_run`, `ref`, `-R`, `--ref`); `finalize_flags` solo opzioni lunghe; gli argomenti di `gh workflow run` sono costruiti dai pezzi validati e ricontrollati quando il batch parte.
- **I vecchi batch non si firmano alla cieca.** `finalize` propone alla firma solo un'esecuzione il cui batch ha registrato di essere stato costruito sul commit verificato. Un batch scritto da una versione precedente è `needs_review`; `finalize --accept-legacy` rilegge l'esecuzione da GitHub, la accetta solo se il suo commit è quello registrato, avvisa e chiede la parola LEGACY prima di ogni firma.
- **`act` resta dentro lo spazio di lavoro.** Il clone viene risolto e deve essere una vera cartella dello spazio di lavoro (un collegamento, un nome con `..` o un `.github` che punta altrove è rifiutato; `act.allow_symlinks` consente un collegamento a un clone). Il limite di tempo e Stop terminano l'intero albero di processi avviato dall'esecuzione (un gruppo di processi su Linux e macOS, `taskkill /T` sul proprio PID su Windows) e rimuovono i container `act-` creati da quell'esecuzione.
- **Modalità rete**: HTTPS servito direttamente con il tuo certificato e la tua chiave (`listen.tls_cert_file`, `listen.tls_key_file`; TLS 1.2 o successivo; il monitor non parte in HTTP semplice se non possono essere usati) o il cookie `Secure` dietro un proxy HTTPS (`listen.secure_cookie`); il token di accesso lascia subito la barra degli indirizzi (reindirizzamento, nessun `Referer`); un indirizzo che invia troppi token errati è rifiutato per cinque minuti (`listen.max_failed_attempts`); l'indirizzo della pagina è quello su cui il server è in ascolto; sono accettati solo indirizzi IPv4, nelle impostazioni come nella guardia; la console avvisa quando la connessione è HTTP semplice.
- **Webhook**: ogni consegna richiede il suo id `X-GitHub-Delivery` e una ripetuta viene ignorata per `webhook.replay_seconds`; un repository può causare al massimo `webhook.max_per_minute` eventi accettati al minuto; il proprietario in `full_name` deve essere l'account osservato; un indirizzo è limitato a 120 richieste al minuto in modalità rete; un evento accettato scarta le letture condizionali salvate di quel repository e lo segna per il ciclo successivo; un'intestazione di firma con caratteri insoliti è un semplice rifiuto.
- **Server MCP**: un messaggio di forma errata (parametri, argomenti, id, metodo) riceve un errore solo per quel messaggio, un difetto inatteso in uno strumento è un errore interno che non termina il server, e una riga oltre 64 KB è rifiutata.
- **Il token GitHub salvato è dato solo a `gh`.** Non viene più messo nell'ambiente del monitor, quindi `act`, il tuo comando di notifica e ogni altro processo figlio non possono ereditarlo.
- **Un GET non scrive mai.** La copia del rapporto giornaliero nella cartella di audit è un POST con il token monouso (`/api/sentinel/parte/save`); `?save=1` sul GET non esiste più.
- `--doctor` nomina le combinazioni pericolose (modalità rete su tutte le interfacce, azioni dell'IA che eseguono con la modalità rete attiva, `act` con la modalità rete attiva, il token in un file in chiaro) e mostra dove è conservato il token, mai il token.

### Corretto

- `max_per_hour` delle notifiche ora limita i messaggi (un'unità per canale, prenotata subito sotto un unico blocco) e non gli eventi; un canale che non può inviare non prenota nulla.
- Due salvataggi delle impostazioni contemporanei non ne perdono più uno (un blocco nel processo e un file di blocco).
- L'esportazione della coda di firma dice perché non ha scritto (un'unità o un percorso di rete rifiutato, una cartella al posto di un file, l'errore del sistema) invece di un semplice rifiuto.
- L'attesa del limite secondario e il nuovo tentativo dopo un timeout portano un jitter casuale.
- Il test che decomprime lo zip in una cartella pulita non fa più parte della suite ordinaria: `make_release.py` esegue la suite una volta con un limite di tempo, poi l'installazione pulita come fase a sé, e mostra stdout e stderr quando una fallisce.

### Modificato

- Le guide di notifiche, webhook, funzioni avanzate, uscite, avvisi dell'IA e migrazione dicono tutto questo in otto lingue; `docs/MIGRATING.md` ha un blocco dalla 1.6.4 alla 1.6.5.

## [1.6.4]

### Aggiunto

- **Avvisi per le IA**: il monitor scrive un feed locale di sola lettura (`ai_alerts.jsonl`, una riga per evento, e `ALERTS_BRIEF.md`, riscritto a ogni ciclo, 2 KB per impostazione predefinita) con un avviso per ogni workflow rosso: id stabile, gravità, causa probabile distinta come reale o transitoria con regole modificabili, azione suggerita e uno stato (aperto, riconosciuto, risolto da solo quando il workflow torna verde). Tutto passa per un pulitore di token, chiavi, indirizzi e-mail, indirizzi IP e cartelle personali. `GET /api/ai/brief` e `GET /api/ai/alerts`, un server MCP opzionale di sola lettura (`mcp_server.py`: `get_alerts`, `get_red_repos`, `get_run_failure`, `get_quota` e `ack_alert` con `--allow-ack`), una notifica quando compare un nuovo avviso REALE, un hook opzionale verso un indirizzo di questo computer (spento) e un `ai_hint` opzionale in `ci_red.json`. Nuova guida `AI_ALERTS.md` in otto lingue.
- **Funzioni opzionali, tutte spente per impostazione predefinita, ciascuna con il suo interruttore in Impostazioni > Avanzate** e test che provano che rifiutano senza l'interruttore, la conferma o il token: la modalità rete (un indirizzo privato, un token di accesso per ogni richiesta, nomi host accettati, una barra rossa persistente, chiavi di esposizione modificabili solo dal computer stesso); un token GitHub conservato dal monitor nell'archivio sicuro del sistema (DPAPI di Windows, Keychain di macOS, Secret Service di Linux, altrimenti un file con permessi 600) e mai in un'impostazione, un registro o una risposta, con un pulsante di cancellazione; azioni su GitHub (rieseguire, annullare, chiudere, unire), ciascuna confermata a parte dopo aver mostrato esattamente cosa verrà inviato; eseguire un workflow qui con `act` da una lista chiusa, senza segreti reali; una copia locale degli artefatti; runner self-hosted (inattivi, occupati, offline, disco e carico opzionali); esportazione OpenTelemetry (tracce e metriche, OTLP/HTTP JSON); le organizzazioni del login; FinOps per etichette dei job (Linux, Windows, macOS e runner più grandi), il prezzo dei minuti oltre quelli inclusi, Codespaces, Packages e archiviazione dal rapporto di fatturazione. Nuova guida `ADVANCED.md` in otto lingue e `tools/manual_check_live.py` per provare a mano i servizi reali.
- `--doctor --json`; il doctor segnala anche le porte occupate, il margine rimasto, se hai un tuo file dei target, il token monouso e l'esposizione. Il README del pacchetto inizia con la scelta del lanciatore (completo, lite, batch, terminale, doctor, demo).
- L'applicazione da terminale modifica le impostazioni semplici (non quelle di sicurezza) e ha una scheda IA; un avviso persistente per le impostazioni che richiedono un riavvio sopravvive a un ricaricamento; l'intestazione mostra quando l'A10 della sentinella è in pausa per la quota e quanto del budget di minuti è stato usato; anche il server ricorda il benvenuto.
- `redrule.py` ignora le esecuzioni dinamiche degli aggiornamenti delle dipendenze come fa la dashboard, e i casi condivisi della regola sono ora una fixture di test.

### Modificato

- **L'Aiuto è completo in otto lingue**: i documenti di roadmap, contributi, sicurezza e supporto sono tradotti, le etichette fisse del registro delle modifiche sono tradotte e le sue voci sono segnate come solo in inglese, con un avviso tradotto; `tools/make_help_index.py --check` e un test falliscono quando a un argomento manca una lingua. Una ricerca mostra al massimo 30 risultati e un documento enorme non trattiene più il thread del server.
- La tessera rossa conta i workflow in entrambe le edizioni e dice in quanti repository. L'edizione lite eredita il ritmo di aggiornamento di quella completa al primo avvio.
- Un errore passeggero (un singhiozzo TLS, un 5xx) viene ritentato con un'attesa esponenziale e mostrato come errore solo dopo tre cicli di fila; resta l'ultima immagine.
- La vista da terminale dell'edizione lite non chiede più la sentinella; l'edizione lite non carica mai il modulo della sentinella (la guardia locale è passata in `localguard.py`).
- `--demo` reindirizza alla sua cartella temporanea ogni file che potrebbe scrivere (registri, cache, feed degli eventi, cronologia, benvenuto).

### Sicurezza

- Con `updates.check` spento o `airgapped` acceso, il monitor non fa alcuna richiesta di rete per l'avviso di aggiornamento (testato).
- Verificato contro la vera API di GitHub: gli scope del token vengono letti correttamente, l'elenco delle organizzazioni e il rapporto di fatturazione degradano in silenzio (un login senza lo scope `user` riceve «non trovato» e il monitor tiene la stima).

## [1.6.3]

### Aggiunto

- **Pannello Informazioni** (il pulsante **i** dell'intestazione, in entrambe le edizioni): versione, edizione, autore, licenza, Python e sistema, link (repository, release, registro delle modifiche, documentazione, issue), i file che usa (sola lettura), lo stato del server, i riconoscimenti delle librerie e un pulsante che copia le informazioni per il supporto (nessun segreto, nessun token, la cartella personale mostrata come `~`). `GET /api/about`, e `--about` in console.
- **Pannello Aiuto** (il pulsante **?**, il tasto `?`, e un «?» nella barra delle schede che apre la pagina della scheda in cui ti trovi): tutta la documentazione (README, avvio rapido, ogni guida, roadmap, registro delle modifiche, contributi, sicurezza) come indice in cui cercare, nella lingua della pagina e in inglese dove un documento non è tradotto, servito dal server locale senza Internet. Viene costruito dai documenti reali da `tools/make_help_index.py` (`--check` nella CI), così nessun testo è scritto due volte; il markdown è mostrato in modo sicuro (tutto con escape, nessuna immagine caricata, solo link `http(s)` e link ad altri documenti). In console: `--help-topics [ARGOMENTO]` e `--help-search PAROLE`.
- **Avviso di una versione più recente**: un badge discreto nell'intestazione, una riga in Informazioni, in console e in `--doctor` quando viene pubblicata una release più recente. Una sola richiesta di sola lettura al giorno alla pagina pubblica delle release, con lo stesso client di tutto il resto (lettura condizionale), non scarica né installa mai nulla, non invia nulla su di te, ignora le prerelease, confronta le versioni come numeri (1.6.10 è più recente di 1.6.9), tace offline e si spegne con `updates.check` o in un'installazione isolata (`airgapped`).
- **Impostazioni > Base**, la prima scheda: aprire il browser all'avvio, l'avviso di aggiornamento, l'interruttore dell'installazione isolata, il token monouso, le opzioni di scoperta, le regole del ciclo di vita, e il piano e le quote. Sotto, ciò che il monitor ha trovato nell'account (proprietario, repository trovati, osservati, esclusi), le novità e i gruppi suggeriti.
- **`--doctor`**: Python, `gh`, il login, il margine rimasto, la rete, il permesso di scrittura della cartella, una porta libera, e gli opzionali Docker, Rich e Textual; ogni errore arriva con il comando esatto che lo risolve, in otto lingue.
- **`--demo`**: la pagina con dati inventati, senza `gh`, senza login e senza rete; nulla di tuo viene letto o scritto.
- **Un benvenuto in tre passi** la prima volta che si apre la pagina (cosa fa, cosa ha trovato nel tuo account, dove andare dopo).
- **Scoperta automatica**: eventi per un repository nuovo, sparito, archiviato o ripristinato (console, Impostazioni > Base e, nell'edizione completa, le notifiche); un gruppo suggerito quando tre o più repository non classificati condividono un prefisso, aggiunto solo dopo la tua conferma e con una copia del file; regole del ciclo di vita per escludere fork, repository vuoti e privati; una frequenza di aggiornamento automatica opzionale che segue l'attività reale entro il budget di chiamate.
- **Un token monouso** (`session_guard`, attivo per impostazione predefinita) che la pagina chiede subito prima di salvare un'impostazione o confermare un'azione, e una **barra di riavvio** su ogni scheda finché un'impostazione salvata attende un riavvio.
- **Livelli del linter dei workflow** (informazione, avviso, errore) come filtri nella pagina, e `Scripts` nell'applicazione da terminale.
- **Quote e piani per ogni tipo di account**: il tuo piano in Impostazioni > Base; le cifre (minuti inclusi come denaro, tariffe per sistema, concorrenza, limiti di un job e di un'esecuzione, margini dell'API) stanno in `quotas.json`, che puoi modificare senza una nuova versione; minuti fatturabili distinti dai minuti di orologio (i repository pubblici non costano nulla, quelli privati usano il moltiplicatore di Windows o macOS), una proiezione mensile segnata come stima, un avviso una volta al mese al 75 % e al 90 % dei minuti inclusi tramite le notifiche, job in esecuzione e in coda rispetto al limite del piano, job vicini al limite di 6 ore e il tipo di token letto dalle intestazioni stesse di GitHub (con il consiglio di accedere quando restano solo 60 chiamate l'ora). L'uso reale viene solo dal rapporto di fatturazione opzionale e di sola lettura (`quota.billing_api`, spento per impostazione predefinita, silenzioso su un 403 o 404). `GET /api/quota`.
- **Modalità di lavoro: normale, veloce e turbo** (`modes.py`, guida `MODES`): un selettore con un'icona a indicatore nell'intestazione e `--mode` / `--mode-minutes` in console, in entrambe le edizioni. I preset stanno nel blocco `modes` della configurazione; prima di partire la pagina mostra le chiamate all'ora nel caso peggiore, quanto risparmiano di solito le letture condizionali e quanto durerebbe il margine rimasto; torna normale da solo quando il tempo finisce o quando il margine scende sotto `min_rate_remaining`, con un avviso; senza login (60 chiamate l'ora) veloce e turbo vengono rifiutati con il motivo; richiede il token monouso, vive in memoria e il banner della console lo nomina. `GET` e `POST /api/mode`.
- **Dopo un limite di frequenza secondario** il monitor attende almeno un minuto e poi raddoppia l'attesa fino a cinque minuti invece di riprovare subito.
- **L'applicazione da terminale interattiva** `tui_textual.py` (opzionale, `pip install textual`): schede Riepilogo, Repository, Build, Prestazioni, Script e Impostazioni (gli interruttori di base), un filtro, i livelli del linter, aggiorna, apri nel browser, Informazioni e Aiuto; `--lite` mostra le schede dell'edizione lite. La vista semplice con Rich (`tui.py`, `--once`) resta e ha anche `--about` e `--help-topics`.
- **L'edizione si riconosce a colpo d'occhio**: un banner di avvio (`GitHub Actions Monitor LITE 1.6.3 · porta 8766 · actions_monitor_lite.json · senza sentinella · http://127.0.0.1:8766/`, oppure COMPLETE · porta 8765 · sentinella attiva), il titolo della finestra della console e del terminale, l'etichetta `[LITE]` / `[COMPLETE]` nelle righe di stato, in `--doctor` e nelle viste da terminale, e lo stesso titolo nei lanciatori.
- Nuove guide in otto lingue: **La sentinella e i suoi controlli A1-A13** (cos'è, come parte, i file che scrive, come leggerla, la regola esatta, l'impostazione e l'azione di ogni controllo e i venticinque controlli di A10; un test mantiene guida e codice in accordo), **Quote e piani** e **I tuoi primi cinque minuti** (`FIRST_STEPS`); la guida alla migrazione ha un blocco da 1.5.x a 1.6.x e il README ha un selettore tra le due edizioni.
- Test per tutto questo (le versioni semantiche, l'avviso offline, spento e in installazione isolata, il markdown sicuro, l'indice, il token monouso, la scoperta, `--doctor`, le quote per repository pubblici e privati, Windows e macOS, senza token, Enterprise e un 403 del rapporto di fatturazione, il banner e i lanciatori).

### Modificato

- La pagina delle Impostazioni inizia con la scheda **Base**; la guida `SETTINGS` viene generata con essa.
- Il monitor elenca i repository dell'account con il loro tipo (archiviato, fork, privato, vuoto); un `gh` più vecchio senza quei campi torna all'elenco semplice.

### Sicurezza

- Nulla di nuovo scrive su GitHub. L'avviso di aggiornamento, il rapporto di fatturazione e la scoperta sono di sola lettura e disattivabili; nessuno invia dati su di te. I pannelli Aiuto e Informazioni sono serviti da questo computer e il testo di supporto non contiene alcun segreto.
- Scrivere un'impostazione, confermare un'azione dell'assistente IA e aggiungere un gruppo suggerito richiedono il token monouso della pagina.

## [1.6.2]

> Questa versione è per ora disponibile solo in inglese; la traduzione arriverà in una versione successiva.

### Aggiunto

- **A catch-all group** `rest` ("Everything else", prefix `*`) at the end of the example catalogue of ecosystems, so a new installation leaves no repository out.
- **An automatic group "Unclassified"** for the repositories that no group claims (setting `show_unclassified`, on by default; an explicit choice of ecosystems is respected).
- **A warning when the filter hides repositories**: a banner (complete and lite) says "your ecosystem filter hides N of the M repositories of the account" and names them.
- **The lite edition starts with what you already set up**: on its first start `actions_monitor_lite.json` copies from `actions_monitor.json` (when it exists) the account, the repositories and ecosystems to watch, the catalogue files, the exclusions, the language and the reading depth, and says so on the console. Without such a file its template watches all the ecosystems.
- **`tui.py --lite`** (or `MONITOR_MODE=lite`) reads the lite edition on port 8766.
- **`redrule.py`**, the single small rule of "red on main", used by the sentinel and by the lite edition (which marks the figure as approximate because it guesses the default branch).
- **`ghamon_etag_invalid_total`**, the count of damaged cache entries, in `/metrics`.
- Tests: header-data parity between the complete and the lite edition, the catch-all group, the hidden-repository count, the lite start, the webhook hot mark, the damaged cache entry, and that importing the monitor or the sentinel never loads Rich.
- Guides `LITE` and `SETTINGS` (eight languages) updated.

### Modificato

- **Both editions show the same header figures**: runs, failures, successes, compute minutes, running and queued are counted once, by the server, over the same 24 hours with each run counted once; the lite edition reads as deep as the complete one. The lite edition hides the "unsigned" tile.
- **A webhook event marks the repository as hot**, so the next cycle reads it again whatever the event said.
- The GitHub allowance tile is painted from the first moment, while the repositories are still loading.

### Corretto

- A new installation with the example catalogue saw almost no repository; the lite edition detected one repository out of 129 because its template filtered by ecosystem.
- **A damaged cache entry is only a miss**: it is thrown away and the endpoint is read again in full.
- "Red on main" and the compute minutes differed between the two editions.

### Sicurezza

- The lite edition never inherits the sentinel, the AI, the webhook, the outputs or the notifications, nor any secret, from the complete one; it writes neither `ci_red.json` nor a signing queue.

## [1.6.1]

> Questa versione è per ora disponibile solo in inglese; la traduzione arriverà in una versione successiva.

### Aggiunto

- **The lite edition**, a second and simpler product in the same package: `MONITOR_LITE_GITHUB_ACTIONS.bat` / `.sh` / `.command` or `--lite` / `MONITOR_MODE=lite`. What is running and what failed, failures and successes of 24 hours, red on main, the history and the basic charts; a short Settings page (account, repositories and ecosystems, refresh, language, theme); its own file `actions_monitor_lite.json`, its own state files with the suffix `_lite` and port 8766, so both can run side by side.
- **`act` command in the repository panel**: for each workflow of the repository, `act -W .github/workflows/FILE -j JOB` ready to copy. The monitor never runs it (running it exists only as a confirmed action of the AI assistant).
- **A container example** (`deploy/Dockerfile`) that the CI builds.
- Guide `LITE` in eight languages, a Lite-versus-Complete table in every README and new screenshots of both editions in light and dark.
- The roadmap lists what did not fit: local mirror of artifacts, FinOps of the minutes, self-hosted runner status and an OTLP export, and the notes of the terminal view (why it uses Rich).

### Sicurezza

- The lite edition has no sentinel: it is not imported and its endpoints answer 404.

## [1.6.0]

> Questa versione è per ora disponibile solo in inglese; la traduzione arriverà in una versione successiva.

### Aggiunto

- **Conditional reads (ETag)**: every read of the run lists sends `If-None-Match`; a `304 Not Modified` answer costs no quota. The header and `ghamon_etag_saved_total` count the reads saved; `cache.etag.*` in the Settings tab.
- **Resilience to network cuts**: when every read of a cycle fails with a connection problem the page keeps the last picture with an offline banner and resumes by itself; `offline` and `online` events (they can be notified) and `ghamon_offline`.
- **Analytics** (section A12 of the Sentinel tab, `/api/analytics`, `/metrics`, the Grafana JSON source): p50 / p95 of the duration of each workflow, of the queue time of its jobs and of each step; workflows that got slower than usual; **flaky** workflows (failed, then passed on the same commit, or needed another attempt), only a label that never changes what counts as red.
- **Incoming webhook in real time**: a signed `workflow_run` event updates the run list of its repository without reading GitHub, `workflow_job` events bring queue and step times; only short validated fields are kept (`/api/live-events`).
- **Workflow linter**: `lint_workflows.py` (actions not pinned by SHA, missing or broad permissions, secrets in clear text, injection, `pull_request_target` with the PR's code), rules switchable with their own severity, a line in the daily report and the section A13. A comment `# monitor-lint: ignore RULE reason` or the setting `lint.ignore` silences a finding.
- **Notifications** (off by default): Telegram, Discord, Slack, Matrix, MQTT and a local HTTP address, a limit per hour, a test button and a documented adapter contract (`monitor/docs/schemas/notification_event.schema.json`).
- **AI assistant**: new providers `anthropic` (Messages API, the model is yours to choose) and `copilot` (`gh copilot` with your own login, text only, no tools); new tasks (daily report, release notes, a question about a repository); settings for the kinds of event, the repositories, the language and the limits, a test button and the use of the day. A closed list of actions (`gh run rerun`, `gh issue close`, `act`), only PROPOSED by default.
- **The figures of the header are tiles** with an icon, a big figure and a small label, coloured by state, with a tooltip, a click that leads to the tab, counting figures and a skeleton that shows the last known values at once; the second line (repositories, hot, mode, reads saved, GitHub allowance with a bar and a live countdown, connection, last update and the loading progress) is made of tiles too.
- **Terminal view**: `tui.py` draws a live grid in the console (read-only, optional, needs the package `rich`; the monitor and its tests need no package).
- **For servers and bigger accounts**: `GET /api/health`, `GH_HOST` for GitHub Enterprise Server (every link of the page follows it), `discover_limit`, minimum permissions per feature, and a guide to run it as a service (systemd, launchd, a scheduled task, a container) and behind a reverse proxy.
- Published JSON schemas of `ci_red.json`, of the public export and of the notification event (`monitor/docs/schemas`), and a public roadmap (`docs/ROADMAP.md`).
- New guides in eight languages: notifications, the AI assistant, analytics, console tools and deployment; the webhook guide covers the real-time events. All screenshots were redone (light and dark, console tools included) with `tools/make_screenshots.py` and invented data.

### Modificato

- **Settings**: new sub-tabs for reads and cache, notifications, analytics, the linter and the terminal view; the AI and webhook sub-tabs have all their options.

### Corretto

- **The linter no longer cries wolf on placeholders**: a value that looks like a secret is classified (a known token format or a long high-entropy string is serious, a readable filler such as `placeholder` or `changeme` is only information, anything else a warning; references and empty values are no finding) and its value is never printed or stored.
- **A browser that closes or reloads its tab while the page is loading no longer prints a traceback** (`ConnectionAbortedError`, `ConnectionResetError`, `BrokenPipeError`): they are counted in `ghamon_client_disconnects_total`; a real error is still shown.

### Sicurezza

- The incoming webhook stays off by default, on `127.0.0.1`, with a mandatory HMAC.
- Notification secrets live only in environment variables; hosts are fixed; notifications never write to GitHub.
- AI actions: running one needs its own switch and a confirmation of the full command each time, only on targets the monitor already watches, with a limit per hour, a local log and a lock after two failures in a row.

## [1.5.2]

> Questa versione è per ora disponibile solo in inglese; la traduzione arriverà in una versione successiva.

### Aggiunto

- **The Settings tab is organised in sub-tabs**, ordered from the common to the advanced (This browser, General, Refresh and limits, Sentinel, Surface checks A10, Readiness A11, Folders and files, Outputs, External AI, Incoming webhook). Inside a sub-tab the settings sit in titled blocks whose first field is the main switch (the rest of the block dims while it is off). Every field shows its unit and range, a badge (needs a restart / applies now), a badge for the safety options that start in their conservative state, and one line of help. A search box filters all the sub-tabs, each sub-tab counts its unsaved changes, Save and Discard stay visible, the arrow keys, Home and End move between the tabs and the last sub-tab used is remembered by the browser.
- **Every setting of the configuration file is in the page now**: the A10 checks (a switch per check and its limits), the weights of the ecosystem health score, the sources of the pinned versions, the Actions-minutes ceilings, the required files, the audit file patterns, the hot period of the sentinel, the unknown-sample rule of A2, the candidate prefixes, the list of repositories and the switch of the incoming webhook.
- **Signing queue by trust**: each row says `verified`, `unknown` or `failed`; the Sentinel tab has a Signature filter with the count of each kind; `read_report.py --sign-trust` filters the console list and the export, and the exported rows carry `trust`.
- **Readiness chips in the header**: one coloured chip per ecosystem with its health score.
- **A minimal Grafana board** (`red_by_ecosystem.json`) and a test that checks every metric of both boards against what `/metrics` serves.
- New guide `WEBHOOK` (refresh-only mode) and a commented example of the pin sources, in eight languages.
- `tools/make_settings_doc.py` writes the settings table of the guides from the schema and the texts of the page, and the CI checks it.

### Modificato

- **The daily report groups the issue-closing suggestions** in one line per repository (the monitor still closes nothing).
- **The contract of the profile dashboard** is documented and checked by a test (`/api/outputs/dashboard.json` is exactly the document of `ci_red.json`; the public export never carries the signing side).

### Sicurezza

- The shared secret of the webhook is never shown in the page: it only says whether it is defined.

## [1.5.1]

> Questa versione è per ora disponibile solo in inglese; la traduzione arriverà in una versione successiva.

### Aggiunto

- **The settings page can set the external AI of the sentinel** (group "External AI for the sentinel"): `ai.provider` (`none` / `ollama` / `openai-compatible`), `ai.model`, `ai.ollama_url` (only this computer), `ai.base_url` (https only), `ai.api_key_env` and `ai.daily_limit`. Off by default; an outside service receives data of your repositories.
- **`migrate_state.py`**: brings the files written before 1.5.0 to the new names (events, report history, release candidates, batch records, the `report_history_days` setting). A dry run by default; `--apply` copies and keeps the old files, `--move` renames them; nothing that exists is overwritten. One-page guide in `docs/MIGRATING.md`, in eight languages.
- **`--init-catalog`** creates editable `ecosystems.json`, `targets.json` and `profiles.json` from the examples.
- A test makes sure no document sends the reader to a command that was renamed in 1.5.0 (only the tables of old and new names and the migration guides may name them).
- The version in every README.

### Modificato

- **First start without catalogue files of your own**: the console says the example files are in use.
- Python 3.11 or newer is the documented minimum (tested on 3.11 and 3.13 on Windows, Linux and macOS).

### Sicurezza

- Only the NAME of the environment variable that holds the AI key can be set: the key itself is never shown or saved.

## [1.5.0]

> Questa versione è per ora disponibile solo in inglese; la traduzione arriverà in una versione successiva.

**Update notice (read this first).** Several files and settings have English names now. Nothing is lost: the old names are still READ where a file written by an earlier version may exist, and the new names are the only ones written.

| Before 1.5.0 | From 1.5.0 |
|---|---|
| `leer_parte.py` | `read_report.py` |
| `eventos.py` | `events.py` |
| `parte_history.py` | `report_history.py` |
| `LOTE_GITHUB_ACTIONS.bat` / `.sh` / `.command` | `BATCH_GITHUB_ACTIONS.bat` / `.sh` / `.command` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` (copy or rename them to keep the history of events) |
| `PARTE_CENTINELA_DIA_<day>.txt/.json` (report history) | `SENTINEL_REPORT_DAY_<day>.txt/.json` (the old ones are still read) |
| `PARTE_CENTINELA_<time>.txt` (saved report) | `SENTINEL_REPORT_<time>.txt` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_<time>.json` | `<signed_dir>/batches/batch_<time>.json` (the old records are still read) |
| `parte_history_days` (setting) | `report_history_days` (the old name is still read) |
| `monitor_y_centinela.zip` and folder | `github_actions_monitor.zip` and folder; `LEEME_CORREO.txt` is `README_MAIL.txt` |
| A8 looked for `RECONCILIACION_TOTAL_AUDITORIAS_*.txt`, `MAPA_DE_RONDAS_*` | the names are `sentinel.audit_files` (neutral defaults `RECONCILIATION_TOTAL_*.txt`, `ROUNDS_MAP_2*.txt`, `ROUNDS_MAP_EXTRA_*.txt`); set your own there |
| `ci_red.json`, its schema and the `--export-status` files | unchanged (they are a contract) |

- **English by default.** The language of the system no longer decides: the tools start in English until you choose another one in the Settings tab, with `language` in `actions_monitor.json`, `MONITOR_LANG` or `--lang`.
- **A clean, neutral package.** `ecosystems.json`, `targets.json` and `profiles.json` are no longer part of the package: only the `*.example.json` files travel, and a missing default file falls back to its example. Your own files live anywhere and are named by `ecosystems_file`, `targets_file` and the new `profiles_file`; the folder of your local signing tools is the new `tools_dir`. The tests use their own fixtures (`tests/fixtures`).
- **Settings tab.** A new tab changes the values of `actions_monitor.json` from the page: a whitelist of keys with their type and range, one request refused as a whole when a value is invalid, a copy of the previous file in `config_backups/` before every save (the last ten are kept), an atomic write, only on 127.0.0.1 with the same Host and Origin checks as every other endpoint, JSON only. Tokens, secrets, signature keys and the command of the sentinel are not in the list: they are never shown and never written, and every other key of the file is kept as it was. Each setting says whether it needs a restart. The language selector, the theme and the dense view moved there.
- **Buttons and icons.** Buttons have relief, light up on hover and sink when pressed; the icon buttons are inline SVG with an accessible name and a tooltip in the 8 languages. Colours, type, cards, bars and the ring follow the status dashboard of the profile repository.
- **Life in the charts.** Bars grow in, what is red or running has a discreet pulse, the figures of the header count up, hovering a bar highlights it and gives its text as a tooltip, widths change smoothly; all of it stops with `prefers-reduced-motion`.
- **Outputs for other tools (off by default, 127.0.0.1 only, no new token).** `/metrics` in the Prometheus format (red workflows per ecosystem and repository, red streaks and hours, builds waiting for a signature, A10 paused, allowance left, incomplete snapshot...), `/api/outputs/grafana.json` for the Grafana JSON / Infinity source and `/api/outputs/dashboard.json` (the `ci_red.json` document) for the status dashboard. An importable Grafana dashboard is in `docs/grafana/` and the details in `docs/OUTPUTS.md`.
- **Report:** a line (code `tag_vs_manifest`) when a release tag is ahead of the version of the manifest; the unsigned figure is ordered by the longest wait and says how long it is; the repository panel suggests the `gh issue close` command (never run) for a failure issue whose workflow is green again; the `hil` batch profile is documented in `profiles.example.json`; tests for `finalize` and for `monitor_link`.
- **Docs:** `docs/SETTINGS.md`, `docs/OUTPUTS.md`, README and QUICKSTART in the 8 languages updated, screenshots made with invented repositories.

## [1.4.5]

> Questa versione è per ora disponibile solo in inglese; la traduzione arriverà in una versione successiva.

- **The report says when the snapshot is incomplete:** a line with the stable code `incomplete` (still loading, no local workspace, errors while reading) right after the headline, so nobody acts on a half-read list of red repositories or signing queue.
- **Signing summary:** one line with how many releases wait to be signed (verified / not checked / failed the check) and how many builds are build-only on purpose, so "not signed on purpose" is not confused with "signature missing" (code `sign_summary`).
- **A10 paused for the quota is said in the report** (code `a10_paused`) with the allowance left and needed, and the three knobs that control it.
- Texts in the 8 languages; tests for the three lines.

## [1.4.4]

> Questa versione è per ora disponibile solo in inglese; la traduzione arriverà in una versione successiva.

- **Author and licence are always visible:** the web panel has a footer with the author and the licence, `read_report.py --version` and the new `gha_dispatch_all.py --version` print them under the version, and the monitor prints the same line when it starts. The text is in the 8 languages (`ui.about`); the author and the licence come from `tool_version.py`.
- **Bridge to the dashboard written down:** `docs/CI_RED_BRIDGE.md` says what `ci_red.json` contains (schema 2, `complete`), how to export it and what a reader must check; the monitor still never pushes or commits.
- Tests for the author line in the 8 languages, the footer, both `--version` flags and the start-up line.

## [1.4.3]

> Questa versione è per ora disponibile solo in inglese; la traduzione arriverà in una versione successiva.

- **A workflow that only runs on pull requests no longer makes A2 inconclusive:** `pull_request` and `pull_request_target` join the events whose runs never sit on the default branch (like `workflow_dispatch`, `release` and `workflow_call`), so a workflow such as a contract integration check that only runs on pull requests is not asked for a last run on main. A workflow that also has `push` or `schedule` still counts. Tests for both cases.

## [1.4.2]

> Questa versione è per ora disponibile solo in inglese; la traduzione arriverà in una versione successiva.

- **A2 no longer counts a run in progress or a cancelled one as seen:** when it resolves a hidden workflow, the Sentinel now asks for the last completed runs of that workflow on the default branch (`gh run list -w <file> --branch <default> --status completed -L 10`, read only) and uses the first one with a real conclusion. A cancelled or skipped run (and anything without a conclusion) is ignored, so it can no longer hide an earlier red; a workflow with no completed run with a conclusion on the branch stays inconclusive on its own. Same quota gate, call limit and cache as before.

## [1.4.1]

> Questa versione è per ora disponibile solo in inglese; la traduzione arriverà in una versione successiva.

- **A2 resolves a hidden workflow instead of giving up on the whole repository:** when a repository has a full run sample and a workflow of its clone (one that can run on the default branch) is missing from it, the Sentinel asks GitHub for the last run of THAT workflow on the default branch (`gh run list -w <file> --branch <default> -L 1`, read only). A red answer counts as red in A2; a green one removes the workflow from the inconclusive list; a workflow with no run on the branch stays inconclusive on its own and the panel names it (`repo/file.yml (no run on the default branch)`) instead of only the repository. Without quota (same gate as A10: `min_rate_remaining` x `surface.min_rate_factor`, plus the hourly budget) the workflow stays inconclusive and the panel says why. New options `sentinel.a2_resolve_max_calls_per_tick` (4; 0 = never ask) and `sentinel.a2_resolve_ttl_seconds` (3600, how long an answer is kept; it is also saved in the cache file). The snapshot carries `a2.inconclusive_workflows` (labels) and `a2.inconclusive_details`; `a2.inconclusive` is still the list of repositories. 5 new texts in the 8 languages and a reworded `ui.a2_inconclusive`.

## [1.4.0]

> Questa versione è per ora disponibile solo in inglese; la traduzione arriverà in una versione successiva.

- **New layer A11 "Readiness" (read only, real data only):** a panel of the Sentinel tab, a traffic light in its header and two lines of the report. It is switched with `sentinel.readiness.enabled` and described in `readiness.py`.
  - **Release readiness:** one row per repository with at least `candidate_min_entries` entries in `[Unreleased]` (external ecosystems excluded): CI of the default branch (the single rule of A2) with the commit it ran on, whether the version the clone declares (`*.project.json`, else `pyproject.toml`, else the first CHANGELOG heading) is already above the last release, whether a build exists after that release, whether it is signed (the states of A5), and the next step (`fix the red CI`, `wait for run data`, `bump the version`, `build in Actions`, `sign`, `publish`, `cut and publish`). A green CI over a full run sample that may hide an older workflow says so.
  - **Ecosystem health:** per ecosystem, 100 minus weighted counts of red CI, stuck builds, secrets, serious alerts, other alerts, Dependabot PRs older than `stale_pr_days`, builds waiting for signing and repositories with hygiene problems (`sentinel.readiness.health.weights`); the parts that lower the score are listed. No score is shown (`?`) when fewer than `min_coverage` (0.5) of the repositories of the ecosystem have run data and alerts. The report warns when a score is under `warn_below` (70).
  - **Dependency pins:** repositories that pin an older version than the one of the repository that provides the contract or library. Where the pins live is data (`sentinel.readiness.pins.sources`): a JSON table of pins in the provider (`pin_table`) or lock files in the consumers (`lock_files`, the oldest one found counts). Plain file reads of the local clones, cached `pins.refresh_seconds`; an ecosystem without a configured source is listed as having none, and nothing is guessed. The shipped example has no source.
  - 60 new texts in the 8 languages; `tests/test_readiness.py` (rules, weights, coverage, pins on a temporary tree, the page and the 8 catalogues).
- **`docs/CI_RED_SCHEMA.md`:** says explicitly that the PC publishes neither `ci_red.json` nor `pending_sign` to any repository or dashboard (the signing side is local by decision); a public consumer recomputes the rule from the public runs or uses `read_report.py --export-status`.
- **Quota tuning from the log (`actions_monitor_log.txt`, 3 days, 889 samples):** the shared allowance was under the floor (`min_rate_remaining` 1500) in 11% of the samples since 5 November and under 3000 in 45%; the hourly burn was 3000-5000 calls in most hours and reached the limit in some. In the maintainer's `actions_monitor.json`: `refresh_seconds` 120 -> 180 (the real cycle was a median of 139 s) and `sentinel.surface.min_rate_factor` 2.0 -> 1.5 (the cold calls of A10 are about 260 a day, so they can run above 2250; with 3000 they waited almost half of the time). `max_repos_per_tick` (6) and the daily cold cycle stay: they cost less than 1% of the allowance. The shipped example keeps its neutral defaults.

## [1.3.3]

> Questa versione è per ora disponibile solo in inglese; la traduzione arriverà in una versione successiva.

- **A2 ignores workflows that never run on the default branch:** when deciding whether a full run sample hides a workflow, the files of the clone whose `on:` has no `push`, `pull_request` or `schedule` for the branch (only `workflow_dispatch`, `release`, tag-only `push` without `branches`, or `workflow_call`) are no longer expected in the sample. `on:` is read with the standard library only (string, list, map, and the YAML `true` key); if it cannot be parsed the workflow counts as before. The workflow scan carries the new field `main_triggered` (`true`/`false`/`null`).

## [1.3.2]

> Questa versione è per ora disponibile solo in inglese; la traduzione arriverà in una versione successiva.

- **A2 shows `unknown` instead of green when its sample is full and inconclusive:** a repository whose list of runs is as long as the sample asked for (`runs_per_repo` / `cold_runs_per_repo` of the monitor, which the check did not see before) and whose clone has a workflow file with no run in that sample (or that has no clone) is listed as inconclusive, and A2 is `unknown` unless something is red. New option `sentinel.a2_full_sample_unknown` (default `true`; `false` = only informative as before). The page lists the repositories.
- **`profiles.example.json`:** a neutral batch-profiles template that matches `targets.example.json` and `ecosystems.example.json`. A test (and the release gate) validates it against those catalogues, not the maintainer's, and checks that every profile selects at least one target.
- **Clean-install check in `make_release`:** before anything is left in the output folder the zip is extracted into a new, empty temporary directory and, from there with `python -I`, every member must be present, every module must compile, `read_report.py --version` must run and the whole suite must pass; any gap fails the release.
- **Wording:** README and QUICKSTART in the 8 languages now say that the package writes nothing to GitHub on its own and that only `dispatch --go`, `dispatch --real` and `finalize --execute` (which you run) do.
- **A10 quota:** the share of the sentinel's per-tick call budget that A10 may use is now `sentinel.surface.budget_share` (default `0.5`, as before but configurable); the page shows "A10 paused for quota" with the allowance left and the one needed (`min_rate_remaining` x `min_rate_factor`) while the cold calls wait.

## [1.3.1]

> Questa versione è per ora disponibile solo in inglese; la traduzione arriverà in una versione successiva.

- **A run built on another commit is never offered for signing:** when `dispatch` could only find a recent run of another commit (`sha_matched` false), `finalize` now lists it as not ready with the reason and gives no signing command; an old batch without the field behaves as before. Tests with two concurrent runs of different commits.
- **`/api/data` goes through the same Host/Origin guard as the other routes** of the local server (DNS rebinding).

## [1.3.0]

> Questa versione è per ora disponibile solo in inglese; la traduzione arriverà in una versione successiva.

Made to be shared: eight languages, authorship and licence in every file, no private data, and nothing tied to one GitHub account.

- **8 languages** (en, es, de, fr, it, ja, zh, pt = European Portuguese) for the page, the command line tools, the launchers, the events, the reports and the error
  messages. `i18n.py` + `locales/<lang>.json` (one flat catalogue per language, standard library only, `t("key", name=value)` with a fallback to English). The language
  is `language` in `actions_monitor.json` (default: the system language, English if unsupported), a selector in the header of the page (remembered by the browser),
  `MONITOR_LANG` / `JUANENRAC_LANG`, or `--lang CODE` in every tool (it wins over the rest). Technical names, commands, paths and the markers that scripts read
  (`SKIP`, `DISPATCHED`, `READY`, `FAILED`, `Summary:`, `BUILD ONLY`, `WOULD DISPATCH`...) are never translated. Events in `events_monitor.jsonl` now carry a stable
  `code` (and `args`) next to the text, so nobody has to parse a language.
- A test checks that the 8 catalogues have exactly the same keys, none empty, the same `{placeholders}`, that every key used by the code and the page exists, and that no
  visible string in the code bypasses `t()`.
- README and QUICKSTART in the 8 languages (`README_<lang>.txt`, `QUICKSTART_<lang>.txt`); `README.txt` is now a short language chooser with the quick start.
- **Authorship and licence**: every source file carries "Copyright (C) 2026 JuanenRac (Electro Hobby 3D)" and "GPL-3.0-or-later - see LICENSE"; JSON data files carry
  `_author` / `_license`; `LICENSE` (GPL-3.0 text), `NOTICE` and `AUTHORS` travel in the zip. `make_release.py` refuses to build when a file lacks them, when private data
  would travel, when the locales differ, or when a launcher loses its executable bit.
- **Shareable**: `github_owner` in the configuration (default: the account of `gh`) replaces the constant that was spread over three modules; the ecosystem prefixes and the
  signing tools are data (`ecosystems.json`, neutral `ecosystems.example.json`; `"*"` = every repository; `"external": true` = only reported) and so are the targets (`targets.json`
  is the maintainer's real catalogue, `targets.example.json` the neutral one; `targets_file` / `ecosystems_file` choose them; keys that start with `_` are metadata).
  The example configuration is neutral. Nothing of this adds a call to the hot cycle.
- **The workspace is optional**: without local clones the monitor starts in a reduced mode (only what the GitHub API gives: no local signing queue, no audit report, no
  CHANGELOG scan) and says so on the page, in the report and at start, instead of stopping. `MONITOR_ROOT` / `MONITOR_AUDIT_DIR` / `MONITOR_SIGNED_DIR` and `signed_dir`
  were added next to the old names. The roadmap layer (A9) is optional too.
- Launchers: menus and messages come from `launcher_msg.py` (your language); comments in English; header on every file.
- Fix: `workspace_root()` no longer ends the monitor when the sentinel starts without a workspace.

## [1.2.0]

> Questa versione è per ora disponibile solo in inglese; la traduzione arriverà in una versione successiva.

What was missing and what else can be done on GitHub, all of it read only and local.

**Part A - what was missing**
- `ci_red.json` schema 2 is now a documented contract: `docs/CI_RED_SCHEMA.md` (shape, the one rule of "red", what is for the owner only). Nothing is
  published from the PC. Optional, explicit exports (never a commit or a push): `read_report.py --export-status DIR` writes ONLY the red list
  (`ci_status_public.json/.md`); `read_report.py --export-sign-queue FILE` (.json/.csv) writes the global signing queue with the local commands.
- Attestation: the signing queue shows whether the build has an attestation (existence by digest of the signed files, one lookup per entry, no signature
  check; switch `sentinel.surface.checks.attestation`). A missing one is a line in the report.
- More verified formats: HYDRA `hydra-sign` (`FILE.sig` = base64 Ed25519 over the bytes of the file, the pinned release key, read in blocks) is checked
  definitively; URTC `.imgsig` has its strict format checked (152 hex digits + LF; malformed = not valid) and stays "unknown" when well formed (the signed
  message also needs the build header, which the signed folder does not carry); ARMOR APKs are signed inside the APK by apksigner and stay "unknown".
- `HYDRA-UMC-OS` is labelled on purpose in `targets.json` (`"build_only": true` + `reason`): `plan` lists it under BUILD ONLY and it is no longer an orphan.
  The signing tools were not touched (its workflow takes other inputs and a different signature scheme).
- Fix: `ci_red.target_path` refused every Windows path written with backslashes (`C:\...`); only forward slashes were accepted.

**Part B - the A10 layer "Actions & releases surface"** (`surface.py`, new section of the tab, a switch and a threshold per check under `sentinel.surface`)
- Actions: workflows disabled by hand, schedules with no run in N days (only when the sample of runs covers the window), `uses:` not pinned by SHA
  (reusable workflows flagged apart), `permissions: write-all`, `pull_request_target` with a checkout of the PR, stuck concurrency queues, failures on only one
  OS of a matrix, artifact cost and retention, required status checks that are red or missing (GraphQL), `dispatch --profile release|nightly|hil` with a canary
  (the first target alone, the rest only if it is green) and a quota gate (`--min-rate`, fails closed). Profiles live in `profiles.json`.
- Releases: expected assets per kind of target (alert when a release was published incomplete), tag vs manifest vs CHANGELOG, GitHub Packages, forgotten drafts
  and pre-releases, `release_notes.py` (a DRAFT of notes from the commits since the last tag; it publishes nothing).
- Security: critical/high alerts by age with a ranking of repositories, coverage (a stack without CodeQL/Dependabot), secret scanning open vs resolved,
  Dependabot by priority (runtime major first, CI-only last).
- Issues and PRs: suggestion of `gh issue close` for build issues whose CI is green again (an event with the text; nothing is ever closed), overdue milestones,
  old human PRs, PRs that touch workflows or CODEOWNERS, the merge queue (approved with green checks). Stale board cards: PENDING (needs per-item reads and a threshold).
- Manifest vs evidence (maturity), 8-language README parity failures, Actions minutes per ecosystem in the header, the report and A7.
- `finalize --execute` now tells the running monitor (127.0.0.1) to refresh just the signed repositories and rewrite `ci_red.json` at once (`monitor_link.py`).
- Optional signed webhook receiver (`webhook.enabled`, off by default, 127.0.0.1 only, HMAC with a shared secret from the config, never a GitHub token).
- Cost: nothing in the hot cycle. Cold, spread over ticks and inside the hourly budget: 2 REST calls per repository per day, one GraphQL query per 15
  repositories per day, 3 for Packages, plus the jobs of red runs and the attestation lookups of the signing queue, and only while the allowance is above
  twice `min_rate_remaining`. The hot GraphQL pass asks for 3 more fields per node (alert dates, review decision, checks state): no extra call.
- The gate also compares `sentinel.surface` of the example file with the defaults and validates `profiles.json`.

## [1.1.1]

> Questa versione è per ora disponibile solo in inglese; la traduzione arriverà in una versione successiva.

- **Cross-platform:** the monitor and the batch tools work on Windows, macOS and Linux. Launchers `MONITOR_GITHUB_ACTIONS.sh`/`.command` and `BATCH_GITHUB_ACTIONS.sh`/`.command` (the zip keeps the executable permission and make_release rejects Windows line endings in them).
- New `platform_compat.py`: the command that starts a child tool (`py -3` on Windows, the current interpreter elsewhere), the text of the commands that `finalize` shows (cmd/PowerShell or POSIX quoting), UTF-8 console and a notice with the way to install `gh` on each system.
- New tests of the cross-platform part (Windows and POSIX simulated from any system).

## [1.1.0]

> Questa versione è per ora disponibile solo in inglese; la traduzione arriverà in una versione successiva.

Signature trust, a stable bridge to the dashboard, orphans and conventions in the batch tools, and a more useful page.

- Signature trust: `sigverify.py` (standard library, read only, no network) checks the signed folder `_firmados/<REPO>/release-<version>/` against the PUBLIC
  key each ecosystem pins (URTC `release_sign.py`, ARMOR helper `PACKAGE_PUBLIC_KEY`, HYDRA updater `RELEASES_PUBLIC_KEY`, or `sentinel.signature_pubkeys`).
  Every state now carries `signature_kind` (none | dev | release) and `signature_verified` (true | false | "unknown"); only a release signature that verifies
  (`trusted`) lowers the pending-signature alert, besides "published". A signature that does not verify keeps the alert and says so in the report.
  `sentinel.require_verified_signature` (default true; false = the 1.0.0 rule). Formats this module cannot check (.sig2, .hdr2, .imgsig, APK, hydra-sign) are
  "unknown", never "false". The build attestation still needs the network and stays with the signing tools.
- `ci_red.json` schema 2: per repository a `pending_sign` list (workflow, hours, state, signature_kind, signature_verified, last_build_at, url) next to the red
  workflows, plus `schema`, `pending_sign_repos` and the threshold; the format is documented in `ci_red.py` and is only ever extended.
- One definition of "last run on main" (`signstate.completed_runs`) shared by the red check, the green-without-release check and the target states.
- `ci_red.target_path` refuses D: paths, WSL/Git Bash forms of D: and drive/UNC paths that the running system cannot use; the tests simulate both systems
  and the whole suite now passes on Linux.
- `gha_dispatch_all.py plan` always ends with the section "Signature orphans" (green CI + known `*-build.yml` + no target); coverage is by repository AND workflow.
- Convention for targets (ecosystem prefix -> default signing tool, workflow in the known list); `targets.json` only holds the overrides and always wins.
  `hygiene --write-candidates` writes the proposed entries to `targets.candidates.json` (never applied by itself, never packaged).
- Page: clickable header counters "red on main" and "unsigned" (filter the repositories; the second one also focuses the signing queue), the signing queue
  with its commands and a copy button, repository panel with build / signed / published, signature kind and verification, and the suggested command;
  a header badge when a minutes budget reaches 80 % (red when exceeded); "yesterday vs today" also compares budget warnings and the lines of the report.

Not done: reading the build attestation / SBOM (network); `HYDRA-UMC-OS` has a build workflow but its signing tool does not support it yet (listed as an orphan).

## [1.0.0]

> Questa versione è per ora disponibile solo in inglese; la traduzione arriverà in una versione successiva.

First numbered version. What the package does:

- Monitor of GitHub Actions for the four ecosystems (local web page, run cache, stuck builds, build-failed/build-stuck issues).
- Sentinel layer A (read only, no AI needed): A1 stuck builds, A2 red CI (one criterion: last completed run of each workflow on the default
  branch), A3 CodeQL/Dependabot/secret alerts, A4 Dependabot pull requests, A5 releases (candidates, green builds without a release,
  pending signature), A6 hygiene, A7 consumption (minutes and API allowance), A8 audits and rounds, A9 roadmap boards.
- Explicit state of each build target: built_on_gha -> signed_local (none | dev | release) -> published, with `last_build_at`,
  `last_signed_at`, `signature_kind` and the real hours waiting; local batch and signed-folder records lower the pending-signature
  alert without waiting for GitHub.
- Signing queue of the day (`a5.sign_queue`): most urgent first, with the exact finalize command of each target.
- Budget of Actions minutes per ecosystem (`sentinel.minutes_budget`, empty by default): warning at 80 % in the report and as an event.
- Event feed (`events_monitor.jsonl`) and `ci_red.json` (repository -> red workflows + hours pending signature), written atomically.
- Batch tools: `gha_dispatch_all.py plan|dispatch|status|finalize|hygiene` with `--only` or `--ecosystem`, `plan --json`,
  `finalize --json`, one retry of a failed dispatch at the end of the batch, targets as data in `targets.json`.
- `read_report.py`: the report as plain text from the running monitor, without spending API quota.
- `make_release.py`: quality gate (unit tests, clean zip, complete example configuration, version/changelog agreement) and SHA256SUMS.

Not done in this version: verifying release signatures against the public key and the build attestation from the sentinel
(different signature formats per ecosystem; the attestation needs the network; the signing tools verify both before publishing).
