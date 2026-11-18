# Roadmap

Ciò che è stato pubblicato, ciò che viene dopo e ciò che è solo un'idea, in questo ordine di certezza. Sono direzioni, non impegni; una issue o una pull request è il modo migliore per farne avanzare una.

## A che punto è il monitor

Versione 2.0.2. L'edizione lite mostra ciò che gira e ciò che è fallito. L'edizione completa aggiunge tre sentinelle (CI, Collab e Security), un elenco di avvisi, più account e un team con ruoli, il punteggio di ogni account, la salute di ogni repository e del team, rapporti programmati, un registro delle azioni, notifiche (ntfy, Teams, e-mail e Apprise), un assistente IA facoltativo con preset di servizi compatibili, la modalità servizio con Docker e una pagina per ogni dimensione di schermo, dal telefono al 4K.

## Previsto, in quest'ordine

Ogni versione porta solo contenuto reale: una versione senza nulla di reale da aggiungere viene saltata e mai pubblicata vuota. Nulla di questo è dato per provato su servizi reali se la sua guida non lo dice.

### Da 2.0.2 a 2.0.9 - Dopo il congelamento

Ciò che emerge solo con un uso reale prolungato: la migrazione dalla 1.8 e dalla 1.9, la crescita degli eventi e del database in mesi, le sessioni dopo un aggiornamento, i volumi Docker, molti account con tre sentinelle e la modalità squadra insieme, e ciò che trova la suite di contratto. Nulla della quarta fase (plugin, automazione estesa, IA avanzata) entra in queste versioni; una versione senza contenuto reale viene saltata.

I workflow del monitor stesso rispettano ciò che la sentinella di igiene chiederà agli altri: azioni fissate a un commit, permessi minimi e un limite di tempo su ogni job.

## Fatto dalla 1.8.2 alla 2.1.2

### 2.1.2 - Il monitor si aggiorna da un menu, confronta un periodo con il precedente e i pannelli aperti arrivano in fondo

Il menu Aggiornamenti (edizione Completa) mostra la versione installata e quelle pubblicate con le loro note, applica un aggiornamento con copia preventiva, controllo dello zip rispetto a SHA256SUMS, migrazione della configurazione e riavvio, e torna indietro con un clic se la nuova versione non parte; l'aggiornatore autonomo resta la via di ritorno. Il confronto mette un periodo accanto al precedente, con stati onesti quando una cifra non si può dire, un rapporto di cosa è cambiato, una rotta, un comando, una sezione della scheda Grafici e una sezione facoltativa del report pianificato. I file scritti da più processi usano il blocco del sistema operativo, il pannello aperto di una scheda del Sentinella arriva in fondo alla sua casella, avviare il monitor dall'aggiornatore non apre più una finestra di console per ogni chiamata a git e gh, e l'immagine dell'architettura mostra cosa è diventato il monitor.

### 2.1.1 - Due nuove sentinelle, una per la catena di fornitura e una per la consegna, e un gate di release più rigoroso

Due nuove sentinelle, disattivate di fabbrica e solo nell'edizione Complete, leggono ciò che un repository costruisce e ciò che consegna senza scrivere nulla su GitHub: quella della catena di fornitura controlla nei file di workflow le azioni non bloccate, i rami mobili e i permessi troppo ampi o assenti, quella della consegna confronta release, tag, changelog, file di versione e versioni bloccate. Il doctor ora segnala in rosso un webhook in ingresso senza segreto, la copertura del webhook non resta più attiva quando l'orologio è portato indietro, e il gate di release confronta il contenuto di ogni file dello zip con il commit, accetta un'esecuzione verde completa in base al conteggio dato da unittest e può mostrare l'avanzamento delle sue suite.

### 2.1.0 - Schermi a muro con tema, logo e modalità a rotazione, una copia ripristinabile e un aggiornatore

