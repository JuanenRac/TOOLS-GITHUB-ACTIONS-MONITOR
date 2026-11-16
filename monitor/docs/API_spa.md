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

- `docs/schemas/api_contract.json` lista cada endpoint de lectura con sus claves y tipos en cada edición y los códigos de error.
- `python tools/check_api_contract.py` comprueba un monitor en marcha contra él (`--lite`, `--url`, `--token-file`) e imprime `CONTRACT=PASS` o `CONTRACT=FAIL`; ejecútalo tras cada actualización del monitor o de tu cliente.

## Streams

- `GET /api/ai/stream` (las alertas) y `GET /api/live-events/stream` (los eventos del webhook, `live.sse.enabled`) son eventos enviados por el servidor, de solo lectura y apagados por defecto; mira [AI_ALERTS_spa.md](AI_ALERTS_spa.md) y [WEBHOOK_spa.md](WEBHOOK_spa.md).
