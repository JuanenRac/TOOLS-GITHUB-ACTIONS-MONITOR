<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](WEBHOOK.md) | [🇪🇸 Español](WEBHOOK_spa.md) | [🇫🇷 Français](WEBHOOK_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](WEBHOOK_deu.md) | [🇨🇳 简体中文](WEBHOOK_zho.md) | [🇯🇵 日本語](WEBHOOK_jpn.md) | [🇵🇹 Português](WEBHOOK_por.md)

# Webhook in ingresso

Facoltativo e **spento per impostazione predefinita**. Permette a GitHub di avvisare il monitor che qualcosa è cambiato, così il repository viene aggiornato nel ciclo successivo invece di attendere la prossima interrogazione.

## Cosa fa (solo aggiornare)

Un evento accettato segna soltanto il repository indicato per un aggiornamento nel ciclo successivo. Non si scrive nulla su GitHub né su disco, nessun testo dell'evento viene conservato o mostrato, e si accettano solo i repository già osservati dal monitor. Eventi compresi: `workflow_run`, `workflow_job`, `push`, `release`, `check_run`, `check_suite` e `ping`; ogni altro riceve `202` ed è ignorato.

## Sicurezza

- Il monitor continua ad ascoltare solo su `127.0.0.1`. GitHub può raggiungerlo solo tramite un tunnel che crei di proposito; lo strumento non ne apre mai uno.
- Spento finché `webhook.enabled` non è attivo **e** il segreto condiviso (32 caratteri o più) non è nella variabile d'ambiente indicata da `webhook.secret_env` (`MONITOR_WEBHOOK_SECRET` per impostazione predefinita; `MONITOR_WEBHOOK_SECRET_FILE` può indicare un file la cui prima riga è il segreto, come i segreti di un container). Il segreto non viene mai scritto in `actions_monitor.json`, mostrato, registrato né ereditato dai programmi che il monitor avvia; la scheda Impostazioni dice solo se è definito. Il vecchio modo (un `secret` nel file) viene letto solo se `webhook.allow_config_secret` è vero, e la vista Dal vivo avvisa finché lo si usa.
- Ogni richiesta deve portare `X-Hub-Signature-256: sha256=<hmac>`, calcolato con quel segreto e confrontato in tempo costante; ogni altra riceve `401` e nulla del contenuto viene guardato prima di verificare la firma.
- Un corpo oltre 256 KB riceve `413`, prima di calcolare qualsiasi cosa.
- Le liste sono chiuse: si agisce solo su `workflow_run`, `workflow_job`, `check_run`, `push`, `release`, `check_suite` e `ping`, di un evento si conservano solo campi brevi e validati (mai un messaggio di commit né testo libero), e tutto il resto riceve `202` ed è scartato.

## Come attivarlo

