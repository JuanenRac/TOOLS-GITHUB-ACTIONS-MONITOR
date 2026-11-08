<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Avisos para IAs

Un workflow en rojo no sirve de nada si nadie de los que trabajan en el repositorio se entera. El monitor escribe un pequeño feed que cualquier herramienta de IA (Codex, Gemini CLI, Copilot) o script puede leer.

## Qué escribe (local, solo lectura, sin red)
- `ai_alerts.jsonl`: una línea por evento (abierto, reconocido, resuelto) con id estable, severidad, repositorio, workflow, conclusión, desde cuándo, racha, enlace, una causa probable (**real** o **transitoria**), una acción sugerida y el estado.
- `ALERTS_BRIEF.md`: se reescribe en cada ciclo y es corto (`ai_alerts.brief_max_bytes`, 2 KB por defecto). Las alertas reales van primero.
- Las causas transitorias (502/503/504, tiempos agotados, límites de uso, fallos de descarga, una ejecución que no arrancó) se distinguen de los fallos reales con reglas que puedes editar en `ai_alerts.transient_patterns`. Una alerta se resuelve sola cuando el workflow vuelve a verde, y puedes reconocerla (`ack`), lo que solo cambia este estado local.
- Todo pasa antes por un limpiador: tokens, claves, correos, direcciones IP y tu carpeta personal nunca llegan a los ficheros, a los endpoints ni al hook.
- La carpeta es `ai_alerts.folder` (por defecto junto al monitor); elige una que lean tus sesiones de IA. `ci_red.json` lleva un `ai_hint` opcional (clase, causa, acción) en cada workflow en rojo.

## Cómo la lee una IA
- Pon esto en las instrucciones de tu proyecto o skill: *«Al empezar, lee ALERTS_BRIEF.md (ruta) y di qué alertas reales hay abiertas.»*
- O pregunta al monitor en marcha: `GET /api/ai/brief` (Markdown, o `?fmt=json`) y `GET /api/ai/alerts?since=SEGUNDOS`. Siguen las mismas reglas que el resto de la página (este equipo; con el modo red, el token de acceso).
- O añade el servidor MCP (solo lectura): `python mcp_server.py`, herramientas `get_alerts`, `get_red_repos`, `get_run_failure`, `get_quota`; `--allow-ack` añade `ack_alert` (solo estado local). Gemini CLI, Codex y VS Code (Copilot): añade el mismo comando como servidor stdio en sus ajustes MCP.

## Avisos que te llegan
- Una alerta real NUEVA va a los canales de notificación que ya configuraste (Ajustes > Notificaciones).
- Opcional, apagado por defecto: `ai_alerts.hook` envía por POST la alerta real nueva (una lista cerrada de campos limpiados) a una dirección de este equipo, como máximo `max_per_hour` veces por hora, para que un script tuyo despierte una sesión de IA.
- Nada de esto envía datos a un proveedor de IA, ejecuta un comando ni escribe en GitHub.
