<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](QUOTA.md) | **🇪🇸 Español** | [🇫🇷 Français](QUOTA_fra.md) | [🇮🇹 Italiano](QUOTA_ita.md) | [🇩🇪 Deutsch](QUOTA_deu.md) | [🇨🇳 简体中文](QUOTA_zho.md) | [🇯🇵 日本語](QUOTA_jpn.md) | [🇵🇹 Português](QUOTA_por.md)

# Más cuota, menos gasto

GitHub da a cada cuenta una **cuota limitada de llamadas a la API**, compartida por todas las herramientas que la usan. Esta guía explica cómo funciona y todas las vías que tiene el monitor para gastar menos.

## Cómo funciona la cuota
- **REST**: 5000 llamadas por hora por usuario (60 sin sesión). **GraphQL** tiene la suya, aparte. El `GITHUB_TOKEN` de un workflow en Actions también tiene la suya. Una **GitHub App** tiene una cuota propia, separada de la tuya, que crece con los repositorios en los que está instalada (unas 10 000 por hora con 130 repositorios).
- Qué cuenta y qué no: una lectura condicional que responde `304 Not Modified` (ETag) no cuenta; pedir `rate_limit` es gratis; `git push`, `git fetch` y `git clone` no usan la API.

## Las vías con las que el monitor ahorra
1. **Lecturas condicionales** (ETag y `304`): `cache.etag.enabled` (activado por defecto); la página muestra cuántas lecturas se ahorraron.
2. **Modo Bajo**: solo los repositorios calientes cada 4 minutos, el resto cada 30; `modes.auto_low` (activado) entra con menos de 1000 llamadas y vuelve por encima de 2500 o en la renovación; presets en `modes.low`. La barra dice que las cifras pueden ser antiguas, y cuánto.
3. **Panel central como línea base**: `central.source` (`off`, `git`, `http`) lee `data/sentinel.json` de tu repositorio de perfil, que refresca un workflow con su propio token; no gasta nada de tu cuota. `central.max_age_minutes` (120): más viejo que eso está "atrasado" y no se fía.
4. **Un solo aviso cuando se agota la cuota**: las lecturas se paran hasta la renovación, la página dice una vez "cuota agotada hasta las HH:MM" (no un error por repositorio) y se reanudan solas.
5. **Una GitHub App para las lecturas** (`github_app.*`), más abajo.
6. **GraphQL para los repositorios tranquilos (opcional, desactivado por defecto)**: `network.graphql_checks` lee por lotes (`network.graphql_batch`, 20 por defecto) los repositorios que no están calientes mediante GraphQL, que tiene una cuota propia; una llamada sustituye a muchas llamadas REST. Solo ve el último commit de la rama por defecto (un workflow que no corrió en él no aparece) y no da duraciones, intentos ni otras ramas, así que los repositorios calientes y cualquiera que GraphQL no responda se siguen leyendo por REST en el mismo ciclo. La contabilidad (lotes, repositorios, puntos, repositorios que pasaron a REST) está en el resumen y en el estado para las herramientas de IA.

## Una GitHub App, paso a paso
1. En GitHub, *Settings*, *Developer settings*, *GitHub Apps*, *New GitHub App*. Sin webhook. Permisos **de solo lectura**: Actions, Checks, Code scanning alerts, Commit statuses, Contents, Dependabot alerts, Issues, Pull requests, Secret scanning alerts y Metadata.
2. *Generate a private key* y guarda el `.pem` **fuera de cualquier repositorio**, legible solo por ti.
3. *Install App* en tu cuenta, en todos los repositorios que quieras vigilar.
4. En el monitor: `github_app.enabled` activado, `github_app.app_id` (el número de la App) y `github_app.key_path` (solo la RUTA de la clave). `github_app.installation_id` puede quedar vacío.
5. Compruébalo con `GET /api/github-app/status` (solo desde este equipo): muestra el nombre, la instalación, los permisos concedidos y la cuota de la App, nunca la clave ni un token. El doctor comprueba `openssl`, el fichero de la clave y sus permisos.

Seguridad: el monitor lee la clave en memoria solo para firmar un JWT de diez minutos como máximo (con la biblioteca estándar, sin necesitar `openssl`; `openssl` es solo el respaldo) y nunca la copia, imprime ni registra. El token de instalación dura una hora, se queda en memoria y se renueva cinco minutos antes. **Solo las lecturas** lo usan; las escrituras y acciones mantienen tu token. Si la App falla o le falta un permiso, la lectura se repite con tu token. La página muestra las dos cuotas.

