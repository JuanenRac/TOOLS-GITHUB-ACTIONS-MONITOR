<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Registro de cambios

Versión de la propia herramienta (monitor + centinela + herramientas por lotes), con su propio semver. La fuente es el CHANGELOG.md en inglés; este fichero lleva las mismas versiones y secciones.

## [1.6.8]

El proxy HTTPS de la 1.6.7 se comprueba ahora contra un proxy real, las imágenes se han vuelto a tomar y el historial de cambios está traducido hasta la 1.6.3.

### Añadido

- `python tools/manual_check_live.py proxy HOST [PUERTO] [CONECTAR]`: comprueba, a través de tu proxy HTTPS real en el puerto 443, que la página entra (la sesión se abre con el token de acceso en el cuerpo y la cookie vuelve `Secure` y `HttpOnly`) y que tres peticiones siguen rechazadas (el otro esquema, otro nombre de host, el nombre con puerto). Lee el token de acceso de `MONITOR_ACCESS_TOKEN`, nunca lo imprime y, sin argumentos, dice qué poner en nginx o Caddy.
- `tools/demo_monitor.py --network` muestra la página como se ve en el modo red (la barra roja persistente y, en Ajustes, el aviso de todas las interfaces y el nombre nuevo del proxy) para poder fotografiarla; la demo sigue escuchando solo en `127.0.0.1`. `tools/make_screenshots.py` toma con él dos imágenes nuevas: `web_network_now` y `web_network_settings`.
- Pruebas que recorren toda la cadena: un cliente sobre TLS real, un proxy inverso que termina el TLS y reenvía `Host` y `Origin` sin puerto, y el monitor real detrás. Comprueban que un cambio hecho desde la página llega a los ajustes, que la misma petición se rechaza sin `listen.proxy_public_host`, que un esquema, un nombre o un puerto equivocados siguen rechazados, que la sesión se abre y la cookie es `Secure`, y que la comprobación a mano coincide con el proxy y nunca imprime el token (la batería pasó de 858 a 866).

### Cambiado

- El historial de cambios (Ayuda > Registro de cambios) está traducido a los otros siete idiomas de la 1.6.8 a la 1.6.3 (la 1.6.7 y la 1.6.5 ya lo estaban); las entradas anteriores a la 1.6.3 conservan el texto en inglés bajo un aviso traducido.
- Las imágenes del README se han vuelto a tomar, 76 en total, y el README en ocho idiomas muestra la subpestaña Avanzado de Ajustes y las dos imágenes del modo red.
- `docs/MIGRATING.md` tiene un bloque de la 1.6.7 a la 1.6.8, y la hoja de ruta en ocho idiomas recoge lo que queda: las entradas antiguas del historial y las comprobaciones que necesitan tus propios servicios.

### Corregido

- El historial de la 1.6.7 decía que solo estaban traducidas la 1.6.7 y la 1.6.5 y que el proxy solo se había comprobado con la guarda; esta versión traduce el resto hasta la 1.6.3 y comprueba el proxy de extremo a extremo, como se explica arriba.

## [1.6.7]

Un proxy HTTPS en el puerto 443 por defecto ya funciona con el modo red, y una parte más del historial de cambios está traducida.

### Añadido

- `listen.proxy_public_host` (Ajustes > Avanzado > Red, vacío por defecto): el nombre de host público de un proxy HTTPS en el puerto 443 por defecto que reenvía `Host` y `Origin` sin puerto. Hasta ahora la guarda comparaba ambos con el puerto del monitor, así que ese proxy se rechazaba; ahora ese único nombre se acepta tal cual. Solo cuenta mientras el modo red está activo y la sesión es HTTPS (TLS directo o `listen.secure_cookie`), debe ser un nombre de host simple (un puerto, una ruta, un usuario, un espacio o un literal IPv6 lo dejan vacío), como todo ajuste que el esquema marca como `secure` solo se cambia desde el propio equipo, y su etiqueta y su ayuda están en ocho idiomas.
- Pruebas para cada cambio de esta versión (la batería pasó de 843 a 858 y el fichero nuevo comprueba la guarda, el valor, el esquema y los textos).

### Seguridad

- La excepción de la guarda es lo más estrecha posible: solo ese nombre se acepta sin puerto, nunca otro host sin puerto, nunca con HTTP simple, y el `Origin` debe llevar el mismo nombre con el esquema `https` (otro esquema, un puerto, una ruta, un usuario o un host distinto se siguen rechazando). El nombre del proxy no aparece nunca en el estado público de la guarda.

### Cambiado

- El historial de cambios (Ayuda > Registro de cambios) está traducido a los otros siete idiomas para la 1.6.7 y la 1.6.5 (la 1.6.6 ya lo estaba); las entradas más antiguas conservan el texto en inglés bajo un aviso traducido y seguirán, de la más nueva a la más vieja.
- `docs/ADVANCED.md` (ocho idiomas) explica el proxy en el puerto por defecto en lugar de decir que no está soportado, `docs/MIGRATING.md` tiene un bloque de la 1.6.6 a la 1.6.7, y la guía de ajustes y el índice de la Ayuda se han regenerado.

## [1.6.6]

Correcciones del modo red y de `act`, los pendientes de la 1.6.5 y el historial de cambios en ocho idiomas.

### Añadido

- Una barra roja persistente arriba de Ajustes cuando el modo red escucha en todas las interfaces (`listen.host` = `0.0.0.0`), en ocho idiomas. Hasta ahora solo lo decía `--doctor`.
- `POST /api/access` con `{"token": "..."}`: abre la sesión del modo red con el token de acceso en el cuerpo, de modo que nunca queda en una barra de direcciones, un historial o un registro. Mismas comprobaciones que cualquier petición (host, origen, bloqueo tras tokens erróneos, comparación en tiempo constante); la cookie vuelve `HttpOnly`, `SameSite=Strict` y, con HTTPS, `Secure`. La dirección con `?access=` de la 1.6.5 sigue funcionando.
- Un contador de los fallos que el monitor traga a propósito (`degraded.py`): una línea estructurada en la consola por cada uno, una cuenta por origen en `degraded.json` junto al monitor, la nueva comprobación `degraded` de `--doctor` y una línea "Fallos tragados" en el panel Acerca de. El comportamiento no cambia: siguen sin parar nunca el monitor.
- El historial de cambios (Ayuda > Registro de cambios) tiene ahora un fichero de traducción por idioma, `docs/CHANGELOG_<idioma>.md`, con las mismas versiones y secciones que la fuente en inglés; `tools/make_help_index.py --check` y una prueba fallan si falta una versión en una traducción. Las entradas aún sin traducir lo dicen, en el idioma del lector.
- Pruebas para cada cambio de esta versión (la batería pasó de 811 a 843).

### Corregido

- **El modo red con HTTPS era inutilizable desde la página.** La guarda de mismo origen solo aceptaba un origen `http://`, así que con TLS directo o un proxy HTTPS (`listen.secure_cookie`) el `Origin: https://...` del propio navegador se rechazaba y todo cambio (ajustes, confirmaciones) respondía 403. Ahora la guarda construye el origen permitido con el esquema de la sesión (https o http, nunca ambos), compara host y puerto exactamente y rechaza un origen mal formado. Probado con un servidor TLS real y un certificado que genera la prueba.
- `act`: Stop libera ahora la ejecución, de modo que el siguiente inicio ya no responde `busy` para siempre si el proceso no termina; un worker que vuelve tarde nunca toca una ejecución más nueva; la tubería de salida y el temporizador se cierran en todos los casos (fin normal, límite de tiempo, Stop, error inesperado) y la suite ya no emite `ResourceWarning`.
- `tools/make_screenshots.py` podía terminar sin decir nada: el navegador corre sin tuberías capturadas y con límite de tiempo, se avisa si falta el navegador o no arranca la demo, `MONITOR_BROWSER` indica un navegador a mano y el código de salida es 1 si no se hizo alguna imagen.

### Seguridad

