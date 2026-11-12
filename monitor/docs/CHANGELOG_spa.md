<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Registro de cambios

Versión de la propia herramienta (monitor + centinela + herramientas por lotes), con su propio semver. La fuente es el CHANGELOG.md en inglés; este fichero lleva las mismas versiones y secciones.

## [Unreleased]

La conexión entre el monitor y una herramienta de IA: el flujo coincide siempre con la página, cada alerta dice por qué está roja, un flujo en directo y tres herramientas MCP empujan las novedades, un comando instala el script de enlace, la barra muestra si hay una IA conectada y todos los ficheros de estado son privados de su dueño.

### Añadido

- **El resumen y el flujo siguen cada refresco de la pestaña Alertas** (y cada lectura del flujo y cada ciclo): antes iban un ciclo por detrás, así que una IA podía leer 10 alertas mientras la página mostraba 6. `ALERTS_BRIEF.md` lleva ahora `Updated:` en tu zona horaria y una línea para máquinas `updated_epoch:`, y `GET /api/ai/brief?fmt=json` añade `updated`, `updated_local` y `age_seconds`. Un ciclo que aún no ha cargado sus datos nunca resuelve alertas.
- **`ai_alerts.diagnose`** (desactivado por defecto, en la pestaña Ajustes, en los ocho idiomas): cada alerta de una ejecución roja nueva lleva `diagnosis`, el primer paso que falla y unas diez líneas relevantes del log, leídas con llamadas de solo lectura, limpias de secretos y acotadas en tamaño y en ejecuciones por ciclo; un error de infraestructura en el log hace la alerta transitoria.
- **`ai_alerts.cascade`**: las alertas que están rojas porque otro repositorio está rojo (nombrado en el log o en la regla `ai_alerts.cascade.map`) se listan bajo él en el resumen y llevan `origin`.
- **`GET /api/ai/stream`** (`ai_alerts.stream`, desactivado por defecto): eventos del servidor, solo lectura, con el token de acceso en modo red, limitado en oyentes y en tiempo, reanudable con `Last-Event-ID`; la edición lite no lo tiene.
- **Herramientas MCP `alerts_open`, `alert_diagnose` y `alert_ack`** (esta última solo con `--allow-ack`), y un aviso a la IA cuando se conecta, en las `instructions` y con una notificación, que dice cuántas alertas reales hay abiertas.
- **`monitor_cli.py ai-hook install|status|uninstall [--cursor|--generic] [--scope project|user] [--dry-run]`** y el script de enlace `ai_hook.py` (solo biblioteca estándar): añade el resumen a la sesión de IA y, solo con `ai_alerts.client_hook.block_on_stop` (desactivado por defecto), pide a la IA que mire las alertas reales abiertas antes de cerrar un turno. Los ajustes de la herramienta se fusionan, nunca se reemplazan, se guarda una copia del fichero, un fichero que no es JSON válido se rechaza sin tocarlo y todo lo escrito es ASCII puro. Las cifras viven en `ai_alerts.client_hook` (pestaña Ajustes, ocho idiomas).
- **Un latido de IA** (`ai_alerts.heartbeat`): el flujo, el servidor MCP, el script de enlace y los endpoints anotan su última lectura en un pequeño fichero local, y la barra inferior muestra si hay una IA conectada y hace cuánto leyó.
- **`monitor_cli.py --token-file FICHERO`** y un aviso por stderr cuando se usa `--token` (se ve en la lista de procesos) o cuando otros usuarios pueden leer el fichero del token.
- Pruebas para cada cambio, en una carpeta temporal y sin red, incluido el modo de cada fichero de estado con un `umask` laxo.

### Cambiado

- **Todos los ficheros de estado del monitor se crean con modo 0600** (y las carpetas que crea con 0700) mediante un solo ayudante, `private_io.py`: silencios, eventos, el flujo, el resumen, cachés, los ajustes y los ficheros que escribe el instalador del script de enlace. En Windows el programa no puede imponer los modos (las carpetas heredan los permisos de su carpeta madre).
- **Al arrancar el modo red** con `listen.query_access` aún activo se imprimen ahora los primeros pasos (desactivarlo; usar HTTPS o una VPN), y la ayuda de `listen.network` y la guía avanzada dicen lo mismo en los ocho idiomas.

## [1.7.5]

La línea de comandos toma el token de acceso con su propio nombre, el modo red es más seguro por defecto (la dirección del ordenador se oculta a la red, la dirección antigua ?access= se puede desactivar, se rechazan los destinos de notificación de la red local, aviso sobre HTTP plano), las horas para las personas usan tu zona horaria, una alerta se puede silenciar hasta que cambie el elemento, y se corrigen los recuentos y comprobaciones que daban respuestas erróneas.

### Añadido

- **`monitor_cli.py --token TOKEN`**, y el token de acceso de la línea de comandos tiene ahora el nombre que lee el propio monitor: `MONITOR_ACCESS_TOKEN`, luego su alias `MONITOR_TOKEN`, luego `--token` (una opción se ve en la lista de procesos, así que es el último recurso). El mensaje de un cliente rechazado nombra la variable. Probado contra un monitor falso que exige la cabecera.
- **Un aviso por stderr** cuando `monitor_cli.py` apunta a `http` sin cifrar en otro ordenador (el token y las respuestas viajarían sin cifrar); la respuesta y `--json` no se tocan.
- **`listen.query_access`** (activo por defecto, en la pestaña Ajustes, en los ocho idiomas): desactívalo y la dirección obsoleta `?access=` se rechaza, de modo que la sesión se abre solo con `POST /api/access` (el token en el cuerpo) o la cabecera. La dirección que funciona responde con una cabecera `Deprecation` y la consola avisa de que es obsoleta.
- **Un silencio «hasta que cambie el elemento»**: `POST /api/alerts/mute` acepta `until_change` para una alerta; el silencio guarda el `updated_at` que tenía el issue o la pull request y termina enseguida cuando cambia (un comentario nuevo, un push), o al acabar las horas, lo que ocurra primero. Las alertas de Collab llevan ahora `details.updated`.
- **Una comprobación del doctor para un token compartido por varias cuentas** (`credential`): compara solo una huella corta de los tokens con los que las cuentas leerían GitHub (el token guardado por el monitor, o `GH_TOKEN` / `GITHUB_TOKEN` del entorno) y lista las cuentas que comparten uno; el token nunca se muestra.
- Pruebas para cada cambio, incluida una de higiene del webhook: un payload con un secreto, un correo, un mensaje de commit y un token no llega ni a la lista en vivo, ni al feed, ni a una notificación, y la lista en vivo se filtra ahora con una lista de campos permitidos.

- **`notify.allow_private_targets`** (apagado por defecto, en la pestaña de Ajustes, en los ocho idiomas): se rechaza un destino de notificación que sea, o resuelva a, una dirección de bucle local, privada (10.x, 172.16-31.x, 192.168.x, fc00::/7), de enlace local (169.254.x, con la dirección de metadatos de la nube, fe80::/10), compartida (100.64.0.0/10) o reservada. El nombre se resuelve una vez y el socket se abre a la dirección comprobada (un nombre que cambie su respuesta no puede colarse), y cada redirección pasa por la misma regla. Los canales `mqtt` y `http_local` siguen siendo solo locales por definición. Probado con un servidor y un resolutor falsos.
- **Un aviso sobre HTTP plano en el modo red**: la ayuda del interruptor `listen.network` dice ahora, en los ocho idiomas, que sin HTTPS el token y los datos viajan sin cifrar; la consola ya avisa al arrancar en red sin certificado.
- **Horas para las personas en tu propia zona horaria**: la línea `Last read` y los silencios de `monitor_cli.py`, el registro `actions_monitor_log.txt`, los partes del centinela, el resumen para IAs y las notificaciones mostraban UTC (`...Z`) sin decirlo, una o dos horas distinto del reloj de la pared. Ahora se leen como `11:43:07 CET (10:43:07 UTC)`: la zona del ordenador, su nombre y la hora UTC al lado. Se sigue el horario de verano (probado en ambos cambios del año y para Madrid, UTC, Tokio y Nueva York).
- **`display.timezone`** (`local` por defecto, en la pestaña Ajustes y en los ocho idiomas): `utc` o un nombre IANA como `Europe/Madrid` muestra los textos y los relojes de la página en esa zona; la variable de entorno `MONITOR_TIMEZONE` manda sobre el archivo. Sin base de datos de zonas horarias en el sistema (Windows sin `tzdata`) se usa una tabla incorporada de las zonas habituales.
- **Los campos para máquinas conservan UTC y tienen un hermano legible**: `generated_local` en `ci_red.json` y en la exportación local de la cola, `updated_local` en `monitor_cli.py status --json` y en los datos de la página, y una línea `Updated:` en `ALERTS_BRIEF.md`. Los relojes de la página y la barra inferior muestran la zona (`CET`, `JST`...).
- **Un botón «Hasta que cambie» en la pestaña Alertas**: silencia una alerta de un issue o pull request hasta que cambie su `updated_at` (un comentario nuevo, un push), o como máximo las horas habituales; la alerta silenciada indica «silenciada hasta que cambie». Textos en los ocho idiomas y una prueba de regresión.

### Cambiado

