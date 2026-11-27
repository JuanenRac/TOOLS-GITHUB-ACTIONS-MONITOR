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
- Il segreto condiviso è l'unica barriera: GitHub non può inviare un token di accesso, quindi il ricevitore non lo chiede e si fida solo della firma. Con il ricevitore attivo e senza segreto rifiuta ogni consegna con `401`, e il doctor lo segnala in rosso. Tieni l'indirizzo dietro un tunnel o un proxy che controlli.
- Ogni richiesta deve portare `X-Hub-Signature-256: sha256=<hmac>`, calcolato con quel segreto e confrontato in tempo costante; ogni altra riceve `401` e nulla del contenuto viene guardato prima di verificare la firma.
- Un corpo oltre `webhook.max_body_kb` (1 MiB per impostazione predefinita, fino a 25 MiB) riceve `413`, prima di leggere o calcolare qualsiasi cosa; i rifiuti sono contati in `stats.too_big`.
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
| `413` | Il corpo supera `webhook.max_body_kb` (1 MiB per impostazione predefinita). |
| `503` | La coda degli eventi è piena: GitHub o tu la inviate di nuovo più tardi (`Retry-After`); la consegna non viene ricordata come duplicato. |
| `400` | Nessun id `X-GitHub-Delivery` valido, o contenuto non compreso. |
| `202` | Accettato e ignorato: un repository non sorvegliato, un evento fuori lista, un invio ripetuto o un repository oltre il limite al minuto. |
| `429` | Un indirizzo ha inviato più di 120 richieste firmate correttamente in un minuto, o più di `webhook.max_bad_per_minute` (120 di default) la cui firma non si verifica. |

## Replay e inondazioni

