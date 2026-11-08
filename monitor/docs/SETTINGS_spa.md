<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SETTINGS.md) | **🇪🇸 Español** | [🇫🇷 Français](SETTINGS_fra.md) | [🇮🇹 Italiano](SETTINGS_ita.md) | [🇩🇪 Deutsch](SETTINGS_deu.md) | [🇨🇳 简体中文](SETTINGS_zho.md) | [🇯🇵 日本語](SETTINGS_jpn.md) | [🇵🇹 Português](SETTINGS_por.md)

# La pestaña Ajustes

La pestaña Ajustes (el icono del engranaje en la cabecera o en la barra de pestañas) cambia desde la página los valores de `actions_monitor.json`, de modo que nadie tenga que editar el fichero a mano.
Está escrita en los ocho idiomas de la página y sigue el aspecto del resto.

<!-- settings:begin -->
## Qué se puede cambiar

Solo las claves de la lista de `settings_api.py` (el esquema). Cada una tiene un tipo y un rango, y la página dice si un cambio necesita **reiniciar** el monitor (el bucle lee su configuración una vez) o **se aplica ya**.

La pestaña se divide en subpestañas, ordenadas de lo común a lo avanzado: Este navegador, General, Refresco y límites, Centinela, Comprobaciones de superficie (A10), Preparación (A11), Carpetas y archivos, Salidas y después las integraciones. Dentro de cada subpestaña los ajustes van en bloques con título; el primer campo de un bloque es su interruptor principal y, mientras está apagado, el resto del bloque se atenúa y no se puede editar. Cada campo muestra su unidad (s, min, h, días, MB, llamadas), su rango, una insignia (pide reinicio / se aplica ya), otra para las opciones de seguridad que arrancan en su estado conservador y una línea de ayuda. El buscador filtra los ajustes de todas las subpestañas; cada subpestaña cuenta sus cambios sin guardar; los botones Guardar y Descartar siempre están visibles; el navegador recuerda la última subpestaña. Las pestañas siguen el patrón de teclado de las pestañas (flechas, Inicio, Fin).

