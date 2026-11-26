<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI.md) | **🇪🇸 Español** | [🇫🇷 Français](CLI_fra.md) | [🇮🇹 Italiano](CLI_ita.md) | [🇩🇪 Deutsch](CLI_deu.md) | [🇨🇳 简体中文](CLI_zho.md) | [🇯🇵 日本語](CLI_jpn.md) | [🇵🇹 Português](CLI_por.md)

# La línea de comandos como cliente del monitor

`python bin/monitor_cli.py COMANDO` pregunta al monitor en marcha lo que sabe (un `GET` en `127.0.0.1`, o en la dirección de `--url` / `MONITOR_URL`) y lo imprime. No repite el trabajo de la página contra GitHub, nunca escribe en GitHub y no cambia ningún ajuste. Las herramientas anteriores (`bin/read_report.py`, `--doctor`, `bin/gha_dispatch_all.py`) siguen funcionando igual.

## Comandos

| Comando | Qué muestra | Lite |
|---|---|---|
| `status` | versión, edición, cuenta, repositorios, qué corre y qué falla, la cuota | sí |
| `health` (o `check`) | una comprobación rápida antes de leer nada pesado: ¿se alcanza el monitor?, ¿acepta a este cliente?, ¿responde el acceso de GitHub de la cuenta? | sí |
| `doctor` | las comprobaciones de `--doctor` de esta instalación (el monitor no tiene que estar en marcha) | sí |
| `backup` | la copia de seguridad completa de la instalación (el monitor no tiene que estar en marcha): `backup create [ARCHIVO] [--account ID]`, `verify ARCHIVO [--deep]`, `restore ARCHIVO [--account ID] [--to-dir CARPETA] [--force]`, `status`, `list`; `--encrypt` con `--key-env NOMBRE` la cifra (biblioteca opcional); mira [OPS_spa.md](OPS_spa.md) | no |
| `accounts` | las cuentas del supervisor (solo con varias cuentas) | no |
| `alerts` | las alertas de todos los centinelas en una lista: `--sentinel ci\|collab\|security\|supply\|delivery`, `--level info\|warning\|error`, `--muted show\|hide\|only`; `--since 90m|24h|7d|2w` lista las que estuvieron abiertas en algún momento de ese tiempo, también las cerradas (del historial que el monitor guarda mientras funciona; una alerta cuenta como cerrada tras diez minutos de ausencia) | no |
| `proposals` | las acciones que propuso la IA (`ai.actions.enabled`): `proposals list`, `show ID`, `approve ID`, `reject ID`, `execute ID` (un id puede abreviarse). `approve` y `reject` solo anotan la decisión; `execute` la ejecuta por la misma puerta que la página y necesita `ai.actions.execute`, y con `ai.actions.require_approval` una aprobación antes. Aprobar, rechazar y ejecutar son solo de este equipo | no |
| `score` | la puntuación de la cuenta: número, letra, tendencia, partes, cobertura y el desglose por repositorio; `--compare` la compara con el histórico de la ventana | no |
| `compare` | este periodo frente al anterior: las cifras con su cambio y dirección, quién empeora o mejora; `--window 7\|30d`, `--days all\|workdays\|weekend`, `--baseline previous\|year_ago`, `--format table\|json\|ndjson\|csv`; salida 4 si una cifra tiene pocos datos, 5 con `--fail-on` si una empeora; `--format csv` con otra orden es un mal uso (salida 1) | no |
| `api` | la API de lectura para clientes: `api openapi` imprime el documento OpenAPI de cada ruta congelada (redirígelo a un fichero), `api me` dice por quién toma el monitor a este cliente (modo, usuario, rol, lo que puede hacer la sesión, versión del contrato); un monitor con `api.v1_enabled` cerrado lo dice; `api contract-check` lanza contra él la suite de contrato para clientes (salida 4 si falla una comprobación) | no |
| `team` | la salud de los repositorios en orden, primero los que necesitan a una persona; `--severity warn\|bad` deja los peores y `--repo owner/name` da el detalle de uno | no |
| `live` | el estado del receptor del webhook y los últimos eventos | no |
| `ai` | `ai models [--refresh]` lista los modelos del proveedor de IA con los datos de cada uno; `ai test --provider NOMBRE --model NOMBRE` prueba uno con un texto sintético (latencia, tokens, coste estimado); `ai doctor` dice por qué una IA no responde, sin imprimir una clave | no |
| `lessons` | lo que han enseñado los fallos de esta CI: `lessons list`, `lessons brief --repo NOMBRE` (léelo antes de un push), `lessons failures`, `lessons close` | no |
| `briefs` | los briefs de las pestañas que leen las herramientas de IA: `briefs index`, `briefs show PESTAÑA`, `briefs all` | sí |
| `docs` | las guías de esta versión, leídas de la instalación (sin monitor): `docs list` las nombra con su título, `docs show NOMBRE` imprime una en el idioma de `--lang` | no |
| `screens` | el menú Pantallas de la página: `screens list` (cada tipo de pantalla y si se puede abrir) y `screens urls` (las direcciones completas, listas para un comando de quiosco) | no |
| `keyring` | las claves públicas que pueden firmar: `keyring list`, `add` (`--key-id`, `--public-key`, `--key-scope`, `--expires`), `revoke --key-id`, `verify --document FILE`; sin monitor, las claves privadas se rechazan | no |
| `verify-release` | una carpeta de ficheros de release descargados, comprobada sin red contra SHA256SUMS y su firma: `verify-release --folder DIR`; salida 4 si no son de fiar Además `--installed` (esta instalación contra la lista de materiales), `--attestations`, `--fetch` (necesita `ops.verify_release.fetch`); `doctor --verify-release DIR` comprueba la instalación; `keyring check-rotation --document FILE` comprueba el anuncio de una clave nueva. | no |
| `toolbox` | las pequeñas herramientas del operador que funcionan en este ordenador, sin monitor en marcha: `toolbox limits [N]` (la configuración frente a sus techos), `toolbox workspaces` (los espacios de trabajo y el que se usa), `toolbox ledger [--force]` (el registro de notificaciones ya enviadas; `--force` lo olvida), `toolbox summary` (los eventos por tipo, repositorio y día) y `toolbox export-events FILE` (los eventos como jsonl, csv, parquet o duckdb según el final del nombre; parquet y duckdb necesitan su paquete, el fichero debe ser nuevo) | no |
| `credential` | otro acceso a GitHub para una cuenta mientras todo funciona: `credential replace\|reload [--account ID] [--new-token-file FICHERO\|-]`; nunca imprime un token | no |
| `install-skill` | copia una skill del monitor (`internal` o `external`) a la carpeta donde una herramienta de IA lee sus skills: `install-skill external --dest CARPETA`; el monitor no tiene que estar en marcha | no |
| `gh-token` | imprime un token de instalación de una hora de la GitHub App para que las lecturas de una herramienta gasten la cuota de la App (solo con `github_app.share_reads` activado); ejecútalo sin `--json` | no |
| `watch` | la misma lectura una y otra vez (`watch status\|alerts`, `--interval`, `--once`, `--exit-on-change`); véase [CLI_OPERATOR_spa.md](CLI_OPERATOR_spa.md) | no |
| `completions` | el script de compleción para `bash`, `zsh`, `fish` o `powershell`, escrito desde el analizador real (solo imprime) | no |
| `kiosk` | la dirección del monitor para una TV o una pared (`ops`, `team`, `release`, `quiet`); véase [KIOSK_spa.md](KIOSK_spa.md) | no |
| `metrics` | las cifras como líneas `nombre=valor` para cron y el correo; con `--if-problem` no escribe nada cuando todo va bien; véase [CLI_OPERATOR.md](CLI_OPERATOR.md) | no |
| `posture` | Postura de repositorios y organización, solo lectura (`posture status|matrix|check --repo-name`); véase [POSTURE.md](POSTURE_spa.md) | no |
| `external-ci` | Fuentes de CI externas, solo lectura (`external-ci list|status|probe --source`); véase [EXTERNAL_CI.md](EXTERNAL_CI_spa.md) | no |

