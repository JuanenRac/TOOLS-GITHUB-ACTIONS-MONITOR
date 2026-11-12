<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL.md) | [🇪🇸 Español](SENTINEL_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](SENTINEL_ita.md) | [🇩🇪 Deutsch](SENTINEL_deu.md) | [🇨🇳 简体中文](SENTINEL_zho.md) | [🇯🇵 日本語](SENTINEL_jpn.md) | [🇵🇹 Português](SENTINEL_por.md)

# La sentinelle et ses contrôles A1-A13

La **sentinelle** est la seconde moitié de l'édition complète. Le *moniteur* montre ce qui tourne et ce qui échoue à l'instant ; la *sentinelle* examine tout le compte toutes les quelques minutes et répond à une autre question : **qu'est-ce qui demande une personne**. Elle lit GitHub (n'y écrit jamais), garde un court historique sur cet ordinateur et transforme tout ce qu'elle trouve en treize contrôles numérotés, **A1 à A13**, avec un feu tricolore chacun.

**L'édition lite ne l'inclut pas.** `MONITOR_LITE_GITHUB_ACTIONS` (port 8766) n'a pas de sentinelle : le module n'est même pas importé et ses points d'accès répondent 404. L'édition complète (`MONITOR_GITHUB_ACTIONS`, port 8765) la démarre seule ; on la coupe avec `sentinel.enabled` (Réglages > Sentinelle). Les deux éditions utilisent la même règle de « rouge sur main » (A2), leurs chiffres coïncident donc.

## Comment elle démarre et ce qu'elle coûte

Elle démarre avec le moniteur complet et tourne dans le même processus, dans son propre fil, avec son propre budget d'appels à GitHub (`sentinel.budget_per_hour`, 600 par défaut, et `sentinel.max_calls_per_tick`). Quand le quota de GitHub passe sous `sentinel.min_rate_remaining`, elle cesse de demander et la page indique la pause pour quota. Rien de ce qu'elle fait n'écrit sur GitHub.

## Fichiers qu'elle écrit (à côté du moniteur, jamais publiés)

| Fichier | Contenu |
|---|---|
| `ci_red.json` | schéma 2 : par dépôt, les workflows en rouge et les heures qu'une release attend sa signature. Contrat stable pour d'autres outils, voir `CI_RED_SCHEMA_fra.md` et `CI_RED_BRIDGE_fra.md`. Où : `sentinel.ci_red_file`. |
| `sentinel_history.json` | les totaux quotidiens (alertes, rouges, candidates) pour les tendances et « nouveau depuis hier ». |
| `sentinel_cache.json` | les dernières réponses des lectures lentes, pour qu'un redémarrage ne redemande pas tout. |
| `events_monitor.jsonl`, `events_state.json` | le flux d'événements (ce qui est passé au rouge, ce qui a été corrigé) avec un `code` stable par événement. |
| `SENTINEL_REPORT_*.txt` | le rapport quotidien, enregistré dans le dossier d'audit s'il existe. |

## Comment le lire

Chaque contrôle a l'un de cinq niveaux : **ok** (rien à faire), **info** (bon à savoir), **warn** (à regarder bientôt), **bad** (agir maintenant) et **unknown** (pas encore vérifiable : **unknown n'est jamais affiché en vert**). Le rapport en haut de l'onglet le résume en quelques lignes ; le détail s'ouvre par contrôle. Un dépôt filtré dans le moniteur n'est pas contrôlé.

## Les contrôles

