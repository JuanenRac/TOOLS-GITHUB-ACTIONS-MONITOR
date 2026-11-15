<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCORE.md) | **🇪🇸 Español** | [🇫🇷 Français](SCORE_fra.md) | [🇮🇹 Italiano](SCORE_ita.md) | [🇩🇪 Deutsch](SCORE_deu.md) | [🇨🇳 简体中文](SCORE_zho.md) | [🇯🇵 日本語](SCORE_jpn.md) | [🇵🇹 Português](SCORE_por.md)

# La puntuación de una cuenta

Un número de 0 a 100, una letra de A a E y una tendencia, para cada cuenta, hechos solo con lo que el monitor ya sabe (las ejecuciones terminadas y las alertas del centinela de colaboración). Está en la edición Complete; Lite no tiene puntuación.

## De qué está hecha

Una suma ponderada de cuatro partes, cada una de 0 a 100. Una parte vale 100 en su límite **bueno**, 0 en su límite **malo** y es lineal entre ambos. Los pesos y los límites son ajustes.

| Parte | Peso | Qué mide | Bueno | Malo |
|---|---|---|---|---|
| Fiabilidad | 40 | proporción de ejecuciones terminadas que salen bien (las canceladas y omitidas no cuentan) | 98 % | 50 % |
| Velocidad | 20 | percentil 95 de la duración de las ejecuciones correctas | 10 min | 60 min |
| Recuperación | 20 | tiempo mediano desde el primer fallo de un flujo hasta su siguiente éxito | 30 min | 24 h |
| Colaboración | 20 | tiempo mediano que una alerta del centinela de colaboración está abierta hasta que desaparece | 2 días | 14 días |

La letra es A desde 90, B desde 80, C desde 70, D desde 55 y E por debajo. La tendencia compara la puntuación con la ventana inmediatamente anterior: sube, baja o estable (un cambio menor que `score.trend_flat` puntos es estable).

## Cuando no hay número

La puntuación nunca muestra un número que no pueda respaldar. La respuesta siempre lleva su `state`, su `coverage` y su `data_quality`:

- **calibrating** (calibrando): la cuenta lleva vigilada menos de `score.calibrating_hours` (24 por defecto). Sin número ni letra.
- **insufficient_data** (datos insuficientes): menos de `score.min_runs` ejecuciones terminadas en la ventana (20 por defecto), o las partes con datos pesan menos de `score.min_coverage` del total (la mitad por defecto). Sin número.
- **scored** (puntuada): un número, una letra y una tendencia. Una parte sin datos se deja fuera y las demás se reescalan; eso baja la `coverage` (por ejemplo 0,8 si el centinela de colaboración está apagado). Nunca cuenta como 0 ni como 100.

La seguridad todavía no es una parte. Mientras tanto, cada respuesta dice `complete: false` y lista `security` en `missing_parts`, así que un 85 nunca se lee como "todo en orden".

## La ventana

La ventana es el número de días de ejecuciones que mira la puntuación: `score.window_days`, 7 por defecto, elegido por el usuario para cada cuenta. La ventana inmediatamente anterior, de la misma duración, da la tendencia. El monitor guarda un pequeño libro de las ejecuciones terminadas que ha visto, así que la ventana puede ser más larga que la lista de últimas ejecuciones que muestra la página. Se guarda una instantánea cada hora y se conserva tanto como el histórico de analíticas (`retention.analytics_days`).

## Por repositorio y por cuenta

Cada cuenta tiene su propia puntuación. Su detalle la desglosa por repositorio (solo las partes de CI, los peores primero). No hay un número único para toda la instalación.

## La API

`GET /api/score` responde la última instantánea de la cuenta: `state`, `score`, `letter`, `trend`, `parts`, `coverage`, `data_quality`, `complete`, `missing_parts`, `repos`, `age_seconds` y `stale` (verdadero si la instantánea tiene más de tres horas). `GET /api/score/history` responde los puntos en el tiempo, del más antiguo al más reciente (`?hours=` hacia atrás desde ahora, 90 días como máximo, y `?limit=`, 2000 como máximo). Un número ausente es `null`, nunca 0. En el modo equipo, quien puede ver la cuenta puede leer su puntuación; los pesos y los límites son ajustes y solo un administrador los cambia.

## Los ajustes

En la página de Ajustes, subpestaña Centinela, bloques Puntuación de la cuenta, Pesos de la puntuación y Letras de la puntuación: `score.enabled`, `score.window_days`, `score.calibrating_hours`, `score.min_runs`, `score.min_coverage`, `score.trend_flat`, `score.weights.reliability`, `score.weights.speed`, `score.weights.recovery`, `score.weights.collaboration`, de `score.grades.A` a `score.grades.D`, `score.alert.enabled`, `score.alert.drop_points` y `score.alert.notify_external` (apagado por defecto). Los límites bueno y malo de cada parte se leen del fichero, en `score.limits` (véase el fichero de ejemplo); no se editan en la página.
