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

- Cada lectura de las listas de runs envía `If-None-Match`; GitHub responde `304 Not Modified` cuando nada cambió y esa respuesta no gasta cuota. La cabecera muestra cuántas lecturas se ahorraron y `ghamon_etag_saved_total` las cuenta. `cache.etag.enabled` y `cache.etag.ttl_hours` están en la pestaña Configuración.
- La caché es el archivo local `etag_cache.json` (nunca se publica); un archivo roto es simplemente una caché vacía.


## Cuando se pierde la conexión

Si todas las lecturas de un ciclo fallan por un problema de conexión (no de login ni de cuota), la página conserva la última imagen y muestra un aviso rojo `sin conexión desde HH:MM`. Nada lanza excepciones; el monitor se reanuda solo y escribe un evento `offline` y otro `online`, una vez cada uno (se pueden notificar). Mientras tanto `ghamon_offline` vale 1.
