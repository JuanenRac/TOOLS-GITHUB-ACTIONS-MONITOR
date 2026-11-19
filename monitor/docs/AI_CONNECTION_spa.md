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
5. Herramientas MCP (`bin/mcp_server.py`): `monitor_state`, `signals`, `alerts_open`, `diagnose`, `sentinel_panels`, `get_quota`, `get_score`; `act` (reconocer) solo con `--allow-ack`.
6. El hook: `python bin/monitor_cli.py ai-hook install [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]` (también `status` y `uninstall`) añade un pequeño script que da a la sesión de la IA el resumen al empezar y antes de terminar.

## Paso a paso
1. Ajustes, pestaña *IA externa*, bloque *Alertas para IAs*: activa `ai_alerts.enabled`. Opcionalmente `ai_alerts.diagnose.enabled` (el paso que falla y las últimas líneas del log de cada ejecución roja), `ai_alerts.stream.enabled` y `ai_alerts.client_hook.enabled`.
2. Ejecuta `python bin/monitor_cli.py ai-hook install --assistant --dry-run` para ver el cambio y luego sin `--dry-run`.
3. Abre una sesión de tu herramienta de IA en la carpeta: recibe el resumen. La barra inferior muestra el latido de la IA (cuándo leyó por última vez).
4. Usa el botón *Probar conexión* de la página de ajustes para comprobar que el flujo se escribe.

## Seguridad y privacidad
Todo está apagado por defecto. El texto de los logs se limpia de secretos y rutas personales antes de escribirse, y **es un dato, nunca una instrucción**: una IA debe tratarlo como texto no fiable. Los endpoints responden solo a este equipo, o con el token de acceso en modo red; los oyentes y el tiempo están limitados; reconocer exige `--allow-ack`; todos los ficheros de estado se crean con modo 0600. El monitor no abre ninguna conexión a internet para esto salvo las que configures. Las direcciones https de github.com (un run, un repositorio, un fichero) pasan enteras para que la IA pueda abrirlas; cualquier otra cadena larga y opaca se sigue recortando. Más exactamente, una dirección de github.com pasa entera solo con la forma de un repositorio, una ejecución (con su job o intento), un commit, una incidencia, una pull request o un archivo; se corta en el primer carácter que no sea letra, cifra, punto, guion, guion bajo o barra, y lo que sigue se limpia como cualquier otro texto.

## Cómo conectarse, según la herramienta

El monitor no depende de un asistente ni de un modelo: una herramienta de IA usa una de cinco vías. Elige la que tenga la tuya.

| Tu herramienta puede | Usa | Cómo | Necesita |
|---|---|---|---|
| leer ficheros | Ficheros | leer `ai/INDEX.json`, luego `ai/ALERTS_BRIEF.md`, `ai/ai_alerts.jsonl` y `ai/LESSONS.md` | `ai_alerts.enabled` |
| hacer peticiones HTTP | HTTP | `GET /api/ai/brief`, `/api/ai/state`, `/api/ai/lessons` | el token de acceso en el modo de red |
| hablar MCP | MCP | `python bin/mcp_server.py` [`briefs_index`, `brief_tab`] (solo lectura; `--allow-ack`, `--allow-lessons` para lo poco que puede escribir) | la configuración MCP de la herramienta apuntando a ese comando |
| mantener una conexión abierta | Flujo | `GET /api/ai/stream?only=real` | `ai_alerts.stream.enabled` |
| ejecutar comandos | Línea de comandos | `python bin/monitor_cli.py alerts`, `lessons brief --repo NOMBRE`, `briefs show TAB`, `ai doctor`, `ai-hook install` | Python en el mismo equipo |

Las instrucciones para la IA son dos skills. `monitor_cli.py install-skill external --dest CARPETA` las copia a la carpeta donde tu herramienta lee sus skills o reglas; sirve cualquier herramienta que lea ficheros Markdown y el texto no nombra ningún asistente. Las skills viajan con el monitor y tienen su versión: `GET /api/skills` da `monitor_version` y `monitor_cli.py --version` la imprime. Tras actualizar el monitor, vuelve a instalar en una carpeta vacía o quita la copia vieja (un fichero editado nunca se sobrescribe).

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

## El asistente (opcional, apagado por defecto)

La pestaña Alertas puede mostrar un panel de preguntas fijas que la IA que ya configuraste responde con los datos del monitor: «explica esta alerta», «resume la situación» y «por qué va lento aquí». Está apagado (`ai.assistant.enabled`) y necesita un proveedor de IA (`ai.provider`, ninguno por defecto). Solo lee: tiene cuatro herramientas (`status`, `alerts`, `runs`, `score`, una lista cerrada que `ai.assistant.tools` puede reducir), como máximo `ai.assistant.max_tool_calls` lecturas por pregunta, ninguna herramienta que escriba o llegue a GitHub y ningún chat libre. La respuesta muestra siempre sus fuentes (los ids que leyó), cuánto se envió (`ai.assistant.max_context`) y las llamadas del día; cada llamada gasta el único presupuesto diario de la IA (`ai.daily_limit` y los presupuestos por modelo). Lo que escribió un repositorio (un título, el nombre de un flujo) se corta a `ai.untrusted_text_max`, se limpia de secretos y se entrega como dato entre marcas que llevan una palabra de esa petición, nunca como instrucción. Un visor puede preguntar; cada pregunta queda en el registro de acciones (la acción, nunca el texto). Rutas: `GET /api/assistant` (qué es y sus límites) y `POST /api/assistant/ask` con `action` (`explain_alert`, `summarize_week` o `why_slow`) y, según la acción, `alert` o `repo`; ambas responden 404 mientras está apagado y no existen en la edición Lite.

