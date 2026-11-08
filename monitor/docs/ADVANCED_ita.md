<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Funzioni avanzate (tutte spente di default)

Tutto in questa pagina è **spento finché non lo attivi** in *Impostazioni > Avanzate* (o in `actions_monitor.json`), e le chiavi che decidono chi può raggiungere il monitor o cosa può fare su GitHub sono segnate come opzioni di sicurezza. Attiva solo ciò che ti serve.

## Ascolto in rete

Di default la pagina risponde solo su `127.0.0.1`. Con `listen.network` attivo (serve il riavvio) ascolta anche su `listen.host`: un indirizzo privato di questo computer, oppure `0.0.0.0` per tutte le interfacce. Un indirizzo pubblico viene rifiutato.

- **Ogni richiesta richiede il token di accesso** (cookie, intestazione `X-Monitor-Access` o `Authorization: Bearer`). Il token è il valore della variabile d'ambiente indicata in `listen.token_env` (16 caratteri o più); senza, a ogni avvio se ne crea uno casuale mostrato una volta nella console. Apri una volta l'indirizzo stampato lì: imposta il cookie e passa all'indirizzo pulito.
- Il token monouso della pagina è forzato, la pagina mostra una barra rossa su ogni scheda finché la modalità è attiva, e le chiavi di `listen.*`, `github_token.*`, `act.*` e `github_actions.*` si cambiano solo dal computer stesso.
- `listen.allowed_hosts` elenca i nomi con cui si può aprire la pagina (protezione dal DNS rebinding).
- **Rischi.** Il traffico è HTTP in chiaro: chi può leggere la tua rete può leggere token e dati. Usalo solo su una rete fidata, o metti davanti un reverse proxy con HTTPS (vedi `DEPLOYMENT.md`). Non esporlo mai a Internet. L'edizione lite non ascolta mai oltre questo computer.

## Un token GitHub conservato dal monitor

Il predefinito resta il tuo login `gh`. Con `github_token.enabled` attivo puoi incollare un token in Impostazioni > Avanzate: è conservato nell'archivio sicuro del sistema (DPAPI di Windows, Portachiavi di macOS, Secret Service di Linux) e, solo se manca, in un file con permessi 600 (la pagina lo dice). Non viene mai scritto in `actions_monitor.json`, in un log, nel pannello Informazioni né nel testo per il supporto, e raggiunge `gh` solo tramite l'ambiente del processo. Il pulsante **Elimina il token** lo rimuove ovunque.

## Azioni su GitHub

Con `github_actions.enabled` attivo, il monitor può rilanciare un'esecuzione fallita (`rerun_failed`, `rerun_run`, `rerun_job`), annullare un'esecuzione (`cancel`), chiudere una issue o una pull request (`close_issue`, `close_pr`) e unirne una (`merge_pr`, con `github_actions.merge_method`). Si possono usare solo i nomi in `github_actions.allowed` (di default `rerun_failed` e `cancel`). **Ogni azione è confermata a parte**: la pagina mostra esattamente cosa sarà inviato (metodo ed endpoint) e non invia nulla finché non confermi quel piano con il token monouso. Il token di GitHub richiede il permesso (`workflow` per le esecuzioni, `repo` per issue e pull request; altrimenti si mostra il rifiuto di GitHub). Ogni tentativo è scritto in `github_actions_log.jsonl`. L'assistente IA non ha modo di avviarne alcuna.

## Eseguire un workflow qui con act

Con `act.enabled` attivo e voci `repository:file.yml:evento` in `act.allowed` (tutte e tre esatte), un pulsante esegue `act` sul clone locale dopo la conferma della riga di comando esatta. Non vengono forniti segreti reali (file di segreti, variabili, ambiente e input vuoti, e un ambiente minimo senza token), l'output compare man mano, un'esecuzione alla volta, con il limite di tempo `act.timeout_seconds`, e puoi fermarla.

## Copia locale degli artefatti

Con `mirror.enabled` attivo e una `mirror.folder` su questo computer, gli artefatti delle esecuzioni concluse vi sono copiati (`mirror.max_per_cycle` per ciclo, `mirror.max_mb` per la cartella, `mirror.keep_days` di conservazione), una volta ciascuno, con nomi ripuliti dentro la cartella.

