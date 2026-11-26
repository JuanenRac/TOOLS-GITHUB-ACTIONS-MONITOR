<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](OPS.md) | **🇪🇸 Español** | [🇫🇷 Français](OPS_fra.md) | [🇮🇹 Italiano](OPS_ita.md) | [🇩🇪 Deutsch](OPS_deu.md) | [🇨🇳 简体中文](OPS_zho.md) | [🇯🇵 日本語](OPS_jpn.md) | [🇵🇹 Português](OPS_por.md)

# Operar la instalación

Para un monitor que se deja en marcha durante meses (edición Completa). Cubre la copia de seguridad completa, la restauración, la copia programada, el doctor con códigos de salida en los que un cron puede confiar, y cómo montarlo como appliance (systemd o Docker). La edición Lite no tiene nada de esto.

## El paquete de copia

`python bin/monitor_cli.py backup create [ARCHIVO]` escribe UN `.zip` (formato 2) y lo verifica antes de dejarlo en su sitio. Sin `ARCHIVO` va a la carpeta `backups` de la carpeta de datos (`ops.backup.dir`) con el nombre `ghamon-backup-<hora UTC>.zip`. No hace falta parar el monitor: los datos se leen con las lecturas atómicas del almacén (archivos o SQLite), nunca copiando una base que se está escribiendo.

| Miembro | Qué contiene |
|---|---|
| `dump.jsonl` | cada cuenta (sus ajustes, el estado de los centinelas, los documentos pequeños, los eventos, las analíticas, las instantáneas de la puntuación) y los registros globales (usuarios y las cuentas que pueden ver; nunca las sesiones) |
| `files.json` | los ajustes de la página y las listas de la instalación (`targets.json`, `ecosystems.json`, `profiles.json`, los silencios), limpios; también los almacenes de los módulos opcionales si existen (`proposals.json`, `devices.json`) |
| `manifest.json` | el formato, la versión del producto, el esquema, los recuentos y el tamaño y el SHA-256 de cada miembro |

**Lo que nunca viaja:** tokens y claves de GitHub o de una App, contraseñas, el valor de cualquier variable `*_env` (solo su nombre), el secreto del webhook, las claves de los proveedores de IA, las sesiones y el contenido del almacén de secretos. Los ajustes pasan por una lista blanca (las mismas claves que puede mostrar la página de Ajustes) y luego por una limpieza que descarta cualquier clave que parezca un secreto y cualquier texto que parezca un token o una clave privada. Con `ops.backup.include_config` apagado se dejan fuera por completo los ajustes y las listas. Una restauración no devuelve ninguna credencial: vuelve a poner el acceso a GitHub (su lista de pendientes lo dice).

La copia solo la puede leer su propietario (modo 600) y el paquete no va cifrado salvo que lo pidas: mira abajo.

### Un paquete de una cuenta

`backup create --account ID [ARCHIVO]` escribe el paquete de UNA cuenta: su volcado (con sus ajustes, limpios de la misma manera) y nada más. No lleva ningún usuario ni sesión, ni los ajustes o las listas de la instalación; el manifiesto dice `scope: account`. `backup verify` comprueba que contiene solo esa cuenta, y `backup restore ARCHIVO` restaura esa cuenta (no hace falta `--account`) sin tocar las demás cuentas, los usuarios ni los archivos del destino; se rechaza únicamente cuando esa cuenta ya existe allí y no hay `--force`. Es la forma de mover o recuperar una sola cuenta.

### Cifrar la copia (opcional)

`ops.backup.encrypt` (o `--encrypt` para una copia) cifra el paquete con AES-256-GCM usando una clave tomada de la variable de entorno que indica `ops.backup.key_env` (`--key-env NOMBRE`). La clave nunca es un ajuste, nunca se escribe y nunca va en una línea de órdenes. Necesita la biblioteca opcional `cryptography` (`pip install cryptography`; el núcleo del monitor sigue siendo solo biblioteca estándar). Sin la biblioteca, o sin una clave de 12 caracteres o más, la copia se **rechaza** con un mensaje claro y no se escribe nada: nunca se hace una copia en claro cuando pediste una cifrada, ni se cifra con algo más débil. Un archivo cifrado acaba en `.enc`; `verify` y `restore` lo abren con la misma variable. Guarda la clave aparte del archivo: sin ella la copia no se puede abrir.

