<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL.md) | **🇪🇸 Español** | [🇫🇷 Français](SENTINEL_fra.md) | [🇮🇹 Italiano](SENTINEL_ita.md) | [🇩🇪 Deutsch](SENTINEL_deu.md) | [🇨🇳 简体中文](SENTINEL_zho.md) | [🇯🇵 日本語](SENTINEL_jpn.md) | [🇵🇹 Português](SENTINEL_por.md)

# El centinela y sus comprobaciones A1-A13

El **centinela** es la segunda mitad de la edición completa. El *monitor* muestra qué corre y qué falla ahora mismo; el *centinela* revisa toda la cuenta cada pocos minutos y responde otra pregunta: **qué necesita a una persona**. Lee GitHub (nunca escribe en él), guarda un historial corto en este ordenador y convierte lo que encuentra en trece comprobaciones numeradas, **A1 a A13**, con un semáforo cada una.

**La edición lite no lo incluye.** `MONITOR_LITE_GITHUB_ACTIONS` (puerto 8766) no tiene centinela: ni siquiera se importa el módulo y sus endpoints responden 404. La edición completa (`MONITOR_GITHUB_ACTIONS`, puerto 8765) lo arranca sola; se apaga con `sentinel.enabled` (Ajustes > Centinela). Las dos ediciones usan la misma regla de «rojo en main» (A2), así que sus cifras coinciden.

## Cómo arranca y qué cuesta

Arranca con el monitor completo y corre en el mismo proceso, en su propio hilo, con su propio presupuesto de llamadas a GitHub (`sentinel.budget_per_hour`, 600 por defecto, y `sentinel.max_calls_per_tick`). Cuando la cuota de GitHub baja de `sentinel.min_rate_remaining` deja de preguntar y la página dice que está en pausa por cuota. Nada de lo que hace escribe en GitHub.

## Archivos que escribe (junto al monitor, nunca se publican)

| Archivo | Qué contiene |
|---|---|
| `ci_red.json` | esquema 2: por repositorio, los workflows en rojo y las horas que una release espera su firma. Contrato estable para otras herramientas, véase `CI_RED_SCHEMA.md` y `CI_RED_BRIDGE.md`. Dónde: `sentinel.ci_red_file`. |
| `sentinel_history.json` | los totales diarios (alertas, rojos, candidatas) para las tendencias y para «nuevas desde ayer». |
| `sentinel_cache.json` | las últimas respuestas de las lecturas lentas, para que un reinicio no vuelva a preguntarlo todo. |
| `events_monitor.jsonl`, `events_state.json` | el flujo de eventos (qué se puso rojo, qué se arregló) con un `code` estable por evento. |
| `SENTINEL_REPORT_*.txt` | el parte diario, guardado en la carpeta de auditoría si existe. |

## Cómo leerlo

Cada comprobación tiene uno de cinco niveles: **ok** (nada que hacer), **info** (conviene saberlo), **warn** (míralo pronto), **bad** (actúa ya) y **unknown** (aún no se pudo comprobar: **desconocido nunca se muestra como verde**). El parte de arriba de la pestaña lo resume en pocas líneas; el detalle se abre por comprobación. Un repositorio que filtraste en el monitor no se comprueba.

## Las comprobaciones

