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

Una petición a una ruta cuyo interruptor está apagado recibe `404`. La forma anterior de entregar el mismo documento a un panel, `ci_red.json` y `read_report.py --export-status`, no cambia: es un contrato.

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
