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

## El servidor MCP es local

`mcp_server.py` habla JSON por entrada y salida estándar con la herramienta de IA que lo arranca: no tiene puerto de red y nunca debe ponerse detrás de uno. Un mensaje mal formado recibe un error solo para ese mensaje, una línea de más de 64 KB se rechaza, y `ack_alert` (solo con `--allow-ack`) no cambia más que el estado local del feed. El feed puede contener nombres de repositorios y mensajes de error breves de la CI; todo se limpia de tokens, claves, correos, direcciones IP y la carpeta de una persona antes de salir.

## La conexión con una herramienta de IA (solo lectura)

- **Siempre al día.** El flujo y el resumen se reescriben en cada refresco de la pestaña Alertas, en cada lectura del flujo y en cada ciclo, así que coinciden con la página (antes la seguían con un ciclo de retraso). `ALERTS_BRIEF.md` lleva `Updated:` (tu zona horaria, con UTC) y una línea para máquinas `updated_epoch:`; `GET /api/ai/brief?fmt=json` añade `updated`, `updated_local` y `age_seconds`.
- **Por qué está roja.** Con `ai_alerts.diagnose.enabled` (desactivado por defecto: lee de GitHub la lista de trabajos y el final del log de una ejecución roja nueva, con llamadas de solo lectura que cuentan en tu cuota) cada alerta lleva `diagnosis`: el primer paso que falla y unas diez líneas relevantes (`ai_alerts.diagnose.log_lines`), limpias de secretos y por debajo de `ai_alerts.diagnose.max_bytes`. Se leen como mucho `max_per_cycle` ejecuciones por ciclo, cada una una sola vez. Un log que muestra un error de infraestructura hace la alerta transitoria.
- **Cascadas.** Con `ai_alerts.cascade.enabled` (activado: solo cambia cómo se listan las alertas) una alerta que está roja porque otro repositorio está rojo - su log lo nombra, o lo dice una regla de `ai_alerts.cascade.map` (`{"repo-base": ["repo-cliente"]}`) - se lista bajo ese en el resumen («Also red because of it (fix this one first)») y lleva `origin` en el flujo.
- **Flujo en directo.** Con `ai_alerts.stream.enabled` (desactivado por defecto), `GET /api/ai/stream[?only=real]` envía eventos del servidor: un marco `hello` (cuántas alertas reales hay abiertas, las primeras, la edad del resumen) y un marco `alert` por cada evento del flujo; `Last-Event-ID` (o `?since=`) reanuda. Es de solo lectura, sigue las mismas reglas de acceso que el resto de la página (en modo red, el token de acceso como cabecera o cookie) y lo limitan `stream.max_clients` y `stream.max_seconds`.
- **Herramientas MCP.** `alerts_open` (alertas abiertas con edad, diagnóstico y origen), `alert_diagnose(id)` (el diagnóstico guardado, o una lectura del log con llamadas `gh` de solo lectura) y, solo con `--allow-ack`, `alert_ack(id)`. Cuando la herramienta de IA se conecta, el servidor le dice en sus `instructions` y con una notificación cuántas alertas reales hay abiertas.
- **Script de enlace.** `python monitor_cli.py ai-hook install [--assistant|--cursor|--generic] [--scope project|user]` (también `status` y `uninstall`; `--dry-run` muestra el cambio) añade `ai_hook.py` a los ajustes de ganchos de la herramienta: SessionStart y UserPromptSubmit añaden el resumen a la sesión cuando hay alertas reales abiertas; Stop pide a la IA que las mire antes de cerrar un turno, pero solo con `ai_alerts.client_hook.block_on_stop` (desactivado por defecto) y como mucho una vez cada `cooldown_minutes`. El fichero de ajustes se fusiona (los demás ganchos se quedan), se guarda una copia (las tres últimas), un fichero que no es JSON válido se rechaza sin tocarlo y todo lo escrito es ASCII puro. El destino por defecto escribe `settings.local.json` (project) o `settings.json` (user) en la carpeta oculta propia de la herramienta; `--cursor` escribe `.cursor/hooks.json` (mejor esfuerzo: su formato de ganchos puede cambiar); `--generic` no escribe nada y muestra los comandos. El script solo necesita Python y toma sus cifras de `ai_alerts.client_hook`.
- **¿Hay una IA conectada?** Con `ai_alerts.heartbeat.enabled` un pequeño fichero local `ai_heartbeat.json` anota la última lectura del flujo, del servidor MCP, del script de enlace o de un endpoint, y la barra inferior muestra «IA: mcp, hace 3 min» (o «ninguna conectada») durante `window_minutes`. No se envía nada a ningún sitio.
- **Ficheros privados.** El flujo, el resumen, el latido y cualquier otro fichero de estado del monitor se crean con modo 0600 (y las carpetas que crea el monitor con 0700). En Windows el programa no puede imponer los modos: las carpetas heredan los permisos de su carpeta madre, así que mantén la carpeta del monitor dentro de tu propio perfil.
