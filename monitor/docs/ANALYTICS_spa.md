<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ANALYTICS.md) | **🇪🇸 Español** | [🇫🇷 Français](ANALYTICS_fra.md) | [🇮🇹 Italiano](ANALYTICS_ita.md) | [🇩🇪 Deutsch](ANALYTICS_deu.md) | [🇨🇳 简体中文](ANALYTICS_zho.md) | [🇯🇵 日本語](ANALYTICS_jpn.md) | [🇵🇹 Português](ANALYTICS_por.md)

# Analítica, lecturas condicionales y conexión perdida

Lo que el monitor aprende de los runs que ya lee, cómo ahorra cuota y cómo sobrevive a un corte de red. Todo es local; no se envía nada a ningún sitio.

## Duraciones, tiempo en cola y pasos

- `p50` y `p95` de la duración de los runs correctos de cada workflow; del tiempo que un job esperó antes de empezar (creado a iniciado); y de cada paso de un workflow. Un workflow muestra cifras cuando tiene `analytics.min_samples` muestras.
- Los tiempos de jobs y pasos necesitan los jobs de runs completados: hasta `analytics.jobs_per_cycle` runs por ciclo, cada uno leído una vez (0 no lee ninguno). El webhook de entrada los aporta gratis.
- Se exportan como `ghamon_workflow_duration_seconds`, `ghamon_job_queue_seconds` y `ghamon_step_duration_seconds` (etiqueta `quantile` 0.5 / 0.95; requiere `per_repo`) y en la fuente JSON de Grafana (`durations`, `queue`). `slower` lista los workflows cuyo p50 es `analytics.slow_factor` veces el habitual.


## Workflows inestables (flaky)

Un workflow que FALLÓ y luego PASÓ en el mismo commit (o cuyo run necesitó otro intento) se etiqueta como inestable: `ghamon_workflow_flaky_rate`. Es solo una etiqueta: lo que cuenta como rojo no cambia.


## Lecturas condicionales (ETag)

- Cada lectura de las listas de runs envía `If-None-Match`; GitHub responde `304 Not Modified` cuando nada cambió y esa respuesta no gasta cuota. La cabecera muestra cuántas lecturas se ahorraron y `ghamon_etag_saved_total` las cuenta. `cache.etag.enabled` y `cache.etag.ttl_hours` están en la pestaña Configuración. Cada entrada pertenece a la credencial que la leyó (una huella corta del token forma parte de la clave, nunca el token), así que un `304` nunca devuelve el cuerpo de otra identidad. Un estado que aún se mueve se lee siempre entero: los trabajos de una ejecución, una ejecución concreta, las suites y comprobaciones (`cache.etag.skip_stateful`) y cualquier lista de ejecuciones cuya última respuesta aún tenía una en cola o en curso (`cache.etag.revalidate_active`). Un rechazo (404 o 403 que no sea límite de cuota) se recuerda `cache.negative_ttl_s` segundos. `/metrics` cuenta además las respuestas sin ETag, las lecturas enteras hechas a propósito y los rechazos no repetidos, y el informe para las herramientas de IA tiene la señal quota.etag.
- El informe para las herramientas de IA nombra schema.drift cuando GitHub envió un estado o una conclusión que el monitor no conoce, o una ejecución sin número utilizable: el valor desconocido se muestra como llegó y nunca se cuenta como rojo ni como verde.
- La caché es el archivo local `etag_cache.json` (nunca se publica); un archivo roto es simplemente una caché vacía.


## Cuando se pierde la conexión

Si todas las lecturas de un ciclo fallan por un problema de conexión (no de login ni de cuota), la página conserva la última imagen y muestra un aviso rojo `sin conexión desde HH:MM`. Nada lanza excepciones; el monitor se reanuda solo y escribe un evento `offline` y otro `online`, una vez cada uno (se pueden notificar). Mientras tanto `ghamon_offline` vale 1.

## Cuánto tiempo se conserva el histórico

Además de `keep_days` del bloque de analíticas, la pasada de retención elimina los días del histórico más antiguos que `retention.analytics_days` (180 por defecto); las muestras están limitadas por `max_samples`. Véase [STORAGE_spa.md](STORAGE_spa.md).


## Tiempo ahorrado (una estimación)

Apagado por defecto (`productivity.enabled`). Encendido, la sección muestra, tarea por tarea, cuántos minutos a la semana ahorra el monitor, con la fórmula de [PRODUCTIVITY_spa.md](PRODUCTIVITY_spa.md): veces por semana x minutos cada vez sin el monitor x el ahorro de la tarea.

- Se cuantifican dos tareas. **Vigilar** (mirar las pestañas de Actions a mano y decidir qué está rojo) toma las veces por semana y los minutos de sus notas (`productivity.watch_times_per_week`, `productivity.watch_minutes_before`). **Diagnóstico** (hallar la causa de una ejecución fallida) cuenta las ejecuciones fallidas que el monitor tiene a la vista en `productivity.window_days` y toma los minutos de sus notas (`productivity.triage_minutes_before`).
- El monitor no puede ver lo que usted hacía antes de instalarse. Una tarea sin esas notas dice **sin datos** y no se inventa ningún número. El total también dice sin datos mientras todas las tareas carezcan de notas.
- Si además anotó los minutos con el monitor (`productivity.watch_minutes_after`, `productivity.triage_minutes_after`), el ahorro se mide con sus notas: 1 - después / antes. Si no, es el porcentaje de `productivity.saving_percent` (90 por defecto) y la tabla dice **supuesto (sin medir)**.
- Con `productivity.team_hours_per_week` la estimación dice también qué parte del tiempo de trabajo son los minutos ahorrados.
- Arreglar un fallo lleva el mismo tiempo con o sin el monitor y nunca se cuenta. Solo se cuentan las ejecuciones fallidas que el monitor tiene: una lista de ejecuciones muy larga puede tener más fallos de los que se muestran.
- Es local y de solo lectura: ninguna llamada a GitHub, nada sale del equipo. Está en `/api/analytics` (`time_saved`), en el resumen del panel A12 y en el brief de la pestaña Resumen para las herramientas de IA.
