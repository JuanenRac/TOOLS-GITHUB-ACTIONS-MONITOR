<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCORE.md) | **🇪🇸 Español** | [🇫🇷 Français](SCORE_fra.md) | [🇮🇹 Italiano](SCORE_ita.md) | [🇩🇪 Deutsch](SCORE_deu.md) | [🇨🇳 简体中文](SCORE_zho.md) | [🇯🇵 日本語](SCORE_jpn.md) | [🇵🇹 Português](SCORE_por.md)

# La puntuación de una cuenta

Un número de 0 a 100, una letra de A a E y una tendencia, para cada cuenta, hechos solo con lo que el monitor ya sabe (las ejecuciones terminadas y las alertas del centinela de colaboración). Está en la edición Complete; Lite no tiene puntuación.

## De qué está hecha

Una suma ponderada de cinco partes, cada una de 0 a 100. Una parte vale 100 en su límite **bueno**, 0 en su límite **malo** y es lineal entre ambos. Los pesos y los límites son ajustes.

| Parte | Peso | Qué mide | Bueno | Malo |
|---|---|---|---|---|
| Fiabilidad | 30 | proporción de ejecuciones terminadas que salen bien (las canceladas y omitidas no cuentan) | 98 % | 50 % |
| Velocidad | 15 | percentil 95 de la duración de las ejecuciones correctas | 10 min | 60 min |
| Recuperación | 15 | tiempo mediano desde el primer fallo de un flujo hasta su siguiente éxito; un flujo que sigue en rojo cuenta el tiempo que lleva en rojo hasta ahora | 30 min | 24 h |
| Colaboración | 15 | tiempo mediano que una alerta del centinela de colaboración está abierta hasta que desaparece | 2 días | 14 días |
| Seguridad | 25 | los puntos que los hallazgos abiertos del centinela de seguridad restan a 100 (solo mientras ese centinela está activo) | 0 puntos | 100 puntos |

La letra es A desde 90, B desde 80, C desde 70, D desde 55 y E por debajo. La tendencia compara la puntuación con la ventana inmediatamente anterior: sube, baja o estable (un cambio menor que `score.trend_flat` puntos es estable).

## Cuando no hay número

La puntuación nunca muestra un número que no pueda respaldar. La respuesta siempre lleva su `state`, su `coverage` y su `data_quality`:

- **calibrating** (calibrando): la cuenta lleva vigilada menos de `score.calibrating_hours` (24 por defecto). Sin número ni letra.
- **insufficient_data** (datos insuficientes): menos de `score.min_runs` ejecuciones terminadas en la ventana (20 por defecto), o las partes con datos pesan menos de `score.min_coverage` del total (la mitad por defecto). Sin número.
- **scored** (puntuada): un número, una letra y una tendencia. Una parte sin datos se deja fuera y las demás se reescalan; eso baja la `coverage` (por ejemplo 0,85 si el centinela de colaboración está apagado). Nunca cuenta como 0 ni como 100.

La seguridad es una parte como las demás, pero solo tiene datos mientras el centinela de seguridad está activo y ha mirado suficientes repositorios. Sin él, la respuesta dice `complete: false` y lista `security` en `missing_parts`, y las demás partes se reescalan, así que el número nunca se lee como un todo en orden. GitHub no da histórico de los hallazgos, así que la parte de seguridad es la misma en la ventana y en la anterior: la tendencia muestra lo que hicieron la CI y la colaboración. Los pesos son 30, 15, 15, 15 y 25 por defecto. Una ventana con ejecuciones y ningún fallo no tiene nada que recuperar: su parte de recuperación es completa, como un hecho y no como un hueco.

Un flujo que sigue en rojo al final de la ventana no se olvida: la parte de recuperación cuenta el tiempo que lleva en rojo hasta ahora, una cota inferior que crece mientras dura el rojo, así que un fallo que nadie arregla baja más el número cada hora. Un fallo arreglado cuenta su tiempo real. Un relanzamiento de una ejecución cuenta como una ejecución más del flujo, de modo que se ven el primer intento fallido y el segundo en verde. Si actualizas desde una versión anterior, los números de una cuenta con un flujo en rojo pueden ser más bajos que antes. Cuando ninguna parte tiene datos, la respuesta es `insufficient_data` con el motivo `no_data`. El libro guarda como mucho 20000 ejecuciones: cuando tuvo que descartar ejecuciones que pertenecen a la ventana actual, `data_quality.truncated` es verdadero y `truncated` figura entre los motivos, para que una tasa de éxito que ve solo parte de la ventana no se tome por completa. En `GET /api/score/global` una cuenta cuya instantánea está caducada queda fuera de la media y se cuenta en `accounts_stale`, y `/metrics` no exporta `ghamon_score` para una instantánea caducada.

