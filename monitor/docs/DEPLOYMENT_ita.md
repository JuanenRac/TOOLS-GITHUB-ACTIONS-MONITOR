<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->


[🇺🇸 English](DEPLOYMENT.md) | [🇪🇸 Español](DEPLOYMENT_spa.md) | [🇫🇷 Français](DEPLOYMENT_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](DEPLOYMENT_deu.md) | [🇨🇳 简体中文](DEPLOYMENT_zho.md) | [🇯🇵 日本語](DEPLOYMENT_jpn.md) | [🇵🇹 Português](DEPLOYMENT_por.md)

# Eseguirlo come servizio

Il monitor è un programma che, per impostazione predefinita, ascolta solo su `127.0.0.1` e non ha login. Queste note servono per eseguirlo come servizio: l'immagine ufficiale, Docker Compose con un proxy inverso, un'installazione classica con systemd e cosa succede quando GitHub revoca l'accesso.

## Dove ascolta

Il monitor ascolta in uno di tre modi, e la pagina, `GET /api/accounts`, `bin/monitor_cli.py status` e `bin/monitor_cli.py accounts` dicono quale: **questo computer** (solo `127.0.0.1`: il predefinito, senza login), **la rete** (la modalità rete, `listen.network`: ascolta anche su `listen.host` e ogni richiesta porta il token di accesso) oppure **dietro un proxy** (la modalità rete con un proxy inverso dichiarato davanti: `listen.proxy_public_host`, `listen.secure_cookie` o `listen.trusted_proxy`). L'immagine e l'unità di servizio sono fatte per il secondo e il terzo; un monitor avviato a mano resta nel primo.

In modalità rete il supervisore di più account segue le stesse regole del monitor di un account: il token di accesso a ogni richiesta (cookie, intestazione o `POST /api/access`), blocco dopo token errati, il controllo di `Host`, TLS facoltativo con il tuo certificato, la seconda porta di chi è al computer (`listen.local_port`), e le chiavi che decidono l'esposizione, l'accesso a GitHub e le azioni su GitHub solo dal computer del monitor (una richiesta dalla rete raggiunge l'account contrassegnata come remota).

## Le porte delle due edizioni

L'edizione completa ascolta sulla porta 8765 e la lite sulla 8766, salvo che il file di configurazione ne indichi un'altra: `ports.complete` e `ports.lite` (un intero da 1024 a 65535, serve il riavvio; sono anche nella pagina Impostazioni, blocco Porte). I due numeri si leggono in un solo punto, quindi l'avvio, il controllo «c'è già un monitor su questa porta», `--doctor`, il controllo di salute (`python -m github_actions_monitor.cli.healthcheck`), la riga di comando (`--lite` parla con la porta lite), le viste da terminale e i lanciatori concordano. L'ordine è: `--port N` sulla riga di comando, poi `MONITOR_PORT` (lo impostano il servizio e il container; solo l'edizione completa), poi il file dell'edizione, poi quello dell'altra edizione (un menu può impostarle entrambe), poi il valore predefinito. L'edizione lite non prende mai la porta della completa: se entrambe indicano lo stesso numero, la lite mantiene 8766, e la pagina Impostazioni rifiuta di salvare lo stesso numero per entrambe. Se la porta è occupata, il monitor prende la successiva libera, fino a dieci sopra.

## Senza browser e il controllo di salute

`python -m github_actions_monitor.service` è l'ingresso di un servizio: prepara le cartelle e il primo account dall'ambiente (vedi la tabella sotto) e avvia il monitor senza browser. `python bin/actions_monitor.py --no-browser --port 8765` vale ancora per un monitor che gestisci tu.

`GET /api/health` risponde `{"ok": true, "version": ..., "loaded": ..., "offline": ...}` più lo stato del ciclo di aggiornamento e dell'accesso GitHub dell'account; non chiama GitHub. `GET /api/health?deep=1` è il controllo approfondito: risponde 503 quando il ciclo di aggiornamento di un account dura più di `watchdog_minutes` (30 minuti se è 0) o il suo thread è sparito; nel supervisore di più account anche quando il ciclo di supervisione stesso si è fermato, quando il ciclo di QUALSIASI account è bloccato o quando nessun account risponde passato l'avvio. Un account il cui accesso GitHub non serve (cieco) è nominato nella risposta ma non è un guasto: un riavvio non ripara un accesso perso, uno nuovo sì.