## Cuando varias herramientas comparten la misma cuota
Todas las herramientas de la cuenta gastan las mismas 5000 llamadas por hora. Un buen patrón: un pequeño envoltorio de `gh` con una **caché compartida** de un par de minutos, una **reserva** (se niega a llamar cuando quedan menos de unas 1000, salvo lo urgente), el trabajo que necesita datos frescos **justo tras la renovación**, y nunca `gh run watch` (sondea). Por ejemplo, un envoltorio que guarda la respuesta de cada lectura en un fichero temporal con el nombre del comando y la sirve de nuevo durante 120 segundos, y comprueba `gh api rate_limit` antes de cualquier otra llamada.

## Qué NO hacer
No uses varias cuentas ni varios tokens del mismo usuario para esquivar el límite: va contra las normas de GitHub y puede bloquear la cuenta. Usa una App, el panel central y el modo Bajo.

## Ajustes
| Ajuste | Defecto |
|---|---|
| `cache.etag.enabled` | activado |
| `modes.auto_low` / `modes.auto_low_enter` / `modes.auto_low_exit` | activado / 1000 / 2500 |
| `modes.low.*` (`refresh_seconds`, `cold_refresh_seconds`, `runs_per_repo`, `hot_hours`) | 240 / 1800 / 10 / 2 |
| `min_rate_remaining` | 800 |
| `central.source` / `central.max_age_minutes` | off / 120 |
| `github_app.enabled` / `github_app.app_id` / `github_app.key_path` / `github_app.installation_id` | off / vacío / vacío / vacío |

## Solución de problemas y FAQ
- *"cuota agotada hasta las HH:MM"*: espera; el monitor se reanuda solo. Puede que otras herramientas la estén gastando: mira las suyas.
- *Las cifras son antiguas*: el modo Bajo está activo (elegido o automático); la barra lo dice.
- *La App no funciona*: mira `/api/github-app/status` y el doctor: openssl, la ruta de la clave, los permisos.
- *¿Cuesta cuota `git fetch`?* No. Véase también [QUOTAS_spa.md](QUOTAS_spa.md) (planes y minutos) y [MODES_spa.md](MODES_spa.md).

## La pestaña Cuota y una segunda cuenta
Todo lo de la cuota está en un solo sitio: *Ajustes*, pestaña *Cuota*. Reúne los modos (`modes.auto_low`, `modes.auto_low_enter`, `modes.auto_low_exit` y los valores de Bajo en `modes.low.*`), el ahorro (`network.etag`, junto con `cache.etag.enabled`), el panel central (`central.source`, `central.max_age_minutes`), la GitHub App (`github_app.*`) y una **segunda cuenta para las lecturas**. Los botones de la pestaña muestran la cuota de cada fuente (tu sesión, la App, la segunda cuenta) con la hora de renovación, prueban la App y la segunda cuenta, listan los permisos que le faltan a la App y aplican los valores recomendados o los defectos.

La segunda cuenta (`extra_reader.enabled`, `extra_reader.file`) es una cuenta de solo lectura cuyo token de acceso fino está en un fichero de texto fuera de cualquier repositorio, legible solo por ti; el ajuste guarda SOLO la ruta de ese fichero. El monitor lee el token en el momento de usarlo, lo guarda en memoria y nunca lo almacena, imprime ni registra. Las lecturas se reparten entre tu sesión, la App y la segunda cuenta según las llamadas que le quedan a cada una (la cifra de la llamada gratuita `rate_limit`, menos las lecturas hechas desde entonces); una fuente que se rechaza se deja fuera cinco minutos y la lectura se repite con la siguiente. Las escrituras y acciones nunca la usan. Es para una cuenta tuya (por ejemplo una segunda cuenta propia con acceso de lectura a los repositorios), no una forma de esquivar el límite con cuentas de otras personas. El archivo debe estar dentro de la carpeta de cuentas del monitor (`accounts/`, o la carpeta que indique `MONITOR_ACCOUNTS_DIR`) y nunca se lee a través de un enlace; `extra_reader.any_folder` (apagado por defecto) levanta la regla de la carpeta. Lo que depende de quién pregunta (tu cuenta, sus organizaciones, las notificaciones, una búsqueda de `@me`, `gh auth`, `gh repo list` sin propietario) lo contesta siempre tu propio login, y solo se reparte entre las fuentes una lectura simple `gh api ENDPOINT` (con, como mucho, las opciones `--jq`, `--paginate`, `-H`, `-i` y `--cache`): cualquier otra llamada va a tu login.

