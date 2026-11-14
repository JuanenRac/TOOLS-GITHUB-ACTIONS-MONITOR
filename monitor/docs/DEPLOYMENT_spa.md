<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->


[🇺🇸 English](DEPLOYMENT.md) | **🇪🇸 Español** | [🇫🇷 Français](DEPLOYMENT_fra.md) | [🇮🇹 Italiano](DEPLOYMENT_ita.md) | [🇩🇪 Deutsch](DEPLOYMENT_deu.md) | [🇨🇳 简体中文](DEPLOYMENT_zho.md) | [🇯🇵 日本語](DEPLOYMENT_jpn.md) | [🇵🇹 Português](DEPLOYMENT_por.md)

# Ejecutarlo como servicio

El monitor es un programa que, por defecto, escucha solo en `127.0.0.1` y no tiene login. Estas notas son para ejecutarlo como servicio: la imagen oficial, Docker Compose con un proxy inverso, una instalación clásica con systemd, y lo que pasa cuando GitHub revoca el acceso.

## Dónde escucha

El monitor escucha de una de tres maneras, y la página, `GET /api/accounts`, `bin/monitor_cli.py status` y `bin/monitor_cli.py accounts` dicen cuál: **este equipo** (solo `127.0.0.1`: lo predeterminado, sin login), **la red** (el modo red, `listen.network`: escucha también en `listen.host` y toda petición lleva el token de acceso) o **tras un proxy** (el modo red con un proxy inverso declarado delante: `listen.proxy_public_host`, `listen.secure_cookie` o `listen.trusted_proxy`). La imagen y la unidad del servicio están hechas para la segunda y la tercera; un monitor que arrancas a mano se queda en la primera.

En el modo red el supervisor de varias cuentas sigue las mismas reglas que el monitor de una cuenta: el token de acceso en cada petición (cookie, cabecera o `POST /api/access`), bloqueo tras tokens erróneos, la comprobación de `Host`, TLS opcional con tu certificado, el segundo puerto de quien está en el equipo (`listen.local_port`), y las claves que deciden la exposición, el acceso a GitHub y las acciones sobre GitHub solo desde el equipo del monitor (una petición de la red llega a la cuenta marcada como remota).

## Sin navegador y la comprobación de salud

`python -m github_actions_monitor.service` es la entrada de un servicio: prepara las carpetas y la primera cuenta a partir del entorno (ver la tabla de abajo) y arranca el monitor sin navegador. `python bin/actions_monitor.py --no-browser --port 8765` sigue valiendo para un monitor que gestionas tú.

`GET /api/health` responde `{"ok": true, "version": ..., "loaded": ..., "offline": ...}` más el estado del ciclo de refresco y del acceso a GitHub de la cuenta; no llama a GitHub. `GET /api/health?deep=1` es la comprobación profunda: responde 503 cuando el ciclo de refresco de una cuenta lleva más de `watchdog_minutes` (30 minutos si es 0) o su hilo ha desaparecido; en el supervisor de varias cuentas también cuando el propio bucle de supervisión se ha parado, cuando el ciclo de CUALQUIER cuenta está atascado o cuando ninguna cuenta responde pasado el arranque. Una cuenta cuyo acceso a GitHub no sirve (ciega) se nombra en la respuesta pero no es un fallo: reiniciar no arregla un acceso perdido, uno nuevo sí.

`python -m github_actions_monitor.cli.healthcheck` hace esa llamada para un contenedor o un gestor de servicios (código de salida 0 sano, 1 no sano, 2 sin respuesta, 3 rechazado). Lee el token de acceso de `MONITOR_ACCESS_TOKEN`, del archivo que indica `MONITOR_ACCESS_TOKEN_FILE` o del que el servicio guarda en `MONITOR_STATE_DIR`. `bin/monitor_cli.py health --deep` hace lo mismo desde cualquier equipo.

## La imagen oficial

