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
- **HTTPS.** Con il tuo certificato e la tua chiave (`listen.tls_cert_file`, `listen.tls_key_file`) il monitor serve HTTPS da sé; dietro un proxy che lo fa per te, imposta `listen.secure_cookie`. In entrambi i casi il browser invia `Origin: https://host:porta` a ogni modifica, e la guardia accetta esattamente lo schema della sessione (l'altro schema, un altro host, un'altra porta o un'origine malformata vengono rifiutati). L'indirizzo usato dal browser deve contenere la porta del monitor, tranne dietro un proxy HTTPS sulla porta 443 predefinita che inoltra `Host` e `Origin` senza porta: indica il suo nome pubblico in `listen.proxy_public_host` (solo un nome host, vuoto per impostazione predefinita). Conta solo con HTTPS, solo quel nome è accettato senza porta e si cambia solo dallo stesso computer.
- **Aprire la sessione con POST.** Invece dell'indirizzo con `?access=` puoi inviare `POST /api/access` con il JSON `{"token": "..."}`: il token resta fuori dalla barra degli indirizzi, dalla cronologia e dai registri, e il cookie torna nella risposta. L'indirizzo con `?access=` è obsoleto: funziona ancora per impostazione predefinita (nulla di già configurato si rompe) e solo con un `GET`, ma il token resta nella cronologia, nei registri e nel `Referer`, e il monitor risponde con un'intestazione `Deprecation`. Disattiva `listen.query_access` per rifiutarlo e aprire la sessione solo con `POST /api/access` o l'intestazione `X-Monitor-Access`. Una barra rossa in cima alle Impostazioni avvisa quando `listen.host` è `0.0.0.0`. Ogni impostazione che lo schema contrassegna come sicura (non solo `listen.*`, `github_token.*`, `act.*` e `github_actions.*`: anche webhook, azioni dell'IA, notifiche, OpenTelemetry, mirror, runner e uscite) si cambia solo dal computer stesso.
- **Primi passi per ascoltare sulla rete.** Disattiva prima `listen.query_access` (così il token non viaggia mai in un indirizzo, una cronologia o un log; apri la sessione con `POST /api/access` o con l'intestazione) e metti davanti HTTPS (un certificato in `listen.tls_cert_file` o un proxy HTTPS) o una VPN. La console lo ripete all'avvio della modalità di rete finché il vecchio indirizzo è ancora accettato.

## Modalità team: utenti e ruoli

Disattivata di default: una persona usa il monitor senza login. Con `auth.enabled` attivo (senza riavvio) non cambia nulla finché non esiste il primo amministratore. L'edizione lite non ha mai un login.

- **Primo amministratore.** Apri `/login` sul computer che esegue il monitor e crealo (solo da quel computer e una sola volta; una richiesta che arriva da un proxy viene rifiutata). Oppure da console: `python -m github_actions_monitor.security.auth_cli create-admin NOME --password-env VAR` (la password non compare mai nella riga di comando). Poi la pagina chiede il login; `reset-password` e `revoke` dello stesso strumento recuperano una password di amministratore persa.
- **Ruoli.** `viewer` legge (ogni GET); `maintainer` silenzia e conferma anche gli avvisi e cambia la modalità di lavoro; `admin` modifica anche impostazioni, utenti e tutto ciò che può raggiungere GitHub o l'esterno. Una rotta non elencata è chiusa a tutti tranne che a un admin. Ogni utente ha anche l'elenco degli account che può vedere (gli admin vedono tutto): un altro account richiesto con `?account=` o `X-Account-Id` risponde 403 `account_scope`, nell'API e nelle esportazioni.
- **Sessioni.** Il browser riceve il cookie `monitor_session` (HttpOnly, SameSite=Strict, Secure con HTTPS) e un token CSRF (`X-CSRF-Token`, restituito dal login e da `/api/auth/me`) che ogni POST deve inviare. Uno script o un'app usa `POST /api/auth/login` con `{"client": "api"}` e invia il token ricevuto come `Authorization: Bearer msn_...` (`auth.allow_bearer` lo disattiva). Il token monouso della pagina (`session_guard`) resta richiesto oltre alla sessione.
- **Password.** Conservate solo come hash scrypt con salt, di almeno `auth.min_length` caratteri. Dopo `auth.max_failed_logins` password errate l'utente è bloccato per `auth.lockout_minutes`, e ogni indirizzo ha il proprio limite di richieste. Una nuova password, ruolo o stato chiude le sessioni di quell'utente; resta sempre almeno un amministratore attivo.
- **Endpoint.** `/api/auth/login`, `logout`, `me`, `bootstrap`, `password`; per gli admin `/api/auth/users` (con `/update`, `/delete`, `/revoke`) e `/api/auth/audit`. Gli errori sono JSON con codice stabile: `{"error": "...", "code": "..."}`.
- **Audit.** `auth_audit.jsonl` (file privato; si conserva una copia precedente) registra accessi, blocchi, richieste rifiutate e modifiche degli utenti; mai una password, un hash o un token. `auth.audit` lo disattiva.
- **Rischio.** Con HTTP non cifrato in una rete, cookie e password viaggiano in chiaro: usa HTTPS o una VPN, come per la modalità di rete.

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

`listen.trusted_proxy` (disattivato per impostazione predefinita): solo se un reverse proxy TUO sullo stesso computer è l'unico ingresso. I tentativi falliti vengono allora contati sull'ultimo indirizzo di `X-Forwarded-For` (quello che aggiunge il tuo proxy) e non sul proxy; una richiesta che passa da un proxy non è comunque mai trattata come questo computer. Se qualcun altro può raggiungere direttamente il monitor, lascialo spento.
