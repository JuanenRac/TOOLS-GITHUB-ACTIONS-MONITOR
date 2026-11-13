<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Funciones avanzadas (todas apagadas por defecto)

Todo lo de esta página está **apagado hasta que lo actives** en *Ajustes > Avanzado* (o en `actions_monitor.json`), y las claves que deciden quién puede llegar al monitor o qué puede hacer en GitHub están marcadas como opciones de seguridad. Activa solo lo que necesites.

## Escuchar en la red

Por defecto la página responde solo en `127.0.0.1`. Con `listen.network` activado (requiere reinicio) también escucha en `listen.host`: una dirección privada de este equipo, o `0.0.0.0` para todas las interfaces. Una dirección pública se rechaza.

- **Cada petición necesita el token de acceso** (cookie, cabecera `X-Monitor-Access` o `Authorization: Bearer`). El token es el valor de la variable de entorno indicada en `listen.token_env` (16 caracteres o más); sin ella se crea un token aleatorio en cada arranque y se muestra una vez en la consola. Abre una vez la dirección que se imprime allí: guarda la cookie y pasa a la dirección limpia.
- El token de un solo uso de la página queda forzado, la página muestra una barra roja en todas las pestañas mientras el modo esté activo, y las claves de `listen.*`, `github_token.*`, `act.*` y `github_actions.*` solo se pueden cambiar desde el propio equipo.
- `listen.allowed_hosts` lista los nombres con los que se puede abrir la página (protección contra DNS rebinding).
- **Riesgos.** El tráfico es HTTP sin cifrar: quien pueda leer tu red puede leer el token y los datos. Úsalo solo en una red de confianza, o pon delante un proxy inverso con HTTPS (véase `DEPLOYMENT.md`). No lo expongas nunca a Internet. La edición lite nunca escucha más allá de este equipo.
- **HTTPS.** Con tu propio certificado y clave (`listen.tls_cert_file`, `listen.tls_key_file`) el monitor sirve HTTPS por sí mismo; detrás de un proxy que lo hace por ti, activa `listen.secure_cookie`. En ambos casos el navegador envía `Origin: https://host:puerto` con cada cambio, y la guarda acepta exactamente el esquema de la sesión (el otro esquema, otro host, otro puerto o un origen mal formado se rechazan). La dirección que usa el navegador debe llevar el puerto del monitor, salvo detrás de un proxy HTTPS en el puerto 443 por defecto que reenvía `Host` y `Origin` sin puerto: pon su nombre público en `listen.proxy_public_host` (solo un nombre de host, vacío por defecto). Solo cuenta con HTTPS, solo se acepta ese nombre sin puerto y solo se cambia desde el propio equipo.
- **Abrir la sesión por POST.** En lugar de la dirección con `?access=` puedes enviar `POST /api/access` con el JSON `{"token": "..."}`: el token no pasa por la barra de direcciones, el historial ni los registros, y la cookie vuelve en la respuesta. La dirección con `?access=` es obsoleta: sigue funcionando por defecto (nada de lo ya configurado se rompe) y solo en un `GET`, pero el token queda en el historial, los registros y el `Referer`, y el monitor la responde con una cabecera `Deprecation`. Desactiva `listen.query_access` para rechazarla y abrir la sesión solo con `POST /api/access` o la cabecera `X-Monitor-Access`. Una barra roja arriba de Ajustes avisa cuando `listen.host` es `0.0.0.0`. Todo ajuste que el esquema marca como seguro (no solo `listen.*`, `github_token.*`, `act.*` y `github_actions.*`: también el webhook, las acciones de la IA, las notificaciones, OpenTelemetry, el espejo, los runners y las salidas) solo se cambia desde el propio equipo.
- **Primeros pasos al escuchar en la red.** Desactiva primero `listen.query_access` (así el token nunca viaja en una dirección, un historial o un log; abre la sesión con `POST /api/access` o con la cabecera) y pon por delante HTTPS (un certificado en `listen.tls_cert_file` o un proxy HTTPS) o una VPN. La consola lo repite al arrancar el modo red mientras la dirección antigua siga aceptándose.

## Un token de GitHub guardado por el monitor

Lo predeterminado sigue siendo tu propio inicio de sesión de `gh`. Con `github_token.enabled` activado puedes pegar un token en Ajustes > Avanzado: se guarda en el almacén seguro del sistema (DPAPI de Windows, Llavero de macOS, Secret Service de Linux) y, solo cuando falta, en un fichero con permisos 600 (la página lo dice). Nunca se escribe en `actions_monitor.json`, en un registro, en el panel Acerca de ni en el texto para soporte, y llega a `gh` solo por el entorno del proceso. El botón **Borrar el token** lo elimina de todos los sitios.

## Acciones sobre GitHub

Con `github_actions.enabled` activado, el monitor puede relanzar una ejecución fallida (`rerun_failed`, `rerun_run`, `rerun_job`), cancelar una ejecución (`cancel`), cerrar un issue o un pull request (`close_issue`, `close_pr`) y fusionar uno (`merge_pr`, con `github_actions.merge_method`). Solo se pueden usar los nombres de `github_actions.allowed` (por defecto `rerun_failed` y `cancel`). **Cada acción se confirma por separado**: la página muestra exactamente qué se enviará (método y endpoint) y no envía nada hasta que confirmes ese plan con el token de un solo uso. El token de GitHub necesita el permiso (`workflow` para ejecuciones, `repo` para issues y pull requests; si no, se muestra el rechazo del propio GitHub). Cada intento se escribe en `github_actions_log.jsonl`. El asistente de IA no tiene forma de iniciar ninguna.

