<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->


[🇺🇸 English](DEPLOYMENT.md) | [🇪🇸 Español](DEPLOYMENT_spa.md) | [🇫🇷 Français](DEPLOYMENT_fra.md) | [🇮🇹 Italiano](DEPLOYMENT_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](DEPLOYMENT_zho.md) | [🇯🇵 日本語](DEPLOYMENT_jpn.md) | [🇵🇹 Português](DEPLOYMENT_por.md)

# Als Dienst betreiben

Der Monitor ist ein Programm, das standardmäßig nur auf `127.0.0.1` lauscht und keine Anmeldung hat. Diese Hinweise gelten für den Betrieb als Dienst: das offizielle Image, Docker Compose mit Reverse-Proxy, eine klassische Installation mit systemd und was geschieht, wenn GitHub den Zugang widerruft.

## Wo er lauscht

Der Monitor lauscht auf eine von drei Arten, und die Seite, `GET /api/accounts`, `monitor_cli.py status` und `monitor_cli.py accounts` sagen welche: **dieser Rechner** (nur `127.0.0.1`: der Standard, ohne Anmeldung), **das Netzwerk** (der Netzwerkmodus, `listen.network`: lauscht auch auf `listen.host`, und jede Anfrage trägt das Zugriffstoken) oder **hinter einem Proxy** (der Netzwerkmodus mit einem davor angemeldeten Reverse-Proxy: `listen.proxy_public_host`, `listen.secure_cookie` oder `listen.trusted_proxy`). Image und Dienst-Unit sind für die zweite und dritte Art gemacht; ein von Hand gestarteter Monitor bleibt bei der ersten.

Im Netzwerkmodus folgt der Supervisor mehrerer Konten denselben Regeln wie der Monitor eines Kontos: das Zugriffstoken bei jeder Anfrage (Cookie, Header oder `POST /api/access`), Sperre nach falschen Token, die `Host`-Prüfung, optional TLS mit Ihrem Zertifikat, der zweite Port der Person am Rechner (`listen.local_port`), und die Schlüssel, die über die Erreichbarkeit entscheiden, der GitHub-Zugang und die Aktionen auf GitHub nur vom Rechner des Monitors aus (eine Anfrage aus dem Netzwerk erreicht das Konto als entfernt markiert).

## Ohne Browser, und die Gesundheitsprüfung

`python -m github_actions_monitor.service` ist der Einstieg eines Dienstes: Er bereitet Ordner und erstes Konto aus der Umgebung vor (siehe Tabelle unten) und startet den Monitor ohne Browser. `python actions_monitor.py --no-browser --port 8765` gilt weiter für einen Monitor, den Sie selbst verwalten.

`GET /api/health` antwortet `{"ok": true, "version": ..., "loaded": ..., "offline": ...}` samt dem Zustand des Aktualisierungszyklus und des GitHub-Zugangs des Kontos; es ruft GitHub nicht auf. `GET /api/health?deep=1` ist die tiefe Prüfung: Sie antwortet 503, wenn der Aktualisierungszyklus eines Kontos länger als `watchdog_minutes` läuft (30 Minuten bei 0) oder sein Thread fehlt; im Supervisor mehrerer Konten auch, wenn die Überwachungsschleife selbst stillsteht, der Zyklus IRGENDEINES Kontos hängt oder nach dem Start kein Konto antwortet. Ein Konto, dessen GitHub-Zugang unbrauchbar ist (blind), wird in der Antwort genannt, ist aber kein Fehler: Ein Neustart behebt keinen verlorenen Zugang, ein neuer schon.

`python -m github_actions_monitor.cli.healthcheck` macht diesen Aufruf für einen Container oder einen Dienstmanager (Exit-Code 0 gesund, 1 nicht gesund, 2 keine Antwort, 3 abgelehnt). Es liest das Zugriffstoken aus `MONITOR_ACCESS_TOKEN`, aus der Datei, die `MONITOR_ACCESS_TOKEN_FILE` nennt, oder aus der Datei, die der Dienst in `MONITOR_STATE_DIR` führt. `monitor_cli.py health --deep` tut dasselbe von jedem Rechner aus.

## Das offizielle Image

