<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Actualizar el monitor (el actualizador)

[English](UPDATE.md) · **Español** · [Français](UPDATE_fra.md) · [Italiano](UPDATE_ita.md) · [Deutsch](UPDATE_deu.md) · [简体中文](UPDATE_zho.md) · [日本語](UPDATE_jpn.md) · [Português](UPDATE_por.md)

El actualizador lleva una instalación de cualquier versión publicada a cualquier otra (subiendo o bajando), migra tu configuración y deja una vuelta atrás. Es UN solo fichero, `monitor_updater.py`, que solo necesita Python y funciona sea cual sea la versión instalada; también va dentro del producto (`tools/monitor_updater.py`) y como el comando `monitor_cli.py update`. Nunca actualiza por sí solo: solo cuando lo pides, y no borra nada (lo reemplazado va a la carpeta de copias).

## Tres formas de abrirlo

- `py -3 monitor_updater.py` abre una página en tu navegador. Se sirve en 127.0.0.1 solo mientras el actualizador corre, con un token de un solo uso en la dirección; nada más puede usarla.
- `py -3 monitor_updater.py --tk` abre lo mismo en una ventana (necesita Tkinter).
- `py -3 monitor_updater.py --console` es un menú de texto para servidores, SSH y contenedores.
- `py -3 bin/monitor_cli.py update` es el mismo fichero lanzado desde el producto; `update plan`, `update apply` y los demás comandos de abajo aceptan las opciones de la tabla.

## El menú Actualizaciones dentro del monitor

La edición Completa lleva el mismo actualizador dentro de su página: **Sistema > Actualizaciones**. Muestra la versión instalada y la que encontró la comprobación (ajuste `updates.check`; no se pregunta nada a GitHub mientras esté apagada o el monitor esté sin conexión), las notas de cada release y, con el botón «Buscar versiones», la lista de las publicadas. No se descarga ni se aplica nada si no pulsas un botón. Aplicar exige un administrador en el equipo donde corre el monitor (las rutas `/api/updates/*` responden 403 desde la red) y una confirmación que dice qué va a pasar: el SHA-256 del zip frente a SHA256SUMS, la copia que se hace antes (con su carpeta), la migración de la configuración y el reinicio. La actualización corre en un proceso propio: el monitor se detiene solo, se aplica la actualización, el monitor arranca de nuevo con la versión nueva y la página se reconecta; si la versión nueva no arranca, se repone la anterior y se arranca. «Volver a la versión anterior» hace lo mismo al revés. Los pasos, el historial y el resultado se ven en la página y se anotan en el registro de acciones. No se ofrece en la edición Lite, en un contenedor ni bajo un gestor de servicios (reinician el proceso por su cuenta: usa la línea de comandos), y solo corre una actualización a la vez. Tu configuración, datos, claves y registros no se sustituyen. El fichero independiente sigue ahí como camino de vuelta cuando el monitor no arranca.

Bajo un gestor de servicios la página no aplica actualizaciones por defecto. Si el monitor corre como servicio de USUARIO de systemd (`systemctl --user`), puedes encender `updates.systemd_helper` (apagado por defecto): la página ofrece entonces la actualización y el proceso que la aplica detiene ese servicio, aplica la actualización y vuelve a arrancar el servicio, siempre con `systemctl --user` y nunca con `sudo`. Un servicio del sistema (el que necesita al administrador) no se toca y sigue siendo «usa la línea de comandos». Lo mismo funciona desde la línea de comandos con `--systemd-unit UNIDAD` (`apply` y `rollback`); si no se puede detener el servicio no se inicia nada, y si la versión nueva no arranca se pone la anterior y se arranca el servicio de nuevo.

**Confianza.** SHA256SUMS sale de la misma release de GitHub que el zip, así que por sí solo solo detecta una descarga dañada o incompleta. Lo que prueba el origen de una release desde la 2.2.0 es su firma (abajo).

## Releases firmadas

