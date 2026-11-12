<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Registro delle modifiche

Versione dello strumento stesso (monitor + sentinella + strumenti batch), con il proprio semver. La fonte è il CHANGELOG.md in inglese; questo file ha le stesse versioni e sezioni.

## [Unreleased]

### Aggiunto

- **Una verifica che nessun testo esca dal suo riquadro** (`tools/check_overflow.py` e un test che si salta senza browser): la pagina viene aperta in un browser senza finestra nelle otto lingue, larga e stretta, percorre ogni scheda e finestra e fallisce se un testo è più largo di un riquadro con bordo o sfondo o esce dalla finestra.
- **`display.blink_red_tiles`** (attivo per impostazione predefinita, nella scheda Impostazioni, nelle otto lingue): i riquadri in alto e gli elementi della barra in basso che diventano rossi lampeggiano dolcemente finché la causa non è risolta; con il movimento ridotto del sistema mostrano invece un bordo rosso fisso e più spesso.
- **Un controllo del doctor per il fuso orario**: un fuso che né il sistema né la tabella interna conoscono viene segnalato e gli orari sono mostrati in UTC (prima ricadevano sul fuso del computer senza dirlo).
- **La scheda Cronologia dice "n di N"** quando l'elenco è più corto di ciò che l'intestazione ha contato (il monitor conserva le 600 esecuzioni più recenti; i dati portano `runs_total`).
- **I pannelli della scheda Sentinella come dati**: `GET /api/sentinel/panels` (sola lettura), lo strumento MCP `sentinel_panels` e una sezione "Sentinel panels" nel riepilogo danno, per A1..A13 e il secondo sentinella, il livello, una riga e le righe su cui agire con repository e link; le righe di un pannello su "agire" o "tenere d'occhio" diventano anche avvisi del feed (classi `real` e `watch`), quindi flusso, hook, `alerts_open` e il contatore degli avvisi reali le includono.
- **Un "bing bing" quando qualcosa di nuovo fallisce** (le impostazioni `sound`, nelle otto lingue): la pagina riproduce due brevi toni (Web Audio) solo per un NUOVO rosso o una connessione persa, mai a un aggiornamento né per ciò che c'era già, con pausa minima, volume e un chip "Suono" nella barra in basso che sblocca l'audio del browser, lo silenzia ed è ricordato; un pulsante "Prova il suono" in Questo browser; e `sound.server_beep` (disattivato per impostazione predefinita, solo locale) per quando la pagina è chiusa (beep di Windows, `afplay` di macOS, `canberra-gtk-play` su Linux o la campanella del terminale, senza shell e senza rete).
- **Tutto ciò che dice il monitor, come segnali per uno strumento di IA**: un inventario unico (`signals.py`) con livello (agire / tenere d'occhio / info), riepilogo e righe con repository, link, età e passo successivo per la scheda Ora e i suoi riquadri, gli avvisi, i repository, i pannelli del sentinella A1..A13 e il secondo sentinella, la quota, la connessione e la salute del monitor; `GET /api/ai/state` (versionato, sola lettura), un riepilogo con "Cosa fare ora", "In sospeso" e "Salute del monitor" e il contatore dei segnali su cui agire, e gli strumenti MCP `monitor_state`, `signals`, `diagnose` e `act`. Un test percorre la pagina e fallisce per un riquadro o una scheda che non è nell'inventario né segnato come decorativo.
- **La connessione con uno strumento di IA è la stessa nell'edizione lite e in quella completa**: stessi canali (riepilogo, feed, `/api/ai/state`, flusso, strumenti MCP, `ai-hook`), stesso codice e stesse impostazioni in entrambe; lo stato dice `edition` ed elenca i pannelli che non esistono in lite, così un pannello assente non viene scambiato per dati mancanti.
- **Una modalità risparmio (risparmio estremo della quota)**: accanto a Normale, Veloce e Turbo, `low` legge solo i repository caldi ogni 4 minuti e il resto ogni 30, con elenchi di esecuzioni brevi, e dice nella barra e nel riepilogo che le sue cifre possono essere vecchie e di quanto; `modes.auto_low` (attivo per impostazione predefinita) entra da solo sotto 1000 chiamate rimaste e torna sopra 2500 o al rinnovo della quota (due numeri diversi, senza oscillare); i valori sono in `modes.low` del file.
- **Il pannello centrale come base che non spende quota** (`central.source`: disattivato per impostazione predefinita, `git` o `http`; `central.max_age_minutes`, nelle otto lingue): il monitor legge `data/sentinel.json` del repository di profilo (aggiornato ogni mezz'ora da un workflow con il proprio token) con un semplice git fetch o il file grezzo, mostra "fonte: pannello centrale, N min fa" nello stato e nel riepilogo, ignora un file in ritardo (oltre due ore) e lo dice, e in modalità risparmio interroga l'API dal vivo solo per i repository che il pannello dice rossi, quelli con un'esecuzione in corso e ciò che il pannello non contiene.

### Modificato

- **La barra in basso è ridisegnata**: ogni elemento è una pastiglia con il suo bordo, la connessione e la quota prendono il colore del loro stato, l'orologio è un riquadro con grandi cifre in grassetto tabulari, la data sopra e il fuso in piccolo, e la barra mantiene il suo ordine nelle finestre strette.
- **Ogni riquadro lascia spezzare il testo invece di farlo uscire** (riquadri, pastiglie, etichette, celle, titoli, pulsanti delle finestre): l'ora dell'ultima lettura porta il fuso a parte in piccolo, le righe degli avvisi passano su due colonne nelle finestre strette e le griglie dei riquadri possono restringersi sotto il loro contenuto.

### Corretto

- **Un solo numero per i guasti aperti**: il riquadro "rossi su main", l'elenco degli avvisi, la barra in basso e il riepilogo contano la stessa cosa, un workflow la cui ultima esecuzione sul ramo predefinito è fallita (un guasto su un ramo di lavoro non appare più come avviso aperto), e la barra non dice mai "nessun avviso" finché ci sono avvisi aperti.
- **L'avvio del monitor nomina la versione una sola volta**: la riga "GitHub Actions v..." che ripeteva l'intestazione sparisce; autore e licenza restano in una riga.
- **File di stato danneggiati** (stato di collaborazione, cache e cronologia del sentinella di forma errata) vengono ignorati voce per voce invece di raggiungere il codice che li legge.
- **Una quota GitHub esaurita è UN avviso, non un errore per repository**: le letture dei repository si fermano fino al rinnovo (e riprendono da sole), l'elenco degli avvisi dice "Quota di GitHub esaurita fino alle HH:MM ... (N repository non aggiornati)", la barra in basso anche, nulla diventa rosso e nulla arriva al feed, al suono o al riepilogo come guasto; i testi di errore di `gh` sono tagliati a una riga (senza paragrafo legale né id della richiesta) e molti repository con lo stesso tipo di errore sono raggruppati in una riga.

## [1.7.6]

Il collegamento tra il monitor e uno strumento di IA: il feed coincide sempre con la pagina, ogni avviso dice perché è rosso, un flusso e tre strumenti MCP spingono le novità, un comando installa lo script di collegamento, la barra mostra se una IA è collegata e ogni file di stato è privato del suo proprietario.

### Aggiunto

- **Il riepilogo e il feed seguono ogni aggiornamento della scheda Avvisi** (e ogni lettura del feed e ogni ciclo): prima avevano un ciclo di ritardo, così una IA poteva leggere 10 avvisi mentre la pagina ne mostrava 6. `ALERTS_BRIEF.md` ora contiene `Updated:` nel tuo fuso orario e una riga per macchine `updated_epoch:`, e `GET /api/ai/brief?fmt=json` aggiunge `updated`, `updated_local` e `age_seconds`. Un ciclo che non ha ancora caricato i dati non risolve mai avvisi.
- **`ai_alerts.diagnose`** (disattivato per impostazione predefinita, nella scheda Impostazioni, in otto lingue): ogni avviso di una nuova esecuzione rossa porta `diagnosis`, il primo passo che fallisce e una decina di righe utili del log, lette con chiamate di sola lettura, ripulite dai segreti e limitate in dimensione e in esecuzioni per ciclo; un errore di infrastruttura nel log rende l'avviso transitorio.
- **`ai_alerts.cascade`**: gli avvisi rossi perché un altro repository è rosso (nominato nel log o nella regola `ai_alerts.cascade.map`) vengono elencati sotto di esso nel riepilogo e portano `origin`.
- **`GET /api/ai/stream`** (`ai_alerts.stream`, disattivato per impostazione predefinita): eventi del server, sola lettura, con il token di accesso in modalità di rete, limitato in ascoltatori e tempo, riprendibile con `Last-Event-ID`; l'edizione lite non lo ha.
- **Strumenti MCP `alerts_open`, `alert_diagnose` e `alert_ack`** (l'ultimo solo con `--allow-ack`) e un avviso alla IA quando si collega, nelle `instructions` e con una notifica, che dice quanti avvisi reali sono aperti.
- **`monitor_cli.py ai-hook install|status|uninstall [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]`** e lo script di collegamento `ai_hook.py` (solo libreria standard): aggiunge il riepilogo alla sessione di IA e, solo con `ai_alerts.client_hook.block_on_stop` (disattivato per impostazione predefinita), chiede alla IA di esaminare gli avvisi reali aperti prima di chiudere un turno. Le impostazioni dello strumento vengono unite, mai sostituite, si conserva una copia del file, un file che non è JSON valido viene rifiutato senza toccarlo e tutto ciò che si scrive è ASCII puro. I valori stanno in `ai_alerts.client_hook` (scheda Impostazioni, otto lingue).
- **Un battito della IA** (`ai_alerts.heartbeat`): il flusso, il server MCP, lo script di collegamento e gli endpoint annotano l'ultima lettura in un piccolo file locale, e la barra in basso mostra se una IA è collegata e da quanto ha letto.
- **`monitor_cli.py --token-file FILE`** e un avviso su stderr quando si usa `--token` (compare nell'elenco dei processi) o quando il file del token è leggibile da altri utenti.
- Test per ogni modifica, in una cartella temporanea e offline, compreso il modo di ogni file di stato con un `umask` permissivo.

### Modificato

- **Ogni file di stato del monitor viene creato con modo 0600** (le cartelle create con 0700) tramite un solo helper, `private_io.py`: silenziamenti, eventi, feed, riepilogo, cache, impostazioni e i file scritti dall'installatore dello script di collegamento. Su Windows il programma non può imporre i modi (le cartelle ereditano i permessi della cartella superiore).
- **All'avvio della modalità di rete** con `listen.query_access` ancora attivo ora si stampano i primi passi (disattivarlo; usare HTTPS o una VPN), e l'aiuto di `listen.network` e la guida avanzata dicono lo stesso in otto lingue.
- **Il feed degli avvisi per IA è disattivato per impostazione predefinita** (`ai_alerts.enabled`, era attivo): una nuova installazione non scrive alcun feed finché non lo attivi. Un'installazione che ha già un feed nella sua cartella lo mantiene attivo, e la console lo dice una volta all'avvio, così chi lo usava di proposito non viene spento.


### Sicurezza

- **Le notifiche in uscita ignorano le variabili di proxy dell'ambiente** (`http_proxy`, `https_proxy`): un proxy faceva giudicare al controllo l'indirizzo del proxy e non quello della destinazione, e un proxy che rispondeva con un reindirizzamento poteva mandare la richiesta alla rete locale (compreso l'indirizzo dei metadati di un cloud). La nuova impostazione `network.use_proxy` (disattivata per impostazione predefinita, nella scheda Impostazioni, in otto lingue) li usa di nuovo, e allora la destinazione e il bersaglio di ogni reindirizzamento vengono controllati prima che il proxy riceva qualcosa. Provato con un proxy che reindirizza all'indirizzo dei metadati.
- **`/api/ai/actions/confirm`, `/api/ai/actions/unlock`, `/api/ai/test` e `/api/notify/test` valgono solo per questo computer** in modalità di rete (403 `local_only`), come gli altri endpoint che agiscono.
- **Un piano di `act` è legato al suo workflow**: il piano conserva il percorso risolto e lo SHA-256 del file, e li ricontrolla subito prima di avviare `act`; un workflow modificato, sostituito o rimosso dopo la conferma non viene eseguito (`workflow_changed`, con testo in otto lingue).
- **Il portachiavi di macOS non riceve più il token su una riga di comando**: `security -i` legge il comando dall'input standard, quindi il token non compare nell'elenco dei processi.
- **Tutto ciò che stampa `gh` viene ripulito prima di essere conservato**: il registro delle azioni per IA e il dettaglio di un'azione rifiutata passano dal pulitore, che ora copre anche i vecchi token di 40 caratteri esadecimali e il token conservato dal monitor.
- **L'elenco degli indirizzi rifiutati è limitato** (`localguard`): il blocco successivo elimina tutti i blocchi scaduti, non solo quello dell'indirizzo che chiede, e non conserva mai più di 2000 voci.
- **Un silenziamento che non si è potuto salvare non viene dato per salvato**: `POST /api/alerts/mute` e `unmute` rispondono `ok: false` quando il file non si è potuto scrivere.
- **La riga di comando non mostra mai un traceback per una risposta di forma sbagliata**: una lista, `null` o un numero al posto di un oggetto, o un campo del tipo sbagliato, termina con il codice di uscita 4 e un messaggio.
- **Un client della rete può scrivere solo un breve elenco di impostazioni** (la lingua, il fuso orario e il ritmo della pagina): ogni canale di notifiche, ogni percorso, ogni nome di variabile d'ambiente e i file di cui si fida il flusso di firma e invio si cambiano dal computer del monitor. Un'impostazione aggiunta dopo è solo locale finché non viene inclusa di proposito.
- **Dietro un proxy inverso sulla stessa macchina**, una richiesta con intestazione di inoltro (`Forwarded`, `X-Forwarded-*`, `X-Real-IP`) o con il nome pubblico del proxy non è mai «questo computer», e il token di accesso viene giudicato prima del blocco per indirizzo, così un'ondata di token sbagliati non lascia fuori il proprietario.
- **Le chiamate a questo computer non passano mai da un proxy dell'ambiente** (`netguard.local_open`, usato dalla riga di comando, dal server MCP, dalle viste da terminale e dagli hook), e la riga di comando non segue i reindirizzamenti, quindi il token di accesso non viene inoltrato a un altro indirizzo.
- **Ogni risposta vieta di essere inserita in un frame** (`X-Frame-Options: DENY`, `frame-ancestors 'none'`, `nosniff`), la pagina controlla l'`Host` come l'API, e ogni risposta autenticata dall'indirizzo obsoleto `?access=` porta l'intestazione `Deprecation`.
- **Invio e firma**: le esecuzioni che esistono prima di un invio vengono annotate e solo una nuova può essere presa per nostra (senza orologi); due nuove candidate richiedono revisione; l'input `ref` è il commit controllato; un workflow obbligatorio si confronta con il suo FILE, mai con un nome visibile; il nome di un lotto è in UTC.
- **Il pulitore del feed per IA copre più formati**: nomi che finiscono in `PASSWORD`, `PWD`, `SECRET` o `TOKEN`, credenziali dentro un indirizzo, webhook di Slack e Discord, token di bot di Telegram, token `glpat-`, `npm_` e `pypi-`, chiavi private, lunghe stringhe esadecimali e il token di accesso di questo monitor. `get_run_failure` del server MCP legge solo repository che il monitor osserva (o `ai.allowed_repos`).
- **I file modificati a mano** (silenziamenti, stato degli aggiornamenti) perdono solo le voci errate, e uno stato degli aggiornamenti errato non ferma più l'avvio.
- **Fusi orari**: Il Cairo segue l'ora legale dal 2023 nella tabella interna, e un nome di fuso sconosciuto al sistema viene rifiutato nella scheda Impostazioni. L'edizione completa riporta nell'intestazione i workflow rossi come la lite, e `monitor_cli.py status` senza dati termina con il codice 4 come `health`.

## [1.7.5]

La riga di comando prende il token di accesso con il suo nome, la modalità di rete è più sicura per impostazione predefinita (l'indirizzo del computer è nascosto alla rete, il vecchio indirizzo ?access= si può disattivare, le destinazioni di notifica della rete locale sono rifiutate, avviso sul semplice HTTP), gli orari per le persone usano il tuo fuso orario, un avviso si può silenziare finché l'elemento non cambia, e sono corretti i conteggi e i controlli che davano risposte sbagliate.

### Aggiunto

- **`monitor_cli.py --token TOKEN`**, e il token di accesso della riga di comando ha ora il nome che legge il monitor stesso: `MONITOR_ACCESS_TOKEN`, poi il suo alias `MONITOR_TOKEN`, poi `--token` (un'opzione compare nell'elenco dei processi, quindi è l'ultima risorsa). Il messaggio di un client rifiutato nomina la variabile. Provato contro un monitor finto che esige l'intestazione.
- **Un avviso su stderr** quando `monitor_cli.py` punta a `http` non cifrato su un altro computer (il token e le risposte viaggerebbero in chiaro); la risposta e `--json` non vengono toccati.
- **`listen.query_access`** (attivo di default, nella scheda Impostazioni, in otto lingue): se lo disattivi l'indirizzo obsoleto `?access=` viene rifiutato e la sessione si apre solo con `POST /api/access` (il token nel corpo) o l'intestazione. L'indirizzo che funziona risponde con un'intestazione `Deprecation` e la console dice che è obsoleto.
- **Un silenziamento «finché l'elemento non cambia»**: `POST /api/alerts/mute` accetta `until_change` per un avviso; il silenziamento conserva l'`updated_at` che aveva la issue o la pull request e termina subito quando cambia (un nuovo commento, un push), oppure alla fine delle ore, quel che viene prima. Gli avvisi di Collab portano ora `details.updated`.
- **Un controllo del doctor per un token condiviso da più account** (`credential`): confronta solo una breve impronta dei token con cui gli account leggerebbero GitHub (il token conservato dal monitor, o `GH_TOKEN` / `GITHUB_TOKEN` dell'ambiente) ed elenca gli account che ne condividono uno; il token non viene mai mostrato.
- Test per ogni modifica, compreso un test di igiene del webhook: un payload con un segreto, un'e-mail, un messaggio di commit e un token non arriva né all'elenco dal vivo, né al feed, né a una notifica, e l'elenco dal vivo è ora filtrato da una lista di campi consentiti.

- **`notify.allow_private_targets`** (spento per impostazione predefinita, nella scheda Impostazioni, nelle otto lingue): una destinazione di notifica che è, o si risolve in, un indirizzo di loopback, privato (10.x, 172.16-31.x, 192.168.x, fc00::/7), link-local (169.254.x, con l'indirizzo dei metadati cloud, fe80::/10), condiviso (100.64.0.0/10) o riservato viene rifiutata. Il nome viene risolto una volta e il socket si apre verso l'indirizzo verificato (un nome che cambia risposta non passa), e ogni reindirizzamento segue la stessa regola. I canali `mqtt` e `http_local` restano solo locali per definizione. Provato con un server e un resolver finti.
- **Un avviso sull'HTTP semplice in modalità rete**: l'aiuto dell'interruttore `listen.network` ora dice, nelle otto lingue, che senza HTTPS token e dati viaggiano non cifrati; la console avvisa già all'avvio in rete senza certificato.
- **Orari per le persone nel proprio fuso orario**: la riga `Last read` e i silenziamenti di `monitor_cli.py`, il registro `actions_monitor_log.txt`, i rapporti della sentinella, il riepilogo per le IA e le notifiche mostravano UTC (`...Z`) senza dirlo, a una o due ore dall'orologio a muro. Ora si leggono come `11:43:07 CET (10:43:07 UTC)`: il fuso del computer, il suo nome e accanto l'ora UTC. L'ora legale è seguita (provata attorno ai due cambi dell'anno e per Madrid, UTC, Tokyo e New York).
- **`display.timezone`** (`local` di default, nella scheda Impostazioni e nelle otto lingue): `utc` o un nome IANA come `Europe/Madrid` mostra i testi e gli orologi della pagina in quel fuso; la variabile d'ambiente `MONITOR_TIMEZONE` prevale sul file. Senza un database dei fusi nel sistema (Windows senza `tzdata`) si usa una tabella incorporata dei fusi più comuni.
- **I campi per le macchine restano in UTC e hanno un gemello leggibile**: `generated_local` in `ci_red.json` e nell'esportazione locale della coda, `updated_local` in `monitor_cli.py status --json` e nei dati della pagina, e una riga `Updated:` in `ALERTS_BRIEF.md`. Gli orologi della pagina e la barra in basso mostrano il fuso (`CET`, `JST`...).
- **Un pulsante «Fino al cambiamento» nella scheda Avvisi**: silenzia un avviso di una issue o pull request finché il suo `updated_at` non cambia (nuovo commento, push), o al massimo per le ore abituali; l'avviso silenziato indica «silenziato fino al cambiamento». Testi nelle otto lingue e un test di regressione.

### Modificato

- **L'API chiama l'edizione `complete`** (diceva `full`) in `/api/about`, `/api/statusbar`, `--doctor --json` e nella riga di comando; `full` resta riservato a ciò che la sentinella può eseguire. La pagina e la riga di comando capiscono ancora entrambe le parole.
- **I silenziamenti si fanno solo dal computer del monitor** (anche in modalità di rete, fino alle edizioni con utenti): la guida di Collab lo dice in otto lingue e un test mantiene la route dietro questa regola.
- **I workflow di questo repository usano azioni fissate a un commit completo**, con la versione in un commento, e un test lo mantiene.

### Corretto

- **Issue che si potrebbero chiudere** (controllo di superficie): un'esecuzione verde di un altro workflow non propone più di chiudere una issue; la issue deve nominare il workflow (con il suo nome o con il suo file, «Firmware build failed» per `firmware-build.yml`) e quello stesso workflow deve avere un'esecuzione verde successiva sul ramo predefinito. Una issue che non nomina alcun workflow non propone nulla.
- **Tag rispetto al manifesto** (controllo di superficie): quando il tag dell'ultima release precede il manifesto letto dal clone, il manifesto del ramo predefinito su GitHub viene letto una volta per quella release (il clone può essere indietro dopo una release) e l'avviso sparisce se aveva già quella versione; i tag che non sono versioni (`meshes-1`) vengono ignorati.
- **Passo successivo di un candidato alla release**: un repository la cui release richiede una build firmata dice ora «compilare in Actions e firmare», distinto da «alzare la versione», «firmare» e «pubblicare»; i repository di ecosistemi gestiti altrove restano fuori dai candidati (testato).
- **I run in corso e in coda si contano una sola volta**: le tessere «in corso» e «in coda», l'elenco «Adesso», la barra di stato (nuovo elemento «N in corso · M in coda», anche in `/api/statusbar` come `runs`) e `monitor_cli status` danno gli stessi numeri per gli stessi dati, in entrambe le edizioni. Quando i filtri della pagina (ecosistema, stato, ricerca, un elenco da una tessera) nascondono dei run, le tessere mostrano «3 di 13» e l'elenco inizia con «Mostro 3 di 14 (filtri attivi)»: un filtro salvato nel browser non sembra più un'incoerenza. L'elenco dei run attivi scarta anche un run letto due volte. Testi nelle otto lingue e test per entrambe le edizioni.

### Sicurezza

- **`/api/statusbar` non consegna più l'indirizzo del computer nella rete locale (`lan_address`) a un client della rete** in modalità di rete; la barra si disegna senza.
- L'indirizzo obsoleto `?access=` viene considerato solo con un `GET`.

## [1.7.4]

Una barra a piè di pagina per gli avvisi e i dati del monitor, un pulsante a schermo intero, tabelle che si ordinano per una o più colonne con le colonne a tua scelta e la riga di comando come client del monitor in esecuzione.

### Aggiunto

- **Una barra di stato a piè di pagina** (tutte le edizioni) al posto della riga dell'autore. A sinistra, l'avviso più importante (rosso prima del giallo) con il numero degli altri e un pulsante che apre una finestra con tutti, il più recente per primo, con filtro per livello; senza avvisi lo dice. A destra, la connessione (una spia: GitHub online, offline o quota bassa), la quota e quando si rinnova, l'ultima lettura, la modalità di lavoro, quante sentinelle sono attive, i repository sorvegliati, l'account, versione ed edizione, l'indirizzo del monitor e data e ora locali. Segue la larghezza della finestra: i dati secondari si ripiegano sugli schermi stretti. `GET /api/statusbar` le dà i dati che GitHub non porta (nessuna chiamata a GitHub, nessun segreto).
- **Un pulsante a schermo intero** nell'angolo in alto a destra (l'API Fullscreen; una seconda pressione esce), con icona e testo nelle otto lingue.
- **Tabelle ordinabili**: Repository e Cronologia si ordinano con un clic su un'intestazione (crescente, decrescente, nessuno), per più colonne insieme con Maiusc+clic (ogni criterio mostra numero e verso), con i valori vuoti sempre in fondo, e l'ordine viene ricordato. Un selettore di colonne ne aggiunge altre: numero di esecuzione, autore, commit breve, tentativo, attesa in coda, file ed ecosistema nella Cronologia; ecosistema, numero di esecuzione, autore, commit, tentativo, attesa in coda, esecuzioni in 24 h, ramo predefinito, visibilità, ultimo push e pull request aperte nei Repository. Il monitor ora invia il numero di esecuzione e l'attesa in coda di ogni esecuzione e un piccolo blocco di dati per repository (ricavato da ciò che ha già letto; nulla di nuovo da GitHub).
- **`monitor_cli.py`**, la riga di comando come client del monitor in esecuzione (`status`, `health` o `check`, `doctor`, `accounts`, `alerts`, `live`): legge `GET /api/...` su questo computer o su `--url` / `MONITOR_URL`, stampa testo o un documento JSON con `--json`, accetta `--account`, `--sentinel`, `--level`, `--muted`, `--timeout` e `--lang`, e usa codici di uscita stabili (0 ok, 1 uso errato, 2 monitor non raggiungibile, 3 credenziale rifiutata, 4 degradato, 5 avvisi trovati con `--fail-on`). `health` distingue un monitor che non risponde da un accesso GitHub fallito e da una quota esaurita. L'edizione lite risponde a `status`, `doctor` e `health`. Non scrive mai su GitHub; il token di accesso della modalità di rete va in `MONITOR_TOKEN`. Gli strumenti precedenti continuano a funzionare. Guida in otto lingue (`CLI.md`).
- Test per ogni modifica, compresa la logica di ordinamento eseguita davvero con Node dove è installato, i comandi contro un monitor finto, ogni codice di uscita e un test che verifica che ogni registro delle modifiche, in ogni lingua, elenchi le sue versioni dalla più recente alla più vecchia, con le stesse versioni della fonte.

### Modificato

- **Gli avvisi rossi e gialli non stanno più in cima alla pagina**: gli stessi avvisi compaiono nella barra a piè di pagina (il più importante) e nella sua finestra (tutti).
- **Il README del pacchetto** (`README_<lingua>.txt`) non porta più una cronologia delle versioni: rimanda al registro delle modifiche.
- Le immagini del README, dell'architettura e della struttura sono ridisegnate per questa versione, con un'immagine delle nuove tabelle e della barra.

### Rimosso

- **La riga dell'autore a piè di pagina**: autore e licenza sono in Informazioni.

## [1.7.3]

Una seconda sentinella per issue e pull request, una scheda con gli avvisi di tutte le sentinelle e silenziamenti che finiscono da soli. Collab legge soltanto; nulla di questo scrive su GitHub.

### Aggiunto

- **La sentinella Collab** (`sentinel_collab.py`, solo edizione completa, disattivata di default): le issue e le pull request aperte dei tuoi repository, con un orologio proprio (`sentinels.collab.refresh_seconds`) che non altera mai la sentinella CI. Sei regole con codici stabili: `collab.issue.stale`, `collab.issue.critical`, `collab.issue.external`, `collab.pr.review_pending`, `collab.pr.draft_old` e `collab.pr.conflict`. Legge con richieste condizionali (un repository invariato non consuma quota), al massimo `max_repos_per_tick` repository per giro, si ferma sotto `min_rate_remaining`, tiene il suo stato in `collab_state.json` (nella cartella di ogni account) e annuncia solo i cambiamenti. I bot sono esclusi. Il suo livello *Issue e pull request* è nella scheda Sentinella e `GET /api/sentinel/collab` lo serve.
- **Due nuovi eventi**, `collab_new` e `collab_fixed`, per il registro e per tutti i canali di notifica (sono nell'elenco degli eventi dei canali e nello schema degli eventi).
- **La scheda Avvisi** (edizione completa): un elenco con gli avvisi di tutte le sentinelle, ciascuno con la sua origine (CI o Collab) e il suo livello, un filtro per origine e per livello, un link a GitHub e un punto rosso sulla scheda con gli errori aperti. `?view=alerts&sentinel=collab` la apre già filtrata.
- **Silenziamenti con una fine** (`alert_center.py`): dalla scheda Avvisi si può silenziare un avviso, una regola (il suo codice) o un'intera sentinella per `alerts.mute_hours` ore (24 di default, da 1 a 720). Un silenziamento scade da solo, si ripristina subito e un breve storico dice cosa è stato silenziato, da quando e fino a quando. È una nota del monitor, conservata per account in `alert_mutes.json`; su GitHub non cambia nulla.
- **`ignore_labels`** nelle regole di Collab (`monitor:ignore` di default): un'issue o una pull request che una persona ha etichettato così su GitHub non genera avvisi. Il monitor non scrive mai etichette.
- **`GET /api/alerts`** (`?sentinel=`, `?level=`, `?muted=show|hide|only`) e **`GET /api/events`** (`?sentinel=`, `?since=`), entrambi di sola lettura e per account; `POST /api/alerts/mute` e `/api/alerts/unmute` (solo da questo computer, token monouso, come ogni altra modifica).
- **Una lista di controllo nella vista dal vivo** (segreto di 32 caratteri o più, inoltro o tunnel verso `/api/webhook`, l'evento di prova di GitHub, tenere d'occhio la quota) e gli stessi passi nella guida del webhook.
- **Una guida della sentinella Collab** nelle otto lingue (`COLLAB.md`), trovata dalla Guida.
- Test per ogni modifica: le regole e i loro codici stabili, il costo (letture condizionali, il tetto per giro, la pausa), che legge soltanto, i silenziamenti (ambiti, fine, limiti, storico, un file danneggiato), l'etichetta di esclusione, gli endpoint, che lite non ha nulla di tutto ciò, i file di stato di ogni account e della demo e i testi nelle otto lingue.

### Modificato

- La pagina delle impostazioni ha dodici impostazioni di Collab in un blocco della scheda Sentinella, e `alerts.mute_hours` accanto.
- I file `alert_mutes.json`, `collab_state.json`, `ai_alerts_state.json` e `ALERTS_BRIEF.md` non vengono mai versionati né inclusi in un pacchetto.

## [1.7.2]

Un'intestazione che si legge in ordine e si adatta alla finestra, i controlli rapidi fissi nell'angolo in alto a destra, Informazioni nel pannello laterale e la fine dell'avviso di nuova versione. I test smettono di lasciare file accanto al codice, ed era proprio questo ad aver sostituito le impostazioni di una persona con il modello neutro.

### Modificato

- **Le cifre dell'intestazione, in ordine e in una griglia** (tutte le edizioni): la prima riga va ora da ciò che sta succedendo a ciò che richiede attenzione (in corso, in coda, errori, successi, minuti di calcolo, issue aperte, workflow rossi su main, non firmati) e la seconda tiene la parte meccanica (repository, caldi, modalità, letture risparmiate, quota, connessione, aggiornato). Ogni riga è una griglia di otto colonne, quattro o due secondo la larghezza del suo blocco, così le due righe riempiono sempre le loro file a qualsiasi larghezza di finestra, da uno schermo 1080p in su (una tessera non impone mai una larghezza propria). La lunga tessera della quota occupa due colonne.
- **I controlli rapidi restano nell'angolo in alto a destra**: il pulsante «solo i caldi», l'elenco della velocità (normale, veloce, turbo) e le etichette di salute degli ecosistemi (e gli avvisi di budget e di pausa) sono fissati lì, in una colonna propria, e vanno a capo al suo interno senza spostare le cifre. Sotto i 1100 punti di larghezza l'angolo passa sopra le cifre. La pagina di tutti gli account lo nasconde, come nasconde le cifre.
- **Impostazioni, Guida e Informazioni sono solo nel pannello laterale**: i pulsanti dell'ingranaggio, del punto interrogativo e dell'informazione lasciano l'intestazione. Impostazioni era già una sezione del pannello; Guida di questa scheda resta in fondo e accanto si aggiunge **Informazioni**. La guida delle Impostazioni lo dice nelle otto lingue.

### Rimosso

- **L'avviso di nuova versione nell'intestazione** (il badge arancione) con il suo codice e il suo stile. Il pannello Informazioni dice ancora se c'è una versione più recente, e così la console; l'impostazione `updates.check` e la cache di 24 ore sono le stesse.

### Corretto

- **Il modello neutro poteva sostituire le impostazioni di una persona.** Tre gruppi di test (l'isolamento di lite, il token monouso e la parte lite degli account) avviavano un monitor il cui primo avvio scrive `actions_monitor.json` o `update_check.json` accanto al codice, e nulla li rimuoveva; copiando la cartella `monitor/` su un'installazione, le impostazioni della persona (il suo catalogo di ecosistemi) venivano sostituite dal modello, e tutti i repository finivano nel gruppo «Everything else» (un angolo che diceva «Everything else 54»). Ognuno di quei test rimuove ora ciò che ha creato, e un test lo dimostra. Il pacchetto non ha mai contenuto le impostazioni né il catalogo di nessuno, e continua a non contenerli.

## [1.7.1]

Una pagina nuova e la stessa sentinella dietro un contratto. La pagina ha un pannello laterale a sinistra con il logo, le sezioni in gruppi e sedici temi; la sentinella CI è ora una delle sentinelle di un registro, ed è ciò che permette l'arrivo delle prossime. Ciò che il monitor mostra e decide non cambia.

### Aggiunto

- **Un pannello laterale** (tutte le edizioni): il logo dello strumento (un SVG che si disegna con i colori del tema e sta fermo quando il sistema chiede meno movimento), il selettore degli account, le sezioni in tre gruppi comprimibili (Sorveglia, Dati, Sistema) e la guida. Il pannello si riduce alle sue icone e le due scelte vengono ricordate nel browser. La barra in alto mostra il nome della sezione e gli strumenti. Le frecce, anche su e giù, passano da una sezione all'altra. Su uno schermo piccolo il pannello va in alto. `?chrome=0` lo nasconde, come nascondeva la barra delle schede.
- **Sedici temi** oltre ad auto, chiaro e scuro: quelli dello Studio del sistema di allarme (Armor, Aqua, Midnight, Ember, Forest, Violet, Solar, Ice, Crimson, Mono, High contrast, Metallic, Professional, Videogame, Terminal e Blueprint), scelti da un elenco in Impostazioni > Questo browser o con `?theme=`. Ognuno definisce la pagina, il pannello laterale, i pannelli, le linee, il testo, l'accento, gli angoli e i caratteri. Verde, rosso, ambra e blu mantengono il loro significato in tutti, schiariti o scuriti dove un tema lo richiede perché ogni cifra si legga a 4,5:1 o più, e il testo di un badge segue il suo colore.
- **`BaseSentinel`, `Alert` e `SentinelRegistry`** (`sentinel_base.py`, `sentinel_registry.py`; solo l'edizione completa): il contratto di una sentinella (`start`, `stop`, `tick`, `get_status`, `get_alerts`, `get_metrics`, `get_config_schema`, `refresh_seconds`), un avviso con un codice stabile che non dipende mai dalla lingua (`ci.red`, `ci.stuck`, `ci.pending_sign`) e l'account a cui appartiene, e un registro che dà a ogni sentinella un orologio proprio. `sentinels.<nome>.enabled` in `actions_monitor.json` ne accende o ne spegne una; senza di esso decide `sentinel.enabled`, come sempre, e dove entrambi dicono qualcosa vince il nuovo blocco.
- **`SentinelCI`** (`sentinel_ci.py`): la sentinella di sempre dietro quel contratto. Contiene il vecchio `Sentinel` e non cambia il modo in cui decide: la stessa regola del rosso (l'ultima esecuzione terminata di ogni workflow sul ramo predefinito), gli stessi file, lo stesso ciclo, la stessa istantanea.
- Test per ogni modifica di questa versione: il contratto, il registro e i suoi interruttori, la sentinella CI e i suoi avvisi in due lingue, che l'edizione lite non carichi nulla di tutto ciò, il pannello laterale e i sedici temi (che ognuno definisca tutte le variabili e che il testo, il piccolo testo grigio, l'accento e i quattro colori di stato si leggano a 4,5:1 sulla sua pagina e sui suoi pannelli).

### Modificato

- Il tema si sceglie da un elenco in Impostazioni > Questo browser (prima era un pulsante che percorreva auto, chiaro e scuro); un tema salvato da una versione precedente viene ancora capito.
- Il colore di un badge, di una barra e di un avviso che era bianco su rosso, ambra o verde è ora quello che si legge su quel colore nel tema in uso.
- La sentinella si avvia tramite il registro; `SENTINEL["obj"]` resta la sentinella CI, quindi tutto ciò che le chiedeva qualcosa continua a funzionare. Gli eventi, i file e gli endpoint sono gli stessi.

### Corretto

- Un test della 1.7.0 leggeva l'output di `tasklist` con la tabella di caratteri sbagliata e poteva fallire su un Windows con un'altra lingua.
- **Un rifiuto poteva perdersi per strada** (tutte le edizioni): un POST che il monitor rifiutava prima di leggerne il corpo (token mancante, corpo troppo grande) chiudeva la connessione con dati non letti, e Windows, a volte Linux, rispondeva con un reset: il client vedeva una connessione interrotta invece del 403 dovuto. Ora il monitor legge e scarta ciò che resta del corpo (fino a 1 MB, al massimo 2 secondi) dopo aver risposto, così la risposta arriva sempre. Il rifiuto, il suo codice e il suo testo sono gli stessi. Un test invia le intestazioni, attende e invia il corpo, e fallisce senza questo.

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
- `tools/demo_accounts.py` per le immagini, la guida `ACCOUNTS.md` in otto lingue e test per ogni modifica (la suite è passata da 866 a 914).

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

### Aggiunto

- **Un gruppo jolly** `rest` («Tutto il resto», prefisso `*`) alla fine del catalogo di esempio degli ecosistemi, così una nuova installazione non lascia fuori nessun repository.
- **Un gruppo automatico «Non classificati»** per i repository che nessun gruppo rivendica (impostazione `show_unclassified`, attiva di default; una scelta esplicita di ecosistemi viene rispettata).
- **Un avviso quando il filtro nasconde repository**: un banner (completa e lite) dice «il tuo filtro degli ecosistemi nasconde N dei M repository dell'account» e li nomina.
- **L'edizione lite parte da ciò che hai già configurato**: al primo avvio `actions_monitor_lite.json` copia da `actions_monitor.json` (se esiste) l'account, i repository e gli ecosistemi da sorvegliare, i file di catalogo, le esclusioni, la lingua e la profondità di lettura, e lo dice nella console. Senza quel file il suo modello sorveglia tutti gli ecosistemi.
- **`tui.py --lite`** (o `MONITOR_MODE=lite`) legge l'edizione lite sulla porta 8766.
- **`redrule.py`**, la regola unica e piccola del «rosso su main», usata dalla sentinella e dall'edizione lite (che segna la cifra come approssimata perché indovina il ramo predefinito).
- **`ghamon_etag_invalid_total`**, il conteggio delle voci di cache danneggiate, in `/metrics`.
- Test: parità dei dati dell'intestazione tra l'edizione completa e la lite, il gruppo jolly, il conteggio dei repository nascosti, l'avvio lite, il segno caldo del webhook, la voce di cache danneggiata, e che importare il monitor o la sentinella non carichi mai Rich.
- Guide `LITE` e `SETTINGS` (otto lingue) aggiornate.

### Modificato

- **Entrambe le edizioni mostrano le stesse cifre dell'intestazione**: esecuzioni, errori, successi, minuti di calcolo, in corso e in coda sono contati una sola volta, dal server, sulle stesse 24 ore e con ogni esecuzione contata una volta; l'edizione lite legge con la stessa profondità della completa. L'edizione lite nasconde il riquadro «non firmati».
- **Un evento del webhook segna il repository come caldo**, così il ciclo successivo lo rilegge qualunque cosa dicesse l'evento.
- Il riquadro della quota di GitHub viene disegnato fin dal primo momento, mentre i repository stanno ancora caricando.

### Corretto

- Una nuova installazione con il catalogo di esempio vedeva quasi nessun repository; l'edizione lite ne rilevava uno su 129 perché il suo modello filtrava per ecosistema.
- **Una voce di cache danneggiata è solo un mancato riscontro**: viene scartata e l'endpoint viene riletto per intero.
- «Rosso su main» e i minuti di calcolo differivano tra le due edizioni.

### Sicurezza

- L'edizione lite non eredita mai dalla completa la sentinella, l'IA, il webhook, le uscite né le notifiche, né alcun segreto; non scrive né `ci_red.json` né una coda di firma.

## [1.6.1]

### Aggiunto

- **L'edizione lite**, un secondo prodotto più semplice nello stesso pacchetto: `MONITOR_LITE_GITHUB_ACTIONS.bat` / `.sh` / `.command` o `--lite` / `MONITOR_MODE=lite`. Cosa gira e cosa è fallito, errori e successi delle 24 ore, rosso su main, la cronologia e i grafici di base; una pagina Impostazioni breve (account, repository ed ecosistemi, aggiornamento, lingua, tema); un file proprio `actions_monitor_lite.json`, file di stato propri con il suffisso `_lite` e la porta 8766, così le due possono girare affiancate.
- **Comando `act` nel pannello del repository**: per ogni workflow del repository, `act -W .github/workflows/FILE -j JOB` pronto da copiare. Il monitor non lo esegue mai (eseguirlo esiste solo come azione confermata dell'assistente IA).
- **Un esempio di container** (`deploy/Dockerfile`) che la CI costruisce.
- Guida `LITE` in otto lingue, una tabella Lite contro Completa in ogni README e nuove schermate di entrambe le edizioni in chiaro e scuro.
- La roadmap elenca ciò che non è rientrato: mirror locale degli artefatti, FinOps dei minuti, stato dei runner self-hosted e un'esportazione OTLP, e le note della vista terminale (perché usa Rich).

### Sicurezza

- L'edizione lite non ha sentinella: non viene importata e i suoi endpoint rispondono 404.

## [1.6.0]

### Aggiunto

- **Letture condizionali (ETag)**: ogni lettura degli elenchi di esecuzioni invia `If-None-Match`; una risposta `304 Not Modified` non consuma quota. L'intestazione e `ghamon_etag_saved_total` contano le letture risparmiate; `cache.etag.*` nella scheda Impostazioni.
- **Resistenza ai tagli di rete**: quando tutte le letture di un ciclo falliscono per un problema di connessione, la pagina conserva l'ultima immagine con un banner offline e riprende da sola; eventi `offline` e `online` (possono essere notificati) e `ghamon_offline`.
- **Analisi** (sezione A12 della scheda Sentinella, `/api/analytics`, `/metrics`, la sorgente JSON per Grafana): p50 / p95 della durata di ogni workflow, del tempo in coda dei suoi job e di ogni passo; workflow diventati più lenti del solito; workflow **instabili** (falliti e poi riusciti sullo stesso commit, o che hanno richiesto un altro tentativo), solo un'etichetta che non cambia mai ciò che conta come rosso.
- **Webhook in ingresso in tempo reale**: un evento `workflow_run` firmato aggiorna l'elenco delle esecuzioni del suo repository senza leggere GitHub, gli eventi `workflow_job` portano i tempi di coda e di passo; si conservano solo campi brevi validati (`/api/live-events`).
- **Linter dei workflow**: `lint_workflows.py` (azioni non fissate per SHA, permessi mancanti o ampi, segreti in chiaro, injection, `pull_request_target` con il codice della PR), regole attivabili con una propria gravità, una riga nel rapporto del giorno e la sezione A13. Un commento `# monitor-lint: ignore REGOLA motivo` o l'impostazione `lint.ignore` mette a tacere un rilievo.
- **Notifiche** (disattivate di default): Telegram, Discord, Slack, Matrix, MQTT e un indirizzo HTTP locale, un limite orario, un pulsante di prova e un contratto degli adattatori documentato (`monitor/docs/schemas/notification_event.schema.json`).
- **Assistente IA**: nuovi fornitori `anthropic` (API Messages, il modello lo scegli tu) e `copilot` (`gh copilot` con il tuo accesso, solo testo, senza strumenti); nuovi compiti (rapporto del giorno, note di versione, una domanda su un repository); impostazioni per i tipi di evento, i repository, la lingua e i limiti, un pulsante di prova e l'uso del giorno. Un elenco chiuso di azioni (`gh run rerun`, `gh issue close`, `act`), solo PROPOSTE di default.
- **Le cifre dell'intestazione sono riquadri** con un'icona, una cifra grande e una piccola etichetta, colorati secondo lo stato, con tooltip, un clic che porta alla scheda, cifre che contano e uno scheletro che mostra subito gli ultimi valori noti; anche la seconda riga (repository, caldi, modalità, letture risparmiate, quota di GitHub con una barra e un conto alla rovescia in diretta, connessione, ultimo aggiornamento e avanzamento del caricamento) è fatta di riquadri.
- **Vista terminale**: `tui.py` disegna una griglia in diretta nella console (sola lettura, opzionale, richiede il pacchetto `rich`; il monitor e i suoi test non richiedono alcun pacchetto).
- **Per server e account grandi**: `GET /api/health`, `GH_HOST` per GitHub Enterprise Server (ogni link della pagina lo segue), `discover_limit`, permessi minimi per funzione e una guida per eseguirlo come servizio (systemd, launchd, un'attività pianificata, un container) e dietro un reverse proxy.
- Schemi JSON pubblicati di `ci_red.json`, dell'esportazione pubblica e dell'evento di notifica (`monitor/docs/schemas`) e una roadmap pubblica (`docs/ROADMAP.md`).
- Nuove guide in otto lingue: notifiche, l'assistente IA, analisi, strumenti da console e distribuzione; la guida del webhook copre gli eventi in tempo reale. Tutte le schermate sono state rifatte (chiaro e scuro, strumenti da console inclusi) con `tools/make_screenshots.py` e dati inventati.

### Modificato

- **Impostazioni**: nuove sotto-schede per letture e cache, notifiche, analisi, il linter e la vista terminale; le sotto-schede IA e webhook hanno tutte le loro opzioni.

### Corretto

- **Il linter non dà più falsi allarmi sui segnaposto**: un valore che sembra un segreto viene classificato (un formato di token noto o una lunga stringa ad alta entropia è grave, un riempitivo leggibile come `placeholder` o `changeme` è solo un'informazione, tutto il resto un avviso; i riferimenti e i valori vuoti non sono un rilievo) e il suo valore non viene mai stampato né salvato.
- **Un browser che chiude o ricarica la sua scheda mentre la pagina carica non stampa più un traceback** (`ConnectionAbortedError`, `ConnectionResetError`, `BrokenPipeError`): vengono contati in `ghamon_client_disconnects_total`; un errore vero viene ancora mostrato.

### Sicurezza

- Il webhook in ingresso resta disattivato di default, su `127.0.0.1`, con HMAC obbligatorio.
- I segreti delle notifiche vivono solo nelle variabili d'ambiente; gli host sono fissi; le notifiche non scrivono mai su GitHub.
- Azioni dell'IA: eseguirne una richiede un interruttore proprio e una conferma del comando completo ogni volta, solo su destinazioni che il monitor già sorveglia, con un limite orario, un registro locale e un blocco dopo due errori di fila.

## [1.5.2]

### Aggiunto

- **La scheda Impostazioni è organizzata in sotto-schede**, ordinate dal comune all'avanzato (Questo browser, Generale, Aggiornamento e limiti, Sentinella, Controlli di superficie A10, Prontezza A11, Cartelle e file, Uscite, IA esterna, Webhook in ingresso). In una sotto-scheda le impostazioni stanno in blocchi con titolo il cui primo campo è l'interruttore principale (il resto del blocco si attenua finché è spento). Ogni campo mostra unità e intervallo, un badge (richiede riavvio / si applica subito), un badge per le opzioni di sicurezza che partono nello stato conservativo e una riga di aiuto. Una casella di ricerca filtra tutte le sotto-schede, ogni sotto-scheda conta le sue modifiche non salvate, Salva e Annulla restano visibili, le frecce, Home e Fine si muovono tra le schede e il browser ricorda l'ultima sotto-scheda usata.
- **Ogni impostazione del file di configurazione è ora nella pagina**: i controlli A10 (un interruttore per controllo e i suoi limiti), i pesi del punteggio di salute dell'ecosistema, le fonti delle versioni fissate, i tetti dei minuti di Actions, i file richiesti, i modelli dei file di audit, il periodo caldo della sentinella, la regola del campione sconosciuto di A2, i prefissi dei candidati, l'elenco dei repository e l'interruttore del webhook in ingresso.
- **Coda di firma per affidabilità**: ogni riga dice `verified`, `unknown` o `failed`; la scheda Sentinella ha un filtro Firma con il conteggio di ogni tipo; `read_report.py --sign-trust` filtra l'elenco della console e l'esportazione, e le righe esportate portano `trust`.
- **Chip di prontezza nell'intestazione**: un chip colorato per ecosistema con il suo punteggio di salute.
- **Una dashboard Grafana minima** (`red_by_ecosystem.json`) e un test che controlla ogni metrica di entrambe le dashboard rispetto a ciò che serve `/metrics`.
- Nuova guida `WEBHOOK` (modalità solo aggiornamento) e un esempio commentato delle fonti di fissaggio, in otto lingue.
- `tools/make_settings_doc.py` scrive la tabella delle impostazioni delle guide dallo schema e dai testi della pagina, e la CI la controlla.

### Modificato

- **Il rapporto del giorno raggruppa i suggerimenti di chiusura delle issue** in una riga per repository (il monitor continua a non chiudere nulla).
- **Il contratto della dashboard del profilo** è documentato e verificato da un test (`/api/outputs/dashboard.json` è esattamente il documento di `ci_red.json`; l'esportazione pubblica non porta mai il lato della firma).

### Sicurezza

- Il segreto condiviso del webhook non viene mai mostrato nella pagina: dice solo se è definito.

## [1.5.1]

### Aggiunto

- **La pagina delle impostazioni può configurare l'IA esterna della sentinella** (gruppo «IA esterna per la sentinella»): `ai.provider` (`none` / `ollama` / `openai-compatible`), `ai.model`, `ai.ollama_url` (solo questo computer), `ai.base_url` (solo https), `ai.api_key_env` e `ai.daily_limit`. Disattivata di default; un servizio esterno riceve dati dei tuoi repository.
- **`migrate_state.py`**: porta ai nuovi nomi i file scritti prima della 1.5.0 (eventi, cronologia dei rapporti, candidati alla release, registri dei lotti, l'impostazione `report_history_days`). Una prova a vuoto di default; `--apply` copia e mantiene i vecchi, `--move` li rinomina; nulla di ciò che esiste viene sovrascritto. Guida di una pagina in `docs/MIGRATING.md`, in otto lingue.
- **`--init-catalog`** crea `ecosystems.json`, `targets.json` e `profiles.json` modificabili a partire dagli esempi.
- Un test assicura che nessun documento rimandi il lettore a un comando rinominato nella 1.5.0 (solo le tabelle dei nomi vecchi e nuovi e le guide di migrazione possono nominarli).
- La versione in ogni README.

### Modificato

- **Primo avvio senza file di catalogo propri**: la console dice che si usano i file di esempio.
- Python 3.11 o successivo è il minimo documentato (provato su 3.11 e 3.13 su Windows, Linux e macOS).

### Sicurezza

- Si può indicare solo il NOME della variabile d'ambiente che contiene la chiave dell'IA: la chiave stessa non viene mai mostrata né salvata.

## [1.5.0]

**Avviso di aggiornamento (leggilo per primo).** Diversi file e impostazioni hanno ora nomi inglesi. Non si perde nulla: i vecchi nomi vengono ancora LETTI dove può esistere un file scritto da una versione precedente, e i nuovi nomi sono gli unici scritti.

| Prima della 1.5.0 | Dalla 1.5.0 |
|---|---|
| `leer_parte.py` | `read_report.py` |
| `eventos.py` | `events.py` |
| `parte_history.py` | `report_history.py` |
| `LOTE_GITHUB_ACTIONS.bat` / `.sh` / `.command` | `BATCH_GITHUB_ACTIONS.bat` / `.sh` / `.command` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` (copiali o rinominali per conservare la cronologia degli eventi) |
| `PARTE_CENTINELA_DIA_<day>.txt/.json` (cronologia dei rapporti) | `SENTINEL_REPORT_DAY_<day>.txt/.json` (i vecchi vengono ancora letti) |
| `PARTE_CENTINELA_<time>.txt` (rapporto salvato) | `SENTINEL_REPORT_<time>.txt` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_<time>.json` | `<signed_dir>/batches/batch_<time>.json` (i vecchi registri vengono ancora letti) |
| `parte_history_days` (impostazione) | `report_history_days` (il vecchio nome viene ancora letto) |
| `monitor_y_centinela.zip` e cartella | `github_actions_monitor.zip` e cartella; `LEEME_CORREO.txt` diventa `README_MAIL.txt` |
| A8 cercava `RECONCILIACION_TOTAL_AUDITORIAS_*.txt`, `MAPA_DE_RONDAS_*` | i nomi sono `sentinel.audit_files` (valori neutri predefiniti `RECONCILIATION_TOTAL_*.txt`, `ROUNDS_MAP_2*.txt`, `ROUNDS_MAP_EXTRA_*.txt`); inserisci lì i tuoi |
| `ci_red.json`, il suo schema e i file di `--export-status` | invariati (sono un contratto) |

- **Inglese di default.** La lingua del sistema non decide più: gli strumenti partono in inglese finché non ne scegli un'altra nella scheda Impostazioni, con `language` in `actions_monitor.json`, `MONITOR_LANG` o `--lang`.
- **Un pacchetto pulito e neutro.** `ecosystems.json`, `targets.json` e `profiles.json` non fanno più parte del pacchetto: viaggiano solo i file `*.example.json`, e un file predefinito mancante ricade sul suo esempio. I tuoi file vivono dove vuoi e si indicano con `ecosystems_file`, `targets_file` e il nuovo `profiles_file`; la cartella dei tuoi strumenti di firma locali è il nuovo `tools_dir`. I test usano i propri dati (`tests/fixtures`).
- **Scheda Impostazioni.** Una nuova scheda cambia i valori di `actions_monitor.json` dalla pagina: una lista bianca di chiavi con tipo e intervallo, una richiesta rifiutata per intero quando un valore non è valido, una copia del file precedente in `config_backups/` prima di ogni salvataggio (si conservano le ultime dieci), una scrittura atomica, solo su 127.0.0.1 con gli stessi controlli di Host e Origin di ogni altro endpoint, solo JSON. Token, segreti, chiavi di firma e il comando della sentinella non sono nella lista: non vengono mai mostrati né scritti, e ogni altra chiave del file resta com'era. Ogni impostazione dice se richiede un riavvio. Il selettore della lingua, il tema e la vista densa si sono spostati lì.
- **Pulsanti e icone.** I pulsanti hanno rilievo, si illuminano al passaggio e si abbassano quando premuti; i pulsanti con icona sono SVG inline con nome accessibile e tooltip nelle 8 lingue. Colori, tipografia, schede, barre e anello seguono la dashboard di stato del repository del profilo.
- **Vita nei grafici.** Le barre crescono all'apparire, ciò che è rosso o in corso ha una pulsazione discreta, le cifre dell'intestazione contano verso l'alto, passare su una barra la evidenzia e ne dà il testo come tooltip, le larghezze cambiano con dolcezza; tutto si ferma con `prefers-reduced-motion`.
- **Uscite per altri strumenti (disattivate di default, solo 127.0.0.1, nessun nuovo token).** `/metrics` in formato Prometheus (workflow rossi per ecosistema e repository, serie e ore di rosso, build in attesa di firma, A10 in pausa, quota rimasta, istantanea incompleta...), `/api/outputs/grafana.json` per la sorgente JSON / Infinity di Grafana e `/api/outputs/dashboard.json` (il documento `ci_red.json`) per la dashboard di stato. Una dashboard Grafana importabile è in `docs/grafana/` e i dettagli in `docs/OUTPUTS.md`.
- **Rapporto:** una riga (codice `tag_vs_manifest`) quando un tag di release è avanti rispetto alla versione del manifesto; la cifra dei non firmati è ordinata per l'attesa più lunga e dice quanto è; il pannello del repository suggerisce il comando `gh issue close` (mai eseguito) per un'issue di errore il cui workflow è tornato verde; il profilo di lotto `hil` è documentato in `profiles.example.json`; test per `finalize` e per `monitor_link`.
- **Documenti:** `docs/SETTINGS.md`, `docs/OUTPUTS.md`, README e QUICKSTART nelle 8 lingue aggiornati, schermate fatte con repository inventati.

## [1.4.5]

- **Il rapporto dice quando l'istantanea è incompleta:** una riga con il codice stabile `incomplete` (caricamento in corso, nessuno spazio di lavoro locale, errori di lettura) subito dopo il titolo, così nessuno agisce su un elenco letto a metà di repository rossi o della coda di firma.
- **Riepilogo della firma:** una riga con quante release attendono di essere firmate (verificate / non controllate / controllo fallito) e quante build sono solo di compilazione di proposito, per non confondere «non firmato di proposito» con «firma mancante» (codice `sign_summary`).
- **A10 in pausa per la quota è detto nel rapporto** (codice `a10_paused`) con la quota rimasta e quella necessaria, e le tre manopole che la controllano.
- Testi nelle 8 lingue; test delle tre righe.

## [1.4.4]

- **Autore e licenza sono sempre visibili:** il pannello web ha un piè di pagina con autore e licenza, `read_report.py --version` e il nuovo `gha_dispatch_all.py --version` li stampano sotto la versione, e il monitor stampa la stessa riga all'avvio. Il testo è nelle 8 lingue (`ui.about`); autore e licenza vengono da `tool_version.py`.
- **Il ponte verso la dashboard messo per iscritto:** `docs/CI_RED_BRIDGE.md` dice cosa contiene `ci_red.json` (schema 2, `complete`), come esportarlo e cosa deve controllare un lettore; il monitor continua a non fare push né commit.
- Test della riga dell'autore nelle 8 lingue, del piè di pagina, di entrambe le opzioni `--version` e della riga di avvio.

## [1.4.3]

- **Un workflow che gira solo sulle pull request non rende più A2 inconcludente:** `pull_request` e `pull_request_target` si aggiungono agli eventi le cui esecuzioni non stanno mai sul ramo predefinito (come `workflow_dispatch`, `release` e `workflow_call`), così a un workflow come un controllo di integrazione di contratto che gira solo sulle pull request non si chiede un'ultima esecuzione su main. Un workflow che ha anche `push` o `schedule` conta ancora. Test di entrambi i casi.

## [1.4.2]

- **A2 non considera più vista un'esecuzione in corso o annullata:** nel risolvere un workflow nascosto, la sentinella chiede ora le ultime esecuzioni completate di quel workflow sul ramo predefinito (`gh run list -w <file> --branch <predefinito> --status completed -L 10`, sola lettura) e usa la prima con una conclusione reale. Un'esecuzione annullata o saltata (e qualsiasi senza conclusione) viene ignorata, così non può più nascondere un rosso precedente; un workflow senza esecuzione completata con conclusione sul ramo resta inconcludente da solo. Stessa soglia di quota, stesso limite di chiamate e stessa cache di prima.

## [1.4.1]

- **A2 risolve un workflow nascosto invece di arrendersi con tutto il repository:** quando un repository ha un campione completo di esecuzioni e gli manca un workflow del suo clone (uno che può girare sul ramo predefinito), la sentinella chiede a GitHub l'ultima esecuzione di QUEL workflow sul ramo predefinito (`gh run list -w <file> --branch <predefinito> -L 1`, sola lettura). Una risposta rossa conta come rosso in A2; una verde toglie il workflow dall'elenco degli inconcludenti; un workflow senza esecuzione sul ramo resta inconcludente da solo e il pannello lo nomina (`repo/file.yml (nessuna esecuzione sul ramo predefinito)`) invece di nominare solo il repository. Senza quota (la stessa soglia di A10: `min_rate_remaining` x `surface.min_rate_factor`, più il budget orario) il workflow resta inconcludente e il pannello dice perché. Nuove opzioni `sentinel.a2_resolve_max_calls_per_tick` (4; 0 = non chiedere mai) e `sentinel.a2_resolve_ttl_seconds` (3600, per quanto si conserva una risposta; viene salvata anche nel file di cache). L'istantanea porta `a2.inconclusive_workflows` (etichette) e `a2.inconclusive_details`; `a2.inconclusive` resta l'elenco dei repository. 5 nuovi testi nelle 8 lingue e un `ui.a2_inconclusive` riformulato.

## [1.4.0]

- **Nuovo livello A11 «Prontezza» (sola lettura, solo dati reali):** un pannello della scheda Sentinella, un semaforo nella sua intestazione e due righe del rapporto. Si attiva con `sentinel.readiness.enabled` ed è descritto in `readiness.py`.
  - **Prontezza della release:** una riga per ogni repository con almeno `candidate_min_entries` voci in `[Unreleased]` (esclusi gli ecosistemi esterni): la CI del ramo predefinito (la regola unica di A2) con il commit su cui è girata, se la versione dichiarata dal clone (`*.project.json`, altrimenti `pyproject.toml`, altrimenti la prima intestazione del CHANGELOG) è già sopra l'ultima release, se esiste una build successiva a quella release, se è firmata (gli stati di A5) e il passo successivo (`correggere la CI rossa`, `attendere i dati di esecuzione`, `alzare la versione`, `compilare in Actions`, `firmare`, `pubblicare`, `tagliare e pubblicare`). Una CI verde su un campione di esecuzioni completo che può nascondere un workflow più vecchio lo dice.
  - **Salute dell'ecosistema:** per ecosistema, 100 meno i conteggi ponderati di CI rossa, build bloccate, segreti, avvisi gravi, altri avvisi, PR di Dependabot più vecchie di `stale_pr_days`, build in attesa di firma e repository con problemi di igiene (`sentinel.readiness.health.weights`); le parti che abbassano il punteggio sono elencate. Non si mostra alcun punteggio (`?`) quando meno di `min_coverage` (0,5) dei repository dell'ecosistema hanno dati di esecuzione e avvisi. Il rapporto avvisa quando un punteggio è sotto `warn_below` (70).
  - **Pin delle dipendenze:** repository che fissano una versione più vecchia di quella del repository che fornisce il contratto o la libreria. Dove vivono i pin è un dato (`sentinel.readiness.pins.sources`): una tabella JSON di pin nel fornitore (`pin_table`) o file di lock nei consumatori (`lock_files`, conta il più vecchio trovato). Semplici letture di file dei cloni locali, in cache `pins.refresh_seconds`; un ecosistema senza fonte configurata è elencato come senza, e nulla viene indovinato. L'esempio incluso non ha fonte.
  - 60 nuovi testi nelle 8 lingue; `tests/test_readiness.py` (regole, pesi, copertura, pin su un albero temporaneo, la pagina e gli 8 cataloghi).
- **`docs/CI_RED_SCHEMA.md`:** dice esplicitamente che il PC non pubblica né `ci_red.json` né `pending_sign` su alcun repository o dashboard (il lato della firma è locale per decisione); un consumatore pubblico ricalcola la regola dalle esecuzioni pubbliche o usa `read_report.py --export-status`.
- **Regolazione della quota dal registro (`actions_monitor_log.txt`, 3 giorni, 889 campioni):** la quota condivisa era sotto la soglia (`min_rate_remaining` 1500) nell'11 % dei campioni dal 5 novembre e sotto 3000 nel 45 %; il consumo orario era di 3000-5000 chiamate nella maggior parte delle ore e in alcune raggiungeva il limite. Nel `actions_monitor.json` del manutentore: `refresh_seconds` 120 -> 180 (il ciclo reale aveva una mediana di 139 s) e `sentinel.surface.min_rate_factor` 2,0 -> 1,5 (le chiamate a freddo di A10 sono circa 260 al giorno, quindi possono girare sopra 2250; con 3000 aspettavano quasi metà del tempo). `max_repos_per_tick` (6) e il ciclo giornaliero a freddo restano: costano meno dell'1 % della quota. L'esempio incluso mantiene i suoi valori neutri.

## [1.3.3]

- **A2 ignora i workflow che non girano mai sul ramo predefinito:** nel decidere se un campione completo di esecuzioni nasconde un workflow, i file del clone il cui `on:` non ha `push`, `pull_request` né `schedule` per il ramo (solo `workflow_dispatch`, `release`, `push` solo di tag senza `branches`, o `workflow_call`) non sono più attesi nel campione. `on:` viene letto con la sola libreria standard (stringa, elenco, mappa e la chiave YAML `true`); se non si può interpretare, il workflow conta come prima. La scansione dei workflow porta il nuovo campo `main_triggered` (`true`/`false`/`null`).

## [1.3.2]

- **A2 mostra `unknown` invece di verde quando il suo campione è pieno e inconcludente:** un repository la cui lista di esecuzioni è lunga quanto il campione richiesto (`runs_per_repo` / `cold_runs_per_repo` del monitor, che il controllo prima non vedeva) e il cui clone ha un file di workflow senza esecuzione in quel campione (o non ha clone) viene elencato come inconcludente, e A2 è `unknown` a meno che qualcosa non sia rosso. Nuova opzione `sentinel.a2_full_sample_unknown` (predefinita `true`; `false` = solo informativa come prima). La pagina elenca i repository.
- **`profiles.example.json`:** un modello neutro di profili di lotto che corrisponde a `targets.example.json` e `ecosystems.example.json`. Un test (e la soglia della release) lo convalida contro quei cataloghi, non quelli del manutentore, e controlla che ogni profilo selezioni almeno una destinazione.
- **Controllo di installazione pulita in `make_release`:** prima di lasciare qualcosa nella cartella di uscita lo zip viene estratto in una nuova cartella temporanea vuota e, da lì con `python -I`, ogni membro deve esserci, ogni modulo compilare, `read_report.py --version` funzionare e l'intera suite passare; qualsiasi lacuna fa fallire la release.
- **Formulazione:** README e QUICKSTART nelle 8 lingue dicono ora che il pacchetto non scrive nulla su GitHub da solo e che solo `dispatch --go`, `dispatch --real` e `finalize --execute` (che esegui tu) lo fanno.
- **Quota di A10:** la parte del budget di chiamate per ciclo della sentinella che A10 può usare è ora `sentinel.surface.budget_share` (predefinito `0.5`, come prima ma configurabile); la pagina mostra «A10 in pausa per la quota» con la quota rimasta e quella necessaria (`min_rate_remaining` x `min_rate_factor`) mentre le chiamate a freddo attendono.

## [1.3.1]

- **Un'esecuzione costruita su un altro commit non viene mai offerta per la firma:** quando `dispatch` ha potuto trovare solo un'esecuzione recente di un altro commit (`sha_matched` falso), `finalize` ora la elenca come non pronta con il motivo e non dà alcun comando di firma; un vecchio lotto senza il campo si comporta come prima. Test con due esecuzioni concorrenti di commit diversi.
- **`/api/data` passa per la stessa guardia Host/Origin delle altre rotte** del server locale (DNS rebinding).

## [1.3.0]

Fatta per essere condivisa: otto lingue, paternità e licenza in ogni file, nessun dato privato e nulla legato a un account GitHub.

- **8 lingue** (en, es, de, fr, it, ja, zh, pt = portoghese del Portogallo) per la pagina, gli strumenti a riga di comando, i lanciatori, gli eventi, i rapporti e i messaggi di errore. `i18n.py` + `locales/<lingua>.json` (un catalogo piatto per lingua, solo libreria standard, `t("chiave", nome=valore)` con ripiego sull'inglese). La lingua è `language` in `actions_monitor.json` (predefinita: la lingua del sistema, inglese se non supportata), un selettore nell'intestazione della pagina (il browser lo ricorda), `MONITOR_LANG` / `JUANENRAC_LANG`, o `--lang CODICE` in ogni strumento (prevale sul resto). I nomi tecnici, i comandi, i percorsi e i marcatori che leggono gli script (`SKIP`, `DISPATCHED`, `READY`, `FAILED`, `Summary:`, `BUILD ONLY`, `WOULD DISPATCH`...) non vengono mai tradotti. Gli eventi in `events_monitor.jsonl` portano ora un `code` stabile (e `args`) accanto al testo, così nessuno deve interpretare una lingua.
- Un test verifica che gli 8 cataloghi abbiano esattamente le stesse chiavi, nessuna vuota, gli stessi `{segnaposto}`, che ogni chiave usata dal codice e dalla pagina esista e che nessun testo visibile nel codice aggiri `t()`.
- README e QUICKSTART nelle 8 lingue (`README_<lingua>.txt`, `QUICKSTART_<lingua>.txt`); `README.txt` è ora un breve selettore di lingua con l'avvio rapido.
- **Paternità e licenza**: ogni file sorgente porta «Copyright (C) 2026 JuanenRac (Electro Hobby 3D)» e «GPL-3.0-or-later - see LICENSE»; i file di dati JSON portano `_author` / `_license`; `LICENSE` (testo della GPL-3.0), `NOTICE` e `AUTHORS` viaggiano nello zip. `make_release.py` si rifiuta di costruire quando a un file mancano, quando viaggerebbero dati privati, quando i locali differiscono o quando un lanciatore perde il bit di esecuzione.
- **Condivisibile**: `github_owner` nella configurazione (predefinito: l'account di `gh`) sostituisce la costante sparsa in tre moduli; i prefissi degli ecosistemi e gli strumenti di firma sono dati (`ecosystems.json`, neutro `ecosystems.example.json`; `"*"` = ogni repository; `"external": true` = solo segnalato) e così le destinazioni (`targets.json` è il catalogo reale del manutentore, `targets.example.json` quello neutro; `targets_file` / `ecosystems_file` li scelgono; le chiavi che iniziano con `_` sono metadati). La configurazione di esempio è neutra. Nulla di questo aggiunge una chiamata al ciclo caldo.
- **Lo spazio di lavoro è facoltativo**: senza cloni locali il monitor parte in modalità ridotta (solo ciò che dà l'API di GitHub: niente coda di firma locale, niente rapporto di audit, niente scansione del CHANGELOG) e lo dice nella pagina, nel rapporto e all'avvio, invece di fermarsi. `MONITOR_ROOT` / `MONITOR_AUDIT_DIR` / `MONITOR_SIGNED_DIR` e `signed_dir` sono stati aggiunti accanto ai vecchi nomi. Anche il livello della roadmap (A9) è facoltativo.
- Lanciatori: menu e messaggi vengono da `launcher_msg.py` (la tua lingua); commenti in inglese; intestazione in ogni file.
- Correzione: `workspace_root()` non termina più il monitor quando la sentinella parte senza spazio di lavoro.

## [1.2.0]

Ciò che mancava e che altro si può fare su GitHub, tutto in sola lettura e locale.

**Parte A - ciò che mancava**
- Lo schema 2 di `ci_red.json` è ora un contratto documentato: `docs/CI_RED_SCHEMA.md` (forma, la regola unica del «rosso», ciò che è solo per il proprietario). Dal PC non si pubblica nulla. Esportazioni facoltative ed esplicite (mai un commit né un push): `read_report.py --export-status DIR` scrive SOLO l'elenco dei rossi (`ci_status_public.json/.md`); `read_report.py --export-sign-queue FILE` (.json/.csv) scrive la coda di firma globale con i comandi locali.
- Attestazione: la coda di firma mostra se la build ha un'attestazione (esistenza per digest dei file firmati, una ricerca per voce, senza verifica della firma; interruttore `sentinel.surface.checks.attestation`). Una mancante è una riga del rapporto.
- Più formati verificati: HYDRA `hydra-sign` (`FILE.sig` = Ed25519 in base64 sui byte del file, la chiave di release fissata, letto a blocchi) viene verificato in modo definitivo; URTC `.imgsig` ha il formato rigoroso controllato (152 cifre esadecimali + LF; malformato = non valido) e resta «unknown» quando è ben formato (il messaggio firmato richiede anche l'intestazione della build, che la cartella dei firmati non porta); gli APK di ARMOR sono firmati dentro l'APK da apksigner e restano «unknown».
- `HYDRA-UMC-OS` è etichettato di proposito in `targets.json` (`"build_only": true` + `reason`): `plan` lo elenca sotto BUILD ONLY e non è più orfano. Gli strumenti di firma non sono stati toccati (il suo workflow prende altri input e uno schema di firma diverso).
- Correzione: `ci_red.target_path` rifiutava ogni percorso Windows scritto con barre rovesciate (`C:\...`); si accettavano solo le barre normali.

**Parte B - il livello A10 «superficie di Actions e release»** (`surface.py`, nuova sezione della scheda, un interruttore e una soglia per controllo sotto `sentinel.surface`)
- Actions: workflow disattivati a mano, pianificazioni senza esecuzione da N giorni (solo quando il campione di esecuzioni copre la finestra), `uses:` non fissati per SHA (i workflow riutilizzabili segnalati a parte), `permissions: write-all`, `pull_request_target` con checkout della PR, code di concorrenza bloccate, errori su un solo SO di una matrice, costo e conservazione degli artefatti, controlli di stato richiesti rossi o mancanti (GraphQL), `dispatch --profile release|nightly|hil` con un canarino (solo la prima destinazione, le altre solo se è verde) e una soglia di quota (`--min-rate`, fallisce chiusa). I profili vivono in `profiles.json`.
- Release: asset attesi per tipo di destinazione (avviso quando una release è stata pubblicata incompleta), tag contro manifesto contro CHANGELOG, GitHub Packages, bozze e prerelease dimenticate, `release_notes.py` (una BOZZA di note dai commit dall'ultimo tag; non pubblica nulla).
- Sicurezza: avvisi critici/alti per età con una classifica dei repository, copertura (uno stack senza CodeQL/Dependabot), scansione dei segreti aperti contro risolti, Dependabot per priorità (prima le major di runtime, per ultime quelle solo di CI).
- Issue e PR: suggerimento di `gh issue close` per le issue di build la cui CI è tornata verde (un evento con il testo; non si chiude mai nulla), milestone scadute, vecchie PR umane, PR che toccano workflow o CODEOWNERS, la coda di merge (approvate con controlli verdi). Schede di board obsolete: IN SOSPESO (richiede letture per elemento e una soglia).
- Manifesto contro evidenza (maturità), errori di parità del README in 8 lingue, minuti di Actions per ecosistema nell'intestazione, nel rapporto e in A7.
- `finalize --execute` ora dice al monitor in esecuzione (127.0.0.1) di aggiornare solo i repository firmati e di riscrivere subito `ci_red.json` (`monitor_link.py`).
- Ricevitore facoltativo di webhook firmati (`webhook.enabled`, disattivato di default, solo 127.0.0.1, HMAC con un segreto condiviso dalla configurazione, mai un token di GitHub).
- Costo: nulla nel ciclo caldo. A freddo, distribuito sui cicli e dentro il budget orario: 2 chiamate REST per repository al giorno, una query GraphQL ogni 15 repository al giorno, 3 per Packages, più i job delle esecuzioni rosse e le ricerche di attestazione della coda di firma, e solo finché la quota è sopra il doppio di `min_rate_remaining`. Il passaggio GraphQL caldo chiede 3 campi in più per nodo (date degli avvisi, decisione di revisione, stato dei controlli): nessuna chiamata in più.
- La soglia confronta anche `sentinel.surface` del file di esempio con i valori predefiniti e convalida `profiles.json`.

## [1.1.1]

- **Multipiattaforma:** il monitor e gli strumenti di lotti funzionano su Windows, macOS e Linux. Lanciatori `MONITOR_GITHUB_ACTIONS.sh`/`.command` e `BATCH_GITHUB_ACTIONS.sh`/`.command` (lo zip conserva il permesso di esecuzione e make_release rifiuta i fine riga di Windows al loro interno).
- Nuovo `platform_compat.py`: il comando che avvia uno strumento figlio (`py -3` su Windows, l'interprete corrente altrove), il testo dei comandi che mostra `finalize` (virgolette cmd/PowerShell o POSIX), console UTF-8 e un avviso con il modo di installare `gh` su ogni sistema.
- Nuovi test della parte multipiattaforma (Windows e POSIX simulati da qualsiasi sistema).

## [1.1.0]

Affidabilità delle firme, un ponte stabile verso la dashboard, orfani e convenzioni negli strumenti di lotti, e una pagina più utile.

- Affidabilità della firma: `sigverify.py` (libreria standard, sola lettura, senza rete) controlla la cartella dei firmati `_firmados/<REPO>/release-<versione>/` contro la chiave PUBBLICA che ogni ecosistema fissa (URTC `release_sign.py`, l'helper ARMOR `PACKAGE_PUBLIC_KEY`, l'updater HYDRA `RELEASES_PUBLIC_KEY`, o `sentinel.signature_pubkeys`). Ogni stato porta ora `signature_kind` (none | dev | release) e `signature_verified` (true | false | "unknown"); solo una firma di release che si verifica (`trusted`) abbassa l'avviso di firma in sospeso, oltre a «pubblicato». Una firma che non si verifica mantiene l'avviso e lo dice nel rapporto. `sentinel.require_verified_signature` (predefinito true; false = la regola della 1.0.0). I formati che questo modulo non può controllare (.sig2, .hdr2, .imgsig, APK, hydra-sign) sono «unknown», mai «false». L'attestazione della build richiede ancora la rete e resta agli strumenti di firma.
- Schema 2 di `ci_red.json`: per repository una lista `pending_sign` (workflow, ore, stato, signature_kind, signature_verified, last_build_at, url) accanto ai workflow rossi, più `schema`, `pending_sign_repos` e la soglia; il formato è documentato in `ci_red.py` e viene solo esteso.
- Una sola definizione di «ultima esecuzione su main» (`signstate.completed_runs`) condivisa dal controllo del rosso, da quello del verde senza release e dagli stati delle destinazioni.
- `ci_red.target_path` rifiuta i percorsi D:, le forme WSL/Git Bash di D: e i percorsi di unità/UNC che il sistema in esecuzione non può usare; i test simulano entrambi i sistemi e l'intera suite ora passa su Linux.
- `gha_dispatch_all.py plan` termina sempre con la sezione «Orfani di firma» (CI verde + `*-build.yml` noto + nessuna destinazione); la copertura è per repository E workflow.
- Convenzione per le destinazioni (prefisso dell'ecosistema -> strumento di firma predefinito, workflow nell'elenco noto); `targets.json` contiene solo le eccezioni e vince sempre. `hygiene --write-candidates` scrive le voci proposte in `targets.candidates.json` (mai applicate da sole, mai impacchettate).
- Pagina: contatori dell'intestazione cliccabili «rosso su main» e «non firmati» (filtrano i repository; il secondo mette a fuoco anche la coda di firma), la coda di firma con i suoi comandi e un pulsante di copia, pannello del repository con costruito / firmato / pubblicato, tipo di firma e verifica, e il comando suggerito; un badge nell'intestazione quando un budget di minuti raggiunge l'80 % (rosso se superato); «ieri contro oggi» confronta anche gli avvisi di budget e le righe del rapporto.

Non fatto: leggere l'attestazione della build / SBOM (rete); `HYDRA-UMC-OS` ha un workflow di build ma il suo strumento di firma non lo supporta ancora (elencato come orfano).

## [1.0.0]

Prima versione numerata. Cosa fa il pacchetto:

- Monitor di GitHub Actions per i quattro ecosistemi (pagina web locale, cache delle esecuzioni, build bloccate, issue build-failed/build-stuck).
- Livello A della sentinella (sola lettura, senza IA): A1 build bloccate, A2 CI rossa (un solo criterio: l'ultima esecuzione completata di ogni workflow sul ramo predefinito), A3 avvisi CodeQL/Dependabot/segreti, A4 pull request di Dependabot, A5 release (candidate, build verdi senza release, firma in sospeso), A6 igiene, A7 consumo (minuti e quota dell'API), A8 audit e giri, A9 board della roadmap.
- Stato esplicito di ogni destinazione di build: built_on_gha -> signed_local (none | dev | release) -> published, con `last_build_at`, `last_signed_at`, `signature_kind` e le ore reali di attesa; i registri locali di lotti e della cartella dei firmati abbassano l'avviso di firma in sospeso senza aspettare GitHub.
- Coda di firma del giorno (`a5.sign_queue`): il più urgente per primo, con il comando finalize esatto di ogni destinazione.
- Budget dei minuti di Actions per ecosistema (`sentinel.minutes_budget`, vuoto di default): avviso all'80 % nel rapporto e come evento.
- Flusso di eventi (`events_monitor.jsonl`) e `ci_red.json` (repository -> workflow rossi + ore in attesa di firma), scritti in modo atomico.
- Strumenti di lotti: `gha_dispatch_all.py plan|dispatch|status|finalize|hygiene` con `--only` o `--ecosystem`, `plan --json`, `finalize --json`, un nuovo tentativo di un dispatch fallito alla fine del lotto, destinazioni come dati in `targets.json`.
- `read_report.py`: il rapporto come testo semplice dal monitor in esecuzione, senza consumare quota dell'API.
- `make_release.py`: soglia di qualità (test unitari, zip pulito, configurazione di esempio completa, accordo versione/changelog) e SHA256SUMS.

Non fatto in questa versione: verificare le firme delle release contro la chiave pubblica e l'attestazione della build dalla sentinella (formati di firma diversi per ecosistema; l'attestazione richiede la rete; gli strumenti di firma verificano entrambe prima di pubblicare).

