<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](OUTPUTS.md) | **🇪🇸 Español** | [🇫🇷 Français](OUTPUTS_fra.md) | [🇮🇹 Italiano](OUTPUTS_ita.md) | [🇩🇪 Deutsch](OUTPUTS_deu.md) | [🇨🇳 简体中文](OUTPUTS_zho.md) | [🇯🇵 日本語](OUTPUTS_jpn.md) | [🇵🇹 Português](OUTPUTS_por.md)

# Salidas para otras herramientas

Tres salidas opcionales, **todas desactivadas por defecto**, que se activan en la pestaña Ajustes (grupo «Salidas para otras herramientas») o en `actions_monitor.json`:

```json
"outputs": {"prometheus": {"enabled": false, "per_repo": true}, "json": {"enabled": false}, "dashboard": {"enabled": false}}
```

Las sirve el mismo servidor web, solo en `127.0.0.1`, con las mismas comprobaciones de `Host` / `Origin` que el resto, y **no necesitan token**. Leen el estado que el monitor ya tiene, así que una
consulta de scrape o un refresco de un panel no gasta cuota de la API de GitHub. Activarlas o desactivarlas se aplica al instante (sin reiniciar).

| Ruta | Formato | Interruptor |
|---|---|---|
| `/metrics` | Texto de Prometheus, versión 0.0.4 | `outputs.prometheus.enabled` (`per_repo` añade las series por repositorio) |
| `/api/outputs/grafana.json` | Tablas JSON para la fuente de datos «Infinity» / JSON de Grafana | `outputs.json.enabled` |
| `/api/outputs/dashboard.json` | el documento de `ci_red.json` (esquema 2, véase CI_RED_SCHEMA_spa.md) para un panel de estado | `outputs.dashboard.enabled` |

Una petición a una ruta cuyo interruptor está apagado recibe `404`. La forma anterior de entregar el mismo documento a un panel, `ci_red.json` y `bin/read_report.py --export-status`, no cambia: es un contrato.

## Métricas de Prometheus

Todos los nombres empiezan por `ghamon_`. Solo medidores (gauges). Un valor desconocido se **omite**, nunca se escribe como 0.

| Métrica | Etiquetas | Significado |
|---|---|---|
| `ghamon_info` | `version` | siempre 1 |
| `ghamon_snapshot_complete` | | 1 cuando la instantánea del centinela está completa, 0 mientras carga o está reducida |
| `ghamon_red_workflows`, `ghamon_red_repos` | | workflows (repositorios) cuya última ejecución completada en la rama por defecto está en rojo |
| `ghamon_ecosystem_red_workflows` | `ecosystem` | lo mismo por ecosistema |
| `ghamon_repo_red_workflows` | `repo`, `ecosystem` | por repositorio (requiere `per_repo`) |
| `ghamon_workflow_red_streak` | `repo`, `workflow`, `ecosystem` | ejecuciones rojas consecutivas (requiere `per_repo`) |
| `ghamon_workflow_red_hours` | `repo`, `workflow`, `ecosystem` | horas desde que se puso en rojo (requiere `per_repo`) |
| `ghamon_pending_sign`, `ghamon_pending_sign_repos`, `ghamon_pending_sign_hours_max` | | compilaciones a la espera de la firma o publicación locales, por encima del umbral |
| `ghamon_repo_pending_sign_hours` | `repo`, `ecosystem` | la espera más larga de un repositorio (requiere `per_repo`) |
| `ghamon_surface_paused`, `ghamon_surface_paused_remaining`, `ghamon_surface_paused_needed` | | 1 mientras las comprobaciones de superficie (A10) esperan cuota de GitHub, con la cuota restante y la necesaria |
| `ghamon_api_rate_remaining`, `ghamon_api_rate_limit` | | la cuota de la API de GitHub |
| `ghamon_score`, `ghamon_score_coverage`, `ghamon_score_scored` | | la puntuación de la cuenta (0 a 100, solo mientras tiene número), la proporción de sus pesos con datos y 1 cuando tiene número (solo Complete; véase SCORE.md) |
| `ghamon_sentinel_calls_last_hour`, `ghamon_sentinel_budget_per_hour` | | las llamadas a la API del centinela frente a su presupuesto |
| `ghamon_repos_watched`, `ghamon_runs_active`, `ghamon_runs_stuck`, `ghamon_runs_failing`, `ghamon_issues_open`, `ghamon_quota_paused` | | las cifras en vivo de la pestaña Ahora |