Tampoco se olvida un fallo que cruza el borde de la ventana: la parte de recuperación cuenta el tramo del rojo que cae dentro de la ventana (la ventana anterior contó su propio tramo, ningún día se cuenta dos veces), y el libro guarda el último fallo de un flujo que nadie ha arreglado mientras la regla del rojo lo siga mostrando (`ci.red_age_days`). Del mismo modo, un aviso del centinela de colaboración que sigue abierto al final de la ventana cuenta con el tiempo que lleva abierto, una cota inferior: dejar avisos sin resolver baja la parte de colaboración en vez de dejarla sin datos. Si actualizas desde una versión anterior, las notas pueden ser más bajas que antes.

Un repositorio no está sano porque no tenga nada que mostrar. Cada repositorio vigilado está *activo* (una ejecución propia más reciente que `ci.inactive_days` días), *dormido* (nunca ha ejecutado nada propio) o *inactivo* (su ejecución más reciente es más antigua): los repositorios dormidos e inactivos no son verdes ni rojos y se cuentan aparte (`activity` de la instantánea, las cifras `dormant` y `inactive_repos`, la ayuda emergente de la ficha), así que una cuenta con cientos de forks no muestra una puntuación hecha de nada. Un repositorio que el monitor no pudo leer está *desconocido*, nunca dormido. `ci.dormant_repos` desactiva el recuento.

## La ventana

La ventana es el número de días de ejecuciones que mira la puntuación: `score.window_days`, 7 por defecto, elegido por el usuario para cada cuenta. La ventana inmediatamente anterior, de la misma duración, da la tendencia. El monitor guarda un pequeño libro de las ejecuciones terminadas que ha visto, así que la ventana puede ser más larga que la lista de últimas ejecuciones que muestra la página. Se guarda una instantánea cada hora y se conserva tanto como el histórico de analíticas (`retention.analytics_days`).

## Por repositorio y por cuenta

Cada cuenta tiene su propia puntuación. Su detalle la desglosa por repositorio (solo las partes de CI, los peores primero). No hay un número único para toda la instalación. Solo como información, `GET /api/score/global` del supervisor da la media de las cuentas puntuadas que el solicitante puede ver, ponderada por sus repositorios con número y siempre con cuántas cuentas entran; una cuenta sin número se lista y se deja fuera.

## Qué ejecuciones lee

La página lista las 600 ejecuciones más recientes, pero una cuenta con muchos repositorios puede leer miles en un ciclo. `score.source` elige de qué salen la puntuación, los informes, el espejo y la analítica:

- `recent600`: las 600 ejecuciones más recientes de la página, como antes. Cuando el ciclo leyó más, la instantánea lo dice: `data_quality.cut` es verdadero, `data_quality.runs_read` es el número leído y `recent_cut` está entre los motivos, y la página muestra la línea "El ciclo leyó N ejecuciones pero la puntuación vio solo las 600 más recientes". No se oculta nada: una cifra que ve solo una parte reciente de la ventana nunca se presenta como el total.
- `ledger` (el valor por defecto desde esta versión): todas las ejecuciones que leyó el ciclo, contadas una vez en el libro de la cuenta. El libro guarda además totales por hora (éxitos y fallos por hora) que sobreviven a su tope de 20000 ejecuciones: cuando el tope tuvo que descartar ejecuciones de la ventana, `data_quality.truncated` es verdadero y `data_quality.aggregate` da las ejecuciones y la tasa de éxito que esos totales guardan para la ventana.

El valor por defecto de `score.source` es `ledger` desde esta versión, con su entrada en el registro de migraciones: el actualizador se lo da a quien nunca lo fijó y conserva el valor de quien lo fijó a mano (`recent600` incluido). Fijar `recent600` devuelve el comportamiento anterior. Un libro escrito antes de esta versión construye sus totales por hora con las ejecuciones que tiene; las instantáneas de versiones anteriores se leen tal cual, sin los campos nuevos. No se añade ninguna llamada a GitHub.