- En modo red, todo ajuste que el esquema marca como `secure` solo se puede cambiar desde el propio equipo, no solo las cuatro familias de antes (`listen.`, `github_token.`, `act.`, `github_actions.`): también el webhook, las acciones de la IA, las notificaciones, OpenTelemetry, el espejo, los runners, las salidas y el resto. La lista se lee del esquema, así que un ajuste seguro nuevo queda cubierto sin que nadie lo recuerde; una prueba los recorre todos.

### Cambiado

- Se vuelven a tomar las imágenes de Acerca de, Ayuda, Ahora, Básico y Avanzado en el README y las guías.
- `docs/ADVANCED.md` (ocho idiomas): HTTPS con tu certificado o detrás de un proxy, la regla del origen, la sesión abierta por POST y la barra de aviso.

## [1.6.5]

Una versión de integridad y seguridad: sin ninguna función nueva grande. Lo que no se puede demostrar ya no se da por seguro.

### Añadido

- Ajustes nuevos, todos con un valor por defecto conservador: `dispatch.required_ci` (y, en el fichero, `dispatch.required_ci_repos` y `dispatch.required_ci_profiles`), `act.allow_symlinks`, `listen.tls_cert_file`, `listen.tls_key_file`, `listen.secure_cookie`, `listen.max_failed_attempts`, `webhook.replay_seconds`, `webhook.max_per_minute`; la guía de ajustes se regenera.
- `finalize --accept-legacy` para los lotes escritos por una versión anterior, y las comprobaciones `risks` y `backend` de `--doctor` (ocho idiomas).
- Pruebas para cada cambio de esta versión (la batería pasó de 729 a más de 800).

### Seguridad

- **Un commit en verde necesita la CI obligatoria.** `gha_dispatch_all.py` da un commit por verde solo cuando los ficheros de workflow obligatorios tuvieron éxito sobre él (`ci.yml` por defecto; `dispatch.required_ci`, `dispatch.required_ci_repos`, `dispatch.required_ci_profiles`), nada falló, caducó ni espera una aprobación (`action_required` bloquea como un fallo), nada sigue en marcha y la lista de ejecuciones está completa (lee hasta cinco páginas; una lista más larga no es verde).
- **Un `git fetch` fallido detiene el despacho** de ese repositorio, los comandos git tienen un límite de tiempo y los ids de commit se validan; un `origin/main` viejo nunca se toma como prueba.
- **El catálogo no puede salir de su carpeta ni cambiar el despacho.** `tool` debe ser un nombre de fichero simple que esté en la carpeta de herramientas (los enlaces que salen de ella también se rechazan); `extra` solo puede contener entradas de workflow `-f clave=valor` (nunca `dry_run`, `ref`, `-R`, `--ref`); `finalize_flags` solo banderas largas; los argumentos de `gh workflow run` se construyen con las piezas validadas y se comprueban de nuevo al lanzar el lote.
- **Los lotes antiguos no se firman a ciegas.** `finalize` ofrece para firmar solo una ejecución cuyo lote registró que se construyó sobre el commit comprobado. Un lote escrito por una versión anterior queda como `needs_review`; `finalize --accept-legacy` vuelve a leer la ejecución de GitHub, la acepta solo si su commit es el registrado, avisa y pide la palabra LEGACY antes de cada firma.
- **`act` se queda dentro del espacio de trabajo.** El clon se resuelve y debe ser una carpeta real del espacio de trabajo (se rechaza un enlace, un nombre con `..` o un `.github` que apunte a otro sitio; `act.allow_symlinks` permite un enlace a un clon). El límite de tiempo y Stop terminan todo el árbol de procesos que inició la ejecución (un grupo de procesos en Linux y macOS, `taskkill /T` sobre su propio PID en Windows) y eliminan los contenedores `act-` que esa ejecución creó.
- **Modo red**: HTTPS servido directamente con tu propio certificado y clave (`listen.tls_cert_file`, `listen.tls_key_file`; TLS 1.2 o superior; el monitor no arranca en HTTP simple si no se pueden usar) o la cookie `Secure` tras un proxy HTTPS (`listen.secure_cookie`); el token de acceso sale de la barra de direcciones al instante (redirección, sin `Referer`); una dirección que envía demasiados tokens erróneos se rechaza durante cinco minutos (`listen.max_failed_attempts`); la dirección de la página es la que escucha el servidor; solo se aceptan direcciones IPv4, tanto en los ajustes como en la guarda; la consola avisa cuando la conexión es HTTP simple.
- **Webhook**: cada entrega necesita su id `X-GitHub-Delivery` y una repetida se ignora durante `webhook.replay_seconds`; un repositorio puede causar como máximo `webhook.max_per_minute` eventos aceptados por minuto; el propietario de `full_name` debe ser la cuenta vigilada; una dirección se limita a 120 peticiones por minuto en el modo red; un evento aceptado descarta las lecturas condicionales guardadas de ese repositorio y lo marca para el siguiente ciclo; una cabecera de firma con caracteres raros es un rechazo simple.
- **Servidor MCP**: un mensaje con mala forma (parámetros, argumentos, id, método) recibe un error solo para ese mensaje, un fallo inesperado en una herramienta es un error interno que no termina el servidor, y una línea de más de 64 KB se rechaza.
- **El token de GitHub guardado se entrega solo a `gh`.** Ya no se pone en el entorno del monitor, así que `act`, tu comando de notificación y cualquier otro proceso hijo no pueden heredarlo.
- **Un GET nunca escribe.** La copia del parte diario en la carpeta de auditoría es un POST con el token de un solo uso (`/api/sentinel/parte/save`); `?save=1` en el GET ha desaparecido.
- `--doctor` nombra las combinaciones peligrosas (modo red en todas las interfaces, acciones de la IA que ejecutan con el modo red activo, `act` con el modo red activo, el token en un fichero plano) y muestra dónde se guarda el token, nunca el token.

### Corregido

- `max_per_hour` de las notificaciones limita ahora mensajes (una unidad por canal, reservada de una vez bajo un solo bloqueo) y no eventos; un canal que no puede enviar no reserva nada.
- Dos guardados de los ajustes a la vez ya no pierden uno de ellos (un bloqueo en el proceso y un fichero de bloqueo).
- La exportación de la cola de firma dice por qué no escribió (una unidad o ruta de red rechazada, una carpeta en lugar de un fichero, el error del sistema) en vez de un rechazo a secas.
- La espera del límite secundario y el reintento tras un tiempo agotado llevan una variación aleatoria.
- La prueba que descomprime el zip en una carpeta limpia ya no forma parte de la batería ordinaria: `make_release.py` ejecuta la batería una vez con un límite de tiempo, luego la instalación limpia como etapa propia, y muestra stdout y stderr cuando alguna falla.

### Cambiado

- Las guías de notificaciones, webhook, funciones avanzadas, salidas, alertas de IA y migración dicen todo esto en los ocho idiomas; `docs/MIGRATING.md` tiene un bloque de la 1.6.4 a la 1.6.5.

## [1.6.4]

### Añadido

