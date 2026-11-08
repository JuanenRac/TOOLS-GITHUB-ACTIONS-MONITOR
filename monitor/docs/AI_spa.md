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
