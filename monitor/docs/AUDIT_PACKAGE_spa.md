<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AUDIT_PACKAGE.md) | **🇪🇸 Español** | [🇫🇷 Français](AUDIT_PACKAGE_fra.md) | [🇮🇹 Italiano](AUDIT_PACKAGE_ita.md) | [🇩🇪 Deutsch](AUDIT_PACKAGE_deu.md) | [🇨🇳 简体中文](AUDIT_PACKAGE_zho.md) | [🇯🇵 日本語](AUDIT_PACKAGE_jpn.md) | [🇵🇹 Português](AUDIT_PACKAGE_por.md)

# Paquete para el auditor

Lo que necesita un auditor para revisar el modo equipo, la exposición en red y el manejo de secretos de esta herramienta: una lista de comprobación, los hallazgos de revisiones anteriores con su arreglo y la prueba que lo mantiene arreglado, cómo ejecutar las pruebas y lo que se sabe que queda.

## Lista de comprobación de seguridad del modo equipo

- El modo equipo (`auth.enabled`) está apagado por defecto; actívalo solo tras HTTPS o un proxy de confianza (`listen.trusted_proxy`).
- Con el modo equipo y la red abiertos, el monitor no arranca antes de que exista el primer administrador.
- Hasta entonces solo entra el propio equipo (el primer administrador se crea allí).
- Los tokens para scripts (`auth.allow_bearer`) están apagados por defecto; una sesión necesita el token CSRF para escribir.
- El proceso de cada cuenta responde solo a su supervisor (una clave que recibe al arrancar).
- Ningún secreto se escribe en el registro ni en las respuestas de la API; el fichero de ajustes se guarda bajo un candado.
- Toda petición que sale del monitor (avisos, OpenTelemetry, exportadores de runners) obedece la misma regla: ninguna dirección privada ni redirección a una.

## Hallazgos, arreglos y pruebas

| Hallazgo | Arreglo | Prueba |
|---|---|---|
| Con el modo equipo y sin usuarios, todas las rutas estaban abiertas a la red | Solo entra el propio equipo hasta que existe el primer administrador, y el modo red no arranca sin uno | `test_184_audit_auth.py::FirstAdministratorWindow, test_185_bootstrap_start.py` |
| El proceso de una cuenta se saltaba las comprobaciones del modo equipo | Pide la clave de su supervisor en cada petición | `test_184_audit_auth.py::ChildAnswersOnlyToItsSupervisor` |
| Guardar los ajustes seguía sin el candado del fichero tras un tiempo de espera | El guardado se rechaza con un mensaje si el candado sigue tomado diez segundos | `test_184_audit_hardening.py::ConfigurationLock` |
| El comando del centinela podía ser un intérprete con argumentos | El comando es una lista cuya primera palabra es la ruta completa de un programa que no es un intérprete, sin caracteres de control | `test_184_audit_hardening.py::NotifyCommand` |
| Los tokens para scripts (bearer) estaban activos por defecto | Apagados por defecto; solo un true real los activa | `test_184_audit_hardening.py::ScriptTokens` |
| El feed para las IAs se compartía entre cuentas, y refresco, confirmación y tope de avisos podían adelantarse unos a otros | Un feed por cuenta; refresco, confirmación y estado toman un mismo candado; el tope se reserva en un paso con candado | `test_184_audit_feed.py (OneStepAtATime, CapOfTheNotices)` |
| La pausa del gancho de una herramienta de IA no se reservaba en un paso; un exportador de runner podía redirigir al monitor; las llamadas a GitHub que no vuelven se acumulaban | La pausa se guarda con candado; las redirecciones se comprueban y limitan; las llamadas abandonadas se cuentan y se acotan (`watchdog_max_abandoned`) | `test_184_audit_robustness.py (HookCooldown, Exporter, AbandonedCalls)` |
| Un nombre que acababa en salto de línea pasaba las comprobaciones de ids, repositorios y claves | Toda comprobación termina en el final del texto (`\Z`) | `test_184_audit_anchors.py` |
| La exportación OpenTelemetry no obedecía la regla de peticiones salientes; no se decía que el proxy es una frontera de confianza; el escapado de la página no tenía prueba | La exportación pasa por la misma guarda (sin dirección privada ni redirección); la frontera está documentada en la ayuda; una prueba mantiene escapado cada texto de la API | `test_184_audit_network.py (Collector, ProxyIsAFrontierOfTrust, PageEscaping)` |
| Dos monitores podían escuchar en un puerto; no se encontraba openssl de Git for Windows; los fallos tragados a propósito no dejaban rastro de su origen | El puerto se toma en exclusiva y un segundo monitor se niega a arrancar; openssl se busca donde lo guarda Git for Windows; cada fallo tragado escribe una línea con su tipo y lugar | `test_185_startup.py (OnePerPort, WhereIsOpenssl), test_185_degraded.py` |
| Las ejecuciones sin duración (leídas por GraphQL) hacían fallar al centinela en cada ciclo | Una duración ausente cuenta como cero | `test_186_unfinished_rows.py` |

## Cómo ejecutar las pruebas

Desde la carpeta `monitor/`: `python -m unittest discover -s tests`. Las pruebas no necesitan red ni token de GitHub. Las pruebas de navegador se ejecutan si hay Edge, Chrome o Chromium (o con `MONITOR_BROWSER_TESTS=1`). Los ficheros de la tabla están en `monitor/tests/`.

## Límites conocidos

- El proxy del entorno (`network.use_proxy`, apagado por defecto) resuelve los nombres por su cuenta: la comprobación del nombre ocurre antes. La garantía fuerte debe venir de la red (un cortafuegos que rechace direcciones privadas).
- Windows no puede hacer privado un fichero solo con permisos: los secretos se cifran con la clave del usuario donde el sistema lo ofrece.
- Las pruebas no demuestran nada sobre un GitHub real, un proxy real o un servidor de correo real: usan dobles locales.
