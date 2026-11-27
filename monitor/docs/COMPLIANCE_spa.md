<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLIANCE.md) | **🇪🇸 Español** | [🇫🇷 Français](COMPLIANCE_fra.md) | [🇮🇹 Italiano](COMPLIANCE_ita.md) | [🇩🇪 Deutsch](COMPLIANCE_deu.md) | [🇨🇳 简体中文](COMPLIANCE_zho.md) | [🇯🇵 日本語](COMPLIANCE_jpn.md) | [🇵🇹 Português](COMPLIANCE_por.md)

# Cumplimiento: lo que puedes demostrar de tu instalación

Todo esto está apagado de fábrica y solo funciona en la edición completa, salvo las dos restricciones, que valen para cualquier proceso del monitor. Nada de ello es una certificación.

## Modo de solo lectura estricto

`security.read_only_strict` (apagado). Encendido, no se escribe nada en GitHub digan lo que digan la edición o los demás ajustes: solo se ejecutan órdenes de lectura de `gh` (lo que no se sabe que lee se rechaza), sin `git push`, sin `act` y sin peticiones a la API de GitHub que no sean GET o HEAD. Se aplica por debajo de todas las partes, con un gancho de auditoría de Python que ve cada programa que arranca. Solo se cambia desde el equipo del monitor y relajarlo exige reiniciar. La ventana Acerca de y `/api/about` (`restrictions`) dicen si está en vigor.

## Política de red

`security.egress_policy`: `default`, `github_only` o `none`; `security.egress_allow` añade hosts (`nombre`, `*.nombre`, una dirección) o `program:NOMBRE`. Con `github_only` los procesos del monitor solo llegan a `api.github.com`, `uploads.github.com`, el host de `GH_HOST` (GitHub Enterprise) y lo que permitas; con `none`, solo a este equipo, y `gh` no se arranca. Los programas que abren la red por su cuenta (`git` en órdenes de red, `apprise`, `curl`, `docker`, las herramientas de los almacenes de secretos) no se arrancan. Una conexión rechazada falla con un error que nombra el ajuste. `python bin/monitor_cli.py doctor` falla cuando un destino configurado queda fuera de la política, y `doctor --egress` lista todos los destinos. No es un cortafuegos: no gobierna lo que hagan otros programas del equipo.

## El informe de cumplimiento

`python bin/monitor_cli.py compliance report` (con `--json`), `GET /api/compliance/report` (administradores) y una caja al final de la pestaña Seguridad. Cada línea dice si está **comprobada** (el monitor miró la cosa) o solo **declarada** (lo dice la configuración): versión y soporte, edición, autenticación y proveedor de identidad, modo de red y TLS, las dos restricciones y los destinos, retención y retención legal, el registro de acciones y su cadena, copias y su cifrado, cifrado en reposo (ninguno), almacenamiento, complementos, despliegue y perfil. No lleva secretos, rutas ni nombres. `GET /api/compliance/state` da las restricciones, la tabla de retención y el estado de la exportación.

## Retención y retención legal

Eventos, analítica y puntuaciones conservan sus ajustes (`retention.events_days`, `retention.analytics_days`, `retention.mode`). Las demás categorías se guardan siempre salvo que les pongas días: `retention.audit_days` (ficheros rotados enteros del registro de acciones), `retention.reports_days` (el informe más reciente de cada cuenta se queda), `retention.ai_log_days`, `retention.backups_days` (la copia más reciente se queda). Cada borrado deja una línea en el registro de acciones. `retention.legal_hold` detiene todo borrado: eventos, analítica, puntuaciones, informes, copias, el recorte del feed y del registro de prompts, y la rotación y purga del registro. Las propuestas de la IA caducan solas; los dispositivos emparejados se quedan hasta que los quites; esta versión no guarda postmortems, incidentes ni notas.

## Puntos de control firmados del registro de acciones

`audit_checkpoints.enabled` (apagado) firma la cadena (HMAC-SHA256) con una clave de la instalación: `config/audit_checkpoint.key`, o el fichero indicado en `MONITOR_AUDIT_KEY_FILE` para tenerla aparte. Un punto de control en la primera línea y después al menos cada hora y cada 1000 líneas; el ancla también va firmada, y un recorte del final seguido de una línea nueva queda escrito en la cadena. `python bin/monitor_cli.py audit verify` (`--audit-from N`), `audit checkpoint` y `audit purge --older-than-days N` (`--dry-run`), que borra ficheros rotados enteros y firma por dónde sigue la cadena. Quien pueda leer la clave puede firmar: tenla lejos de quien pueda escribir el registro.

## Exportación del registro de acciones

`audit_export.enabled` (apagado) con `audit_export.target` = `file` (`path`, rotado a `max_mb`), `syslog` (`host`, `port` 6514, RFC 5424 sobre TCP con TLS, `ca_file`) o `http` (`url`, POST de líneas JSON, token de la variable indicada en `token_env`). Las direcciones privadas necesitan `audit_export.allow_private_targets`. El registro es la cola: lo que el destino no aceptó espera ahí; al pasar de `spool_mb` el doctor dice `system.audit_export_lag`, y las líneas rotadas antes de poder enviarse se cuentan como perdidas. `python bin/monitor_cli.py audit export` hace una pasada ahora. Probado contra receptores de este equipo, no contra un syslog o SIEM real.

## Versiones soportadas

Solo se soporta la última versión publicada: no hay rama de largo plazo. El doctor (`compliance_support`) avisa cuando sabe de una más nueva.

## Evidencia del endurecimiento

`[IMP]` = una prueba de este repositorio ejercita el control; `[PAR]` = solo se ejercita una parte, y la línea dice qué falta. La lista es `schemas/controls.json` y una prueba comprueba que esta tabla y las pruebas que nombra coinciden.

| Control | Estado | Nombre |
|---|---|---|
| `sqlite_contention` | [IMP] | Varios procesos escribiendo una base de datos |
| `storage_migrations` | [IMP] | Migraciones del almacenamiento |
| `retention_by_category` | [IMP] | Retención por categoría y retención legal |
| `incoming_webhook` | [IMP] | Webhook entrante: firma, tamaño, tiempo |
| `metrics_labels` | [IMP] | Etiquetas de /metrics |
| `timezone` | [IMP] | Zonas horarias y cambio de hora |
| `read_only_strict` | [IMP] | Modo de solo lectura estricto |
| `egress_policy` | [IMP] | Política de red |
| `audit_chain` | [IMP] | Cadena y puntos de control del registro |
| `service_and_volume` | [PAR] | Servicio en systemd y base grande (los sistemas de ficheros de red no se prueban) |

## Límites conocidos

- Quien tenga una cuenta `viewer` y esté sentado en el propio equipo del monitor se trata como local y ve las rutas completas.
- El webhook entrante solo comprueba la ventana de tiempo en las entregas `workflow_run` y `workflow_job`.
- Con `none` o `github_only`, un proceso Python que arranque el monitor aplica la misma política solo si importa el monitor; un programa que ejecutes tú queda fuera.
- En esta versión no existen el cifrado en reposo, una rama de largo plazo ni la federación.