- **Alertas para IA**: el monitor escribe un feed local de solo lectura (`ai_alerts.jsonl`, una línea por evento, y `ALERTS_BRIEF.md`, reescrito en cada ciclo, 2 KB por defecto) con una alerta por workflow en rojo: id estable, gravedad, causa probable distinguida como real o transitoria con reglas editables, acción sugerida y un estado (abierta, reconocida, resuelta sola cuando el workflow vuelve a verde). Todo pasa por un limpiador de tokens, claves, direcciones de correo, direcciones IP y carpetas personales. `GET /api/ai/brief` y `GET /api/ai/alerts`, un servidor MCP opcional de solo lectura (`mcp_server.py`: `get_alerts`, `get_red_repos`, `get_run_failure`, `get_quota` y `ack_alert` con `--allow-ack`), un aviso cuando aparece una alerta REAL nueva, un gancho opcional a una dirección de este equipo (apagado) y un `ai_hint` opcional en `ci_red.json`. Guía nueva `AI_ALERTS.md` en ocho idiomas.
- **Funciones opcionales, todas apagadas por defecto, cada una con su interruptor en Ajustes > Avanzado** y pruebas que demuestran que se niegan sin el interruptor, la confirmación o el token: el modo red (una dirección privada, un token de acceso para cada petición, nombres de host aceptados, una barra roja persistente, claves de exposición que solo se cambian desde el propio equipo); un token de GitHub guardado por el monitor en el almacén seguro del sistema (DPAPI de Windows, Keychain de macOS, Secret Service de Linux, o si no un fichero con permisos 600) y nunca en un ajuste, un registro ni una respuesta, con un botón de borrado; acciones sobre GitHub (volver a ejecutar, cancelar, cerrar, fusionar), cada una confirmada por separado tras mostrar exactamente qué se enviará; ejecutar un workflow aquí con `act` desde una lista cerrada, sin secretos reales; una copia local de artefactos; runners propios (inactivos, ocupados, sin conexión, disco y carga opcionales); exportación OpenTelemetry (trazas y métricas, OTLP/HTTP JSON); las organizaciones del login; FinOps por etiquetas de job (Linux, Windows, macOS y runners grandes), el precio de los minutos por encima de los incluidos, Codespaces, Packages y almacenamiento del informe de facturación. Guía nueva `ADVANCED.md` en ocho idiomas y `tools/manual_check_live.py` para probar a mano los servicios reales.
- `--doctor --json`; el doctor también informa de puertos ocupados, del margen que queda, de si tienes tu propio fichero de objetivos, del token de un solo uso y de la exposición. El README del paquete empieza con la elección del lanzador (completo, lite, por lotes, terminal, doctor, demo).
- La aplicación de terminal edita los ajustes sencillos (no los de seguridad) y tiene una pestaña de IA; un aviso persistente para los ajustes que necesitan reinicio sobrevive a una recarga; la cabecera muestra cuándo el A10 del centinela está en pausa por cuota y cuánto del presupuesto de minutos se ha usado; el servidor también recuerda la bienvenida.
- `redrule.py` ignora las ejecuciones dinámicas de las actualizaciones de dependencias igual que el panel, y los casos compartidos de la regla son ahora un fixture de pruebas.

### Cambiado

- **La Ayuda está completa en ocho idiomas**: los documentos de la hoja de ruta, de contribución, de seguridad y de soporte están traducidos, las etiquetas fijas del historial de cambios están traducidas y sus entradas se marcan como solo en inglés, con un aviso traducido; `tools/make_help_index.py --check` y una prueba fallan cuando a un tema le falta un idioma. Una búsqueda muestra como máximo 30 resultados y un documento enorme ya no retiene el hilo del servidor.
- El mosaico rojo cuenta workflows en ambas ediciones e indica en cuántos repositorios. La edición lite hereda el ritmo de refresco de la completa en su primer arranque.
- Un fallo pasajero (un hipo de TLS, un 5xx) se reintenta con una espera exponencial y solo se muestra como error tras tres ciclos seguidos; se mantiene la última imagen.
- La vista de terminal de la edición lite ya no pide el centinela; la edición lite nunca carga el módulo del centinela (la guarda local pasó a `localguard.py`).
- `--demo` redirige a su carpeta temporal todo fichero que pudiera escribir (registros, cachés, feed de eventos, historial, bienvenida).

### Seguridad

- Con `updates.check` apagado o `airgapped` encendido, el monitor no hace ninguna petición de red para el aviso de actualización (probado).
- Verificado contra la API real de GitHub: los scopes del token se leen bien, la lista de organizaciones y el informe de facturación degradan en silencio (un login sin el scope `user` recibe «no encontrado» y el monitor conserva la estimación).

## [1.6.3]

### Añadido

- **Panel Acerca de** (el botón **i** de la cabecera, en ambas ediciones): versión, edición, autor, licencia, Python y sistema, enlaces (repositorio, releases, historial de cambios, documentación, incidencias), los ficheros que usa (solo lectura), la salud del servidor, los créditos de las bibliotecas y un botón que copia la información para soporte (sin secretos ni tokens, con la carpeta personal mostrada como `~`). `GET /api/about`, y `--about` en la consola.
- **Panel de Ayuda** (el botón **?**, la tecla `?`, y un «?» en la barra de pestañas que abre la página de la pestaña en la que estás): toda la documentación (README, inicio rápido, cada guía, hoja de ruta, historial de cambios, contribución, seguridad) como un índice en el que se puede buscar, en el idioma de la página y en inglés donde un documento no está traducido, servido por el servidor local sin Internet. Se construye a partir de los documentos reales con `tools/make_help_index.py` (`--check` en la CI), así que ningún texto se escribe dos veces; el markdown se muestra de forma segura (todo escapado, sin cargar imágenes, solo enlaces `http(s)` y enlaces a otros documentos). En la consola: `--help-topics [TEMA]` y `--help-search PALABRAS`.
- **Aviso de una versión nueva**: una insignia discreta en la cabecera, una línea en Acerca de, en la consola y en `--doctor` cuando se publica una release más reciente. Una sola petición de solo lectura al día a la página pública de releases, con el mismo cliente que todo lo demás (lectura condicional), nunca descarga ni instala nada, no envía nada sobre ti, ignora las prereleases, compara las versiones como números (1.6.10 es más nueva que 1.6.9), calla sin conexión y se apaga con `updates.check` o en una instalación aislada (`airgapped`).
- **Ajustes > Básico**, la primera pestaña: abrir el navegador al arrancar, el aviso de actualización, el interruptor de instalación aislada, el token de un solo uso, las opciones de descubrimiento, las reglas de ciclo de vida, y el plan y las cuotas. Debajo, lo que el monitor encontró en la cuenta (propietario, repositorios encontrados, vigilados, excluidos), las novedades y los grupos sugeridos.
- **`--doctor`**: Python, `gh`, el login, el margen disponible, la red, el permiso de escritura de la carpeta, un puerto libre, y los opcionales Docker, Rich y Textual; cada fallo viene con el comando exacto que lo arregla, en ocho idiomas.
- **`--demo`**: la página con datos inventados, sin `gh`, sin login y sin red; no se lee ni se escribe nada tuyo.
- **Una bienvenida de tres pasos** la primera vez que se abre la página (qué hace, qué encontró en tu cuenta, adónde ir después).
- **Descubrimiento automático**: eventos para un repositorio nuevo, desaparecido, archivado o desarchivado (consola, Ajustes > Básico y, en la edición completa, las notificaciones); un grupo sugerido cuando tres o más repositorios sin clasificar comparten un prefijo, añadido solo tras tu confirmación y con una copia del fichero; reglas de ciclo de vida para dejar fuera forks, repositorios vacíos y privados; una frecuencia de refresco automática opcional que sigue la actividad real dentro del presupuesto de llamadas.
- **Un token de un solo uso** (`session_guard`, activado por defecto) que la página pide justo antes de guardar un ajuste o confirmar una acción, y una **barra de reinicio** en cada pestaña mientras un ajuste guardado espera un reinicio.
- **Niveles del linter de workflows** (información, aviso, error) como filtros en la página, y `Scripts` en la aplicación de terminal.
- **Cuotas y planes para cualquier tipo de cuenta**: tu plan en Ajustes > Básico; las cifras (minutos incluidos como dinero, tarifas por sistema, concurrencia, límites de un job y de una ejecución, márgenes de la API) viven en `quotas.json`, que puedes editar sin una versión nueva; minutos facturables aparte de los minutos de reloj (los repositorios públicos no cuestan nada, los privados usan el multiplicador de Windows o macOS), una proyección mensual marcada como estimación, un aviso una vez al mes al 75 % y al 90 % de los minutos incluidos a través de las notificaciones, jobs en ejecución y en cola frente al límite del plan, jobs cerca del límite de 6 horas y el tipo de token leído de las propias cabeceras de GitHub (con el consejo de iniciar sesión cuando solo quedan 60 llamadas por hora). El uso real viene solo del informe de facturación opcional y de solo lectura (`quota.billing_api`, apagado por defecto, silencioso ante un 403 o 404). `GET /api/quota`.
- **Modos de trabajo: normal, rápido y turbo** (`modes.py`, guía `MODES`): un selector con un icono de medidor en la cabecera y `--mode` / `--mode-minutes` en la consola, en ambas ediciones. Los preajustes viven en el bloque `modes` de la configuración; antes de empezar, la página muestra las llamadas por hora en el peor caso, lo que suelen ahorrar las lecturas condicionales y cuánto duraría el margen restante; vuelve a normal por sí solo cuando se acaba el tiempo o cuando el margen cae por debajo de `min_rate_remaining`, con un aviso; sin login (60 llamadas por hora) rápido y turbo se rechazan con el motivo; necesita el token de un solo uso, vive en memoria y el banner de la consola lo nombra. `GET` y `POST /api/mode`.
- **Tras un límite de tasa secundario** el monitor espera al menos un minuto y luego duplica la espera hasta cinco minutos en lugar de reintentar enseguida.
- **La aplicación de terminal interactiva** `tui_textual.py` (opcional, `pip install textual`): pestañas Resumen, Repositorios, Builds, Rendimiento, Scripts y Ajustes (los interruptores básicos), un filtro, los niveles del linter, refrescar, abrir en el navegador, Acerca de y Ayuda; `--lite` muestra las pestañas de la edición lite. La vista simple con Rich (`tui.py`, `--once`) se mantiene y también tiene `--about` y `--help-topics`.
- **La edición se distingue de un vistazo**: un banner de arranque (`GitHub Actions Monitor LITE 1.6.3 · puerto 8766 · actions_monitor_lite.json · sin centinela · http://127.0.0.1:8766/`, o COMPLETE · puerto 8765 · centinela activo), el título de la ventana de la consola y del terminal, la etiqueta `[LITE]` / `[COMPLETE]` en las líneas de estado, en `--doctor` y en las vistas de terminal, y el mismo título en los lanzadores.
- Guías nuevas en ocho idiomas: **El centinela y sus comprobaciones A1-A13** (qué es, cómo arranca, los ficheros que escribe, cómo leerlo, la regla exacta, el ajuste y la acción de cada comprobación y las veinticinco comprobaciones de A10; una prueba mantiene la guía y el código de acuerdo), **Cuotas y planes** y **Tus primeros cinco minutos** (`FIRST_STEPS`); la guía de migración tiene un bloque de 1.5.x a 1.6.x y el README tiene un selector entre las dos ediciones.
- Pruebas para todo ello (las versiones semánticas, el aviso sin conexión, apagado y en instalación aislada, el markdown seguro, el índice, el token de un solo uso, el descubrimiento, `--doctor`, las cuotas para repositorios públicos y privados, Windows y macOS, sin token, Enterprise y un 403 del informe de facturación, el banner y los lanzadores).