- **La API llama a la edición `complete`** (decía `full`) en `/api/about`, `/api/statusbar`, `--doctor --json` y la línea de comandos; `full` queda reservado para lo que el centinela puede ejecutar. La página y la línea de comandos siguen entendiendo ambas palabras.
- **Los silencios se hacen solo desde el ordenador del monitor** (también en el modo red, hasta las ediciones con usuarios): la guía de Collab lo dice en los ocho idiomas y una prueba mantiene la ruta tras esa regla.
- **Los workflows de este repositorio usan acciones fijadas a un commit completo**, con la versión en un comentario, y una prueba lo mantiene.

### Corregido

- **Issues que se podrían cerrar** (comprobación de superficie): una ejecución verde de otro workflow ya no propone cerrar un issue; el issue debe nombrar el workflow (por su nombre o por su archivo, «Firmware build failed» para `firmware-build.yml`) y ese mismo workflow debe tener una ejecución verde posterior en la rama por defecto. Un issue que no nombra ningún workflow no propone nada.
- **Tag frente al manifiesto** (comprobación de superficie): cuando el tag de la última release va por delante del manifiesto leído del clon, se lee una vez el manifiesto de la rama por defecto en GitHub para esa release (el clon puede ir atrasado tras una release) y el aviso desaparece si ya tenía esa versión; los tags que no son versiones (`meshes-1`) se ignoran.
- **Siguiente paso de un candidato a release**: un repositorio cuya release necesita una compilación firmada dice ahora «compilar en Actions y firmar», aparte de «subir la versión», «firmar» y «publicar»; los repositorios de ecosistemas gestionados en otro sitio quedan fuera de los candidatos (probado).
- **Los runs en curso y en cola se cuentan una sola vez**: los mosaicos «en curso» y «en cola», la lista «Ocurriendo ahora», la barra de estado (elemento nuevo «N en curso · M en cola», también en `/api/statusbar` como `runs`) y `monitor_cli status` dan las mismas cifras para los mismos datos, en las dos ediciones. Cuando los filtros de la página (ecosistema, estado, búsqueda, una lista de un mosaico) ocultan runs, los mosaicos muestran «3 de 13» y la lista empieza con «Mostrando 3 de 14 (filtros activos)», de modo que un filtro guardado en el navegador ya no parece una incoherencia. La lista de runs activos también descarta un run leído dos veces. Textos en los ocho idiomas y pruebas para ambas ediciones.

### Seguridad

- **`/api/statusbar` ya no entrega la dirección del ordenador en la red local (`lan_address`) a un cliente de la red** en el modo red; la barra se dibuja sin ella.
- La dirección obsoleta `?access=` solo se atiende en un `GET`.

## [1.7.4]

Una barra al pie de la página para los avisos y los datos del monitor, un botón de pantalla completa, tablas que se ordenan por una o varias columnas con las columnas que elijas, y la línea de comandos como cliente del monitor en marcha.

### Añadido

- **Una barra de estado al pie de la página** (todas las ediciones) en lugar de la línea de autoría. A la izquierda, el aviso más importante (rojo antes que amarillo) con el número de los demás y un botón que abre una ventana con todos, el más reciente primero, con filtro por nivel; sin avisos lo dice. A la derecha, la conexión (una luz: GitHub en línea, sin conexión o cuota baja), la cuota y cuándo se renueva, la última lectura, el modo de trabajo, cuántos centinelas están activos, los repositorios vigilados, la cuenta, la versión y edición, la dirección del monitor y la fecha y hora locales. Sigue el ancho de la ventana: los datos secundarios se pliegan en pantallas estrechas. `GET /api/statusbar` le da los datos que no vienen de GitHub (sin llamada a GitHub, sin secretos).
- **Un botón de pantalla completa** en la esquina superior derecha (la API Fullscreen; una segunda pulsación sale), con su icono y texto en los ocho idiomas.
- **Tablas ordenables**: Repositorios e Historial se ordenan con un clic en la cabecera (ascendente, descendente, sin orden), por varias columnas a la vez con Mayús+clic (cada criterio muestra su número y dirección), con los valores vacíos siempre al final, y el orden se recuerda. Un selector de columnas añade más columnas: número de run, autor, commit corto, intento, espera en cola, fichero y ecosistema en Historial; ecosistema, número de run, autor, commit, intento, espera en cola, runs en 24 h, rama por defecto, visibilidad, último push y pull requests abiertos en Repositorios. El monitor ahora envía el número de run y la espera en cola de cada run y un pequeño bloque de datos por repositorio (sacado de lo que ya leyó; nada nuevo de GitHub).
- **`monitor_cli.py`**, la línea de comandos como cliente del monitor en marcha (`status`, `health` o `check`, `doctor`, `accounts`, `alerts`, `live`): lee `GET /api/...` en este ordenador o en `--url` / `MONITOR_URL`, imprime texto o un documento JSON con `--json`, acepta `--account`, `--sentinel`, `--level`, `--muted`, `--timeout` y `--lang`, y usa códigos de salida estables (0 bien, 1 uso incorrecto, 2 monitor no alcanzable, 3 credencial rechazada, 4 degradado, 5 alertas encontradas con `--fail-on`). `health` distingue un monitor que no responde de un acceso de GitHub que falló y de una cuota agotada. La edición lite responde a `status`, `doctor` y `health`. Nunca escribe en GitHub; el token de acceso del modo red va en `MONITOR_TOKEN`. Las herramientas anteriores siguen funcionando. Guía en ocho idiomas (`CLI.md`).
- Pruebas de cada cambio, incluida la lógica de ordenación ejecutada de verdad con Node donde está instalado, los comandos contra un monitor falso, cada código de salida y una prueba de que cada registro de cambios, en cada idioma, lista sus versiones de la más nueva a la más antigua, con las mismas versiones que la fuente.

### Cambiado

- **Los avisos rojos y amarillos ya no están arriba de la página**: los mismos avisos se muestran en la barra del pie (el más importante) y en su ventana (todos).
- **El README del paquete** (`README_<idioma>.txt`) ya no lleva un historial de versiones: remite al registro de cambios.
- Los dibujos del README, la arquitectura y la estructura se hacen de nuevo para esta versión, con una imagen de las tablas y la barra nuevas.

### Eliminado

- **La línea de autoría al pie de la página**: el autor y la licencia están en Acerca de.

## [1.7.3]

Un segundo centinela para incidencias y pull requests, una pestaña con las alertas de todos los centinelas y silencios que acaban solos. Collab solo lee; nada de esto escribe en GitHub.

### Añadido

- **El centinela Collab** (`sentinel_collab.py`, solo edición completa, apagado por defecto): las incidencias y pull requests abiertos de tus repositorios, con un reloj propio (`sentinels.collab.refresh_seconds`) que nunca altera al centinela de CI. Seis reglas con códigos estables: `collab.issue.stale`, `collab.issue.critical`, `collab.issue.external`, `collab.pr.review_pending`, `collab.pr.draft_old` y `collab.pr.conflict`. Lee con peticiones condicionales (un repositorio sin cambios no gasta cuota), como mucho `max_repos_per_tick` repositorios por ronda, se detiene por debajo de `min_rate_remaining`, guarda su estado en `collab_state.json` (dentro de la carpeta de cada cuenta) y solo anuncia los cambios. Los bots se dejan fuera. Su capa *Incidencias y pull requests* está en la pestaña Centinela y `GET /api/sentinel/collab` la sirve.
- **Dos eventos nuevos**, `collab_new` y `collab_fixed`, para el registro y para todos los canales de notificación (están en la lista de eventos de los canales y en el esquema de eventos).
- **La pestaña Alertas** (edición completa): una lista con las alertas de todos los centinelas, cada una con su origen (CI o Collab) y su nivel, filtro por origen y por nivel, enlace a GitHub y un punto rojo en la pestaña con los errores abiertos. `?view=alerts&sentinel=collab` la abre ya filtrada.
- **Silencios con final** (`alert_center.py`): desde la pestaña Alertas se puede silenciar una alerta, una regla (su código) o un centinela entero durante `alerts.mute_hours` horas (24 por defecto, de 1 a 720). Un silencio caduca solo, se puede restaurar al instante, y un historial corto dice qué se silenció, desde cuándo y hasta cuándo. Es una nota del monitor, guardada por cuenta en `alert_mutes.json`; en GitHub no cambia nada.
- **`ignore_labels`** en las reglas de Collab (`monitor:ignore` por defecto): una incidencia o pull request que una persona etiquetó así en GitHub no genera alerta. El monitor nunca escribe etiquetas.
- **`GET /api/alerts`** (`?sentinel=`, `?level=`, `?muted=show|hide|only`) y **`GET /api/events`** (`?sentinel=`, `?since=`), ambos de solo lectura y por cuenta; `POST /api/alerts/mute` y `/api/alerts/unmute` (solo desde este ordenador, token de un solo uso, como cualquier otro cambio).
- **Una lista de comprobación en la vista En vivo** (secreto de 32 caracteres o más, redirección o túnel a `/api/webhook`, el evento de prueba de GitHub, vigilar la cuota) y los mismos pasos en la guía del webhook.
- **Una guía del centinela Collab** en los ocho idiomas (`COLLAB.md`), que encuentra la Ayuda.
- Pruebas de cada cambio: las reglas y sus códigos estables, el coste (lecturas condicionales, el tope por ronda, la pausa), que solo lee, los silencios (ámbitos, final, límites, historial, un fichero dañado), la etiqueta de ignorar, los endpoints, que lite no tiene nada de esto, los ficheros de estado de cada cuenta y de la demo, y los textos en los ocho idiomas.