Desde la versión 2.2.0 cada release va firmada: SHA256SUMS tiene una firma Ed25519 separada, el fichero `SHA256SUMS.ed25519.sig`, hecha con la clave del proyecto, cuya parte pública viaja dentro del actualizador. El actualizador la comprueba antes de descomprimir nada. Una release desde la 2.2.0 sin firma válida se rechaza, y también un zip firmado que se ofrezca con otra versión. Volver a una versión anterior, publicada sin firma, está permitido con un aviso. Para un zip descargado a mano, pon `SHA256SUMS` y `SHA256SUMS.ed25519.sig` junto a él (con `--zip`).

Clave pública (Ed25519, hex): `380c75210e444f71bc4fe4b9aa7cb451aad5ef2592711f7dc6ba2fd7adc3d272`. Su huella SHA-256: `6d6b995655147955a1c2fb8a84a02d828606de29b36583799ada6ca5524b5d1a`.

Además del zip, una release lleva `monitor_updater.py`, dos listas de materiales (`github_actions_monitor.cdx.json` en CycloneDX y `github_actions_monitor.spdx.json` en SPDX), una firma junto a cada fichero y las atestaciones que GitHub hace de la compilación, que se comprueban con `gh attestation verify github_actions_monitor.zip --repo JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR`. La firma prueba quién tiene la clave; la atestación prueba qué workflow construyó el fichero. Son dos comprobaciones separadas.

**Rotación de la clave.** Una clave nueva viaja en una release que lleva la antigua y la nueva durante un solape; la que deja de ser de confianza se quita (o se marca revocada) en una release posterior. El fichero cosign (`github_actions_monitor.zip.cosign.bundle`) registra la firma sin clave del workflow; se comprueba con `cosign verify-blob --bundle github_actions_monitor.zip.cosign.bundle --certificate-oidc-issuer https://token.actions.githubusercontent.com --certificate-identity https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/.github/workflows/release-build.yml@refs/heads/main github_actions_monitor.zip`.

## El aviso de versión nueva y las órdenes

Cuando la comprobación de versión (`updates.check`) encuentra una más nueva, una ventana en la edición Completa muestra el resumen de sus cambios en tu idioma, un enlace al historial y un botón a la página de Actualizaciones (ajuste `updates.notify_window`, encendido por defecto). «Más tarde» la cierra durante esta sesión del navegador; «No avisar de esta versión» silencia solo esa versión. Nunca aparece en pantallas de pared o quiosco. Sus rutas son `/api/supply/update-notice` y `/api/supply/update-dismiss`.

`monitor_cli.py verify-release --folder DIR` comprueba sin red una carpeta de ficheros de release descargados contra SHA256SUMS y su firma. `monitor_cli.py keyring list|add|revoke|verify` gestiona las claves públicas (`--key-id`, `--public-key`, `--key-scope`, `--expires`, `--document`); tus claves se guardan en `keyring.json` en la carpeta de configuración, las claves privadas se rechazan y la clave de release del proyecto no se puede cambiar.

## Qué hace, paso a paso Las rutas que lo sostienen son `/api/updates/status`, `/api/updates/progress`, `/api/updates/history`, `/api/updates/log` (las últimas líneas del registro del proceso, con los valores tras token o secret ocultos), `/api/updates/copies` (solo lectura) y `/api/updates/check`, `/api/updates/plan`, `/api/updates/apply`, `/api/updates/rollback`, `/api/updates/discard` (administrador, solo desde este equipo). El progreso viaja además como eventos enviados por el servidor en `/api/updates/stream` (la página lo usa mientras corre una actualización y vuelve a preguntar cada segundo y medio si el navegador o la conexión no lo permiten).