Gli schermi a muro portano il tema del prodotto e possono mostrare il logo dell'organizzazione; una finestra può scorrere tra i tre schermi e saltare a un nuovo rosso; il quadro generale mostra la mappa della flotta per gruppi; un aggiornamento Dependabot fallito è un avviso a sé; e ogni tipo di evento ha il suo suono anche su questo computer. L'installazione si può copiare per intero, verificare e ripristinare, con una pianificazione se si vuole, il doctor controlla il funzionamento con codici di uscita che non cambiano e si può eseguire una pulizia su richiesta. L'aggiornatore porta un'installazione a qualsiasi versione pubblicata, la copia prima e torna indietro se qualcosa fallisce. Il cancello di rilascio nomina i test che falliscono e accetta una passata verde già vista, le etichette di stato dei pannelli di dettaglio restano su una riga, i link della pagina si verificano leggendo l'indirizzo e la guida del container spiega come aprire la prima sessione.

### 2.0.9 - Un audit indipendente più sicuro, menu con gruppi, un suono per ogni tipo di evento e comandi chat di sola lettura

L'audit indipendente ha irrobustito il monitor: il token di accesso non viaggia più nell'indirizzo per impostazione predefinita, un silenziamento per pattern non silenzia più ciò che non è un workflow, il pulitore di testo cattura più forme di un log reale, un'intestazione con un segreto non segue mai un reindirizzamento, una consegna del webhook viene verificata e non può essere ripetuta, e un provider su internet o a un indirizzo privato richiede il proprio interruttore. Il menu a sinistra ha gruppi con titolo, ogni tipo di evento ha il suo suono, comandi di sola lettura rispondono in Slack e Discord (spenti per impostazione predefinita), le schermate a parete seguono la lingua della pagina principale e l'IA integrata ha un solo budget che conta anche l'avviso attivo. Il registro delle azioni può diventare condizione delle azioni e conserva il numero di file ruotati che scegli, un ciclo conta una sola volta per tutte le fasi della sentinella, e un workflow per l'audit dell'immagine del container, con i difetti trovati nel container, fa parte della versione.

### 2.0.8 - Un segreto del webhook più sicuro, check run e una guida per configurare il webhook (la versione che chiude la quarta fase)

Il segreto condiviso del webhook in ingresso viaggia solo nell'ambiente (o in un file che l'impostazione nomina), il webhook accetta anche gli eventi di check run, la vista Dal vivo dice quanta parte del tempo coprono gli eventi, e una guida in otto idiomi (`docs/WEBHOOK.md`) configura il webhook in GitHub passo per passo. Gli studi di account reali aggiungono tre righe: un workflow il cui file è stato eliminato non è attivabile, un fork mai spinto non è spinto di recente, e il runner `codspeed` è riconosciuto come runner di terzi a pagamento. I documenti non dicono più che macOS gira nel CI. È la versione che chiude la quarta fase: una versione di stabilizzazione prima dell'audit.

### 2.0.7 - Un'API di lettura per i client, il repository originale di ogni fork e i workflow disattivati a mano

Un'API di lettura sotto `/api/v1/` per i client (`me`, `repos` e `openapi`, disattivata di default, con un contratto congelato); un seguimento facoltativo del repository originale di ogni fork (`upstream.enabled`, disattivato di default, con un limite di richieste all'ora); e un workflow che il proprietario ha disattivato a mano non è più un rosso ma viene mostrato a parte (`ci.disabled_apart`).

### 2.0.6 - Tre schermi a parete, disegnati e disattivati di default

I tre schermi a parete sono disegnati: Panoramica (punteggio, lampade della flotta, grafici, mappa di calore, runner e la quota), Adesso (esecuzioni in corso, coda, approvazioni, guasti recenti e una linea dal vivo) e Sentinelle (una scheda per sentinella con un radar animato). La pagina disegna da sola ogni grafico, un nuovo guasto lampeggia una volta e si calma, nulla si muove per chi ha chiesto meno movimento, tutto si sposta un poco ogni minuto contro il burn-in, la pagina può attenuarsi di notte, una finestra può ruotare tra le tre pagine e un test del browser le verifica in 1080p, 4K e ruotate negli otto idiomi. Gli schermi sono disattivati di default (`screens.enabled`), e il README e la guida degli schermi ora li mostrano.

### 2.0.5 - Meno falsi rossi, repository dormienti e domande visibili a schermo intero

