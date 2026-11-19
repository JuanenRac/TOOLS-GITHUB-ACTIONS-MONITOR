<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_SECURITY.md) | **🇪🇸 Español** | [🇫🇷 Français](SENTINEL_SECURITY_fra.md) | [🇮🇹 Italiano](SENTINEL_SECURITY_ita.md) | [🇩🇪 Deutsch](SENTINEL_SECURITY_deu.md) | [🇨🇳 简体中文](SENTINEL_SECURITY_zho.md) | [🇯🇵 日本語](SENTINEL_SECURITY_jpn.md) | [🇵🇹 Português](SENTINEL_SECURITY_por.md)

# El centinela de seguridad

El tercer centinela, junto al de CI y Collab. Lee, sin escribir nada en GitHub, lo que el propio GitHub dice que está abierto o falta en la seguridad de cada repositorio, y lo convierte en alertas de la pestaña de Alertas (origen Seguridad). Está en la edición Complete, apagado por defecto (`sentinels.security.enabled`); Lite no tiene centinelas.

## Qué lee y qué señala

| Señal | Alerta | Nivel | Activa por defecto |
|---|---|---|---|
| Alertas abiertas de Dependabot de la gravedad `min_severity` o superior (high por defecto) | `security.dependabot` | crítica si alguna es crítica, error si alguna es alta, si no aviso | sí |
| Alertas abiertas del análisis de código de la gravedad `min_severity` o superior | `security.code_scanning` | igual | sí |
| Alertas abiertas del análisis de secretos | `security.secret` | siempre crítica (un secreto que GitHub encuentra es un secreto expuesto) | sí |
| La rama por defecto no tiene protección | `security.branch_unprotected` | aviso | sí |
| Los flujos reciben permiso de escritura por defecto | `security.workflow_write` | aviso | sí |
| No hay archivo CODEOWNERS | `security.codeowners_missing` | información | no |
| Una ejecución importante (un push a la rama por defecto, una ejecución manual, una de `pull_request_target`) que el monitor había visto fue borrada | `security.runs_deleted` | error | no |

**Ejecuciones borradas** (`security.runs_deleted`, desactivado por defecto): tras una fuga de secretos, borrar la ejecución que los imprimió es la forma habitual de eliminar el rastro y GitHub no deja un registro visible. Con `sentinels.security.signals.runs_deleted.enabled` el centinela guarda una lista corta y privada de las ejecuciones importantes que ha visto y, cuando una ya no está en la lista de ejecuciones, pide esa ejecución sola: un 404 explícito es un borrado; una negativa (403), un error de red o un 5xx nunca cuentan. Una ejecución más antigua que `sentinels.security.signals.runs_deleted.check_window_days` (14) no se consulta (la retención de la cuenta puede haberla purgado) y un borrado detectado se mantiene como aviso ese mismo número de días. Se piden como mucho `sentinels.security.signals.runs_deleted.max_checks` (50) ejecuciones sueltas por repositorio y ronda. El aviso nombra el workflow, quién la lanzó y la rama, nunca contenido de la ejecución.

Hay una alerta por repositorio y señal, con las cuentas por gravedad en sus detalles. Cada señal puede apagarse (`sentinels.security.signals.<señal>.enabled`) y, en Dependabot y el análisis de código, tener otra gravedad mínima. De un repositorio archivado no se pide nada más.

## Lo que no pudo comprobar

Una fuente que GitHub no responde para un repositorio (la función está apagada allí, o el acceso no puede leerla: 403, 404) **no** es una alerta y **no** es un certificado de buena salud. Se lista en el estado bajo `unavailable`, con cuántos repositorios afecta, y la página lo dice. La única excepción es la protección de la rama por defecto: GitHub responde 404 cuando una rama no tiene ninguna, y eso es el hallazgo; un 403 ahí es solo no legible.