Opciones de todos los comandos: `--json` (la respuesta como un documento JSON: `{"ok", "exit", "data"}`), `--account ID`, `--url URL`, `--lite` (puerto 8766), `--timeout SEGUNDOS` (de 1 a 60), `--lang CÓDIGO`. En el modo red pon el token de acceso en la variable de entorno `MONITOR_ACCESS_TOKEN`, la que lee el propio monitor (`MONITOR_TOKEN` se acepta como alias; `--token TOKEN` es el último recurso, porque una opción se ve en la lista de procesos). El orden es: `MONITOR_ACCESS_TOKEN`, luego `MONITOR_TOKEN`, luego `--token`. Viaja en la cabecera `X-Monitor-Access`, nunca en la dirección ni en pantalla. Un `--url` con `http` sin cifrar hacia otro ordenador imprime un aviso por stderr (el token y las respuestas viajarían sin cifrar): usa `https` fuera de una red que controles.

Todos los comandos aceptan también `--format text|table|plain|json|ndjson` (`--json` es `--format json`); véase [CLI_OPERATOR_spa.md](CLI_OPERATOR_spa.md).

La línea de comandos es un cliente de la API de lectura para clientes: las rutas que el contrato congela (`docs/schemas/api_contract.json`) se piden primero bajo `/api/v1/`, y si el monitor responde 404 allí (la API está cerrada, `api.v1_enabled`) se pide la ruta antigua y no se vuelve a probar el prefijo. El documento es el mismo por ambos caminos, así que la salida de ningún comando cambia. `cli.prefer_v1` (activado por defecto) lo desactiva, y la variable `MONITOR_CLI_PREFER_V1` (`0` o `1`) manda sobre él. Las rutas que el contrato no congela se piden siempre por el camino antiguo.