Un rosso ora conta in base all'origine dell'evento: i workflow che GitHub crea per sé (`dynamic/`) non sono CI rossa né file, la ricerca di un workflow nascosto segue la stessa regola di origine, le esecuzioni in coda per giorni sono riconosciute come coda fantasma (7 giorni di default) e un rosso di cui nessuno si occupa invecchia dopo 30 giorni e diventa inattivo; i repository dormienti e inattivi sono uno stato a sé, né verdi né rossi; i fork entrano in igiene, lint e punteggio solo se hanno una CI propria negli ultimi 90 giorni; la protezione del ramo predefinito è giudicata di default su ciò che è in vigore, da tutte le fonti pubbliche; e le cinque conferme della pagina usano un dialogo della pagina visibile a schermo intero.

### 2.0.4 - Un modello per ogni compito, menu indipendenti e un aiuto che apre l'argomento giusto

L'IA del monitor può usare un modello per ogni tipo di compito, una catena di riserve quando il modello principale fallisce e un budget per ogni modello, il tutto disattivato finché non è scritto nelle impostazioni; Avvisi, Rapporti e Lezioni sono tre voci indipendenti del menu, ciascuna con il proprio pannello, badge, argomento di aiuto e indirizzo; la scheda Cronologia mantiene un solo contatore invece di accumulare copie a ogni aggiornamento; il pulsante «Aiuto di questa scheda» apre in ogni scheda l'argomento della scheda aperta; e i test del browser vengono saltati senza errori quando manca la cartella degli strumenti.

### 2.0.3 - Account grandi, meno falsi rossi, lint senza cloni e archiviazione più sicura

Una vista di flotta, elenchi paginati, un budget di richieste e una copertura onesta dell'elenco delle esecuzioni per account con centinaia di repository; un rosso conta solo se l'ha causato il repository stesso, e le esecuzioni in attesa di approvazione, i workflow abbandonati, quelli che reagiscono solo a issue, la coda di merge e i rami di manutenzione hanno ciascuno il proprio posto; il linter dei workflow e i controlli di superficie funzionano tramite l'API o un clone parziale senza clonare; i modelli del fornitore di IA vengono letti e verificati, e ogni link della pagina passa dal filtro degli indirizzi; i blocchi e il registro delle azioni sono più sicuri su Windows e il registro del punteggio non viene mai sovrascritto; schermi a parete per un monitor o un televisore, disattivati di default; i test del repository per ora non girano più su macOS.

### 2.0.2 - Registri più sicuri, testo per l'IA più pulito e un punteggio più giusto

Tutto ciò che un'IA può leggere passa per un solo pulitore che conosce più forme di segreto, l'assistente integrato conserva la sua chiave e non segue più reindirizzamenti né proxy, il registro delle azioni è una catena in un file per account e un lettore non può leggerlo, l'immagine e i processi degli account non portano più segreti, il punteggio penalizza un errore mai corretto e non conta più una fonte illeggibile come pulita, e un lungo elenco di correzioni di archivio, backup, migrazione, viste da terminale e avviatore.

### 2.0.1 - Pacchetto e una chiave mancante

Lo zip pubblicato ora contiene il file dei preset IA e ogni altro file di dati del pacchetto, e la porta di rilascio fallisce se ne manca uno nello zip; la pagina di tutti gli account non mostra più una chiave di stato non tradotta, e un test verifica che ogni chiave usata dalla pagina esista negli otto cataloghi.

### 2.0.0 - Maturità

L'API di lettura e le interfacce pubbliche sono congelate: un file di contratto con le chiavi e i tipi di ogni endpoint di lettura e i codici di errore, una suite di test e uno strumento che lo verificano su qualsiasi monitor in esecuzione, un test che fissa i campi di un avviso e i metodi di una sentinella e di un'archiviazione, e una guida per ogni uso (lite, una persona, servizio, squadra) e per i client dell'API, in otto lingue. Le versioni da 1.9.6 a 1.9.9 non avevano nulla di reale da aggiungere dopo le revisioni di chiusura e sono state saltate.

### 1.9.5 - Flusso degli eventi in diretta