`ghcr.io/juanenrac/tools-github-actions-monitor` para `linux/amd64` y `linux/arm64`, con las etiquetas `1.8.2`, `1.8` y `latest`, construida por el flujo de publicación con una atestación de su procedencia. Se hace en tres etapas (`deploy/Dockerfile`) y contiene solo Python, la CLI de GitHub, los certificados de las CA y el código, de solo lectura y de root. Corre como el usuario 10001 (nunca como root) y solo escribe en dos volúmenes: `/config` (`actions_monitor.json`, creado en el primer arranque y nunca sobrescrito) y `/data` (`accounts/`, `state/` con el token de acceso, `secrets/`, el acceso de `gh`). Escucha en el modo red en el puerto 8765 del contenedor, así que toda petición necesita el token de acceso, y no publica ningún puerto por sí misma.

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

En el primer arranque crea la configuración, la primera cuenta (a partir de `MONITOR_GITHUB_OWNER`; varias con `MONITOR_ACCOUNTS=personal:yo,trabajo:mi-org`) y, si no se da `MONITOR_ACCESS_TOKEN`, un token de acceso que guarda en `/data/state/access_token` (modo 600) y nunca imprime. Abre `http://127.0.0.1:8765/?access=TOKEN` una vez: se pone la cookie y se limpia la dirección. Con un bind mount en lugar de un volumen con nombre, da la carpeta al usuario 10001 (`chown -R 10001:10001`). La edición lite no está en la imagen.

## Docker Compose, con proxy y TLS opcionales

`deploy/compose.yaml` ejecuta el monitor con el código de solo lectura, sin capacidades, el acceso como secreto de Docker y los dos volúmenes. El perfil `proxy` añade delante Caddy (`deploy/Caddyfile`): obtiene y renueva solo el certificado de un nombre público (`tls internal` para un nombre de tu propia red, `http://nombre` para ninguno). Copia `deploy/.env.example` a `deploy/.env`, rellénalo y arranca:

```sh
cp deploy/.env.example deploy/.env                                   # fill in MONITOR_GITHUB_OWNER
printf '%s' "ghp_..." > deploy/gh_token.txt && chmod 600 deploy/gh_token.txt
docker compose -f deploy/compose.yaml up -d                          # on 127.0.0.1:8765
docker compose -f deploy/compose.yaml --profile proxy up -d          # behind Caddy (deploy/Caddyfile)
```

Tras el proxy el monitor debe conocer su nombre público y que la sesión es HTTPS: `MONITOR_PROXY_PUBLIC_HOST` y `MONITOR_SECURE_COOKIE=1`. Entonces nada de lo que llega al puerto principal cuenta como el equipo del monitor: usa el segundo puerto (`MONITOR_LOCAL_PORT`, 8766 en la imagen, solo loopback) con `docker compose exec monitor python bin/monitor_cli.py ...` (la imagen pone `MONITOR_URL` apuntando a él).

## Una instalación clásica con systemd

`deploy/github-actions-monitor.service` y `deploy/github-actions-monitor.env` ejecutan la versión descomprimida como el usuario `monitor` con el endurecimiento de systemd (nada escribible salvo su carpeta, sin nuevos privilegios), la reinician si falla, comprueban la salud profunda tras el arranque y releen los archivos de credencial con `systemctl reload`.

```sh
useradd --system --home-dir /var/lib/github-actions-monitor --create-home --shell /usr/sbin/nologin monitor
install -d -o monitor -g monitor -m 700 /etc/github-actions-monitor
install -m 600 -o monitor deploy/github-actions-monitor.env /etc/github-actions-monitor/env     # edit it
install -m 644 deploy/github-actions-monitor.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now github-actions-monitor
systemctl reload github-actions-monitor                              # SIGHUP: read the credential files again
```

El archivo env guarda los datos en `/var/lib/github-actions-monitor` y el acceso en `/etc/github-actions-monitor/gh_token` (modo 600). Escucha en `127.0.0.1` salvo que actives allí el modo red.

launchd (macOS): `ProgramArguments` = `/usr/bin/python3`, `-m`, `github_actions_monitor.service`, las variables en `EnvironmentVariables`, `KeepAlive` y `RunAtLoad` en true. Windows: `schtasks /Create /SC ONLOGON /TN GhaMonitor /TR "py -3 C:/ruta/a/bin/actions_monitor.py --no-browser"`.

## Variables de entorno