Una richiesta firmata valida che qualcuno ha catturato e rinvia riceve risposta ma non viene eseguita: ogni consegna richiede il proprio id `X-GitHub-Delivery`, gli id già accettati e il corpo firmato stesso sono ricordati per `webhook.replay_seconds` (un'ora di default, memoria limitata): una richiesta catturata e rinviata con un altro id è quindi la stessa consegna, e una ripetizione riceve `202 {"duplicate": true}`. (Una riconsegna manuale dalla pagina di GitHub ripete lo stesso corpo, quindi viene ignorata in questa finestra.) Un repository può causare al massimo `webhook.max_per_minute` eventi accettati al minuto; gli altri ricevono risposta e vengono ignorati. Se il payload indica `full_name`, il suo proprietario deve essere l'account osservato (o uno di `webhook.allowed_owners`). Un indirizzo può inviare 120 richieste firmate correttamente al minuto e `webhook.max_bad_per_minute` con firma che non si verifica; le due cose sono contate a parte, in ogni modalità, così la spazzatura non consuma mai la quota delle consegne vere (con `listen.trusted_proxy` l'indirizzo è quello visto dal proxy). Dopo un evento accettato le letture condizionali salvate di quel repository vengono eliminate e il repository viene riletto al ciclo successivo, così un evento dal vivo è sempre riconciliato con GitHub. La memoria delle consegne è conservata in un file privato della cartella dei dati (`webhook.persist_deliveries`, attivo di default; limitata, e un file danneggiato è una memoria vuota): un riavvio non rende di nuovo valida una consegna catturata. Con `webhook.reject_stale` attivo (attivo di default) un evento di workflow firmato il cui orario è più vecchio di `webhook.replay_seconds` riceve risposta ed è ignorato. La quota di richieste firmate correttamente di un indirizzo è `webhook.max_verified_per_minute` (120). `webhook.secret_env` non accetta mai una variabile di sistema o del tuo accesso a GitHub (PATH, GH_TOKEN...) né un segreto che appartiene a un'altra impostazione, e un nome può essere scritto in una sola impostazione.

L'orologio usato è sempre quello di questo computer, mai quello della consegna. `webhook.clock_skew_s` (300 secondi per impostazione predefinita, da 0 a 3600) è lo scarto che due orologi possono avere: un evento che appare così più vecchio della finestra non è per questo scaduto (`webhook.reject_stale`), e un evento segnato quando l'orologio di questo computer era avanti e poi è stato riportato indietro conta comunque come arrivato, così un repository non appare morto per colpa di un orologio; invecchia dal momento in cui viene notato. Un segno in anticipo di più di un giorno non viene creduto. `webhook.reject_stale` è attivo di default: un evento di run o di job il cui orario è più vecchio di `webhook.replay_seconds` più quello scarto riceve `202` e non viene eseguito, e una consegna si ricorda esattamente per quel tempo più lo scarto (la memoria è limitata dal tempo, con una rete di sicurezza di 20000 voci); una consegna catturata non può quindi essere accettata di nuovo quando la memoria l'ha lasciata andare. Il link di un run (`html_url`) si conserva solo se punta a github.com o all'host di `GH_HOST`. Limite noto: solo gli eventi `workflow_run` e `workflow_job` portano un orario che viene controllato; una consegna catturata di un altro evento (`push`, `release`, `check_run`, `check_suite`) può essere accettata di nuovo quando la memoria l'ha lasciata andare, al costo di una lettura in più di quel repository.

## Ordine, coda e consegne perse

- **Ordine.** GitHub non promette l'ordine delle consegne. Un'esecuzione o un job va solo avanti (in coda, in corso, completato): un evento che dice meno di quanto già si sa della stessa esecuzione (conta anche ciò che ha letto l'ultimo ciclo) non cambia nulla ed è contato in `stats.out_of_order` di `GET /api/live-status`. Un nuovo tentativo di un'esecuzione riparte da capo.
- **Coda.** Un evento accettato attende in una coda di al massimo `webhook.queue_max` eventi (500 per impostazione predefinita, da 1 a 10000) e un lavoratore lo applica, così GitHub riceve subito una risposta. Quando la coda è piena il ricevitore risponde `503` con `Retry-After` e dimentica la consegna, così quella che GitHub rinvia viene accettata: un evento non viene mai scartato in silenzio. La profondità è `queue` in `GET /api/live-status` e i rifiuti sono `stats.queue_full`.
- **Consegne perse.** Un'esecuzione che un evento ha lasciato aperta (in coda o in corso) e che non riceve un evento finale entro `webhook.stale_after_h` ore (6 per impostazione predefinita, da 1 a 168) viene segnata `stale` nell'elenco delle esecuzioni e il suo repository viene riletto al ciclo successivo (`stats.stale`; `open_runs` conta le esecuzioni tenute aperte).
- **Pronto.** `GET /readyz` (solo da questo computer) risponde `200` quando il monitor può prendere lavoro e `503` quando no, con il controllo che fallisce: `loaded` (c'è una prima lettura), `cycle` (il ciclo di aggiornamento non è bloccato né fermo), `store` (la cartella dei dati è scrivibile) e `queue` (la coda ha posto). `GET /api/health` dice solo che il processo vive.

## Senza webhook: gli eventi dell'account (disattivato per impostazione predefinita)

Con `events_feed.enabled` attivo, il monitor legge gli eventi dell'account (`GET /orgs/OWNER/events`, o `/users/OWNER/events`; `events_feed.owner_kind` dice quale, e `auto` prova prima l'organizzazione) ogni `events_feed.interval_seconds` (60 per impostazione predefinita; vale `X-Poll-Interval` se è più lungo) con un ETag. Una lettura che non trova nulla di nuovo risponde `304` e non costa quota; quando qualcosa è cambiato (un push, una pull request, un tag o una release) viene riletto al ciclo successivo solo il repository indicato nell'evento, al massimo `events_feed.max_per_tick` per turno. La prima lettura impara solo a che punto è l'elenco. Non servono webhook né tunnel e può funzionare accanto a uno. I contatori sono `feed` in `GET /api/live-status`.

## Senza indirizzo pubblico: il WebSocket di GitHub (disattivato per impostazione predefinita)

GitHub non può raggiungere un monitor a casa, dietro un router. Con `webhook.transport` su `websocket` la CLI di GitHub fa il contrario: `gh webhook forward` crea un webhook temporaneo, tiene aperta una connessione da questo computer e consegna ogni invio al ricevitore del monitor, quindi nulla è esposto e non serve un tunnel.

- `webhook.ws_targets` elenca cosa inoltrare: `owner/repo` per un repository o `owner` per un'intera organizzazione (un account personale richiede una voce per repository, al massimo `webhook.ws_max_targets`). Vuoto per impostazione predefinita: cambiare solo il trasporto non avvia nulla. Il ricevitore deve essere attivo (`webhook.enabled` e il segreto condiviso) e il monitor riavviato.
- **Scrive su GitHub** (gli hook temporanei) e richiede un token che possa gestire i webhook (`admin:repo_hook`, `admin:org_hook`). Con un token che non può, lo stato della destinazione dice `forbidden` e si riprova solo ogni pochi minuti.
- Le consegne sono firmate con un segreto creato a ogni avvio, tenuto in memoria e passato a `gh` sulla riga di comando; un altro processo dello stesso utente su questo computer potrebbe leggerlo, e permette solo a quell'utente di inviare eventi a un ricevitore che è su questo computer. Il segreto condiviso non lascia mai l'ambiente. GitHub non firma ogni frame del WebSocket separatamente: la connessione è autenticata dal token.
- Un inoltro che termina viene riavviato con un'attesa sempre più lunga (da 5 secondi a 5 minuti). Un hook accetta un solo sottoscrittore: non eseguire `gh webhook forward` a mano per la stessa destinazione. Le consegne di questo trasporto non appaiono come rinviabili nella pagina dell'hook in GitHub, quindi il recupero qui sotto funziona solo con il trasporto `http`.
- `webhook.ws_cleanup` (disattivato) elimina all'avvio gli hook che puntano all'inoltro di GitHub nelle destinazioni indicate, ripulendo ciò che un arresto ha lasciato; elimina hook, quindi attivalo solo se sai che nessun'altra sessione li usa.
- Lo stato di ogni inoltro è `forwarders` in `GET /api/live-status`.

## Consegne che non sono mai arrivate (disattivato per impostazione predefinita)

Un monitor a casa non è sempre acceso: il computer è spento di notte, il tunnel cade. GitHub conserva le consegne recenti di un webhook, dice quali sono fallite e permette di rinviarne una fallita. Con `webhook.redeliver.enabled` attivo, il monitor controlla i webhook che indichi in `webhook.redeliver.hooks` (`repo:OWNER/REPO#ID` oppure `org:OWNER#ID`, dove ID è il numero alla fine dell'indirizzo del webhook in GitHub) un minuto dopo l'avvio e poi ogni `webhook.redeliver.interval_minutes` (60 per impostazione predefinita), e chiede a GitHub di rinviare le consegne a cui nessun tentativo ha risposto con un 2xx.

- **Scrive su GitHub** (la richiesta di rinvio) e richiede un token che possa gestire il webhook. Disattivato per impostazione predefinita; le consegne di una GitHub App non sono coperte.
- Al massimo `webhook.redeliver.max_per_run` (20) consegne per controllo, nessuna più vecchia di `webhook.redeliver.max_age_hours` (24; GitHub le conserva tre giorni), prima quelle mai richieste. Una consegna viene richiesta di nuovo con un'attesa crescente (5, 10, 20, 40, 80, 160 e 300 secondi) e abbandonata (`dead`) dopo l'ottava volta. Ciò che è stato richiesto è conservato in un file privato della cartella dei dati (l'id della consegna e il conteggio, mai un contenuto), così un riavvio non richiede di nuovo subito.
- Una consegna che arriva di nuovo viene trattata dal ricevitore come duplicato, quindi chiedere due volte non fa danno.
- `POST /api/webhook/redeliver` (amministratori, solo da questo computer, con il token monouso) controlla subito, qualunque sia la pianificazione, e lascia una riga nel registro delle azioni. I contatori sono `redelivery` in `GET /api/live-status`.

## Lista di controllo della vista dal vivo

1. Metti un segreto di almeno 32 caratteri nella variabile d'ambiente indicata da `webhook.secret_env` e attiva il webhook.
2. Inoltra la porta (`gh webhook forward`) o apri un tunnel e usa il suo indirizzo che termina con `/api/webhook` in GitHub.
3. Avvia un workflow (o fai un push in un repository osservato) e cerca l'evento in `?view=live`. Il `ping` di GitHub prova solo la firma: riceve `200` e non compare nell'elenco, e un nuovo invio da GitHub viene ignorato come ripetizione.
4. Tieni d'occhio la quota nell'intestazione: con i webhook basta un ciclo più lento.