Un flusso degli eventi in diretta del webhook in ingresso per client e schermi a parete che non possono interrogare, spento per impostazione predefinita, in sola lettura, con un limite di ascoltatori e un limite di tempo per ciascuno.

### 1.9.4 - Preset dell'IA

Una tabella di dodici servizi ospitati e sei server locali che parlano un protocollo che il monitor già conosce, un selettore nelle impostazioni dell'IA che compila l'indirizzo, il nome della variabile della chiave e un modello di esempio, server locali che funzionano senza chiave e gli indirizzi dei servizi principali letti nella loro documentazione pubblica.

### 1.9.3 - Rapporti programmati e registro di audit

Modelli di rapporto in HTML e Markdown (PDF facoltativo) con punteggio, avvisi principali e modifiche, un pianificatore e un registro di audit di sola aggiunta su chi ha fatto cosa e quando, senza alcun segreto dentro. Facoltativo, nella stessa versione: una vista «versione pronta / bloccata» con l'ultimo commit verde di ogni repository.

### 1.9.2 - Salute del repository e del team

Una vista di salute di ogni repository (CI, issue e pull request, sicurezza, prontezza per una versione, attività) e una del team con classifica, totali e filtri; pagine per entrambe con collegamenti diretti per schermi a parete. Facoltativo, nella stessa versione: un pannello di benchmark notturni rispetto a un budget (mediana rispetto a una base per classe di macchina) e un pannello di distinte dei materiali software e attestazioni di ogni versione.

### 1.9.1 - Sentinella di sicurezza

La terza sentinella: Dependabot, analisi del codice, analisi dei segreti, protezione dei rami, permessi dei workflow e proprietari del codice, con regole per tipo di segnale, lo stesso filtro nella scheda Avvisi e una penalità nel punteggio per gli avvisi critici aperti. Facoltativo, nella stessa versione: igiene dei workflow (azioni non fissate a un commit, job senza limite di tempo, workflow senza permessi o senza concorrenza, uso pericoloso di pull_request_target), sul verificatore di workflow che il progetto ha già.

### 1.9.0 - Un punteggio

Raccoglitori di metriche per account e per sentinella (tasso di successo, durata, tempo di ripristino, throughput), un motore di punteggio con soglie modificabili, un andamento rispetto al periodo precedente, istantanee conservate nell'archiviazione, un widget del punteggio con minigrafico, avvisi quando il punteggio scende e un verbo della riga di comando che lo stampa.

### 1.8.4 - Stabilizzazione

Nessuna grande funzione. Isolamento tra account, la pagina, l'archiviazione, accesso e ruoli, notifiche, un GitHub che a tratti cede, l'avvio dopo una migrazione interrotta, il ripristino dopo un'interruzione, un doctor più ampio, i punti che scrivono su GitHub, log senza token, una lista di controllo di sicurezza della modalità team e documenti coerenti con il comportamento. La serie arriva alla 1.8.9 solo se serve.

### 1.8.3 - Notifiche per utente

Preferenze per utente (canale, sentinella, livello minimo), un distributore che decide chi avvisare in base alle preferenze e ai ruoli, canali come semplici plugin e riepiloghi degli avvisi non ancora letti. Inoltre: un rapporto sul tempo che i job attendono in coda per ogni runner, e un job saltato per i percorsi che osserva è mostrato a parte da un job rosso.

### 1.8.2 - Immagine Docker ufficiale e modalità servizio

Un'immagine a più fasi con utente non privilegiato, volumi per dati e configurazione, variabili d'ambiente documentate, un esempio di compose con reverse proxy e TLS facoltativi, un'unità systemd per chi preferisce l'installazione classica e un controllo di salute profondo che fallisce se il supervisore o il ciclo di un account è bloccato. Una credenziale che GitHub revoca o lascia scadere segna solo quell'account come cieco, genera un allarme di sistema critico e si può sostituire senza riavviare il supervisore. Backup, aggiornamento e primo avvio come servizio sono documentati; la pagina dice se ascolta su questo computer, sulla rete o dietro un proxy; la riga di comando funziona contro un monitor remoto. L'edizione lite resta locale.

## Fatto nella 1.8.0

Tutto ciò che segue è stato consegnato nella serie 1.8 ed è provato; nulla si dà per dimostrato con servizi reali.

