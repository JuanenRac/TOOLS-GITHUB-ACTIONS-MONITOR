<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_DELIVERY.md) | **🇪🇸 Español** | [🇫🇷 Français](SENTINEL_DELIVERY_fra.md) | [🇮🇹 Italiano](SENTINEL_DELIVERY_ita.md) | [🇩🇪 Deutsch](SENTINEL_DELIVERY_deu.md) | [🇨🇳 简体中文](SENTINEL_DELIVERY_zho.md) | [🇯🇵 日本語](SENTINEL_DELIVERY_jpn.md) | [🇵🇹 Português](SENTINEL_DELIVERY_por.md)

# El centinela de entrega

El quinto centinela, junto al de CI, Collab, Seguridad y Cadena de suministro. Lee, sin escribir nada en GitHub, las últimas versiones publicadas, las últimas etiquetas, el CHANGELOG y los ficheros de versión que indiques de cada repositorio (por la API, sin clonar) y avisa de lo que se construyó pero no se entregó. Lo convierte en alertas de la pestaña Alertas (origen Entrega). Está en la edición Complete, apagado por defecto (`sentinels.delivery.enabled`); Lite no tiene centinelas.

Tiene su propia entrada en el grupo Centinela del menú, **Centinela de entrega** (dirección `#sentinel-delivery`), visible mientras el centinela está encendido: un panel con los hallazgos abiertos de cada repositorio, el estado de su ciclo y lo que no se pudo leer; el distintivo de la entrada cuenta los errores.

## Qué señala

| Señal | Alerta | Nivel | Activa por defecto |
|---|---|---|---|
| El CHANGELOG tiene entradas bajo `[Unreleased]` y la última versión publicada tiene más de `sentinels.delivery.unreleased_days` días (14) | `release.unreleased_pending` | info | sí |
| Una etiqueta de versión más nueva que la última versión publicada y sin versión propia (un borrador no cuenta como entregado) | `release.tag_without_release` | warning | sí |
| La última versión publicada tiene la descripción vacía | `release.release_without_notes` | info | sí |
| Los ficheros de versión de `version_files` y el primer encabezado con versión del CHANGELOG no dicen todos la misma versión (`1.2` y `1.2.0` son la misma) | `release.version_mismatch` | warning | sí |
| Un repositorio fija una versión anterior a la última del repositorio que ofrece un contrato compartido (las tablas de fijaciones de `sentinel.readiness.pins.sources`, tipo `pin_table`) | `release.ecosystem_drift` | warning | sí |
| La última versión publicada no tiene un fichero para alguno de los patrones de `expected_assets` (por ejemplo `*.zip`, `SHA256SUMS*`) | `release.assets_missing` | warning | sí |

Hay una alerta por repositorio y señal, con los números y algunas etiquetas, patrones o versiones en sus detalles. Cada señal se puede apagar (`sentinels.delivery.signals.<señal>.enabled`) y darle otro nivel (`info`, `warning`, `error`, `critical`). Un repositorio sin ninguna versión publicada no se juzga por las señales de versiones: no las usa. Las preversiones y los borradores nunca se toman como la última versión.

## Un dueño para cada hallazgo

El panel de preparación de la pestaña Centinela (A11) es una fila por repositorio sacada de clones locales; este centinela produce alertas con identificador estable, silencios, eventos y ciclo propio, leídas por la API sin clonar. Las señales sobre los workflows de un repositorio son del centinela de Cadena de suministro y las de los ajustes de GitHub, de Seguridad: nada se genera dos veces. El plugin opcional «Releases» de la hoja de ruta lo sustituye este centinela.

## Lo que no pudo comprobar

Un repositorio que no se puede leer (sin acceso, SSO sin autorizar, cuota agotada, una ronda con menos llamadas de las que necesita un repositorio) **no** es una alerta y **no** es un estado limpio. Se lista en el estado bajo `unavailable`, con el motivo y cuántos, y un nivel `ok` se muestra como `unknown` cuando la mayor parte de lo mirado no se pudo leer. Si un repositorio deja de responder mientras tiene alertas, estas se quedan una semana (marcadas `unread_since`) y nunca se anuncian como resueltas. Un fichero que no existe (sin CHANGELOG en esa ruta, sin ese fichero de versión) simplemente falta. Las tablas de fijaciones se leen una vez por ciclo; una que no se puede leer conserva sus alertas y también se lista.