## Verificar, listar y estado

- `backup verify ARCHIVO` vuelve a leer el paquete y comprueba cada tamaño y SHA-256 y los recuentos. Se informa de un byte cambiado, de un miembro que falta o de uno que el manifiesto no lista. `--deep` además lo restaura en una carpeta temporal y comprueba el resultado.
- `backup list` muestra las copias de la carpeta; `backup status` muestra la última copia buena, su antigüedad, la programación y el último fallo.
- Un paquete del primer formato (hecho antes de la 2.1.0) se sigue verificando y restaurando.

## Restaurar

`python bin/monitor_cli.py backup restore ARCHIVO`: para antes el monitor (la restauración se rechaza mientras uno responda en su puerto). Verifica el paquete y luego escribe las cuentas y los archivos.

- Un almacén que ya tiene cuentas se rechaza salvo que añadas `--force` (las cuentas del paquete se escriben entonces encima; los ajustes se **fusionan**: una clave que el paquete no lleva nunca se quita).
- `--account ID` restaura solo esa cuenta y deja las demás y los archivos globales como están (se rechaza únicamente cuando esa cuenta existe y no hay `--force`).
- `--to-dir CARPETA` restaura en una carpeta vacía (backend de archivos) sin tocar la instalación: la forma de mirar una copia o de mudarse a otra máquina.
- Escribe `ops/restore_report.json` en la carpeta de datos e imprime lo que falta por hacer: volver a poner el acceso a GitHub, volver a fijar los ajustes que el paquete dejó fuera, reiniciar el monitor para que el supervisor arranque cada cuenta, ejecutar el doctor.

## La copia programada

Dos maneras, usa una:

1. Dentro del monitor: `ops.backup.enabled` (apagado por defecto) hace una copia cada `ops.backup.interval_hours` en un hilo propio, conserva las `ops.backup.keep` más recientes (solo se borran archivos con nombre de copia) y anota el resultado en `ops/backup_status.json`. Un fallo (disco lleno, clave que falta) se anota y se muestra en el panel Acerca de y en el doctor; nunca para el monitor.
2. Con systemd: `deploy/github-actions-monitor-backup.service` y `deploy/github-actions-monitor-backup.timer` (mira abajo).

El panel Acerca de tiene una tarjeta **Operación** con el modo (servicio o local), la última copia buena, la programación, la retención en vigor y el botón **Copia ahora** (un administrador, desde este equipo). `GET /api/ops/status` da los mismos datos; `POST /api/ops/backup` hace una copia.

## Purga bajo demanda

La purga de retención se ejecuta sola cada `retention.interval_hours`. Para lanzarla ahora hay un botón (y `POST /api/ops/purge`) que **no existe** hasta que `ops.purge.enabled` está encendido (apagado por defecto). Una petición es un ensayo (la política en vigor y cuántos eventos se irían) salvo que diga `dry_run` false, y una purga real se rechaza sin una copia buena más reciente que `ops.purge.require_backup_hours` (24 por defecto; 0 no lo exige). Deja su línea en la auditoría de la retención y en el registro de acciones.

## El doctor y sus códigos de salida

`python bin/monitor_cli.py doctor [--strict] [--json]` (o `python bin/actions_monitor.py --doctor`) comprueba la instalación, no cambia nada y no imprime ningún secreto. La edición Completa añade estas comprobaciones tras las habituales:

| Comprobación | Qué mira |
|---|---|
| `volumes` | se escribe, se lee y se borra de verdad un archivo en las carpetas de datos, registros y copias (un volumen de Docker montado como root o de solo lectura falla aquí) |
| `supervisor` | un monitor en marcha: la salud profunda del supervisor y de cada ciclo de refresco (no se arranca nada) |
| `limits` | el secreto del webhook está definido y tiene al menos `ops.doctor.webhook_min_length` caracteres (solo se compara la longitud) y la política de retención |
| `sqlite_hot` | cada base SQLite abierta solo para lectura: `quick_check` (por defecto) o `integrity_check` (`ops.doctor.sqlite_check` deep), cortada en `ops.doctor.sqlite_timeout_s`; un archivo corrupto tras un corte de luz falla |
| `backup_age` | la última copia buena frente a `ops.doctor.backup_max_age_days` |
| `disk` | espacio libre del volumen de datos frente a `ops.doctor.min_free_mb` |
| `metrics` | `/metrics` responde cuando la salida Prometheus está encendida y hay un monitor en marcha |
| `plugins` | con `plugins.enabled`: complementos instalados que ya no pasan la comprobación (clave revocada, fichero cambiado) y los pausados |

