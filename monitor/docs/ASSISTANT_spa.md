<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# El asistente

Preguntas fijas a la IA que ya configuraste, respondidas con los datos del monitor, solo lectura. Apagado por defecto.

## Enciéndelo

1. Configura un proveedor de IA (`ai.provider`; ver [AI_CONNECTION_spa.md](AI_CONNECTION_spa.md)).
2. En Ajustes, IA, activa `ai.assistant.enabled`. El panel aparece en la pestaña Alertas. No existe en la edición Lite.
3. Haz una pregunta; la respuesta muestra sus fuentes, cuánto se envió y las llamadas del día.

## Las cinco preguntas

- `explain_alert`: por qué hay una alerta abierta (necesita la alerta).
- `summarize_week`: la situación de la cuenta.
- `why_slow`: por qué el CI de un repositorio va lento o atascado (necesita el repositorio).
- `explain_repo`: la situación de un repositorio, sus ejecuciones y sus alertas abiertas.
- `prioritize`: las alertas abiertas, el estado y la puntuación puestos en orden, con sus ids.

No hay chat libre.

## Qué lee

Cuatro herramientas, una lista cerrada que `ai.assistant.tools` puede reducir: `status`, `alerts`, `runs` y `score`. Como mucho `ai.assistant.max_tool_calls` lecturas por pregunta y `ai.assistant.max_context` de texto enviado. Con `ai.similar.enabled` activo, «explica esta alerta» también lista alertas parecidas, halladas comparando palabras, sin modelo.

## Qué no hace nunca

No escribe nada ni toca nada en GitHub. Lo que escribió un repositorio (un título, el nombre de un workflow) se recorta, se limpia de secretos y de las palabras que ocultaste, y se entrega como dato entre marcas, nunca como instrucción. Cada pregunta gasta el único presupuesto diario de la IA (`ai.daily_limit`). Con `ai.airgapped` activo solo se usa un modelo de este equipo o de tu red privada.

## Compruébalo

`GET /api/assistant` dice qué es y sus límites; `POST /api/assistant/ask` recibe `action` y, según haga falta, `alert` o `repo`. Ambas responden 404 mientras está apagado. La pregunta queda en el registro de acciones (nunca su texto); con `ai.prompt_log.enabled` los prompts limpios se guardan en un registro local que puedes ver y vaciar en Ajustes.

## Propuestas que aprueban personas

Cada orden que propone una IA (`ai.actions.enabled`) queda marcada como venida de una IA, lleva la huella (SHA-256) de lo que se ejecutaría y se conserva hasta que caduca, también tras un reinicio. Nunca se ejecuta sola. Aprobarla desde la página o la línea de órdenes es decisión de personas: con dos o más usuarios hacen falta dos personas (quien preguntó a la IA cuenta como una y no puede aprobar la suya); con un usuario escribes los ocho primeros caracteres de la huella. Una persona basta para rechazar. Con `ai.assistant.can_propose` (apagado) una respuesta del chat también puede convertirse en propuesta. Se ven en la pestaña Alertas.

## Chat libre

`ai.chat.enabled` (apagado) añade un chat en la pestaña Alertas. La IA solo puede leer, con las cuatro herramientas de arriba; las pide y el monitor decide. Mismo presupuesto, mismo limpiador, mismas marcas alrededor de lo que escribieron los repositorios; cada respuesta lista lo leído. No hay ninguna herramienta que escriba.

## Alertas parecidas con un modelo local

Con `ai.rag.enabled` (apagado) y `ai.rag.model`, «explicar esta alerta» ordena las alertas por los embeddings de un modelo que corre en este equipo (la API de Ollama; solo se acepta una dirección local). El índice guarda vectores y huellas, nunca el texto, hasta `ai.rag.max_mb`; borrar `ai_rag_index.json` no pierde nada. Sin modelo se usa la comparación de palabras. Solo se ha probado con un servidor falso.

## Informe de un repositorio

Con `ui.copy_report.enabled` la pestaña Alertas copia el informe de un repositorio en Markdown, o un borrador de comentario de triaje, para pegarlo a mano. Sin IA, sin consultar GitHub, sin publicar nada.

Rutas: `GET /api/assistant/extras`, `GET /api/assistant/repo-report?repo=`, `POST /api/assistant/chat`. Para clientes MCP los resúmenes también son recursos: `resources/list`, `resources/read`, `monitor://briefs/index`, `monitor://briefs/<tab>`.
