# Hoja de ruta

Lo ya publicado, lo que viene y lo que solo es una idea, en ese orden de certeza. Son direcciones, no compromisos; una incidencia o una pull request es la mejor forma de empujar una.

## Dónde está el monitor ahora

Versión 2.0.2. La edición lite muestra lo que se ejecuta y lo que falló. La edición completa añade tres centinelas (CI, Collab y Security), una lista de alertas, varias cuentas y un equipo con roles, la puntuación de cada cuenta, la salud de cada repositorio y del equipo, informes programados, un registro de acciones, notificaciones (ntfy, Teams, correo y Apprise), un asistente de IA opcional con preajustes de servicios compatibles, el modo servicio con Docker y una página para todos los tamaños de pantalla, de un móvil a 4K.

## Previsto, en este orden

Cada versión lleva solo contenido real: una versión sin nada real que añadir se salta y nunca se publica vacía. Nada de esto se da por probado con servicios reales salvo que su guía lo diga.

### 2.0.2 a 2.0.9 - Después de la congelación

Lo que solo aparece con un uso real prolongado: la migración desde la 1.8 y la 1.9, el crecimiento de los eventos y de la base de datos durante meses, las sesiones tras una actualización, los volúmenes de Docker, muchas cuentas con tres centinelas y el modo equipo a la vez, y lo que encuentre la batería de contrato. Nada de la cuarta fase (plugins, automatización amplia, IA avanzada) entra en estas versiones; una versión sin nada real que añadir se salta.

Los workflows del propio monitor cumplen lo que el centinela de higiene pedirá a los demás: acciones fijadas a un commit, los permisos mínimos y un límite de tiempo en cada trabajo.

## Hecho en la 1.8.2 a la 2.1.1

### 2.1.1 - Dos centinelas nuevos, uno de cadena de suministro y otro de entrega, y una puerta de release más estricta

Dos centinelas nuevos, apagados de fábrica y solo en la edición Complete, leen lo que un repositorio construye y lo que entrega sin escribir nada en GitHub: el de cadena de suministro revisa los ficheros de workflow en busca de acciones sin fijar, ramas móviles y permisos amplios o ausentes, y el de entrega compara releases, etiquetas, el changelog, los ficheros de versión y las versiones fijadas. El doctor muestra ahora en rojo un webhook entrante sin secreto, la cobertura del webhook ya no se queda viva cuando se atrasa el reloj, y la puerta de release compara el contenido de cada fichero del zip con el commit, acepta una pasada verde completa por el recuento que dio unittest y puede decir cómo van sus suites.

### 2.1.0 - Pantallas de pared con tema, logo y modo rotativo, una copia que se puede restaurar y un actualizador

Las pantallas de pared llevan el tema del producto y pueden mostrar el logo de la organización; una ventana puede recorrer las tres pantallas y saltar a un rojo nuevo; el resumen muestra el mapa de la flota por grupos; una actualización de Dependabot que falla es una alerta propia; y cada tipo de evento tiene también su sonido en este equipo. La instalación se puede copiar entera, verificar y restaurar, con un calendario si se quiere; el doctor comprueba el funcionamiento con códigos de salida que no cambian y se puede lanzar una purga a petición. El actualizador lleva una instalación a cualquier versión publicada, la copia antes y deshace si algo falla. La puerta de publicación nombra los tests que fallan y acepta una pasada verde ya vista, las etiquetas de estado de los paneles de detalle se quedan en una línea, los enlaces de la página se comprueban leyendo la dirección y la guía del contenedor explica cómo abrir la primera sesión.

### 2.0.9 - Una auditoría independiente más segura, menús con grupos, un sonido por tipo de evento y comandos de chat de solo lectura