## En la página

Una ficha en la cabecera, junto a las fichas de preparación, muestra la puntuación: el número, la letra, una flecha con el cambio respecto a la ventana anterior y una pequeña línea con los últimos días. Su color sigue a la letra (A y B verde, C ámbar, D y E rojo). Mientras no hay número es neutra y dice por qué (calibrando, datos insuficientes). Una estrella tras la letra significa que una parte todavía no cuenta (hoy, la seguridad): un número alto no es entonces un todo en orden. Al pasar el ratón muestra la cobertura, las partes con sus pesos y el repositorio más débil. La ficha no se muestra en Lite ni con la puntuación apagada (`score.enabled`). Mientras calibra, la ficha dice cuánto falta de `score.calibrating_hours` (`data_quality.calibrating_hours`), con una barra y el día y la hora en que aparecerá el número; con datos insuficientes dice qué condición falla (ejecuciones o cobertura), y el texto emergente dice también por qué una parte no cuenta (un centinela apagado, que no ha terminado su primer barrido o que ha leído muy pocos repositorios).

## Para otras herramientas

Las métricas (`/metrics`, con la salida Prometheus activada) llevan tres series sin etiquetas: `ghamon_score_scored` (1 cuando la cuenta tiene número), `ghamon_score_coverage` (la proporción de los pesos con datos, de 0 a 1) y `ghamon_score` (el número, solo mientras lo hay: nunca se exporta como 0 cuando no lo hay). El servidor MCP tiene una herramienta de solo lectura `get_score` con la respuesta de la API. `--demo` muestra una puntuación inventada y no escribe nada. El panel de Grafana de ejemplo (`docs/grafana/monitor_dashboard.json`) tiene un panel de la puntuación y otro de la puntuación en el tiempo.

## La API

`GET /api/score` responde la última instantánea de la cuenta: `state`, `score`, `letter`, `trend`, `parts`, `coverage`, `data_quality`, `complete`, `missing_parts`, `repos`, `age_seconds` y `stale` (verdadero si la instantánea tiene más de tres horas). `GET /api/score/history` responde los puntos en el tiempo, del más antiguo al más reciente (`?hours=` hacia atrás desde ahora, 90 días como máximo, y `?limit=`, 2000 como máximo). Un número ausente es `null`, nunca 0. En el modo equipo, quien puede ver la cuenta puede leer su puntuación; los pesos y los límites son ajustes y solo un administrador los cambia.

## La alerta por caída

Cuando la puntuación baja `score.alert.drop_points` puntos (10 por defecto) o más frente a la ventana anterior, o pasa a una letra inferior, la pestaña de Alertas muestra la alerta `score.dropped` (un aviso; crítica si la letra es E), con la puntuación antigua y la nueva. Permanece mientras la instantánea muestre la caída y desaparece cuando la puntuación se recupera, y puede silenciarse como cualquier otra alerta. Está activada para el panel por defecto. Sale por los canales de notificación externos (evento `score_dropped`) solo si `score.alert.notify_external` está activado, lo que no ocurre por defecto, y solo en el momento en que aparece. `score.alert.enabled` apaga la alerta.

## Los ajustes

En la página de Ajustes, subpestaña Centinela, bloques Puntuación de la cuenta, Pesos de la puntuación y Letras de la puntuación: `score.enabled`, `score.source`, `score.window_days`, `score.calibrating_hours`, `score.min_runs`, `score.min_coverage`, `score.trend_flat`, `score.weights.reliability`, `score.weights.speed`, `score.weights.recovery`, `score.weights.collaboration`, `score.weights.security`, de `score.grades.A` a `score.grades.D`, `score.alert.enabled`, `score.alert.drop_points` y `score.alert.notify_external` (apagado por defecto). Los límites bueno y malo de cada parte se leen del fichero, en `score.limits` (véase el fichero de ejemplo); no se editan en la página.

## Frente al periodo anterior

La comparación de periodos (`GET /api/compare`, `monitor_cli.py compare`) pone la puntuación media, la proporción de ejecuciones fallidas, las duraciones y el tiempo de resolución de alertas de un periodo frente al anterior, con el mismo libro y las mismas fotos horarias que la puntuación. Está apagada por defecto (`compare.enabled`) y dice `insufficient_data` o `baseline_unavailable` en lugar de inventar un número. Véase [COMPARE_spa.md](COMPARE_spa.md).
