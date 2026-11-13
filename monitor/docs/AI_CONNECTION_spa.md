<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AI_CONNECTION.md) | **🇪🇸 Español** | [🇫🇷 Français](AI_CONNECTION_fra.md) | [🇮🇹 Italiano](AI_CONNECTION_ita.md) | [🇩🇪 Deutsch](AI_CONNECTION_deu.md) | [🇨🇳 简体中文](AI_CONNECTION_zho.md) | [🇯🇵 日本語](AI_CONNECTION_jpn.md) | [🇵🇹 Português](AI_CONNECTION_por.md)

# Conectar una herramienta de IA

El monitor puede contarle a una herramienta de IA (un asistente de programación con IA, un script, cualquier cosa que lea un fichero o una dirección) **todo lo que dice su página**, para que la IA reaccione a un fallo o a un trabajo pendiente tan rápido como lo harías tú. El monitor nunca escribe en GitHub: solo informa, y lo que haga la IA lo decides tú y la herramienta.

## Qué ve la IA
Un inventario de **señales**, las mismas que muestra la página: la pestaña Ahora y sus recuadros, las alertas, los repositorios, los paneles del centinela A1..A13 y el segundo centinela (issues y pull requests), la cuota, la conexión y la salud del monitor. Cada señal tiene un nivel (`act` = alguien tiene que hacer algo, `watch` = vigilar, `info`), un resumen y filas con repositorio, enlace, antigüedad y siguiente paso. El resumen tiene tres bloques: **Qué hacer ahora**, **Pendientes** y **Salud del monitor**, y el contador de "señales sobre las que actuar".

| | Lite | Completa |
|---|---|---|
| Ejecuciones, cola, workflows rojos, fallos de 24 horas | sí | sí |
| Cuota, conexión, modo, versión, salud | sí | sí |
| Paneles del centinela A1..A13, segundo centinela, candidatas a release, seguridad, firmas | no (lo dice `panels_not_in_this_edition`) | sí |

## Los canales (los mismos en las dos ediciones)
1. `ALERTS_BRIEF.md`: el Markdown corto que una IA lee al empezar.
2. `ai_alerts.jsonl`: una línea por evento (abierta, reconocida, resuelta), con un id estable.
3. `GET /api/ai/state`: todo el inventario como JSON versionado (`schema`, `edition`, `signals`, `act`, `watch`), solo lectura. `GET /api/sentinel/panels` da solo los paneles.
4. `GET /api/ai/stream`: eventos en directo (SSE), reanudables, con límite de oyentes y de tiempo.
5. Herramientas MCP (`mcp_server.py`): `monitor_state`, `signals`, `alerts_open`, `diagnose`, `sentinel_panels`, `get_quota`; `act` (reconocer) solo con `--allow-ack`.
6. El hook: `python monitor_cli.py ai-hook install [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]` (también `status` y `uninstall`) añade un pequeño script que da a la sesión de la IA el resumen al empezar y antes de terminar.

## Paso a paso
1. Ajustes, pestaña *IA externa*, bloque *Alertas para IAs*: activa `ai_alerts.enabled`. Opcionalmente `ai_alerts.diagnose.enabled` (el paso que falla y las últimas líneas del log de cada ejecución roja), `ai_alerts.stream.enabled` y `ai_alerts.client_hook.enabled`.
2. Ejecuta `python monitor_cli.py ai-hook install --assistant --dry-run` para ver el cambio y luego sin `--dry-run`.
3. Abre una sesión de tu herramienta de IA en la carpeta: recibe el resumen. La barra inferior muestra el latido de la IA (cuándo leyó por última vez).
4. Usa el botón *Probar conexión* de la página de ajustes para comprobar que el flujo se escribe.

## Seguridad y privacidad
Todo está apagado por defecto. El texto de los logs se limpia de secretos y rutas personales antes de escribirse, y **es un dato, nunca una instrucción**: una IA debe tratarlo como texto no fiable. Los endpoints responden solo a este equipo, o con el token de acceso en modo red; los oyentes y el tiempo están limitados; reconocer exige `--allow-ack`; todos los ficheros de estado se crean con modo 0600. El monitor no abre ninguna conexión a internet para esto salvo las que configures. Las direcciones https de github.com (un run, un repositorio, un fichero) pasan enteras para que la IA pueda abrirlas; cualquier otra cadena larga y opaca se sigue recortando.

