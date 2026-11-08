# Roadmap

Idee che non sono entrate nella versione attuale, senza ordine promesso. Sono direzioni, non impegni; una issue o una pull request è il modo migliore per farne avanzare una.

## Fatto nella 1.6.4

Test di isolamento dell'edizione lite e della demo, nessuna richiesta di rete quando il controllo versione è spento o l'installazione è isolata, un README che inizia con la scelta del lanciatore, `--doctor --json`, una barra persistente per la modalità rete, la Guida e i suoi documenti in otto lingue, e le funzioni opzionali (modalità rete, un token conservato dal monitor, azioni su GitHub, `act`, copia locale degli artefatti, runner self-hosted, OpenTelemetry, FinOps per etichette dei job); vedi il registro delle modifiche e `ADVANCED.md`.

## Prossimamente

Ciò che la 1.6.4 non ha raggiunto, e perché:

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
