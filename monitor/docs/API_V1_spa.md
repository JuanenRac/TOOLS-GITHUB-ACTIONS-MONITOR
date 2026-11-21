<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](API_V1.md) | **🇪🇸 Español** | [🇫🇷 Français](API_V1_fra.md) | [🇮🇹 Italiano](API_V1_ita.md) | [🇩🇪 Deutsch](API_V1_deu.md) | [🇨🇳 简体中文](API_V1_zho.md) | [🇯🇵 日本語](API_V1_jpn.md) | [🇵🇹 Português](API_V1_por.md)

# La API de lectura v1, paso a paso

Una guía para quien escribe un cliente (un script, una pantalla de pared, una app móvil, una herramienta de IA) contra la API de lectura del monitor. La referencia de cada ruta es el documento OpenAPI que sirve el propio monitor; las reglas del contrato (qué está congelado y qué puede crecer) están en [API_spa.md](API_spa.md). Aquí está el camino a seguir, con órdenes que una prueba ejecuta contra un monitor.

## 1. ¿Está abierta la API?

El prefijo `/api/v1/` responde solo cuando el monitor funciona como servicio (una cuenta del modo equipo, la imagen Docker, la unidad systemd) y se queda cerrado, con 404, para una persona en un equipo. Lo decide el ajuste `api.v1_enabled` (`auto`, `on`, `off`). Un cliente empieza preguntando quién es: un `404` ahí significa que la API está cerrada, no que el cliente esté mal.

## 2. Identificarse

Desde el mismo equipo y sin modo de red no hace falta token. En el modo de red cada petición lleva el token de acceso en la cabecera `X-Monitor-Access`, leído aquí de un fichero para que no aparezca en una línea de órdenes guardada en el historial; con el modo equipo un script inicia sesión en `POST /api/auth/login`. Un token de lectura es todo lo que necesita un cliente de esta API: bajo el prefijo no se escribe.

## 3. Las órdenes

En este orden: quién eres y la versión del contrato (`/api/v1/me`), la descripción de cada ruta congelada (`/api/v1/openapi.json`), los repositorios por páginas (filtran `state`, `ecosystem` y `q`; `limit`; `fields` o `profile=compact` para líneas más cortas; `cursor` es el `next_cursor` de la página anterior, hasta que es `null`), la respuesta comprimida con gzip y dos rutas de la API antigua que el prefijo sirve también con la misma respuesta.

```
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/me
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/openapi.json -o openapi.json
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?state=bad&limit=20&profile=compact"
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?fields=repo,state,risk&limit=5"
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=50&cursor=THE_NEXT_CURSOR"
curl -s --compressed -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=100"
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/health
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/alerts
```

## 4. Errores

Un error de las rutas propias es un objeto JSON con tres claves: `error` y `code` son estables y están pensados para programas, `message` sigue el idioma de `?lang=` y está pensado para personas. Los códigos son api.bad_cursor, api.bad_limit, api.unknown_field, api.bad_profile y api.server_error. Toda respuesta del prefijo, errores incluidos, lleva la cabecera `X-API-Version: 1`. Cada error lleva también `help`, una frase con el siguiente paso y la guía que leer, en el mismo idioma (el campo falta cuando un código no lo tiene; un programa que lo ignore no pierde nada).

```
curl -s -i -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=0"
```

La respuesta, tras las cabeceras, es `{"error": "bad_request", "code": "api.bad_limit", "message": "..."}`.

## 5. Lo mismo desde la línea de órdenes y desde una herramienta de IA

Tres puertas dan los mismos documentos, y una prueba los compara: HTTP como arriba, la línea de órdenes (`python bin/monitor_cli.py api me`, `api openapi`, `api contract-check`; añade `--json` para la respuesta como datos) y el servidor MCP (`python bin/mcp_server.py`, solo lectura: las herramientas `api_me`, `api_openapi` y `api_contract_check`).

## 6. Comprobar un servidor antes de fiarse de él

`python tools/api_contract_suite.py --url URL --token-file token.txt` toma el documento que sirve el servidor como descripción de lo que hay que comprobar e imprime una línea por comprobación y `API_CONTRACT=PASS` o `API_CONTRACT=FAIL`. `python tools/check_api_contract.py --v1` ejecuta la misma suite y además compara las respuestas con el contrato congelado. Ejecuta cualquiera tras cada actualización del monitor o de tu cliente; la CI del monitor ejecuta la suite contra una demo en modo servicio.