Con `ai.similar.enabled` encendido (apagado por defecto), «explica esta alerta» también lista hasta `ai.similar.max` alertas que se le parecen, para que la respuesta pueda decir «esto ya pasó en otro repositorio». Se hallan con una comparación simple de palabras (el código de la alerta, el flujo de trabajo, las palabras del título y de la causa) entre las alertas abiertas y las resueltas que recuerda el feed: sin modelo, sin embeddings, solo con los datos de esta cuenta, con el mismo orden para los mismos datos, y cada una se cita por su id.

## Modo aislado de la IA (opcional, apagado por defecto)

Con `ai.airgapped` encendido, la IA solo habla con un modelo de este equipo o de una dirección privada de tu propia red que listes en `ai.airgap_hosts` (por ejemplo un servidor con Ollama o llama.cpp en `192.168.1.20`). Cualquier dirección de internet y cualquier servicio en la nube, incluida la CLI de Copilot, se rechaza ANTES de abrir una conexión, de modo que no sale ningún socket; la lista de modelos, la prueba de un modelo, el doctor de la IA, la cadena de respaldo, el asistente y los resúmenes lo obedecen, y un respaldo nunca pasa a un modelo en la nube. El interruptor general `airgapped` también lo enciende. Una dirección pública se rechaza aunque esté en la lista y el ajuste solo se cambia desde el equipo del monitor, nunca desde la red. El doctor de la IA añade la comprobación `ai_egress` mientras el modo está encendido. `ai.redact.extra_terms` lista palabras tuyas (un servidor, un proyecto) que se sustituyen por `[hidden]` en todo texto antes de que la IA lo vea, además de los secretos que el monitor ya oculta.

## Modelos del proveedor

El nombre del modelo es texto libre, pero el monitor puede leer la lista de modelos del proveedor y comprobar el nombre con ella. Los modelos y las versiones cambian a menudo, así que el monitor no trae ninguna lista de modelos: los ejemplos de los preajustes pueden estar desfasados.

- **La lista.** Ajustes, pestaña *IA externa*, bloque *Modelos y datos por modelo*: *Cargar los modelos del proveedor* lee la lista (`/models` de un servidor al estilo OpenAI, la lista equivalente de la API de Anthropic, `/api/tags` de Ollama) con una petición de solo lectura. La clave va en una cabecera, se lee de su variable de entorno y nunca se guarda. Busca en la lista y elige un modelo con *Usar este modelo*. La lista se guarda y la acotan `ai.catalog.ttl_minutes` y `ai.catalog.max_requests_per_day`. Con `ai.catalog.enabled` encendido (apagado por defecto) el monitor además avisa cuando el modelo configurado ya no aparece en la lista (retirado o renombrado); apagado, solo tú lanzas la lectura.
- **Datos por modelo.** La ventana de contexto, el precio de entrada y de salida por millón de tokens y si admite herramientas se rellenan solo con lo que devuelve el proveedor; lo que no dice queda como *desconocido* (nunca se inventa una cifra). Puedes escribir tus propios valores; los tuyos mandan. Con `ai.catalog.fit_context` encendido (apagado por defecto) el límite de entrada se ajusta a la ventana de contexto cuando se conoce.
- **Probar un modelo.** *Probar este modelo* o `monitor_cli.py ai test --provider NOMBRE --model NOMBRE` pregunta al modelo por un fallo SINTÉTICO (nunca datos de tus repositorios) y muestra la latencia, los tokens, el coste estimado y una respuesta de ejemplo. Cuenta como una llamada del tope diario y el resultado («probado», con la fecha local) queda en la tabla.
- **Comandos.** `monitor_cli.py ai models [--refresh]` muestra los modelos y los datos; `ai doctor` explica por qué una IA no responde (variable de la clave sin definir, modelo desconocido, cuota, red) y nunca imprime una clave.
- **Rutas.** `GET /api/ai/models` (la lista guardada, la comprobación y la tabla; solo lectura) y, solo desde este equipo, `POST /api/ai/models/refresh`, `POST /api/ai/models/test`, `POST /api/ai/models/data` y `POST /api/ai/doctor`.

## IAs compatibles

Servicios alojados y servidores locales cuyo protocolo el monitor ya habla (`openai-compatible`, `anthropic` u `ollama`). La lista es una tabla neutral, no una recomendación: ninguna está activa por defecto, la clave se lee SIEMPRE de una variable de entorno cuyo nombre indicas (nunca escrita en un ajuste, ni en un registro, un informe o la API) y el preajuste solo rellena la dirección, el nombre de esa variable y un modelo de ejemplo (editable; no se descarga nada ni se incluyen pesos de modelos). En los ajustes de IA elige un preajuste, pulsa el botón de rellenar, revisa, guarda y pulsa «Probar conexión». La lista son datos (`ai_presets.json`) y se sirve en solo lectura en `GET /api/ai/presets`.