Un trabajo de scrape:

```yaml
scrape_configs:
  - job_name: github-actions-monitor
    scrape_interval: 30s
    static_configs:
      - targets: ["127.0.0.1:8765"]
```

## Grafana

`docs/grafana/monitor_dashboard.json` es un panel importable (Grafana 10 o posterior): paneles de estadística para los workflows en rojo, las compilaciones a la espera de firma, la cuota restante, el
estado de A10, si la instantánea está completa y las ejecuciones atascadas; un gráfico de barras de workflows en rojo por ecosistema; un gráfico de la racha roja más larga y de la espera de firma; y dos tablas leídas
de `/api/outputs/grafana.json` con la fuente de datos Infinity (`root_selector` `red` y `pending_sign`). Al importar, Grafana pide las fuentes de datos de Prometheus e Infinity; cambia
el puerto en la URL de las dos tablas si el monitor no usa el 8765. Grafana debe ejecutarse en la misma máquina (las salidas solo responden en 127.0.0.1).

## Ideas tomadas de proyectos similares

Leer lo que hacen otras herramientas para GitHub Actions dio algunas ideas; no se usa nada de su código ni de sus textos. De un exportador de métricas de Prometheus: el estado de una ejecución como número más etiquetas, la
elección de qué etiquetas exportar y un puerto e intervalo configurables. De un panel de TV alimentado por webhooks: un estado por repositorio con filtros, mostrado en grande. De un vigilante de terminal: todos los
workflows de un repositorio a la vez hasta que terminan. De un panel de webhooks con reglas de alerta: filtros por repositorio, rama y workflow antes de alertar. Aquí las mismas ideas aparecen como
`per_repo` (elegir las series), la fuente JSON con una fila por workflow en rojo, la pestaña Ahora en vivo y el fichero de eventos con filtros en la página.

## El panel mínimo de Grafana

`docs/grafana/red_by_ecosystem.json` es un panel de un solo gráfico: workflows en rojo por ecosistema (consulta `ghamon_ecosystem_red_workflows`, leyenda `{{ecosystem}}`). Impórtalo y elige tu fuente Prometheus. Una prueba de este repositorio comprueba que la métrica y la etiqueta que usa se sirven de verdad en `/metrics`.

## La cola de firma por confianza

Cada fila de la cola tiene un `trust`: `verified` (la firma se comprobó con la clave pública), `unknown` (el formato no se puede comprobar aquí: nunca se adivina) o `failed` (se comprobó y no coincide). La pestaña Centinela tiene un filtro Firma con el número de cada tipo y marca las filas (borde verde, gris o rojo). Desde la consola: `py -3 bin/read_report.py --export-sign-queue FILE --sign-trust failed`.

## En el modo red

`/metrics` y `dashboard.json` listan tus repositorios y su estado: no son páginas públicas. Con el modo red activo exigen el token de acceso como cualquier otro endpoint; apaga `outputs.prometheus.enabled` / `outputs.dashboard.enabled` si no quieres que ese inventario sea accesible en absoluto.

## Guardar e imprimir el informe de una pestaña

La barra superior de la página (en todas las pestañas) hace UN informe de la pestaña abierta y lo dibuja de cuatro maneras con los mismos datos, así que los formatos nunca difieren:

- **Guardar el informe** abre una ventana con tres casillas: **TXT** (marcada), **PDF** (marcada) y **JSON** (sin marcar: los datos del informe, para otras herramientas). Al aceptar, se abre la ventana **Guardar como** del navegador una vez por formato, con el nombre sugerido `monitor-<pestaña>-<fecha>.<extensión>` y el tipo de archivo correcto (el navegador pide un clic por ventana, así que el botón pasa al formato siguiente). Un navegador sin esa ventana descarga el archivo y la página dice dónde ha caído.
- **PDF**: el monitor escribe el PDF él mismo, sin librerías y con la fuente estándar Helvetica, en inglés, español, alemán, francés, italiano y portugués (`GET /api/report/tab.pdf`, solo desde este equipo; cada uso deja una línea en el registro de acciones). El japonés y el chino necesitan fuentes que un PDF escrito así no tiene, así que para ellos, o cuando eliges «El navegador» en la ventana, el PDF sale de la ventana de impresión del navegador: elige allí **Guardar como PDF**. La página lo dice; nunca escribe un PDF con caracteres rotos.
- **Imprimir** muestra el mismo informe sin menús ni barras (título con el nombre de la pestaña, fecha y hora, versión del monitor, cifras principales, alertas y las tablas de la pestaña) y abre la ventana de impresión.
- El informe lo sirve `GET /api/report/tab?tab=now&lang=es` (`&fmt=json`, `&fmt=txt` o `&fmt=options`), igual en las dos ediciones.

Ajustes (Ajustes > Salidas para otras herramientas > «Guardar e imprimir el informe de una pestaña»): `report_export.txt`, `report_export.pdf` y `report_export.json` (qué casillas empiezan marcadas: TXT y PDF sí, JSON no), `report_export.name` (nombre sugerido, por defecto `monitor-{tab}-{date}`), `report_export.paper` (`a4` o `letter`, por defecto `a4`) y `report_export.pdf_path` (`auto`, `own` o `browser`, por defecto `auto`).

## Métricas del servidor: ciclo, cola de lecturas, facturación, runners e histogramas

Además de los indicadores de arriba, `/metrics` escribe (un valor que no se conoce se omite):

| Métrica | Etiquetas | Significado |
|---|---|---|
| `ghamon_ticks_total`, `ghamon_tick_failures_total` | | ciclos de refresco terminados y ciclos que acabaron con error (contadores) |
| `ghamon_tick_last_seconds`, `ghamon_tick_phase_seconds`, `ghamon_tick_seconds` | `phase` | duración del último ciclo, de cada una de sus fases y el histograma de todos |
| `ghamon_tick_last_ok_timestamp_seconds`, `ghamon_tick_reads_last` | | cuándo acabó bien el último ciclo y cuántos repositorios leyó |
| `ghamon_read_retries_total` | | lecturas que fallaron por una causa pasajera y se repitieron (contador) |
| `ghamon_repos_circuit_open`, `ghamon_repos_read_failing`, `ghamon_repos_read_fail_streak_max` | | repositorios que esperan antes de la siguiente lectura por haber fallado varias veces seguidas (el circuito), repositorios cuya última lectura falló, la racha más larga |
| `ghamon_read_queue_depth`, `ghamon_read_queue_allowed`, `ghamon_read_queue_oldest_wait_cycles`, `ghamon_read_queue_deferred_total`, `ghamon_read_queue_shed_cycles_total` | | la cola de lecturas con contrapresión (solo con `backpressure.enabled` encendido) |
| `ghamon_billing_minutes_total`, `ghamon_billing_minutes_included`, `ghamon_billing_minutes_paid`, `ghamon_billing_sku_minutes`, `ghamon_billing_usd` | `sku`, `product` | el informe de facturación del mes (solo con `quota.billing_api` encendido; un scrape nunca lee GitHub, escribe el último informe que el ciclo tenía) |
| `ghamon_runners` | `state` | runners propios libres, ocupados y desconectados (`runners.enabled`) |
| `ghamon_runner_up`, `ghamon_runner_busy` | `runner` | por runner (`outputs.prometheus.per_runner`) |
| `ghamon_runner_kind_jobs_waiting`, `ghamon_runner_kind_oldest_wait_seconds` | `kind` | jobs sin empezar y la espera más antigua por tipo de runner (`runners.model.enabled`) |

Con `outputs.prometheus.histograms` encendido (y el webhook recibiendo eventos de jobs) escribe también **histogramas**, construidos en memoria con los eventos firmados `workflow_job` y `workflow_run`:

| Métrica | Etiquetas | Significado |
|---|---|---|
| `ghamon_job_wait_seconds` | `runner_group`, `label` | tiempo en cola de un job, contado **una vez por job** |
| `ghamon_job_run_seconds` | `runner_group`, `label`, `conclusion` | duración de los jobs terminados |
| `ghamon_workflow_run_seconds` | `conclusion` | duración de las ejecuciones terminadas |
| `ghamon_jobs_total` | `label`, `conclusion` | jobs terminados (contador) |
| `ghamon_runner_jobs_waiting`, `ghamon_runner_oldest_wait_seconds` | `label` | la demanda de runners ahora: jobs en cola sin empezar y la espera más antigua |

`outputs.prometheus.histogram_max_series` (200 por defecto) acota las series de cada histograma: las que pasan del límite se cuentan bajo el valor de etiqueta `other`. Con `outputs.prometheus.per_runner` encendido añade, por runner propio, `ghamon_runner_jobs_total`, `ghamon_runner_jobs_failed_total` y `ghamon_runner_busy_seconds_total` (también en `GET /api/runners/model` como `per_runner`).

## Pack de observabilidad: reglas de alerta, Alertmanager, OnCall y n8n

`docs/grafana/` lleva, además de los dos paneles, un pack que se copia y se adapta:

- `ghamon_alert_rules.yml`: reglas para Prometheus (también vmalert) con su PromQL: un monitor que no responde, workflows en rojo y rachas, cuota y facturación cerca del final, un ciclo lento o parado, repositorios en el circuito, lecturas que esperan demasiado, jobs que esperan un runner (`histogram_quantile(0.95, sum by (le, label) (rate(ghamon_job_wait_seconds_bucket[30m])))`), runners desconectados y demanda sin ningún runner libre.
- `alertmanager.example.yml`: rutas por gravedad a tres receptores (un webhook por defecto, Grafana OnCall y n8n). Todas las direcciones son `https://example.invalid/...`: no se envía nada hasta que pongas las tuyas, y ningún secreto va en el fichero.
- `n8n_ghamon_alerts.json`: un flujo de n8n que recibe el webhook de Alertmanager y escribe un mensaje por alerta; su último nodo no hace nada hasta que pongas ahí tu nodo de chat, correo o ticket.
- `prometheus.example.yml` y `docker-compose.observability.yml` arrancan Prometheus, Alertmanager y Grafana en el ordenador del monitor para probar el pack (los contenedores comparten la red del host, los puertos están en `127.0.0.1` y la contraseña de Grafana sale de tu shell, nunca del fichero).
## Dónde llama el monitor y eventos hacia un SIEM

- **Tabla de destinos de red**: `monitor_cli.py doctor --egress` (también con `--json`) lista cada host al que la configuración ACTUAL puede llamar, para qué sirve, el ajuste que lo convierte en destino y qué falla si se bloquea: `api.github.com`, `github.com`, `objects.githubusercontent.com` y `release-assets.githubusercontent.com` (actualizaciones), `raw.githubusercontent.com` (`lint.anonymous_public`), ntfy, Telegram, los webhooks de chat, el proveedor de IA que elegiste, el colector OTLP y los sumideros del SIEM. Con `airgapped` no hay nada en uso. Una prueba mantiene la tabla igual a los hosts que nombra el código.
- **SIEM** (apagado): `siem.sinks` en el fichero lista los destinos, cada uno con `enabled: true` para usarse: `elasticsearch` (bulk), `splunk_hec`, `loki`, `sentinel` (Log Analytics, firmado con la clave compartida), `bigquery` (`insertAll`) o `http` (líneas JSON). El token o la clave se lee de la variable de entorno que nombra `token_env`, nunca del fichero. Cada sumidero filtra con `from_minutes` (5), `levels` y `repos_filter`; los eventos tienen una lista cerrada de campos (sin token ni texto de log); un receptor en una dirección privada se rechaza salvo que el sumidero tenga `allow_private`; si un receptor está caído los eventos esperan en una cola de `siem.queue_max` (500) y se descartan primero los más antiguos. No se envía nada en el modo sin conexión.