La auditoría independiente endureció el monitor: el token de acceso ya no viaja en la dirección por defecto, una silenciación por patrón ya no silencia lo que no es un workflow, el limpiador de texto atrapa más formas de un log real, una cabecera con un secreto nunca sigue una redirección, una entrega del webhook se comprueba y no se puede repetir, y un proveedor en internet o en una dirección privada necesita su propio interruptor. El menú de la izquierda tiene grupos con título, cada tipo de evento tiene su propio sonido, comandos de solo lectura responden en Slack y Discord (apagados por defecto), las pantallas de pared siguen el idioma de la página principal y la IA integrada tiene un único presupuesto que también cuenta el aviso activo. El registro de acciones puede ser condición de las acciones y guarda el número de ficheros rotados que elijas, un ciclo cuenta una sola vez para todas las etapas del centinela, y un workflow para la auditoría de la imagen del contenedor, con los fallos que encontró en el contenedor, forma parte de la versión.

### 2.0.8 - Un secreto del webhook más seguro, check runs y una guía para configurar el webhook (la versión que cierra la cuarta fase)

El secreto compartido del webhook de entrada solo viaja en el entorno (o en un fichero que nombra el ajuste), el webhook también recibe eventos de check run, la vista En vivo dice cuánto del tiempo cubren los eventos, y una guía en ocho idiomas (`docs/WEBHOOK.md`) configura el webhook en GitHub paso a paso. Los estudios de cuentas reales añaden tres filas: un workflow cuyo fichero se borró no es uno que se pueda activar, un fork que nunca se empujó no está recién empujado, y el runner `codspeed` se reconoce como un runner de terceros de pago. Los documentos ya no dicen que macOS corre en el CI. Es la versión que cierra la cuarta fase: una versión de estabilización previa a la auditoría.

### 2.0.7 - Una API de lectura para clientes, el repositorio original de cada fork y los workflows desactivados a mano

Una API de lectura bajo `/api/v1/` para clientes (`me`, `repos` y `openapi`, desactivada por defecto, con un contrato congelado); un seguimiento opcional del repositorio original de cada fork (`upstream.enabled`, desactivado por defecto, con un límite de peticiones por hora); y un workflow que el propietario desactivó a mano deja de ser un rojo y se muestra aparte (`ci.disabled_apart`).

### 2.0.6 - Tres pantallas de pared, dibujadas y desactivadas por defecto

Las tres pantallas de pared están dibujadas: General (puntuación, lámparas de la flota, gráficos, mapa de calor, runners y la cuota), Ahora (ejecuciones en curso, cola, aprobaciones, fallos recientes y una línea en vivo) y Centinelas (una ficha por centinela con un radar animado). La página dibuja cada gráfico ella misma, un fallo nuevo parpadea una vez y se calma, nada se mueve para quien pidió menos movimiento, todo se desplaza un poco cada minuto contra el quemado, la página puede atenuarse de noche, una ventana puede girar entre las tres páginas y una prueba de navegador las comprueba en 1080p, 4K y girada en los ocho idiomas. Las pantallas están desactivadas por defecto (`screens.enabled`), y el README y la guía de las pantallas ya las muestran.

### 2.0.5 - Menos falsos rojos, repositorios dormidos y preguntas que se ven a pantalla completa

Un rojo cuenta ahora según el origen del evento: los workflows que GitHub hace por su cuenta (`dynamic/`) no son CI en rojo ni ficheros, la búsqueda de un workflow oculto obedece la misma regla de origen, las ejecuciones en cola durante días se distinguen como una cola fantasma (7 días por defecto) y un rojo que nadie atiende envejece a los 30 días y pasa a inactivo; los repositorios dormidos e inactivos son un estado propio, ni verde ni rojo; los forks entran en la higiene, el lint y la puntuación solo cuando tienen CI propia en los últimos 90 días; la protección de la rama por defecto se juzga por defecto por lo que está en vigor, con todas las fuentes públicas; y las cinco confirmaciones de la página usan un diálogo de la página que se ve a pantalla completa.

### 2.0.4 - Un modelo para cada tarea, menús independientes y una ayuda que abre el tema correcto