`ghcr.io/juanenrac/tools-github-actions-monitor` für `linux/amd64` und `linux/arm64`, mit den Tags `1.8.2`, `1.8` und `latest`, vom Release-Workflow mit einer Attestierung seiner Herkunft gebaut. Es entsteht in drei Stufen (`deploy/Dockerfile`) und enthält nur Python, die GitHub-CLI, die CA-Zertifikate und den Code, schreibgeschützt und im Besitz von root. Es läuft als Benutzer 10001 (nie als root) und schreibt nur in zwei Volumes: `/config` (`actions_monitor.json`, beim ersten Start angelegt und nie überschrieben) und `/data` (`accounts/`, `state/` mit dem Zugriffstoken, `secrets/`, der Zugang von `gh`). Es lauscht im Netzwerkmodus auf Port 8765 des Containers, jede Anfrage braucht also das Zugriffstoken, und es veröffentlicht von sich aus keinen Port.

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

Beim ersten Start legt es die Konfiguration an, das erste Konto (aus `MONITOR_GITHUB_OWNER`; mehrere mit `MONITOR_ACCOUNTS=privat:ich,arbeit:meine-org`) und, wenn `MONITOR_ACCESS_TOKEN` fehlt, ein Zugriffstoken, das es in `/data/state/access_token` (Modus 600) verwahrt und nie ausgibt. Öffnen Sie einmal `http://127.0.0.1:8765/?access=TOKEN`: Das Cookie wird gesetzt und die Adresse bereinigt. Bei einem Bind-Mount statt eines benannten Volumes übergeben Sie den Ordner dem Benutzer 10001 (`chown -R 10001:10001`). Die Lite-Edition ist nicht im Image.

## Docker Compose, mit optionalem Proxy und TLS

`deploy/compose.yaml` startet den Monitor mit schreibgeschütztem Code, ohne Capabilities, dem Zugang als Docker-Secret und den zwei Volumes. Das Profil `proxy` stellt Caddy (`deploy/Caddyfile`) davor: Es holt und erneuert das Zertifikat eines öffentlichen Namens selbst (`tls internal` für einen Namen im eigenen Netz, `http://name` für keines). Kopieren Sie `deploy/.env.example` nach `deploy/.env`, füllen Sie es aus und starten Sie:

```sh
cp deploy/.env.example deploy/.env                                   # fill in MONITOR_GITHUB_OWNER
printf '%s' "ghp_..." > deploy/gh_token.txt && chmod 600 deploy/gh_token.txt
docker compose -f deploy/compose.yaml up -d                          # on 127.0.0.1:8765
docker compose -f deploy/compose.yaml --profile proxy up -d          # behind Caddy (deploy/Caddyfile)
```

Hinter dem Proxy muss der Monitor seinen öffentlichen Namen kennen und wissen, dass die Sitzung HTTPS ist: `MONITOR_PROXY_PUBLIC_HOST` und `MONITOR_SECURE_COOKIE=1`. Nichts, was am Hauptport ankommt, gilt dann als der Rechner des Monitors: Nehmen Sie den zweiten Port (`MONITOR_LOCAL_PORT`, im Image 8766, nur Loopback) mit `docker compose exec monitor python monitor_cli.py ...` (das Image setzt `MONITOR_URL` darauf).

## Eine klassische Installation mit systemd

`deploy/github-actions-monitor.service` und `deploy/github-actions-monitor.env` betreiben das entpackte Release als Benutzer `monitor` mit der Härtung von systemd (nichts beschreibbar außer dem eigenen Ordner, keine neuen Privilegien), starten es bei Fehlern neu, prüfen nach dem Start die tiefe Gesundheit und lesen die Credential-Dateien bei `systemctl reload` neu.

```sh
useradd --system --home-dir /var/lib/github-actions-monitor --create-home --shell /usr/sbin/nologin monitor
install -d -o monitor -g monitor -m 700 /etc/github-actions-monitor
install -m 600 -o monitor deploy/github-actions-monitor.env /etc/github-actions-monitor/env     # edit it
install -m 644 deploy/github-actions-monitor.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now github-actions-monitor
systemctl reload github-actions-monitor                              # SIGHUP: read the credential files again
```

Die env-Datei hält die Daten in `/var/lib/github-actions-monitor` und den Zugang in `/etc/github-actions-monitor/gh_token` (Modus 600). Er lauscht auf `127.0.0.1`, solange Sie dort nicht den Netzwerkmodus einschalten.

