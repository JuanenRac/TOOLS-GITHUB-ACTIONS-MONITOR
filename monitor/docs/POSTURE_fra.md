<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](POSTURE.md) | [🇪🇸 Español](POSTURE_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](POSTURE_ita.md) | [🇩🇪 Deutsch](POSTURE_deu.md) | [🇨🇳 简体中文](POSTURE_zho.md) | [🇯🇵 日本語](POSTURE_jpn.md) | [🇵🇹 Português](POSTURE_por.md)

# Posture des dépôts et de l'organisation

Une liste de contrôles, en lecture seule, sur la protection de vos dépôts et de l'organisation : webhooks, réglages d'Actions, analyses, branches, clés de déploiement, âge des secrets, applications, versions. Rien n'est modifié sur GitHub. Éditions Complete et Full ; désactivée par défaut.

## Activation

Activez `posture.enabled` (Réglages > Posture). Quelques dépôts sont lus par cycle (`posture.repos_per_cycle`), chacun au plus toutes les `posture.refresh_hours` ; cela consomme le quota GitHub. `posture.org_checks` ajoute l'organisation.

## Ce qui est contrôlé

Chaque constat indique sa place dans les risques OWASP Top 10 CI/CD et dans le guide CIS de la chaîne d'approvisionnement. La correspondance aide à lire ; ce n'est pas une certification.

| Zone | Identifiants |
|---|---|
| Envois de webhooks | webhook.no_secret webhook.plain_http webhook.tls_off |
| Réglages d'Actions | actions.token_write actions.approves_prs actions.all_allowed actions.sha_not_required actions.fork_approval |
| Code et dépendances | scan.no_code scan.no_credentials scan.no_push_protection scan.no_dependency_alerts repo.no_policy repo.no_update_tool |
| Branches protégées | branch.unprotected branch.no_review branch.bypass branch.release_unprotected branch.merged_unreviewed |
| Clés et secrets | deploy.write deploy.old stored.old |
| Organisation | org.no_two_factor org.default_write org.public_creation org.app_broad org.settings_changed |
| Exécuteurs | runner.not_hardened runner.coverage_lost |
| Versions | release.asset_replaced release.asset_removed release.tag_moved release.outside_window |

## Couverture honnête

Ce que GitHub refuse ou ne répond pas est listé comme **non vérifié**, jamais comme correct, et les constats antérieurs de cette zone restent. Beaucoup de réglages exigent un droit de lecture d'administration : le rapport donne l'autorisation de chaque groupe et ceux refusés. D'un webhook seul l'hôte est gardé ; d'un secret, le nom et les dates. Les versions sont comparées à ce qui a été vu avant : la première lecture ne fait que mémoriser. Dépôts archivés et forks sont ignorés.

## Référence et options

`posture.profile` vaut basic ou strict. `posture.types` donne à des motifs un type (`standard`, `library`, `internal`, `sandbox`) avec sa référence ; `posture.skip` écarte des contrôles. `posture.release_branches` sont des motifs de branches à protéger. `posture.deploy_max_days` et `posture.stored_max_days` fixent les âges. Désactivés tant que vous ne les demandez pas : `posture.audit_log` (journal d'audit, GitHub Enterprise), `posture.review_sample` (changements fusionnés sans approbation), `posture.runner_runs` (étape de durcissement réellement exécutée). `posture.releases` surveille fichiers remplacés et étiquettes déplacées ; `posture.release_window` fixe les heures.

## Où le voir

L'onglet Sécurité des sentinelles montre les constats, la maturité de la chaîne de sécurité de chaque dépôt, un historique par jour et les autorisations. `posture.alerts` place chaque constat dans Alertes, où il peut être mis en sourdine. API : `GET /api/posture`. Ligne de commande :

```
posture status
posture matrix
posture check --repo-name my-repo
```

## Limites

Les jetons fins des membres ne sont pas lus (GitHub ne les liste qu'à une GitHub App) et une seconde application d'écriture n'est pas gérée. Les contrôles d'organisation n'ont été testés qu'avec des réponses inventées.