### Cambiado

- La página de ajustes tiene doce ajustes de Collab en un bloque de la pestaña Centinela, y `alerts.mute_hours` junto a ellos.
- Los ficheros `alert_mutes.json`, `collab_state.json`, `ai_alerts_state.json` y `ALERTS_BRIEF.md` nunca se suben a git ni viajan en un paquete.

## [1.7.2]

Una cabecera que se lee en orden y se ajusta a la ventana, los controles rápidos fijos en la esquina superior derecha, Acerca de en el panel lateral y el fin del aviso de versión nueva. Las pruebas dejan de dejar ficheros junto al código, que es lo que había sustituido los ajustes de una persona por la plantilla neutra.

### Cambiado

- **Las cifras de la cabecera, en orden y en rejilla** (todas las ediciones): la primera fila va ahora de lo que está pasando a lo que pide atención (en marcha, en cola, fallos, éxitos, minutos de cómputo, incidencias abiertas, workflows en rojo en main, sin firmar) y la segunda guarda la maquinaria (repositorios, calientes, modo, lecturas ahorradas, cupo, conexión, actualizado). Cada fila es una rejilla de ocho columnas, cuatro o dos según el ancho de su propio bloque, así que las dos filas llenan siempre sus líneas con cualquier ancho de ventana, desde una pantalla de 1080p hacia arriba (un mosaico nunca impone un ancho propio). El mosaico largo del cupo ocupa dos columnas.
- **Los controles rápidos quedan en la esquina superior derecha**: el botón de solo calientes, la lista de velocidad (normal, rápido, turbo) y las etiquetas de salud de los ecosistemas (y los avisos de presupuesto y de pausa) están fijos ahí, en una columna propia, y se ajustan dentro de ella sin mover las cifras. Por debajo de 1100 puntos de ancho la esquina pasa encima de las cifras. La página de todas las cuentas la oculta, como oculta las cifras.
- **Ajustes, Ayuda y Acerca de están solo en el panel lateral**: los botones del engranaje, la interrogación y la información salen de la cabecera. Ajustes ya era una sección del panel; Ayuda de esta pestaña sigue al pie y se añade **Acerca de** a su lado. La guía de los Ajustes lo dice en los ocho idiomas.

### Eliminado

- **El aviso de versión nueva en la cabecera** (la insignia naranja) con su código y su estilo. El panel Acerca de sigue diciendo si hay una versión más nueva, y la consola también; el ajuste `updates.check` y la caché de 24 horas son los mismos.

### Corregido

- **La plantilla neutra podía sustituir los ajustes de una persona.** Tres grupos de pruebas (el aislamiento de lite, el token de un solo uso y la parte lite de las cuentas) arrancaban un monitor cuyo primer arranque escribe `actions_monitor.json` o `update_check.json` junto al código, y nada los quitaba; al copiar la carpeta `monitor/` sobre una instalación, los ajustes de la persona (su catálogo propio de ecosistemas) quedaban sustituidos por la plantilla, y todos los repositorios caían en el grupo «Everything else» (una esquina que decía «Everything else 54»). Cada una de esas pruebas quita ahora lo que creó, y una prueba lo demuestra. El paquete nunca llevó los ajustes ni el catálogo de nadie, y sigue sin llevarlos.

## [1.7.1]

Una página nueva y el mismo centinela detrás de un contrato. La página tiene un panel lateral a la izquierda con el logotipo, las secciones en grupos y dieciséis temas; el centinela de CI es ahora uno de los centinelas de un registro, y eso es lo que permite que lleguen los siguientes. Lo que el monitor muestra y decide no cambia.

### Añadido

- **Un panel lateral** (todas las ediciones): el logotipo de la herramienta (un SVG que se dibuja con los colores del tema y se queda quieto cuando el sistema pide menos movimiento), el selector de cuentas, las secciones en tres grupos que se pliegan (Vigilar, Datos, Sistema) y la ayuda. El panel se contrae a sus iconos y las dos elecciones se recuerdan en el navegador. La barra superior muestra el nombre de la sección y las herramientas. Las flechas, también arriba y abajo, mueven entre secciones. En una pantalla pequeña el panel pasa arriba. `?chrome=0` lo oculta, como ocultaba la barra de pestañas.
- **Dieciséis temas** además de auto, claro y oscuro: los del Studio del sistema de alarma (Armor, Aqua, Midnight, Ember, Forest, Violet, Solar, Ice, Crimson, Mono, High contrast, Metallic, Professional, Videogame, Terminal y Blueprint), que se eligen en una lista en Ajustes > Este navegador o con `?theme=`. Cada uno define la página, el panel lateral, los paneles, las líneas, el texto, el acento, las esquinas y las letras. El verde, el rojo, el ámbar y el azul conservan su significado en todos, aclarados u oscurecidos donde un tema lo necesita para que cada cifra se lea a 4,5:1 o más, y el texto de una insignia sigue a su color.
- **`BaseSentinel`, `Alert` y `SentinelRegistry`** (`sentinel_base.py`, `sentinel_registry.py`; solo la edición completa): el contrato de un centinela (`start`, `stop`, `tick`, `get_status`, `get_alerts`, `get_metrics`, `get_config_schema`, `refresh_seconds`), una alerta con un código estable que nunca depende del idioma (`ci.red`, `ci.stuck`, `ci.pending_sign`) y la cuenta a la que pertenece, y un registro que da a cada centinela un reloj propio. `sentinels.<nombre>.enabled` en `actions_monitor.json` enciende o apaga uno; sin él decide `sentinel.enabled`, como siempre, y donde los dos dicen algo gana el bloque nuevo.
- **`SentinelCI`** (`sentinel_ci.py`): el centinela de siempre detrás de ese contrato. Contiene el `Sentinel` antiguo y no cambia cómo decide: la misma regla de rojo (la última ejecución terminada de cada workflow en la rama por defecto), los mismos ficheros, el mismo bucle, la misma instantánea.
- Pruebas para cada cambio de esta versión: el contrato, el registro y sus interruptores, el centinela de CI y sus alertas en dos idiomas, que la edición lite no carga nada de esto, el panel lateral y los dieciséis temas (que cada uno define todas las variables y que el texto, el texto gris pequeño, el acento y los cuatro colores de estado se leen a 4,5:1 sobre su página y sus paneles).

### Cambiado

- El tema se elige en una lista en Ajustes > Este navegador (antes era un botón que recorría auto, claro y oscuro); un tema guardado por una versión anterior se sigue entendiendo.
- El color de una insignia, una barra y un aviso que era blanco sobre rojo, ámbar o verde es ahora el que se lee sobre ese color en el tema en uso.
- El centinela se arranca por el registro; `SENTINEL["obj"]` sigue siendo el centinela de CI, así que todo lo que le preguntaba algo sigue funcionando. Los eventos, los ficheros y los endpoints son los mismos.

### Corregido

- Una prueba de la 1.7.0 leía la salida de `tasklist` con la página de códigos equivocada y podía fallar en un Windows con otro idioma.
- **Una negativa podía perderse por el camino** (todas las ediciones): un POST que el monitor rechazaba antes de leer su cuerpo (falta de token, cuerpo demasiado grande) cerraba la conexión con datos sin leer, y Windows, a veces Linux, respondía con un reinicio: el cliente veía una conexión rota en vez del 403 que se le debía. Ahora el monitor lee y descarta lo que queda del cuerpo (hasta 1 MB, durante 2 segundos como máximo) después de contestar, así que la respuesta siempre llega. La negativa, su código y su texto son los mismos. Una prueba envía las cabeceras, espera y envía el cuerpo, y falla sin esto.

## [1.7.0]

Varias cuentas en la edición completa, cada una un monitor propio, y una página que las conoce. La edición lite no cambia: una cuenta, y ni siquiera muestra las opciones nuevas.

### Añadido