| Contrôle | Ce qu'il vérifie et la règle exacte | Où configurer | Niveau et que faire |
|---|---|---|---|
| **A1** | **Builds.** Un run en cours ou en file plus longtemps que la limite est *bloqué*. Les issues ouvertes avec l'étiquette `build-failed` ou `build-stuck` sont listées aussi. Les runs de l'événement `dynamic` (internes de Dependabot) sont ignorés. | `stuck_minutes` | **bad** si quelque chose est bloqué ou si une issue est ouverte. Ouvrir le run, l'annuler ou le relancer ; fermer l'issue une fois corrigé. |
| **A2** | **CI rouge.** Pour chaque fichier de workflow, le DERNIER run TERMINÉ sur la branche PAR DÉFAUT : rouge s'il a échoué (`failure`, `timed_out`, `startup_failure`, `action_required`). Les runs `cancelled`, `skipped`, `neutral` ou `stale`, ceux en cours et ceux d'autres branches ne disent rien et ne cachent jamais un rouge plus ancien. *Série* = rouges consécutifs. Quand la liste de runs d'un dépôt est aussi longue que l'échantillon demandé, un workflow peut se cacher au-delà : la sentinelle demande à GitHub le dernier run de chacun de ces workflows. | `runs_per_repo`, `cold_runs_per_repo`, `sentinel.a2_full_sample_unknown`, `sentinel.a2_resolve_max_calls_per_tick`, `sentinel.a2_resolve_ttl_seconds` | **bad** si un workflow est rouge ; **unknown** (jamais vert) si un dépôt n'a aucune donnée de run ou si un workflow n'a pu être résolu. Corriger le workflow ou le relancer ; l'édition lite montre le même chiffre, marqué approximatif car elle devine la branche par défaut. |
| **A3** | **Alertes de sécurité.** Alertes ouvertes CodeQL, Dependabot et secret scanning par dépôt, avec la gravité, et combien sont nouvelles depuis le dernier jour de l'historique. | `sentinel.alerts_hot_seconds`, `sentinel.alerts_cold_seconds` | **bad** pour toute alerte de secret ou critique/haute ; **warn** pour toute autre ; **unknown** pendant le chargement. Renouveler d'abord un secret divulgué ; puis mettre à jour ou écarter le reste. |
| **A4** | **Pull requests de Dependabot.** PR ouvertes de Dependabot avec leur âge, un saut de version *majeur* et un conflit de fusion ; les PR d'autres personnes sont seulement comptées. | `sentinel.stale_pr_days` (7) | **warn** si l'une est un saut majeur ou en conflit ; **info** s'il n'y a que des PR. Fusionner les vertes ; rebaser ou fermer les conflictuelles. |
| **A5** | **Releases.** (a) *Candidate* : au moins `candidate_min_entries` entrées sous `[Unreleased]` du CHANGELOG et la dernière release plus ancienne que `candidate_days` (ou aucune). (b) Un *build vert* d'un workflow de release plus récent que la dernière release. (c) *En attente de signature* : un build vert de plus de `pending_sign_hours` ni signé ni publié ; une signature ne compte que si elle se vérifie avec la clé publique de l'écosystème. | `sentinel.candidate_days` (2), `sentinel.candidate_min_entries` (1), `sentinel.skip_candidate_prefixes`, `sentinel.pending_sign_hours` (24), `sentinel.require_verified_signature` | **warn** avec une candidate ou une signature en attente ; **info** avec des builds verts pas encore publiés. Couper la release ou signer le build. |
| **A6** | **Hygiène.** Par dépôt : le ruleset `protect-main` est ACTIVE, l'étiquette `dependencies` existe, les fichiers requis existent (par défaut README, LICENSE, CHANGELOG, SECURITY), l'épinglage par SHA est exigé, `allowed_actions` vaut `selected` et aucun workflow planifié n'a été désactivé par GitHub. | `sentinel.required_files`, `sentinel.hygiene_seconds` | **warn** si un dépôt a un problème ; **info** tant que certains ne sont pas vérifiés. Chaque problème indique le correctif. |
| **A7** | **Usage.** Minutes d'Actions des dernières 24 heures et 7 jours par dépôt et écosystème, le quota d'API restant et le *budget* par écosystème : **ok** sous 80 %, **warn** dès 80 %, **over** dès 100 % du plafond. | `sentinel.min_rate_remaining` (800), `sentinel.minutes_budget`, `sentinel.minutes_budget_period` (7d) | **warn** si le quota est sous la limite ou si un budget atteint 80 %. Espacer l'actualisation ou réduire les workflows longs. |
| **A8** | **Tours.** Lit les fichiers d'audit et de tours du dossier d'audit (les motifs de `sentinel.audit_files`) et montre leur état. Vide s'il n'y a pas de dossier d'audit. | `sentinel.audit_files.*`, `audit_dir` | **info** seulement. Rien à faire. |
| **A9** | **Roadmaps.** Si les tableaux GitHub Projects des écosystèmes sont *vivants* : réconciliés dans les 8 derniers jours et pas plus vieux que leurs définitions. Nécessite la portée `read:project` de `gh` ; sans elle l'onglet fonctionne avec les définitions et dit ce qui manque. | (fixed: 8 days) | **warn** si un tableau est périmé ou jamais réconcilié ; **unknown** si non configuré. |
| **A10** | **Surface d'Actions et des releases.** Vingt-cinq contrôles en lecture seule sur les clones et quelques appels à froid, listés dans le tableau ci-dessous. Chacun a un interrupteur et, quand c'est utile, un seuil. | `sentinel.surface.*` | Par contrôle, voir ci-dessous. En pause quand le quota est bas (le rapport le dit). |
| **A11** | **Préparation des releases, santé de l'écosystème et pins.** Préparation par dépôt (entrées, CI, version, build, signature, étape suivante) ; une note de santé 0-100 par écosystème qui retire des pénalités pondérées pour rouges, blocages, secrets, alertes hautes, alertes, PR anciennes, builds non signés et hygiène ; et les pins de dépendances en retard. Une note n'apparaît que si `min_coverage` des dépôts ont des données. | `sentinel.readiness.*` (`warn_below` 70, `min_coverage` 0.5) | **warn** quand une note est sous `warn_below` ; **info** avec des dépôts en retard ; **unknown** avec trop peu de données. |
| **A12** | **Analytique.** p50 / p95 de la durée de chaque workflow, du temps en file de ses jobs et de chaque étape ; workflows plus lents que d'habitude (`analytics.slow_factor`) ; workflows *flaky* (échoué puis réussi sur le même commit). Simple étiquette : elle ne change jamais ce qui compte comme rouge. | `analytics.*` | Pas de feu propre. Regarder d'abord les lents et les flaky. |
| **A13** | **Linter de workflows.** Règles statiques sur les clones locaux : `unpinned_uses`, `permissions`, `secrets_in_clear`, `injection`, `pr_target`. Chaque constat a un niveau (info / avertissement / erreur) ; un commentaire `# monitor-lint: ignore RÈGLE motif` ou `lint.ignore` en réduit un au silence. | `lint.*` | Couleur du pire constat. Corriger d'abord les erreurs ; la page filtre par niveau. |