`python -m github_actions_monitor.cli.healthcheck` fa quella chiamata per un contenitore o un gestore di servizi (codice di uscita 0 sano, 1 non sano, 2 nessuna risposta, 3 rifiutato). Legge il token di accesso da `MONITOR_ACCESS_TOKEN`, dal file indicato da `MONITOR_ACCESS_TOKEN_FILE` o da quello che il servizio tiene in `MONITOR_STATE_DIR`. `bin/monitor_cli.py health --deep` fa lo stesso da qualsiasi computer.

## L'immagine ufficiale

`ghcr.io/juanenrac/tools-github-actions-monitor` per `linux/amd64` e `linux/arm64`, con i tag `2.1.0`, `2.1` e `latest`, costruita dal workflow di rilascio con un'attestazione della sua provenienza. È fatta in tre fasi (`deploy/Dockerfile`) e contiene solo Python, la CLI di GitHub, i certificati delle CA e il codice, in sola lettura e di proprietà di root. Gira come utente 10001 (mai root) e scrive solo in due volumi: `/config` (`actions_monitor.json`, creato al primo avvio e mai sovrascritto) e `/data` (`accounts/`, `state/` con il token di accesso, `secrets/`, l'accesso di `gh`). Ascolta in modalità rete sulla porta 8765 del contenitore, quindi ogni richiesta richiede il token di accesso, e non pubblica alcuna porta da sola.

```sh
docker run -d --name github-actions-monitor --restart unless-stopped \
  --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges:true \
  -e MONITOR_GITHUB_OWNER=my-org -e GH_TOKEN_FILE=/run/secrets/gh_token \
  -v "$PWD/gh_token.txt:/run/secrets/gh_token:ro" \
  -v monitor-config:/config -v monitor-data:/data \
  -p 127.0.0.1:8765:8765 \
  ghcr.io/juanenrac/tools-github-actions-monitor:latest

docker exec github-actions-monitor cat /data/state/access_token      # the access token, made on the first start
```

Al primo avvio crea la configurazione, il primo account (da `MONITOR_GITHUB_OWNER`; più account con `MONITOR_ACCOUNTS=personale:io,lavoro:mia-org`) e, se `MONITOR_ACCESS_TOKEN` non è dato, un token di accesso che conserva in `/data/state/access_token` (modo 600) e non stampa mai. Apri la sessione senza mettere il token nell'indirizzo: invia `POST /api/access` con `{"token": "..."}` (il cookie torna nella risposta) o l'intestazione `X-Monitor-Access`. Per aprirla una volta dalla barra degli indirizzi di un browser, avvia il container con `MONITOR_QUERY_ACCESS=1`, apri `http://127.0.0.1:8765/?access=TOKEN` e spegni di nuovo la variabile. Con un bind mount invece di un volume con nome, dai la cartella all'utente 10001 (`chown -R 10001:10001`). L'edizione lite non è nell'immagine.

## Docker Compose, con proxy e TLS facoltativi

`deploy/compose.yaml` esegue il monitor con il codice in sola lettura, senza capability, l'accesso come secret di Docker e i due volumi. Il profilo `proxy` mette davanti Caddy (`deploy/Caddyfile`): ottiene e rinnova da solo il certificato di un nome pubblico (`tls internal` per un nome della tua rete, `http://nome` per nessuno). Copia `deploy/.env.example` in `deploy/.env`, compilalo e avvia:

```sh
cp deploy/.env.example deploy/.env                                   # fill in MONITOR_GITHUB_OWNER
printf '%s' "ghp_..." > deploy/gh_token.txt && sudo chown 10001:10001 deploy/gh_token.txt && chmod 600 deploy/gh_token.txt
docker compose -f deploy/compose.yaml up -d                          # on 127.0.0.1:8765
docker compose -f deploy/compose.yaml --profile proxy up -d          # behind Caddy (deploy/Caddyfile)
```

Dietro il proxy il monitor deve conoscere il proprio nome pubblico e sapere che la sessione è HTTPS: `MONITOR_PROXY_PUBLIC_HOST` e `MONITOR_SECURE_COOKIE=1`. Nulla di ciò che arriva sulla porta principale conta allora come il computer del monitor: usa la seconda porta (`MONITOR_LOCAL_PORT`, 8766 nell'immagine, solo loopback) con `docker compose exec monitor python bin/monitor_cli.py ...` (l'immagine vi punta `MONITOR_URL`).

## Un'installazione classica con systemd