- **Varias cuentas** (solo la edición completa). Una carpeta `accounts/<id>/` por cuenta (una persona o una organización) con su propio `actions_monitor.json`, su propia caché, eventos, analítica, estado del centinela y registros; `accounts/global.json` es opcional (`default_account`, `enabled_accounts`) y `MONITOR_ACCOUNTS_DIR` mueve la carpeta. El id son letras minúsculas, dígitos, `_` y `-` (hasta 40), así que siempre es un nombre de carpeta seguro. Sin una carpeta `accounts/` nada cambia: una cuenta, con sus ficheros junto al código.
- **Un supervisor** (`accounts_supervisor.py`): con una carpeta `accounts/`, `python actions_monitor.py` arranca un proceso pequeño en el puerto de siempre que ejecuta un monitor por cuenta (`account_child.py`), cada uno en su propio puerto de `127.0.0.1`. Un fallo, una respuesta lenta o un límite de tasa de una cuenta nunca toca a otra; una cuenta caída se arranca de nuevo con una espera creciente (2, 5, 15, 30, 60 y luego 120 segundos) y el resumen dice que está caída mientras tanto. No lee nada de GitHub y no escribe nada; al detenerlo termina todos los procesos que arrancó, también en Windows.
- **La API de las cuentas**: `GET /api/accounts` (el resumen), `GET /api/accounts/<id>/status`, y cualquier otra petición `/api/` va a la cuenta indicada con `?account=<id>` o la cabecera `X-Account-Id` (la cuenta por defecto sin ninguna; una cuenta desconocida es un 404). Las reglas de acceso son las de un monitor suelto, y el token de un solo uso de un cambio se pide a la misma cuenta a la que va el cambio.
- **Un webhook para todas**: `POST /api/webhook` es una sola dirección para la instalación; el supervisor lee solo el propietario de `repository.full_name` y pasa el evento intacto a la cuenta cuyo `github_owner` es ese propietario, que verifica la firma con su propio secreto. Un propietario que nadie vigila se responde y se ignora.
- **`--accounts`, `--account <id>` y `--migrate-accounts [--apply]`**: listan las cuentas, ejecutan solo una como un monitor normal y mueven el diseño antiguo a `accounts/default/`. La migración es un ensayo salvo con `--apply`, nunca mueve ni borra los originales, se niega a una segunda ejecución y no toca los ficheros de la edición lite.
- **La página con varias cuentas**: un selector de cuentas bajo la cabecera y una entrada **Todas las cuentas** con una tarjeta por cuenta (estado, repositorios, en marcha, en rojo). Cada ventana guarda su propia cuenta y vista, que se leen de la dirección.
- **Vistas por dirección** (`?view=now|alerts|charts|repos|settings|live` y `?chrome=0`, una pantalla sin botones de cabecera, pestañas ni filtros para una pared o un segundo monitor). La vista **En vivo** muestra los últimos eventos que envió GitHub, el estado del receptor de webhook (nunca el secreto) y un selector del modo de trabajo. `GET /api/live-status` es su fuente.
- `tools/demo_accounts.py` para las imágenes, la guía `ACCOUNTS.md` en ocho idiomas y pruebas para cada cambio (la batería pasó de 866 a 914).

### Cambiado

- Los ficheros de estado de un monitor que es una cuenta de varias viven en su carpeta mediante `state_dir()`; un monitor único los mantiene junto al código, como siempre.
- Las imágenes del README se han vuelto a tomar y el README en ocho idiomas muestra las cuentas.

### Seguridad

- El supervisor y las cuentas escuchan solo en `127.0.0.1` salvo que el modo red esté activo. El webhook no tiene comprobación de Host ni token de acceso (un túnel cambia el host) y su prueba sigue siendo el HMAC de GitHub; una cookie de la sesión nunca se pasa a una cuenta.

### Corregido

- La vista En vivo de la 1.6.8 no tenía estado del receptor: con el webhook apagado o con un secreto de menos de 32 caracteres no decía nada, y ahora dice cuál de los dos.

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

### Añadido

- **Un grupo comodín** `rest` («Todo lo demás», prefijo `*`) al final del catálogo de ejemplo de ecosistemas, para que una instalación nueva no deje ningún repositorio fuera.
- **Un grupo automático «Sin clasificar»** para los repositorios que ningún grupo reclama (ajuste `show_unclassified`, activo por defecto; una elección explícita de ecosistemas se respeta).
- **Un aviso cuando el filtro oculta repositorios**: un banner (completa y lite) dice «tu filtro de ecosistemas oculta N de los M repositorios de la cuenta» y los nombra.
- **La edición lite arranca con lo que ya configuraste**: en su primer arranque `actions_monitor_lite.json` copia de `actions_monitor.json` (si existe) la cuenta, los repositorios y ecosistemas a vigilar, los ficheros de catálogo, las exclusiones, el idioma y la profundidad de lectura, y lo dice en la consola. Sin ese fichero, su plantilla vigila todos los ecosistemas.
- **`tui.py --lite`** (o `MONITOR_MODE=lite`) lee la edición lite en el puerto 8766.
- **`redrule.py`**, la regla única y pequeña de «rojo en main», usada por el centinela y por la edición lite (que marca la cifra como aproximada porque adivina la rama por defecto).
- **`ghamon_etag_invalid_total`**, el recuento de entradas de caché dañadas, en `/metrics`.
- Pruebas: paridad de los datos de la cabecera entre la edición completa y la lite, el grupo comodín, el recuento de repositorios ocultos, el arranque lite, la marca caliente del webhook, la entrada de caché dañada, y que importar el monitor o el centinela nunca carga Rich.
- Guías `LITE` y `SETTINGS` (ocho idiomas) actualizadas.

### Cambiado

- **Ambas ediciones muestran las mismas cifras de cabecera**: ejecuciones, fallos, éxitos, minutos de cómputo, en marcha y en cola se cuentan una sola vez, en el servidor, sobre las mismas 24 horas y con cada ejecución contada una vez; la edición lite lee con la misma profundidad que la completa. La edición lite oculta el recuadro «sin firmar».
- **Un evento del webhook marca el repositorio como caliente**, de modo que el siguiente ciclo lo lee otra vez diga lo que diga el evento.
- El recuadro de la cuota de GitHub se pinta desde el primer momento, mientras los repositorios aún cargan.

### Corregido

- Una instalación nueva con el catálogo de ejemplo veía casi ningún repositorio; la edición lite detectaba un repositorio de 129 porque su plantilla filtraba por ecosistema.
- **Una entrada de caché dañada es solo un fallo de caché**: se descarta y el endpoint se lee de nuevo completo.
- «Rojo en main» y los minutos de cómputo diferían entre las dos ediciones.

### Seguridad

- La edición lite nunca hereda de la completa el centinela, la IA, el webhook, las salidas ni las notificaciones, ni ningún secreto; no escribe ni `ci_red.json` ni una cola de firma.

## [1.6.1]

### Añadido

- **La edición lite**, un segundo producto más sencillo en el mismo paquete: `MONITOR_LITE_GITHUB_ACTIONS.bat` / `.sh` / `.command` o `--lite` / `MONITOR_MODE=lite`. Lo que corre y lo que falla, fallos y éxitos de 24 horas, rojo en main, el historial y los gráficos básicos; una página de Ajustes breve (cuenta, repositorios y ecosistemas, actualización, idioma, tema); su propio fichero `actions_monitor_lite.json`, sus propios ficheros de estado con el sufijo `_lite` y el puerto 8766, de modo que ambas pueden correr a la vez.
- **Comando `act` en el panel del repositorio**: para cada workflow del repositorio, `act -W .github/workflows/FICHERO -j JOB` listo para copiar. El monitor nunca lo ejecuta (ejecutarlo existe solo como acción confirmada del asistente de IA).
- **Un ejemplo de contenedor** (`deploy/Dockerfile`) que construye la CI.
- Guía `LITE` en ocho idiomas, una tabla Lite frente a Completa en cada README y capturas nuevas de ambas ediciones en claro y oscuro.
- La hoja de ruta lista lo que no cupo: espejo local de artefactos, FinOps de los minutos, estado de los runners propios y una exportación OTLP, y las notas de la vista de terminal (por qué usa Rich).

### Seguridad

- La edición lite no tiene centinela: no se importa y sus endpoints responden 404.

## [1.6.0]

### Añadido

- **Lecturas condicionales (ETag)**: cada lectura de las listas de ejecuciones envía `If-None-Match`; una respuesta `304 Not Modified` no gasta cuota. La cabecera y `ghamon_etag_saved_total` cuentan las lecturas ahorradas; `cache.etag.*` en la pestaña Ajustes.
- **Resistencia a cortes de red**: cuando todas las lecturas de un ciclo fallan por un problema de conexión, la página conserva la última imagen con un banner de sin conexión y se reanuda sola; eventos `offline` y `online` (se pueden notificar) y `ghamon_offline`.
- **Analítica** (sección A12 de la pestaña Centinela, `/api/analytics`, `/metrics`, la fuente JSON de Grafana): p50 / p95 de la duración de cada workflow, del tiempo en cola de sus jobs y de cada paso; workflows que se han vuelto más lentos de lo habitual; workflows **inestables** (fallaron y luego pasaron con el mismo commit, o necesitaron otro intento), solo una etiqueta que nunca cambia lo que cuenta como rojo.
- **Webhook de entrada en tiempo real**: un evento `workflow_run` firmado actualiza la lista de ejecuciones de su repositorio sin leer GitHub, los eventos `workflow_job` traen tiempos de cola y de pasos; solo se guardan campos cortos validados (`/api/live-events`).
- **Linter de workflows**: `lint_workflows.py` (acciones sin fijar por SHA, permisos ausentes o amplios, secretos en claro, inyección, `pull_request_target` con el código de la PR), reglas activables con su propia gravedad, una línea en el parte diario y la sección A13. Un comentario `# monitor-lint: ignore REGLA motivo` o el ajuste `lint.ignore` silencia un hallazgo.
- **Notificaciones** (apagadas por defecto): Telegram, Discord, Slack, Matrix, MQTT y una dirección HTTP local, un límite por hora, un botón de prueba y un contrato de adaptadores documentado (`monitor/docs/schemas/notification_event.schema.json`).
- **Asistente de IA**: nuevos proveedores `anthropic` (API de Messages, el modelo lo eliges tú) y `copilot` (`gh copilot` con tu propio acceso, solo texto, sin herramientas); tareas nuevas (parte diario, notas de versión, una pregunta sobre un repositorio); ajustes para los tipos de evento, los repositorios, el idioma y los límites, un botón de prueba y el uso del día. Una lista cerrada de acciones (`gh run rerun`, `gh issue close`, `act`), solo PROPUESTAS por defecto.
- **Las cifras de la cabecera son recuadros** con un icono, una cifra grande y una etiqueta pequeña, coloreados según el estado, con tooltip, un clic que lleva a la pestaña, cifras que cuentan y un esqueleto que muestra los últimos valores conocidos al instante; la segunda línea (repositorios, calientes, modo, lecturas ahorradas, cuota de GitHub con una barra y cuenta atrás en vivo, conexión, última actualización y progreso de carga) también está hecha de recuadros.
- **Vista de terminal**: `tui.py` dibuja una cuadrícula en vivo en la consola (solo lectura, opcional, necesita el paquete `rich`; el monitor y sus pruebas no necesitan ningún paquete).
- **Para servidores y cuentas grandes**: `GET /api/health`, `GH_HOST` para GitHub Enterprise Server (todos los enlaces de la página lo siguen), `discover_limit`, permisos mínimos por función y una guía para ejecutarlo como servicio (systemd, launchd, una tarea programada, un contenedor) y tras un proxy inverso.
- Esquemas JSON publicados de `ci_red.json`, de la exportación pública y del evento de notificación (`monitor/docs/schemas`), y una hoja de ruta pública (`docs/ROADMAP.md`).
- Guías nuevas en ocho idiomas: notificaciones, el asistente de IA, analítica, herramientas de consola y despliegue; la guía del webhook cubre los eventos en tiempo real. Todas las capturas se rehicieron (claro y oscuro, herramientas de consola incluidas) con `tools/make_screenshots.py` y datos inventados.