## Les contrôles de A10

Ce sont toutes des suggestions en lecture seule pour une personne ; le moniteur ne ferme jamais une issue, ne fusionne aucune pull request et ne publie aucune release. On en coupe un avec `sentinel.surface.checks.<nom>.enabled`.

| Contrôle | Ce qu'il cherche | Par défaut |
|---|---|---|
| `workflows_disabled` | Workflows désactivés à la main | on |
| `dead_schedule` | Planifications sans exécutions | on · days=14 |
| `unpinned_uses` | uses: non épinglé par SHA | on |
| `broad_permissions` | Permissions trop larges (write-all) | on |
| `pr_target` | pull_request_target avec checkout de la PR | on |
| `stuck_concurrency` | Concurrence bloquée (runs en attente du même workflow) | on · minutes=60 |
| `matrix_os` | Échecs sur un seul système de la matrice | on · max_per_tick=4 |
| `artifacts` | Coût des artifacts | on · max_mb=500, retention_days=30 |
| `required_checks` | Checks obligatoires rouges ou absents | on |
| `release_assets` | Releases publiées incomplètes | on · recent_days=30, required |
| `tag_vs_version` | Étiquette de release vs version du manifeste/CHANGELOG | on |
| `packages` | GitHub Packages | on |
| `drafts` | Brouillons et pré-releases oubliés | on · days=14 |
| `security_aged` | Alertes critiques/élevées par ancienneté (classement des dépôts) | on · days=30 |
| `coverage` | Couverture de sécurité (CodeQL / Dependabot) | on |
| `secret_resolved` | Secret scanning : ouvertes vs résolues | on |
| `dependabot_priority` | Dependabot par priorité | on |
| `issue_close` | Issues qui pourraient être fermées (simple suggestion) | on |
| `milestones` | Jalons échus par écosystème | on |
| `pr_human` | PR humaines anciennes | on · days=7 |
| `pr_workflow_touch` | PR qui modifient des workflows ou CODEOWNERS (priorité) | on |
| `merge_queue` | File de fusion : approuvées avec CI verte | on |
| `maturity` | Maturité du manifeste face aux preuves | on |
| `parity` | Parité des README en 8 langues rompue | on |
| `attestation` | Attestations de build | on · max_per_tick=3 |

## Où tout se configure

Chaque seuil ci-dessus est un réglage des onglets **Sentinelle**, **Contrôles de surface (A10)**, **Préparation (A11)**, **Dossiers et fichiers**, **Analytique** et **Linter de workflows** de la page Réglages, et une clé de `actions_monitor.json`. La liste complète avec ses plages est dans `SETTINGS_fra.md`. Le panneau d'Aide et `--help-topics sentinel` affichent cette page hors ligne.

## La seconde sentinelle et la liste des alertes

En plus de cette sentinelle (CI), l'édition complète a la **sentinelle Collab**, qui surveille les issues et pull requests ouvertes sur une horloge propre et n'écrit jamais sur GitHub : [COLLAB_fra.md](COLLAB_fra.md). L'onglet **Alertes** réunit les alertes des deux dans une liste, avec un filtre par origine et niveau et des mises en sourdine locales qui se terminent seules (`alerts.mute_hours`) ; `GET /api/alerts` sert la même liste.
