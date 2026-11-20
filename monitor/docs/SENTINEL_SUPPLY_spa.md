<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_SUPPLY.md) | **🇪🇸 Español** | [🇫🇷 Français](SENTINEL_SUPPLY_fra.md) | [🇮🇹 Italiano](SENTINEL_SUPPLY_ita.md) | [🇩🇪 Deutsch](SENTINEL_SUPPLY_deu.md) | [🇨🇳 简体中文](SENTINEL_SUPPLY_zho.md) | [🇯🇵 日本語](SENTINEL_SUPPLY_jpn.md) | [🇵🇹 Português](SENTINEL_SUPPLY_por.md)

# El centinela de cadena de suministro

El cuarto centinela, junto al de CI, Collab y Seguridad. Lee, sin escribir nada en GitHub, los ficheros de flujo de cada repositorio (`.github/workflows`, por la API, sin clonar) y avisa de lo que permite que una etiqueta movida o un extraño actúe con el token y el código del repositorio. Lo convierte en alertas de la pestaña Alertas (origen Cadena de suministro). Está en la edición Completa, apagado por defecto (`sentinels.supply.enabled`); Lite no tiene centinelas.

Tiene su propia entrada en el grupo Centinela del menú, **Centinela de cadena de suministro** (dirección `#sentinel-supply`), visible mientras el centinela está encendido: un panel con los hallazgos abiertos de cada repositorio, el estado de su ciclo y lo que no se pudo leer; el distintivo de la entrada cuenta los errores.

## Qué señala

| Señal | Alerta | Nivel | Activa por defecto |
|---|---|---|---|
| Un `uses:` de una acción o flujo reutilizable que no está fijado a un SHA de commit completo (su dueño puede mover la etiqueta) | `actions.supply.unpinned` | warning | sí |
| Un `uses:` que sigue una rama que se mueve sola (`@main`, `@master`...): peor que una etiqueta | `actions.supply.mutable_ref` | warning | sí |
| Un flujo con `permissions: write-all` | `actions.supply.permissions_wide` | warning | sí |
| Un flujo sin bloque `permissions:` (el token recibe el permiso por defecto, más amplio) | `actions.supply.permissions_missing` | warning | sí |
| `pull_request_target` junto con la descarga del código de la pull request | `actions.supply.pr_target_checkout` | error | sí |

Hay una alerta por repositorio y señal, con el número de hallazgos, los ficheros donde están y unos pocos ejemplos (el nombre de una acción) en sus detalles. Cada señal se puede apagar (`sentinels.supply.signals.<señal>.enabled`) y darle otro nivel (`info`, `warning`, `error`, `critical`). Un `uses:` de un flujo del mismo repositorio no es de terceros y se deja fuera.

## Una sola fuente de verdad

No tiene reglas propias: los hallazgos salen del linter de flujos (`bin/lint_workflows.py`, el mismo que usan la pestaña Centinela y la línea de comandos); aquí solo están activas `unpinned_uses`, `permissions` y `pr_target`, y las demás reglas quedan apagadas. En concreto, la regla que busca secretos escritos en un fichero está apagada, así que **el valor de un secreto nunca se lee, se guarda ni se muestra**. Los ajustes `lint.own_owners` y `lint.unpinned_own` siguen decidiendo cómo se trata una acción de tu propia cuenta, y un comentario `# monitor-lint: ignore REGLA` en un flujo silencia el hallazgo allí mismo.

## Un dueño para cada hallazgo

`security.workflow_write` (centinela de Seguridad) es el permiso por defecto del repositorio, un ajuste de GitHub; las señales de aquí tratan del contenido de cada fichero de flujo, así que un repositorio nunca levanta el mismo hallazgo desde los dos. El panel del lint de la pestaña Centinela sigue siendo un panel; las alertas de la pestaña Alertas sobre estas señales salen solo de aquí.

## Qué no pudo comprobar

Un repositorio cuyos flujos no se pueden leer (sin acceso, SSO no autorizado, cuota gastada, una carpeta con demasiados ficheros) **no** es una alerta y **no** es una señal de limpieza. Se lista en el estado bajo `unavailable`, con el motivo y cuántos repositorios son, y un nivel `ok` se muestra como `unknown` cuando la mayor parte de lo mirado no se pudo leer. Si un repositorio deja de responder mientras tiene alertas, estas se quedan una semana (marcadas `unread_since`) y nunca se anuncian como resueltas. Un repositorio sin carpeta `.github/workflows` se lee y simplemente no tiene nada que contar. Un repositorio cuyas lecturas siguen fallando espera 5 minutos, 30 minutos y luego 6 horas antes del siguiente intento.