### Cambiado

- **Ajustes**: subpestañas nuevas para lecturas y caché, notificaciones, analítica, el linter y la vista de terminal; las subpestañas de IA y webhook tienen todas sus opciones.

### Corregido

- **El linter ya no da falsas alarmas con los marcadores de posición**: un valor que parece un secreto se clasifica (un formato de token conocido o una cadena larga de alta entropía es grave, un relleno legible como `placeholder` o `changeme` es solo información, cualquier otra cosa un aviso; las referencias y los valores vacíos no son hallazgo) y su valor nunca se imprime ni se guarda.
- **Un navegador que cierra o recarga su pestaña mientras la página carga ya no imprime un traceback** (`ConnectionAbortedError`, `ConnectionResetError`, `BrokenPipeError`): se cuentan en `ghamon_client_disconnects_total`; un error real se sigue mostrando.

### Seguridad

- El webhook de entrada sigue apagado por defecto, en `127.0.0.1`, con HMAC obligatorio.
- Los secretos de las notificaciones viven solo en variables de entorno; los hosts son fijos; las notificaciones nunca escriben en GitHub.
- Acciones de la IA: ejecutar una necesita su propio interruptor y una confirmación del comando completo cada vez, solo sobre destinos que el monitor ya vigila, con un límite por hora, un registro local y un bloqueo tras dos fallos seguidos.

## [1.5.2]

### Añadido

- **La pestaña Ajustes se organiza en subpestañas**, ordenadas de lo común a lo avanzado (Este navegador, General, Actualización y límites, Centinela, Comprobaciones de superficie A10, Preparación A11, Carpetas y ficheros, Salidas, IA externa, Webhook de entrada). Dentro de una subpestaña los ajustes están en bloques con título cuyo primer campo es el interruptor principal (el resto del bloque se atenúa mientras está apagado). Cada campo muestra su unidad y rango, una insignia (necesita reinicio / se aplica ya), una insignia para las opciones de seguridad que arrancan en su estado conservador y una línea de ayuda. Un cuadro de búsqueda filtra todas las subpestañas, cada subpestaña cuenta sus cambios sin guardar, Guardar y Descartar siguen visibles, las flechas, Inicio y Fin se mueven entre las pestañas y el navegador recuerda la última subpestaña usada.
- **Todos los ajustes del fichero de configuración están ya en la página**: las comprobaciones A10 (un interruptor por comprobación y sus límites), los pesos de la puntuación de salud del ecosistema, las fuentes de las versiones fijadas, los topes de minutos de Actions, los ficheros requeridos, los patrones de ficheros de auditoría, el periodo caliente del centinela, la regla de muestra desconocida de A2, los prefijos de candidatos, la lista de repositorios y el interruptor del webhook de entrada.
- **Cola de firma por confianza**: cada fila dice `verified`, `unknown` o `failed`; la pestaña Centinela tiene un filtro de Firma con el recuento de cada tipo; `read_report.py --sign-trust` filtra la lista de la consola y la exportación, y las filas exportadas llevan `trust`.
- **Chips de preparación en la cabecera**: un chip coloreado por ecosistema con su puntuación de salud.
- **Un panel mínimo de Grafana** (`red_by_ecosystem.json`) y una prueba que comprueba cada métrica de ambos paneles contra lo que sirve `/metrics`.
- Guía nueva `WEBHOOK` (modo solo actualizar) y un ejemplo comentado de las fuentes de fijación, en ocho idiomas.
- `tools/make_settings_doc.py` escribe la tabla de ajustes de las guías a partir del esquema y los textos de la página, y la CI la comprueba.

### Cambiado

- **El parte diario agrupa las sugerencias de cierre de incidencias** en una línea por repositorio (el monitor sigue sin cerrar nada).
- **El contrato del panel del perfil** está documentado y comprobado por una prueba (`/api/outputs/dashboard.json` es exactamente el documento de `ci_red.json`; la exportación pública nunca lleva el lado de la firma).

### Seguridad

- El secreto compartido del webhook nunca se muestra en la página: solo dice si está definido.

## [1.5.1]

### Añadido

- **La página de ajustes puede configurar la IA externa del centinela** (grupo «IA externa para el centinela»): `ai.provider` (`none` / `ollama` / `openai-compatible`), `ai.model`, `ai.ollama_url` (solo este ordenador), `ai.base_url` (solo https), `ai.api_key_env` y `ai.daily_limit`. Apagada por defecto; un servicio externo recibe datos de tus repositorios.
- **`migrate_state.py`**: lleva a los nombres nuevos los ficheros escritos antes de la 1.5.0 (eventos, historial de partes, candidatos a versión, registros de lotes, el ajuste `report_history_days`). Por defecto es un ensayo; `--apply` copia y conserva los antiguos, `--move` los renombra; nada de lo que existe se sobrescribe. Guía de una página en `docs/MIGRATING.md`, en ocho idiomas.
- **`--init-catalog`** crea `ecosystems.json`, `targets.json` y `profiles.json` editables a partir de los ejemplos.
- Una prueba asegura que ningún documento manda al lector a un comando que se renombró en la 1.5.0 (solo las tablas de nombres antiguos y nuevos y las guías de migración pueden nombrarlos).
- La versión en cada README.

### Cambiado

- **Primer arranque sin ficheros de catálogo propios**: la consola dice que se usan los ficheros de ejemplo.
- Python 3.11 o posterior es el mínimo documentado (probado en 3.11 y 3.13 en Windows, Linux y macOS).

### Seguridad

- Solo se puede indicar el NOMBRE de la variable de entorno que guarda la clave de la IA: la clave nunca se muestra ni se guarda.

## [1.5.0]

**Aviso de actualización (léelo primero).** Varios ficheros y ajustes tienen ahora nombres en inglés. No se pierde nada: los nombres antiguos se siguen LEYENDO donde pueda existir un fichero escrito por una versión anterior, y los nombres nuevos son los únicos que se escriben.

| Antes de la 1.5.0 | Desde la 1.5.0 |
|---|---|
| `leer_parte.py` | `read_report.py` |
| `eventos.py` | `events.py` |
| `parte_history.py` | `report_history.py` |
| `LOTE_GITHUB_ACTIONS.bat` / `.sh` / `.command` | `BATCH_GITHUB_ACTIONS.bat` / `.sh` / `.command` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` (cópialos o renómbralos para conservar el historial de eventos) |
| `PARTE_CENTINELA_DIA_<day>.txt/.json` (historial de partes) | `SENTINEL_REPORT_DAY_<day>.txt/.json` (los antiguos se siguen leyendo) |
| `PARTE_CENTINELA_<time>.txt` (parte guardado) | `SENTINEL_REPORT_<time>.txt` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_<time>.json` | `<signed_dir>/batches/batch_<time>.json` (los registros antiguos se siguen leyendo) |
| `parte_history_days` (ajuste) | `report_history_days` (el nombre antiguo se sigue leyendo) |
| `monitor_y_centinela.zip` y carpeta | `github_actions_monitor.zip` y carpeta; `LEEME_CORREO.txt` pasa a ser `README_MAIL.txt` |
| A8 buscaba `RECONCILIACION_TOTAL_AUDITORIAS_*.txt`, `MAPA_DE_RONDAS_*` | los nombres son `sentinel.audit_files` (valores neutros por defecto `RECONCILIATION_TOTAL_*.txt`, `ROUNDS_MAP_2*.txt`, `ROUNDS_MAP_EXTRA_*.txt`); pon ahí los tuyos |
| `ci_red.json`, su esquema y los ficheros de `--export-status` | sin cambios (son un contrato) |

