Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE

MONITOR DE GITHUB ACTIONS + CENTINELA (versión 1.6.2)
=====================================================
Requisitos: Python 3.11+ y GitHub CLI (`gh`) con la sesión iniciada (gh auth login). Nada más: el núcleo no necesita paquetes (la vista de consola, tui.py, usa el paquete opcional rich).
Pasos rápidos para el primer uso: QUICKSTART_es.txt.

ARRANQUE   Windows: MONITOR_GITHUB_ACTIONS.bat | Linux: ./MONITOR_GITHUB_ACTIONS.sh | macOS: doble clic en MONITOR_GITHUB_ACTIONS.command
           (abre http://127.0.0.1:<puerto>, solo local). En cualquier sistema también vale:  python3 actions_monitor.py  (Windows: py -3 actions_monitor.py)
LOTES      BATCH_GITHUB_ACTIONS.bat / .sh / .command  (gha_dispatch_all.py: plan, dispatch, status, finalize, hygiene). Opcional, para quien firma sus builds en local.
LO QUE NUNCA HACE   Solo escucha en 127.0.0.1 (nunca lo enlaces a 0.0.0.0: no tiene inicio de sesión). No guarda ningún token (se lo pide a `gh`). Por sí solo no escribe nada en GitHub: solo los comandos de lote `dispatch --go`, `dispatch --real` y `finalize --execute` escriben en GitHub (lanzan workflows, crean el borrador sin firmar, publican), y solo cuando los ejecutas tú.
           NO firma y NO publica nada por sí solo: firmar y publicar son comandos que ejecutas TÚ; el monitor solo los muestra como texto.
           No hay IA en el camino crítico; el explicador opcional con IA viene apagado.

IDIOMA     8 idiomas: en, es, de, fr, it, ja, zh, pt (portugués de Portugal). Arranca en INGLÉS: el idioma del sistema no decide. Elige otro en la pestaña CONFIGURACIÓN de la página
           (icono del engranaje; el navegador lo recuerda), o con "language" en actions_monitor.json, o con la variable de entorno MONITOR_LANG, o con --lang CÓDIGO en las herramientas de línea de comandos (gana a todo).
           Las líneas que leen los scripts (SKIP, DISPATCHED, READY, FAILED, Summary:, BUILD ONLY...) están siempre en inglés.
CONFIG     actions_monitor.json (se crea a partir de actions_monitor.example.json en el primer arranque). Claves útiles: github_owner (vacío = la cuenta de gh),
           language, ecosystems_file, targets_file, refresh_seconds, cold_refresh_seconds, max_workers, min_rate_remaining, sentinel.*
           ecosystems_file: agrupa repositorios por prefijo de nombre (ver ecosystems.example.json; "*" = todos los repos). targets_file: catálogo de builds
           para las herramientas de lote (ver targets.example.json). profiles_file (profiles.example.json): perfiles de lote. Las claves que empiezan por "_" en estos ficheros son metadatos.
WORKSPACE  OPCIONAL: una carpeta con clones locales de tus repositorios (MONITOR_ROOT, "workspace_root" en el json, o una carpeta superior con un fichero .monitor-root).
           Sin él, el monitor arranca en MODO REDUCIDO y lo dice: solo lo que da la API de GitHub (sin cola de firma local, sin parte de auditoría, sin lectura de CHANGELOG).
           Con él, además, hay candidatas a release, cola de firma y las herramientas de lote. Registros de firma: "signed_dir"; ficheros de auditoría: "audit_dir".
PRUEBAS    py -3 -I -m unittest discover -s tests   (Linux/macOS: python3 -I -m unittest discover -s tests). No necesitan red.
PROBLEMAS  "API rate limit": se agotó la cuota compartida de gh (5000/hora); espera al reinicio (gh api rate_limit) y sube refresh_seconds / baja max_workers.
           El monitor se detiene al arrancar si gh no responde. Un fichero de caché corrupto se ignora; borra sentinel_cache.json para empezar la caché de nuevo.
           Reinicia el monitor tras actualizar el paquete (un proceso en marcha sigue con el código antiguo).

HERRAMIENTAS  read_report.py [--lang CÓDIGO] [--json] [--export-status DIR] [--export-sign-queue FICHERO]  imprime lo que dice el monitor en marcha (local, sin cuota de GitHub)
           gha_dispatch_all.py [--lang CÓDIGO] plan|dispatch|status|finalize|hygiene    lote de builds de GitHub Actions (nada se compila en tu PC)
           release_notes.py REPO [--since ETIQUETA] [--out FICHERO]    borrador de notas de release desde los commits (una propuesta; no publica nada)
           release_candidates.py    proyectos con entradas en CHANGELOG [Unreleased] y última release antigua (solo lectura)
EVENTOS    El Centinela escribe una línea JSON por cada CAMBIO (rojo nuevo, CI recuperado, build colgado, alertas nuevas...) en events_monitor.jsonl. Cada línea lleva
           un `code` estable (nunca depende del idioma), `kind`, `level`, `repo`, `args` y `text` (en el idioma configurado). `tail -F` lo sigue.
CI EN ROJO Un solo criterio: el ÚLTIMO run terminado de cada workflow en la rama por defecto. Rojo = failure, timed_out, startup_failure o action_required.
           cancelled, skipped, neutral y stale no cuentan.

NOVEDADES 1.5.1 (historial: CHANGELOG.md)
  - Pestaña AJUSTES: grupo nuevo «IA externa para el centinela» (ai.provider none / ollama / openai-compatible, modelo, dirección de Ollama (solo este equipo), un endpoint https, el NOMBRE de la variable de entorno que guarda la clave, llamadas al día). La clave en sí nunca se guarda. Apagada por defecto; un servicio externo recibe datos de tus repositorios.
  - migrate_state.py: lleva los ficheros escritos antes de la 1.5.0 a los nombres nuevos. `python migrate_state.py` es una simulación; `--apply` copia (los antiguos se quedan), `--move` renombra. Nada se sobrescribe. Una página en docs/MIGRATING.md, en 8 idiomas.
  - Primer arranque sin ficheros de catálogo propios: el monitor avisa de que usa los de ejemplo (consola), y `--init-catalog` crea copias editables de ecosystems.json, targets.json y profiles.json.
  - Python 3.11 o superior (probado en 3.11 y 3.13, en Windows, Linux y macOS).

NOVEDADES 1.5.0 (historial: CHANGELOG.md)
  - Pestaña CONFIGURACIÓN: cambia desde la página los valores de actions_monitor.json (lista de claves permitidas con tipo y rango, validadas, copia en config_backups/ antes de cada guardado, nunca tokens ni secretos; docs/SETTINGS.md).
  - Botones con relieve que se iluminan y se hunden, iconos SVG con nombre y tooltip en 8 idiomas, el aspecto del panel de estado, barras y cifras con vida (todo se detiene con prefers-reduced-motion).
  - Salidas opcionales, apagadas por defecto, solo en 127.0.0.1: /metrics (Prometheus), /api/outputs/grafana.json (Grafana JSON / Infinity), /api/outputs/dashboard.json (docs/OUTPUTS.md, panel de ejemplo en docs/grafana/).
  - Paquete neutro: tus ecosistemas, objetivos y perfiles viven fuera (ecosystems_file, targets_file, profiles_file; tools_dir para las herramientas de firma locales); inglés por defecto; nombres de ficheros y carpetas en inglés.
  AL ACTUALIZAR desde 1.4.x: cambiaron estos nombres (los antiguos se siguen leyendo donde pueda haber un fichero; solo se escriben los nuevos):
  leer_parte.py -> read_report.py          eventos.py -> events.py          parte_history.py -> report_history.py
  LOTE_GITHUB_ACTIONS.bat/.sh/.command -> BATCH_GITHUB_ACTIONS.bat/.sh/.command
  eventos_monitor.jsonl -> events_monitor.jsonl          eventos_estado.json -> events_state.json
  PARTE_CENTINELA_DIA_<day>.* -> SENTINEL_REPORT_DAY_<day>.*     PARTE_CENTINELA_<time>.txt -> SENTINEL_REPORT_<time>.txt     CANDIDATAS_RELEASE.txt -> RELEASE_CANDIDATES.txt
  <signed_dir>/lotes/lote_<time>.json -> <signed_dir>/batches/batch_<time>.json     parte_history_days -> report_history_days     monitor_y_centinela.zip -> github_actions_monitor.zip
  sentinel.audit_files: names of the A8 audit files (neutral defaults RECONCILIATION_TOTAL_*.txt, ROUNDS_MAP_2*.txt, ROUNDS_MAP_EXTRA_*.txt)
  ci_red.json and --export-status: unchanged (a contract).

NOVEDADES 1.4.2 (historial: CHANGELOG.md)
  Cuando A2 pregunta por el último run de un workflow oculto, un run en curso o cancelado ya no cuenta como visto (podría ocultar un rojo anterior): el Centinela pide los
  últimos runs completados de ese workflow y usa el primero con conclusión real (cancelled y skipped se ignoran). Si no hay ninguno en la rama por defecto, solo ese workflow sigue sin concluir.

NOVEDADES 1.4.1 (historial: CHANGELOG.md)
  A2 ya no da un repositorio entero por no concluyente solo porque su muestra de ejecuciones esté llena: por cada workflow del clon que falta en la muestra
  pregunta a GitHub por el último run de ese workflow en la rama por defecto (solo lectura, misma puerta de cuota que A10, limitado por
  sentinel.a2_resolve_max_calls_per_tick, respuestas guardadas sentinel.a2_resolve_ttl_seconds). El rojo cuenta como rojo; un workflow sin ejecuciones en la rama
  sigue sin concluir y el panel lo nombra.

NOVEDADES 1.4.0 (historial: CHANGELOG.md)
  Panel A11 "Preparación": preparación de releases por repositorio (CI de la rama por defecto y su commit, versión por encima de la última release, compilación, firma,
  siguiente paso), salud de los ecosistemas (puntuación solo con recuentos reales, que se retiene si pocos repositorios tienen datos) y versiones fijadas que van por detrás
  de su proveedor (leídas de los ficheros de versiones de los clones locales, configurados en sentinel.readiness.pins.sources). Solo lectura; nada se estima.

NOVEDADES 1.3.0 (historial: CHANGELOG.md)
  8 idiomas en la página, la línea de comandos, los eventos y los partes; selector de idioma; ecosistemas, objetivos y cuenta de GitHub como datos (github_owner,
  ecosystems_file, targets_file); workspace opcional con un modo reducido honesto; autoría y GPL-3.0-or-later en cada fichero; LICENSE, NOTICE, AUTHORS;
  README y QUICKSTART en 8 idiomas.
LICENCIA   GPL-3.0-or-later (ver LICENSE y NOTICE). Copyright (C) 2026 JuanenRac (Electro Hobby 3D).