La IA del monitor puede usar un modelo para cada tipo de tarea, una cadena de respaldos cuando falla el modelo principal y un presupuesto para cada modelo, todo desactivado hasta escribirlo en los ajustes; Alertas, Informes y Lecciones son tres entradas independientes del menú, cada una con su panel, insignia, tema de ayuda y dirección; la pestaña Historia mantiene un solo contador en vez de acumular copias en cada refresco; el botón «Ayuda de esta pestaña» abre en todas las pestañas el tema de la pestaña abierta; y las pruebas del navegador se omiten limpiamente cuando falta la carpeta de herramientas.

### 2.0.3 - Cuentas grandes, menos falsos rojos, linter sin clones y un almacenamiento más seguro

Una vista de flota, listas paginadas, un presupuesto de peticiones y una cobertura honesta de la lista de ejecuciones para cuentas con cientos de repositorios; un rojo solo cuenta cuando lo causó el propio repositorio, y las ejecuciones que esperan una aprobación, los workflows abandonados, los que solo reaccionan a issues, la cola de fusión y las ramas de mantenimiento tienen cada uno su sitio; el linter de workflows y las comprobaciones de superficie funcionan por la API o con un clon parcial sin clonar; los modelos del proveedor de IA se leen y se comprueban, y cada enlace de la página pasa por el filtro de direcciones; los bloqueos y el registro de acciones son más seguros en Windows y el libro de puntuación nunca se sobrescribe; pantallas de pared para un monitor o un televisor, desactivadas por defecto; las pruebas del repositorio dejan de ejecutarse en macOS por ahora.

### 2.0.2 - Registros más seguros, texto de IA más limpio y una puntuación más justa

Todo lo que puede leer una IA pasa por un solo limpiador que conoce más formas de secreto, el asistente integrado conserva su clave y ya no sigue redirecciones ni proxies, el registro de acciones es una cadena en un fichero por cuenta y un lector no puede leerlo, la imagen y los procesos de las cuentas ya no llevan secretos, la puntuación penaliza un fallo que nunca se arregla y ya no cuenta una fuente ilegible como limpia, y una larga lista de correcciones del almacenamiento, las copias de seguridad, la migración, las vistas de terminal y el lanzador.

### 2.0.1 - Empaquetado y una clave que faltaba

El zip publicado ahora lleva el fichero de los preajustes de IA y todos los demás ficheros de datos del paquete, y la puerta de publicación falla si falta alguno en el zip; la página de todas las cuentas ya no muestra una clave de estado sin traducir, y un test comprueba que cada clave que usa la página existe en los ocho catálogos.

### 2.0.0 - Madurez

La API de lectura y las interfaces públicas quedan congeladas: un fichero de contrato con las claves y los tipos de cada endpoint de lectura y los códigos de error, una batería de tests y una herramienta que lo comprueban contra cualquier monitor en marcha, un test que fija los campos de una alerta y los métodos de un centinela y de un almacenamiento, y una guía para cada uso (lite, una persona, servicio, equipo) y para los clientes de la API, en ocho idiomas. Las versiones 1.9.6 a 1.9.9 no tenían nada real que añadir tras las revisiones de cierre y se saltaron.

### 1.9.5 - Flujo de eventos en vivo

Un flujo de los eventos en vivo del webhook de entrada para clientes y pantallas de pared que no pueden sondear, apagado por defecto, de solo lectura, con un límite de oyentes y un límite de tiempo para cada uno.

### 1.9.4 - Preajustes de IA

Una tabla de doce servicios alojados y seis servidores locales que hablan un protocolo que el monitor ya conoce, un selector en los ajustes de IA que rellena la dirección, el nombre de la variable de la clave y un modelo de ejemplo, servidores locales que funcionan sin clave y las direcciones de los principales servicios leídas en su documentación pública.

### 1.9.3 - Informes programados y registro de auditoría

