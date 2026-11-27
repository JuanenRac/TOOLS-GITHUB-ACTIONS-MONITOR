<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](POSTURE.md) | **🇪🇸 Español** | [🇫🇷 Français](POSTURE_fra.md) | [🇮🇹 Italiano](POSTURE_ita.md) | [🇩🇪 Deutsch](POSTURE_deu.md) | [🇨🇳 简体中文](POSTURE_zho.md) | [🇯🇵 日本語](POSTURE_jpn.md) | [🇵🇹 Português](POSTURE_por.md)

# Postura de repositorios y organización

Una lista de comprobaciones, solo lectura, de cómo están protegidos sus repositorios y organización: webhooks, ajustes de Actions, análisis, ramas, claves de despliegue, edad de secretos, aplicaciones y versiones. No se cambia nada en GitHub. Ediciones Complete y Full; apagada de fábrica.

## Activación

Active `posture.enabled` (Ajustes > Postura). Se leen unos pocos repositorios por ciclo (`posture.repos_per_cycle`), cada uno como mucho cada `posture.refresh_hours`; consume cuota de GitHub. `posture.org_checks` añade la organización.

## Qué se comprueba

Cada hallazgo indica su lugar en los riesgos OWASP Top 10 CI/CD y en la guía CIS de cadena de suministro. La correspondencia ayuda a leer; no es una certificación.

| Zona | Identificadores |
|---|---|
| Entregas de webhooks | webhook.no_secret webhook.plain_http webhook.tls_off |
| Ajustes de Actions | actions.token_write actions.approves_prs actions.all_allowed actions.sha_not_required actions.fork_approval |
| Código y dependencias | scan.no_code scan.no_credentials scan.no_push_protection scan.no_dependency_alerts repo.no_policy repo.no_update_tool |
| Ramas | branch.unprotected branch.no_review branch.bypass branch.release_unprotected branch.merged_unreviewed |
| Claves y secretos | deploy.write deploy.old stored.old |
| Organización | org.no_two_factor org.default_write org.public_creation org.app_broad org.settings_changed org.pat_broad |
| Ejecutores | runner.not_hardened runner.coverage_lost |
| Versiones | release.asset_replaced release.asset_removed release.tag_moved release.outside_window |

## Cobertura honesta

Lo que GitHub deniega o no responde aparece como **sin comprobar**, nunca como correcto, y los hallazgos anteriores de esa zona se mantienen. Muchos ajustes requieren permisos de lectura de administración: el informe lista el permiso de cada grupo y cuáles se denegaron. De un webhook solo se guarda el host; de un secreto, nombre y fechas. Las versiones se comparan con lo visto antes, así que la primera lectura solo recuerda. Se omiten repositorios archivados y forks. Una comprobación apagada, excluida por el perfil o el tipo de proyecto, o repositorios que aún esperan turno dejan la norma «comprobada en parte», nunca «sin hallazgos». La política de seguridad del repositorio público `.github` de la cuenta cuenta para los repositorios que no tienen una.

## Línea base y opciones

`posture.profile` es basic o strict. `posture.types` asigna a patrones un tipo (`standard`, `library`, `internal`, `sandbox`) con su línea base; `posture.skip` omite comprobaciones. `posture.release_branches` son patrones de ramas protegidas. `posture.deploy_max_days` y `posture.stored_max_days` fijan edades. Apagados hasta pedirlos: `posture.audit_log` (auditoría de la organización, GitHub Enterprise), `posture.review_sample` (cambios fusionados sin aprobación), `posture.runner_runs` (paso de endurecimiento en lo ejecutado). `posture.releases` vigila ficheros reemplazados y etiquetas movidas; `posture.release_window` fija el horario.

## Dónde verlo

La pestaña de Seguridad de los centinelas muestra los hallazgos, la madurez de la cadena de seguridad de cada repositorio, un historial diario y los permisos. `posture.alerts` lleva cada hallazgo a Alertas, donde se puede silenciar. API: `GET /api/posture`. Consola:

```
posture status
posture matrix
posture check --repo-name my-repo
posture report
```

## Límites

Sin hacer: una segunda GitHub App de escritura (lectura y escritura no se reparten entre dos Apps). `org.pat_broad` necesita una GitHub App con el permiso de tokens de acceso personal; con un token personal queda sin comprobar. Las comprobaciones de organización solo se han probado con respuestas inventadas.

## Informe de cumplimiento y permisos

`posture report` (y `compliance` en `GET /api/posture`) lee los hallazgos frente a los diez riesgos OWASP de CI/CD y las secciones CIS a las que corresponden: con hallazgos, sin hallazgos, leído en parte o no comprobado, con un texto corto sobre lo que significa cada riesgo y la tendencia respecto a una semana antes. Es una ayuda de lectura, no una certificación; los números de sección CIS no se han contrastado con el documento oficial. `original.weak` (`posture.upstream`, apagado) señala un fork cuyo original público no tiene política de seguridad o herramienta de actualización. La tabla de permisos dice qué permiso de GitHub App desbloquea cada grupo y, con una App configurada, si está concedido.
