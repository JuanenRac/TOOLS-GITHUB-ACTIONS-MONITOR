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


## Qué puede ver

- Toda entrada se limpia: se quitan los caracteres de control, se tachan los secretos por patrón, se limita la longitud, el contenido va entre delimitadores aleatorios y se declara dato no fiable. La respuesta se corta y sus enlaces se neutralizan.
- En la pestaña Configuración eliges los tipos de evento que puede analizar (`build`, `codeql`, `report`), los repositorios que puede ver (vacío = los que vigila el monitor), el idioma de las respuestas, el límite diario de llamadas y los límites de tamaño. Un botón prueba la conexión y la página muestra las llamadas de hoy.


## Proponer y ejecutar acciones

- Nivel 3 (`ai.actions.enabled`): un comando de la respuesta solo se conserva si coincide con la LISTA CERRADA: `gh run rerun N --failed`, `gh run rerun N`, `gh issue close N` y `act -W ARCHIVO -j JOB` (este último solo se muestra). El comando mostrado se reconstruye con las piezas comprobadas, nunca se copia del modelo; el repositorio y el número de run o issue deben ser ya vigilados por el monitor.
- Nivel 4 (`ai.actions.execute`, interruptor propio, apagado): cada propuesta tiene un botón de confirmar; un diálogo muestra el comando completo y nada se ejecuta hasta que aceptes. Se ejecuta con tu propio `gh` y sin shell, como mucho `ai.actions.max_per_hour` por hora, cada intento va al registro local que muestra la página, y tras dos fallos seguidos las acciones se bloquean hasta que las desbloquees.
- No están en la lista, a propósito: borrar ramas, cerrar o fusionar pull requests, nada sobre secretos o ajustes.

## IAs compatibles

Servicios alojados y servidores locales cuyo protocolo el monitor ya habla (`openai-compatible`, `anthropic` u `ollama`). La lista es una tabla neutral, no una recomendación: ninguna está activa por defecto, la clave se lee SIEMPRE de una variable de entorno cuyo nombre indicas (nunca escrita en un ajuste, ni en un registro, un informe o la API) y el preajuste solo rellena la dirección, el nombre de esa variable y un modelo de ejemplo (editable; no se descarga nada ni se incluyen pesos de modelos). En los ajustes de IA elige un preajuste, pulsa el botón de rellenar, revisa, guarda y pulsa «Probar conexión». La lista son datos (`ai_presets.json`) y se sirve en solo lectura en `GET /api/ai/presets`.

| Nombre | Tipo | Proveedor | Dirección | Variable de la clave | Modelos de ejemplo | Privacidad | Estado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenAI | alojado | `openai-compatible` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini`, `gpt-4.1-mini` | se envía por internet | compatible por protocolo, no probado con esta herramienta |
| Anthropic | alojado | `anthropic` | `dirección por defecto` | `ANTHROPIC_API_KEY` | — | se envía por internet | compatible por protocolo, no probado con esta herramienta |
| Google Gemini | alojado | `openai-compatible` | `https://generativelanguage.googleapis.com/v1beta/openai` | `GEMINI_API_KEY` | `gemini-2.5-flash` | se envía por internet | dirección leída en la documentación pública; compatible por protocolo, no probado con esta herramienta |
| xAI Grok | alojado | `openai-compatible` | `https://api.x.ai/v1` | `XAI_API_KEY` | `grok-4` | se envía por internet | compatible por protocolo, no probado con esta herramienta |
| Mistral | alojado | `openai-compatible` | `https://api.mistral.ai/v1` | `MISTRAL_API_KEY` | `mistral-small-latest` | se envía por internet | compatible por protocolo, no probado con esta herramienta |
| DeepSeek | alojado | `openai-compatible` | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` | `deepseek-chat` | se envía por internet | compatible por protocolo, no probado con esta herramienta |
| Groq | alojado | `openai-compatible` | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | se envía por internet | compatible por protocolo, no probado con esta herramienta |
| OpenRouter | alojado | `openai-compatible` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `meta-llama/llama-3.3-70b-instruct` | se envía por internet | compatible por protocolo, no probado con esta herramienta |
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