Las horas escritas para las personas (la línea `Last read`, los silencios, el registro, los partes, las notificaciones) usan la zona de este ordenador y la nombran, con la hora UTC al lado (`11:43:07 CET (10:43:07 UTC)`). Elige otra zona con `display.timezone` (`local`, `utc` o un nombre como `Europe/Madrid`; la variable de entorno `MONITOR_TIMEZONE` manda sobre el archivo). `--json` conserva UTC y añade `updated_local`.

## Códigos de salida (estables)

| Código | Significado |
|---|---|
| 0 | todo bien |
| 1 | uso incorrecto del comando (también `--lite` con un comando que necesita la edición completa) |
| 2 | no se alcanza el monitor |
| 3 | el monitor rechaza a este cliente, o el acceso de GitHub de la cuenta falló o caducó (un problema de credencial, no una cuota agotada) |
| 4 | el monitor responde pero está degradado: sin conexión, cuota agotada, aún sin datos, un endpoint que no tiene, o una respuesta que no es JSON |
| 5 | `alerts --fail-on NIVEL` encontró una alerta abierta de ese nivel o peor (una alerta silenciada no cuenta) |
| 6 | `watch --exit-on-change` vio un cambio (solo cuando se da esa opción); véase [CLI_OPERATOR_spa.md](CLI_OPERATOR_spa.md) |

Todo error lleva un `help`: una frase con el siguiente paso, que a menudo nombra la guía que conviene leer (`docs show FIRST_STEPS`). En el formato de texto es la última línea, que empieza por `ayuda:`; con `--json` es el campo `help` junto a `error`: `{"ok": false, "exit": 2, "error": "...", "help": "..."}`.

## Ejemplos

```
python bin/monitor_cli.py health && python bin/monitor_cli.py alerts --fail-on error
python bin/monitor_cli.py alerts --sentinel collab --level warning --json
python bin/monitor_cli.py status --account org-acme
MONITOR_URL=http://192.168.0.20:8765 MONITOR_ACCESS_TOKEN=... python bin/monitor_cli.py health --json
```