`deploy/github-actions-monitor.service` e `deploy/github-actions-monitor.env` eseguono la release decompressa come utente `monitor` con l'hardening di systemd (nulla di scrivibile tranne la propria cartella, nessun nuovo privilegio), la riavviano in caso di errore, verificano la salute approfondita dopo l'avvio e rileggono i file delle credenziali con `systemctl reload`.

```sh
useradd --system --home-dir /var/lib/github-actions-monitor --create-home --shell /usr/sbin/nologin monitor
install -d -o monitor -g monitor -m 700 /etc/github-actions-monitor
install -m 600 -o monitor deploy/github-actions-monitor.env /etc/github-actions-monitor/env     # edit it
install -m 644 deploy/github-actions-monitor.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now github-actions-monitor
systemctl reload github-actions-monitor                              # SIGHUP: read the credential files again
```

Il file env tiene i dati in `/var/lib/github-actions-monitor` e l'accesso in `/etc/github-actions-monitor/gh_token` (modo 600). Ascolta su `127.0.0.1` a meno che tu vi attivi la modalità rete.

launchd (macOS): `ProgramArguments` = `/usr/bin/python3`, `-m`, `github_actions_monitor.service`, le variabili in `EnvironmentVariables`, `KeepAlive` e `RunAtLoad` true. Windows: `schtasks /Create /SC ONLOGON /TN GhaMonitor /TR "py -3 C:/percorso/di/bin/actions_monitor.py --no-browser"`.

## Variabili d'ambiente

Vengono lette solo i nomi di questa tabella. Nel servizio un valore illeggibile viene ignorato con un avviso e non cambia nulla. Quelle che nominano una parte della configurazione (`MONITOR_LISTEN_*`, `MONITOR_ALLOWED_HOSTS`, `MONITOR_PROXY_PUBLIC_HOST`, `MONITOR_SECURE_COOKIE`, `MONITOR_TRUSTED_PROXY`, `MONITOR_LOCAL_PORT`, `MONITOR_TLS_*`, `MONITOR_QUERY_ACCESS`, `MONITOR_TEAM_MODE`) vengono scritte in `listen` e `auth` a ogni avvio del servizio, così l'ambiente resta l'autorità per esse; tutto il resto del file è tuo. Una variabile del proxy impostata ma lasciata vuota (`MONITOR_TRUSTED_PROXY`, `MONITOR_TRUSTED_PROXIES`, `MONITOR_SECURE_COOKIE`, `MONITOR_PROXY_PUBLIC_HOST`, `MONITOR_ALLOWED_HOSTS`) spegne la sua chiave all'avvio, così una riga vuota del file `.env` non mantiene mai viva una vecchia dichiarazione del proxy; una non impostata non cambia nulla.