1. Detecta la instalación: carpeta, versión, edición (Completa o Lite), configuración, datos, puertos, si el monitor está en marcha, contenedor o servicio.
2. Lista todas las versiones publicadas en GitHub (sin token) con su fecha y notas, y marca la instalada y la última. Sin conexión, dale un zip con `--zip`.
3. Tú eliges la versión de destino. Una menor es un downgrade: pide `--allow-downgrade`.
4. Muestra el PLAN como ensayo en seco: la cadena de pasos entre las dos versiones (leída del registro de migraciones), qué cambia en TU configuración, los cambios de comportamiento que notarás y cada incoherencia encontrada.
5. Lo aplica: copia previa, SHA-256 comprobado contra SHA256SUMS, zip extraído en una carpeta nueva e inspeccionado (rutas con `..`, enlaces, tamaño), producto copiado, tus líneas propias de los lanzadores devueltas a su sitio, configuración migrada, disposición de carpetas migrada y, si quieres, el monitor arrancado y `/api/health` comprobado.
6. Si algo falla vuelve solo al estado anterior y escribe un informe. Cada actualización queda en el historial (`update_history.jsonl`) y la última se puede deshacer con el comando `rollback`.

## Comandos

Sin comando se abre la página. Los comandos responden una vez (añade `--json` para un documento):

| Comando | Significado |
|---|---|
| `status` | qué hay instalado y qué encuentran las comprobaciones |
| `releases` | todas las versiones publicadas |
| `plan` | el ensayo en seco para un destino |
| `apply` | hacerlo (`--dry-run` solo muestra el plan) |
| `migrate` | solo migrar un fichero de configuración, ver abajo |
| `rollback` | volver a la versión anterior a la última actualización |
| `history` | las actualizaciones hechas en esta instalación |
| `copies` | las copias de la carpeta de copias: nombre, estado, versiones, tamaño y cuál necesita la vuelta atrás |
| `discard` | `discard --name COPIA` borra UNA copia tras confirmarlo (`--yes` omite la pregunta); la copia que necesita la vuelta atrás solo con `--force`; la de una actualización en curso, nunca |
| `log` | las últimas líneas (`--lines N`, como mucho 2000) del registro del proceso de la última actualización, con los valores tras token, secret o password ocultos |

## Opciones

| Opción | Significado |
|---|---|
| `--dir` | la instalación (por defecto, donde está el fichero, buscando hacia arriba) |
| `--to` | versión de destino (por defecto, la última) |
| `--from` | migrate: versión de la que viene el fichero |
| `--config` | migrate: un fichero de configuración |
| `--zip` | usar este zip en vez de GitHub |
| `--sha256` | SHA-256 esperado del zip |
| `--dry-run` | solo mostrar el plan |
| `--apply` | migrate: escribir el resultado |
| `--yes` | no pedir confirmación |
| `--json` | la respuesta como un documento JSON |
| `--keep-old-defaults` | escribe el defecto antiguo de cada ajuste que nunca definiste, para que el comportamiento no cambie |
| `--adopt-new-defaults` | mueve también al nuevo defecto los ajustes que aún tienen el antiguo |
| `--start` | arrancar el monitor después y comprobarlo |
| `--handover` | el monitor que lanzó este proceso se detiene solo: esperarlo, aplicar y arrancarlo de nuevo (si no arranca, vuelve la versión anterior) |
| `--status-file` | escribe el progreso en este fichero JSON (lo lee el menú Actualizaciones) |
| `--edition` | complete o lite, si no se puede deducir |
| `--allow-downgrade` | permitir una versión menor |
| `--allow-container` | trabajar dentro de un contenedor igualmente (la imagen no se sustituye) |
| `--no-gh` | no usar el programa `gh`, solo la API pública |
| `--backups` | carpeta de copias (por defecto, update_backups en la instalación) |
| `--restore-data` | yes, no o auto: qué hace la vuelta atrás con los datos |
| `--port` | puerto de la página |
| `--no-browser` | no abrir el navegador |
| `--tk` | la ventana |
| `--console` | el menú de texto |
| `--lang` | idioma: en es de fr it ja zh pt |

## Tu configuración y los defectos que cambian

