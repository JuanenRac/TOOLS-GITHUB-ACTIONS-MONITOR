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

Lassen Sie den Monitor auf `127.0.0.1` und binden Sie ihn nie an `0.0.0.0`: Er hat keinen Login. Wenn Sie ihn von einem anderen Rechner erreichen müssen, setzen Sie einen Reverse-Proxy mit Authentifizierung und TLS davor. Der Monitor lehnt jede Anfrage ab, deren `Host` nicht seine eigene Adresse ist; der Proxy muss ihn also senden:

```nginx
location / {
    auth_basic           "monitor";
    auth_basic_user_file /etc/nginx/monitor.htpasswd;
    proxy_pass           http://127.0.0.1:8765;
    proxy_set_header     Host 127.0.0.1:8765;   # the monitor refuses any other Host
}
```


## Mindestberechtigungen des Logins (`gh` oder ein feingranulares Token)

- Run-Listen, Jobs und Issues: Actions (lesen), Issues (lesen), Metadata (lesen). Warnungen: Code-Scanning-, Dependabot- und Secret-Scanning-Warnungen (lesen). Pull Requests und Releases: Pull requests (lesen), Contents (lesen). Pakete: `read:packages`.
- Nur die optionalen KI-Aktionen schreiben: Einen Workflow neu zu starten braucht Actions (schreiben), ein Issue zu schließen Issues (schreiben). Lassen Sie sie aus und geben Sie dem Login nur Leserechte.


## Viele Repositorys

Bedingte Lesungen (`cache.etag`) lassen ein unverändertes Repository kein Kontingent kosten; `mode: lite`, `ecosystems`, `exclude` und `max_workers` begrenzen die Arbeit; der eingehende Webhook ersetzt das Abfragen der Repositorys, die Ereignisse senden. `discover_limit` ist die Höchstzahl aufgelisteter Repositorys je Konto (Standard 1000).