launchd (macOS): `ProgramArguments` = `/usr/bin/python3`, `-m`, `github_actions_monitor.service`, die Variablen in `EnvironmentVariables`, `KeepAlive` und `RunAtLoad` true. Windows: `schtasks /Create /SC ONLOGON /TN GhaMonitor /TR "py -3 C:/pfad/zu/actions_monitor.py --no-browser"`.

## Umgebungsvariablen

Gelesen werden nur die Namen dieser Tabelle. Im Dienst wird ein nicht lesbarer Wert mit einem Hinweis ignoriert und ändert nichts. Die Variablen, die einen Teil der Konfiguration benennen (`MONITOR_LISTEN_*`, `MONITOR_ALLOWED_HOSTS`, `MONITOR_PROXY_PUBLIC_HOST`, `MONITOR_SECURE_COOKIE`, `MONITOR_TRUSTED_PROXY`, `MONITOR_LOCAL_PORT`, `MONITOR_TLS_*`, `MONITOR_QUERY_ACCESS`, `MONITOR_TEAM_MODE`), werden bei jedem Start des Dienstes in `listen` und `auth` geschrieben, die Umgebung bleibt dafür also maßgeblich; alles andere in der Datei gehört Ihnen.

| Variable | Was sie bewirkt |
|---|---|
| `MONITOR_GITHUB_OWNER` | Der zu überwachende Benutzer oder die Organisation; daraus wird beim ersten Start das erste Konto angelegt. |
| `MONITOR_ACCOUNT` | Die ID des ersten Kontos (Standard `default`). |
| `MONITOR_ACCOUNTS` | Mehrere Konten auf einmal: `privat:ich,arbeit:meine-org` (ID:Eigentümer). Nur, solange es noch kein Konto gibt. |
| `MONITOR_LANG` | Die Sprache der Texte (`en es de fr it ja zh pt`). |
| `MONITOR_PORT` | Der Port im Container oder des Dienstes (Standard 8765). |
| `MONITOR_CONFIG` | Die Konfigurationsdatei (im Image: `/config/actions_monitor.json`); wird beim ersten Start angelegt und nie überschrieben. |
| `MONITOR_ACCOUNTS_DIR` | Der Ordner der Konten, je Konto ein Ordner (im Image: `/data/accounts`). |
| `MONITOR_STATE_DIR` | Dateien, die sonst neben dem Code lägen: das Zugriffstoken des Dienstes, das Audit der Anmeldungen (im Image: `/data/state`). |
| `MONITOR_SECRET_DIR` | Wo das vom Monitor selbst verwahrte Token liegt, falls Sie das einschalten (im Image: `/data/secrets`). |
| `GH_CONFIG_DIR` | Der Konfigurationsordner von `gh` (im Image: `/data/gh`). |
| `GH_TOKEN_FILE` | Eine Datei mit dem GitHub-Token in der ersten Zeile (ein Docker-Secret, eine systemd-Credential). Wird beim Start und bei SIGHUP gelesen. |
| `GH_TOKEN` | Ein GitHub-Token in der Umgebung; `gh` liest es. Besser ist eine Datei: Die Umgebung sieht jeder Prozess des Containers. |
| `GH_HOST` | Ein Hostname eines GitHub Enterprise Servers: Alle Aufrufe und alle Links der Seite verwenden ihn. |
| `MONITOR_ACCESS_TOKEN` | Das Zugriffstoken des Netzwerkmodus (mindestens 16 Zeichen). Ohne es erzeugt der Dienst eines und legt es in `MONITOR_STATE_DIR` ab. |
| `MONITOR_ACCESS_TOKEN_FILE` | Eine Datei mit dem Zugriffstoken in der ersten Zeile, statt der Variable. |
| `MONITOR_LISTEN_NETWORK` | `1` = der Netzwerkmodus (`listen.network`): lauscht auf `MONITOR_LISTEN_HOST`, und jede Anfrage braucht das Zugriffstoken. Das Image setzt es. |
| `MONITOR_LISTEN_HOST` | Die Adresse, auf der er im Netzwerkmodus lauscht (im Image `0.0.0.0`; anderswo besser eine private Adresse des Rechners). |
| `MONITOR_ALLOWED_HOSTS` | Hostnamen, die der Monitor außer seiner eigenen Adresse annimmt, durch Kommas getrennt (`listen.allowed_hosts`). |
| `MONITOR_PROXY_PUBLIC_HOST` | Der öffentliche Name des Reverse-Proxys (`listen.proxy_public_host`); er meldet den Proxy an. |
| `MONITOR_SECURE_COOKIE` | `1` = die Sitzung ist HTTPS (ein Proxy beendet sie): Das Cookie bekommt Secure (`listen.secure_cookie`). |
| `MONITOR_TRUSTED_PROXY` | `1` = der Proxy läuft auf DEMSELBEN Rechner, und sein `X-Forwarded-For` wird geglaubt (`listen.trusted_proxy`). |
| `MONITOR_LOCAL_PORT` | Ein zweiter Port, nur Loopback, für die Person am Rechner, wenn ein Proxy angemeldet ist (`listen.local_port`; im Image 8766). |
| `MONITOR_TLS_CERT_FILE` | Ein Zertifikat (PEM), um HTTPS direkt auszuliefern (`listen.tls_cert_file`); mit Schlüssel. Ist es unbrauchbar, startet der Monitor nicht mit reinem HTTP. |
| `MONITOR_TLS_KEY_FILE` | Der private Schlüssel dieses Zertifikats (`listen.tls_key_file`). |
| `MONITOR_QUERY_ACCESS` | `0` = die Adresse mit `?access=` öffnet keine Sitzung mehr (`listen.query_access`); verwenden Sie `POST /api/access`. |
| `MONITOR_TEAM_MODE` | `1` = der Teammodus (`auth.enabled`): Benutzer, Rollen und Sitzungen. |
| `MONITOR_SERVICE` | `1` = läuft als Dienst: gibt bei einem unbrauchbaren Zugang nicht auf, und der Doctor prüft die Aufbewahrung. Image und Dienst setzen es. |
| `MONITOR_URL` | Für `monitor_cli.py` und die Gesundheitsprüfung: die Adresse des Monitors (im Image: der zweite Port). |
| `MONITOR_CA_FILE` | Für `monitor_cli.py`: eine PEM-Datei mit der Stelle, die das HTTPS-Zertifikat des Monitors signiert hat. |
| `MONITOR_USER` | Für `monitor_cli.py` im Teammodus: der Benutzer, als der man sich anmeldet. |
| `MONITOR_PASSWORD_FILE` | Für `monitor_cli.py`: eine Datei mit dem Passwort von `MONITOR_USER` in der ersten Zeile. |
| `MONITOR_RELEASE_TEST_TIMEOUT` | `tools/make_release.py`: Sekunden, die die gewöhnliche Suite brauchen darf, bevor die Schranke scheitert (Standard 3600; 60 bis 86400). |
| `MONITOR_RELEASE_CLEAN_TIMEOUT` | `tools/make_release.py`: Sekunden, die die Suite des entpackten Zips brauchen darf (Standard 3600; 60 bis 86400). |