Solo se leen los nombres de esta tabla. En el servicio un valor que no se puede leer se ignora con un aviso y no cambia nada. Las que nombran una parte de la configuración (`MONITOR_LISTEN_*`, `MONITOR_ALLOWED_HOSTS`, `MONITOR_PROXY_PUBLIC_HOST`, `MONITOR_SECURE_COOKIE`, `MONITOR_TRUSTED_PROXY`, `MONITOR_LOCAL_PORT`, `MONITOR_TLS_*`, `MONITOR_QUERY_ACCESS`, `MONITOR_TEAM_MODE`) se escriben en `listen` y `auth` en cada arranque del servicio, de modo que el entorno sigue mandando sobre ellas; todo lo demás del archivo es tuyo.

| Variable | Qué hace |
|---|---|
| `MONITOR_GITHUB_OWNER` | El usuario u organización que se vigila; con él se crea la primera cuenta en el primer arranque. |
| `MONITOR_ACCOUNT` | El id de la primera cuenta (por defecto `default`). |
| `MONITOR_ACCOUNTS` | Varias cuentas a la vez: `personal:yo,trabajo:mi-org` (id:propietario). Solo si aún no hay ninguna cuenta. |
| `MONITOR_LANG` | El idioma de los textos (`en es de fr it ja zh pt`). |
| `MONITOR_PORT` | El puerto dentro del contenedor o del servicio (por defecto 8765). |
| `MONITOR_CONFIG` | El archivo de configuración (la imagen: `/config/actions_monitor.json`); se crea en el primer arranque y nunca se sobrescribe. |
| `MONITOR_ACCOUNTS_DIR` | La carpeta de las cuentas, una carpeta por cuenta (la imagen: `/data/accounts`). |
| `MONITOR_STATE_DIR` | Archivos que si no quedarían junto al código: el token de acceso del servicio, la auditoría de los inicios de sesión (la imagen: `/data/state`). |
| `MONITOR_CONFIG_DIR` | La carpeta `config/`: los ficheros de configuración (`targets.json`, `quotas.json` ...) y `config_backups/` (la imagen: `/config`). |
| `MONITOR_DATA_DIR` | La carpeta `data/`: el estado, las cachés y las cuentas; `logs/` y `ai/` van dentro salvo que `MONITOR_LOGS_DIR` / `MONITOR_AI_DIR` digan otra cosa (la imagen: `/data`). Véase LAYOUT. |
| `MONITOR_SECRET_DIR` | Dónde vive el token que guarda el propio monitor, si lo activas (la imagen: `/data/secrets`). |
| `GH_CONFIG_DIR` | La carpeta de configuración de `gh` (la imagen: `/data/gh`). |
| `GH_TOKEN_FILE` | Un archivo con el token de GitHub en su primera línea (un secreto de Docker, una credencial de systemd). Se lee al arrancar y de nuevo con SIGHUP. |
| `GH_TOKEN` | Un token de GitHub en el entorno; `gh` lo lee. Es mejor un archivo: el entorno lo ve cualquier proceso del contenedor. |
| `GH_HOST` | El nombre de un host de GitHub Enterprise Server: todas las llamadas y todos los enlaces de la página lo usan. |
| `MONITOR_ACCESS_TOKEN` | El token de acceso del modo red (al menos 16 caracteres). Sin él, el servicio crea uno y lo guarda en `MONITOR_STATE_DIR`. |
| `MONITOR_ACCESS_TOKEN_FILE` | Un archivo con el token de acceso en su primera línea, en lugar de la variable. |
| `MONITOR_LISTEN_NETWORK` | `1` = el modo red (`listen.network`): escucha en `MONITOR_LISTEN_HOST` y toda petición necesita el token de acceso. La imagen lo activa. |
| `MONITOR_LISTEN_HOST` | La dirección en la que escucha en el modo red (`0.0.0.0` en la imagen; en otros sitios es mejor una dirección privada del equipo). |
| `MONITOR_ALLOWED_HOSTS` | Nombres de host que el monitor acepta además de su propia dirección, separados por comas (`listen.allowed_hosts`). |
| `MONITOR_PROXY_PUBLIC_HOST` | El nombre público del proxy inverso (`listen.proxy_public_host`); declara el proxy. |
| `MONITOR_SECURE_COOKIE` | `1` = la sesión es HTTPS (un proxy la termina): la cookie lleva Secure (`listen.secure_cookie`). |
| `MONITOR_TRUSTED_PROXY` | `1` = el proxy corre en el MISMO equipo y se cree su `X-Forwarded-For` (`listen.trusted_proxy`). |
| `MONITOR_LOCAL_PORT` | Un segundo puerto, solo loopback, para quien está en el equipo cuando hay un proxy declarado (`listen.local_port`; 8766 en la imagen). |
| `MONITOR_TLS_CERT_FILE` | Un certificado (PEM) para servir HTTPS directamente (`listen.tls_cert_file`); con su clave. Si no se puede usar, el monitor no arranca en HTTP plano. |
| `MONITOR_TLS_KEY_FILE` | La clave privada de ese certificado (`listen.tls_key_file`). |
| `MONITOR_QUERY_ACCESS` | `0` = la dirección con `?access=` ya no abre sesión (`listen.query_access`); usa `POST /api/access`. |
| `MONITOR_TEAM_MODE` | `1` = el modo de equipo (`auth.enabled`): usuarios, roles y sesiones. |
| `MONITOR_SERVICE` | `1` = funciona como servicio: no se rinde ante un acceso que no sirve y el doctor revisa la retención. La imagen y el servicio lo activan. |
| `MONITOR_URL` | Para `bin/monitor_cli.py` y la comprobación de salud: la dirección del monitor (la imagen: el segundo puerto). |
| `MONITOR_CA_FILE` | Para `bin/monitor_cli.py`: un archivo PEM con la autoridad que firmó el certificado HTTPS del monitor. |
| `MONITOR_USER` | Para `bin/monitor_cli.py` en el modo de equipo: el usuario con el que iniciar sesión. |
| `MONITOR_PASSWORD_FILE` | Para `bin/monitor_cli.py`: un archivo con la contraseña de `MONITOR_USER` en su primera línea. |
| `MONITOR_RELEASE_TEST_TIMEOUT` | `tools/make_release.py`: segundos que puede tardar la suite ordinaria antes de que falle la puerta (por defecto 3600; de 60 a 86400). |
| `MONITOR_RELEASE_CLEAN_TIMEOUT` | `tools/make_release.py`: segundos que puede tardar la suite del zip extraído (por defecto 3600; de 60 a 86400). |

