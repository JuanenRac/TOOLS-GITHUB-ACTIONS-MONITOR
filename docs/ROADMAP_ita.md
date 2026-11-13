# Roadmap

Idee che non sono entrate nella versione attuale, senza ordine promesso. Sono direzioni, non impegni; una issue o una pull request è il modo migliore per farne avanzare una.

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

- **Deciso, non fatto nella 1.6.6**: l'avviso attivo a un'IA esterna (spento di default, una prima conferma per fornitore, solo i campi già filtrati dell'elenco chiuso, un tetto di chiamate e di costo all'ora, la chiave tramite il nome di una variabile d'ambiente, e l'IA non esegue mai un'azione) con la sua variante di comando in uscita (elenco chiuso, senza shell); e i repository di più proprietari in una pagina (il monitor identifica un repository solo dal nome, quindi serve il proprietario in ogni identificatore; è la base di più account). Ciascuno è una funzione a sé con il suo progetto e i suoi test, quindi la 1.6.6 ha chiuso prima le correzioni.
- **Le voci più vecchie del registro delle modifiche nelle altre sette lingue**: l'Aiuto mostra la cronologia in ogni lingua, e dalla 1.6.8 alla 1.6.3 sono tradotte; la 1.6.2 e le precedenti mantengono il testo inglese sotto un avviso tradotto e saranno tradotte versione per versione, dalla più recente alla più vecchia.
- **Più proprietari in un processo e in una pagina**: dalla 1.7.0 ogni account è un monitor a sé e la pagina li mostra uno accanto all'altro, ma dentro un monitor un repository si identifica ancora solo con il suo nome, quindi due proprietari nello stesso monitor si mescolerebbero. Gli account della 1.7.0 sono il modo per tenerli separati; portarli in un solo processo, con il proprietario in ogni identificatore, è ciò che resta.
- **Il rapporto di fatturazione con un login che può leggerlo**: la risposta reale per un login senza lo scope `user` è «non trovato» e il monitor torna alla stima (verificato); le cifre non sono state confrontate con un account di fatturazione.
- **I prezzi dei runner grandi** in `quotas.json` vengono dalla memoria del listino pubblico e sono segnati come non verificati; confrontali con la pagina di fatturazione di GitHub e modifica il file.
- **`gh copilot`**: le sue opzioni si verificano con `gh copilot -- --help`, che richiede la riga di comando di Copilot; qui non è installata, quindi restano non verificate.
- **Notifiche, webhook, Enterprise Server ed esempi di servizio** su servizi reali: `tools/manual_check_live.py` li controlla a mano; servono i tuoi canali e host, quindi qui non sono stati eseguiti.
- **L'applicazione da terminale** modifica le impostazioni semplici e mostra lo stato dell'IA; la spiegazione di un singolo workflow rosso e la modifica di liste e mappe restano nella pagina.
- **Un controllo di nuova versione che scarichi o installi**: mai; il monitor si limita ad avvisare.

## Più avanti

- **Altri adattatori di notifica**: ntfy, Microsoft Teams ed e-mail tramite un relay locale.
- **Più account in una pagina**: fatto nella 1.7.0, ogni account nel proprio monitor sotto un supervisore.
- **Telemetria hardware dei runner** tramite un agente: oggi si legge solo un endpoint opzionale di node exporter.

## Idee che richiedono prima una decisione

- Una schermata di login per la pagina, così la modalità rete non richiede di digitare una volta il token di accesso. Oggi la risposta è il token di accesso e, per Internet, un reverse proxy con autenticazione (vedi `monitor/docs/DEPLOYMENT.md`).
- Leggere nella pagina i log di un passaggio fallito, con la stessa pulizia dell'assistente IA.