- **Inglés por defecto.** El idioma del sistema ya no decide: las herramientas arrancan en inglés hasta que eliges otro en la pestaña Ajustes, con `language` en `actions_monitor.json`, `MONITOR_LANG` o `--lang`.
- **Un paquete limpio y neutro.** `ecosystems.json`, `targets.json` y `profiles.json` ya no forman parte del paquete: solo viajan los ficheros `*.example.json`, y un fichero por defecto ausente recurre a su ejemplo. Tus propios ficheros viven donde quieras y se nombran con `ecosystems_file`, `targets_file` y el nuevo `profiles_file`; la carpeta de tus herramientas de firma locales es el nuevo `tools_dir`. Las pruebas usan sus propios datos de prueba (`tests/fixtures`).
- **Pestaña Ajustes.** Una pestaña nueva cambia los valores de `actions_monitor.json` desde la página: una lista blanca de claves con su tipo y rango, una petición rechazada entera cuando un valor no es válido, una copia del fichero anterior en `config_backups/` antes de cada guardado (se conservan las diez últimas), una escritura atómica, solo en 127.0.0.1 con las mismas comprobaciones de Host y Origin que cualquier otro endpoint, solo JSON. Los tokens, secretos, claves de firma y el comando del centinela no están en la lista: nunca se muestran ni se escriben, y las demás claves del fichero se conservan tal como estaban. Cada ajuste dice si necesita reinicio. El selector de idioma, el tema y la vista densa se movieron allí.
- **Botones e iconos.** Los botones tienen relieve, se iluminan al pasar el ratón y se hunden al pulsarlos; los botones de icono son SVG en línea con nombre accesible y tooltip en los 8 idiomas. Los colores, la tipografía, las tarjetas, las barras y el anillo siguen el panel de estado del repositorio del perfil.
- **Vida en los gráficos.** Las barras crecen al aparecer, lo que está en rojo o en marcha tiene un pulso discreto, las cifras de la cabecera cuentan hacia arriba, pasar sobre una barra la resalta y da su texto como tooltip, los anchos cambian suavemente; todo se detiene con `prefers-reduced-motion`.
- **Salidas para otras herramientas (apagadas por defecto, solo 127.0.0.1, sin token nuevo).** `/metrics` en formato Prometheus (workflows en rojo por ecosistema y repositorio, rachas y horas en rojo, compilaciones pendientes de firma, A10 en pausa, cuota restante, instantánea incompleta...), `/api/outputs/grafana.json` para la fuente JSON / Infinity de Grafana y `/api/outputs/dashboard.json` (el documento `ci_red.json`) para el panel de estado. Un panel de Grafana importable está en `docs/grafana/` y los detalles en `docs/OUTPUTS.md`.
- **Parte:** una línea (código `tag_vs_manifest`) cuando una etiqueta de versión va por delante de la versión del manifiesto; la cifra de sin firmar se ordena por la espera más larga y dice cuánto es; el panel del repositorio sugiere el comando `gh issue close` (nunca ejecutado) para una incidencia de fallo cuyo workflow vuelve a estar en verde; el perfil de lote `hil` está documentado en `profiles.example.json`; pruebas de `finalize` y de `monitor_link`.
- **Documentos:** `docs/SETTINGS.md`, `docs/OUTPUTS.md`, README y QUICKSTART en los 8 idiomas actualizados, capturas hechas con repositorios inventados.

## [1.4.5]

- **El parte dice cuándo la instantánea está incompleta:** una línea con el código estable `incomplete` (aún cargando, sin espacio de trabajo local, errores al leer) justo después del titular, para que nadie actúe sobre una lista a medio leer de repositorios en rojo o de cola de firma.
- **Resumen de firma:** una línea con cuántas versiones esperan a ser firmadas (verificadas / sin comprobar / con la comprobación fallida) y cuántas compilaciones son solo de compilación a propósito, para no confundir «sin firmar a propósito» con «falta la firma» (código `sign_summary`).
- **A10 en pausa por la cuota se dice en el parte** (código `a10_paused`) con la cuota restante y la necesaria, y los tres mandos que la controlan.
- Textos en los 8 idiomas; pruebas de las tres líneas.

## [1.4.4]

- **El autor y la licencia están siempre visibles:** el panel web tiene un pie con el autor y la licencia, `read_report.py --version` y el nuevo `gha_dispatch_all.py --version` los imprimen bajo la versión, y el monitor imprime la misma línea al arrancar. El texto está en los 8 idiomas (`ui.about`); el autor y la licencia vienen de `tool_version.py`.
- **El puente al panel, por escrito:** `docs/CI_RED_BRIDGE.md` dice qué contiene `ci_red.json` (esquema 2, `complete`), cómo exportarlo y qué debe comprobar un lector; el monitor sigue sin empujar ni confirmar nada.
- Pruebas de la línea de autor en los 8 idiomas, el pie, ambos indicadores `--version` y la línea de arranque.

## [1.4.3]

- **Un workflow que solo corre en pull requests ya no vuelve inconcluyente a A2:** `pull_request` y `pull_request_target` se suman a los eventos cuyas ejecuciones nunca están en la rama por defecto (como `workflow_dispatch`, `release` y `workflow_call`), así que a un workflow como una comprobación de integración de contrato que solo corre en pull requests no se le pide una última ejecución en main. Un workflow que además tiene `push` o `schedule` sigue contando. Pruebas de ambos casos.

## [1.4.2]

- **A2 ya no da por vista una ejecución en curso ni una cancelada:** al resolver un workflow oculto, el centinela pide ahora las últimas ejecuciones completadas de ese workflow en la rama por defecto (`gh run list -w <fichero> --branch <por defecto> --status completed -L 10`, solo lectura) y usa la primera con una conclusión real. Una ejecución cancelada u omitida (y cualquiera sin conclusión) se ignora, de modo que ya no puede ocultar un rojo anterior; un workflow sin ejecución completada con conclusión en la rama sigue siendo inconcluyente por sí solo. Misma puerta de cuota, mismo límite de llamadas y misma caché que antes.

## [1.4.1]

- **A2 resuelve un workflow oculto en vez de rendirse con todo el repositorio:** cuando un repositorio tiene una muestra completa de ejecuciones y a ella le falta un workflow de su clon (uno que puede correr en la rama por defecto), el centinela pregunta a GitHub por la última ejecución de ESE workflow en la rama por defecto (`gh run list -w <fichero> --branch <por defecto> -L 1`, solo lectura). Una respuesta en rojo cuenta como rojo en A2; una en verde saca el workflow de la lista de inconcluyentes; un workflow sin ejecución en la rama sigue siendo inconcluyente por sí solo y el panel lo nombra (`repo/fichero.yml (sin ejecución en la rama por defecto)`) en lugar de nombrar solo el repositorio. Sin cuota (la misma puerta que A10: `min_rate_remaining` x `surface.min_rate_factor`, más el presupuesto por hora) el workflow sigue inconcluyente y el panel dice por qué. Opciones nuevas `sentinel.a2_resolve_max_calls_per_tick` (4; 0 = no preguntar nunca) y `sentinel.a2_resolve_ttl_seconds` (3600, cuánto se conserva una respuesta; también se guarda en el fichero de caché). La instantánea lleva `a2.inconclusive_workflows` (etiquetas) y `a2.inconclusive_details`; `a2.inconclusive` sigue siendo la lista de repositorios. 5 textos nuevos en los 8 idiomas y un `ui.a2_inconclusive` reformulado.

## [1.4.0]

- **Capa nueva A11 «Preparación» (solo lectura, solo datos reales):** un panel de la pestaña Centinela, un semáforo en su cabecera y dos líneas del parte. Se activa con `sentinel.readiness.enabled` y se describe en `readiness.py`.
  - **Preparación de versión:** una fila por repositorio con al menos `candidate_min_entries` entradas en `[Unreleased]` (sin los ecosistemas externos): la CI de la rama por defecto (la regla única de A2) con el commit en el que corrió, si la versión que declara el clon (`*.project.json`, si no `pyproject.toml`, si no el primer encabezado del CHANGELOG) ya está por encima de la última versión publicada, si existe una compilación posterior a esa versión, si está firmada (los estados de A5) y el siguiente paso (`arreglar la CI en rojo`, `esperar datos de ejecuciones`, `subir la versión`, `compilar en Actions`, `firmar`, `publicar`, `cortar y publicar`). Una CI en verde sobre una muestra de ejecuciones completa que puede ocultar un workflow más antiguo lo dice.
  - **Salud del ecosistema:** por ecosistema, 100 menos los recuentos ponderados de CI en rojo, compilaciones atascadas, secretos, alertas graves, otras alertas, PRs de Dependabot más antiguas que `stale_pr_days`, compilaciones a la espera de firma y repositorios con problemas de higiene (`sentinel.readiness.health.weights`); se listan las partes que bajan la puntuación. No se muestra puntuación (`?`) cuando menos de `min_coverage` (0,5) de los repositorios del ecosistema tienen datos de ejecuciones y alertas. El parte avisa cuando una puntuación está por debajo de `warn_below` (70).
  - **Fijaciones de dependencias:** repositorios que fijan una versión más antigua que la del repositorio que provee el contrato o la biblioteca. Dónde viven las fijaciones es un dato (`sentinel.readiness.pins.sources`): una tabla JSON de fijaciones en el proveedor (`pin_table`) o ficheros de bloqueo en los consumidores (`lock_files`, cuenta el más antiguo hallado). Son lecturas simples de ficheros de los clones locales, en caché `pins.refresh_seconds`; un ecosistema sin fuente configurada se lista como sin ninguna, y no se adivina nada. El ejemplo incluido no tiene fuente.
  - 60 textos nuevos en los 8 idiomas; `tests/test_readiness.py` (reglas, pesos, cobertura, fijaciones sobre un árbol temporal, la página y los 8 catálogos).