- Una nuova organizzazione delle cartelle (il pacchetto in `src/`, la pagina, gli esempi e le lingue in `assets/`), con uno strumento di migrazione che sposta una vecchia installazione piatta senza cancellare nulla.
- Un livello di archiviazione dietro un'unica interfaccia, con il supporto a file che mantiene la disposizione di `accounts/<id>/`, scritture atomiche e copie di sicurezza che qualsiasi supporto può ripristinare.
- Un supporto SQLite facoltativo (spento per impostazione predefinita), un database per account, migrazioni con versione, un tempo di attesa regolabile e strumenti per spostare lo stato tra il supporto a file e SQLite nei due sensi, prima con una simulazione.
- La cronologia delle modifiche è tradotta nelle otto lingue fino alla 1.0.0 e un test la mantiene completa.
- Conservazione e rotazione della cronologia (eventi e analisi per un numero di giorni, eliminare o archiviare, una riga di audit per passata, un avviso di dimensione nel doctor; lo stato delle sentinelle e la configurazione non vengono mai toccati).
- Modalità di rete: il freno di blocco torna ad agire prima di guardare il token, un reverse proxy dichiarato non è mai scambiato per questo computer, le letture remote delle impostazioni si limitano a ciò che un client remoto può cambiare e la guida alla distribuzione ha la ricetta completa.
- Il flusso per l'IA è ripulito campo per campo, passano solo indirizzi GitHub di forme chiuse e l'hook non consegna testo dei log, solo il repository, il workflow, il risultato e il collegamento.
- Le letture di identità sono sempre dell'utente, una lettura è giudicata su una lista bianca e il file del token del secondo account resta dentro la cartella degli account.
- Un test di fumo della pagina in un vero browser rende rossa la CI quando una scheda si rompe o una funzione è definita due volte.
- Una barra inferiore di una sola riga che dice solo ciò che i riquadri in alto non dicono, un riepilogo per gli strumenti di IA e un registro coerenti con il monitor in esecuzione, una pagina che segnala quando è fuori passo col monitor e un suono che si sblocca con un clic e sopravvive a un ricaricamento.
- Una lettura facoltativa dei repository tranquilli tramite GraphQL (spenta per impostazione predefinita) con la sua contabilità.
- L'avviso attivo a un'IA esterna (spento per impostazione predefinita, una prima conferma per fornitore, solo i campi oscurati di una lista chiusa, un tetto di chiamate e di costo all'ora, la chiave tramite il nome di una variabile, e l'IA non esegue mai un'azione).
- L'applicazione da terminale modifica elenchi e mappe.
- Modalità team (spenta per impostazione predefinita): utenti, ruoli (admin, maintainer, viewer) e sessioni conservati nell'archiviazione, una pagina di accesso, un token Bearer per i client che non sono un browser, errori JSON stabili e il ripristino di un amministratore dalla console di questo computer. La modalità individuale continua senza accesso e l'edizione lite non ne ha mai.
- Una pagina più viva: icone animate, spie di stato il cui movimento segue lo stato, risposte a passaggio, focus e clic; tutto si spegne con il movimento ridotto ed è leggero nell'edizione lite.

## Fatto nella 1.7.9

### Corretto

## Fatto nella 1.7.8

### Aggiunto

## Fatto nella 1.7.7

### Aggiunto

## Fatto nella 1.7.6

Il collegamento tra il monitor e uno strumento di IA: il feed coincide sempre con la pagina, ogni avviso dice perché è rosso, un flusso e tre strumenti MCP spingono le novità, un comando installa lo script di collegamento, la barra mostra se una IA è collegata e ogni file di stato è privato del suo proprietario.

## Fatto nella 1.7.5

La riga di comando prende il token di accesso con il suo nome, la modalità di rete è più sicura per impostazione predefinita (l'indirizzo del computer è nascosto alla rete, il vecchio indirizzo ?access= si può disattivare, le destinazioni di notifica della rete locale sono rifiutate, avviso sul semplice HTTP), gli orari per le persone usano il tuo fuso orario, un avviso si può silenziare finché l'elemento non cambia, e sono corretti i conteggi e i controlli che davano risposte sbagliate.

## Fatto nella 1.7.4

Una barra a piè di pagina con l'avviso più importante (e una finestra con tutti), la connessione, la quota, l'ultima lettura, la modalità, l'indirizzo e l'orologio; un pulsante a schermo intero; tabelle Repository e Cronologia che si ordinano per una o più colonne con le colonne a tua scelta; `bin/monitor_cli.py`, la riga di comando come client del monitor in esecuzione (`status`, `health`, `alerts`, `accounts`, `live`, `doctor`) con `--json` e codici di uscita stabili, e la sua guida in otto lingue; i registri delle modifiche controllati nell'ordine, il README del pacchetto senza cronologia dentro e le immagini ridisegnate.

## Fatto nella 1.7.3

Una seconda sentinella per issue e pull request (Collab, disattivata di default, sola lettura, orologio proprio), una scheda Avvisi con gli avvisi di tutte le sentinelle e filtro per origine e livello, silenziamenti locali che finiscono da soli (un avviso, una regola o una sentinella; `alerts.mute_hours`), l'etichetta che fa ignorare un elemento, `GET /api/alerts` e `GET /api/events`, una lista di controllo della vista dal vivo, una guida della sentinella Collab in otto lingue e le immagini ridisegnate.

## Fatto nella 1.7.2

L'intestazione con le sue cifre in un ordine che si legge e in una griglia che segue la larghezza; i controlli rapidi (solo i caldi, velocità, salute degli ecosistemi) fissi in alto a destra; Impostazioni, Guida e Informazioni solo nel pannello laterale; l'avviso di nuova versione fuori dall'intestazione; e i test che non lasciano più file accanto al codice.

## Fatto nella 1.7.1

Una pagina con pannello laterale (il logo, il selettore degli account, le sezioni in gruppi comprimibili, la guida) e sedici temi oltre ad auto, chiaro e scuro, quelli dello Studio del sistema di allarme; e la sentinella CI dietro un contratto (`BaseSentinel`, `Alert`, `SentinelRegistry`, `SentinelCI`), per poter aggiungere le prossime sentinelle senza che il monitor sappia cosa fa ciascuna. Ciò che si mostra e si decide non cambia.

## Fatto nella 1.7.0

Più account nell'edizione completa, ciascuno un monitor a sé sotto un supervisore (`accounts/<id>/`, `--accounts`, `--account`, `--migrate-accounts`), l'API degli account, un webhook per tutti, la pagina con un selettore e le schede di tutti gli account, le viste per indirizzo (`?view=` e `?chrome=0`) e la vista Live con lo stato del ricevitore webhook. L'edizione lite non cambia.

## Fatto nella 1.6.8

Il proxy HTTPS della 1.6.7 è verificato contro un proxy reale sulla porta 443 (`tools/manual_check_live.py proxy`, e test che percorrono un client su TLS, un reverse proxy e il monitor), le immagini sono rifatte con due nuove della modalità rete, e la cronologia delle modifiche è tradotta nelle altre sette lingue fino alla 1.6.3.

## Fatto nella 1.6.7

Un proxy HTTPS sulla porta 443 predefinita ora funziona con la modalità rete (`listen.proxy_public_host`, vuoto per impostazione predefinita: l'unico nome pubblico del proxy è accettato senza porta, solo con HTTPS, e si cambia solo dal computer stesso), e la cronologia delle modifiche è tradotta nelle altre sette lingue per la 1.6.7, la 1.6.6 e la 1.6.5.

## Fatto nella 1.6.6

Correzioni dopo la 1.6.5: la modalità rete ora funziona su HTTPS dalla pagina (la guardia di origine segue lo schema della sessione), ogni impostazione che lo schema contrassegna sicura si cambia solo dal computer stesso, `act` libera la sua esecuzione dopo Stop e chiude la sua pipe, una barra rossa nelle Impostazioni quando la modalità rete è in ascolto su tutte le interfacce, la sessione si può aprire con POST invece che con l'indirizzo, un contatore di guasti ingoiati in `--doctor` e Informazioni, `tools/make_screenshots.py` dice cosa fa e le immagini sono rifatte, e il registro delle modifiche è tradotto in otto lingue.

## Fatto nella 1.6.5

Una versione di integrità e sicurezza, senza grandi novità: un commit verde richiede il workflow obbligatorio del repository, un fetch fallito ferma l'avvio, il catalogo non può indicare uno strumento fuori dalla cartella degli strumenti né cambiare `dry_run`/`ref`, e un lotto senza verifica del commit registrata non viene più proposto alla firma; `act` resta nell'area di lavoro e Stop termina l'intero albero di processi e i container dell'esecuzione; la modalità rete può servire HTTPS, blocca i token errati e accetta solo IPv4; il webhook rifiuta replay e inondazioni; il server MCP sopravvive ai messaggi malformati; `max_per_hour` conta i messaggi; le impostazioni si salvano sotto blocco; il token conservato arriva solo a `gh`; `--doctor` segnala le combinazioni pericolose; il test di installazione pulita è una fase a sé del controllo di pubblicazione.

## Fatto nella 1.6.4

Test di isolamento dell'edizione lite e della demo, nessuna richiesta di rete quando il controllo versione è spento o l'installazione è isolata, un README che inizia con la scelta del lanciatore, `--doctor --json`, una barra persistente per la modalità rete, la Guida e i suoi documenti in otto lingue, e le funzioni opzionali (modalità rete, un token conservato dal monitor, azioni su GitHub, `act`, copia locale degli artefatti, runner self-hosted, OpenTelemetry, FinOps per etichette dei job); vedi il registro delle modifiche e `ADVANCED.md`.

## Prossimamente

Ciò che la 1.6.4 non ha raggiunto, e perché:

- **Più proprietari in un processo e in una pagina**: dalla 1.7.0 ogni account è un monitor a sé e la pagina li mostra affiancati, ma dentro un monitor un repository è ancora identificato solo dal nome, quindi due proprietari nello stesso monitor si mescolerebbero. Portarli in un solo processo richiede il proprietario in ogni identificatore (le letture, gli identificatori degli avvisi, le liste delle impostazioni, le sentinelle e la pagina); non si è potuto dimostrare senza i repository di due proprietari reali, quindi gli account della 1.7.0 restano il modo per tenerli separati.
- **Il rapporto di fatturazione con un login che può leggerlo**: la risposta reale per un login senza lo scope `user` è «non trovato» e il monitor torna alla stima (verificato); le cifre non sono state confrontate con un account di fatturazione.
- **I prezzi dei runner grandi** in `quotas.json` vengono dalla memoria del listino pubblico e sono segnati come non verificati; confrontali con la pagina di fatturazione di GitHub e modifica il file.
- **`gh copilot`**: le sue opzioni si verificano con `gh copilot -- --help`, che richiede la riga di comando di Copilot; qui non è installata, quindi restano non verificate.
- **Notifiche, webhook, Enterprise Server ed esempi di servizio** su servizi reali: `tools/manual_check_live.py` li controlla a mano; servono i tuoi canali e host, quindi qui non sono stati eseguiti.
- **L'applicazione da terminale** modifica le impostazioni semplici, le liste e le mappe di numeri e mostra lo stato della IA; la spiegazione di un singolo workflow rosso resta nella pagina.
- **Solo il proprietario può dimostrarle su un'installazione reale**: più account con la sentinella Collab su repository reali, una GitHub App e un secondo account di sola lettura con chiavi reali, e il proxy HTTPS con un certificato reale. Si verificano a mano (`tools/manual_check_live.py`) e non si danno per fatte.
- **Un controllo di nuova versione che scarichi o installi**: mai; il monitor si limita ad avvisare.

## Più avanti

- **Telemetria hardware dei runner** tramite un agente: oggi si legge solo un endpoint facoltativo di node exporter.
- **Una quarta fase** (plugin, automazione più ampia, IA avanzata) solo dopo diverse settimane di 2.0.x stabile e una decisione esplicita.

## Idee che richiedono prima una decisione

- Una versione PDF dei rapporti programmati (oggi HTML e Markdown).
- Una vista delle versioni pronte o bloccate, una per repository, nella scheda Team.
