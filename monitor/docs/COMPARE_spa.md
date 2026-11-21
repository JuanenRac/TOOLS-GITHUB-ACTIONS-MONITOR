<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPARE.md) | **🇪🇸 Español** | [🇫🇷 Français](COMPARE_fra.md) | [🇮🇹 Italiano](COMPARE_ita.md) | [🇩🇪 Deutsch](COMPARE_deu.md) | [🇨🇳 简体中文](COMPARE_zho.md) | [🇯🇵 日本語](COMPARE_jpn.md) | [🇵🇹 Português](COMPARE_por.md)

# Comparar periodos

¿Cómo nos fue esta semana frente a la pasada? La comparación lo responde con lo que el monitor ya guarda (el libro de ejecuciones y alertas terminadas y las fotos horarias de la puntuación). No lee nada de GitHub, no escribe nada, no necesita IA y no inventa nada. Existe solo en la edición Completa y está **apagada** hasta que actives `compare.enabled`.

## Los dos periodos

- **Periodo**: los últimos 7 días (o 30, o cualquier número hasta 90), o un rango exacto con `from` y `to`.
- **Referencia**: `previous` (el periodo de la misma duración justo antes, por defecto), `year_ago` (las mismas fechas de hace un año) o `custom` (`base_from` y `base_to`).
- **Días**: `all`, `workdays` o `weekend`. El filtro se aplica a todas las cifras. El día de un instante es su día en la zona horaria de `display.timezone`; los laborables son `compare.workdays` (de lunes = 1 a domingo = 7, de lunes a viernes por defecto). Los festivos no se conocen: un festivo cuenta como el día de la semana en que cae.

Mezclar laborables y fines de semana oculta cosas (un fallo que solo ocurre los sábados pesa poco en una semana de datos mezclados), y por eso existe el filtro.

## Las cifras

| Cifra | Cómo se calcula | Mejor cuando |
|---|---|---|
| `red_rate` | ejecuciones fallidas / (correctas + fallidas) que empezaron en el periodo | es menor |
| `duration_p50` | mediana de segundos de las ejecuciones correctas | es menor |
| `resolution` | mediana del tiempo entre la apertura y el cierre de las alertas del centinela de colaboración que se cerraron en el periodo | es menor |
| `score_mean` | puntuación media de las fotos horarias que tuvieron número | es mayor |
| `score_coverage` | parte media de la puntuación que tuvo datos | es mayor |

Cada cifra viaja con `now`, `base`, `delta`, una `direction` (`better`, `worse`, `same`) y su `state`. Las ejecuciones canceladas, omitidas y sin terminar no cuentan en ningún sentido.

## Cuando no hay cifra

La comparación nunca muestra un número que no pueda respaldar: una cifra que falta es `null`, nunca 0 ni 100.

- `insufficient_data`: menos ejecuciones terminadas que `compare.min_runs_per_window`, menos alertas resueltas que `compare.min_resolved` o menos fotos que `compare.min_snapshots` en uno de los dos periodos. La respuesta dice cuál y por qué (`missing`).
- `baseline_unavailable`: el periodo con el que comparar no es fiable. El motivo es `history_too_short` (el monitor lleva menos de `compare.min_days_of_history` días vigilando), `before_history` (ese periodo es anterior a los datos guardados) o `no_history`. Las cifras del periodo actual se muestran igualmente.
- `calibrating`: el monitor aún no ha vigilado `score.calibrating_hours` horas. No se compara nada.
- `off`: `compare.enabled` está apagado.

`data_quality` lleva las ejecuciones contadas en cada periodo y `truncated` cuando el libro tuvo que descartar ejecuciones antiguas. `coverage` es la parte de las cifras que se pudo comparar.

## Qué cambió

Además de las cifras: los repositorios que empeoran o mejoran (cambio en su proporción de ejecuciones fallidas; solo los que tienen al menos `compare.min_repo_runs` ejecuciones en ambos periodos), los workflows que empiezan a fallar y los que dejan de fallar, y el número de alertas abiertas en el periodo y aún abiertas al final. Cada lista tiene como mucho `compare.top_changes` filas, ordenadas por el tamaño del cambio y luego por nombre. El libro no guarda el repositorio de las alertas del centinela de colaboración, así que aparecen como cuentas, nunca por nombre.