## El programa openssl y un monitor por puerto

El monitor busca `openssl` en el PATH y, si no está, donde lo guarda Git for Windows (`Git\usr\bin`, `Git\mingw64\bin` en Archivos de programa y en los Programas del usuario) y en las carpetas habituales de macOS y Linux, de modo que un monitor lanzado desde un `.bat` o un servicio lo encuentra. `github_app.openssl_path` (ruta absoluta al programa) permite elegir uno a mano. `/api/github-app/status` muestra `openssl` y `openssl_path`, y el doctor dice cuál firma cuando no es el del PATH.

En Windows el puerto del monitor se abre en exclusiva (SO_EXCLUSIVEADDRUSE): dos procesos ya no pueden escuchar en el 8765 a la vez. Y un monitor que arranca mientras otro monitor ya responde en su puerto lo dice y se detiene en vez de buscar otro puerto.

## Reparto de la cuota: fuente preferida y reserva

Por defecto cada lectura va a la fuente (usuario, GitHub App, segunda cuenta) con más llamadas libres. El bloque `readpool` lo cambia, en la pestaña Cuota de los ajustes, con los valores conservadores de siempre (`auto`, reserva 0):

- `readpool.prefer.<tipo>` (`auto`, `user`, `app`, `extra`): la fuente que responde primero a un TIPO de lectura. Los tipos los da la propia llamada: `runs` (ejecuciones, workflows, checks), `security` (code scanning, Dependabot, secret scanning), `issues` (issues y pull requests), `history` (versiones, commits, etiquetas, contenido), `discovery` (organizaciones, búsqueda, listas de repositorios) y `other`. Si la fuente preferida falla o está bajo su reserva, responden las demás, el usuario la última.
- `readpool.reserve.<fuente>` (0 a 4000): llamadas que se dejan libres en esa fuente. Mientras una fuente tenga como mucho las llamadas de su reserva, el monitor no lee con ella si otra puede. Usa `readpool.reserve.user` para dejar llamadas al `gh` de tus herramientas y agentes.
- `quota.failover` (desactivada por defecto): una lectura que responde 429 o «rate limit exceeded» se repite una vez con otra fuente que pueda leer, y la fuente que se agotó cuenta como gastada hasta su próxima comprobación gratuita. Cuando todas las fuentes están gastadas se muestra la última copia buena de esa lectura con su edad en vez de un error (`quota.failover_max_age_minutes`, 60 por defecto, de 1 a 1440; una copia más antigua no se muestra). Un límite nunca se toma por una negativa de permiso, una escritura nunca cambia de fuente y `GET /api/quota-pool/status` tiene el bloque `failover` con cuántas veces actuó.

Las escrituras y acciones usan siempre el token del usuario. La barra de cuota y los modos de trabajo (rápido y turbo) cuentan la SUMA de todas las fuentes: el recuadro muestra la suma y su ayuda emergente la cifra de cada fuente, y la pestaña Cuota (Estado) añade una línea con el total junto a la cuota del usuario, la App y la segunda cuenta.

## Leer menos: el webhook primero y las fuentes gratuitas

Las dos vías están **desactivadas por defecto** y solo afectan a los repositorios tranquilos (aquellos cuyas últimas ejecuciones han terminado y están en verde). Un repositorio en ejecución, en rojo o tocado por un evento se lee como siempre.

- `savings.webhook_first`: mientras el webhook entrante está vivo (entregó un evento en los últimos `savings.webhook_window_minutes`), un repositorio tranquilo no se lee en su turno lento: GitHub avisa cuando pasa algo. Aun así se lee completo cada `savings.webhook_full_minutes`. Sin un webhook vivo no cambia nada.
- `savings.webhook_live_per_repo`: hace que "vivo" sea cosa de cada repositorio. Solo un repositorio tranquilo cuyos eventos PROPIOS llegaron en los últimos `savings.webhook_window_minutes` se salta su lectura lenta; uno cuyo webhook nunca se montó, o se rompió, se lee como siempre mientras los demás se ahorran. Ahorra menos lecturas, y el panel del Webhook cuenta los repositorios que están vivos por sí mismos. Apagado por defecto; funciona junto con `savings.webhook_first`.
- `savings.feeds.enabled`: antes de leer con la API un repositorio tranquilo, se pregunta el último commit de su rama por defecto a una fuente que no gasta cuota - el feed Atom público de los commits, `git ls-remote`, o cualquiera de los dos (`savings.feeds.method`: `atom`, `git`, `auto`). Si es el commit de la última lectura completa, el repositorio se deja como está. Cada `savings.feeds.max_age_minutes` se lee completo de todos modos. Solo repositorios públicos: con uno privado, un error o una respuesta rara, el repositorio se lee con la API como siempre. Solo salen del equipo peticiones GET a github.com, nunca una contraseña, y no se escribe nada. No se usa si el monitor está aislado de la red (air-gapped).