## Coste

Una ronda lee como máximo `sentinels.supply.max_repos_per_tick` repositorios (10 por defecto) y hace como máximo `sentinels.supply.max_calls_per_tick` llamadas (60): una para listar los flujos de un repositorio y otra más por cada fichero nuevo o cambiado, porque un fichero cuyo SHA no cambió no se vuelve a leer. Van primero los leídos hace más tiempo y un poco antes los que tienen una alerta abierta; un ciclo cada `sentinels.supply.refresh_seconds` (una hora por defecto). El centinela se pausa mientras la cuota restante esté por debajo de `sentinels.supply.min_rate_remaining`. Su estado (`supply_state.json`) guarda las alertas abiertas, así que un reinicio no anuncia nada de nuevo, y la primera mirada a un repositorio no escribe ningún evento. `sentinels.supply.max_files_per_repo` limita los ficheros leídos en un repositorio; uno que lo supera se lee en parte y se cuenta como parcial. Una ronda también deja de empezar repositorios nuevos pasados `sentinels.supply.deadline_s` segundos (30 por defecto; 0 = sin tope): los que no se alcanzan esperan a la ronda siguiente y el estado los lista por nombre como `unchecked` (con `round_cut`) en lugar de contarlos como cero alertas.

Con `sentinels.supply.incremental` (desactivado por defecto), un repositorio cuyos ficheros de workflow (sus SHA de blob) y reglas son los mismos que en la última pasada buena no se vuelve a analizar y sus avisos se quedan exactamente como están: no mirar nunca cierra un aviso, y cambiar una regla, la lista de ignorados o la versión del programa hace que todos los repositorios se analicen de nuevo. El estado indica cuántos repositorios quedaron sin cambios (`unchanged`). Es una decisión para repositorios que conoces, no un valor heredado.

## Ignorar un hallazgo

`sentinels.supply.ignore` admite patrones `repositorio:fichero:regla` (con `*` para cualquiera) que nombran la regla del linter, por ejemplo `mirepo:release.yml:unpinned_uses`; ten en cuenta que `unpinned_uses` es la regla detrás de `unpinned` y de `mutable_ref`, y `permissions` la de las dos señales de permisos. Los patrones de `lint.ignore` no se aplican aquí.

## Eventos, notificaciones y puntuación

Un hallazgo nuevo escribe el evento `security_new` y uno cerrado `security_fixed` (el evento dice `sentinel: supply` y el código de la alerta), de modo que la casilla Seguridad de las preferencias de notificación de cada usuario y los canales deciden quién se entera. No se anuncia nada la primera vez que se mira un repositorio. Las métricas llevan `supply_alerts`, `supply_findings`, `supply_penalty` (informativa: `sentinels.supply.penalty.per_finding`, 2, y `cap_per_repo`, 10, se leen del fichero), `supply_repos_checked`, `supply_repos_unreadable` y `supply_calls_last_hour`. La puntuación no usa la penalización. La API responde `GET /api/sentinel/supply` y la pestaña Alertas y `monitor_cli.py alerts --sentinel supply` filtran por él.

## Los ajustes

En la página de Ajustes, subpestaña Centinela, bloque Cadena de suministro: `sentinels.supply.enabled`, `sentinels.supply.incremental`, `sentinels.supply.refresh_seconds`, `sentinels.supply.max_repos_per_tick`, `sentinels.supply.max_calls_per_tick`, `sentinels.supply.max_files_per_repo`, `sentinels.supply.min_rate_remaining`, `sentinels.supply.repos`, `sentinels.supply.ignore`, `sentinels.supply.signals.unpinned.enabled`, `sentinels.supply.signals.unpinned.level`, `sentinels.supply.signals.mutable_ref.enabled`, `sentinels.supply.signals.mutable_ref.level`, `sentinels.supply.signals.permissions_wide.enabled`, `sentinels.supply.signals.permissions_wide.level`, `sentinels.supply.signals.permissions_missing.enabled`, `sentinels.supply.signals.permissions_missing.level`, `sentinels.supply.signals.pr_target_checkout.enabled`, `sentinels.supply.signals.pr_target_checkout.level`.

## Qué no hace

No escribe en GitHub (ni pull requests, ni etiquetas, ni incidencias), no propone el SHA al que fijar una acción y no lee el valor de ningún secreto.