| Pestaña | Bloques y ajustes |
|---|---|
| Este navegador | idioma de la página, tema (auto / claro / oscuro), vista densa de la pestaña Ahora. Se guardan en el navegador, no en el archivo. |
| General | **Identidad**: `github_owner`, `language`<br>**Alcance**: `mode`, `repos`, `ecosystems`, `exclude`<br>**Historial**: `report_history_days` |
| Actualización y límites | **Repositorios calientes**: `refresh_seconds`, `hot_hours`, `runs_per_repo`, `stuck_minutes`<br>**Repositorios fríos**: `cold_refresh_seconds`, `cold_runs_per_repo`<br>**Tareas de fondo**: `issues_refresh_seconds`, `discover_refresh_seconds`, `max_workers`<br>**Cuota de la API**: `min_rate_remaining` |
| Centinela | **Principal**: `sentinel.enabled`, `sentinel.refresh_seconds`, `sentinel.hot_hours`<br>**Alertas e higiene**: `sentinel.alerts_hot_seconds`, `sentinel.alerts_cold_seconds`, `sentinel.hygiene_seconds`<br>**Presupuesto de la API**: `sentinel.max_calls_per_tick`, `sentinel.budget_per_hour`, `sentinel.workers`, `sentinel.min_rate_remaining`<br>**Releases y firmas**: `sentinel.candidate_days`, `sentinel.candidate_min_entries`, `sentinel.skip_candidate_prefixes`, `sentinel.pending_sign_hours`, `sentinel.require_verified_signature`<br>**Consultas de rojos (A2)**: `sentinel.a2_full_sample_unknown`, `sentinel.a2_resolve_max_calls_per_tick`, `sentinel.a2_resolve_ttl_seconds`<br>**Pull requests**: `sentinel.stale_pr_days`<br>**Archivos obligatorios**: `sentinel.required_files`<br>**Minutos de Actions**: `sentinel.minutes_budget_period`, `sentinel.minutes_budget`<br>**Archivos de auditoría**: `sentinel.audit_files.reconciliation`, `sentinel.audit_files.rounds`, `sentinel.audit_files.rounds_extra` |
| Comprobaciones de superficie (A10) | **Principal**: `sentinel.surface.enabled`, `sentinel.surface.refresh_seconds`, `sentinel.surface.local_seconds`, `sentinel.surface.max_repos_per_tick`, `sentinel.surface.min_rate_factor`, `sentinel.surface.budget_share`<br>**Workflows desactivados a mano**: `sentinel.surface.checks.workflows_disabled.*` (`enabled`)<br>**Schedules sin ejecuciones**: `sentinel.surface.checks.dead_schedule.*` (`enabled`, `days`)<br>**uses: sin fijar por SHA**: `sentinel.surface.checks.unpinned_uses.*` (`enabled`)<br>**Permisos demasiado amplios (write-all)**: `sentinel.surface.checks.broad_permissions.*` (`enabled`)<br>**pull_request_target con checkout del PR**: `sentinel.surface.checks.pr_target.*` (`enabled`)<br>**Concurrencia atascada (runs en cola del mismo workflow)**: `sentinel.surface.checks.stuck_concurrency.*` (`enabled`, `minutes`)<br>**Fallos solo en un sistema de la matriz**: `sentinel.surface.checks.matrix_os.*` (`enabled`, `max_per_tick`)<br>**Coste de artifacts**: `sentinel.surface.checks.artifacts.*` (`enabled`, `max_mb`, `retention_days`)<br>**Checks obligatorios rojos o ausentes**: `sentinel.surface.checks.required_checks.*` (`enabled`)<br>**Releases publicadas incompletas**: `sentinel.surface.checks.release_assets.*` (`enabled`, `recent_days`)<br>**Etiqueta de release vs versión del manifiesto/CHANGELOG**: `sentinel.surface.checks.tag_vs_version.*` (`enabled`)<br>**GitHub Packages**: `sentinel.surface.checks.packages.*` (`enabled`)<br>**Borradores y prereleases olvidados**: `sentinel.surface.checks.drafts.*` (`enabled`, `days`)<br>**Alertas críticas/altas con edad (ranking de repos)**: `sentinel.surface.checks.security_aged.*` (`enabled`, `days`)<br>**Cobertura de seguridad (CodeQL / Dependabot)**: `sentinel.surface.checks.coverage.*` (`enabled`)<br>**Secret scanning: abiertas vs resueltas**: `sentinel.surface.checks.secret_resolved.*` (`enabled`)<br>**Dependabot priorizado**: `sentinel.surface.checks.dependabot_priority.*` (`enabled`)<br>**Issues que se pueden cerrar (solo sugerencia)**: `sentinel.surface.checks.issue_close.*` (`enabled`)<br>**Milestones vencidos por ecosistema**: `sentinel.surface.checks.milestones.*` (`enabled`)<br>**PRs humanas envejecidas**: `sentinel.surface.checks.pr_human.*` (`enabled`, `days`)<br>**PRs que tocan workflows o CODEOWNERS (prioridad)**: `sentinel.surface.checks.pr_workflow_touch.*` (`enabled`)<br>**Cola de fusión: aprobadas con CI verde**: `sentinel.surface.checks.merge_queue.*` (`enabled`)<br>**Madurez del manifiesto frente a la evidencia**: `sentinel.surface.checks.maturity.*` (`enabled`)<br>**Paridad de README de 8 idiomas rota**: `sentinel.surface.checks.parity.*` (`enabled`)<br>**Atestaciones de build**: `sentinel.surface.checks.attestation.*` (`enabled`, `max_per_tick`) |
| Preparación (A11) | **Principal**: `sentinel.readiness.enabled`, `sentinel.readiness.min_coverage`, `sentinel.readiness.warn_below`<br>**Pesos de la salud**: `sentinel.readiness.health.weights.red`, `sentinel.readiness.health.weights.stuck`, `sentinel.readiness.health.weights.secret`, `sentinel.readiness.health.weights.high_alert`, `sentinel.readiness.health.weights.alert`, `sentinel.readiness.health.weights.stale_pr`, `sentinel.readiness.health.weights.unsigned`, `sentinel.readiness.health.weights.hygiene`<br>**Versiones fijadas**: `sentinel.readiness.pins.refresh_seconds`, `sentinel.readiness.pins.max_depth`, `sentinel.readiness.pins.sources` |
| Carpetas y ficheros | **Carpetas locales**: `workspace_root`, `signed_dir`, `audit_dir`, `tools_dir`<br>**Archivos de datos**: `ecosystems_file`, `targets_file`, `profiles_file`<br>**ci_red.json**: `sentinel.ci_red_file`, `sentinel.ci_red_audit_copy` |
| Salidas para otras herramientas | **Prometheus**: `outputs.prometheus.enabled`, `outputs.prometheus.per_repo`<br>**JSON de Grafana**: `outputs.json.enabled`<br>**Panel de estado**: `outputs.dashboard.enabled` |
| IA externa para el centinela | **Servicio**: `ai.provider`, `ai.model`, `ai.ollama_url`, `ai.base_url`, `ai.api_key_env`, `ai.daily_limit` |
| Webhook de entrada | **Webhook de entrada**: `webhook.enabled`, `webhook.signing_state` |