## Hasta dónde llega hacia atrás

La comparación lee el libro de la puntuación. Mientras `compare.enabled` está activo, el libro conserva dos periodos de `compare.default_window_days` (al menos 15 días) en lugar de las dos ventanas de la puntuación; nunca es más antiguo que el monitor, así que una instalación nueva no puede comparar 30 días con 30 días hasta tener 60 días de histórico.

## La API

`GET /api/compare?window=7&days=workdays&baseline=previous` (también `from`, `to`, `base_from`, `base_to`). Responde `state`, `windows`, `metrics`, `changes`, `alerts`, `coverage` y `data_quality`. `format=ndjson` o `format=csv` dan una fila por cifra. Una petición sin sentido es un 400 con un `code` estable: `bad_range` (desde posterior a hasta, más de 90 días, en el futuro), `bad_window`, `bad_days`, `bad_baseline` o `bad_format`. Un visor puede leerla; sirve la cuenta del proceso, nunca otra. Con la API de lectura v1 activada también se sirve bajo el prefijo `/api/v1/`. No está en la edición Lite.

## La línea de comandos

`monitor_cli.py compare [--window 7|30d] [--days all|workdays|weekend] [--baseline previous|year_ago] [--format table|json|ndjson|csv]`. Códigos de salida: 0 todo se pudo comparar; 4 una cifra tiene pocos datos, no hay referencia o la comparación está apagada; 5 con `--fail-on` cuando una cifra empeora. `score --compare` sigue comparando la puntuación con el histórico de su ventana.

## En la página

La pestaña Gráficos muestra la sección «Comparar periodos» cuando la comparación está activa: un selector de periodo, días y referencia, una línea por cifra con su cambio, las alertas y las listas de cambios.

## Respuestas frescas, obsoletas y lentas

La comparación y los informes opcionales son consultas pesadas, así que su respuesta se guarda en memoria y cada petición la encuentra en uno de tres estados. **Fresca** (más joven que `cache.heavy_fresh_s`, 5 segundos): se sirve tal cual, sin calcularla otra vez. **Obsoleta** (más vieja que eso y más joven que `cache.stale_serve_h` horas, 1 hora): se sirve al instante y se marca con `freshness` = `{"state": "stale", "age_s": N}` mientras un cálculo la renueva en segundo plano; una respuesta fresca no lleva esa clave. **Caducada** (más vieja o nunca hecha): se calcula ahora, y una copia tan vieja nunca se sirve. Un cálculo tiene un tope, `analytics.query_timeout_s` (120 segundos): pasado ese tiempo la respuesta es `504` con el código `query_timeout` en vez de esperar para siempre; un cálculo no se puede matar, así que termina solo, su respuesta se guarda para la petición siguiente y mientras tanto no se empieza un segundo cálculo de la misma consulta. Nada de esto llama a GitHub.

## Los ajustes

Ajustes, pestaña Centinela, bloque Comparación de periodos: `compare.enabled`, `compare.default_window_days`, `compare.default_days_filter`, `compare.workdays`, `compare.min_runs_per_window`, `compare.min_days_of_history`, `compare.min_resolved`, `compare.min_snapshots`, `compare.min_repo_runs`, `compare.top_changes`, `compare.include_in_report` y `compare.cache_seconds`. Una respuesta se conserva `compare.cache_seconds` segundos y luego se calcula de nuevo.

## Ventanas largas en una cuenta grande

Con `compare.progressive` encendido (apagado por defecto) una comparación sobre una ventana más larga que `compare.progressive_days` (7 por defecto) se responde ya con sus últimos días y la respuesta lo dice (`partial`: los días pedidos, los días mostrados y que el resto se está calculando); la ventana entera se termina en segundo plano y la siguiente petición, o el siguiente refresco de la página, la recibe. Una petición con `from` y `to` nunca se parte.