Plantillas de informe en HTML y Markdown (PDF opcional) con la puntuación, las alertas principales y los cambios, un planificador y un registro de auditoría de solo añadir con quién hizo qué y cuándo, sin ningún secreto dentro. Opcional, en la misma versión: una vista «versión lista / bloqueada» con el último commit en verde de cada repositorio.

### 1.9.2 - Salud del repositorio y del equipo

Una vista de salud de cada repositorio (CI, incidencias y pull requests, seguridad, preparación para una versión, actividad) y una del equipo con clasificación, totales y filtros; páginas para ambas con enlaces directos para pantallas de pared. Opcional, en la misma versión: un panel de benchmarks nocturnos frente a un presupuesto (mediana frente a una referencia por clase de máquina) y un panel de listas de materiales de software y atestaciones de cada versión.

### 1.9.1 - Centinela de seguridad

El tercer centinela: Dependabot, análisis de código, análisis de secretos, protección de ramas, permisos de los workflows y propietarios del código, con reglas por tipo de señal, el mismo filtro en la pestaña Alertas y una penalización en la puntuación por alertas críticas abiertas. Opcional, en la misma versión: higiene de workflows (acciones que no están fijadas a un commit, trabajos sin límite de tiempo, workflows sin permisos o sin concurrencia, uso peligroso de pull_request_target), sobre el comprobador de workflows que el proyecto ya tiene.

### 1.9.0 - Una puntuación

Recolectores de métricas por cuenta y por centinela (tasa de éxito, duración, tiempo de recuperación, rendimiento), un motor de puntuación con umbrales que puedes cambiar, tendencia frente al periodo anterior, instantáneas guardadas en el almacenamiento, un widget de puntuación con minigráfica, alertas cuando la puntuación baja y un verbo de la línea de comandos que la imprime.

### 1.8.4 - Estabilización

Sin grandes funciones. Aislamiento entre cuentas, la página, el almacenamiento, acceso y roles, notificaciones, un GitHub que falla a ratos, el arranque tras una migración interrumpida, la recuperación tras un corte, un doctor más amplio, los sitios que escriben en GitHub, registros sin tokens, una lista de comprobación de seguridad del modo equipo y documentos que coinciden con el comportamiento. La serie sigue hasta la 1.8.9 solo si hace falta.

### 1.8.3 - Notificaciones por usuario

Preferencias por usuario (canal, centinela, nivel mínimo), un despachador que decide a quién avisar según las preferencias y los roles, canales como complementos sencillos y resúmenes de las alertas aún no leídas. Además: un informe del tiempo que esperan los trabajos en cola por cada runner, y un trabajo omitido por las rutas que vigila se muestra aparte de un trabajo en rojo.

### 1.8.2 - Imagen Docker oficial y modo servicio

Una imagen de varias etapas con usuario sin privilegios, volúmenes para datos y configuración, variables de entorno documentadas, un ejemplo de compose con proxy inverso y TLS opcionales, una unidad de systemd para quien prefiera la instalación clásica y una comprobación de salud profunda que falla si el supervisor o el ciclo de una cuenta están atascados. Una credencial que GitHub revoca o deja caducar marca solo esa cuenta como ciega, lanza una alerta crítica de sistema y se puede sustituir sin reiniciar el supervisor. Copia de seguridad, actualización y primer arranque como servicio quedan documentados; la página dice si escucha en este equipo, en la red o detrás de un proxy; la línea de comandos funciona contra un monitor remoto. La edición lite sigue siendo local.

## Hecho en la 1.8.0

Todo lo que sigue se entregó en la serie 1.8 y está probado; nada se da por demostrado con servicios reales.