- **`docs/CI_RED_SCHEMA.md`:** dice expresamente que el PC no publica ni `ci_red.json` ni `pending_sign` en ningún repositorio ni panel (el lado de la firma es local por decisión); un consumidor público recalcula la regla a partir de las ejecuciones públicas o usa `read_report.py --export-status`.
- **Ajuste de la cuota a partir del registro (`actions_monitor_log.txt`, 3 días, 889 muestras):** la cuota compartida estuvo por debajo del mínimo (`min_rate_remaining` 1500) en el 11 % de las muestras desde el 5 de noviembre y por debajo de 3000 en el 45 %; el gasto por hora fue de 3000-5000 llamadas en la mayoría de las horas y llegó al límite en algunas. En el `actions_monitor.json` del mantenedor: `refresh_seconds` 120 -> 180 (el ciclo real tenía una mediana de 139 s) y `sentinel.surface.min_rate_factor` 2,0 -> 1,5 (las llamadas en frío de A10 son unas 260 al día, así que pueden correr por encima de 2250; con 3000 esperaban casi la mitad del tiempo). `max_repos_per_tick` (6) y el ciclo diario en frío se mantienen: cuestan menos del 1 % de la cuota. El ejemplo incluido conserva sus valores neutros.

## [1.3.3]

- **A2 ignora los workflows que nunca corren en la rama por defecto:** al decidir si una muestra completa de ejecuciones oculta un workflow, ya no se esperan en la muestra los ficheros del clon cuyo `on:` no tiene `push`, `pull_request` ni `schedule` para la rama (solo `workflow_dispatch`, `release`, `push` solo de etiquetas sin `branches`, o `workflow_call`). `on:` se lee solo con la biblioteca estándar (cadena, lista, mapa y la clave YAML `true`); si no se puede interpretar, el workflow cuenta como antes. El análisis de workflows lleva el campo nuevo `main_triggered` (`true`/`false`/`null`).

## [1.3.2]

- **A2 muestra `unknown` en vez de verde cuando su muestra está llena y es inconcluyente:** un repositorio cuya lista de ejecuciones es tan larga como la muestra pedida (`runs_per_repo` / `cold_runs_per_repo` del monitor, que la comprobación no veía antes) y cuyo clon tiene un fichero de workflow sin ejecución en esa muestra (o que no tiene clon) se lista como inconcluyente, y A2 es `unknown` salvo que algo esté en rojo. Opción nueva `sentinel.a2_full_sample_unknown` (por defecto `true`; `false` = solo informativo como antes). La página lista los repositorios.
- **`profiles.example.json`:** una plantilla neutra de perfiles de lote que concuerda con `targets.example.json` y `ecosystems.example.json`. Una prueba (y la puerta de la versión) la valida contra esos catálogos, no los del mantenedor, y comprueba que cada perfil selecciona al menos un destino.
- **Comprobación de instalación limpia en `make_release`:** antes de dejar nada en la carpeta de salida, el zip se extrae en un directorio temporal nuevo y vacío y, desde allí con `python -I`, debe estar presente cada miembro, compilar cada módulo, funcionar `read_report.py --version` y pasar toda la suite; cualquier hueco hace fallar la versión.
- **Redacción:** README y QUICKSTART en los 8 idiomas dicen ahora que el paquete no escribe nada en GitHub por sí solo y que solo lo hacen `dispatch --go`, `dispatch --real` y `finalize --execute` (que ejecutas tú).
- **Cuota de A10:** la parte del presupuesto de llamadas por ciclo del centinela que A10 puede usar es ahora `sentinel.surface.budget_share` (por defecto `0.5`, como antes pero configurable); la página muestra «A10 en pausa por la cuota» con la cuota restante y la necesaria (`min_rate_remaining` x `min_rate_factor`) mientras esperan las llamadas en frío.

## [1.3.1]

- **Una ejecución construida sobre otro commit nunca se ofrece para firmar:** cuando `dispatch` solo pudo encontrar una ejecución reciente de otro commit (`sha_matched` falso), `finalize` ahora la lista como no lista con el motivo y no da ningún comando de firma; un lote antiguo sin el campo se comporta como antes. Pruebas con dos ejecuciones concurrentes de commits distintos.
- **`/api/data` pasa por la misma guardia de Host/Origin que las demás rutas** del servidor local (DNS rebinding).

## [1.3.0]

Hecha para compartirse: ocho idiomas, autoría y licencia en cada fichero, ningún dato privado y nada atado a una cuenta de GitHub.

- **8 idiomas** (en, es, de, fr, it, ja, zh, pt = portugués de Portugal) para la página, las herramientas de línea de comandos, los lanzadores, los eventos, los partes y los mensajes de error. `i18n.py` + `locales/<idioma>.json` (un catálogo plano por idioma, solo biblioteca estándar, `t("clave", nombre=valor)` con respaldo al inglés). El idioma es `language` en `actions_monitor.json` (por defecto: el idioma del sistema, inglés si no está soportado), un selector en la cabecera de la página (el navegador lo recuerda), `MONITOR_LANG` / `JUANENRAC_LANG`, o `--lang CÓDIGO` en cada herramienta (gana a los demás). Los nombres técnicos, comandos, rutas y las marcas que leen los scripts (`SKIP`, `DISPATCHED`, `READY`, `FAILED`, `Summary:`, `BUILD ONLY`, `WOULD DISPATCH`...) nunca se traducen. Los eventos de `events_monitor.jsonl` llevan ahora un `code` estable (y `args`) junto al texto, para que nadie tenga que interpretar un idioma.
- Una prueba comprueba que los 8 catálogos tienen exactamente las mismas claves, ninguna vacía, los mismos `{marcadores}`, que cada clave usada por el código y la página existe y que ningún texto visible del código se salta `t()`.
- README y QUICKSTART en los 8 idiomas (`README_<idioma>.txt`, `QUICKSTART_<idioma>.txt`); `README.txt` es ahora un selector de idioma breve con el inicio rápido.
- **Autoría y licencia**: cada fichero fuente lleva «Copyright (C) 2026 JuanenRac (Electro Hobby 3D)» y «GPL-3.0-or-later - see LICENSE»; los ficheros de datos JSON llevan `_author` / `_license`; `LICENSE` (texto de la GPL-3.0), `NOTICE` y `AUTHORS` viajan en el zip. `make_release.py` se niega a construir cuando a un fichero le faltan, cuando viajarían datos privados, cuando los locales difieren o cuando un lanzador pierde su bit de ejecución.
- **Compartible**: `github_owner` en la configuración (por defecto: la cuenta de `gh`) sustituye a la constante que estaba repartida en tres módulos; los prefijos de ecosistema y las herramientas de firma son datos (`ecosystems.json`, neutro `ecosystems.example.json`; `"*"` = todos los repositorios; `"external": true` = solo se informa) y los destinos también (`targets.json` es el catálogo real del mantenedor, `targets.example.json` el neutro; `targets_file` / `ecosystems_file` los eligen; las claves que empiezan por `_` son metadatos). La configuración de ejemplo es neutra. Nada de esto añade una llamada al ciclo caliente.
- **El espacio de trabajo es opcional**: sin clones locales el monitor arranca en modo reducido (solo lo que da la API de GitHub: sin cola de firma local, sin parte de auditorías, sin análisis del CHANGELOG) y lo dice en la página, en el parte y al arrancar, en lugar de detenerse. `MONITOR_ROOT` / `MONITOR_AUDIT_DIR` / `MONITOR_SIGNED_DIR` y `signed_dir` se añadieron junto a los nombres antiguos. La capa de hoja de ruta (A9) también es opcional.
- Lanzadores: los menús y mensajes vienen de `launcher_msg.py` (tu idioma); comentarios en inglés; cabecera en cada fichero.
- Corrección: `workspace_root()` ya no termina el monitor cuando el centinela arranca sin espacio de trabajo.

## [1.2.0]

Lo que faltaba y qué más se puede hacer en GitHub, todo de solo lectura y local.

**Parte A - lo que faltaba**
- El esquema 2 de `ci_red.json` es ahora un contrato documentado: `docs/CI_RED_SCHEMA.md` (forma, la regla única de «rojo», lo que es solo para el propietario). No se publica nada desde el PC. Exportaciones opcionales y explícitas (nunca un commit ni un push): `read_report.py --export-status DIR` escribe SOLO la lista en rojo (`ci_status_public.json/.md`); `read_report.py --export-sign-queue FILE` (.json/.csv) escribe la cola de firma global con los comandos locales.
- Atestación: la cola de firma muestra si la compilación tiene una atestación (existencia por huella de los ficheros firmados, una consulta por entrada, sin comprobación de firma; interruptor `sentinel.surface.checks.attestation`). Una ausente es una línea del parte.
- Más formatos verificados: HYDRA `hydra-sign` (`FICHERO.sig` = Ed25519 en base64 sobre los bytes del fichero, la clave de versión fijada, leído por bloques) se comprueba de forma definitiva; URTC `.imgsig` tiene su formato estricto comprobado (152 dígitos hexadecimales + LF; mal formado = no válido) y queda «unknown» cuando está bien formado (el mensaje firmado también necesita la cabecera de la compilación, que la carpeta de firmados no lleva); los APK de ARMOR se firman dentro del APK con apksigner y quedan «unknown».
- `HYDRA-UMC-OS` se etiqueta a propósito en `targets.json` (`"build_only": true` + `reason`): `plan` lo lista en BUILD ONLY y ya no es huérfano. Las herramientas de firma no se tocaron (su workflow toma otras entradas y un esquema de firma distinto).
- Corrección: `ci_red.target_path` rechazaba todas las rutas de Windows escritas con barras invertidas (`C:\...`); solo se aceptaban barras normales.