| Comprobación | Qué comprueba y la regla exacta | Dónde se configura | Nivel y qué hacer |
|---|---|---|---|
| **A1** | **Builds.** Un run en curso o en cola durante más del límite está *atascado*. También se listan las incidencias abiertas con la etiqueta `build-failed` o `build-stuck`. Se ignoran los runs del evento `dynamic` (internos de Dependabot). | `stuck_minutes` | **bad** si algo está atascado o hay una incidencia abierta. Abre el run, cancélalo o relánzalo; cierra la incidencia al arreglarlo. |
| **A2** | **CI en rojo.** Para cada archivo de workflow, el ÚLTIMO run COMPLETADO en la rama POR DEFECTO: está en rojo si falló (`failure`, `timed_out`, `startup_failure`, `action_required`). Los runs `cancelled`, `skipped`, `neutral` o `stale`, los que están en curso y los de otras ramas no dicen nada y nunca ocultan un rojo anterior. *Racha* = rojos consecutivos. Cuando la lista de runs de un repositorio es tan larga como la muestra pedida, un workflow puede quedar más allá: el centinela pregunta a GitHub por el último run de cada uno de esos workflows. | `runs_per_repo`, `cold_runs_per_repo`, `sentinel.a2_full_sample_unknown`, `sentinel.a2_resolve_max_calls_per_tick`, `sentinel.a2_resolve_ttl_seconds` | **bad** si algún workflow está en rojo; **unknown** (nunca verde) si un repositorio no tiene datos de runs o no se pudo resolver un workflow. Arregla el workflow o relánzalo; la edición lite muestra la misma cifra, marcada como aproximada porque adivina la rama por defecto. |
| **A3** | **Alertas de seguridad.** Alertas abiertas de CodeQL, de Dependabot y de secret scanning por repositorio, con su severidad, y cuántas son nuevas desde el último día del historial. | `sentinel.alerts_hot_seconds`, `sentinel.alerts_cold_seconds` | **bad** con cualquier alerta de secretos o crítica/alta; **warn** con cualquier otra; **unknown** mientras carga. Rota primero un secreto filtrado; luego actualiza o descarta el resto. |
| **A4** | **Pull requests de Dependabot.** PRs abiertos de Dependabot con su edad, un salto de versión *mayor* y un conflicto de fusión; los PRs de otras personas solo se cuentan. | `sentinel.stale_pr_days` (7) | **warn** si alguno es un salto mayor o tiene conflicto; **info** si solo hay PRs. Fusiona los verdes; reorganiza o cierra los que chocan. |
| **A5** | **Releases.** (a) *Candidata*: al menos `candidate_min_entries` entradas en `[Unreleased]` del CHANGELOG y la última release más vieja que `candidate_days` (o ninguna). (b) Una *build verde* de un workflow de release más nueva que la última release. (c) *Esperando firma*: una build verde de más de `pending_sign_hours` sin firmar ni publicar; una firma cuenta solo si verifica contra la clave pública del ecosistema. | `sentinel.candidate_days` (2), `sentinel.candidate_min_entries` (1), `sentinel.skip_candidate_prefixes`, `sentinel.pending_sign_hours` (24), `sentinel.require_verified_signature` | **warn** con una candidata o una firma pendiente; **info** con builds verdes aún sin publicar. Corta la release o firma la build. |
| **A6** | **Higiene.** Por repositorio: el ruleset `protect-main` está ACTIVE, existe la etiqueta `dependencies`, existen los archivos exigidos (por defecto README, LICENSE, CHANGELOG, SECURITY), se exige fijar por SHA, `allowed_actions` es `selected` y ningún workflow programado fue desactivado por GitHub. | `sentinel.required_files`, `sentinel.hygiene_seconds` | **warn** si algún repositorio tiene un problema; **info** mientras algunos no están comprobados. Cada problema indica el arreglo. |
| **A7** | **Uso.** Minutos de Actions de las últimas 24 horas y 7 días por repositorio y ecosistema, la cuota de la API que queda y el *presupuesto* por ecosistema: **ok** bajo el 80 %, **warn** desde el 80 %, **over** desde el 100 % del tope. | `sentinel.min_rate_remaining` (800), `sentinel.minutes_budget`, `sentinel.minutes_budget_period` (7d) | **warn** si la cuota está bajo el límite o un presupuesto llega al 80 %. Espacia el refresco o recorta los workflows largos. |
| **A8** | **Rondas.** Lee los archivos de auditoría y de rondas de la carpeta de auditoría (los patrones de `sentinel.audit_files`) y muestra su estado. Vacío si no hay carpeta de auditoría. | `sentinel.audit_files.*`, `audit_dir` | Solo **info**. Nada que hacer. |
| **A9** | **Roadmaps.** Si los tableros de GitHub Projects de los ecosistemas están *vivos*: reconciliados en los últimos 8 días y no más viejos que sus definiciones. Necesita el permiso `read:project` de `gh`; sin él la pestaña funciona con las definiciones y dice qué falta. | (fixed: 8 days) | **warn** si un tablero está caducado o nunca se reconcilió; **unknown** si no está configurado. |
| **A10** | **Superficie de Actions y releases.** Veinticinco comprobaciones de solo lectura sobre los clones y unas pocas llamadas en frío, listadas en la tabla de abajo. Cada una tiene interruptor y, cuando procede, umbral. | `sentinel.surface.*` | Por comprobación, véase abajo. En pausa cuando la cuota es baja (el parte lo dice). |
| **A11** | **Preparación de releases, salud del ecosistema y pins.** Preparación por repositorio (entradas, CI, versión, build, firma, siguiente paso); una nota de salud 0-100 por ecosistema que resta penalizaciones ponderadas por rojos, atascos, secretos, alertas altas, alertas, PRs viejos, builds sin firmar e higiene; y los pins de dependencias que van atrasados. La nota solo se muestra cuando `min_coverage` de los repositorios tiene datos. | `sentinel.readiness.*` (`warn_below` 70, `min_coverage` 0.5) | **warn** cuando una nota queda bajo `warn_below`; **info** con repositorios atrasados; **unknown** con pocos datos. |
| **A12** | **Analítica.** p50 / p95 de la duración de cada workflow, del tiempo en cola de sus jobs y de cada paso; workflows más lentos de lo habitual (`analytics.slow_factor`); workflows *flaky* (fallaron y luego pasaron en el mismo commit). Es solo una etiqueta: nunca cambia lo que cuenta como rojo. | `analytics.*` | Sin semáforo propio. Mira primero los lentos y los flaky. |
| **A13** | **Linter de workflows.** Reglas estáticas sobre los clones locales: `unpinned_uses`, `permissions`, `secrets_in_clear`, `injection`, `pr_target`. Cada hallazgo tiene un nivel (info / aviso / error); un comentario `# monitor-lint: ignore REGLA motivo` o `lint.ignore` silencia uno. | `lint.*` | Color del peor hallazgo. Arregla antes los errores; la página filtra por nivel. |

