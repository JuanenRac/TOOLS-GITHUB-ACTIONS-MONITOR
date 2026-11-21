<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](API.md) | **🇪🇸 Español** | [🇫🇷 Français](API_fra.md) | [🇮🇹 Italiano](API_ita.md) | [🇩🇪 Deutsch](API_deu.md) | [🇨🇳 简体中文](API_zho.md) | [🇯🇵 日本語](API_jpn.md) | [🇵🇹 Português](API_por.md)

# La API para clientes

Lo que puede dar por seguro un script, una pantalla de pared o un cliente móvil. Desde la 2.0.0 los endpoints de lectura están congelados: una clave del contrato conserva su nombre y su tipo, pueden aparecer claves nuevas y nada se quita ni se cambia sin una versión mayor nueva.

## Preguntar

- En el modo normal la API responde en `127.0.0.1` sin inicio de sesión. En el modo de red cada petición lleva el token de acceso en la cabecera `X-Monitor-Access` (o la cookie de sesión, o `POST /api/access` una vez). Con el modo equipo un script inicia sesión en `POST /api/auth/login`.
- Una palabra de la consulta que un endpoint no conoce se ignora. Las respuestas son JSON en UTF-8, salvo el resumen en Markdown y los streams.

## Errores

- Un error es JSON `{"error": "palabra"}`, a veces con un `code`. `401 access` significa que falta el token o es erróneo, `403 forbidden` que la petición no viene de donde se permite (también un `Host` ajeno), `404` que la ruta no existe en esta edición (la lite responde 404 a lo que solo tiene la completa), `429` que la dirección está bloqueada o los oyentes están llenos.
- Una escritura rechazada nunca cambia nada. Las escrituras no forman parte del contrato.

## El contrato

- `docs/schemas/api_contract.json` lista cada endpoint de lectura con sus claves y tipos en cada edición y los códigos de error. Las rutas que se pueden leer pero no están congeladas (flujos, texto, exportaciones de otras herramientas) se listan en `unfrozen` del mismo fichero, cada una con su motivo; `/api/data`, que da las ejecuciones, los repositorios y la cuota, sí está congelada. Sus claves llegan hasta los elementos de las listas: una lista escrita `[{...}]` en el fichero describe sus elementos (se comprueban los tres primeros), de modo que las ejecuciones, los repositorios y la cuota de `/api/data`, las alertas de `/api/alerts` y `/api/auth/me` no pueden cambiar sin que la comprobación falle.
- `python tools/check_api_contract.py` comprueba un monitor en marcha contra él (`--lite`, `--url`, `--token-file`) e imprime `CONTRACT=PASS` o `CONTRACT=FAIL`; ejecútalo tras cada actualización del monitor o de tu cliente.

## API de lectura v1 (automática por defecto)