1. Crea un segreto di 32 o più caratteri casuali, per esempio `python -c "import secrets; print(secrets.token_hex(32))"`.
2. Dallo al monitor tramite il suo ambiente, mai tramite il file: `$env:MONITOR_WEBHOOK_SECRET = "<il segreto>"` in PowerShell prima di avviare il monitor, `export MONITOR_WEBHOOK_SECRET=...` in una shell, `Environment=` o `EnvironmentFile=` (un file leggibile solo da te) in un servizio, `-e` o un file di segreto indicato da `MONITOR_WEBHOOK_SECRET_FILE` in un container.
3. Attiva il ricevitore (Impostazioni > Webhook in ingresso > Ricevitore attivo, o `"webhook": {"enabled": true}` in `actions_monitor.json`) e riavvia il monitor.
4. Rendi raggiungibile l'indirizzo: GitHub non raggiunge `127.0.0.1`. Usa un tunnel che crei di proposito (un indirizzo HTTPS che termina con `/api/webhook`) oppure, su questo computer, `gh webhook forward` verso `http://127.0.0.1:PORTA/api/webhook` (vedi la documentazione della CLI di GitHub per dargli lo stesso segreto senza scriverlo sulla riga di comando).
5. In GitHub apri il repository (o l'organizzazione) > Settings > Webhooks > Add webhook. **Payload URL**: l'indirizzo del tuo tunnel che termina con `/api/webhook`. **Content type**: `application/json`. **Secret**: lo stesso segreto. **SSL verification**: attiva. **Events**: «Let me select individual events», poi Workflow runs e Workflow jobs, e facoltativamente Check runs, Pushes e Releases. **Active**: attivo. Un webhook di un'organizzazione copre tutti i suoi repository; il monitor ignora quelli che non sorveglia.
6. Verifica: in GitHub, Recent deliveries deve mostrare `200` per il primo `ping`; nel monitor la vista Dal vivo mostra il ricevitore attivo, i contatori e la copertura.

## Eventi in tempo reale

- Con `webhook.record_events` attivo (predefinito), un evento `workflow_run` firmato aggiorna subito l'elenco dei run di quel repository, senza prima leggere GitHub: il run mantiene il tipo di evento che aveva già, quindi il suo colore non cambia, e il repository viene riletto nel ciclo successivo per confermarlo (una lettura per evento accettato). Un evento `workflow_job` porta anche il tempo in coda e quello di ogni passo per le analisi.
- Si conservano solo brevi campi validati (workflow, run, stato, conclusione, branch, commit corto, link al run, durate); mai il messaggio del commit né l'autore. Si conservano anche i nomi brevi di workflow, branch, job e passaggi, su una riga e ripuliti come ogni testo che esce dal monitor. Gli ultimi `webhook.live_events_keep` eventi si leggono su `GET /api/live-events` (in modalità rete, con il token di accesso).
- Con `webhook.record_events` attivo (predefinito), un evento `workflow_run` firmato aggiorna subito l'elenco dei run di quel repository, senza leggere GitHub: il repository viene comunque riletto nel ciclo successivo (l'evento è la notizia, la lettura è la prova): una consegna mostra subito il cambiamento ma non risparmia una lettura. Un evento `workflow_job` porta anche il tempo in coda e quello di ogni passo per le analisi.
- Si conservano solo brevi campi validati (workflow, run, stato, conclusione, branch, commit corto, link al run, durate); mai il messaggio del commit. I nomi di workflow, branch e job sono testo di terzi fino a 100 caratteri: si conservano e si mostrano come testo semplice, e i nomi dei passi vanno alle statistiche. Gli ultimi `webhook.live_events_keep` eventi si leggono su `GET /api/live-events` (chi può aprire la pagina: il token di accesso in modalità rete, una sessione in modalità team).
- Opzionale, spento per impostazione predefinita: con `live.sse.enabled` attivo, `GET /api/live-events/stream` invia gli stessi eventi appena accettati, come eventi del server (`hello`, poi un frame `live` per evento, con un `id` progressivo per riprendere con `Last-Event-ID` o `?since=`, un commento di keep-alive e un `bye` finale). Sola lettura; in modalità rete chiede il token di accesso come ogni altra richiesta; al massimo `live.sse.max_clients` ascoltatori, ciascuno per `live.sse.max_seconds`. L'edizione Lite non lo ha.
- Un run che termina in rosso invia anche la notifica `workflow_failed` se le notifiche sono attive. Con `webhook.record_events` spento il webhook torna alla modalità di solo aggiornamento descritta sopra.
- GitHub non può raggiungere `127.0.0.1`: usa `gh webhook forward` (vedi la documentazione della CLI di GitHub) o un tunnel che crei di proposito, verso `http://127.0.0.1:PORTA/api/webhook`.

## Copertura nel tempo

