<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COLLAB.md) | **🇪🇸 Español** | [🇫🇷 Français](COLLAB_fra.md) | [🇮🇹 Italiano](COLLAB_ita.md) | [🇩🇪 Deutsch](COLLAB_deu.md) | [🇨🇳 简体中文](COLLAB_zho.md) | [🇯🇵 日本語](COLLAB_jpn.md) | [🇵🇹 Português](COLLAB_por.md)

# El centinela Collab: incidencias y pull requests

Un segundo centinela junto al de CI. Mira las **incidencias (issues) y pull requests abiertas** de tus repositorios y te dice lo que necesita a una persona: incidencias olvidadas, etiquetas críticas, revisiones que nadie hace, borradores que no acaban, conflictos que se quedan. Tiene su propio reloj, nunca cambia lo que decide el centinela de CI y **nunca escribe en GitHub**. Es de la edición completa; la edición lite no lo carga.

## Actívalo

Viene apagado. Ajustes > Centinela > Incidencias y pull requests, o en `actions_monitor.json`:

```
"sentinels": {"collab": {"enabled": true, "refresh_seconds": 600, "max_repos_per_tick": 10, "repos": "all",
  "rules": {"issue_stale_days": 14, "issue_critical_labels": ["security", "critical"], "pr_review_pending_days": 3,
            "pr_draft_max_days": 30, "pr_conflict_days": 7, "watch_external_comments": false, "ignore_labels": ["monitor:ignore"]}}}
```

`repos` es `"all"`, una lista de repositorios o `{"ecosystems": [...]}`.

## Las reglas (códigos estables)

| Código | Nivel | Cuándo |
|---|---|---|
| `collab.issue.stale` | aviso | una incidencia abierta sin actividad durante `issue_stale_days` |
| `collab.issue.critical` | error | una incidencia abierta con una de `issue_critical_labels`, sea cual sea su edad |
| `collab.issue.external` | aviso | (solo con `watch_external_comments`) una incidencia de alguien ajeno al equipo que nadie respondió tras un día |
| `collab.pr.review_pending` | aviso | un pull request con revisión pedida que lleva esperando `pr_review_pending_days` |
| `collab.pr.draft_old` | info | un pull request en borrador abierto durante `pr_draft_max_days` |
| `collab.pr.conflict` | aviso | un pull request con conflictos durante `pr_conflict_days` |

Los bots se dejan fuera. Los valores por defecto son lentos a propósito: un borrador que espera meses es normal en muchos equipos.

## Lo que cuesta

Una ronda lee como mucho `max_repos_per_tick` repositorios, con dos peticiones condicionales cada uno (un repositorio que no cambió no gasta cuota) y hasta seis detalles de pull request por ronda. Se detiene mientras la cuota esté por debajo de `min_rate_remaining`. El estado se guarda en `collab_state.json` (dentro de la carpeta de la cuenta si hay varias), así que un reinicio no anuncia nada dos veces.

## Menos ruido: ignorar y silenciar

- **Etiqueta de ignorar**: pon en GitHub una etiqueta de `ignore_labels` (`monitor:ignore` por defecto) en la incidencia o el pull request y Collab no genera alerta para él. El monitor nunca escribe etiquetas.
- **Silencio en el monitor**: en la pestaña Alertas cada alerta tiene botones para silenciar esa alerta, su regla o todo el centinela durante `alerts.mute_hours` horas (24 por defecto, de 1 a 720). Caduca solo, se puede restaurar cuando quieras y la pestaña guarda un historial corto de lo silenciado y hasta cuándo. Es una nota de este monitor; nada cambia en GitHub. En el modo red un silencio solo se puede hacer (y levantar) desde el ordenador donde corre el monitor (`this_computer`); un cliente de la red ve los silencios y no puede cambiarlos. Seguirá así hasta que una edición posterior tenga usuarios propios. El silencio de una alerta también puede durar «hasta que cambie el elemento» (`until_change` en la petición de `POST /api/alerts/mute`): termina enseguida cuando cambia el `updated_at` del issue o de la pull request, o al acabar las horas, lo que ocurra primero.

## Dónde se ve

- La pestaña **Alertas**: una lista para todos los centinelas, filtro por origen (CI, Collab) y por nivel, y las silenciadas si lo pides.
- La pestaña Centinela: la capa *Incidencias y pull requests*.
- `GET /api/alerts?sentinel=collab&level=&muted=show|hide|only` y `GET /api/sentinel/collab`; `GET /api/events?sentinel=collab&since=` para los eventos (`collab_new`, `collab_fixed`, que también envían los canales de notificación si los eliges; ver NOTIFICATIONS).

## Límites

Solo se leen las primeras 100 incidencias abiertas y 100 pull requests abiertos de cada repositorio, los actualizados más recientemente primero. Collab no propone ni ejecuta nada; las acciones sobre incidencias y pull requests son de una edición posterior.