- Una nueva organización de carpetas (el paquete en `src/`, la página, los ejemplos y los idiomas en `assets/`), con una herramienta de migración que mueve una instalación plana antigua sin borrar nada.
- Una capa de almacenamiento tras una sola interfaz, con el soporte de ficheros que mantiene la disposición de `accounts/<id>/`, escrituras atómicas y copias de seguridad que cualquier soporte puede restaurar.
- Un soporte SQLite opcional (apagado por defecto), una base por cuenta, migraciones con versión, un tiempo de espera ajustable y herramientas para pasar el estado entre el soporte de ficheros y SQLite en ambos sentidos, con una simulación previa.
- El historial de cambios está traducido a los ocho idiomas hasta la 1.0.0 y una prueba lo mantiene completo.
- Retención y rotación del historial (eventos y analíticas durante un número de días, borrar o archivar, una línea de auditoría por pasada, aviso de tamaño en el doctor; el estado de los centinelas y la configuración nunca se tocan).
- Modo red: el freno de bloqueo vuelve a actuar antes de mirar el token, un proxy inverso declarado nunca se toma por este equipo, las lecturas remotas de los ajustes se limitan a lo que un cliente remoto puede cambiar y la guía de despliegue trae la receta completa.
- El canal para la IA se limpia campo a campo, solo pasan direcciones de GitHub de formas cerradas y el gancho no entrega texto de registros, solo el repositorio, el workflow, el resultado y el enlace.
- Las lecturas de identidad son siempre del usuario, una lectura se juzga con una lista blanca y el fichero de token de la segunda cuenta se queda dentro de la carpeta de cuentas.
- Una prueba de humo de la página en un navegador real pone la CI en rojo cuando una pestaña se rompe o una función está definida dos veces.
- Una barra inferior de una sola línea que dice solo lo que las cajas de arriba no dicen, un resumen para las herramientas de IA y un registro acordes con el monitor en marcha, una página que avisa cuando va desfasada respecto al monitor y un sonido que se desbloquea con un clic y sobrevive a una recarga.
- Una lectura opcional de repositorios tranquilos por GraphQL (apagada por defecto) con su contabilidad.
- El aviso activo a una IA externa (apagado por defecto, una primera confirmación por proveedor, solo los campos redactados de una lista cerrada, un tope de llamadas y de coste por hora, la clave por el nombre de una variable, y la IA nunca ejecuta una acción).
- La aplicación de terminal edita listas y mapas.
- Modo equipo (apagado por defecto): usuarios, roles (admin, maintainer, viewer) y sesiones guardados en el almacenamiento, página de acceso, un token Bearer para clientes que no son un navegador, errores JSON estables y una recuperación de un administrador desde la consola de este equipo. El modo individual sigue sin acceso y la edición lite nunca lo tiene.
- Una página con más vida: iconos animados, bombillas de estado cuyo movimiento sigue su estado, respuestas al pasar, enfocar y pulsar; todo se apaga con movimiento reducido y es ligero en la edición lite.

## Hecho en la 1.7.9

### Corregido

## Hecho en la 1.7.8

### Añadido

## Hecho en la 1.7.7

### Añadido

## Hecho en la 1.7.6

La conexión entre el monitor y una herramienta de IA: el flujo coincide siempre con la página, cada alerta dice por qué está roja, un flujo en directo y tres herramientas MCP empujan las novedades, un comando instala el script de enlace, la barra muestra si hay una IA conectada y todos los ficheros de estado son privados de su dueño.

## Hecho en la 1.7.5

La línea de comandos toma el token de acceso con su propio nombre, el modo red es más seguro por defecto (la dirección del ordenador se oculta a la red, la dirección antigua ?access= se puede desactivar, se rechazan los destinos de notificación de la red local, aviso sobre HTTP plano), las horas para las personas usan tu zona horaria, una alerta se puede silenciar hasta que cambie el elemento, y se corrigen los recuentos y comprobaciones que daban respuestas erróneas.

## Hecho en la 1.7.4

