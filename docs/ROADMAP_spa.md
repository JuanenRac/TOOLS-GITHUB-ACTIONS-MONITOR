# Hoja de ruta

Ideas que no cupieron en la versión actual, sin orden prometido. Son direcciones, no compromisos; un issue o un pull request es la mejor forma de adelantar una.

## Hecho en la 1.6.4

Pruebas de aislamiento de la edición lite y de la demo, ninguna petición de red cuando la comprobación de versión está apagada o la instalación está aislada, un README que empieza por la elección del lanzador, `--doctor --json`, una barra persistente para el modo red, la Ayuda y sus documentos en ocho idiomas, y las funciones opcionales (modo red, un token guardado por el monitor, acciones sobre GitHub, `act`, copia local de artefactos, runners propios, OpenTelemetry, FinOps por etiquetas de job); véase el registro de cambios y `ADVANCED.md`.

## Siguiente

Lo que la 1.6.4 no alcanzó, y por qué:

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