- Configura `api.v1_enabled` (Ajustes, Avanzado, API de lectura v1): `auto` (por defecto) responde cuando el monitor corre como servicio (una cuenta del modo equipo, la imagen de Docker, la unidad de systemd) y queda cerrada para una persona en un solo equipo; `on` siempre; `off` nunca (los antiguos true y false equivalen a on y off). Cuando responde, cada ruta de lectura se sirve también bajo `/api/v1/` (por ejemplo `/api/v1/alerts`): la misma respuesta y los mismos roles, más la cabecera `X-API-Version: 1`. Mientras está cerrada, en la edición lite y para cualquier otro número de versión, el prefijo responde 404.
- `/api/v1/me`: quién pregunta: `mode` (`individual` o `team`), `authenticated`, `user`, y el `role` y las `accounts` de la sesión de equipo (null sin ella), lo que puede hacer la sesión (`capabilities`: `read`, `write`, `admin` y `v1_write`, siempre falso porque el prefijo es de solo lectura), los `limits` de las listas, la versión del monitor y la versión del contrato (`contract`, `1.0`: crece con cada clave añadida y nunca pierde una).
- `/api/v1/repos`: los repositorios que vigila el monitor, una línea cada uno (`repo`, `ecosystem`, `state`, `risk`, `runs_24h`, `failures_24h`, `red_workflows`, `stuck_runs`, `alerts`, `last_run_at`). Filtros `state`, `ecosystem` y `q`; `limit` (por defecto `api.default_limit`, como mucho `api.max_limit`); `cursor` (el `next_cursor` de la página anterior, firmado y válido durante `api.cursor_ttl_seconds`); `fields=a,b` o `profile=compact` para líneas más cortas. La respuesta se comprime con gzip cuando el cliente lo acepta.
- `/api/v1/openapi.json`: la descripción OpenAPI 3 de toda la API de lectura congelada, construida desde el contrato (`docs/schemas/api_contract.json`) y nunca escrita a mano: cada ruta congelada con las claves y los tipos que promete, `x-lite` (lo que responde la edición lite) y `x-local-only`. Las rutas que el contrato no congela son experimentales: responden 404 bajo `/api/v1/` y no están en el documento, salvo que `api.experimental_routes` esté activado (entonces se listan con `x-experimental`). Las rutas antiguas bajo `/api/` no cambian nunca. Descárgalo con `python bin/monitor_cli.py api openapi`.
- Una guía paso a paso para quien escribe un cliente, con las órdenes en orden y los errores: [API_V1_spa.md](API_V1_spa.md).
- `python tools/api_contract_suite.py` es la suite de contrato para clientes externos (solo la biblioteca estándar, solo lee): dale la dirección de un servidor (`--url`) y un token de lectura (`--token-file`) y toma el documento que sirve el servidor como descripción de lo que comprobar: la forma de cada ruta que no necesita parámetros, la cabecera `X-API-Version`, el sobre de error y sus códigos estables, las páginas y sus cursores, `fields` y `profile=compact`, gzip y que nada se puede escribir bajo el prefijo. Imprime una línea por comprobación y `API_CONTRACT=PASS` o `API_CONTRACT=FAIL` (`--json` para un documento); el código de salida es 0, 1 o 2 (nada responde). `python bin/monitor_cli.py api contract-check` la lanza contra el monitor de la línea de comandos.
- Las mismas tres cosas son herramientas del servidor MCP (`python bin/mcp_server.py`, solo lectura, sin ningún indicador): `api_me` (quién cree el monitor que es el cliente), `api_openapi` (el documento, o una ruta con `path`) y `api_contract_check` (la suite de contrato, respuesta `{ok, checks, failed, rows}`). HTTP, la línea de comandos (`api me`, `api openapi`, `api contract-check`) y MCP dan el mismo documento; una prueba los compara. Mientras el prefijo está cerrado, las herramientas lo dicen en una línea.
- Las dos rutas propias responden un error como `{"error": "bad_request", "code": "api.bad_cursor", "message": "..."}`: `error` y `code` son estables, `message` sigue el idioma de `?lang=`. Códigos: api.bad_cursor, api.bad_limit, api.unknown_field, api.bad_profile, api.server_error. Todo es de solo lectura: no hay ninguna escritura bajo `/api/v1/`. La forma está congelada en la sección `v1_endpoints` del contrato y se comprueba con `python tools/check_api_contract.py --v1` contra un monitor con `api.v1_enabled` activado.

### Ejemplos con curl

El token es el de acceso del modo de red (o usa una sesión del modo equipo); sin modo de red no hace falta token desde el mismo equipo. Un cliente sigue `next_cursor` hasta que sea `null` y lee antes `/api/v1/me` para saber la versión del contrato y lo que puede hacer la sesión.

```
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/me
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?state=bad&limit=20&profile=compact"
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/openapi.json -o openapi.json
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=50&cursor=THE_NEXT_CURSOR"
```

## Streams

- `GET /api/ai/stream` (las alertas) y `GET /api/live-events/stream` (los eventos del webhook, `live.sse.enabled`) son eventos enviados por el servidor, de solo lectura y apagados por defecto; mira [AI_ALERTS_spa.md](AI_ALERTS_spa.md) y [WEBHOOK_spa.md](WEBHOOK_spa.md).
- `POST /api/chatops/slack` y `POST /api/chatops/discord` reciben los comandos de solo lectura de un chat (desactivados por defecto, `chatops.enabled`). No usan el token de acceso: la prueba es la firma de la plataforma, y una petición sin firma válida se rechaza antes de leer nada. Ver [CHATOPS_spa.md](CHATOPS_spa.md).

## Otras rutas de la página

Estas rutas sirven la página y las herramientas de este equipo. No forman parte del contrato congelado y pueden cambiar entre versiones. POST cambia algo; "este equipo" significa que solo puede usarla el equipo que ejecuta el monitor.