## Cuando GitHub revoca o caduca el acceso

Cada cuenta es un proceso propio, así que un acceso que deja de funcionar solo afecta a esa cuenta. Tras dos rechazos seguidos que dicen que el acceso mismo no sirve (un 401, `Bad credentials`, un token caducado o revocado, una cuenta suspendida, ningún acceso) la cuenta queda **ciega**: la página, la comprobación de salud profunda, `GET /api/accounts` (`state: blind`) y `bin/monitor_cli.py` lo dicen, se abre una **alerta crítica de sistema** (`system.credential_blind`, centinela `system`) en la pestaña de alertas, y los tipos de notificación `credential_blind` (activado por defecto) y `credential_back` avisan una vez a los canales. El rechazo de un solo permiso (un 403 para un repositorio) no deja ciega a una cuenta. Las demás cuentas siguen y la comprobación de salud profunda se mantiene en verde. La cuenta sigue intentándolo y el primer ciclo bueno cierra la alerta.

Un servicio que arranca con un acceso que ya no sirve se queda en marcha y ciego en lugar de rendirse, para que haya algo que reemplazar. El token de una cuenta sale de, gana el primero que exista: el archivo `credential` de su carpeta (escrito por un reemplazo), el archivo que indica `GH_TOKEN_FILE`, y luego lo que usa `gh` (`GH_TOKEN` o su propio login). Un reemplazo no necesita reiniciar el supervisor ni la cuenta, de tres maneras:

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

El token nuevo se comprueba con GitHub (la llamada `rate_limit`, gratuita) ANTES de guardarlo: un token que GitHub rechaza no cambia nada y responde 422 (`rejected`). Uno bueno se escribe solo en la carpeta de esa cuenta (modo 600), se usa al instante y la cuenta vuelve a leer sin esperar. En el modo de equipo el endpoint es para una sesión `admin` (con el token CSRF de una sesión de cookie) y la auditoría registra quién lo hizo, nunca el token; sin modo de equipo, con el modo red activo, solo puede el equipo del monitor. El token nunca aparece en una respuesta, un registro, una alerta ni la página.