La vista Dal vivo dice quanta parte del tempo gli eventi coprono lo stato: **coperto da eventi** (l'ultimo evento è più recente di `savings.webhook_window_minutes`, 60 minuti per impostazione predefinita), **nessun evento da ...** (più vecchio: un repository tranquillo o un tunnel perso) oppure **in attesa del primo evento**. Il polling è sempre il ripiego: un invio che non è mai arrivato (monitor spento, tunnel caduto) viene recuperato dalla lettura successiva del repository, quindi gli eventi riducono le letture ma non le sostituiscono mai. Le stesse cifre sono in `GET /api/live-status`, sotto `coverage` e `secret_source` (`env`, `config` o `none`; mai il segreto).

## Se non funziona

| Risposta | Significato |
|---|---|
| `404` | Il ricevitore è spento, oppure il segreto manca o ha meno di 32 caratteri nella variabile d'ambiente. |
| `401` | La firma non corrisponde: stesso segreto da entrambe le parti e tipo di contenuto `application/json`. |
| `413` | Il corpo supera 256 KB. |
| `400` | Nessun id `X-GitHub-Delivery` valido, o contenuto non compreso. |
| `202` | Accettato e ignorato: un repository non sorvegliato, un evento fuori lista, un invio ripetuto o un repository oltre il limite al minuto. |
| `429` | Un indirizzo ha inviato più di 120 richieste firmate correttamente in un minuto, o più di `webhook.max_bad_per_minute` (120 di default) la cui firma non si verifica. |

## Replay e inondazioni

Una richiesta firmata valida che qualcuno ha catturato e rinvia riceve risposta ma non viene eseguita: ogni consegna richiede il proprio id `X-GitHub-Delivery`, gli id già accettati e il corpo firmato stesso sono ricordati per `webhook.replay_seconds` (un'ora di default, memoria limitata): una richiesta catturata e rinviata con un altro id è quindi la stessa consegna, e una ripetizione riceve `202 {"duplicate": true}`. (Una riconsegna manuale dalla pagina di GitHub ripete lo stesso corpo, quindi viene ignorata in questa finestra.) Un repository può causare al massimo `webhook.max_per_minute` eventi accettati al minuto; gli altri ricevono risposta e vengono ignorati. Se il payload indica `full_name`, il suo proprietario deve essere l'account osservato (o uno di `webhook.allowed_owners`). Un indirizzo può inviare 120 richieste firmate correttamente al minuto e `webhook.max_bad_per_minute` con firma che non si verifica; le due cose sono contate a parte, in ogni modalità, così la spazzatura non consuma mai la quota delle consegne vere (con `listen.trusted_proxy` l'indirizzo è quello visto dal proxy). Dopo un evento accettato le letture condizionali salvate di quel repository vengono eliminate e il repository viene riletto al ciclo successivo, così un evento dal vivo è sempre riconciliato con GitHub. La memoria delle consegne è conservata in un file privato della cartella dei dati (`webhook.persist_deliveries`, attivo di default; limitata, e un file danneggiato è una memoria vuota): un riavvio non rende di nuovo valida una consegna catturata. Con `webhook.reject_stale` attivo (spento di default) un evento di workflow firmato il cui orario è più vecchio di `webhook.replay_seconds` riceve risposta ed è ignorato. La quota di richieste firmate correttamente di un indirizzo è `webhook.max_verified_per_minute` (120). `webhook.secret_env` non accetta mai una variabile di sistema o del tuo accesso a GitHub (PATH, GH_TOKEN...) né un segreto che appartiene a un'altra impostazione, e un nome può essere scritto in una sola impostazione.

## Lista di controllo della vista dal vivo

1. Metti un segreto di almeno 32 caratteri nella variabile d'ambiente indicata da `webhook.secret_env` e attiva il webhook.
2. Inoltra la porta (`gh webhook forward`) o apri un tunnel e usa il suo indirizzo che termina con `/api/webhook` in GitHub.
3. Avvia un workflow (o fai un push in un repository osservato) e cerca l'evento in `?view=live`. Il `ping` di GitHub prova solo la firma: riceve `200` e non compare nell'elenco, e un nuovo invio da GitHub viene ignorato come ripetizione.
4. Tieni d'occhio la quota nell'intestazione: con i webhook basta un ciclo più lento.