- El registro de migraciones (ficheros JSON versionados en cada release, `assets/migrations/`) dice de cada versión qué cambió: ajustes renombrados, quitados o nuevos, nuevos defectos, ficheros movidos, cambios de comportamiento. El actualizador aplica la cadena de las versiones que saltas.
- Por defecto conserva lo que fijaste explícitamente y adopta un defecto nuevo solo donde nunca definiste el ajuste. Un cambio de comportamiento (por ejemplo, una función que ahora viene apagada) se cuenta en el informe; `--keep-old-defaults` fija el comportamiento antiguo y `--adopt-new-defaults` lo mueve todo al nuevo.
- `migrate` trabaja sobre un fichero suelto: `monitor_updater.py migrate --from 2.0.1 --to 2.0.8 --config mi.json` muestra el resultado y `--apply` lo escribe (tras una copia). Los secretos salen enmascarados en cualquier informe.

## Comprobaciones antes de aplicar

- Bloquean: el monitor está en marcha, el SHA-256 no coincide, el zip no es seguro, falta espacio en disco, datos de un esquema más nuevo que el destino, un contenedor, otra actualización pendiente.
- Avisan: ajustes que ya no existen o cambiaron de tipo o rango, valores fuera de rango, claves duplicadas, un puerto ocupado por otro programa, un lanzador que cambiaste, un paso que exige otro antes. Cada aviso trae una acción sugerida.

## Seguridad y la vuelta atrás

- Solo escucha en 127.0.0.1 con un token efímero, rechaza peticiones de otros sitios, no ejecuta nada del zip, no usa shell y solo escribe dentro de la instalación y de la carpeta de copias.
- Antes de cambiar nada copia el paquete, la configuración y los datos; si un paso falla se restaura la copia y se escribe un informe. Si falla hasta la vuelta, la copia sigue intacta y el informe explica cómo restaurarla a mano.
- Sin Internet: `--zip FICHERO` con `--sha256` (o un SHA256SUMS al lado). Docker: se actualiza el volumen, la imagen no se sustituye desde dentro (`--allow-container` para forzarlo).
- La página muestra las copias y un botón **Descartar copia** en cada una (pregunta antes, y dos veces por la copia que necesita la vuelta atrás), y un botón para leer el registro completo del proceso de la última actualización. Descartar borra solo esa copia, nunca la instalación ni los datos, y queda anotado en el historial.
- El actualizador independiente, que funciona sin el monitor, tiene lo mismo: su página en el navegador (botones **Copias** y **Registro del proceso**, y **Descartar copia** en cada copia, con las mismas preguntas), su menú de texto (opciones 7 a 9) y su ventana (Tkinter).

## Códigos de salida

| Código | Significado |
|---|---|
| 0 | hecho, o nada que hacer |
| 2 | uso incorrecto |
| 3 | bloqueado por una comprobación, nada cambió |
| 4 | falló la descarga, el SHA-256 o el zip, nada cambió |
| 5 | falló y se restauró el estado anterior |
| 6 | falló y también falló la vuelta: restaura la copia a mano |
| 7 | sin conexión con GitHub y sin zip |
| 8 | no confirmado |

## El aviso nombra la orden de tu forma de instalar

El aviso de una versión más nueva (consola, Acerca de, `/api/about`) dice ahora la orden exacta de la forma en que se instaló este monitor, en el campo `command` junto a `channel`: el producto descomprimido (`py -3 monitor/bin/monitor_cli.py update`), un gestor de servicios (`... update apply --systemd-unit <unidad>`), un contenedor (`docker pull ghcr.io/juanenrac/tools-github-actions-monitor:<versión>`), pipx, uv o una extensión de la orden `gh`. El aviso no ejecuta nada.
## Guardas del ayudante de servicio

Con `updates.systemd_helper` (o `--systemd-unit`) el actualizador comprueba ahora el servicio antes de tocarlo: una unidad cuyo directorio de trabajo y orden no apuntan a ESTA carpeta pertenece a otra instalación y no se detiene ni se arranca; una unidad no se arranca mientras otra cosa (un monitor en primer plano) atienda su puerto; un reinicio no se da por hecho mientras el proceso siga siendo el viejo (la unidad debe mostrar un PID nuevo); y `update status --systemd-unit UNIDAD` lista solo los errores del servicio desde su último arranque. Son preguntas de solo lectura a `systemctl --user show` y `journalctl --user`; una pregunta sin respuesta no bloquea nada.
