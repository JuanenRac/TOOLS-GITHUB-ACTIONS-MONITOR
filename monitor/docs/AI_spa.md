<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AI.md) | **🇪🇸 Español** | [🇫🇷 Français](AI_fra.md) | [🇮🇹 Italiano](AI_ita.md) | [🇩🇪 Deutsch](AI_deu.md) | [🇨🇳 简体中文](AI_zho.md) | [🇯🇵 日本語](AI_jpn.md) | [🇵🇹 Português](AI_por.md)

# El asistente de IA del centinela

Opcional y **apagado por defecto**. Un modelo de lenguaje puede resumir el parte diario, clasificar alertas, explicar un run fallido, redactar notas de release y responder una pregunta sobre un repositorio. Todo lo que escribe se muestra como propuesta sin verificar.

## Proveedores

- `ollama`: un modelo en este equipo (solo `127.0.0.1`; nada sale del equipo).
- `openai-compatible`: cualquier servicio con un endpoint de chat estilo OpenAI. Sirve también para Gemini (su endpoint compatible con OpenAI) y para OpenAI: pon `base_url`, `model` y el NOMBRE de la variable que guarda la clave.
- `anthropic`: la API Messages de Anthropic (`https://api.anthropic.com`, cabeceras `x-api-key` y `anthropic-version`). El modelo lo eliges tú; no hay ninguno fijo.
- `copilot`: `gh copilot` con tu propio acceso de GitHub (sin clave en el monitor), solo respuesta de texto y sin herramientas. Gasta solicitudes premium de tu plan Copilot. Ejecuta `gh copilot` una vez a mano para que se instale la CLI.
- La clave nunca se guarda: se pone el NOMBRE de una variable de entorno. Los tres proveedores remotos ENVÍAN datos de tus repositorios a un tercero.


## Los iconos de IA de la barra

La barra de arriba a la derecha muestra dos iconos: el chip es la IA integrada en el monitor y las ondas son una herramienta de IA externa que lee el monitor. Una insignia dice el estado sin depender del color: una marca de verificación es activa, una barra oblicua (con el dibujo discontinuo) es inactiva y un triángulo es un error (la IA integrada está configurada pero no responde). Pase el ratón para ver el estado exacto; pulse el icono, o Intro o Espacio cuando tenga el foco, para abrir la sección de IA de los ajustes.

## Qué puede ver

- Toda entrada se limpia: se quitan los caracteres de control, se tachan los secretos por patrón, se limita la longitud, el contenido va entre delimitadores aleatorios y se declara dato no fiable. La respuesta se corta y sus enlaces se neutralizan.
- El mismo limpiador único (tokens, claves, credenciales dentro de direcciones, correos, direcciones IP, tu carpeta personal) sirve a este asistente, al feed para IAs, a los endpoints y al gancho. Funciona por patrones: reduce el riesgo, no es una garantía. Una llamada a un proveedor nunca sigue una redirección (la clave pasaría a otra dirección) y no usa las variables de proxy del entorno: un servidor de este equipo se llama directamente y uno remoto solo pasa por el proxy con `network.use_proxy`.
- En la pestaña Configuración eliges los tipos de evento que puede analizar (`build`, `codeql`, `report`), los repositorios que puede ver (vacío = los que vigila el monitor), el idioma de las respuestas, el límite diario de llamadas y los límites de tamaño. Un botón prueba la conexión y la página muestra las llamadas de hoy.


## Proponer y ejecutar acciones

- Nivel 3 (`ai.actions.enabled`): un comando de la respuesta solo se conserva si coincide con la LISTA CERRADA: `gh run rerun N --failed`, `gh run rerun N`, `gh issue close N` y `act -W ARCHIVO -j JOB` (este último solo se muestra). El comando mostrado se reconstruye con las piezas comprobadas, nunca se copia del modelo; el repositorio y el número de run o issue deben ser ya vigilados por el monitor.
- Nivel 4 (`ai.actions.execute`, interruptor propio, apagado): cada propuesta tiene un botón de confirmar; un diálogo muestra el comando completo y nada se ejecuta hasta que aceptes. Se ejecuta con tu propio `gh` y sin shell, como mucho `ai.actions.max_per_hour` por hora, cada intento va al registro local que muestra la página, y tras dos fallos seguidos las acciones se bloquean hasta que las desbloquees.
- No están en la lista, a propósito: borrar ramas, cerrar o fusionar pull requests, nada sobre secretos o ajustes.

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