| Ruta | Qué hace |
| --- | --- |
| `/api/about` | El panel Acerca de: versiones, enlaces, ficheros, salud, créditos y el aviso de una actualización; sin secretos. |
| `/api/act/plan` | POST, este equipo. Prepara lo que haría una ejecución local con `act`; todavía no se ejecuta nada. |
| `/api/act/confirm` | POST, este equipo. Ejecuta un workflow en este equipo con `act` tras su plan; la ejecución queda registrada. |
| `/api/act/status` | El estado de la ejecución local en curso. |
| `/api/act/stop` | POST, este equipo. Detiene la ejecución local. |
| `/api/advanced` | El estado de las funciones que se activan por elección: la red, el almacén del token de GitHub, las acciones en GitHub, la ejecución local y el modo demo; nunca un token. |
| `/api/ai/actions` | El estado de las acciones de la IA (bloqueadas o no), su registro, las propuestas en espera (`proposals`) y el estado de la IA. |
| `/api/ai/actions/confirm` | POST, este equipo. Ejecuta una acción propuesta por la IA, tras confirmarla; queda registrada. |
| `/api/ai/actions/review` | POST, este equipo. Aprueba o rechaza una propuesta de la IA (`id`, `decision`); queda registrado. No se ejecuta nada. |
| `/api/ai/actions/unlock` | POST, este equipo. Desbloquea las acciones de la IA durante un tiempo limitado; queda registrado. |
| `/api/ai/budget` | Las llamadas y el coste estimado de hoy de cada modelo de IA, los límites y los últimos fallos; no consulta a ningún proveedor. |
| `/api/ai/test` | POST, este equipo. Prueba la conexión de la IA configurada; no cambia nada. |
| `/api/alerts/unmute` | POST. Quita el silencio de una alerta; queda registrado. |
| `/api/analytics` | El resumen de la analítica de las ejecuciones: duraciones, cola, pasos, tests inestables y ejecuciones más lentas, y la estimación del tiempo ahorrado si está encendida. |
| `/api/discovery` | Lo que encontró el descubrimiento: el cuadro con la cuenta y los repositorios mostrados y ocultos, los últimos eventos, los grupos sugeridos, sus ajustes, los forks y las organizaciones. |
| `/api/discovery/group` | POST. Añade un grupo sugerido al fichero de ecosistemas, guardando una copia del fichero. |
| `/api/gh-action/plan` | POST, este equipo. Prepara lo que se enviaría a GitHub (un reintento, una cancelación, un dispatch o una fusión); todavía no se envía nada. |
| `/api/gh-action/confirm` | POST, este equipo. Envía a GitHub lo que decía el plan, tras confirmarlo; queda registrado. Si GitHub lo rechaza, la respuesta lleva `reason`: forbidden, not_found, method, conflict o invalid. |
| `/api/github-token` | Solo este equipo. El estado del almacén del token de GitHub (el sistema y si hay uno guardado); nunca su valor. |
| `/api/help/search` | Busca en los temas de ayuda con una palabra y devuelve los que coinciden. |
| `/api/help/topic` | El texto de un tema de ayuda (`id=`) en el idioma de la página. |
| `/api/help/topics` | La lista de los temas de ayuda con sus títulos. |
| `/api/hot-only` | POST, este equipo. El interruptor "solo lo caliente" de la página; no cambia ningún estado guardado. |
| `/api/mirror` | El estado del espejo de los repositorios (apagado por defecto). |
| `/api/mode` | GET: el modo de trabajo, la estimación de cada modo y el tiempo restante. POST, este equipo: cambia el modo. |
| `/api/notify/test` | POST. Envía un mensaje de prueba a un canal de notificación; no cambia nada. |
| `/api/quota-pool/status` | Solo este equipo. La cuota de cada fuente de lecturas y lo que le falta a la GitHub App; nunca una clave ni un token. |
| `/api/refresh-repos` | POST, este equipo. Refresca solo los repositorios que indiques y reescribe el fichero de los rojos (lo usa `finalize --execute`). |
| `/api/screens/logo` | GET: el logo de la organización como imagen. POST: guarda uno nuevo (máximo 1 MB, comprobado por su tipo real). |
| `/api/screens/logo/remove` | POST. Quita el logo de la organización; queda registrado. |
| `/api/sentinel/ai` | POST. Pide a la IA que explique una alerta o una compilación; la petición es pequeña y la pregunta se limpia de secretos antes. No existe mientras la IA está apagada. |
| `/api/sentinel/historial` | Ayer frente a hoy: los rojos y las firmas pendientes que aparecen o desaparecen. |
| `/api/sentinel/parte/save` | POST. Guarda una copia del parte diario en la carpeta de auditoría; un GET nunca escribe. |
| `/api/sentinel/security` | Lo que GitHub dice que está abierto o falta en seguridad (el centinela de Seguridad; apagado por defecto; solo lectura). |
| `/api/session-token` | Un token de un solo uso para el siguiente cambio de un ajuste; la página lo pide justo antes de escribir. |
| `/api/statusbar` | Lo que muestra la barra al pie de la página: edición, dirección, cuenta y centinelas; sin secretos ni llamadas a GitHub. |
| `/api/welcome` | GET: si la guía de primer inicio está hecha. POST, este equipo: la marca como hecha o no. |
