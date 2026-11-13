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

Seguridad: el monitor nunca lee, copia, imprime ni registra la clave; pasa su ruta a `openssl`, que firma un JWT de diez minutos como máximo. El token de instalación dura una hora, se queda en memoria y se renueva cinco minutos antes. **Solo las lecturas** lo usan; las escrituras y acciones mantienen tu token. Si la App falla o le falta un permiso, la lectura se repite con tu token. La página muestra las dos cuotas.

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

La segunda cuenta (`extra_reader.enabled`, `extra_reader.file`) es una cuenta de solo lectura cuyo token de acceso fino está en un fichero de texto fuera de cualquier repositorio, legible solo por ti; el ajuste guarda SOLO la ruta de ese fichero. El monitor lee el token en el momento de usarlo, lo guarda en memoria y nunca lo almacena, imprime ni registra. Las lecturas se reparten entre tu sesión, la App y la segunda cuenta según las llamadas que le quedan a cada una (la cifra de la llamada gratuita `rate_limit`, menos las lecturas hechas desde entonces); una fuente que se rechaza se deja fuera cinco minutos y la lectura se repite con la siguiente. Las escrituras y acciones nunca la usan. Es para una cuenta tuya (por ejemplo una segunda cuenta propia con acceso de lectura a los repositorios), no una forma de esquivar el límite con cuentas de otras personas.