| Variabile | Cosa fa |
|---|---|
| `MONITOR_GITHUB_OWNER` | L'utente o l'organizzazione da controllare; da essa viene creato il primo account al primo avvio. |
| `MONITOR_ACCOUNT` | L'id del primo account (predefinito `default`). |
| `MONITOR_ACCOUNTS` | Più account insieme: `personale:io,lavoro:mia-org` (id:proprietario). Solo se non c'è ancora alcun account. |
| `MONITOR_LANG` | La lingua dei testi (`en es de fr it ja zh pt`). |
| `MONITOR_PORT` | La porta nel contenitore o del servizio (predefinita 8765). |
| `MONITOR_CONFIG` | Il file di configurazione (l'immagine: `/config/actions_monitor.json`); creato al primo avvio e mai sovrascritto. |
| `MONITOR_ACCOUNTS_DIR` | La cartella degli account, una cartella per account (l'immagine: `/data/accounts`). |
| `MONITOR_STATE_DIR` | File che altrimenti resterebbero accanto al codice: il token di accesso del servizio, l'audit degli accessi (l'immagine: `/data/state`). |
| `MONITOR_CONFIG_DIR` | La cartella `config/`: i file di configurazione (`targets.json`, `quotas.json` ...) e `config_backups/` (l'immagine: `/config`). |
| `MONITOR_DATA_DIR` | La cartella `data/`: lo stato, le cache e gli account; `logs/` e `ai/` stanno al suo interno salvo che `MONITOR_LOGS_DIR` / `MONITOR_AI_DIR` dicano altro (l'immagine: `/data`). Vedi LAYOUT. |
| `MONITOR_SECRET_DIR` | Dove vive il token conservato dal monitor stesso, se lo attivi (l'immagine: `/data/secrets`). |
| `GH_CONFIG_DIR` | La cartella di configurazione di `gh` (l'immagine: `/data/gh`). |
| `GH_TOKEN_FILE` | Un file con il token GitHub nella prima riga (un secret di Docker, una credential di systemd). Letto all'avvio e di nuovo con SIGHUP. |
| `GH_TOKEN` | Un token GitHub nell'ambiente; `gh` lo legge. Meglio un file: l'ambiente è visibile a ogni processo del contenitore. |
| `GH_HOST` | Il nome di un host GitHub Enterprise Server: tutte le chiamate e tutti i link della pagina lo usano. |
| `MONITOR_ACCESS_TOKEN` | Il token di accesso della modalità rete (almeno 16 caratteri). Senza di esso il servizio ne crea uno e lo conserva in `MONITOR_STATE_DIR`. |
| `MONITOR_ACCESS_TOKEN_FILE` | Un file con il token di accesso nella prima riga, al posto della variabile. |
| `MONITOR_LISTEN_NETWORK` | `1` = la modalità rete (`listen.network`): ascolta su `MONITOR_LISTEN_HOST` e ogni richiesta richiede il token di accesso. L'immagine la attiva. |
| `MONITOR_LISTEN_HOST` | L'indirizzo su cui ascolta in modalità rete (`0.0.0.0` nell'immagine; altrove meglio un indirizzo privato della macchina). |
| `MONITOR_ALLOWED_HOSTS` | Nomi host che il monitor accetta oltre al proprio indirizzo, separati da virgole (`listen.allowed_hosts`). |
| `MONITOR_PROXY_PUBLIC_HOST` | Il nome pubblico del proxy inverso (`listen.proxy_public_host`); dichiara il proxy. |
| `MONITOR_SECURE_COOKIE` | `1` = la sessione è HTTPS (la termina un proxy): il cookie porta Secure (`listen.secure_cookie`). |
| `MONITOR_TRUSTED_PROXY` | `1` = il proxy gira sulla STESSA macchina e il suo `X-Forwarded-For` è creduto (`listen.trusted_proxy`). |
| `MONITOR_TRUSTED_PROXIES` | Indirizzi o reti del proxy quando non è su questa macchina, separati da virgole (`listen.trusted_proxies`); solo con `MONITOR_TRUSTED_PROXY`. Il file Compose dà a Caddy l'indirizzo fisso `MONITOR_PROXY_IP` (172.29.77.250 per impostazione predefinita, dentro `MONITOR_SUBNET`): indichi solo quell'indirizzo. |
| `MONITOR_LOCAL_PORT` | Una seconda porta, solo loopback, per chi è al computer quando è dichiarato un proxy (`listen.local_port`; 8766 nell'immagine). |
| `MONITOR_TLS_CERT_FILE` | Un certificato (PEM) per servire direttamente HTTPS (`listen.tls_cert_file`); con la chiave. Se non è utilizzabile, il monitor non parte in HTTP semplice. |
| `MONITOR_TLS_KEY_FILE` | La chiave privata di quel certificato (`listen.tls_key_file`). |
| `MONITOR_QUERY_ACCESS` | `1` = l'indirizzo con `?access=` può aprire una sessione (`listen.query_access`, disattivato per impostazione predefinita); la via sicura è `POST /api/access`. |
| `MONITOR_TEAM_MODE` | `1` = la modalità team (`auth.enabled`): utenti, ruoli e sessioni. |
| `MONITOR_ADMIN_USER` | Con `MONITOR_ADMIN_PASSWORD_FILE`: il primo amministratore che il servizio crea quando la modalità team è attiva e non ci sono ancora utenti. |
| `MONITOR_ADMIN_PASSWORD_FILE` | Il file (per esempio un segreto Docker) con la password di `MONITOR_ADMIN_USER` nella prima riga. |
| `MONITOR_SERVICE` | `1` = gira come servizio: non si arrende davanti a un accesso inutilizzabile e il doctor controlla la conservazione. L'immagine e il servizio la attivano. |
| `MONITOR_URL` | Per `bin/monitor_cli.py` e il controllo di salute: l'indirizzo del monitor (l'immagine: la seconda porta). |
| `MONITOR_CA_FILE` | Per `bin/monitor_cli.py`: un file PEM con l'autorità che ha firmato il certificato HTTPS del monitor. |
| `MONITOR_USER` | Per `bin/monitor_cli.py` in modalità team: l'utente con cui accedere. |
| `MONITOR_PASSWORD_FILE` | Per `bin/monitor_cli.py`: un file con la password di `MONITOR_USER` nella prima riga. |
| `MONITOR_RELEASE_TEST_TIMEOUT` | `tools/make_release.py`: secondi che la suite ordinaria può impiegare prima che la porta fallisca (predefinito 3600; da 60 a 86400). |
| `MONITOR_RELEASE_CLEAN_TIMEOUT` | `tools/make_release.py`: secondi che può impiegare la suite dello zip estratto (predefinito 3600; da 60 a 86400). |
| `MONITOR_RELEASE_LOG_DIR` | `tools/make_release.py`: cartella dove viene salvato TUTTO l'output di una suite che fallisce (predefinita: la cartella temporanea); il messaggio del gate nomina i test falliti e questo file. |
| `--accept-green-suite JSON --commit SHA [--skip-clean-suite]` | `tools/make_release.py`: invece di rieseguire la suite ordinaria, accetta la registrazione di un'esecuzione verde completa di quello stesso commit (terminata, senza fallimenti né errori, tutti i test eseguiti); `--skip-clean-suite` non ripete nemmeno la suite dello zip estratto (i controlli rapidi restano) e lo dichiara. |
| `--progress` | `tools/make_release.py`: mostra l'avanzamento delle suite, una riga ogni 250 test, anche nella suite dell'installazione pulita. |

## Un battito esterno (disattivato per impostazione predefinita)

Il monitor gira su un computer che può essere spento, messo in sospensione o riavviato, e allora nessuno viene a sapere che nessuno sorveglia. Con `heartbeat.enabled` attivo, il monitor invia un ping a un indirizzo ogni `heartbeat.interval_seconds` (300 per impostazione predefinita) e un servizio come healthchecks.io, Cronitor o Uptime Kuma ti dice quando i ping si fermano.

- L'indirizzo è un segreto: mettilo nella variabile d'ambiente indicata da `heartbeat.url_env` (`MONITOR_HEARTBEAT_URL` per impostazione predefinita). Non viene mai scritto nella configurazione, mostrato o registrato, e le Impostazioni dicono solo se ne è definito uno. Deve essere `https` (`http` solo con `notify.allow_private_targets`, per un servizio della tua rete), non avere utente né password e viene aperto con la stessa protezione delle notifiche.
- Il ping porta al massimo `msg=<versione> <ok|degraded>` (`heartbeat.send_state`): mai un repository, un avviso o un nome.
- Quando il monitor non è in grado di servire (il suo ciclo di aggiornamento è bloccato o assente) il ping non viene inviato e il silenzio è l'allarme. A un servizio con indirizzo di guasto (healthchecks.io: `/fail`) si può dare `heartbeat.fail_suffix` e allora viene avvisato subito.
- Nell'edizione completa `GET /api/health` mostra `heartbeat` (inviati, falliti, saltati e l'ultimo risultato).

## Quando GitHub revoca o fa scadere l'accesso

Ogni account è un processo a sé, quindi un accesso che smette di funzionare tocca solo quell'account. Dopo due rifiuti di fila che dicono che l'accesso stesso non serve (un 401, `Bad credentials`, un token scaduto o revocato, un account sospeso, nessun accesso) l'account è **cieco**: la pagina, il controllo di salute approfondito, `GET /api/accounts` (`state: blind`) e `bin/monitor_cli.py` lo dicono, si apre un **allarme critico di sistema** (`system.credential_blind`, sentinella `system`) nella scheda Allarmi, e i tipi di notifica `credential_blind` (attivo per impostazione predefinita) e `credential_back` avvisano i canali una volta. Il rifiuto di un solo permesso (un 403 per un repository) non rende cieco un account. Gli altri account continuano e il controllo di salute approfondito resta verde. L'account continua a provare e il primo ciclo buono chiude l'allarme.

Un servizio che parte con un accesso già inutilizzabile resta attivo e cieco invece di arrendersi, così c'è qualcosa da sostituire. Il token di un account viene da, vince il primo che esiste: il file `credential` nella sua cartella (scritto da una sostituzione), il file indicato da `GH_TOKEN_FILE`, poi ciò che usa `gh` (`GH_TOKEN` o il suo login). Una sostituzione non richiede di riavviare il supervisore né l'account, in tre modi:

```sh
# 1. the command line (a token is read from a file or the standard input, never from a flag)
docker compose exec -T monitor python bin/monitor_cli.py credential replace --account default --new-token-file - < new_token.txt
python bin/monitor_cli.py credential replace --url https://monitor.example.org --user ann --password-file pw.txt --account default --new-token-file new_token.txt

# 2. the administrator endpoint (an administrator session in the team mode, or the computer of the monitor)
#    POST /api/accounts/<id>/credential   {"action": "replace", "token": "..."}   or   {"action": "reload"}
#    (a monitor without a supervisor: POST /api/credential, from its own computer)

# 3. replace the file and send SIGHUP: every account reads its credential files again
docker kill --signal HUP github-actions-monitor
systemctl reload github-actions-monitor
```

Il nuovo token viene verificato con GitHub (la chiamata `rate_limit`, gratuita) PRIMA di essere conservato: un token che GitHub rifiuta non cambia nulla e risponde 422 (`rejected`). Uno buono viene scritto solo nella cartella di quell'account (modo 600), usato subito, e l'account rilegge senza attendere. In modalità team l'endpoint è per una sessione `admin` (con il token CSRF di una sessione con cookie) e l'audit registra chi l'ha fatto, mai il token; senza modalità team, con la modalità rete attiva, può solo il computer del monitor. Il token non compare mai in una risposta, un log, un allarme o la pagina.

## Il primo amministratore in un contenitore

Con `MONITOR_TEAM_MODE=1` l'immagine ascolta sulla rete e il monitor non apre la rete prima che esista il primo amministratore (che si può creare solo dal computer del monitor). In un contenitore ciò non si può fare su `/login` e la modalità rete non si può disattivare (l'immagine la imposta a ogni avvio), quindi il servizio si fermerebbe con codice di uscita 1 al primo avvio. Crea il primo amministratore una volta, sugli stessi volumi, prima di avviare il servizio (la password viene chiesta in console, mai nella riga di comando):

```sh
docker compose run --rm --entrypoint python monitor -m github_actions_monitor.security.auth_cli create-admin NAME
docker compose up -d
```

Oppure lascia che lo crei il servizio: imposta `MONITOR_ADMIN_USER` e `MONITOR_ADMIN_PASSWORD_FILE` (un file, per esempio un segreto Docker, con la password nella prima riga); il primo avvio crea quell'amministratore quando la modalità team è attiva e non esiste ancora alcun utente, e non stampa mai la password.

## Primo avvio, backup e aggiornamento

Primo avvio come servizio: imposta il proprietario e l'accesso (`GH_TOKEN_FILE`), avvia, leggi una volta il token di accesso (`/data/state/access_token`), apri la pagina ed esegui `bin/monitor_cli.py health --deep`. `python bin/actions_monitor.py --doctor` con `MONITOR_SERVICE=1` avvisa anche di un blocco di conservazione mancante e di account che condividono lo stesso token.

Backup: tutto ciò che va conservato è nei due volumi. Fai una copia coerente dell'archiviazione prima di un aggiornamento e una copia dei volumi:

```sh
docker compose exec monitor python /app/tools/backup_storage.py backup /data/state/backup.zip --backend file
docker cp github-actions-monitor:/data/state/backup.zip .
docker run --rm -v monitor-data:/data -v "$PWD":/backup alpine tar czf /backup/monitor-data.tgz -C /data .
```

Aggiornamento: i dati sopravvivono perché stanno nei volumi. Fissa una versione (`:2.1.0`) in produzione, scarica, ricrea e verifica l'attestazione dell'immagine. Un monitor più vecchio non apre mai un'archiviazione più recente (vedi `STORAGE.md`): tieni il backup finché la nuova versione non ha girato.

```sh
docker compose pull && docker compose up -d
gh attestation verify oci://ghcr.io/juanenrac/tools-github-actions-monitor:2.1.0 --owner JuanenRac
```

## Dietro un reverse proxy

Per impostazione predefinita il monitor ascolta solo su `127.0.0.1`. Se devi raggiungerlo da un'altra macchina, metti davanti un reverse proxy con TLS, attiva la modalità di rete (`listen.network`: allora ogni richiesta deve portare il token di accesso) e DICHIARA il proxy (`listen.proxy_public_host` con il suo nome pubblico, `listen.secure_cookie` o `listen.trusted_proxy`). Il monitor rifiuta ogni richiesta il cui `Host` non sia il suo indirizzo o quel nome pubblico; il proxy deve quindi inviarlo e deve aggiungere l'indirizzo reale del client:

```nginx
location / {
    proxy_pass           http://127.0.0.1:8765;
    proxy_set_header     Host $host;                                  # the public name: set it in listen.proxy_public_host
    proxy_set_header     X-Forwarded-For $proxy_add_x_forwarded_for;  # APPENDS the real address of the client; never copy the one the client sent
    proxy_set_header     X-Forwarded-Proto $scheme;
}
```

Con un proxy dichiarato, nulla di ciò che arriva sulla porta principale conta come «questo computer», qualunque cosa dicano le intestazioni (un proxy che dimentica un'intestazione farebbe apparire locali tutti i client di internet). Le chiavi che decidono l'esposizione, le azioni su GitHub e le prove dei canali non si possono quindi usare da lì. Per usarle, apri con `listen.local_port` (un numero da 1024 a 65535) una seconda porta in ascolto solo su `127.0.0.1` e usala dal computer del monitor: chiede lo stesso token di accesso.

`listen.trusted_proxy` presuppone che il proxy giri sullo STESSO computer del monitor (il monitor crede a `X-Forwarded-For` su qualsiasi connessione che arrivi da loopback): non usarlo con un proxy su un'altra macchina. I token sbagliati delle richieste che arrivano senza un `X-Forwarded-For` utilizzabile sono contati anche insieme (il triplo del limite di un indirizzo); questo blocco comune non ferma mai una richiesta con il token giusto. Se il proxy è in un altro contenitore o su un'altra macchina, indica il suo indirizzo o la sua rete in `listen.trusted_proxies` (`MONITOR_TRUSTED_PROXIES`; nel file Docker Compose, l'indirizzo fisso di Caddy `MONITOR_PROXY_IP`, non tutta la rete `MONITOR_SUBNET`: si crederebbe anche a un container che salta Caddy): per una connessione da quegli indirizzi, o da questo computer, il suo `X-Forwarded-For` è creduto per contare i tentativi; non fa mai passare una richiesta per questo computer.

## La riga di comando contro un altro computer

`bin/monitor_cli.py` funziona contro un monitor di un'altra macchina: `--url https://monitor.example.org` (o `MONITOR_URL`), il token di accesso da `MONITOR_ACCESS_TOKEN` o `--token-file`, `--ca-file` (o `MONITOR_CA_FILE`) per fidarsi dell'autorità che ha firmato un certificato HTTPS proprio e, in modalità team, `--user NOME` con `--password-file FILE` (o `MONITOR_USER`, `MONITOR_PASSWORD_FILE`), che accede con una sessione Bearer (`auth.allow_bearer`). `status`, `accounts`, `alerts`, `health` (`--deep`) e `credential` funzionano allo stesso modo e i codici di uscita sono gli stessi (3 = rifiutato, anche per un account cieco in `status` e `accounts`). L'HTTP semplice verso un altro computer stampa un avviso.

## Permessi minimi dell'accesso (`gh` o un token a granularità fine)

- Elenchi di run, job e issue: Actions (lettura), Issues (lettura), Metadata (lettura). Avvisi: avvisi di Code scanning, Dependabot e Secret scanning (lettura). Pull request e release: Pull requests (lettura), Contents (lettura). Pacchetti: `read:packages`.
- Solo le azioni facoltative dell'IA scrivono: rilanciare un workflow richiede Actions (scrittura) e chiudere un issue richiede Issues (scrittura). Lasciale spente e dai all'accesso la sola lettura.

## Molti repository

Le letture condizionali (`cache.etag`) fanno sì che un repository invariato non costi quota; `mode: lite`, `ecosystems`, `exclude` e `max_workers` limitano il lavoro; il webhook in ingresso elimina l'interrogazione dei repository che inviano eventi. `discover_limit` è il massimo di repository elencati per un account (1000 predefinito).

## Attivo per mesi: archiviazione e conservazione

Tieni `accounts/` (o il database) su un volume che sopravvive al container e fai una copia con `python tools/backup_storage.py backup FILE.zip --backend file` (o `sqlite`) prima di un aggiornamento. Di serie un breve passaggio rimuove gli eventi più vecchi di 90 giorni e le analisi più vecchie di 180; imposta `retention` nella configurazione per cambiarlo, e `MONITOR_SERVICE=1` fa trattare il monitor come un servizio a `--doctor` (che poi avvisa se manca il blocco `retention` o se gli eventi diventano grandi). Con SQLite il predefinito è un database per account; un file condiviso è possibile ed è descritto in [STORAGE_ita.md](STORAGE_ita.md).

## Backup, volumi e aggiornamenti

Per un servizio, `deploy/github-actions-monitor-backup.service` e `deploy/github-actions-monitor-backup.timer` fanno ogni giorno un backup completo (`monitor_cli.py backup create`); `deploy/compose.yaml` tiene i backup in un volume a parte (`monitor-backups`). Prima di un aggiornamento fai un backup e verificalo, dopo esegui il doctor. I passi, il ripristino e i codici di uscita del doctor sono in [OPS_ita.md](OPS_ita.md).

## Verificare l'immagine in contenitori reali

Il repository contiene un workflow, `docker-audit.yml`, che costruisce su GitHub l'immagine di qualsiasi versione (un tag o un commit) e la verifica in contenitori reali: l'avvio e il controllo di salute, il contratto dell'API, la modalità team con il suo primo amministratore, Caddy come proxy di fiducia con il proprio TLS, l'indurimento (niente root, file system in sola lettura, nessuna capability), i volumi con backup, ripristino e passaggio dalla versione precedente, i segreti, lo spegnimento e il webhook in ingresso dietro il proxy. Non esegue nulla sul tuo computer, non pubblica nulla e non usa alcun segreto. Avvialo a mano e leggi la tabella del riepilogo dell'esecuzione e l'artefatto `docker-audit-<versione>`:

```sh
gh workflow run docker-audit.yml -f ref=<tag>
```

Gli stessi script girano su una macchina Linux con Docker (`tools/docker_audit/run_all.sh`); `tools/docker_audit/LEEME.txt` spiega come leggere ogni risultato.

## Il monitor sul telefono

Tutto in questa sezione è spento o innocuo per impostazione predefinita.

- **App installabile** (`pwa.enabled`): la pagina offre un manifest, due icone e un piccolo service worker, così un browser può installare il monitor come app. I file sono `/manifest.webmanifest`, `/sw.js`, `/pwa/offline`, `/pwa/icon-192.png` e `/pwa/icon-512.png`; in modalità di rete sono serviti dietro il token di accesso come ogni pagina. Il worker conserva solo la pagina offline e le icone: mai la pagina, mai una risposta dell'API. Quando l'app torna in primo piano, o torna la rete, la pagina chiede subito dati freschi (`pwa.refresh_on_return`).
- **Vista compatta** (`ui.compact`): `auto` la usa in una finestra stretta, `on` sempre, `off` mai; `?compact=1` o `?compact=0` la cambia per una finestra. Il menu passa in alto come una riga di schede, le tabelle scorrono di lato, uno schermo tattile riceve bersagli di almeno 44 pixel e i dialoghi seguono l'altezza lasciata dalla tastiera sullo schermo.
- **Abbinamento con un codice QR** (`pairing.enabled`, solo in modalità di rete): apri la tavolozza (Ctrl+K) e scegli "Abbina un telefono", poi "Nuovo codice QR". Il codice vale una sola volta e per `pairing.code_minutes` minuti; un nuovo codice annulla il precedente. Il telefono lo scansiona, preme il pulsante della pagina che si apre e riceve un token proprio (un cookie), mai il token di accesso. La stessa finestra elenca i dispositivi abbinati e ne revoca uno: il suo token smette subito di funzionare. Al massimo `pairing.max_devices` dispositivi; un dispositivo va abbinato di nuovo dopo `pairing.device_days` giorni (0 = mai). Il monitor conserva solo l'hash di ogni token in `devices.json` della cartella dei dati, un codice errato conta contro l'indirizzo come un token di accesso errato, e ogni abbinamento e ogni revoca lasciano una riga nel registro delle azioni.

| Percorso | Cosa fa |
|---|---|
| `GET /api/devices` | i dispositivi abbinati e se l'abbinamento è attivo (solo questo computer) |
| `POST /api/pair/start` | apre un codice monouso e risponde con il suo indirizzo e il suo codice QR (solo questo computer, con il token monouso della pagina) |
| `POST /api/pair/redeem` | il telefono usa il codice (`{"code": "..."}`) e riceve il suo cookie |
| `POST /api/devices/revoke` | revoca un dispositivo (`{"id": "..."}`; solo questo computer) |

- **Tavolozza e scorciatoie** (`ui.palette`): Ctrl+K apre una casella di ricerca di schede, repository e azioni; `?` elenca le scorciatoie, `/` va alla ricerca della scheda, `r` aggiorna e `[` `]` cambiano scheda.
