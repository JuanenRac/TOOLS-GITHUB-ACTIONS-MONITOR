# Hoja de ruta

Ideas que no cupieron en la versión actual, sin orden prometido. Son direcciones, no compromisos; un issue o un pull request es la mejor forma de adelantar una.

## Hecho en la 1.6.6

Correcciones tras la 1.6.5: el modo red funciona ya con HTTPS desde la página (la guarda de origen sigue el esquema de la sesión), todo ajuste que el esquema marca como seguro solo se cambia desde el propio equipo, `act` libera su ejecución tras Stop y cierra su tubería, una barra roja en Ajustes cuando el modo red escucha en todas las interfaces, la sesión puede abrirse por POST en lugar de por la dirección, un contador de fallos tragados en `--doctor` y Acerca de, `tools/make_screenshots.py` dice lo que hace y las imágenes se han vuelto a tomar, y el historial de cambios está traducido a ocho idiomas.

## Hecho en la 1.6.5

Una versión de integridad y seguridad, sin funciones grandes nuevas: un commit en verde exige el workflow obligatorio del repositorio, un fetch fallido detiene el despacho, el catálogo no puede nombrar una herramienta fuera de la carpeta de herramientas ni cambiar `dry_run`/`ref`, y un lote sin comprobación de commit registrada ya no se ofrece para firmar; `act` se queda dentro del espacio de trabajo y Stop termina todo el árbol de procesos y los contenedores de la ejecución; el modo red puede servir HTTPS, bloquea los tokens erróneos y solo acepta IPv4; el webhook rechaza reenvíos e inundaciones; el servidor MCP sobrevive a mensajes mal formados; `max_per_hour` cuenta mensajes; los ajustes se guardan bajo un bloqueo; el token guardado llega solo a `gh`; `--doctor` avisa de combinaciones peligrosas; la prueba de instalación limpia es una etapa propia del control de calidad de la publicación.

## Hecho en la 1.6.4

Pruebas de aislamiento de la edición lite y de la demo, ninguna petición de red cuando la comprobación de versión está apagada o la instalación está aislada, un README que empieza por la elección del lanzador, `--doctor --json`, una barra persistente para el modo red, la Ayuda y sus documentos en ocho idiomas, y las funciones opcionales (modo red, un token guardado por el monitor, acciones sobre GitHub, `act`, copia local de artefactos, runners propios, OpenTelemetry, FinOps por etiquetas de job); véase el registro de cambios y `ADVANCED.md`.

## Siguiente

Lo que la 1.6.4 no alcanzó, y por qué:

- **Decidido, no hecho en la 1.6.6**: el aviso activo a una IA externa (apagado por defecto, una primera confirmación por proveedor, solo los campos ya filtrados de la lista cerrada, un tope de llamadas y de coste por hora, la clave por el nombre de una variable de entorno, y la IA nunca ejecuta una acción) con su variante de comando saliente (lista cerrada, sin shell); y los repositorios de varios propietarios en una página (el monitor identifica un repositorio solo por su nombre, así que necesita el propietario en cada identificador; es la base de varias cuentas). Cada uno es una función con su diseño y sus pruebas, así que la 1.6.6 cerró primero las correcciones.
- **Las entradas antiguas del historial de cambios en los otros siete idiomas**: desde la 1.6.6 la Ayuda muestra el historial en cada idioma, pero solo la entrada más nueva está traducida; las antiguas conservan el texto en inglés bajo un aviso traducido y se irán traduciendo versión a versión, de la más nueva a la más vieja.
- **HTTPS detrás de un proxy en el puerto por defecto**: la guarda compara `Host` y `Origin` con el puerto del monitor, así que un proxy en el puerto 443 que reenvía un `Host` sin puerto aún no está soportado; la página funciona con un puerto TLS directo o con un proxy que conserva el puerto.
- **Varios propietarios en una página**: el monitor identifica un repositorio solo por su nombre (ejecuciones, centinela, caché, exportaciones), así que dos propietarios con un repositorio del mismo nombre se mezclarían. Las organizaciones se listan y cada una se vigila con su propio monitor (`github_owner`). Hacerlo en una página exige poner el propietario en cada identificador.
- **El informe de facturación con un login que pueda leerlo**: la respuesta real de un login sin el permiso `user` es «no encontrado» y el monitor vuelve a la estimación (comprobado); las cifras en sí no se han comparado con una cuenta de facturación.
- **Los precios de los runners grandes** de `quotas.json` salen de la memoria de la lista pública de precios y están marcados como no verificados; compáralos con la página de facturación de GitHub y edita el fichero.
- **`gh copilot`**: sus banderas se comprueban con `gh copilot -- --help`, que necesita la línea de comandos de Copilot; aquí no está instalada, así que siguen sin verificar.
- **Notificaciones, webhook, Enterprise Server y los ejemplos de servicio** contra servicios reales: `tools/manual_check_live.py` los comprueba a mano; necesitan tus canales y equipos, así que no se ejecutaron aquí.
- **La aplicación de terminal** edita los ajustes sencillos y muestra el estado de la IA; la explicación de un workflow en rojo concreto y la edición de listas y mapas siguen en la página.
- **Una comprobación de versión nueva que descargue o instale**: nunca; el monitor solo avisa.

## Más adelante

- **Más adaptadores de notificación**: ntfy, Microsoft Teams y correo mediante un relé local.
- **Varias cuentas en una página**: hoy cada cuenta funciona con su propio monitor.
- **Telemetría de hardware de los runners** mediante un agente: hoy solo se lee un endpoint opcional de node exporter.

## Ideas que necesitan una decisión antes

- Una pantalla de acceso para la página, de modo que el modo red no requiera escribir una vez el token de acceso. Hoy la respuesta es el token de acceso y, para Internet, un proxy inverso con autenticación (véase `monitor/docs/DEPLOYMENT.md`).
- Leer en la página los registros de un paso fallido, con la misma limpieza que aplica el asistente de IA.
