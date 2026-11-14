# Roadmap

Idee che non sono entrate nella versione attuale, senza ordine promesso. Sono direzioni, non impegni; una issue o una pull request è il modo migliore per farne avanzare una.

## Nella 1.8.0 (la prossima versione)

Tutto ciò che segue è scritto e provato; o è già nel ramo principale o attende in una pull request. Nulla è dato per dimostrato su servizi reali (vedi «Prossimi passi»).

### Già nel ramo principale

- Una nuova organizzazione delle cartelle (il pacchetto in `src/`, la pagina, gli esempi e le lingue in `assets/`), con uno strumento di migrazione che sposta una vecchia installazione piatta senza cancellare nulla.
- Un livello di archiviazione dietro un'unica interfaccia, con il supporto a file che mantiene la disposizione di `accounts/<id>/`, scritture atomiche e copie di sicurezza che qualsiasi supporto può ripristinare.
- Un supporto SQLite facoltativo (spento per impostazione predefinita), un database per account, migrazioni con versione, un tempo di attesa regolabile e strumenti per spostare lo stato tra il supporto a file e SQLite nei due sensi, prima con una simulazione.
- La cronologia delle modifiche è tradotta nelle otto lingue fino alla 1.0.0 e un test la mantiene completa.
- Conservazione e rotazione della cronologia (eventi e analisi per un numero di giorni, eliminare o archiviare, una riga di audit per passata, un avviso di dimensione nel doctor; lo stato delle sentinelle e la configurazione non vengono mai toccati).

### Finito e in attesa di essere unito

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

### Ancora in rifinitura

- Silenzi che ricordano chi li ha impostati (richiede la modalità team).

## Previsto, in quest'ordine

Ogni versione porta tutto quello del suo tratto del piano: nulla resta appeso a una versione precedente e nulla è rimandato alla successiva. Dopo la 1.8.3 e dopo la 1.9.3 il prodotto passa una revisione indipendente e i suoi rilievi si chiudono nella versione di stabilizzazione seguente. 1.8.1 è una versione correttiva della 1.8.0: il riquadro «caricamento dei repository» scompare con l'ultimo repository e il ricaricamento della pagina ottiene subito i dati.

### 1.8.2 - Immagine Docker ufficiale e modalità servizio

Un'immagine a più fasi con utente non privilegiato, volumi per dati e configurazione, variabili d'ambiente documentate, un esempio di compose con reverse proxy e TLS facoltativi, un'unità systemd per chi preferisce l'installazione classica e un controllo di salute profondo che fallisce se il supervisore o il ciclo di un account è bloccato. Una credenziale che GitHub revoca o lascia scadere segna solo quell'account come cieco, genera un allarme di sistema critico e si può sostituire senza riavviare il supervisore. Backup, aggiornamento e primo avvio come servizio sono documentati; la pagina dice se ascolta su questo computer, sulla rete o dietro un proxy; la riga di comando funziona contro un monitor remoto. L'edizione lite resta locale. Inoltre: un rapporto sul tempo che i job attendono in coda per ogni runner.

### 1.8.3 - Notifiche per utente

Preferenze per utente (canale, sentinella, livello minimo), un distributore che decide chi avvisare in base alle preferenze e ai ruoli, canali come semplici plugin e riepiloghi degli avvisi non ancora letti. Inoltre: un job saltato per i percorsi che osserva è mostrato a parte da un job rosso.

### 1.8.4 - Stabilizzazione

Nessuna grande funzione. Isolamento tra account, la pagina, l'archiviazione, accesso e ruoli, notifiche, un GitHub che a tratti cede, l'avvio dopo una migrazione interrotta, il ripristino dopo un'interruzione, un doctor più ampio, i punti che scrivono su GitHub, log senza token, una lista di controllo di sicurezza della modalità team e documenti coerenti con il comportamento. La serie arriva alla 1.8.9 solo se serve.

### 1.9.0 - Un punteggio