## Primer arranque, copia de seguridad y actualización

Primer arranque como servicio: indica el propietario y el acceso (`GH_TOKEN_FILE`), arráncalo, lee una vez el token de acceso (`/data/state/access_token`), abre la página y ejecuta `bin/monitor_cli.py health --deep`. `python bin/actions_monitor.py --doctor` con `MONITOR_SERVICE=1` avisa además de un bloque de retención ausente y de cuentas que comparten un mismo token.

Copia de seguridad: todo lo que hay que conservar está en los dos volúmenes. Haz una copia consistente del almacenamiento antes de actualizar, y una copia de los volúmenes:

```sh
docker compose exec monitor python /app/tools/backup_storage.py backup /data/state/backup.zip --backend file
docker cp github-actions-monitor:/data/state/backup.zip .
docker run --rm -v monitor-data:/data -v "$PWD":/backup alpine tar czf /backup/monitor-data.tgz -C /data .
```

Actualización: los datos sobreviven porque viven en los volúmenes. Fija una versión (`:1.8.2`) en producción, descarga, recrea y comprueba la atestación de la imagen. Un monitor más antiguo nunca abre un almacenamiento más nuevo (ver `STORAGE.md`), así que conserva la copia hasta que la versión nueva haya funcionado.

```sh
docker compose pull && docker compose up -d
gh attestation verify oci://ghcr.io/juanenrac/tools-github-actions-monitor:1.8.2 --owner JuanenRac
```

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

## La línea de comandos contra otro equipo

`bin/monitor_cli.py` funciona contra un monitor de otra máquina: `--url https://monitor.example.org` (o `MONITOR_URL`), el token de acceso de `MONITOR_ACCESS_TOKEN` o `--token-file`, `--ca-file` (o `MONITOR_CA_FILE`) para confiar en la autoridad que firmó un certificado HTTPS propio y, en el modo de equipo, `--user NOMBRE` con `--password-file ARCHIVO` (o `MONITOR_USER`, `MONITOR_PASSWORD_FILE`), que inicia sesión con una sesión Bearer (`auth.allow_bearer`). `status`, `accounts`, `alerts`, `health` (`--deep`) y `credential` funcionan igual y los códigos de salida son los mismos (3 = rechazado, también para una cuenta ciega en `status` y `accounts`). HTTP plano hacia otro equipo imprime un aviso.

## Permisos mínimos del acceso (`gh` o un token de granularidad fina)

- Listas de runs, jobs e issues: Actions (lectura), Issues (lectura), Metadata (lectura). Alertas: alertas de Code scanning, Dependabot y Secret scanning (lectura). Pull requests y releases: Pull requests (lectura), Contents (lectura). Paquetes: `read:packages`.
- Solo las acciones opcionales de la IA escriben: relanzar un workflow necesita Actions (escritura) y cerrar un issue necesita Issues (escritura). Déjalas apagadas y da al acceso solo lectura.

## Muchos repositorios

Las lecturas condicionales (`cache.etag`) hacen que un repositorio sin cambios no cueste cuota; `mode: lite`, `ecosystems`, `exclude` y `max_workers` limitan el trabajo; el webhook de entrada elimina el sondeo de los repositorios que envían eventos. `discover_limit` es el máximo de repositorios listados de una cuenta (1000 por defecto).

## Funcionando durante meses: almacenamiento y retención

Guarda `accounts/` (o la base de datos) en un volumen que sobreviva al contenedor y haz una copia con `python tools/backup_storage.py backup FILE.zip --backend file` (o `sqlite`) antes de actualizar. De fábrica, una pasada corta elimina los eventos de más de 90 días y las analíticas de más de 180; define `retention` en la configuración para cambiarlo, y `MONITOR_SERVICE=1` hace que `--doctor` trate el monitor como un servicio (entonces avisa si no hay bloque `retention` o si los eventos crecen mucho). Con SQLite lo predeterminado es una base por cuenta; un archivo compartido es posible y está documentado en [STORAGE_spa.md](STORAGE_spa.md).
