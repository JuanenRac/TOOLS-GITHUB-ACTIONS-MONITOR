# Hoja de ruta

Ideas que no cupieron en la versión actual, sin orden prometido. Son direcciones, no compromisos; un issue o un pull request es la mejor forma de adelantar una.

## En la 1.8.0 (la próxima versión)

Todo lo que sigue está escrito y probado; o ya está en la rama principal o espera en una pull request. Nada se da por demostrado con servicios reales (véase «Siguiente»).

### Ya en la rama principal

- Una nueva organización de carpetas (el paquete en `src/`, la página, los ejemplos y los idiomas en `assets/`), con una herramienta de migración que mueve una instalación plana antigua sin borrar nada.
- Una capa de almacenamiento tras una sola interfaz, con el soporte de ficheros que mantiene la disposición de `accounts/<id>/`, escrituras atómicas y copias de seguridad que cualquier soporte puede restaurar.
- Un soporte SQLite opcional (apagado por defecto), una base por cuenta, migraciones con versión, un tiempo de espera ajustable y herramientas para pasar el estado entre el soporte de ficheros y SQLite en ambos sentidos, con una simulación previa.
- El historial de cambios está traducido a los ocho idiomas hasta la 1.0.0 y una prueba lo mantiene completo.
- Retención y rotación del historial (eventos y analíticas durante un número de días, borrar o archivar, una línea de auditoría por pasada, aviso de tamaño en el doctor; el estado de los centinelas y la configuración nunca se tocan).

### Terminado y a la espera de fusionarse

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

### Aún en cierre

- Silencios que recuerdan quién los puso (necesita el modo equipo).

## Previsto, en este orden

Cada versión lleva todo lo de su tramo del plan: nada queda colgando de una versión anterior ni se aplaza a la siguiente. Tras la 1.8.3 y tras la 1.9.3 el producto pasa por una revisión independiente y sus hallazgos se cierran en la versión de estabilización siguiente. La 1.8.1 es una versión correctiva de la 1.8.0: el cuadro «cargando repositorios» desaparece con el último repositorio y recargar la página trae los datos al instante.

### 1.8.2 - Imagen Docker oficial y modo servicio

Una imagen de varias etapas con usuario sin privilegios, volúmenes para datos y configuración, variables de entorno documentadas, un ejemplo de compose con proxy inverso y TLS opcionales, una unidad de systemd para quien prefiera la instalación clásica y una comprobación de salud profunda que falla si el supervisor o el ciclo de una cuenta están atascados. Una credencial que GitHub revoca o deja caducar marca solo esa cuenta como ciega, lanza una alerta crítica de sistema y se puede sustituir sin reiniciar el supervisor. Copia de seguridad, actualización y primer arranque como servicio quedan documentados; la página dice si escucha en este equipo, en la red o detrás de un proxy; la línea de comandos funciona contra un monitor remoto. La edición lite sigue siendo local. Además: un informe del tiempo que esperan los trabajos en cola por cada runner.

### 1.8.3 - Notificaciones por usuario

Preferencias por usuario (canal, centinela, nivel mínimo), un despachador que decide a quién avisar según las preferencias y los roles, canales como complementos sencillos y resúmenes de las alertas aún no leídas. Además: un trabajo omitido por las rutas que vigila se muestra aparte de un trabajo en rojo.

### 1.8.4 - Estabilización

Sin grandes funciones. Aislamiento entre cuentas, la página, el almacenamiento, acceso y roles, notificaciones, un GitHub que falla a ratos, el arranque tras una migración interrumpida, la recuperación tras un corte, un doctor más amplio, los sitios que escriben en GitHub, registros sin tokens, una lista de comprobación de seguridad del modo equipo y documentos que coinciden con el comportamiento. La serie sigue hasta la 1.8.9 solo si hace falta.

### 1.9.0 - Una puntuación