### Cambiado

- La página de Ajustes empieza con la pestaña **Básico**; la guía `SETTINGS` se genera con ella.
- El monitor lista los repositorios de la cuenta con su tipo (archivado, fork, privado, vacío); un `gh` más antiguo sin esos campos vuelve a la lista simple.

### Seguridad

- Nada nuevo escribe en GitHub. El aviso de actualización, el informe de facturación y el descubrimiento son de solo lectura y se pueden apagar; ninguno envía datos sobre ti. Los paneles Ayuda y Acerca de se sirven desde este equipo y el texto de soporte no lleva ningún secreto.
- Escribir un ajuste, confirmar una acción del asistente de IA y añadir un grupo sugerido necesitan el token de un solo uso de la página.

## [1.6.2]

> Esta versión solo está disponible en inglés por ahora; la traducción llegará en una versión posterior.

### Añadido

- **A catch-all group** `rest` ("Everything else", prefix `*`) at the end of the example catalogue of ecosystems, so a new installation leaves no repository out.
- **An automatic group "Unclassified"** for the repositories that no group claims (setting `show_unclassified`, on by default; an explicit choice of ecosystems is respected).
- **A warning when the filter hides repositories**: a banner (complete and lite) says "your ecosystem filter hides N of the M repositories of the account" and names them.
- **The lite edition starts with what you already set up**: on its first start `actions_monitor_lite.json` copies from `actions_monitor.json` (when it exists) the account, the repositories and ecosystems to watch, the catalogue files, the exclusions, the language and the reading depth, and says so on the console. Without such a file its template watches all the ecosystems.
- **`tui.py --lite`** (or `MONITOR_MODE=lite`) reads the lite edition on port 8766.
- **`redrule.py`**, the single small rule of "red on main", used by the sentinel and by the lite edition (which marks the figure as approximate because it guesses the default branch).
- **`ghamon_etag_invalid_total`**, the count of damaged cache entries, in `/metrics`.
- Tests: header-data parity between the complete and the lite edition, the catch-all group, the hidden-repository count, the lite start, the webhook hot mark, the damaged cache entry, and that importing the monitor or the sentinel never loads Rich.
- Guides `LITE` and `SETTINGS` (eight languages) updated.

### Cambiado

- **Both editions show the same header figures**: runs, failures, successes, compute minutes, running and queued are counted once, by the server, over the same 24 hours with each run counted once; the lite edition reads as deep as the complete one. The lite edition hides the "unsigned" tile.
- **A webhook event marks the repository as hot**, so the next cycle reads it again whatever the event said.
- The GitHub allowance tile is painted from the first moment, while the repositories are still loading.

### Corregido

- A new installation with the example catalogue saw almost no repository; the lite edition detected one repository out of 129 because its template filtered by ecosystem.
- **A damaged cache entry is only a miss**: it is thrown away and the endpoint is read again in full.
- "Red on main" and the compute minutes differed between the two editions.

### Seguridad

- The lite edition never inherits the sentinel, the AI, the webhook, the outputs or the notifications, nor any secret, from the complete one; it writes neither `ci_red.json` nor a signing queue.

## [1.6.1]

> Esta versión solo está disponible en inglés por ahora; la traducción llegará en una versión posterior.

### Añadido

- **The lite edition**, a second and simpler product in the same package: `MONITOR_LITE_GITHUB_ACTIONS.bat` / `.sh` / `.command` or `--lite` / `MONITOR_MODE=lite`. What is running and what failed, failures and successes of 24 hours, red on main, the history and the basic charts; a short Settings page (account, repositories and ecosystems, refresh, language, theme); its own file `actions_monitor_lite.json`, its own state files with the suffix `_lite` and port 8766, so both can run side by side.
- **`act` command in the repository panel**: for each workflow of the repository, `act -W .github/workflows/FILE -j JOB` ready to copy. The monitor never runs it (running it exists only as a confirmed action of the AI assistant).
- **A container example** (`deploy/Dockerfile`) that the CI builds.
- Guide `LITE` in eight languages, a Lite-versus-Complete table in every README and new screenshots of both editions in light and dark.
- The roadmap lists what did not fit: local mirror of artifacts, FinOps of the minutes, self-hosted runner status and an OTLP export, and the notes of the terminal view (why it uses Rich).

### Seguridad

- The lite edition has no sentinel: it is not imported and its endpoints answer 404.

## [1.6.0]

> Esta versión solo está disponible en inglés por ahora; la traducción llegará en una versión posterior.

### Añadido