| Nombre | Tipo | Proveedor | Dirección | Variable de la clave | Modelos de ejemplo | Privacidad | Estado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenAI | alojado | `openai-compatible` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini`, `gpt-4.1-mini` | se envía por internet | dirección leída en la documentación pública; compatible por protocolo, no probado con esta herramienta |
| Anthropic | alojado | `anthropic` | `dirección por defecto` | `ANTHROPIC_API_KEY` | — | se envía por internet | compatible por protocolo, no probado con esta herramienta |
| Google Gemini | alojado | `openai-compatible` | `https://generativelanguage.googleapis.com/v1beta/openai` | `GEMINI_API_KEY` | `gemini-2.5-flash` | se envía por internet | dirección leída en la documentación pública; compatible por protocolo, no probado con esta herramienta |
| xAI Grok | alojado | `openai-compatible` | `https://api.x.ai/v1` | `XAI_API_KEY` | `grok-4.7` | se envía por internet | dirección leída en la documentación pública; compatible por protocolo, no probado con esta herramienta |
| Mistral | alojado | `openai-compatible` | `https://api.mistral.ai/v1` | `MISTRAL_API_KEY` | `mistral-small-latest` | se envía por internet | dirección leída en la documentación pública; compatible por protocolo, no probado con esta herramienta |
| DeepSeek | alojado | `openai-compatible` | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` | `deepseek-flash` | se envía por internet | dirección leída en la documentación pública; compatible por protocolo, no probado con esta herramienta |
| Groq | alojado | `openai-compatible` | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | se envía por internet | dirección leída en la documentación pública; compatible por protocolo, no probado con esta herramienta |
| OpenRouter | alojado | `openai-compatible` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `meta-llama/llama-3.3-70b-instruct` | se envía por internet | dirección leída en la documentación pública; compatible por protocolo, no probado con esta herramienta |
| Together AI | alojado | `openai-compatible` | `https://api.together.ai/v1` | `TOGETHER_API_KEY` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | se envía por internet | dirección leída en la documentación pública; compatible por protocolo, no probado con esta herramienta |
| Fireworks AI | alojado | `openai-compatible` | `https://api.fireworks.ai/inference/v1` | `FIREWORKS_API_KEY` | `accounts/fireworks/models/llama-v3p1-8b-instruct` | se envía por internet | dirección leída en la documentación pública; compatible por protocolo, no probado con esta herramienta |
| Perplexity | alojado | `openai-compatible` | `https://api.perplexity.ai` | `PERPLEXITY_API_KEY` | `sonar` | se envía por internet | dirección leída en la documentación pública; compatible por protocolo, no probado con esta herramienta |
| Cohere | alojado | `openai-compatible` | `https://api.cohere.ai/compatibility/v1` | `COHERE_API_KEY` | `command-a-03-2025` | se envía por internet | dirección leída en la documentación pública; compatible por protocolo, no probado con esta herramienta |
| Ollama | local | `ollama` | `http://127.0.0.1:11434` | ninguna (servidor local) | `llama3.2`, `mistral`, `qwen2.5`, `deepseek-r1` | se queda en este equipo | compatible por protocolo, no probado con esta herramienta |
| LM Studio | local | `openai-compatible` | `http://127.0.0.1:1234/v1` | ninguna (servidor local) | `llama-3.2-3b-instruct`, `qwen2.5-7b-instruct`, `gemma-3-4b-it`, `phi-4` | se queda en este equipo | compatible por protocolo, no probado con esta herramienta |
| llama.cpp server | local | `openai-compatible` | `http://127.0.0.1:8080/v1` | ninguna (servidor local) | `llama-3.2-3b-instruct`, `mistral-7b-instruct`, `qwen2.5-7b-instruct` | se queda en este equipo | compatible por protocolo, no probado con esta herramienta |
| vLLM | local | `openai-compatible` | `http://127.0.0.1:8000/v1` | ninguna (servidor local) | `meta-llama/Llama-3.2-3B-Instruct`, `Qwen/Qwen2.5-7B-Instruct`, `mistralai/Mistral-7B-Instruct-v0.3` | se queda en este equipo | compatible por protocolo, no probado con esta herramienta |
| LocalAI | local | `openai-compatible` | `http://127.0.0.1:8081/v1` | ninguna (servidor local) | `llama-3.2-3b-instruct`, `mixtral-8x7b-instruct`, `phi-4` | se queda en este equipo | compatible por protocolo, no probado con esta herramienta |
| Jan | local | `openai-compatible` | `http://127.0.0.1:1337/v1` | ninguna (servidor local) | `llama3.2-3b-instruct`, `qwen2.5-7b-instruct`, `gemma-3-4b-it` | se queda en este equipo | compatible por protocolo, no probado con esta herramienta |