Cada ajuste aparece en un solo sitio. Solo lectura: `webhook.signing_state` únicamente dice si el secreto compartido está definido; el secreto nunca se muestra.

### Ejemplo de fuentes de versiones fijadas

Las versiones fijadas solo se leen si hay una fuente; con la lista vacía no se lee nada y la página lo dice. El texto siguiente es un ejemplo, comentado:

```jsonc
// Example, commented out: where the pinned versions of an ecosystem live. Copy the part you need into
// "sentinel" > "readiness" > "pins" > "sources" of actions_monitor.json (or paste it in the Settings tab) and remove the comments.
// [
//   {"ecosystem": "alpha", "kind": "pin_table", "provider": "ALPHA-COMMON", "file": "pins/consumers.json", "key": "consumers"},
//   {"ecosystem": "beta",  "kind": "lock_files", "provider": "BETA-CORE", "lock_name": "beta.lock.json", "version_key": "core"}
// ]
// pin_table: a JSON file of the provider that maps each repository to the version it pins (under "key").
// lock_files: every clone is searched (down to "max_depth" folder levels) for files called "lock_name"; the OLDEST version found in "version_key" counts.
```
<!-- settings:end -->

## Lo que nunca se puede cambiar ni ver desde la página

Tokens, secretos, claves de firma, el secreto del webhook, el comando que el centinela puede ejecutar (`sentinel.notify_command`), la clave de la API de la IA (solo se puede indicar el nombre de su variable de entorno) y cualquier clave de otra herramienta: **no están en el
esquema**, así que la página ni los muestra ni los escribe, y una petición que nombre alguno se rechaza. Todas las demás claves del fichero se conservan exactamente como estaban.

## Cómo funciona un guardado

1. Solo se envían los valores que han cambiado, como `POST /api/settings` con `Content-Type: application/json` y un cuerpo de 16 KB como máximo.
2. Cada valor se comprueba según su tipo y su rango; un solo valor no válido rechaza toda la petición y no se escribe nada. Las rutas deben ser texto sin caracteres de control, nunca una
   ruta de red (UNC) y nunca en la unidad `D:`.
3. El fichero anterior se copia a `config_backups/actions_monitor-<time>.json` (se conservan las diez últimas copias).
4. El fichero nuevo se escribe en uno temporal y se mueve sobre el antiguo (de forma atómica), así que un fallo nunca deja un fichero a medias. Un fichero que no sea JSON válido nunca se sobrescribe desde la página.
5. La página indica qué valores guardados necesitan reinicio y mantiene un aviso hasta que reinicies.

## Quién puede pedirlo

Solo la página de la misma máquina: el servidor escucha en `127.0.0.1` y rechaza toda petición cuyo `Host` u `Origin` no sea su propia dirección (las mismas comprobaciones que en todos los demás endpoints).
Un formulario de otro sitio no puede alcanzarlo, porque la petición debe ser JSON.

## Antes de la 1.5.0

El idioma de las herramientas lo decidía el idioma del sistema; ahora arrancan en inglés y el idioma es un ajuste (aquí, `language`, `MONITOR_LANG` o `--lang`).
`parte_history_days` ahora es `report_history_days` (el nombre antiguo se sigue leyendo).
