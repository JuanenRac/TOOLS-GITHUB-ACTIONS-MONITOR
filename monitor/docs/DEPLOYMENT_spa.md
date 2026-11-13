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

Por defecto el monitor solo escucha en `127.0.0.1`. Si necesitas llegar desde otra máquina, pon delante un proxy inverso con TLS, activa el modo red (`listen.network`: entonces cada petición debe llevar el token de acceso) y DECLARA el proxy (`listen.proxy_public_host` con su nombre público, `listen.secure_cookie` o `listen.trusted_proxy`). El monitor rechaza cualquier petición cuyo `Host` no sea su propia dirección o ese nombre público, así que el proxy debe enviarlo, y debe añadir la dirección real del cliente:

```nginx
location / {
    proxy_pass           http://127.0.0.1:8765;
    proxy_set_header     Host $host;                                  # the public name: set it in listen.proxy_public_host
    proxy_set_header     X-Forwarded-For $proxy_add_x_forwarded_for;  # APPENDS the real address of the client; never copy the one the client sent
    proxy_set_header     X-Forwarded-Proto $scheme;
}
```

Con un proxy declarado, nada de lo que llegue por el puerto principal cuenta como «este equipo», diga lo que diga en sus cabeceras (un proxy que olvide una cabecera haría que todos los clientes de internet parecieran locales). Por eso las claves que deciden la exposición, las acciones en GitHub y las pruebas de los canales no se pueden usar desde ahí. Para usarlas, abre un segundo puerto que solo escuche en `127.0.0.1` con `listen.local_port` (un número de 1024 a 65535) y úsalo desde el equipo del monitor: pide el mismo token de acceso.

`listen.trusted_proxy` supone que el proxy corre en el MISMO equipo que el monitor (el monitor se fía de `X-Forwarded-For` en cualquier conexión que llegue por loopback): no lo uses con un proxy en otra máquina. Los tokens erróneos de todos los clientes del proxy se cuentan además juntos (tres veces el límite de una dirección), para que cambiar la cabecera en cada intento no anule el bloqueo.

## Permisos mínimos del acceso (`gh` o un token de granularidad fina)

- Listas de runs, jobs e issues: Actions (lectura), Issues (lectura), Metadata (lectura). Alertas: alertas de Code scanning, Dependabot y Secret scanning (lectura). Pull requests y releases: Pull requests (lectura), Contents (lectura). Paquetes: `read:packages`.
- Solo las acciones opcionales de la IA escriben: relanzar un workflow necesita Actions (escritura) y cerrar un issue necesita Issues (escritura). Déjalas apagadas y da al acceso solo lectura.


## Muchos repositorios

Las lecturas condicionales (`cache.etag`) hacen que un repositorio sin cambios no cueste cuota; `mode: lite`, `ecosystems`, `exclude` y `max_workers` limitan el trabajo; el webhook de entrada elimina el sondeo de los repositorios que envían eventos. `discover_limit` es el máximo de repositorios listados de una cuenta (1000 por defecto).