Recolectores de métricas por cuenta y por centinela (tasa de éxito, duración, tiempo de recuperación, rendimiento), un motor de puntuación con umbrales que puedes cambiar, tendencia frente al periodo anterior, instantáneas guardadas en el almacenamiento, un widget de puntuación con minigráfica, alertas cuando la puntuación baja y un verbo de la línea de comandos que la imprime.

### 1.9.1 - Centinela de seguridad

El tercer centinela: Dependabot, análisis de código, análisis de secretos, protección de ramas, permisos de los workflows y propietarios del código, con reglas por tipo de señal, el mismo filtro en la pestaña Alertas y una penalización en la puntuación por alertas críticas abiertas. Opcional, en la misma versión: higiene de workflows (acciones que no están fijadas a un commit, trabajos sin límite de tiempo, workflows sin permisos o sin concurrencia, uso peligroso de pull_request_target), sobre el comprobador de workflows que el proyecto ya tiene.

### 1.9.2 - Salud del repositorio y del equipo

Una vista de salud de cada repositorio (CI, incidencias y pull requests, seguridad, preparación para una versión, actividad) y una del equipo con clasificación, totales y filtros; páginas para ambas con enlaces directos para pantallas de pared. Opcional, en la misma versión: un panel de benchmarks nocturnos frente a un presupuesto (mediana frente a una referencia por clase de máquina) y un panel de listas de materiales de software y atestaciones de cada versión.

### 1.9.3 - Informes programados y registro de auditoría

Plantillas de informe en HTML y Markdown (PDF opcional) con la puntuación, las alertas principales y los cambios, un planificador y un registro de auditoría de solo añadir con quién hizo qué y cuándo, sin ningún secreto dentro. Opcional, en la misma versión: una vista «versión lista / bloqueada» con el último commit en verde de cada repositorio.

### 1.9.4 - Estabilización de la tercera fase

El mismo tipo de cierre que la 1.8.4 para la puntuación, el centinela de seguridad, las vistas de salud, los informes y el registro de auditoría; el coste en llamadas a la API con tres centinelas en marcha; una puntuación que se mantiene coherente cuando un centinela está apagado.

### 2.0.0 - Madurez

Una versión mayor que limpia la deuda técnica y congela las interfaces públicas: centinelas, almacenamiento, alertas, el esquema de eventos y la API de lectura, con una suite de pruebas de contrato que los clientes pueden ejecutar contra cualquier versión. Una guía para cada forma de usar el producto (lite, individual, servicio, equipo) y una referencia de ajustes, eventos, métricas y API. De la 2.0.1 en adelante hay un colchón para lo que solo aparece con un uso real prolongado.

Los workflows del propio monitor cumplen lo que el centinela de higiene pedirá a los demás: acciones fijadas a un commit, los permisos mínimos y un límite de tiempo en cada trabajo.

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

Una barra al pie de la página con el aviso más importante (y una ventana con todos), la conexión, la cuota, la última lectura, el modo, la dirección y el reloj; un botón de pantalla completa; tablas de Repositorios e Historial que se ordenan por una o varias columnas con las columnas que elijas; `monitor_cli.py`, la línea de comandos como cliente del monitor en marcha (`status`, `health`, `alerts`, `accounts`, `live`, `doctor`) con `--json` y códigos de salida estables, y su guía en ocho idiomas; los registros de cambios comprobados en orden, el README del paquete sin historial dentro y los dibujos hechos de nuevo.

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

- **Más adaptadores de notificación**: ntfy, Microsoft Teams y correo mediante un relé local.
- **Varias cuentas en una página**: hecho en la 1.7.0, cada cuenta en su propio monitor bajo un supervisor.
- **Telemetría de hardware de los runners** mediante un agente: hoy solo se lee un endpoint opcional de node exporter.

## Ideas que necesitan una decisión antes

- Leer en la página los registros de un paso fallido, con la misma limpieza que aplica el asistente de IA.
