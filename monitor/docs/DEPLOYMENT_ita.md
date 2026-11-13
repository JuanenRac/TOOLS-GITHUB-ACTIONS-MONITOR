<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](DEPLOYMENT.md) | [🇪🇸 Español](DEPLOYMENT_spa.md) | [🇫🇷 Français](DEPLOYMENT_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](DEPLOYMENT_deu.md) | [🇨🇳 简体中文](DEPLOYMENT_zho.md) | [🇯🇵 日本語](DEPLOYMENT_jpn.md) | [🇵🇹 Português](DEPLOYMENT_por.md)

# Eseguirlo come servizio

Il monitor è un programma locale che ascolta solo su `127.0.0.1` e non ha login. Queste note servono per eseguirlo senza browser, su un server o in un container, per un account o per un'organizzazione.

## Senza browser

`python actions_monitor.py --no-browser --port 8765`. `GET /api/health` risponde `{"ok": true, "version": ..., "loaded": ..., "offline": ...}` per un gestore di servizi o un controllo del container; non chiama GitHub.


## Configurazione e ambiente

- Tutto sta in `actions_monitor.json`; l'ambiente aggiunge `GH_HOST` (nome host di un GitHub Enterprise Server: tutte le chiamate e tutti i link della pagina lo usano), `GH_TOKEN` (letto da `gh`; il monitor non lo salva mai), `MONITOR_LANG`, `MONITOR_ECOSYSTEMS_FILE`, `MONITOR_TARGETS_FILE` e `MONITOR_PROFILES_FILE`.
- `github_owner` può essere un utente o un'organizzazione. Per osservare più account, esegui un monitor per account, ciascuno con la sua porta e la sua cartella.


## Esempi da adattare

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


## Dietro un reverse proxy

Tieni il monitor su `127.0.0.1` e non associarlo mai a `0.0.0.0`: non ha login. Se devi raggiungerlo da un'altra macchina, metti davanti un reverse proxy con autenticazione e TLS. Il monitor rifiuta ogni richiesta il cui `Host` non sia il proprio indirizzo; il proxy deve quindi inviarlo:

```nginx
location / {
    auth_basic           "monitor";
    auth_basic_user_file /etc/nginx/monitor.htpasswd;
    proxy_pass           http://127.0.0.1:8765;
    proxy_set_header     Host 127.0.0.1:8765;   # the monitor refuses any other Host
}
```


## Permessi minimi dell'accesso (`gh` o un token a granularità fine)

- Elenchi di run, job e issue: Actions (lettura), Issues (lettura), Metadata (lettura). Avvisi: avvisi di Code scanning, Dependabot e Secret scanning (lettura). Pull request e release: Pull requests (lettura), Contents (lettura). Pacchetti: `read:packages`.
- Solo le azioni facoltative dell'IA scrivono: rilanciare un workflow richiede Actions (scrittura) e chiudere un issue richiede Issues (scrittura). Lasciale spente e dai all'accesso la sola lettura.


## Molti repository

Le letture condizionali (`cache.etag`) fanno sì che un repository invariato non costi quota; `mode: lite`, `ecosystems`, `exclude` e `max_workers` limitano il lavoro; il webhook in ingresso elimina l'interrogazione dei repository che inviano eventi. `discover_limit` è il massimo di repository elencati per un account (1000 predefinito).

## Attivo per mesi: archiviazione e conservazione

Tieni `accounts/` (o il database) su un volume che sopravvive al container e fai una copia con `python tools/backup_storage.py backup FILE.zip --backend file` (o `sqlite`) prima di un aggiornamento. Di serie un breve passaggio rimuove gli eventi più vecchi di 90 giorni e le analisi più vecchie di 180; imposta `retention` nella configurazione per cambiarlo, e `MONITOR_SERVICE=1` fa trattare il monitor come un servizio a `--doctor` (che poi avvisa se manca il blocco `retention` o se gli eventi diventano grandi). Con SQLite il predefinito è un database per account; un file condiviso è possibile ed è descritto in [STORAGE_ita.md](STORAGE_ita.md).
