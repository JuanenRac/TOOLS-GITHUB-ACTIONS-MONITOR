Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE

MONITOR DE GITHUB ACTIONS + CENTINELA (versión 1.8.1)
=====================================================
¿CUÁL ARRANCAR? (un usuario nuevo decide en dos minutos)
  COMPLETA  MONITOR_GITHUB_ACTIONS.*       la página con el centinela (puerto 8765): alertas, cola de firma, analítica. Empieza aquí si tienes varios repositorios.
  LITE      MONITOR_LITE_GITHUB_ACTIONS.*  la misma página sin centinela (puerto 8766): qué está en rojo, atascado o en marcha. Más ligera; convive con la completa.
  LOTES     BATCH_GITHUB_ACTIONS.*         solo si firmas y publicas tus propios builds.
  TERMINAL  python bin/tui_textual.py (añade --lite para la edición lite)   la aplicación interactiva de terminal; bin/tui.py --once imprime una pantalla.
  REVISAR   python bin/actions_monitor.py --doctor (--json para scripts)   dice qué falta y el comando exacto que lo arregla.
  PROBAR    python bin/actions_monitor.py --demo   la página con datos inventados: sin gh, sin sesión, no toca nada tuyo.

Requisitos: Python 3.11+ y GitHub CLI (`gh`) con la sesión iniciada (gh auth login). Nada más: el núcleo no necesita paquetes (la vista de consola, bin/tui.py, usa el paquete opcional rich).
Pasos rápidos para el primer uso: QUICKSTART_es.txt.

ARRANQUE   Windows: MONITOR_GITHUB_ACTIONS.bat | Linux: ./MONITOR_GITHUB_ACTIONS.sh | macOS: doble clic en MONITOR_GITHUB_ACTIONS.command
           (abre http://127.0.0.1:<puerto>, solo local). En cualquier sistema también vale:  python3 bin/actions_monitor.py  (Windows: py -3 bin/actions_monitor.py)
LOTES      BATCH_GITHUB_ACTIONS.bat / .sh / .command  (bin/gha_dispatch_all.py: plan, dispatch, status, finalize, hygiene). Opcional, para quien firma sus builds en local.
LO QUE NUNCA HACE   Solo escucha en 127.0.0.1 salvo que actives el modo red (Ajustes > Avanzado: una dirección privada, un token de acceso en cada petición y un aviso en la página). No guarda ningún token (se lo pide a `gh`) salvo que actives el token opcional guardado en el almacén seguro del sistema. Por sí solo no escribe nada en GitHub: solo los comandos de lote `dispatch --go`, `dispatch --real` y `finalize --execute` escriben en GitHub (lanzan workflows, crean el borrador sin firmar, publican), y solo cuando los ejecutas tú.
           NO firma y NO publica nada por sí solo: firmar y publicar son comandos que ejecutas TÚ; el monitor solo los muestra como texto.
           No hay IA en el camino crítico; el explicador opcional con IA viene apagado.

IDIOMA     8 idiomas: en, es, de, fr, it, ja, zh, pt (portugués de Portugal). Arranca en INGLÉS: el idioma del sistema no decide. Elige otro en la pestaña CONFIGURACIÓN de la página
           (icono del engranaje; el navegador lo recuerda), o con "language" en actions_monitor.json, o con la variable de entorno MONITOR_LANG, o con --lang CÓDIGO en las herramientas de línea de comandos (gana a todo).
           Las líneas que leen los scripts (SKIP, DISPATCHED, READY, FAILED, Summary:, BUILD ONLY...) están siempre en inglés.
CONFIG     actions_monitor.json (se crea a partir de assets/examples/actions_monitor.example.json en el primer arranque). Claves útiles: github_owner (vacío = la cuenta de gh),
           language, ecosystems_file, targets_file, refresh_seconds, cold_refresh_seconds, max_workers, min_rate_remaining, sentinel.*
           ecosystems_file: agrupa repositorios por prefijo de nombre (ver assets/examples/ecosystems.example.json; "*" = todos los repos). targets_file: catálogo de builds
           para las herramientas de lote (ver assets/examples/targets.example.json). profiles_file (assets/examples/profiles.example.json): perfiles de lote. Las claves que empiezan por "_" en estos ficheros son metadatos.
WORKSPACE  OPCIONAL: una carpeta con clones locales de tus repositorios (MONITOR_ROOT, "workspace_root" en el json, o una carpeta superior con un fichero .monitor-root).
           Sin él, el monitor arranca en MODO REDUCIDO y lo dice: solo lo que da la API de GitHub (sin cola de firma local, sin parte de auditoría, sin lectura de CHANGELOG).
           Con él, además, hay candidatas a release, cola de firma y las herramientas de lote. Registros de firma: "signed_dir"; ficheros de auditoría: "audit_dir".
PRUEBAS    py -3 -I -m unittest discover -s tests   (Linux/macOS: python3 -I -m unittest discover -s tests). No necesitan red.
PROBLEMAS  "API rate limit": se agotó la cuota compartida de gh (5000/hora); espera al reinicio (gh api rate_limit) y sube refresh_seconds / baja max_workers.
           El monitor se detiene al arrancar si gh no responde. Un fichero de caché corrupto se ignora; borra sentinel_cache.json para empezar la caché de nuevo.
           Reinicia el monitor tras actualizar el paquete (un proceso en marcha sigue con el código antiguo).

HERRAMIENTAS  bin/read_report.py [--lang CÓDIGO] [--json] [--export-status DIR] [--export-sign-queue FICHERO]  imprime lo que dice el monitor en marcha (local, sin cuota de GitHub)
           bin/gha_dispatch_all.py [--lang CÓDIGO] plan|dispatch|status|finalize|hygiene    lote de builds de GitHub Actions (nada se compila en tu PC)
           bin/release_notes.py REPO [--since ETIQUETA] [--out FICHERO]    borrador de notas de release desde los commits (una propuesta; no publica nada)
           bin/release_candidates.py    proyectos con entradas en CHANGELOG [Unreleased] y última release antigua (solo lectura)
EVENTOS    El Centinela escribe una línea JSON por cada CAMBIO (rojo nuevo, CI recuperado, build colgado, alertas nuevas...) en events_monitor.jsonl. Cada línea lleva
           un `code` estable (nunca depende del idioma), `kind`, `level`, `repo`, `args` y `text` (en el idioma configurado). `tail -F` lo sigue.
CI EN ROJO Un solo criterio: el ÚLTIMO run terminado de cada workflow en la rama por defecto. Rojo = failure, timed_out, startup_failure o action_required.
           cancelled, skipped, neutral y stale no cuentan.

HISTORIAL DE CAMBIOS
  Todas las versiones, de la más nueva a la más antigua, están en CHANGELOG.md (en ocho idiomas en docs/CHANGELOG_*.md, y en la página: Ayuda > Registro de cambios).

AYUDA, ACERCA DE Y COMPROBACIONES (1.6.4)
-----------------------------------------
La página tiene un botón de Ayuda (? redondo) y uno de Acerca de (i); en la consola usa --help-topics, --help-search, --about y --doctor; --demo muestra la página con datos inventados. La edición lite arranca con su propio banner y título de ventana (LITE, puerto 8766, sin centinela); la completa dice COMPLETE, puerto 8765, centinela activo. El aviso de versión nueva se puede apagar (Ajustes > Básico).
