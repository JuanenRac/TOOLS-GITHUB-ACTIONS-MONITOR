<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ANALYTICS.md) | [🇪🇸 Español](ANALYTICS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](ANALYTICS_ita.md) | [🇩🇪 Deutsch](ANALYTICS_deu.md) | [🇨🇳 简体中文](ANALYTICS_zho.md) | [🇯🇵 日本語](ANALYTICS_jpn.md) | [🇵🇹 Português](ANALYTICS_por.md)

# Analyses, lectures conditionnelles et connexion perdue

Ce que le moniteur apprend des runs qu'il lit déjà, comment il économise le quota et survit à une coupure réseau. Tout est local ; rien n'est envoyé nulle part.

## Durées, temps en file et étapes

- `p50` et `p95` de la durée des runs réussis de chaque workflow ; du temps qu'un job a attendu avant de démarrer (créé à démarré) ; et de chaque étape d'un workflow. Un workflow affiche des chiffres dès qu'il a `analytics.min_samples` échantillons.
- Les temps des jobs et des étapes demandent les jobs des runs terminés : jusqu'à `analytics.jobs_per_cycle` runs par cycle, chacun lu une fois (0 n'en lit aucun). Le webhook entrant les fournit gratuitement.
- Ils sont exportés en `ghamon_workflow_duration_seconds`, `ghamon_job_queue_seconds` et `ghamon_step_duration_seconds` (étiquette `quantile` 0.5 / 0.95 ; demande `per_repo`) et dans la source JSON de Grafana (`durations`, `queue`). `slower` liste les workflows dont le p50 vaut `analytics.slow_factor` fois l'habituel.


## Workflows instables (flaky)

Un workflow qui a ÉCHOUÉ puis RÉUSSI sur le même commit (ou dont le run a demandé une autre tentative) est étiqueté instable : `ghamon_workflow_flaky_rate`. Ce n'est qu'une étiquette : ce qui compte comme rouge ne change pas.


## Lectures conditionnelles (ETag)

- Chaque lecture des listes de runs envoie `If-None-Match` ; GitHub répond `304 Not Modified` quand rien n'a changé et cette réponse ne coûte aucun quota. L'en-tête montre combien de lectures ont été économisées et `ghamon_etag_saved_total` les compte. `cache.etag.enabled` et `cache.etag.ttl_hours` sont dans l'onglet Réglages. Chaque entrée appartient à l'identifiant qui l'a lue (une courte empreinte du jeton fait partie de la clé, jamais le jeton), donc un `304` ne renvoie jamais le corps d'une autre identité. Un état qui bouge encore est toujours lu en entier : les jobs d'une exécution, une exécution seule, les suites et contrôles (`cache.etag.skip_stateful`) et toute liste d'exécutions dont la dernière réponse contenait encore une exécution en attente ou en cours (`cache.etag.revalidate_active`). Un refus (404 ou 403 hors limite de débit) est retenu `cache.negative_ttl_s` secondes. `/metrics` compte aussi les réponses sans ETag, les lectures faites en entier à dessein et les refus non répétés, et le brief pour les outils d'IA a le signal quota.etag.
- Le brief pour les outils d'IA nomme schema.drift quand GitHub a envoyé un état ou une conclusion que le moniteur ne connaît pas, ou une exécution sans numéro utilisable : la valeur inconnue est montrée telle qu'elle est venue et n'est jamais comptée comme rouge ou verte.
- Le cache est le fichier local `etag_cache.json` (jamais publié) ; un fichier abîmé n'est qu'un cache vide.


## Quand la connexion est perdue

Si toutes les lectures d'un cycle échouent pour un problème de connexion (pas de login ni de quota), la page garde la dernière image et affiche un bandeau rouge `pas de connexion depuis HH:MM`. Rien ne lève d'exception ; le moniteur reprend seul et écrit un événement `offline` et un `online`, une fois chacun (ils peuvent être notifiés). `ghamon_offline` vaut 1 entre-temps.

## Combien de temps l'historique est conservé

En plus de `keep_days` du bloc d'analyses, le passage de conservation supprime les jours de l'historique plus anciens que `retention.analytics_days` (180 par défaut) ; les échantillons eux-mêmes sont limités par `max_samples`. Voir [STORAGE_fra.md](STORAGE_fra.md).


## Temps gagné (une estimation)

Désactivé par défaut (`productivity.enabled`). Activée, la section montre, tâche par tâche, combien de minutes par semaine le moniteur fait gagner, avec la formule de [PRODUCTIVITY_fra.md](PRODUCTIVITY_fra.md) : fois par semaine x minutes à chaque fois sans le moniteur x gain de la tâche.

- Deux tâches sont chiffrées. **Surveiller** (regarder les onglets Actions à la main et décider ce qui est rouge) prend le nombre de fois par semaine et les minutes dans vos notes (`productivity.watch_times_per_week`, `productivity.watch_minutes_before`). **Diagnostic** (trouver la cause d'une exécution échouée) compte les exécutions échouées que le moniteur a en vue sur `productivity.window_days` et prend les minutes dans vos notes (`productivity.triage_minutes_before`).
- Le moniteur ne peut pas voir ce que vous faisiez avant son installation. Une tâche sans ces notes indique **pas de données** et aucun chiffre n'est inventé. Le total indique aussi pas de données tant qu'aucune tâche n'a ses notes.
- Si vous avez aussi noté les minutes avec le moniteur (`productivity.watch_minutes_after`, `productivity.triage_minutes_after`), le gain est mesuré d'après vos notes : 1 - après / avant. Sinon c'est le pourcentage de `productivity.saving_percent` (90 par défaut) et le tableau indique **supposé (non mesuré)**.
- Avec `productivity.team_hours_per_week`, l'estimation dit aussi quelle part du temps de travail représentent les minutes gagnées.
- Corriger un échec prend le même temps avec ou sans le moniteur et n'est jamais compté. Seules les exécutions échouées que le moniteur détient sont comptées : une très longue liste d'exécutions peut contenir plus d'échecs que ceux affichés.
- Local et en lecture seule : aucun appel à GitHub, rien ne quitte l'ordinateur. C'est dans `/api/analytics` (`time_saved`), dans le résumé du panneau A12 et dans le brief de l'onglet Résumé pour les outils d'IA.
