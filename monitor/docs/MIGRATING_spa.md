<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Actualizar desde una versión anterior a la 1.5.0

[English](MIGRATING.md) · **Español** · [Français](MIGRATING_fra.md) · [Italiano](MIGRATING_ita.md) · [Deutsch](MIGRATING_deu.md) · [简体中文](MIGRATING_zho.md) · [日本語](MIGRATING_jpn.md) · [Português](MIGRATING_por.md)

La versión 1.5.0 puso nombres en inglés a ficheros, carpetas, scripts y un ajuste. No se pierde nada: el monitor sigue LEYENDO los nombres antiguos, así que puedes actualizar primero y ordenar después.

## Pasos

1. Para el monitor y descomprime la versión nueva sobre la carpeta antigua (conserva tu `actions_monitor.json`).
2. Mira qué cambiaría: `python migrate_state.py` (simulación, no cambia nada).
3. Hazlo: `python migrate_state.py --apply` copia los ficheros antiguos a los nombres nuevos y conserva los antiguos; añade `--move` para renombrarlos en su lugar. Nunca se sobrescribe lo que ya existe, y el ajuste `parte_history_days` pasa a `report_history_days` tras guardar una copia de `actions_monitor.json`.
4. Arranca el monitor con `MONITOR_GITHUB_ACTIONS` (el mismo lanzador de siempre) y usa `BATCH_GITHUB_ACTIONS` para las herramientas por lotes.
5. Borra los lanzadores antiguos que te queden: `LOTE_GITHUB_ACTIONS.bat`, `.sh` y `.command`.

## Nombres antiguos y nuevos

| Antes de la 1.5.0 | Desde la 1.5.0 |
|---|---|
| `leer_parte.py` | `read_report.py` |
| `eventos.py`, `parte_history.py` | `events.py`, `report_history.py` |
| `LOTE_GITHUB_ACTIONS.*` | `BATCH_GITHUB_ACTIONS.*` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` |
| `PARTE_CENTINELA_*` | `SENTINEL_REPORT_*` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_*.json` | `<signed_dir>/batches/batch_*.json` |
| `parte_history_days` | `report_history_days` |
| `monitor_y_centinela` | `github_actions_monitor` |

`ci_red.json`, su esquema y los ficheros de `--export-status` no cambiaron. El idioma es el inglés hasta que elijas otro en Ajustes.

# De 1.5.x a 1.6.x

No hay nada que convertir: el monitor sigue leyendo tu `actions_monitor.json` y añade las claves nuevas, con valores seguros, la primera vez que guardas desde Ajustes.

1. Detén el monitor y descomprime la versión nueva sobre la carpeta antigua (conserva tu `actions_monitor.json` y tus archivos de catálogo).
2. Arráncalo como antes. Junto a él aparecen archivos nuevos (`etag_cache.json`, `analytics_history.json`, `update_check.json`, `sentinel_history.json`); se pueden borrar en cualquier momento.
3. Opcional: `python actions_monitor.py --doctor` comprueba la instalación.

Qué cambia: existe la **edición lite** (`MONITOR_LITE_GITHUB_ACTIONS`, puerto 8766, su propio `actions_monitor_lite.json`, sin centinela); el **rojo en main** es una sola regla (el último run terminado de cada workflow en la rama por defecto; los runs cancelados, omitidos, neutrales y caducados no dicen nada), así que una cifra puede diferir de la 1.5.x; la página de Ajustes tiene primero una pestaña **Básico**; las notificaciones, la analítica, el linter, los eventos del webhook y el asistente de IA existen y están **apagados** hasta que los actives; escribir en GitHub sigue exigiendo tu confirmación explícita. Rich y Textual siguen siendo opcionales; Python 3.11 o superior.

# De la 1.6.4 a la 1.6.5

No hay que convertir nada. Lo que ahora se comporta distinto, a propósito, porque algo sin comprobar ya no se da por seguro:

- **Lotes**: `finalize` ofrece para firmar solo un run cuyo lote REGISTRA que se construyó sobre el commit comprobado. Un lote de una versión anterior dice `needs_review`. Para usarlo igualmente: `finalize --accept-legacy` relee el run en GitHub, lo acepta solo si su commit es el registrado y pide escribir LEGACY antes de cada firma. O lanza la compilación de nuevo.
- **CI en verde** significa que los ficheros de workflow obligatorios pasaron en ese commit (por defecto `ci.yml`; `dispatch.required_ci`, `dispatch.required_ci_repos`, `dispatch.required_ci_profiles`), que nada falló ni espera aprobación y que la lista de runs está completa. Un repositorio cuyo fichero de CI tenga otro nombre necesita ese nombre en `dispatch.required_ci`.
- **Un `git fetch` fallido** (sin red, sin credenciales) detiene el despacho de ese repositorio.
- **targets.json**: `tool` debe ser un nombre de fichero simple (sin carpeta ni `..`) que esté en la carpeta de herramientas; `extra` solo admite pares `-f clave=valor` (no `dry_run` ni `ref`); `finalize_flags` solo opciones largas como `--bench`. Un catálogo que no cumpla se rechaza con el motivo.
- **Notificaciones**: `max_per_hour` cuenta mensajes (uno por canal), no eventos.
- **Webhook**: cada petición necesita `X-GitHub-Delivery` (GitHub siempre lo envía); un id repetido se ignora; el propietario de `full_name` debe ser la cuenta vigilada.
- **act**: un clon que sea un enlace a otra carpeta se rechaza (`act.allow_symlinks` lo permite).
- **Modo red**: solo direcciones IPv4; la dirección mostrada es la que el servidor escucha; `GET /api/sentinel/parte.txt?save=1` ya no escribe (la copia es un POST con el token de un uso).
- El token de GitHub guardado ya no se pone en el entorno del proceso: solo lo recibe `gh`.
- La prueba que descomprime el zip en una carpeta limpia ya no forma parte de la batería ordinaria; `make_release.py` la ejecuta como etapa propia.

# De la 1.6.5 a la 1.6.6

No hay que convertir nada. Lo que se comporta distinto, a propósito:

- **Modo red con HTTPS**: los cambios hechos desde la página ya funcionan; el `Origin` debe llevar el esquema de la sesión y el puerto del monitor. Detrás de un proxy mantén el puerto del monitor en la dirección, o la comprobación lo rechaza.
- **Modo red**: todo ajuste que el esquema marca como `secure` solo se cambia desde el propio equipo (antes: solo `listen.`, `github_token.`, `act.`, `github_actions.`). Un script en otro equipo que cambiaba `webhook.*`, `notify.*` y similares ahora recibe 403 `local_only`.
- **act**: tras Stop la ejecución queda libre al instante; un inicio inmediato ya no responde `busy`.
- Ficheros nuevos junto al monitor: `degraded.json` y `degraded_lite.json` (los contadores de fallos tragados); se pueden borrar en cualquier momento.
- El historial de cambios (Ayuda > Registro de cambios) está traducido: un fichero `docs/CHANGELOG_<idioma>.md` por idioma.

# De la 1.6.6 a la 1.6.7

No hay que convertir nada. Lo que se comporta distinto, a propósito:

- **Modo red tras un proxy HTTPS en el puerto 443**: ajuste nuevo `listen.proxy_public_host` (vacío por defecto; si lo dejas así no cambia nada). Pon ahí el nombre de host público del proxy cuando reenvíe `Host` y `Origin` sin puerto; ese único nombre se acepta entonces tal cual, solo mientras el modo red está activo y la sesión es HTTPS. Solo se cambia desde el propio equipo. Tras un proxy que conserva el puerto no cambia nada.
- El historial de cambios (Ayuda > Registro de cambios) está ahora traducido para la 1.6.7 y la 1.6.5 en los otros siete idiomas; las entradas más antiguas siguen mostrando el texto en inglés bajo un aviso traducido.

# De la 1.6.7 a la 1.6.8

No hay que convertir nada y ningún ajuste cambia.

- Novedad en el repositorio (no en el paquete): `python tools/manual_check_live.py proxy HOST [PUERTO] [CONECTAR]` comprueba tu proxy HTTPS real en el puerto 443 frente a `listen.proxy_public_host`; define antes `MONITOR_ACCESS_TOKEN`, se lee y nunca se imprime.
- El historial de cambios (Ayuda > Registro de cambios) está ahora traducido a los otros siete idiomas de la 1.6.8 a la 1.6.3.
