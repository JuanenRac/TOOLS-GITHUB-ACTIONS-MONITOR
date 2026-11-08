<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](QUOTAS.md) | **🇪🇸 Español** | [🇫🇷 Français](QUOTAS_fra.md) | [🇮🇹 Italiano](QUOTAS_ita.md) | [🇩🇪 Deutsch](QUOTAS_deu.md) | [🇨🇳 简体中文](QUOTAS_zho.md) | [🇯🇵 日本語](QUOTAS_jpn.md) | [🇵🇹 Português](QUOTAS_por.md)

# Cuotas y planes

El monitor lo usa cualquier tipo de cuenta, así que nunca da una por supuesta. Las cifras de abajo viven en `monitor/quotas.json` (edítalo para seguir los cambios de GitHub sin una versión nueva del monitor) y se contrastaron con la documentación pública de GitHub; cambian con el tiempo, así que tómalas como punto de partida y mira las páginas que nombra el archivo. Elige tu plan en **Ajustes > Básico** (`account.plan`); mientras sea *desconocido* no se muestra ninguna cifra de cuota.

## La cuota de la API

| Cómo inicias sesión | Llamadas por hora |
|---|---|
| Sin sesión | 60 por hora y dirección |
| Tu propia sesión (`gh auth login`) o un token personal | 5.000 |
| El token de un workflow (dentro de Actions) | 1.000 por repositorio (15.000 en Enterprise Cloud) |
| Una aplicación en Enterprise Cloud | 15.000 |
| Una GitHub App en otro caso | 5.000, crece con la instalación hasta 12.500 |

La página muestra el límite real leído de las cabeceras de GitHub (`X-RateLimit-*`), nunca un 5.000 supuesto: eso también hace que funcione GitHub Enterprise Server (`GH_HOST`). Sin sesión (60 por hora) te dice que ejecutes `gh auth login`. Existe además un límite *secundario* (no más de 100 peticiones simultáneas y ráfagas): cuando GitHub responde con él, el monitor espera al menos un minuto, luego duplica la espera hasta cinco minutos y nunca insiste en bloque.

## Minutos de Actions

| Plan | Incluido cada mes (en dinero) | En minutos Linux | Almacenamiento de artefactos |
|---|---|---|---|
| Free | 12 $ | 2.000 | 500 MB |
| Pro | 18 $ | 3.000 | 1 GB |
| Team | 18 $ | 3.000 | 2 GB |
| Enterprise Cloud | 300 $ | 50.000 | 50 GB |

**Los repositorios públicos no gastan minutos en ningún plan** (los runners propios tampoco); los runners más grandes siempre se facturan. Un minuto se multiplica por la tarifa de su sistema: Windows es unas 1,67 veces un minuto de Linux y macOS unas 10,3 veces (son tarifas por minuto en `quotas.json`: 0,006 $ Linux, 0,010 $ Windows, 0,062 $ macOS). Lo que el monitor muestra en **Ajustes > Básico > Plan y cuotas** es una **estimación**: la duración de los runs de las últimas 24 horas, redondeada al minuto, solo de repositorios privados, con el sistema que supones en `quota.default_runner`, y el ritmo de un día multiplicado por los días del mes. Las cifras reales solo vienen del interruptor opcional `quota.billing_api` (apagado por defecto, solo lectura, necesita una sesión que pueda ver la facturación; con un 403 o 404 se mantiene la estimación y lo dice). Se envía un aviso por las notificaciones una vez al mes al llegar a `quota.warn_percent` (75 %) y a `quota.alert_percent` (90 %) de los minutos incluidos.

## Concurrencia y límites

| Plan | Jobs a la vez | de ellos macOS |
|---|---|---|
| Free | 20 | 5 |
| Pro | 40 | 5 |
| Team | 60 | 5 |
| Enterprise | 500 | 50 |

El panel compara los jobs en curso y en cola con el límite de tu plan y avisa al llegar al 90 % o cuando hay jobs esperando con el límite lleno. Un job puede durar 6 horas como máximo en un runner de GitHub (el panel lista los que pasan del 80 % de eso), un run de workflow dura 35 días como máximo y una matriz tiene hasta 256 jobs.

## Lo que no se cubre

No se siguen los precios por minuto extra, los runners grandes, el almacenamiento en uso, Codespaces ni Packages; la tabla de planes es un punto de partida y los límites de macOS cambian. Nada de esto se ha probado todavía contra un informe de facturación real: la lectura de `usageItems` sigue la descripción pública del informe y degrada en silencio.