## Coste

Una ronda lee como máximo `sentinels.delivery.max_repos_per_tick` repositorios (10 por defecto) y hace como máximo `sentinels.delivery.max_calls_per_tick` llamadas (60): una para las versiones y una para las etiquetas, una para el CHANGELOG (más si indicas varias rutas y las primeras no existen) y una por cada fichero de versión. Una señal apagada no se lee nada. Los leídos hace más tiempo van primero y los que tienen una alerta abierta, un poco antes; un ciclo cada `sentinels.delivery.refresh_seconds` (una hora por defecto). No hay peticiones condicionales: el coste lo acotan estos ajustes, no una respuesta 304. El centinela se pausa mientras la cuota restante sea inferior a `sentinels.delivery.min_rate_remaining`. Su estado (`delivery_state.json`) guarda las alertas abiertas, así que un reinicio no vuelve a anunciar nada, y la primera mirada a un repositorio no escribe ningún evento. Una ronda también deja de empezar repositorios nuevos pasados `sentinels.delivery.deadline_s` segundos (30 por defecto; 0 = sin tope): los que no se alcanzan esperan a la ronda siguiente y el estado los lista por nombre como `unchecked` (con `round_cut`) en lugar de contarlos como cero alertas.

## Eventos, notificaciones y puntuación

Un hallazgo nuevo escribe el evento `delivery_new` y uno cerrado `delivery_fixed` (el evento dice `sentinel: delivery` y el código de la alerta). Pertenecen a la familia de versiones, así que solo mantenedores y administradores pueden elegirlos, y la elección del centinela `ci` en las preferencias de notificación de cada usuario decide quién los recibe; no están en ninguna lista de eventos por defecto. Las métricas llevan `delivery_alerts`, `delivery_unreleased_repos`, `delivery_unreleased_days_max`, `delivery_repos_checked`, `delivery_repos_unreadable` y `delivery_calls_last_hour`. La puntuación no las usa. La API responde `GET /api/sentinel/delivery` y la pestaña Alertas y `monitor_cli.py alerts --sentinel delivery` filtran por él.

## Los ajustes

En la página Ajustes, subpestaña Centinela, bloque Entrega: `sentinels.delivery.enabled`, `sentinels.delivery.refresh_seconds`, `sentinels.delivery.max_repos_per_tick`, `sentinels.delivery.max_calls_per_tick`, `sentinels.delivery.min_rate_remaining`, `sentinels.delivery.repos`, `sentinels.delivery.unreleased_days`, `sentinels.delivery.unreleased_min_entries`, `sentinels.delivery.changelog_paths`, `sentinels.delivery.version_files`, `sentinels.delivery.expected_assets`, `sentinels.delivery.signals.unreleased_pending.enabled`, `sentinels.delivery.signals.unreleased_pending.level`, `sentinels.delivery.signals.tag_without_release.enabled`, `sentinels.delivery.signals.tag_without_release.level`, `sentinels.delivery.signals.release_without_notes.enabled`, `sentinels.delivery.signals.release_without_notes.level`, `sentinels.delivery.signals.version_mismatch.enabled`, `sentinels.delivery.signals.version_mismatch.level`, `sentinels.delivery.signals.ecosystem_drift.enabled`, `sentinels.delivery.signals.ecosystem_drift.level`, `sentinels.delivery.signals.assets_missing.enabled`, `sentinels.delivery.signals.assets_missing.level`.

## Lo que no hace

No escribe en GitHub (ni etiqueta, versión, etiqueta de clasificación, pull request ni issue), no publica ni firma nada, no crea propuestas a partir de sus alertas y no lee el contenido de ningún fichero salvo el CHANGELOG y los ficheros de versión que indiques.

## La deriva del ecosistema es información por defecto

`release.ecosystem_drift` compara el pin de cada repositorio en la tabla de pins del proveedor (por ejemplo `registry/contract_pins.json` del repositorio del contrato, la versión contra la que se comprobó cada consumidor por última vez) con la última release publicada del proveedor. Un repositorio atrasado se informa por defecto con nivel `info`, porque los pins los sube el tren de releases del ecosistema y no a mano; `signals.ecosystem_drift.level` lo sube. Las lecturas que superan el tiempo se listan en `unavailable` con el motivo `timeout`.