Raccoglitori di metriche per account e per sentinella (tasso di successo, durata, tempo di ripristino, throughput), un motore di punteggio con soglie modificabili, un andamento rispetto al periodo precedente, istantanee conservate nell'archiviazione, un widget del punteggio con minigrafico, avvisi quando il punteggio scende e un verbo della riga di comando che lo stampa.

### 1.9.1 - Sentinella di sicurezza

La terza sentinella: Dependabot, analisi del codice, analisi dei segreti, protezione dei rami, permessi dei workflow e proprietari del codice, con regole per tipo di segnale, lo stesso filtro nella scheda Avvisi e una penalità nel punteggio per gli avvisi critici aperti. Facoltativo, nella stessa versione: igiene dei workflow (azioni non fissate a un commit, job senza limite di tempo, workflow senza permessi o senza concorrenza, uso pericoloso di pull_request_target), sul verificatore di workflow che il progetto ha già.

### 1.9.2 - Salute del repository e del team

Una vista di salute di ogni repository (CI, issue e pull request, sicurezza, prontezza per una versione, attività) e una del team con classifica, totali e filtri; pagine per entrambe con collegamenti diretti per schermi a parete. Facoltativo, nella stessa versione: un pannello di benchmark notturni rispetto a un budget (mediana rispetto a una base per classe di macchina) e un pannello di distinte dei materiali software e attestazioni di ogni versione.

### 1.9.3 - Rapporti programmati e registro di audit

Modelli di rapporto in HTML e Markdown (PDF facoltativo) con punteggio, avvisi principali e modifiche, un pianificatore e un registro di audit di sola aggiunta su chi ha fatto cosa e quando, senza alcun segreto dentro. Facoltativo, nella stessa versione: una vista «versione pronta / bloccata» con l'ultimo commit verde di ogni repository.

### 1.9.4 - Stabilizzazione della terza fase

La stessa chiusura della 1.8.4 per punteggio, sentinella di sicurezza, viste di salute, rapporti e registro di audit; il costo in chiamate API con tre sentinelle attive; un punteggio che resta coerente quando una sentinella è spenta.

### 2.0.0 - Maturità

Una versione maggiore che ripulisce il debito tecnico e congela le interfacce pubbliche: sentinelle, archiviazione, avvisi, lo schema degli eventi e l'API di lettura, con una suite di test di contratto che i client possono eseguire contro qualsiasi versione. Una guida per ogni modo di usare il prodotto (lite, individuale, servizio, team) e un riferimento di impostazioni, eventi, metriche e API. Dalla 2.0.1 in poi c'è un cuscinetto per ciò che emerge solo con un uso reale prolungato.

I workflow del monitor stesso rispettano ciò che la sentinella di igiene chiederà agli altri: azioni fissate a un commit, permessi minimi e un limite di tempo su ogni job.

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

Una barra a piè di pagina con l'avviso più importante (e una finestra con tutti), la connessione, la quota, l'ultima lettura, la modalità, l'indirizzo e l'orologio; un pulsante a schermo intero; tabelle Repository e Cronologia che si ordinano per una o più colonne con le colonne a tua scelta; `monitor_cli.py`, la riga di comando come client del monitor in esecuzione (`status`, `health`, `alerts`, `accounts`, `live`, `doctor`) con `--json` e codici di uscita stabili, e la sua guida in otto lingue; i registri delle modifiche controllati nell'ordine, il README del pacchetto senza cronologia dentro e le immagini ridisegnate.

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

- **Altri adattatori di notifica**: ntfy, Microsoft Teams ed e-mail tramite un relay locale.
- **Più account in una pagina**: fatto nella 1.7.0, ogni account nel proprio monitor sotto un supervisore.
- **Telemetria hardware dei runner** tramite un agente: oggi si legge solo un endpoint opzionale di node exporter.

## Idee che richiedono prima una decisione

- Leggere nella pagina i log di un passaggio fallito, con la stessa pulizia dell'assistente IA.
