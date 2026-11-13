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

- Chaque lecture des listes de runs envoie `If-None-Match` ; GitHub répond `304 Not Modified` quand rien n'a changé et cette réponse ne coûte aucun quota. L'en-tête montre combien de lectures ont été économisées et `ghamon_etag_saved_total` les compte. `cache.etag.enabled` et `cache.etag.ttl_hours` sont dans l'onglet Réglages.
- Le cache est le fichier local `etag_cache.json` (jamais publié) ; un fichier abîmé n'est qu'un cache vide.


## Quand la connexion est perdue

Si toutes les lectures d'un cycle échouent pour un problème de connexion (pas de login ni de quota), la page garde la dernière image et affiche un bandeau rouge `pas de connexion depuis HH:MM`. Rien ne lève d'exception ; le moniteur reprend seul et écrit un événement `offline` et un `online`, une fois chacun (ils peuvent être notifiés). `ghamon_offline` vaut 1 entre-temps.

## Combien de temps l'historique est conservé

En plus de `keep_days` du bloc d'analyses, le passage de conservation supprime les jours de l'historique plus anciens que `retention.analytics_days` (180 par défaut) ; les échantillons eux-mêmes sont limités par `max_samples`. Voir [STORAGE_fra.md](STORAGE_fra.md).