## Wenn GitHub den Zugang widerruft oder er abläuft

Jedes Konto ist ein eigener Prozess, ein ausfallender Zugang betrifft also nur dieses Konto. Nach zwei Ablehnungen in Folge, die sagen, dass der Zugang selbst unbrauchbar ist (ein 401, `Bad credentials`, ein abgelaufenes oder widerrufenes Token, ein gesperrtes Konto, gar kein Zugang), ist das Konto **blind**: Die Seite, die tiefe Gesundheitsprüfung, `GET /api/accounts` (`state: blind`) und `monitor_cli.py` sagen es, ein **kritischer Systemalarm** (`system.credential_blind`, Wächter `system`) erscheint im Tab Alarme, und die Benachrichtigungsarten `credential_blind` (standardmäßig an) und `credential_back` informieren die Kanäle einmal. Die Ablehnung einer einzelnen Berechtigung (ein 403 für ein Repository) macht ein Konto nicht blind. Die anderen Konten laufen weiter, und die tiefe Gesundheitsprüfung bleibt grün. Das Konto versucht es weiter, und der erste gute Zyklus schließt den Alarm.

Ein Dienst, der mit einem schon unbrauchbaren Zugang startet, bleibt oben und blind, statt aufzugeben, damit es etwas zu ersetzen gibt. Das Token eines Kontos stammt aus dem, was zuerst zutrifft: die Datei `credential` in seinem Ordner (von einem Austausch geschrieben), die Datei, die `GH_TOKEN_FILE` nennt, dann das, was `gh` verwendet (`GH_TOKEN` oder sein eigener Login). Ein Austausch braucht keinen Neustart von Supervisor oder Konto, auf drei Wegen:

```sh
# 1. the command line (a token is read from a file or the standard input, never from a flag)
docker compose exec -T monitor python monitor_cli.py credential replace --account default --new-token-file - < new_token.txt
python monitor_cli.py credential replace --url https://monitor.example.org --user ann --password-file pw.txt --account default --new-token-file new_token.txt

# 2. the administrator endpoint (an administrator session in the team mode, or the computer of the monitor)
#    POST /api/accounts/<id>/credential   {"action": "replace", "token": "..."}   or   {"action": "reload"}
#    (a monitor without a supervisor: POST /api/credential, from its own computer)

# 3. replace the file and send SIGHUP: every account reads its credential files again
docker kill --signal HUP github-actions-monitor
systemctl reload github-actions-monitor
```

Das neue Token wird bei GitHub geprüft (der Aufruf `rate_limit`, kostenlos), BEVOR es behalten wird: Ein Token, das GitHub ablehnt, ändert nichts und antwortet 422 (`rejected`). Ein gutes wird nur in den Ordner dieses Kontos geschrieben (Modus 600), sofort verwendet, und das Konto liest ohne Wartezeit neu. Im Teammodus ist der Endpunkt für eine `admin`-Sitzung (mit dem CSRF-Token einer Cookie-Sitzung), und das Audit hält fest, wer es getan hat, nie das Token; ohne Teammodus darf bei eingeschaltetem Netzwerkmodus nur der Rechner des Monitors. Das Token steht nie in einer Antwort, einem Log, einem Alarm oder der Seite.

## Erster Start, Sicherung und Aktualisierung

Erster Start als Dienst: Eigentümer und Zugang (`GH_TOKEN_FILE`) setzen, starten, das Zugriffstoken einmal lesen (`/data/state/access_token`), die Seite öffnen und `monitor_cli.py health --deep` ausführen. `python actions_monitor.py --doctor` mit `MONITOR_SERVICE=1` warnt außerdem vor einem fehlenden Aufbewahrungsblock und vor Konten, die dasselbe Token teilen.

Sicherung: Alles, was bleiben soll, liegt in den zwei Volumes. Machen Sie vor einer Aktualisierung eine konsistente Kopie des Speichers und eine Kopie der Volumes:

```sh
docker compose exec monitor python /app/tools/backup_storage.py backup /data/state/backup.zip --backend file
docker cp github-actions-monitor:/data/state/backup.zip .
docker run --rm -v monitor-data:/data -v "$PWD":/backup alpine tar czf /backup/monitor-data.tgz -C /data .
```

Aktualisierung: Die Daten überleben, weil sie in den Volumes liegen. Legen Sie in der Produktion eine Version fest (`:1.8.2`), laden Sie, erstellen Sie neu und prüfen Sie die Attestierung des Images. Ein neuerer Speicher wird von einem älteren Monitor nie geöffnet (siehe `STORAGE.md`); behalten Sie die Sicherung, bis die neue Version gelaufen ist.

```sh
docker compose pull && docker compose up -d
gh attestation verify oci://ghcr.io/juanenrac/tools-github-actions-monitor:1.8.2 --owner JuanenRac
```

## Hinter einem Reverse-Proxy

Standardmäßig lauscht der Monitor nur auf `127.0.0.1`. Wenn du ihn von einem anderen Rechner aus erreichen musst, setze einen Reverse-Proxy mit TLS davor, schalte den Netzwerkmodus ein (`listen.network`: dann muss jede Anfrage das Zugriffstoken tragen) und DEKLARIERE den Proxy (`listen.proxy_public_host` mit seinem öffentlichen Namen, `listen.secure_cookie` oder `listen.trusted_proxy`). Der Monitor weist jede Anfrage ab, deren `Host` nicht seine eigene Adresse oder dieser öffentliche Name ist; der Proxy muss ihn also senden und die echte Adresse des Clients anfügen:

```nginx
location / {
    proxy_pass           http://127.0.0.1:8765;
    proxy_set_header     Host $host;                                  # the public name: set it in listen.proxy_public_host
    proxy_set_header     X-Forwarded-For $proxy_add_x_forwarded_for;  # APPENDS the real address of the client; never copy the one the client sent
    proxy_set_header     X-Forwarded-Proto $scheme;
}
```

