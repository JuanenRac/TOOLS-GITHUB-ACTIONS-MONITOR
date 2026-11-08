<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](DEPLOYMENT.md) | [🇪🇸 Español](DEPLOYMENT_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](DEPLOYMENT_ita.md) | [🇩🇪 Deutsch](DEPLOYMENT_deu.md) | [🇨🇳 简体中文](DEPLOYMENT_zho.md) | [🇯🇵 日本語](DEPLOYMENT_jpn.md) | [🇵🇹 Português](DEPLOYMENT_por.md)

# L'exécuter comme un service

Le moniteur est un programme local qui n'écoute que sur `127.0.0.1` et n'a pas de connexion. Ces notes servent à l'exécuter sans navigateur, sur un serveur ou dans un conteneur, pour un compte ou une organisation.

## Sans navigateur

`python actions_monitor.py --no-browser --port 8765`. `GET /api/health` répond `{"ok": true, "version": ..., "loaded": ..., "offline": ...}` pour un gestionnaire de services ou un contrôle de conteneur ; il n'appelle pas GitHub.


## Configuration et environnement

- Tout est dans `actions_monitor.json` ; l'environnement ajoute `GH_HOST` (nom d'hôte d'un GitHub Enterprise Server : tous les appels et tous les liens de la page l'utilisent), `GH_TOKEN` (lu par `gh` ; le moniteur ne le stocke jamais), `MONITOR_LANG`, `MONITOR_ECOSYSTEMS_FILE`, `MONITOR_TARGETS_FILE` et `MONITOR_PROFILES_FILE`.
- `github_owner` peut être un utilisateur ou une organisation. Pour surveiller plusieurs comptes, lancez un moniteur par compte, chacun avec son port et son dossier.


## Exemples à adapter

systemd :

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

Conteneur :

```dockerfile
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

- launchd : `~/Library/LaunchAgents/org.example.ghamon.plist`: `ProgramArguments` = `/usr/bin/python3`, `actions_monitor.py`, `--no-browser`; `WorkingDirectory` = the folder; `KeepAlive` = true; `RunAtLoad` = true.
- Windows : `schtasks /Create /SC ONLOGON /TN GhaMonitor /TR "py -3 C:/path/to/actions_monitor.py --no-browser"`


## Derrière un reverse proxy

Gardez le moniteur sur `127.0.0.1` et ne le liez jamais à `0.0.0.0` : il n'a pas de connexion. Si vous devez l'atteindre depuis une autre machine, placez devant un reverse proxy avec authentification et TLS. Le moniteur refuse toute requête dont le `Host` n'est pas sa propre adresse ; le proxy doit donc l'envoyer :

```nginx
location / {
    auth_basic           "monitor";
    auth_basic_user_file /etc/nginx/monitor.htpasswd;
    proxy_pass           http://127.0.0.1:8765;
    proxy_set_header     Host 127.0.0.1:8765;   # the monitor refuses any other Host
}
```


## Permissions minimales de la connexion (`gh` ou un jeton à granularité fine)

- Listes de runs, jobs et issues : Actions (lecture), Issues (lecture), Metadata (lecture). Alertes : alertes Code scanning, Dependabot et Secret scanning (lecture). Pull requests et releases : Pull requests (lecture), Contents (lecture). Paquets : `read:packages`.
- Seules les actions optionnelles de l'IA écrivent : relancer un workflow demande Actions (écriture) et fermer une issue demande Issues (écriture). Laissez-les désactivées et ne donnez à la connexion que la lecture.


## Beaucoup de dépôts

Les lectures conditionnelles (`cache.etag`) font qu'un dépôt inchangé ne coûte aucun quota ; `mode: lite`, `ecosystems`, `exclude` et `max_workers` limitent le travail ; le webhook entrant supprime l'interrogation des dépôts qui envoient des événements. `discover_limit` est le nombre maximal de dépôts listés pour un compte (1000 par défaut).