Una barra al pie de la página con el aviso más importante (y una ventana con todos), la conexión, la cuota, la última lectura, el modo, la dirección y el reloj; un botón de pantalla completa; tablas de Repositorios e Historial que se ordenan por una o varias columnas con las columnas que elijas; `bin/monitor_cli.py`, la línea de comandos como cliente del monitor en marcha (`status`, `health`, `alerts`, `accounts`, `live`, `doctor`) con `--json` y códigos de salida estables, y su guía en ocho idiomas; los registros de cambios comprobados en orden, el README del paquete sin historial dentro y los dibujos hechos de nuevo.

## Hecho en la 1.7.3

Un segundo centinela para incidencias y pull requests (Collab, apagado por defecto, solo lectura, con reloj propio), una pestaña Alertas con las alertas de todos los centinelas y filtro por origen y nivel, silencios locales que acaban solos (una alerta, una regla o un centinela; `alerts.mute_hours`), la etiqueta que hace ignorar un elemento, `GET /api/alerts` y `GET /api/events`, una lista de comprobación de la vista En vivo, una guía del centinela Collab en ocho idiomas y los dibujos hechos de nuevo.

## Hecho en la 1.7.2

La cabecera con sus cifras en un orden que se lee y en una rejilla que sigue el ancho; los controles rápidos (solo calientes, velocidad, salud de los ecosistemas) fijos arriba a la derecha; Ajustes, Ayuda y Acerca de solo en el panel lateral; el aviso de versión nueva fuera de la cabecera; y las pruebas que ya no dejan ficheros junto al código.

## Hecho en la 1.7.1

Una página con panel lateral (el logotipo, el selector de cuentas, las secciones en grupos que se pliegan, la ayuda) y dieciséis temas además de auto, claro y oscuro, los del Studio del sistema de alarma; y el centinela de CI detrás de un contrato (`BaseSentinel`, `Alert`, `SentinelRegistry`, `SentinelCI`), para poder añadir los siguientes centinelas sin que el monitor sepa qué hace cada uno. Lo que se muestra y se decide no cambia.

## Hecho en la 1.7.0

Varias cuentas en la edición completa, cada una un monitor propio bajo un supervisor (`accounts/<id>/`, `--accounts`, `--account`, `--migrate-accounts`), la API de las cuentas, un webhook para todas, la página con un selector y las tarjetas de todas las cuentas, las vistas por dirección (`?view=` y `?chrome=0`) y la vista En vivo con el estado del receptor de webhook. La edición lite no cambia.

## Hecho en la 1.6.8

El proxy HTTPS de la 1.6.7 se comprueba contra un proxy real en el puerto 443 (`tools/manual_check_live.py proxy`, y pruebas que recorren un cliente sobre TLS, un proxy inverso y el monitor), las imágenes se han vuelto a tomar con dos nuevas del modo red, y el historial de cambios está traducido a los otros siete idiomas hasta la 1.6.3.

## Hecho en la 1.6.7

Un proxy HTTPS en el puerto 443 por defecto ya funciona con el modo red (`listen.proxy_public_host`, vacío por defecto: el único nombre público del proxy se acepta sin puerto, solo con HTTPS, y solo se cambia desde el propio equipo), y el historial de cambios está traducido a los otros siete idiomas para la 1.6.7, la 1.6.6 y la 1.6.5.

## Hecho en la 1.6.6

Correcciones tras la 1.6.5: el modo red funciona ya con HTTPS desde la página (la guarda de origen sigue el esquema de la sesión), todo ajuste que el esquema marca como seguro solo se cambia desde el propio equipo, `act` libera su ejecución tras Stop y cierra su tubería, una barra roja en Ajustes cuando el modo red escucha en todas las interfaces, la sesión puede abrirse por POST en lugar de por la dirección, un contador de fallos tragados en `--doctor` y Acerca de, `tools/make_screenshots.py` dice lo que hace y las imágenes se han vuelto a tomar, y el historial de cambios está traducido a ocho idiomas.

## Hecho en la 1.6.5

