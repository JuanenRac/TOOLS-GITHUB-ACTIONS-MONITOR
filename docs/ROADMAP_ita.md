# Roadmap

Idee che non sono entrate nella versione attuale, senza ordine promesso. Sono direzioni, non impegni; una issue o una pull request è il modo migliore per farne avanzare una.

## Fatto nella 1.6.5

Una versione di integrità e sicurezza, senza grandi novità: un commit verde richiede il workflow obbligatorio del repository, un fetch fallito ferma l'avvio, il catalogo non può indicare uno strumento fuori dalla cartella degli strumenti né cambiare `dry_run`/`ref`, e un lotto senza verifica del commit registrata non viene più proposto alla firma; `act` resta nell'area di lavoro e Stop termina l'intero albero di processi e i container dell'esecuzione; la modalità rete può servire HTTPS, blocca i token errati e accetta solo IPv4; il webhook rifiuta replay e inondazioni; il server MCP sopravvive ai messaggi malformati; `max_per_hour` conta i messaggi; le impostazioni si salvano sotto blocco; il token conservato arriva solo a `gh`; `--doctor` segnala le combinazioni pericolose; il test di installazione pulita è una fase a sé del controllo di pubblicazione.

## Fatto nella 1.6.4

Test di isolamento dell'edizione lite e della demo, nessuna richiesta di rete quando il controllo versione è spento o l'installazione è isolata, un README che inizia con la scelta del lanciatore, `--doctor --json`, una barra persistente per la modalità rete, la Guida e i suoi documenti in otto lingue, e le funzioni opzionali (modalità rete, un token conservato dal monitor, azioni su GitHub, `act`, copia locale degli artefatti, runner self-hosted, OpenTelemetry, FinOps per etichette dei job); vedi il registro delle modifiche e `ADVANCED.md`.

## Prossimamente

Ciò che la 1.6.4 non ha raggiunto, e perché:

- **Deciso, non fatto nella 1.6.5** (la versione è limitata a integrità e sicurezza): l'avviso attivo a una IA esterna (spento di default, una prima conferma per fornitore, solo i campi già filtrati dell'elenco chiuso, un tetto di chiamate e di costo all'ora, la chiave tramite il nome di una variabile d'ambiente, e l'IA non esegue mai un'azione) con la sua variante di comando in uscita (elenco chiuso, senza shell); nuove schermate (`tools/make_screenshots.py --web` non ha prodotto output sulla macchina di pubblicazione, quindi si fanno a mano: avvia `--demo`, apri la pagina e salva una cattura per scheda); e i repository di più proprietari in una sola pagina.
- **Più proprietari in una pagina**: il monitor identifica un repository solo dal nome (esecuzioni, sentinella, cache, esportazioni), quindi due proprietari con un repository dello stesso nome si mescolerebbero. Le organizzazioni sono elencate e ognuna è controllata da un monitor proprio (`github_owner`). In una pagina servirebbe il proprietario in ogni identificatore.
- **Il rapporto di fatturazione con un login che può leggerlo**: la risposta reale per un login senza lo scope `user` è «non trovato» e il monitor torna alla stima (verificato); le cifre non sono state confrontate con un account di fatturazione.
- **I prezzi dei runner grandi** in `quotas.json` vengono dalla memoria del listino pubblico e sono segnati come non verificati; confrontali con la pagina di fatturazione di GitHub e modifica il file.
- **`gh copilot`**: le sue opzioni si verificano con `gh copilot -- --help`, che richiede la riga di comando di Copilot; qui non è installata, quindi restano non verificate.
- **Notifiche, webhook, Enterprise Server ed esempi di servizio** su servizi reali: `tools/manual_check_live.py` li controlla a mano; servono i tuoi canali e host, quindi qui non sono stati eseguiti.
- **L'applicazione da terminale** modifica le impostazioni semplici e mostra lo stato dell'IA; la spiegazione di un singolo workflow rosso e la modifica di liste e mappe restano nella pagina.
- **Un controllo di nuova versione che scarichi o installi**: mai; il monitor si limita ad avvisare.

## Più avanti

- **Altri adattatori di notifica**: ntfy, Microsoft Teams ed e-mail tramite un relay locale.
- **Più account in una pagina**: oggi ogni account gira nel proprio monitor.
- **Telemetria hardware dei runner** tramite un agente: oggi si legge solo un endpoint opzionale di node exporter.

## Idee che richiedono prima una decisione

- Una schermata di login per la pagina, così la modalità rete non richiede di digitare una volta il token di accesso. Oggi la risposta è il token di accesso e, per Internet, un reverse proxy con autenticazione (vedi `monitor/docs/DEPLOYMENT.md`).
- Leggere nella pagina i log di un passaggio fallito, con la stessa pulizia dell'assistente IA.