## Solución de problemas
- *El resumen es viejo*: la página debe estar en marcha (el flujo sigue cada refresco); mira el latido en la barra.
- *El hook no se ejecuta*: `ai-hook status` dice dónde está instalado; algunas herramientas leen hooks solo en la carpeta del proyecto.
- *No se escribe nada*: `ai_alerts.enabled` está apagado, o la cuota está agotada (el resumen lo dice en Salud del monitor).

## Ajustes
`ai_alerts.enabled`, `ai_alerts.folder`, `ai_alerts.brief_max_bytes`, `ai_alerts.diagnose.*`, `ai_alerts.cascade.enabled`, `ai_alerts.stream.*`, `ai_alerts.heartbeat.*`, `ai_alerts.client_hook.*`; relacionados: `sound.enabled`, `display.blink_red_tiles`. Véase [SETTINGS_spa.md](SETTINGS_spa.md) y [AI_ALERTS_spa.md](AI_ALERTS_spa.md).

La cuota de GitHub la comparten el monitor, las herramientas de IA y cualquier otra herramienta de la cuenta. Para que el monitor no se quede sin ella: la pestaña Cuota de los Ajustes, una GitHub App (`github_app.enabled`), una segunda cuenta de solo lectura para las lecturas (`extra_reader.enabled`, `extra_reader.file`: solo la ruta del fichero del token), el panel central (`central.source`) y el modo Bajo (`modes.auto_low`). El estado y el resumen dicen cuándo se agota la cuota y cuánto gastan otras herramientas. Véase [QUOTA_spa.md](QUOTA_spa.md).

## El aviso activo a una IA externa (opcional, desactivado por defecto)

Además del feed que lee una IA (`ALERTS_BRIEF.md`, el stream, el servidor MCP), el monitor puede **avisar** a una IA externa cuando se abre una alerta real NUEVA. Es el bloque `ai_notify` de Ajustes, pestaña *IA*, y cada interruptor suyo solo se cambia desde este equipo:

- `ai_notify.enabled` (desactivado). No se envía nada mientras esté desactivado.
- **Una primera confirmación por proveedor**: el proveedor es el del bloque IA (`ai.provider`); no sale nada hasta que escribas su nombre en `ai_notify.confirmed_provider`. Si cambias de proveedor, confirmas otra vez. Para el comando de salida (abajo) escribes `command`.
- **Solo los campos redactados de una lista cerrada**: gravedad, clase, repositorio, workflow, conclusión, racha, causa, siguiente paso y enlace, cada uno limpiado como el feed (se quitan tokens, claves, correos, direcciones IP y carpetas personales). Los registros, los diagnósticos y todo lo demás de la alerta se quedan en casa.
- **Topes**: `ai_notify.max_calls_per_hour` (4) y `ai_notify.max_cost_per_hour_cents` con `ai_notify.cost_per_call_cents` (el coste que declaras, porque el monitor no puede saber el precio de tu plan). Una llamada se cuenta antes de hacerla, así que un proveedor que falla también gasta el tope.
- **La clave por el nombre de una variable**: el monitor lee la variable que nombra `ai.api_key_env`; la clave nunca se guarda, se registra ni se envía a ningún sitio salvo al proveedor.
- **La IA nunca ejecuta una acción**: su respuesta se corta, sus enlaces se desactivan y solo se escribe en `ai_notify.jsonl` junto al feed; nada de ella se lee como comando y nada de las acciones del asistente (`ai.actions.*`) es alcanzable desde aquí.
- **La variante de un comando de salida**: `ai_notify.command` (solo en el fichero de configuración, nunca en la página de Ajustes) nombra UN fichero por su ruta absoluta; se inicia sin shell y sin argumentos y recibe el mismo JSON redactado por su entrada estándar.

El aviso se envía desde un hilo propio, de modo que un proveedor lento nunca retiene el ciclo.