- **Conditional reads (ETag)**: every read of the run lists sends `If-None-Match`; a `304 Not Modified` answer costs no quota. The header and `ghamon_etag_saved_total` count the reads saved; `cache.etag.*` in the Settings tab.
- **Resilience to network cuts**: when every read of a cycle fails with a connection problem the page keeps the last picture with an offline banner and resumes by itself; `offline` and `online` events (they can be notified) and `ghamon_offline`.
- **Analytics** (section A12 of the Sentinel tab, `/api/analytics`, `/metrics`, the Grafana JSON source): p50 / p95 of the duration of each workflow, of the queue time of its jobs and of each step; workflows that got slower than usual; **flaky** workflows (failed, then passed on the same commit, or needed another attempt), only a label that never changes what counts as red.
- **Incoming webhook in real time**: a signed `workflow_run` event updates the run list of its repository without reading GitHub, `workflow_job` events bring queue and step times; only short validated fields are kept (`/api/live-events`).
- **Workflow linter**: `lint_workflows.py` (actions not pinned by SHA, missing or broad permissions, secrets in clear text, injection, `pull_request_target` with the PR's code), rules switchable with their own severity, a line in the daily report and the section A13. A comment `# monitor-lint: ignore RULE reason` or the setting `lint.ignore` silences a finding.
- **Notifications** (off by default): Telegram, Discord, Slack, Matrix, MQTT and a local HTTP address, a limit per hour, a test button and a documented adapter contract (`monitor/docs/schemas/notification_event.schema.json`).
- **AI assistant**: new providers `anthropic` (Messages API, the model is yours to choose) and `copilot` (`gh copilot` with your own login, text only, no tools); new tasks (daily report, release notes, a question about a repository); settings for the kinds of event, the repositories, the language and the limits, a test button and the use of the day. A closed list of actions (`gh run rerun`, `gh issue close`, `act`), only PROPOSED by default.
- **The figures of the header are tiles** with an icon, a big figure and a small label, coloured by state, with a tooltip, a click that leads to the tab, counting figures and a skeleton that shows the last known values at once; the second line (repositories, hot, mode, reads saved, GitHub allowance with a bar and a live countdown, connection, last update and the loading progress) is made of tiles too.
- **Terminal view**: `tui.py` draws a live grid in the console (read-only, optional, needs the package `rich`; the monitor and its tests need no package).
- **For servers and bigger accounts**: `GET /api/health`, `GH_HOST` for GitHub Enterprise Server (every link of the page follows it), `discover_limit`, minimum permissions per feature, and a guide to run it as a service (systemd, launchd, a scheduled task, a container) and behind a reverse proxy.
- Published JSON schemas of `ci_red.json`, of the public export and of the notification event (`monitor/docs/schemas`), and a public roadmap (`docs/ROADMAP.md`).
- New guides in eight languages: notifications, the AI assistant, analytics, console tools and deployment; the webhook guide covers the real-time events. All screenshots were redone (light and dark, console tools included) with `tools/make_screenshots.py` and invented data.

### Cambiado

- **Settings**: new sub-tabs for reads and cache, notifications, analytics, the linter and the terminal view; the AI and webhook sub-tabs have all their options.

### Corregido

- **The linter no longer cries wolf on placeholders**: a value that looks like a secret is classified (a known token format or a long high-entropy string is serious, a readable filler such as `placeholder` or `changeme` is only information, anything else a warning; references and empty values are no finding) and its value is never printed or stored.
- **A browser that closes or reloads its tab while the page is loading no longer prints a traceback** (`ConnectionAbortedError`, `ConnectionResetError`, `BrokenPipeError`): they are counted in `ghamon_client_disconnects_total`; a real error is still shown.

### Seguridad

- The incoming webhook stays off by default, on `127.0.0.1`, with a mandatory HMAC.
- Notification secrets live only in environment variables; hosts are fixed; notifications never write to GitHub.
- AI actions: running one needs its own switch and a confirmation of the full command each time, only on targets the monitor already watches, with a limit per hour, a local log and a lock after two failures in a row.

## [1.5.2]

> Esta versión solo está disponible en inglés por ahora; la traducción llegará en una versión posterior.

### Añadido

- **The Settings tab is organised in sub-tabs**, ordered from the common to the advanced (This browser, General, Refresh and limits, Sentinel, Surface checks A10, Readiness A11, Folders and files, Outputs, External AI, Incoming webhook). Inside a sub-tab the settings sit in titled blocks whose first field is the main switch (the rest of the block dims while it is off). Every field shows its unit and range, a badge (needs a restart / applies now), a badge for the safety options that start in their conservative state, and one line of help. A search box filters all the sub-tabs, each sub-tab counts its unsaved changes, Save and Discard stay visible, the arrow keys, Home and End move between the tabs and the last sub-tab used is remembered by the browser.
- **Every setting of the configuration file is in the page now**: the A10 checks (a switch per check and its limits), the weights of the ecosystem health score, the sources of the pinned versions, the Actions-minutes ceilings, the required files, the audit file patterns, the hot period of the sentinel, the unknown-sample rule of A2, the candidate prefixes, the list of repositories and the switch of the incoming webhook.
- **Signing queue by trust**: each row says `verified`, `unknown` or `failed`; the Sentinel tab has a Signature filter with the count of each kind; `read_report.py --sign-trust` filters the console list and the export, and the exported rows carry `trust`.
- **Readiness chips in the header**: one coloured chip per ecosystem with its health score.
- **A minimal Grafana board** (`red_by_ecosystem.json`) and a test that checks every metric of both boards against what `/metrics` serves.
- New guide `WEBHOOK` (refresh-only mode) and a commented example of the pin sources, in eight languages.
- `tools/make_settings_doc.py` writes the settings table of the guides from the schema and the texts of the page, and the CI checks it.

### Cambiado

- **The daily report groups the issue-closing suggestions** in one line per repository (the monitor still closes nothing).
- **The contract of the profile dashboard** is documented and checked by a test (`/api/outputs/dashboard.json` is exactly the document of `ci_red.json`; the public export never carries the signing side).

### Seguridad

- The shared secret of the webhook is never shown in the page: it only says whether it is defined.

## [1.5.1]

> Esta versión solo está disponible en inglés por ahora; la traducción llegará en una versión posterior.

### Añadido

- **The settings page can set the external AI of the sentinel** (group "External AI for the sentinel"): `ai.provider` (`none` / `ollama` / `openai-compatible`), `ai.model`, `ai.ollama_url` (only this computer), `ai.base_url` (https only), `ai.api_key_env` and `ai.daily_limit`. Off by default; an outside service receives data of your repositories.
- **`migrate_state.py`**: brings the files written before 1.5.0 to the new names (events, report history, release candidates, batch records, the `report_history_days` setting). A dry run by default; `--apply` copies and keeps the old files, `--move` renames them; nothing that exists is overwritten. One-page guide in `docs/MIGRATING.md`, in eight languages.
- **`--init-catalog`** creates editable `ecosystems.json`, `targets.json` and `profiles.json` from the examples.
- A test makes sure no document sends the reader to a command that was renamed in 1.5.0 (only the tables of old and new names and the migration guides may name them).
- The version in every README.

### Cambiado

- **First start without catalogue files of your own**: the console says the example files are in use.
- Python 3.11 or newer is the documented minimum (tested on 3.11 and 3.13 on Windows, Linux and macOS).

### Seguridad

- Only the NAME of the environment variable that holds the AI key can be set: the key itself is never shown or saved.

## [1.5.0]

> Esta versión solo está disponible en inglés por ahora; la traducción llegará en una versión posterior.

**Update notice (read this first).** Several files and settings have English names now. Nothing is lost: the old names are still READ where a file written by an earlier version may exist, and the new names are the only ones written.

| Before 1.5.0 | From 1.5.0 |
|---|---|
| `leer_parte.py` | `read_report.py` |
| `eventos.py` | `events.py` |
| `parte_history.py` | `report_history.py` |
| `LOTE_GITHUB_ACTIONS.bat` / `.sh` / `.command` | `BATCH_GITHUB_ACTIONS.bat` / `.sh` / `.command` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` (copy or rename them to keep the history of events) |
| `PARTE_CENTINELA_DIA_<day>.txt/.json` (report history) | `SENTINEL_REPORT_DAY_<day>.txt/.json` (the old ones are still read) |
| `PARTE_CENTINELA_<time>.txt` (saved report) | `SENTINEL_REPORT_<time>.txt` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_<time>.json` | `<signed_dir>/batches/batch_<time>.json` (the old records are still read) |
| `parte_history_days` (setting) | `report_history_days` (the old name is still read) |
| `monitor_y_centinela.zip` and folder | `github_actions_monitor.zip` and folder; `LEEME_CORREO.txt` is `README_MAIL.txt` |
| A8 looked for `RECONCILIACION_TOTAL_AUDITORIAS_*.txt`, `MAPA_DE_RONDAS_*` | the names are `sentinel.audit_files` (neutral defaults `RECONCILIATION_TOTAL_*.txt`, `ROUNDS_MAP_2*.txt`, `ROUNDS_MAP_EXTRA_*.txt`); set your own there |
| `ci_red.json`, its schema and the `--export-status` files | unchanged (they are a contract) |

- **English by default.** The language of the system no longer decides: the tools start in English until you choose another one in the Settings tab, with `language` in `actions_monitor.json`, `MONITOR_LANG` or `--lang`.
- **A clean, neutral package.** `ecosystems.json`, `targets.json` and `profiles.json` are no longer part of the package: only the `*.example.json` files travel, and a missing default file falls back to its example. Your own files live anywhere and are named by `ecosystems_file`, `targets_file` and the new `profiles_file`; the folder of your local signing tools is the new `tools_dir`. The tests use their own fixtures (`tests/fixtures`).
- **Settings tab.** A new tab changes the values of `actions_monitor.json` from the page: a whitelist of keys with their type and range, one request refused as a whole when a value is invalid, a copy of the previous file in `config_backups/` before every save (the last ten are kept), an atomic write, only on 127.0.0.1 with the same Host and Origin checks as every other endpoint, JSON only. Tokens, secrets, signature keys and the command of the sentinel are not in the list: they are never shown and never written, and every other key of the file is kept as it was. Each setting says whether it needs a restart. The language selector, the theme and the dense view moved there.
- **Buttons and icons.** Buttons have relief, light up on hover and sink when pressed; the icon buttons are inline SVG with an accessible name and a tooltip in the 8 languages. Colours, type, cards, bars and the ring follow the status dashboard of the profile repository.
- **Life in the charts.** Bars grow in, what is red or running has a discreet pulse, the figures of the header count up, hovering a bar highlights it and gives its text as a tooltip, widths change smoothly; all of it stops with `prefers-reduced-motion`.
- **Outputs for other tools (off by default, 127.0.0.1 only, no new token).** `/metrics` in the Prometheus format (red workflows per ecosystem and repository, red streaks and hours, builds waiting for a signature, A10 paused, allowance left, incomplete snapshot...), `/api/outputs/grafana.json` for the Grafana JSON / Infinity source and `/api/outputs/dashboard.json` (the `ci_red.json` document) for the status dashboard. An importable Grafana dashboard is in `docs/grafana/` and the details in `docs/OUTPUTS.md`.
- **Report:** a line (code `tag_vs_manifest`) when a release tag is ahead of the version of the manifest; the unsigned figure is ordered by the longest wait and says how long it is; the repository panel suggests the `gh issue close` command (never run) for a failure issue whose workflow is green again; the `hil` batch profile is documented in `profiles.example.json`; tests for `finalize` and for `monitor_link`.
- **Docs:** `docs/SETTINGS.md`, `docs/OUTPUTS.md`, README and QUICKSTART in the 8 languages updated, screenshots made with invented repositories.

## [1.4.5]

> Esta versión solo está disponible en inglés por ahora; la traducción llegará en una versión posterior.

- **The report says when the snapshot is incomplete:** a line with the stable code `incomplete` (still loading, no local workspace, errors while reading) right after the headline, so nobody acts on a half-read list of red repositories or signing queue.
- **Signing summary:** one line with how many releases wait to be signed (verified / not checked / failed the check) and how many builds are build-only on purpose, so "not signed on purpose" is not confused with "signature missing" (code `sign_summary`).
- **A10 paused for the quota is said in the report** (code `a10_paused`) with the allowance left and needed, and the three knobs that control it.
- Texts in the 8 languages; tests for the three lines.

## [1.4.4]

> Esta versión solo está disponible en inglés por ahora; la traducción llegará en una versión posterior.

- **Author and licence are always visible:** the web panel has a footer with the author and the licence, `read_report.py --version` and the new `gha_dispatch_all.py --version` print them under the version, and the monitor prints the same line when it starts. The text is in the 8 languages (`ui.about`); the author and the licence come from `tool_version.py`.
- **Bridge to the dashboard written down:** `docs/CI_RED_BRIDGE.md` says what `ci_red.json` contains (schema 2, `complete`), how to export it and what a reader must check; the monitor still never pushes or commits.
- Tests for the author line in the 8 languages, the footer, both `--version` flags and the start-up line.

## [1.4.3]

> Esta versión solo está disponible en inglés por ahora; la traducción llegará en una versión posterior.

- **A workflow that only runs on pull requests no longer makes A2 inconclusive:** `pull_request` and `pull_request_target` join the events whose runs never sit on the default branch (like `workflow_dispatch`, `release` and `workflow_call`), so a workflow such as a contract integration check that only runs on pull requests is not asked for a last run on main. A workflow that also has `push` or `schedule` still counts. Tests for both cases.

## [1.4.2]

> Esta versión solo está disponible en inglés por ahora; la traducción llegará en una versión posterior.

- **A2 no longer counts a run in progress or a cancelled one as seen:** when it resolves a hidden workflow, the Sentinel now asks for the last completed runs of that workflow on the default branch (`gh run list -w <file> --branch <default> --status completed -L 10`, read only) and uses the first one with a real conclusion. A cancelled or skipped run (and anything without a conclusion) is ignored, so it can no longer hide an earlier red; a workflow with no completed run with a conclusion on the branch stays inconclusive on its own. Same quota gate, call limit and cache as before.

## [1.4.1]

> Esta versión solo está disponible en inglés por ahora; la traducción llegará en una versión posterior.

- **A2 resolves a hidden workflow instead of giving up on the whole repository:** when a repository has a full run sample and a workflow of its clone (one that can run on the default branch) is missing from it, the Sentinel asks GitHub for the last run of THAT workflow on the default branch (`gh run list -w <file> --branch <default> -L 1`, read only). A red answer counts as red in A2; a green one removes the workflow from the inconclusive list; a workflow with no run on the branch stays inconclusive on its own and the panel names it (`repo/file.yml (no run on the default branch)`) instead of only the repository. Without quota (same gate as A10: `min_rate_remaining` x `surface.min_rate_factor`, plus the hourly budget) the workflow stays inconclusive and the panel says why. New options `sentinel.a2_resolve_max_calls_per_tick` (4; 0 = never ask) and `sentinel.a2_resolve_ttl_seconds` (3600, how long an answer is kept; it is also saved in the cache file). The snapshot carries `a2.inconclusive_workflows` (labels) and `a2.inconclusive_details`; `a2.inconclusive` is still the list of repositories. 5 new texts in the 8 languages and a reworded `ui.a2_inconclusive`.

## [1.4.0]

> Esta versión solo está disponible en inglés por ahora; la traducción llegará en una versión posterior.

- **New layer A11 "Readiness" (read only, real data only):** a panel of the Sentinel tab, a traffic light in its header and two lines of the report. It is switched with `sentinel.readiness.enabled` and described in `readiness.py`.
  - **Release readiness:** one row per repository with at least `candidate_min_entries` entries in `[Unreleased]` (external ecosystems excluded): CI of the default branch (the single rule of A2) with the commit it ran on, whether the version the clone declares (`*.project.json`, else `pyproject.toml`, else the first CHANGELOG heading) is already above the last release, whether a build exists after that release, whether it is signed (the states of A5), and the next step (`fix the red CI`, `wait for run data`, `bump the version`, `build in Actions`, `sign`, `publish`, `cut and publish`). A green CI over a full run sample that may hide an older workflow says so.
  - **Ecosystem health:** per ecosystem, 100 minus weighted counts of red CI, stuck builds, secrets, serious alerts, other alerts, Dependabot PRs older than `stale_pr_days`, builds waiting for signing and repositories with hygiene problems (`sentinel.readiness.health.weights`); the parts that lower the score are listed. No score is shown (`?`) when fewer than `min_coverage` (0.5) of the repositories of the ecosystem have run data and alerts. The report warns when a score is under `warn_below` (70).
  - **Dependency pins:** repositories that pin an older version than the one of the repository that provides the contract or library. Where the pins live is data (`sentinel.readiness.pins.sources`): a JSON table of pins in the provider (`pin_table`) or lock files in the consumers (`lock_files`, the oldest one found counts). Plain file reads of the local clones, cached `pins.refresh_seconds`; an ecosystem without a configured source is listed as having none, and nothing is guessed. The shipped example has no source.
  - 60 new texts in the 8 languages; `tests/test_readiness.py` (rules, weights, coverage, pins on a temporary tree, the page and the 8 catalogues).
- **`docs/CI_RED_SCHEMA.md`:** says explicitly that the PC publishes neither `ci_red.json` nor `pending_sign` to any repository or dashboard (the signing side is local by decision); a public consumer recomputes the rule from the public runs or uses `read_report.py --export-status`.
- **Quota tuning from the log (`actions_monitor_log.txt`, 3 days, 889 samples):** the shared allowance was under the floor (`min_rate_remaining` 1500) in 11% of the samples since 5 November and under 3000 in 45%; the hourly burn was 3000-5000 calls in most hours and reached the limit in some. In the maintainer's `actions_monitor.json`: `refresh_seconds` 120 -> 180 (the real cycle was a median of 139 s) and `sentinel.surface.min_rate_factor` 2.0 -> 1.5 (the cold calls of A10 are about 260 a day, so they can run above 2250; with 3000 they waited almost half of the time). `max_repos_per_tick` (6) and the daily cold cycle stay: they cost less than 1% of the allowance. The shipped example keeps its neutral defaults.

## [1.3.3]

> Esta versión solo está disponible en inglés por ahora; la traducción llegará en una versión posterior.

- **A2 ignores workflows that never run on the default branch:** when deciding whether a full run sample hides a workflow, the files of the clone whose `on:` has no `push`, `pull_request` or `schedule` for the branch (only `workflow_dispatch`, `release`, tag-only `push` without `branches`, or `workflow_call`) are no longer expected in the sample. `on:` is read with the standard library only (string, list, map, and the YAML `true` key); if it cannot be parsed the workflow counts as before. The workflow scan carries the new field `main_triggered` (`true`/`false`/`null`).

## [1.3.2]

> Esta versión solo está disponible en inglés por ahora; la traducción llegará en una versión posterior.

- **A2 shows `unknown` instead of green when its sample is full and inconclusive:** a repository whose list of runs is as long as the sample asked for (`runs_per_repo` / `cold_runs_per_repo` of the monitor, which the check did not see before) and whose clone has a workflow file with no run in that sample (or that has no clone) is listed as inconclusive, and A2 is `unknown` unless something is red. New option `sentinel.a2_full_sample_unknown` (default `true`; `false` = only informative as before). The page lists the repositories.
- **`profiles.example.json`:** a neutral batch-profiles template that matches `targets.example.json` and `ecosystems.example.json`. A test (and the release gate) validates it against those catalogues, not the maintainer's, and checks that every profile selects at least one target.
- **Clean-install check in `make_release`:** before anything is left in the output folder the zip is extracted into a new, empty temporary directory and, from there with `python -I`, every member must be present, every module must compile, `read_report.py --version` must run and the whole suite must pass; any gap fails the release.
- **Wording:** README and QUICKSTART in the 8 languages now say that the package writes nothing to GitHub on its own and that only `dispatch --go`, `dispatch --real` and `finalize --execute` (which you run) do.
- **A10 quota:** the share of the sentinel's per-tick call budget that A10 may use is now `sentinel.surface.budget_share` (default `0.5`, as before but configurable); the page shows "A10 paused for quota" with the allowance left and the one needed (`min_rate_remaining` x `min_rate_factor`) while the cold calls wait.

## [1.3.1]

> Esta versión solo está disponible en inglés por ahora; la traducción llegará en una versión posterior.

- **A run built on another commit is never offered for signing:** when `dispatch` could only find a recent run of another commit (`sha_matched` false), `finalize` now lists it as not ready with the reason and gives no signing command; an old batch without the field behaves as before. Tests with two concurrent runs of different commits.
- **`/api/data` goes through the same Host/Origin guard as the other routes** of the local server (DNS rebinding).

## [1.3.0]

> Esta versión solo está disponible en inglés por ahora; la traducción llegará en una versión posterior.

Made to be shared: eight languages, authorship and licence in every file, no private data, and nothing tied to one GitHub account.

- **8 languages** (en, es, de, fr, it, ja, zh, pt = European Portuguese) for the page, the command line tools, the launchers, the events, the reports and the error
  messages. `i18n.py` + `locales/<lang>.json` (one flat catalogue per language, standard library only, `t("key", name=value)` with a fallback to English). The language
  is `language` in `actions_monitor.json` (default: the system language, English if unsupported), a selector in the header of the page (remembered by the browser),
  `MONITOR_LANG` / `JUANENRAC_LANG`, or `--lang CODE` in every tool (it wins over the rest). Technical names, commands, paths and the markers that scripts read
  (`SKIP`, `DISPATCHED`, `READY`, `FAILED`, `Summary:`, `BUILD ONLY`, `WOULD DISPATCH`...) are never translated. Events in `events_monitor.jsonl` now carry a stable
  `code` (and `args`) next to the text, so nobody has to parse a language.
- A test checks that the 8 catalogues have exactly the same keys, none empty, the same `{placeholders}`, that every key used by the code and the page exists, and that no
  visible string in the code bypasses `t()`.
- README and QUICKSTART in the 8 languages (`README_<lang>.txt`, `QUICKSTART_<lang>.txt`); `README.txt` is now a short language chooser with the quick start.
- **Authorship and licence**: every source file carries "Copyright (C) 2026 JuanenRac (Electro Hobby 3D)" and "GPL-3.0-or-later - see LICENSE"; JSON data files carry
  `_author` / `_license`; `LICENSE` (GPL-3.0 text), `NOTICE` and `AUTHORS` travel in the zip. `make_release.py` refuses to build when a file lacks them, when private data
  would travel, when the locales differ, or when a launcher loses its executable bit.
- **Shareable**: `github_owner` in the configuration (default: the account of `gh`) replaces the constant that was spread over three modules; the ecosystem prefixes and the
  signing tools are data (`ecosystems.json`, neutral `ecosystems.example.json`; `"*"` = every repository; `"external": true` = only reported) and so are the targets (`targets.json`
  is the maintainer's real catalogue, `targets.example.json` the neutral one; `targets_file` / `ecosystems_file` choose them; keys that start with `_` are metadata).
  The example configuration is neutral. Nothing of this adds a call to the hot cycle.
- **The workspace is optional**: without local clones the monitor starts in a reduced mode (only what the GitHub API gives: no local signing queue, no audit report, no
  CHANGELOG scan) and says so on the page, in the report and at start, instead of stopping. `MONITOR_ROOT` / `MONITOR_AUDIT_DIR` / `MONITOR_SIGNED_DIR` and `signed_dir`
  were added next to the old names. The roadmap layer (A9) is optional too.
- Launchers: menus and messages come from `launcher_msg.py` (your language); comments in English; header on every file.
- Fix: `workspace_root()` no longer ends the monitor when the sentinel starts without a workspace.

## [1.2.0]

> Esta versión solo está disponible en inglés por ahora; la traducción llegará en una versión posterior.

What was missing and what else can be done on GitHub, all of it read only and local.

**Part A - what was missing**
- `ci_red.json` schema 2 is now a documented contract: `docs/CI_RED_SCHEMA.md` (shape, the one rule of "red", what is for the owner only). Nothing is
  published from the PC. Optional, explicit exports (never a commit or a push): `read_report.py --export-status DIR` writes ONLY the red list
  (`ci_status_public.json/.md`); `read_report.py --export-sign-queue FILE` (.json/.csv) writes the global signing queue with the local commands.
- Attestation: the signing queue shows whether the build has an attestation (existence by digest of the signed files, one lookup per entry, no signature
  check; switch `sentinel.surface.checks.attestation`). A missing one is a line in the report.
- More verified formats: HYDRA `hydra-sign` (`FILE.sig` = base64 Ed25519 over the bytes of the file, the pinned release key, read in blocks) is checked
  definitively; URTC `.imgsig` has its strict format checked (152 hex digits + LF; malformed = not valid) and stays "unknown" when well formed (the signed
  message also needs the build header, which the signed folder does not carry); ARMOR APKs are signed inside the APK by apksigner and stay "unknown".
- `HYDRA-UMC-OS` is labelled on purpose in `targets.json` (`"build_only": true` + `reason`): `plan` lists it under BUILD ONLY and it is no longer an orphan.
  The signing tools were not touched (its workflow takes other inputs and a different signature scheme).
- Fix: `ci_red.target_path` refused every Windows path written with backslashes (`C:\...`); only forward slashes were accepted.

**Part B - the A10 layer "Actions & releases surface"** (`surface.py`, new section of the tab, a switch and a threshold per check under `sentinel.surface`)
- Actions: workflows disabled by hand, schedules with no run in N days (only when the sample of runs covers the window), `uses:` not pinned by SHA
  (reusable workflows flagged apart), `permissions: write-all`, `pull_request_target` with a checkout of the PR, stuck concurrency queues, failures on only one
  OS of a matrix, artifact cost and retention, required status checks that are red or missing (GraphQL), `dispatch --profile release|nightly|hil` with a canary
  (the first target alone, the rest only if it is green) and a quota gate (`--min-rate`, fails closed). Profiles live in `profiles.json`.
- Releases: expected assets per kind of target (alert when a release was published incomplete), tag vs manifest vs CHANGELOG, GitHub Packages, forgotten drafts
  and pre-releases, `release_notes.py` (a DRAFT of notes from the commits since the last tag; it publishes nothing).
- Security: critical/high alerts by age with a ranking of repositories, coverage (a stack without CodeQL/Dependabot), secret scanning open vs resolved,
  Dependabot by priority (runtime major first, CI-only last).
- Issues and PRs: suggestion of `gh issue close` for build issues whose CI is green again (an event with the text; nothing is ever closed), overdue milestones,
  old human PRs, PRs that touch workflows or CODEOWNERS, the merge queue (approved with green checks). Stale board cards: PENDING (needs per-item reads and a threshold).
- Manifest vs evidence (maturity), 8-language README parity failures, Actions minutes per ecosystem in the header, the report and A7.
- `finalize --execute` now tells the running monitor (127.0.0.1) to refresh just the signed repositories and rewrite `ci_red.json` at once (`monitor_link.py`).
- Optional signed webhook receiver (`webhook.enabled`, off by default, 127.0.0.1 only, HMAC with a shared secret from the config, never a GitHub token).
- Cost: nothing in the hot cycle. Cold, spread over ticks and inside the hourly budget: 2 REST calls per repository per day, one GraphQL query per 15
  repositories per day, 3 for Packages, plus the jobs of red runs and the attestation lookups of the signing queue, and only while the allowance is above
  twice `min_rate_remaining`. The hot GraphQL pass asks for 3 more fields per node (alert dates, review decision, checks state): no extra call.
- The gate also compares `sentinel.surface` of the example file with the defaults and validates `profiles.json`.

## [1.1.1]

> Esta versión solo está disponible en inglés por ahora; la traducción llegará en una versión posterior.

- **Cross-platform:** the monitor and the batch tools work on Windows, macOS and Linux. Launchers `MONITOR_GITHUB_ACTIONS.sh`/`.command` and `BATCH_GITHUB_ACTIONS.sh`/`.command` (the zip keeps the executable permission and make_release rejects Windows line endings in them).
- New `platform_compat.py`: the command that starts a child tool (`py -3` on Windows, the current interpreter elsewhere), the text of the commands that `finalize` shows (cmd/PowerShell or POSIX quoting), UTF-8 console and a notice with the way to install `gh` on each system.
- New tests of the cross-platform part (Windows and POSIX simulated from any system).

## [1.1.0]

> Esta versión solo está disponible en inglés por ahora; la traducción llegará en una versión posterior.

Signature trust, a stable bridge to the dashboard, orphans and conventions in the batch tools, and a more useful page.

- Signature trust: `sigverify.py` (standard library, read only, no network) checks the signed folder `_firmados/<REPO>/release-<version>/` against the PUBLIC
  key each ecosystem pins (URTC `release_sign.py`, ARMOR helper `PACKAGE_PUBLIC_KEY`, HYDRA updater `RELEASES_PUBLIC_KEY`, or `sentinel.signature_pubkeys`).
  Every state now carries `signature_kind` (none | dev | release) and `signature_verified` (true | false | "unknown"); only a release signature that verifies
  (`trusted`) lowers the pending-signature alert, besides "published". A signature that does not verify keeps the alert and says so in the report.
  `sentinel.require_verified_signature` (default true; false = the 1.0.0 rule). Formats this module cannot check (.sig2, .hdr2, .imgsig, APK, hydra-sign) are
  "unknown", never "false". The build attestation still needs the network and stays with the signing tools.
- `ci_red.json` schema 2: per repository a `pending_sign` list (workflow, hours, state, signature_kind, signature_verified, last_build_at, url) next to the red
  workflows, plus `schema`, `pending_sign_repos` and the threshold; the format is documented in `ci_red.py` and is only ever extended.
- One definition of "last run on main" (`signstate.completed_runs`) shared by the red check, the green-without-release check and the target states.
- `ci_red.target_path` refuses D: paths, WSL/Git Bash forms of D: and drive/UNC paths that the running system cannot use; the tests simulate both systems
  and the whole suite now passes on Linux.
- `gha_dispatch_all.py plan` always ends with the section "Signature orphans" (green CI + known `*-build.yml` + no target); coverage is by repository AND workflow.
- Convention for targets (ecosystem prefix -> default signing tool, workflow in the known list); `targets.json` only holds the overrides and always wins.
  `hygiene --write-candidates` writes the proposed entries to `targets.candidates.json` (never applied by itself, never packaged).
- Page: clickable header counters "red on main" and "unsigned" (filter the repositories; the second one also focuses the signing queue), the signing queue
  with its commands and a copy button, repository panel with build / signed / published, signature kind and verification, and the suggested command;
  a header badge when a minutes budget reaches 80 % (red when exceeded); "yesterday vs today" also compares budget warnings and the lines of the report.

Not done: reading the build attestation / SBOM (network); `HYDRA-UMC-OS` has a build workflow but its signing tool does not support it yet (listed as an orphan).

## [1.0.0]

> Esta versión solo está disponible en inglés por ahora; la traducción llegará en una versión posterior.

First numbered version. What the package does:

- Monitor of GitHub Actions for the four ecosystems (local web page, run cache, stuck builds, build-failed/build-stuck issues).
- Sentinel layer A (read only, no AI needed): A1 stuck builds, A2 red CI (one criterion: last completed run of each workflow on the default
  branch), A3 CodeQL/Dependabot/secret alerts, A4 Dependabot pull requests, A5 releases (candidates, green builds without a release,
  pending signature), A6 hygiene, A7 consumption (minutes and API allowance), A8 audits and rounds, A9 roadmap boards.
- Explicit state of each build target: built_on_gha -> signed_local (none | dev | release) -> published, with `last_build_at`,
  `last_signed_at`, `signature_kind` and the real hours waiting; local batch and signed-folder records lower the pending-signature
  alert without waiting for GitHub.
- Signing queue of the day (`a5.sign_queue`): most urgent first, with the exact finalize command of each target.
- Budget of Actions minutes per ecosystem (`sentinel.minutes_budget`, empty by default): warning at 80 % in the report and as an event.
- Event feed (`events_monitor.jsonl`) and `ci_red.json` (repository -> red workflows + hours pending signature), written atomically.
- Batch tools: `gha_dispatch_all.py plan|dispatch|status|finalize|hygiene` with `--only` or `--ecosystem`, `plan --json`,
  `finalize --json`, one retry of a failed dispatch at the end of the batch, targets as data in `targets.json`.
- `read_report.py`: the report as plain text from the running monitor, without spending API quota.
- `make_release.py`: quality gate (unit tests, clean zip, complete example configuration, version/changelog agreement) and SHA256SUMS.

Not done in this version: verifying release signatures against the public key and the build attestation from the sentinel
(different signature formats per ecosystem; the attestation needs the network; the signing tools verify both before publishing).
