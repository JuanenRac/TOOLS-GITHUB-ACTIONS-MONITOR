<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](DEPLOYMENT.md) | [🇪🇸 Español](DEPLOYMENT_spa.md) | [🇫🇷 Français](DEPLOYMENT_fra.md) | [🇮🇹 Italiano](DEPLOYMENT_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](DEPLOYMENT_zho.md) | [🇯🇵 日本語](DEPLOYMENT_jpn.md) | [🇵🇹 Português](DEPLOYMENT_por.md)

# Als Dienst betreiben

Der Monitor ist ein lokales Programm, das nur auf `127.0.0.1` lauscht und keinen Login hat. Diese Hinweise gelten für den Betrieb ohne Browser, auf einem Server oder in einem Container, für ein Konto oder eine Organisation.

## Ohne Browser

`python actions_monitor.py --no-browser --port 8765`. `GET /api/health` antwortet `{"ok": true, "version": ..., "loaded": ..., "offline": ...}` für einen Dienstmanager oder eine Container-Prüfung; es ruft GitHub nicht auf.


## Konfiguration und Umgebung

- Alles steht in `actions_monitor.json`; die Umgebung ergänzt `GH_HOST` (Hostname eines GitHub Enterprise Servers: alle Aufrufe und alle Links der Seite nutzen ihn), `GH_TOKEN` (von `gh` gelesen; der Monitor speichert es nie), `MONITOR_LANG`, `MONITOR_ECOSYSTEMS_FILE`, `MONITOR_TARGETS_FILE` und `MONITOR_PROFILES_FILE`.
- `github_owner` kann ein Benutzer oder eine Organisation sein. Für mehrere Konten starten Sie je Konto einen Monitor mit eigenem Port und Ordner.


## Beispiele zum Anpassen

systemd:

```ini
# /etc/systemd/system/github-actions-monitor.service
[Unit]
Description=GitHub Actions monitor
After=network-online.target

[Service]
User=monitor
WorkingDirectory=/opt/github_actions_monitor
EnvironmentFile=/etc/github-actions-monitor/env     # a file with a line GH_TOKEN=... (mode 600)
ExecStart=/usr/bin/python3 actions_monitor.py --no-browser --port 8765
Restart=on-failure
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/github_actions_monitor

[Install]
WantedBy=multi-user.target
```

Container:

```dockerfile
# the same file is deploy/Dockerfile of the repository (the CI builds it)
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
 && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /usr/share/keyrings/githubcli.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/githubcli.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list \
 && apt-get update && apt-get install -y gh && rm -rf /var/lib/apt/lists/*
COPY github_actions_monitor /app
WORKDIR /app
USER 1000
CMD ["python", "actions_monitor.py", "--no-browser", "--port", "8765"]
```
```yaml
# docker-compose.yml: the monitor only listens on 127.0.0.1, so on Linux share the host network namespace
services:
  monitor:
    build: .
    network_mode: host
    environment:
      GH_TOKEN: ${GH_TOKEN}          # a token with the minimum permissions listed below
    volumes:
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8765/api/health', timeout=4)"]
```

- launchd: `~/Library/LaunchAgents/org.example.ghamon.plist`: `ProgramArguments` = `/usr/bin/python3`, `actions_monitor.py`, `--no-browser`; `WorkingDirectory` = the folder; `KeepAlive` = true; `RunAtLoad` = true.
- Windows: `schtasks /Create /SC ONLOGON /TN GhaMonitor /TR "py -3 C:/path/to/actions_monitor.py --no-browser"`


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

## Mindestberechtigungen des Logins (`gh` oder ein feingranulares Token)

- Run-Listen, Jobs und Issues: Actions (lesen), Issues (lesen), Metadata (lesen). Warnungen: Code-Scanning-, Dependabot- und Secret-Scanning-Warnungen (lesen). Pull Requests und Releases: Pull requests (lesen), Contents (lesen). Pakete: `read:packages`.
- Nur die optionalen KI-Aktionen schreiben: Einen Workflow neu zu starten braucht Actions (schreiben), ein Issue zu schließen Issues (schreiben). Lassen Sie sie aus und geben Sie dem Login nur Leserechte.


## Viele Repositorys

Bedingte Lesungen (`cache.etag`) lassen ein unverändertes Repository kein Kontingent kosten; `mode: lite`, `ecosystems`, `exclude` und `max_workers` begrenzen die Arbeit; der eingehende Webhook ersetzt das Abfragen der Repositorys, die Ereignisse senden. `discover_limit` ist die Höchstzahl aufgelisteter Repositorys je Konto (Standard 1000).

## Monatelanger Betrieb: Speicherung und Aufbewahrung

Legen Sie `accounts/` (oder die Datenbank) auf ein Volume, das den Container überlebt, und sichern Sie vor einem Update mit `python tools/backup_storage.py backup DATEI.zip --backend file` (oder `sqlite`). Werkseitig entfernt ein kurzer Durchlauf Ereignisse älter als 90 Tage und Analysen älter als 180 Tage; ändern Sie das mit `retention` in der Konfiguration, und `MONITOR_SERVICE=1` lässt `--doctor` den Monitor als Dienst behandeln (dann warnt es, wenn der `retention`-Block fehlt oder die Ereignisse groß werden). Bei SQLite ist eine Datenbank pro Konto der Standard; eine gemeinsame Datei ist möglich und in [STORAGE_deu.md](STORAGE_deu.md) beschrieben.