Sobald ein Proxy deklariert ist, gilt nichts, was am Hauptport ankommt, als „dieser Computer“, was auch immer die Header sagen (ein Proxy, der einen Header vergisst, ließe sonst jeden Client des Internets lokal aussehen). Die Schlüssel, die die Erreichbarkeit bestimmen, die Aktionen auf GitHub und die Tests der Kanäle lassen sich von dort daher nicht verwenden. Um sie zu nutzen, öffne mit `listen.local_port` (eine Zahl von 1024 bis 65535) einen zweiten Port, der nur auf `127.0.0.1` lauscht, und benutze ihn am Rechner des Monitors: Er verlangt dasselbe Zugriffstoken.

`listen.trusted_proxy` setzt voraus, dass der Proxy auf DEMSELBEN Rechner wie der Monitor läuft (der Monitor glaubt `X-Forwarded-For` bei jeder Verbindung über Loopback): Verwende es nicht mit einem Proxy auf einem anderen Rechner. Die falschen Tokens aller Clients des Proxys werden außerdem zusammen gezählt (das Dreifache des Limits einer Adresse), damit das Ändern des Headers bei jedem Versuch die Sperre nicht aushebelt.

## Die Kommandozeile gegen einen anderen Rechner

`monitor_cli.py` arbeitet gegen einen Monitor auf einer anderen Maschine: `--url https://monitor.example.org` (oder `MONITOR_URL`), das Zugriffstoken aus `MONITOR_ACCESS_TOKEN` oder `--token-file`, `--ca-file` (oder `MONITOR_CA_FILE`), um der Stelle zu vertrauen, die ein eigenes HTTPS-Zertifikat signiert hat, und im Teammodus `--user NAME` mit `--password-file DATEI` (oder `MONITOR_USER`, `MONITOR_PASSWORD_FILE`), das sich mit einer Bearer-Sitzung anmeldet (`auth.allow_bearer`). `status`, `accounts`, `alerts`, `health` (`--deep`) und `credential` funktionieren gleich, und die Exit-Codes sind dieselben (3 = abgelehnt, auch für ein blindes Konto bei `status` und `accounts`). Reines HTTP zu einem anderen Rechner gibt eine Warnung aus.

## Mindestberechtigungen des Logins (`gh` oder ein feingranulares Token)

- Run-Listen, Jobs und Issues: Actions (lesen), Issues (lesen), Metadata (lesen). Warnungen: Code-Scanning-, Dependabot- und Secret-Scanning-Warnungen (lesen). Pull Requests und Releases: Pull requests (lesen), Contents (lesen). Pakete: `read:packages`.
- Nur die optionalen KI-Aktionen schreiben: Einen Workflow neu zu starten braucht Actions (schreiben), ein Issue zu schließen Issues (schreiben). Lassen Sie sie aus und geben Sie dem Login nur Leserechte.

## Viele Repositorys

Bedingte Lesungen (`cache.etag`) lassen ein unverändertes Repository kein Kontingent kosten; `mode: lite`, `ecosystems`, `exclude` und `max_workers` begrenzen die Arbeit; der eingehende Webhook ersetzt das Abfragen der Repositorys, die Ereignisse senden. `discover_limit` ist die Höchstzahl aufgelisteter Repositorys je Konto (Standard 1000).

## Monatelanger Betrieb: Speicherung und Aufbewahrung

Legen Sie `accounts/` (oder die Datenbank) auf ein Volume, das den Container überlebt, und sichern Sie vor einem Update mit `python tools/backup_storage.py backup DATEI.zip --backend file` (oder `sqlite`). Werkseitig entfernt ein kurzer Durchlauf Ereignisse älter als 90 Tage und Analysen älter als 180 Tage; ändern Sie das mit `retention` in der Konfiguration, und `MONITOR_SERVICE=1` lässt `--doctor` den Monitor als Dienst behandeln (dann warnt es, wenn der `retention`-Block fehlt oder die Ereignisse groß werden). Bei SQLite ist eine Datenbank pro Konto der Standard; eine gemeinsame Datei ist möglich und in [STORAGE_deu.md](STORAGE_deu.md) beschrieben.