**Parte B - la capa A10 «superficie de Actions y versiones»** (`surface.py`, sección nueva de la pestaña, un interruptor y un umbral por comprobación bajo `sentinel.surface`)
- Actions: workflows desactivados a mano, programaciones sin ejecución en N días (solo cuando la muestra de ejecuciones cubre la ventana), `uses:` no fijados por SHA (los workflows reutilizables se marcan aparte), `permissions: write-all`, `pull_request_target` con checkout de la PR, colas de concurrencia atascadas, fallos en un solo SO de una matriz, coste y retención de artefactos, comprobaciones de estado requeridas que están en rojo o ausentes (GraphQL), `dispatch --profile release|nightly|hil` con un canario (solo el primer destino, el resto solo si está en verde) y una puerta de cuota (`--min-rate`, falla cerrada). Los perfiles viven en `profiles.json`.
- Versiones: activos esperados por tipo de destino (alerta cuando se publicó una versión incompleta), etiqueta frente a manifiesto frente a CHANGELOG, GitHub Packages, borradores y preversiones olvidados, `release_notes.py` (un BORRADOR de notas a partir de los commits desde la última etiqueta; no publica nada).
- Seguridad: alertas críticas/altas por antigüedad con un ranking de repositorios, cobertura (una pila sin CodeQL/Dependabot), escaneo de secretos abiertos frente a resueltos, Dependabot por prioridad (primero las mayores de runtime, al final las solo de CI).
- Incidencias y PRs: sugerencia de `gh issue close` para incidencias de compilación cuya CI vuelve a estar en verde (un evento con el texto; nunca se cierra nada), hitos vencidos, PRs humanas antiguas, PRs que tocan workflows o CODEOWNERS, la cola de fusión (aprobadas con comprobaciones en verde). Tarjetas de tablero obsoletas: PENDIENTE (necesita lecturas por elemento y un umbral).
- Manifiesto frente a evidencia (madurez), fallos de paridad del README en 8 idiomas, minutos de Actions por ecosistema en la cabecera, el parte y A7.
- `finalize --execute` ahora dice al monitor en marcha (127.0.0.1) que actualice justo los repositorios firmados y reescriba `ci_red.json` al instante (`monitor_link.py`).
- Receptor opcional de webhook firmado (`webhook.enabled`, apagado por defecto, solo 127.0.0.1, HMAC con un secreto compartido de la configuración, nunca un token de GitHub).
- Coste: nada en el ciclo caliente. En frío, repartido en ciclos y dentro del presupuesto por hora: 2 llamadas REST por repositorio y día, una consulta GraphQL por cada 15 repositorios y día, 3 para Packages, más los jobs de las ejecuciones en rojo y las consultas de atestación de la cola de firma, y solo mientras la cuota esté por encima del doble de `min_rate_remaining`. El paso GraphQL caliente pide 3 campos más por nodo (fechas de alertas, decisión de revisión, estado de comprobaciones): sin llamadas extra.
- La puerta también compara `sentinel.surface` del fichero de ejemplo con los valores por defecto y valida `profiles.json`.

## [1.1.1]

- **Multiplataforma:** el monitor y las herramientas de lotes funcionan en Windows, macOS y Linux. Lanzadores `MONITOR_GITHUB_ACTIONS.sh`/`.command` y `BATCH_GITHUB_ACTIONS.sh`/`.command` (el zip conserva el permiso de ejecución y make_release rechaza los finales de línea de Windows en ellos).
- Nuevo `platform_compat.py`: el comando que arranca una herramienta hija (`py -3` en Windows, el intérprete actual en el resto), el texto de los comandos que muestra `finalize` (comillas de cmd/PowerShell o de POSIX), consola UTF-8 y un aviso con la forma de instalar `gh` en cada sistema.
- Pruebas nuevas de la parte multiplataforma (Windows y POSIX simulados desde cualquier sistema).

## [1.1.0]

Confianza en las firmas, un puente estable al panel, huérfanos y convenciones en las herramientas de lotes, y una página más útil.

- Confianza en la firma: `sigverify.py` (biblioteca estándar, solo lectura, sin red) comprueba la carpeta de firmados `_firmados/<REPO>/release-<versión>/` contra la clave PÚBLICA que fija cada ecosistema (URTC `release_sign.py`, el ayudante de ARMOR `PACKAGE_PUBLIC_KEY`, el actualizador de HYDRA `RELEASES_PUBLIC_KEY`, o `sentinel.signature_pubkeys`). Cada estado lleva ahora `signature_kind` (none | dev | release) y `signature_verified` (true | false | "unknown"); solo una firma de versión que se verifica (`trusted`) baja la alerta de firma pendiente, además de «publicado». Una firma que no se verifica mantiene la alerta y lo dice en el parte. `sentinel.require_verified_signature` (por defecto true; false = la regla de la 1.0.0). Los formatos que este módulo no puede comprobar (.sig2, .hdr2, .imgsig, APK, hydra-sign) son «unknown», nunca «false». La atestación de la compilación sigue necesitando la red y se queda con las herramientas de firma.
- Esquema 2 de `ci_red.json`: por repositorio una lista `pending_sign` (workflow, horas, estado, signature_kind, signature_verified, last_build_at, url) junto a los workflows en rojo, más `schema`, `pending_sign_repos` y el umbral; el formato está documentado en `ci_red.py` y solo se amplía.
- Una definición de «última ejecución en main» (`signstate.completed_runs`) compartida por la comprobación de rojo, la de verde sin versión y los estados de los destinos.
- `ci_red.target_path` rechaza rutas de D:, las formas WSL/Git Bash de D: y rutas de unidad/UNC que el sistema en marcha no puede usar; las pruebas simulan ambos sistemas y toda la suite pasa ahora en Linux.
- `gha_dispatch_all.py plan` termina siempre con la sección «Huérfanos de firma» (CI en verde + `*-build.yml` conocido + sin destino); la cobertura es por repositorio Y workflow.
- Convención para los destinos (prefijo de ecosistema -> herramienta de firma por defecto, workflow en la lista conocida); `targets.json` solo contiene las excepciones y siempre gana. `hygiene --write-candidates` escribe las entradas propuestas en `targets.candidates.json` (nunca se aplican solas, nunca se empaquetan).
- Página: contadores de cabecera pulsables «rojo en main» y «sin firmar» (filtran los repositorios; el segundo también enfoca la cola de firma), la cola de firma con sus comandos y un botón de copiar, panel del repositorio con compilado / firmado / publicado, tipo de firma y verificación, y el comando sugerido; una insignia en la cabecera cuando un presupuesto de minutos llega al 80 % (roja al superarlo); «ayer frente a hoy» también compara los avisos de presupuesto y las líneas del parte.

No hecho: leer la atestación de la compilación / SBOM (red); `HYDRA-UMC-OS` tiene un workflow de compilación pero su herramienta de firma aún no lo soporta (se lista como huérfano).

## [1.0.0]

Primera versión numerada. Lo que hace el paquete:

- Monitor de GitHub Actions para los cuatro ecosistemas (página web local, caché de ejecuciones, compilaciones atascadas, incidencias de build-failed/build-stuck).
- Capa A del centinela (solo lectura, sin IA): A1 compilaciones atascadas, A2 CI en rojo (un solo criterio: la última ejecución completada de cada workflow en la rama por defecto), A3 alertas de CodeQL/Dependabot/secretos, A4 pull requests de Dependabot, A5 versiones (candidatas, compilaciones en verde sin versión, firma pendiente), A6 higiene, A7 consumo (minutos y cuota de la API), A8 auditorías y rondas, A9 tableros de hoja de ruta.
- Estado explícito de cada destino de compilación: built_on_gha -> signed_local (none | dev | release) -> published, con `last_build_at`, `last_signed_at`, `signature_kind` y las horas reales de espera; los registros locales de lotes y de la carpeta de firmados bajan la alerta de firma pendiente sin esperar a GitHub.
- Cola de firma del día (`a5.sign_queue`): lo más urgente primero, con el comando finalize exacto de cada destino.
- Presupuesto de minutos de Actions por ecosistema (`sentinel.minutes_budget`, vacío por defecto): aviso al 80 % en el parte y como evento.
- Registro de eventos (`events_monitor.jsonl`) y `ci_red.json` (repositorio -> workflows en rojo + horas pendientes de firma), escritos de forma atómica.
- Herramientas de lotes: `gha_dispatch_all.py plan|dispatch|status|finalize|hygiene` con `--only` o `--ecosystem`, `plan --json`, `finalize --json`, un reintento de un dispatch fallido al final del lote, destinos como datos en `targets.json`.
- `read_report.py`: el parte como texto plano desde el monitor en marcha, sin gastar cuota de la API.
- `make_release.py`: puerta de calidad (pruebas unitarias, zip limpio, configuración de ejemplo completa, acuerdo versión/changelog) y SHA256SUMS.

No hecho en esta versión: verificar las firmas de las versiones contra la clave pública y la atestación de la compilación desde el centinela (formatos de firma distintos por ecosistema; la atestación necesita la red; las herramientas de firma verifican ambas antes de publicar).