**Códigos de salida (estables, para cron):** `0` todo bien (también con avisos, sin `--strict`); `1` falló al menos una comprobación; `3` solo avisos y `--strict` (o `ops.doctor.strict_exit`); `4` el propio doctor no pudo ejecutarse. Son los códigos del doctor; las demás órdenes de `monitor_cli.py` conservan los suyos. Ejemplo: `0 * * * * python3 bin/monitor_cli.py doctor --strict --json > /var/lib/github-actions-monitor/doctor.json || true` y avisa ante cualquier código distinto de 0.

## Como appliance

**systemd** (sin contenedor): sigue los comentarios de `deploy/github-actions-monitor.service` e instala después la unidad de copia y su temporizador:

```
install -m 644 deploy/github-actions-monitor-backup.service deploy/github-actions-monitor-backup.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now github-actions-monitor-backup.timer
systemctl list-timers github-actions-monitor-backup.timer
```

Para una copia cifrada pon la variable que indica `ops.backup.key_env` en `/etc/github-actions-monitor/env` (modo 600). El temporizador ejecuta `backup create` cada día; su código de salida es 1 cuando no se pudo hacer la copia.

**Docker:** `deploy/compose.yaml` guarda las copias en un volumen propio (`monitor-backups` en `/data/backups`) para que perder el volumen de datos no las pierda. Saca un archivo con `docker compose exec monitor python bin/monitor_cli.py backup list` y `docker cp`, y restaura en un contenedor parado o con `--to-dir`. El TLS lo renueva el Caddy de `deploy/Caddyfile`.

**Actualizar sin perder las cuentas:** `backup create` → `backup verify ARCHIVO` → parar el monitor → sustituir la carpeta del producto (las carpetas `config/`, `data/`, `logs/` y `ai/` son tuyas y se conservan) → `doctor` → arrancar. Si algo sale mal, `backup restore ARCHIVO`. **Quitarlo limpiamente:** para y desactiva las unidades, quita el temporizador, luego la carpeta del producto y, solo si quieres perder los datos, las carpetas `config/`, `data/` o los volúmenes de Docker.

## Ajustes

Todos están en la pestaña Ajustes (Carpetas y archivos) y en [SETTINGS_spa.md](SETTINGS_spa.md): `ops.backup.*` (enabled, dir, interval_hours, keep, include_config, compress_level, encrypt, key_env), `ops.purge.*` (enabled, require_backup_hours) y `ops.doctor.*` (strict_exit, backup_max_age_days, min_free_mb, sqlite_check, sqlite_timeout_s, webhook_min_length). Todo interruptor empieza apagado o conservador, y los de seguridad (la copia programada, incluir los ajustes, el cifrado, la purga) están marcados como tales.

Mira también [STORAGE_spa.md](STORAGE_spa.md) (los backends y la retención), [DEPLOYMENT_spa.md](DEPLOYMENT_spa.md) (servicio, contenedor, TLS) y [CLI_spa.md](CLI_spa.md).

## El monitor vigila su propia memoria e hilos

Cada `selfwatch.interval_seconds` (60) el monitor lee su memoria residente, sus hilos y su uso de procesador y los muestra en `/api/health` como `selfwatch` (`state`: `ok` o `high`). Cuando la memoria supera `selfwatch.rss_warn_mb` (1024) o los hilos `selfwatch.threads_warn` (400) lo anota una vez en el contador de fallos tragados (`high`, con las cifras), libera lo que puede y anota la vuelta a la normalidad. Se apaga con `selfwatch.enabled`. Pon `selfwatch.rss_warn_mb` algo por debajo del límite de tu contenedor. El CI ejecuta el monitor en un contenedor de un procesador y 512 MB con una cuenta de 120 workflows (`tools/limits_check.py`).
