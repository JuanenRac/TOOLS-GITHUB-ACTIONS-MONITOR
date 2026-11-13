<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](DEPLOYMENT.md) | **🇪🇸 Español** | [🇫🇷 Français](DEPLOYMENT_fra.md) | [🇮🇹 Italiano](DEPLOYMENT_ita.md) | [🇩🇪 Deutsch](DEPLOYMENT_deu.md) | [🇨🇳 简体中文](DEPLOYMENT_zho.md) | [🇯🇵 日本語](DEPLOYMENT_jpn.md) | [🇵🇹 Português](DEPLOYMENT_por.md)

# Ejecutarlo como servicio

El monitor es un programa local que escucha solo en `127.0.0.1` y no tiene login. Estas notas son para ejecutarlo sin navegador, en un servidor o en un contenedor, para una cuenta o para una organización.

## Sin navegador

`python actions_monitor.py --no-browser --port 8765`. `GET /api/health` responde `{"ok": true, "version": ..., "loaded": ..., "offline": ...}` para un gestor de servicios o una comprobación de contenedor; no llama a GitHub.


## Configuración y entorno

- Todo vive en `actions_monitor.json`; el entorno añade `GH_HOST` (el nombre de host de un GitHub Enterprise Server: todas las llamadas y todos los enlaces de la página lo usan), `GH_TOKEN` (lo lee `gh`; el monitor nunca lo guarda), `MONITOR_LANG`, `MONITOR_ECOSYSTEMS_FILE`, `MONITOR_TARGETS_FILE` y `MONITOR_PROFILES_FILE`.
- `github_owner` puede ser un usuario o una organización. Para vigilar varias cuentas, ejecuta un monitor por cuenta, cada uno con su puerto y su carpeta.


## Ejemplos para adaptar

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

Contenedor:

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


## Detrás de un proxy inverso

Mantén el monitor en `127.0.0.1` y nunca lo enlaces a `0.0.0.0`: no tiene login. Si necesitas llegar desde otra máquina, pon delante un proxy inverso con autenticación y TLS. El monitor rechaza cualquier petición cuyo `Host` no sea su propia dirección, así que el proxy debe enviarlo:

```nginx
location / {
    auth_basic           "monitor";
    auth_basic_user_file /etc/nginx/monitor.htpasswd;
    proxy_pass           http://127.0.0.1:8765;
    proxy_set_header     Host 127.0.0.1:8765;   # the monitor refuses any other Host
}
```


## Permisos mínimos del acceso (`gh` o un token de granularidad fina)

- Listas de runs, jobs e issues: Actions (lectura), Issues (lectura), Metadata (lectura). Alertas: alertas de Code scanning, Dependabot y Secret scanning (lectura). Pull requests y releases: Pull requests (lectura), Contents (lectura). Paquetes: `read:packages`.
- Solo las acciones opcionales de la IA escriben: relanzar un workflow necesita Actions (escritura) y cerrar un issue necesita Issues (escritura). Déjalas apagadas y da al acceso solo lectura.


## Muchos repositorios

Las lecturas condicionales (`cache.etag`) hacen que un repositorio sin cambios no cueste cuota; `mode: lite`, `ecosystems`, `exclude` y `max_workers` limitan el trabajo; el webhook de entrada elimina el sondeo de los repositorios que envían eventos. `discover_limit` es el máximo de repositorios listados de una cuenta (1000 por defecto).

## Funcionando durante meses: almacenamiento y retención

Guarda `accounts/` (o la base de datos) en un volumen que sobreviva al contenedor y haz una copia con `python tools/backup_storage.py backup FILE.zip --backend file` (o `sqlite`) antes de actualizar. De fábrica, una pasada corta elimina los eventos de más de 90 días y las analíticas de más de 180; define `retention` en la configuración para cambiarlo, y `MONITOR_SERVICE=1` hace que `--doctor` trate el monitor como un servicio (entonces avisa si no hay bloque `retention` o si los eventos crecen mucho). Con SQLite lo predeterminado es una base por cuenta; un archivo compartido es posible y está documentado en [STORAGE_spa.md](STORAGE_spa.md).
