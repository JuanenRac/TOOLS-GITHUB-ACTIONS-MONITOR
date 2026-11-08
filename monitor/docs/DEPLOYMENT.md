<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

**🇺🇸 English** | [🇪🇸 Español](DEPLOYMENT_spa.md) | [🇫🇷 Français](DEPLOYMENT_fra.md) | [🇮🇹 Italiano](DEPLOYMENT_ita.md) | [🇩🇪 Deutsch](DEPLOYMENT_deu.md) | [🇨🇳 简体中文](DEPLOYMENT_zho.md) | [🇯🇵 日本語](DEPLOYMENT_jpn.md) | [🇵🇹 Português](DEPLOYMENT_por.md)

# Running it as a service

The monitor is a local program that listens on `127.0.0.1` only and has no login. These notes are for running it without a browser, on a server or in a container, for one account or for an organisation.

## Without a browser

`python actions_monitor.py --no-browser --port 8765`. `GET /api/health` answers `{"ok": true, "version": ..., "loaded": ..., "offline": ...}` for a service manager or a container check; it makes no call to GitHub.


## Configuration and environment

- Everything lives in `actions_monitor.json`; the environment adds `GH_HOST` (a GitHub Enterprise Server host name: every call and every link of the page then use it), `GH_TOKEN` (read by `gh`; the monitor never stores it), `MONITOR_LANG`, `MONITOR_ECOSYSTEMS_FILE`, `MONITOR_TARGETS_FILE` and `MONITOR_PROFILES_FILE`.
- `github_owner` can be a user or an organisation. To watch several accounts, run one monitor per account on its own port and folder.


## Examples to adapt

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


## Behind a reverse proxy

Keep the monitor on `127.0.0.1` and never bind it to `0.0.0.0`: it has no login. If you must reach it from another machine, put a reverse proxy with authentication and TLS in front. The monitor refuses any request whose `Host` is not its own address, so the proxy must send it:

```nginx
location / {
    auth_basic           "monitor";
    auth_basic_user_file /etc/nginx/monitor.htpasswd;
    proxy_pass           http://127.0.0.1:8765;
    proxy_set_header     Host 127.0.0.1:8765;   # the monitor refuses any other Host
}
```


## Minimum permissions of the login (`gh` or a fine-grained token)

- Run lists, jobs and issues: Actions (read), Issues (read), Metadata (read). Alerts: Code scanning, Dependabot and Secret scanning alerts (read). Pull requests and releases: Pull requests (read), Contents (read). Packages: `read:packages`.
- Only the optional AI actions write: re-running a workflow needs Actions (write) and closing an issue needs Issues (write). Leave them off and give the login read access only.


## Many repositories

Conditional reads (`cache.etag`) make an unchanged repository cost no quota; `mode: lite`, `ecosystems`, `exclude` and `max_workers` limit the work; the incoming webhook removes the polling of the repositories that send events. `discover_limit` is the most repositories listed for an account (default 1000).