## Las comprobaciones de A10

Todas son sugerencias de solo lectura para una persona; el monitor nunca cierra una incidencia, fusiona un pull request ni publica una release. Se apaga una con `sentinel.surface.checks.<nombre>.enabled`.

| Comprobación | Qué busca | Por defecto |
|---|---|---|
| `workflows_disabled` | Workflows desactivados a mano | on |
| `dead_schedule` | Schedules sin ejecuciones | on · days=14 |
| `unpinned_uses` | uses: sin fijar por SHA | on |
| `broad_permissions` | Permisos demasiado amplios (write-all) | on |
| `pr_target` | pull_request_target con checkout del PR | on |
| `stuck_concurrency` | Concurrencia atascada (runs en cola del mismo workflow) | on · minutes=60 |
| `matrix_os` | Fallos solo en un sistema de la matriz | on · max_per_tick=4 |
| `artifacts` | Coste de artifacts | on · max_mb=500, retention_days=30 |
| `required_checks` | Checks obligatorios rojos o ausentes | on |
| `release_assets` | Releases publicadas incompletas | on · recent_days=30, required |
| `tag_vs_version` | Etiqueta de release vs versión del manifiesto/CHANGELOG | on |
| `packages` | GitHub Packages | on |
| `drafts` | Borradores y prereleases olvidados | on · days=14 |
| `security_aged` | Alertas críticas/altas con edad (ranking de repos) | on · days=30 |
| `coverage` | Cobertura de seguridad (CodeQL / Dependabot) | on |
| `secret_resolved` | Secret scanning: abiertas vs resueltas | on |
| `dependabot_priority` | Dependabot priorizado | on |
| `issue_close` | Issues que se pueden cerrar (solo sugerencia) | on |
| `milestones` | Milestones vencidos por ecosistema | on |
| `pr_human` | PRs humanas envejecidas | on · days=7 |
| `pr_workflow_touch` | PRs que tocan workflows o CODEOWNERS (prioridad) | on |
| `merge_queue` | Cola de fusión: aprobadas con CI verde | on |
| `maturity` | Madurez del manifiesto frente a la evidencia | on |
| `parity` | Paridad de README de 8 idiomas rota | on |
| `attestation` | Atestaciones de build | on · max_per_tick=3 |

## Dónde se configura todo

Cada umbral de arriba es un ajuste de las pestañas **Centinela**, **Comprobaciones de superficie (A10)**, **Preparación (A11)**, **Carpetas y archivos**, **Analítica** y **Linter de workflows** de la página de Ajustes, y una clave de `actions_monitor.json`. La lista completa con sus rangos está en `SETTINGS_spa.md`. El panel de Ayuda y `--help-topics sentinel` muestran esta página sin conexión.