## Runner self-hosted

Con `runners.enabled` attivo, Impostazioni > Avanzate mostra ogni runner come libero, occupato o offline. Disco e carico compaiono solo per i runner elencati in `runners.metrics` ({nome: indirizzo di un node exporter su questo computer o un indirizzo privato}).

## OpenTelemetry

Con `otlp.enabled` attivo e un `otlp.endpoint` (HTTPS, o HTTP su questo computer), le esecuzioni concluse escono come tracce e le cifre dell'intestazione come metriche (OTLP/HTTP con JSON), ogni esecuzione una volta. Si inviano solo repository, workflow, branch, evento, esito e durata.

## Organizzazioni e costi

- `organizations.discover` elenca le organizzazioni del login in Impostazioni > Base. Per controllarne una, avvia un secondo monitor con `github_owner` impostato su di essa.
- `finops.jobs_per_cycle` maggiore di 0 legge le etichette dei job di altrettante esecuzioni private concluse per ciclo, così i minuti usano il moltiplicatore giusto (Linux, Windows, macOS e i runner grandi di `quotas.json`) invece di un sistema presunto. Con il rapporto di fatturazione attivo (`quota.billing_api`) compaiono anche i dollari di Codespaces e Packages, lo spazio in uso e il prezzo dei minuti oltre quelli inclusi.

## Verificare sui servizi reali

`python tools/manual_check_live.py` (nel repository) legge gli scope del tuo token, il rapporto di fatturazione, le organizzazioni, i runner e le opzioni di `gh copilot`, e chiede a un monitor in esecuzione di inviare un messaggio di prova sui tuoi canali. Non chiede mai un segreto.

## Note di sicurezza (da leggere prima di attivare qualcosa)

- **Modalità rete**: usala solo su una rete fidata. Il token di accesso non sostituisce la cifratura; in HTTP semplice token e dati viaggiano in chiaro. Metti davanti un proxy HTTPS (e attiva `listen.secure_cookie`) oppure dai al monitor il tuo certificato e la sua chiave (`listen.tls_cert_file`, `listen.tls_key_file`): allora serve HTTPS da sé (TLS 1.2 o superiore) e non parte se non può usare i file. Preferisci UN indirizzo privato di questo computer a tutte le interfacce. Sono accettati solo indirizzi IPv4. Dopo la prima visita la barra degli indirizzi viene ripulita dal token e il cookie è HttpOnly, SameSite=Strict (e Secure con HTTPS). Un indirizzo che invia `listen.max_failed_attempts` token errati in un minuto viene rifiutato per cinque minuti. `/metrics` e `dashboard.json` elencano i tuoi repository: in modalità rete richiedono anch'essi il token.
- **Azioni su GitHub**: **spente di default, una conferma per azione, elenco chiuso** (rilanciare un'esecuzione o un job, annullare, chiudere una issue o una pull request, unire una pull request se la includi). Eliminare branch o repository, segreti e impostazioni **non** ci sono. L'IA può proporre un elenco più piccolo (`rerun_failed`, `rerun_run`, `close_issue`) e non unisce mai.
- **act**: spento di default, ogni esecuzione confermata, elenco chiuso `repository:file:evento`, nessun segreto reale. Il clone deve essere una cartella reale dentro l'area di lavoro: una cartella che è un collegamento altrove viene rifiutata salvo `act.allow_symlinks` attivo. Il limite di tempo e Stop terminano l'intero albero di processi avviato dall'esecuzione e rimuovono i container `act-` che ha creato.
- **Il tuo token** è conservato nell'archivio del sistema se esiste; il file semplice (permessi 600) è l'archivio più debole. Va solo a `gh`, mai ad `act` né ai tuoi comandi. `--doctor` mostra l'archivio, mai il token.
- **Combinazioni da evitare** (`--doctor` le nomina): modalità rete su tutte le interfacce; azioni dell'IA che eseguono con la modalità rete attiva; `act` con la modalità rete attiva; il token in un file semplice.
- Il server MCP parla solo su ingresso e uscita standard; non metterlo mai dietro una porta di rete.