Lo que cuesta: una ejecución que empieza sin un push (una programación, una repetición) en un repositorio tranquilo se ve en la siguiente lectura completa, no al instante. La pestaña Cuota (Estado) muestra las lecturas que ha ahorrado cada vía desde que arrancó el monitor (cerca de una llamada de la API cada una): lecturas condicionales, GraphQL, webhook primero, feed Atom, git y panel central.

## Cuentas grandes: qué cubre la lista de ejecuciones, y un presupuesto

Un repositorio que lanza cientos de ejecuciones por hora llena en minutos una lista de 20-100 ejecuciones, así que un fallo más antiguo o un workflow que corre poco simplemente no está en ella. El monitor lo dice en vez de verse verde:

- **Cobertura**: la tabla de repositorios muestra hasta cuándo llega cada lista. Una lista llena que remonta menos de `sampling.min_coverage_minutes` se marca como *cobertura baja*; una lista más corta de lo pedido es *completa* (tiene todo el historial); un total de 2.500 o 40.000 es donde GitHub deja de contar, por eso se muestra como *al menos*. El bloque `sampling` de `GET /api/data` lleva las mismas cifras.
- **Segunda mirada**: con `sampling.default_branch_probe` activada, una lista llena pide además los push a la rama por defecto (sin pull requests), una petición más por lectura, para que las ejecuciones que deciden el rojo en main no las desplacen los pull requests ni las programadas.
- **Mirar las ejecuciones en curso**: con `sampling.active_probe` activada, una lista llena pide también, en dos peticiones ligeras, las ejecuciones aún `in_progress` y las `queued`, para que una ejecución larga que empezó antes de la ventana de la lista no se pierda ni se muestre como terminada. Dos peticiones más por repositorio lleno y lectura; desactivada por defecto.
- **A2 de una vez**: a un repositorio con `sentinel.a2_resolve_batch_min` o más workflows por consultar se le piden una sola vez sus ejecuciones completadas más recientes de la rama por defecto (`sentinel.a2_resolve_batch_pages` páginas de 100 como máximo) y se resuelven juntos; lo que esa lista no muestra se pregunta de uno en uno. Con 100 o más workflows tarda unos pocos ciclos en vez de cuatro workflows por ciclo.
- **Presupuesto**: `sampling.api_budget_per_hour` (0 = ninguno) limita las peticiones de listas de ejecuciones en una hora. Al superarlo se leen primero los repositorios con un workflow en rojo, siempre se reserva una décima parte del presupuesto para ellos y el resto espera; la página dice cuántos. La estimación de peticiones por hora para el número de repositorios y los intervalos se muestra a partir de 3.500 (GitHub permite 5.000 por hora), o siempre que haya presupuesto.

Los valores por defecto no cambian nada en una cuenta con pocos repositorios: la segunda mirada y el presupuesto están desactivados, y la marca de cobertura baja solo aparece cuando una lista llena remonta menos de media hora.

## Cuando la App está activada y no se usa

Si `github_app.enabled` está activado pero la App no puede dar un token, las lecturas siguen con tu token y la cuota es la menor del usuario. Nunca es en silencio: el doctor pasa a ámbar con la causa, un fallo se anota una vez en la lista de fallos tragados y la pestaña Cuota muestra una línea `GitHub App` con la causa y el límite en uso. Las causas: la clave no se puede leer o no es una clave RSA sin contraseña (`key_unreadable`), la clave no pudo firmar (`sign_failed`), la App no está instalada en la cuenta (`app_not_installed`), GitHub rechazó el token (`token_refused`) y la App está activada sin su número o su fichero de clave (`not_configured`). La misma nota está en `GET /api/quota` como `app` y en `GET /api/github-app/status` como `signer` y `code`.