`health` distingue tres cosas: el monitor no responde (2), el acceso de GitHub falla (3), y la cuota se agotó o no se alcanza GitHub (4); un monitor que no ha terminado su primera lectura lo dice (4) en vez de mostrar cifras vacías.

## La edición lite

`python bin/monitor_cli.py status --lite`, `doctor --lite` y `health --lite` hablan con el puerto 8766. Los comandos que necesitan cuentas, centinelas o el receptor del webhook se rechazan con el código de salida 1. La edición lite no tiene cuentas ni API de alertas.

## `ai-hook`: decir a una herramienta de IA lo que ve el monitor

`python bin/monitor_cli.py ai-hook install|status|uninstall [--assistant|--cursor|--generic] [--scope project|user] [--project-dir DIR] [--dry-run] [--json]` no necesita un monitor en marcha. Añade, muestra o quita el script de enlace `bin/ai_hook.py` en los ajustes de ganchos de una herramienta de IA (ver la guía de alertas para IA): el fichero de ajustes se fusiona, se guarda una copia y la respuesta de `--json` es ASCII puro. `status` es la acción por defecto.

## El token de acceso en la línea de comandos

En modo red el token se lee de `MONITOR_ACCESS_TOKEN`, luego de `MONITOR_TOKEN`, luego de la primera línea de `--token-file FICHERO` (deja ese fichero legible solo para ti: en un sistema con modos de fichero el comando avisa si otros pueden leerlo) y por último de `--token`, que se ve en la lista de procesos y por eso imprime un aviso por stderr.

## Las herramientas de almacenamiento

`python tools/migrate_storage.py` mueve el estado entre archivos y SQLite, y `python tools/backup_storage.py` hace, comprueba y restaura copias de cualquiera de los dos (ambas se describen en [STORAGE_spa.md](STORAGE_spa.md)). `--doctor` tiene dos comprobaciones para ellas: el almacenamiento y la retención.

## El despachador por lotes: las entradas de un workflow

`python bin/gha_dispatch_all.py plan --inputs` lista además, bajo cada objetivo, las entradas que su workflow pide cuando se dispara a mano (nombre, tipo, obligatoria u opcional, valor por defecto, opciones de una elección y descripción). Se leen del fichero del workflow en `origin/main` del clon con `git show`: no se dispara nada, no se envía nada y no se llama a `gh`. `--json` añade una lista `inputs` a cada fila; es `null` cuando el fichero no está en `origin/main` o usa una forma que el lector no conoce (el estilo de flujo `inputs: {…}`), y `[]` cuando el workflow no pide ninguna entrada.

## Copia de seguridad y el doctor

`backup` y `doctor` trabajan sobre las carpetas de la instalación, así que no necesitan un monitor en marcha. `doctor` sale con `0` cuando todo va bien (también con avisos), `1` cuando falló una comprobación, `3` cuando solo hay avisos y `--strict` (o `ops.doctor.strict_exit`) está activo, y `4` cuando el propio doctor no pudo ejecutarse; son los códigos del doctor, las demás órdenes conservan los códigos de salida de arriba. `backup` sale con `0` cuando termina y `1` cuando se rechaza o el paquete no se verifica. La guía [OPS_spa.md](OPS_spa.md) tiene las comprobaciones, la restauración y la copia programada. El doctor tiene además `compare_window` (si la comparación de dos periodos puede mirar atrás dos ventanas con el historial que pide y conserva) y `etag` (la parte de lecturas condicionales respondidas con 304 en el monitor que corre aquí, y si las respuestas de GitHub llegan sin ETag).

## Identidad de un repositorio, varios dueños

Línea de órdenes: `identity status`, `identity plan`, `identity apply`.

```
python bin/monitor_cli.py identity plan
```

## Órdenes: actions, runner-hook

```
python bin/monitor_cli.py actions proposals
python bin/monitor_cli.py runner-hook started
```

[COLLABORATION_spa.md](COLLABORATION_spa.md)