Cuando la mayor parte de lo que pesa en la penalización (Dependabot, escaneo de código, secretos) no se puede leer, el nivel es `unknown` y no `ok`, y la parte de seguridad de la puntuación se deja fuera en vez de contar como 100; el estado muestra `sources_readable` y `sources_total`. Si una fuente deja de responder mientras hay una alerta abierta, la alerta se mantiene una semana (marcada con `unread_since`) y nunca se anuncia como corregida. Un repositorio cuyas lecturas siguen fallando espera 5 minutos, 30 minutos y luego 6 horas hasta el siguiente intento, así unos pocos repositorios rotos nunca gastan la ronda entera.

Ahora cada centinela dice su **ciclo de vida**: `healthy` (sano), `degraded` (degradado: algunas lecturas fallan, una fuente no puede leerse o no ha terminado su primera pasada), `paused` (en pausa, esperando la cuota de GitHub), `error` (falla y no ha leído nada aún) u `off` (apagado). «Sin alertas» solo significa algo cuando el ciclo de vida es `healthy`.

## Coste

Una ronda lee como máximo `sentinels.security.max_repos_per_tick` repositorios (5 por defecto), los revisados hace más tiempo primero y los que tienen una alerta abierta un poco antes, con un ciclo cada `sentinels.security.refresh_seconds` (30 minutos por defecto). Cada repositorio cuesta como mucho siete lecturas, casi todas condicionales, así que un repositorio que no cambió no gasta cuota; el archivo CODEOWNERS, cuando se pide, se busca como mucho una vez al día. El centinela se pausa mientras la cuota restante sea menor que `sentinels.security.min_rate_remaining`. Su estado (`security_state.json`) guarda las alertas abiertas, así que un reinicio no vuelve a anunciar nada, y la primera pasada por un repositorio no escribe eventos. Una ronda también deja de empezar repositorios nuevos pasados `sentinels.security.deadline_s` segundos (30 por defecto; 0 = sin tope): los que no se alcanzan esperan a la ronda siguiente y el estado los lista por nombre como `unchecked` (con `round_cut`) en lugar de contarlos como cero alertas.

## Un solo propietario por hallazgo

Los paneles de la pestaña Centinela que ya mostraban cifras de seguridad (alertas por repositorio, alertas antiguas, cobertura de Dependabot y CodeQL, pull requests de Dependabot) siguen siendo paneles. Las alertas de la pestaña de Alertas sobre estas señales vienen solo de este centinela, así que nada se genera dos veces. El contenido de cada fichero de flujo (acciones sin fijar a un commit, `write-all`, sin bloque de permisos, `pull_request_target` con descarga) corresponde al [centinela de cadena de suministro](SENTINEL_SUPPLY_spa.md); `security.workflow_write` se queda aquí porque es un ajuste del repositorio.

## Eventos y notificaciones

Un hallazgo nuevo escribe el evento `security_new` y uno cerrado `security_fixed` en el feed, con los canales de notificación colgados de él; ambos son tipos que la persona puede pedir en los ajustes de notificaciones, y las preferencias por usuario tienen una casilla de Seguridad. No se anuncia nada la primera vez que se mira un repositorio.

## Los ajustes

En la página de Ajustes, subpestaña Centinela, bloque Seguridad: `sentinels.security.enabled`, `sentinels.security.refresh_seconds`, `sentinels.security.max_repos_per_tick`, `sentinels.security.min_rate_remaining`, `sentinels.security.repos`, `sentinels.security.signals.dependabot.enabled`, `sentinels.security.signals.dependabot.min_severity`, `sentinels.security.signals.code_scanning.enabled`, `sentinels.security.signals.code_scanning.min_severity`, `sentinels.security.signals.secret.enabled`, `sentinels.security.signals.branch.enabled`, `sentinels.security.signals.workflow.enabled` y `sentinels.security.signals.codeowners.enabled`, `sentinels.security.signals.runs_deleted.enabled`, `sentinels.security.signals.runs_deleted.check_window_days`, `sentinels.security.signals.runs_deleted.max_checks`. Los puntos que cada hallazgo resta a la parte de seguridad de la puntuación (`sentinels.security.penalty`) se leen del fichero; véase el fichero de ejemplo.
