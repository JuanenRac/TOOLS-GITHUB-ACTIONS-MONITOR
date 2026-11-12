# Hoja de ruta

Ideas que no cupieron en la versión actual, sin orden prometido. Son direcciones, no compromisos; un issue o un pull request es la mejor forma de adelantar una.

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

- **Decidido, no hecho en la 1.6.6**: el aviso activo a una IA externa (apagado por defecto, una primera confirmación por proveedor, solo los campos ya filtrados de la lista cerrada, un tope de llamadas y de coste por hora, la clave por el nombre de una variable de entorno, y la IA nunca ejecuta una acción) con su variante de comando saliente (lista cerrada, sin shell); y los repositorios de varios propietarios en una página (el monitor identifica un repositorio solo por su nombre, así que necesita el propietario en cada identificador; es la base de varias cuentas). Cada uno es una función con su diseño y sus pruebas, así que la 1.6.6 cerró primero las correcciones.
- **Las entradas antiguas del historial de cambios en los otros siete idiomas**: la Ayuda muestra el historial en cada idioma y de la 1.6.8 a la 1.6.3 están traducidas; la 1.6.2 y las anteriores conservan el texto en inglés bajo un aviso traducido y se irán traduciendo versión a versión, de la más nueva a la más vieja.
- **Varios propietarios en un proceso y en una página**: desde la 1.7.0 cada cuenta es un monitor propio y la página las muestra una al lado de otra, pero dentro de un monitor un repositorio se identifica solo por su nombre, así que dos propietarios en el mismo monitor se mezclarían. Las cuentas de la 1.7.0 son la manera de mantenerlos aparte; llevarlas a un solo proceso, con el propietario en cada identificador, es lo que queda.
- **El informe de facturación con un login que pueda leerlo**: la respuesta real de un login sin el permiso `user` es «no encontrado» y el monitor vuelve a la estimación (comprobado); las cifras en sí no se han comparado con una cuenta de facturación.
- **Los precios de los runners grandes** de `quotas.json` salen de la memoria de la lista pública de precios y están marcados como no verificados; compáralos con la página de facturación de GitHub y edita el fichero.
- **`gh copilot`**: sus banderas se comprueban con `gh copilot -- --help`, que necesita la línea de comandos de Copilot; aquí no está instalada, así que siguen sin verificar.
- **Notificaciones, webhook, Enterprise Server y los ejemplos de servicio** contra servicios reales: `tools/manual_check_live.py` los comprueba a mano; necesitan tus canales y equipos, así que no se ejecutaron aquí.
- **La aplicación de terminal** edita los ajustes sencillos y muestra el estado de la IA; la explicación de un workflow en rojo concreto y la edición de listas y mapas siguen en la página.
- **Una comprobación de versión nueva que descargue o instale**: nunca; el monitor solo avisa.

## Más adelante

- **Más adaptadores de notificación**: ntfy, Microsoft Teams y correo mediante un relé local.
- **Varias cuentas en una página**: hecho en la 1.7.0, cada cuenta en su propio monitor bajo un supervisor.
- **Telemetría de hardware de los runners** mediante un agente: hoy solo se lee un endpoint opcional de node exporter.

## Ideas que necesitan una decisión antes

- Una pantalla de acceso para la página, de modo que el modo red no requiera escribir una vez el token de acceso. Hoy la respuesta es el token de acceso y, para Internet, un proxy inverso con autenticación (véase `monitor/docs/DEPLOYMENT.md`).
- Leer en la página los registros de un paso fallido, con la misma limpieza que aplica el asistente de IA.