## Ejecutar un workflow aquí con act

Con `act.enabled` activado y las entradas `repositorio:fichero.yml:evento` en `act.allowed` (las tres exactas), un botón ejecuta `act` sobre el clon local tras confirmar la línea de comandos exacta. No se entregan secretos reales (ficheros de secretos, variables, entorno y entradas vacíos, y un entorno mínimo sin ningún token), la salida se muestra según llega, una ejecución cada vez, con el límite de tiempo `act.timeout_seconds`, y puedes detenerla.

## Copia local de artefactos

Con `mirror.enabled` activado y una `mirror.folder` en este equipo, los artefactos de las ejecuciones terminadas se copian allí (`mirror.max_per_cycle` por ciclo, `mirror.max_mb` para la carpeta, `mirror.keep_days` de retención), una vez cada uno, con nombres limpios dentro de la carpeta.

## Runners propios

Con `runners.enabled` activado, Ajustes > Avanzado muestra cada runner como libre, ocupado o desconectado. El disco y la carga solo se muestran para los runners listados en `runners.metrics` ({nombre: dirección de un node exporter en este equipo o una dirección privada}).

## OpenTelemetry

Con `otlp.enabled` activado y un `otlp.endpoint` (HTTPS, o HTTP en este equipo), las ejecuciones terminadas salen como trazas y las cifras de la cabecera como métricas (OTLP/HTTP con JSON), cada ejecución una vez. Solo se envían repositorio, workflow, rama, evento, conclusión y duración.

## Organizaciones y costes

- `organizations.discover` lista las organizaciones del login en Ajustes > Básico. Para vigilar una, arranca un segundo monitor con `github_owner` puesto a ella.
- `finops.jobs_per_cycle` mayor que 0 lee las etiquetas de los jobs de esas ejecuciones privadas terminadas por ciclo, para que los minutos usen el multiplicador correcto (Linux, Windows, macOS y los runners grandes de `quotas.json`) en lugar de un sistema supuesto. Con el informe de facturación activado (`quota.billing_api`) se muestran también los dólares de Codespaces y Packages, el almacenamiento en uso y el precio de los minutos por encima de los incluidos.

## Comprobar contra los servicios reales

`python tools/manual_check_live.py` (en el repositorio) lee los permisos de tu token, el informe de facturación, las organizaciones, los runners y las banderas de `gh copilot`, y pide a un monitor en marcha que envíe un mensaje de prueba por tus canales. Nunca pide un secreto.

## Notas de seguridad (léelas antes de activar nada)

- **Modo red**: úsalo solo en una red de confianza. El token de acceso no sustituye al cifrado; en HTTP simple el token y los datos viajan en claro. Pon delante un proxy HTTPS (y activa `listen.secure_cookie`) o dale al monitor tu propio certificado y clave (`listen.tls_cert_file`, `listen.tls_key_file`): entonces sirve HTTPS él mismo (TLS 1.2 o superior) y no arranca si no puede usar los ficheros. Prefiere UNA dirección privada de este equipo a todas las interfaces. Solo se aceptan direcciones IPv4. Tras la primera visita la barra de direcciones se limpia del token y la cookie es HttpOnly, SameSite=Strict (y Secure con HTTPS). Una dirección que envía `listen.max_failed_attempts` tokens erróneos en un minuto queda rechazada cinco minutos. `/metrics` y `dashboard.json` listan tus repositorios: en modo red también exigen el token.
- **Acciones en GitHub**: **apagadas por defecto, una confirmación por acción, lista cerrada** (relanzar un run o job, cancelar, cerrar un issue o pull request, fusionar un pull request si lo incluyes). Borrar ramas o repositorios, secretos y ajustes **no** están. La IA puede proponer una lista menor (`rerun_failed`, `rerun_run`, `close_issue`) y nunca fusiona.
- **act**: apagado por defecto, cada ejecución confirmada, lista cerrada de `repositorio:fichero:evento`, sin secretos reales. El clon debe ser una carpeta real dentro del espacio de trabajo: una carpeta que sea un enlace a otro lugar se rechaza salvo que `act.allow_symlinks` esté activo. El límite de tiempo y Stop terminan todo el árbol de procesos que lanzó la ejecución y eliminan los contenedores `act-` que creó.
- **Tu propio token** se guarda en el almacén del sistema si lo hay; el fichero simple (permisos 600) es el almacén más débil. Va solo a `gh`, nunca a `act` ni a tus comandos. `--doctor` muestra el almacén, nunca el token.
- **Combinaciones que evitar** (`--doctor` las nombra): modo red en todas las interfaces; acciones de la IA que ejecutan con el modo red activo; `act` con el modo red activo; el token en un fichero simple.
- El servidor MCP habla solo por entrada y salida estándar; nunca lo pongas detrás de un puerto de red.

`listen.trusted_proxy` (apagado por defecto): solo si un proxy inverso TUYO en el mismo equipo es la única entrada. Los intentos fallidos se cuentan entonces contra la última dirección de `X-Forwarded-For` (la que añade tu proxy) y no contra el proxy; una petición que llega por un proxy sigue sin tratarse nunca como este equipo. Si alguien más puede llegar al monitor directamente, déjalo apagado.