Una versión de integridad y seguridad, sin funciones grandes nuevas: un commit en verde exige el workflow obligatorio del repositorio, un fetch fallido detiene el despacho, el catálogo no puede nombrar una herramienta fuera de la carpeta de herramientas ni cambiar `dry_run`/`ref`, y un lote sin comprobación de commit registrada ya no se ofrece para firmar; `act` se queda dentro del espacio de trabajo y Stop termina todo el árbol de procesos y los contenedores de la ejecución; el modo red puede servir HTTPS, bloquea los tokens erróneos y solo acepta IPv4; el webhook rechaza reenvíos e inundaciones; el servidor MCP sobrevive a mensajes mal formados; `max_per_hour` cuenta mensajes; los ajustes se guardan bajo un bloqueo; el token guardado llega solo a `gh`; `--doctor` avisa de combinaciones peligrosas; la prueba de instalación limpia es una etapa propia del control de calidad de la publicación.

## Hecho en la 1.6.4

Pruebas de aislamiento de la edición lite y de la demo, ninguna petición de red cuando la comprobación de versión está apagada o la instalación está aislada, un README que empieza por la elección del lanzador, `--doctor --json`, una barra persistente para el modo red, la Ayuda y sus documentos en ocho idiomas, y las funciones opcionales (modo red, un token guardado por el monitor, acciones sobre GitHub, `act`, copia local de artefactos, runners propios, OpenTelemetry, FinOps por etiquetas de job); véase el registro de cambios y `ADVANCED.md`.

## Siguiente

Lo que la 1.6.4 no alcanzó, y por qué:

- **Varios propietarios en un proceso y en una página**: desde la 1.7.0 cada cuenta es un monitor propio y la página las muestra una al lado de otra, pero dentro de un monitor un repositorio sigue identificándose solo por su nombre, así que dos propietarios en el mismo monitor se mezclarían. Llevarlos a un solo proceso exige el propietario en cada identificador (las lecturas, los identificadores de alerta, las listas de los ajustes, los centinelas y la página); no se pudo demostrar sin repositorios de dos propietarios reales, así que las cuentas de la 1.7.0 siguen siendo la forma de mantenerlos separados.
- **El informe de facturación con un login que pueda leerlo**: la respuesta real de un login sin el permiso `user` es «no encontrado» y el monitor vuelve a la estimación (comprobado); las cifras en sí no se han comparado con una cuenta de facturación.
- **Los precios de los runners grandes** de `quotas.json` salen de la memoria de la lista pública de precios y están marcados como no verificados; compáralos con la página de facturación de GitHub y edita el fichero.
- **`gh copilot`**: sus banderas se comprueban con `gh copilot -- --help`, que necesita la línea de comandos de Copilot; aquí no está instalada, así que siguen sin verificar.
- **Notificaciones, webhook, Enterprise Server y los ejemplos de servicio** contra servicios reales: `tools/manual_check_live.py` los comprueba a mano; necesitan tus canales y equipos, así que no se ejecutaron aquí.
- **La aplicación de terminal** edita los ajustes sencillos, las listas y los mapas de números y muestra el estado de la IA; la explicación de un workflow en rojo concreto se queda en la página.
- **Solo el propietario puede demostrarlo en una instalación real**: varias cuentas con el centinela Collab sobre repositorios reales, una GitHub App y una segunda cuenta de solo lectura con claves reales, y el proxy HTTPS con un certificado real. Se prueban a mano (`tools/manual_check_live.py`) y no se dan por hechos.
- **Una comprobación de versión nueva que descargue o instale**: nunca; el monitor solo avisa.

## Más adelante

- **Telemetría de hardware de los runners** mediante un agente: hoy solo se lee un punto de acceso opcional de node exporter.
- **Una cuarta fase** (plugins, automatización más amplia, IA avanzada) solo tras varias semanas de 2.0.x estable y una decisión explícita.

## Ideas que necesitan una decisión antes

- Una versión en PDF de los informes programados (hoy HTML y Markdown).
- Una vista de las versiones listas o bloqueadas, una por repositorio, en la pestaña Equipo.
