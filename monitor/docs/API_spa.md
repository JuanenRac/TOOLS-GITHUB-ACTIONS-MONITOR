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

- `docs/schemas/api_contract.json` lista cada endpoint de lectura con sus claves y tipos en cada edición y los códigos de error. Las rutas que se pueden leer pero no están congeladas (flujos, texto, exportaciones de otras herramientas) se listan en `unfrozen` del mismo fichero, cada una con su motivo; `/api/data`, que da las ejecuciones, los repositorios y la cuota, sí está congelada.
- `python tools/check_api_contract.py` comprueba un monitor en marcha contra él (`--lite`, `--url`, `--token-file`) e imprime `CONTRACT=PASS` o `CONTRACT=FAIL`; ejecútalo tras cada actualización del monitor o de tu cliente.

## API de lectura v1 (desactivada por defecto)

- Activa `api.v1_enabled` (Ajustes, Avanzado, API de lectura v1). Cada ruta de lectura se sirve entonces también bajo `/api/v1/` (por ejemplo `/api/v1/alerts`): la misma respuesta y los mismos roles, más la cabecera `X-API-Version: 1`. Mientras está desactivada, en la edición lite y para cualquier otro número de versión, el prefijo responde 404.
- `/api/v1/me`: quién pregunta: `mode` (`individual` o `team`), `authenticated`, `user`, y el `role` y las `accounts` de la sesión de equipo (null sin ella), los `limits` de las listas y la versión.
- `/api/v1/repos`: los repositorios que vigila el monitor, una línea cada uno (`repo`, `ecosystem`, `state`, `risk`, `runs_24h`, `failures_24h`, `red_workflows`, `stuck_runs`, `alerts`, `last_run_at`). Filtros `state`, `ecosystem` y `q`; `limit` (por defecto `api.default_limit`, como mucho `api.max_limit`); `cursor` (el `next_cursor` de la página anterior, firmado y válido durante `api.cursor_ttl_seconds`); `fields=a,b` o `profile=compact` para líneas más cortas. La respuesta se comprime con gzip cuando el cliente lo acepta.
- `/api/v1/openapi.json`: una descripción OpenAPI 3 ligera de esas dos rutas.
- Las dos rutas propias responden un error como `{"error": "bad_request", "code": "api.bad_cursor", "message": "..."}`: `error` y `code` son estables, `message` sigue el idioma de `?lang=`. Códigos: api.bad_cursor, api.bad_limit, api.unknown_field, api.bad_profile. Todo es de solo lectura: no hay ninguna escritura bajo `/api/v1/`. La forma está congelada en la sección `v1_endpoints` del contrato y se comprueba con `python tools/check_api_contract.py --v1` contra un monitor con `api.v1_enabled` activado.

## Streams

- `GET /api/ai/stream` (las alertas) y `GET /api/live-events/stream` (los eventos del webhook, `live.sse.enabled`) son eventos enviados por el servidor, de solo lectura y apagados por defecto; mira [AI_ALERTS_spa.md](AI_ALERTS_spa.md) y [WEBHOOK_spa.md](WEBHOOK_spa.md).
- `POST /api/chatops/slack` y `POST /api/chatops/discord` reciben los comandos de solo lectura de un chat (desactivados por defecto, `chatops.enabled`). No usan el token de acceso: la prueba es la firma de la plataforma, y una petición sin firma válida se rechaza antes de leer nada. Ver [CHATOPS_spa.md](CHATOPS_spa.md).
