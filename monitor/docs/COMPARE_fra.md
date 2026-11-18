<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPARE.md) | [🇪🇸 Español](COMPARE_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](COMPARE_ita.md) | [🇩🇪 Deutsch](COMPARE_deu.md) | [🇨🇳 简体中文](COMPARE_zho.md) | [🇯🇵 日本語](COMPARE_jpn.md) | [🇵🇹 Português](COMPARE_por.md)

# Comparer les périodes

Comment s'est passée cette semaine par rapport à la précédente ? La comparaison y répond avec ce que le moniteur détient déjà (le registre des exécutions et des alertes terminées et les relevés horaires du score). Elle ne lit rien sur GitHub, n'écrit rien, n'a pas besoin d'IA et n'invente rien. Elle n'existe que dans l'édition Complete et reste **désactivée** tant que vous n'activez pas `compare.enabled`.

## Les deux périodes

- **Période** : les 7 derniers jours (ou 30, ou tout nombre jusqu'à 90), ou une plage exacte avec `from` et `to`.
- **Référence** : `previous` (la période de même durée juste avant, par défaut), `year_ago` (les mêmes dates un an plus tôt) ou `custom` (`base_from` et `base_to`).
- **Jours** : `all`, `workdays` ou `weekend`. Le filtre s'applique à tous les chiffres. Le jour d'un instant est son jour dans le fuseau de `display.timezone` ; les jours ouvrés sont `compare.workdays` (lundi = 1 à dimanche = 7, du lundi au vendredi par défaut). Les jours fériés ne sont pas connus : un jour férié compte comme le jour de la semaine où il tombe.

Mélanger jours ouvrés et week-ends cache des choses (un échec qui n'arrive que le samedi pèse peu dans une semaine de données mélangées), d'où le filtre.

## Les chiffres

| Chiffre | Calcul | Mieux quand |
|---|---|---|
| `red_rate` | exécutions en échec / (réussies + en échec) commencées dans la période | plus bas |
| `duration_p50` | médiane des secondes des exécutions réussies | plus bas |
| `resolution` | médiane du temps entre l'ouverture et la fermeture des alertes de la sentinelle de collaboration fermées dans la période | plus bas |
| `score_mean` | score moyen des relevés horaires qui avaient un nombre | plus haut |
| `score_coverage` | part moyenne du score qui avait des données | plus haut |

Chaque chiffre voyage avec `now`, `base`, `delta`, une `direction` (`better`, `worse`, `same`) et son `state`. Les exécutions annulées, ignorées et inachevées ne comptent dans aucun sens.

## Quand il n'y a pas de chiffre

La comparaison n'affiche jamais un nombre qu'elle ne peut garantir : un chiffre manquant vaut `null`, jamais 0 ni 100.

- `insufficient_data` : moins d'exécutions terminées que `compare.min_runs_per_window`, moins d'alertes résolues que `compare.min_resolved` ou moins de relevés que `compare.min_snapshots` dans l'une des deux périodes. La réponse dit laquelle et pourquoi (`missing`).
- `baseline_unavailable` : la période de référence n'est pas fiable. Le motif est `history_too_short` (le moniteur surveille depuis moins de `compare.min_days_of_history` jours), `before_history` (cette période est antérieure aux données conservées) ou `no_history`. Les chiffres de la période actuelle restent affichés.
- `calibrating` : le moniteur n'a pas encore surveillé `score.calibrating_hours` heures. Rien n'est comparé.
- `off` : `compare.enabled` est désactivé.

`data_quality` porte les exécutions comptées dans chaque période et `truncated` quand le registre a dû abandonner d'anciennes exécutions. `coverage` est la part des chiffres qui ont pu être comparés.

## Ce qui a changé

Outre les chiffres : les dépôts qui se dégradent ou s'améliorent (variation de leur part d'exécutions en échec, seulement ceux qui ont au moins `compare.min_repo_runs` exécutions dans les deux périodes), les workflows qui se mettent à échouer et ceux qui n'échouent plus, et le nombre d'alertes ouvertes dans la période et encore ouvertes à sa fin. Chaque liste a au plus `compare.top_changes` lignes, classées par l'ampleur du changement puis par nom. Le registre ne garde pas de dépôt pour les alertes de la sentinelle de collaboration : elles apparaissent en nombres, jamais par nom.

## Jusqu'où elle remonte

La comparaison lit le registre du score. Tant que `compare.enabled` est actif, le registre conserve deux périodes de `compare.default_window_days` (au moins 15 jours) au lieu des deux fenêtres du score ; il n'est jamais plus ancien que le moniteur, donc une nouvelle installation ne peut comparer 30 jours à 30 jours qu'avec 60 jours d'historique.

## L'API

`GET /api/compare?window=7&days=workdays&baseline=previous` (aussi `from`, `to`, `base_from`, `base_to`). Elle répond `state`, `windows`, `metrics`, `changes`, `alerts`, `coverage` et `data_quality`. `format=ndjson` ou `format=csv` donnent une ligne par chiffre. Une demande absurde est un 400 avec un `code` stable : `bad_range` (from après to, plus de 90 jours, dans le futur), `bad_window`, `bad_days`, `bad_baseline` ou `bad_format`. Un lecteur peut la consulter ; elle sert le compte du processus, jamais un autre. Avec l'API de lecture v1 activée, elle est aussi servie sous le préfixe `/api/v1/`. Elle n'existe pas dans l'édition Lite.

## La ligne de commande

`monitor_cli.py compare [--window 7|30d] [--days all|workdays|weekend] [--baseline previous|year_ago] [--format table|json|ndjson|csv]`. Codes de sortie : 0 tout a pu être comparé ; 4 un chiffre manque de données, il n'y a pas de référence ou la comparaison est désactivée ; 5 avec `--fail-on` quand un chiffre se dégrade. `score --compare` continue de comparer le score à l'historique de sa fenêtre.

## Sur la page

L'onglet Graphiques affiche la section « Comparer les périodes » quand la comparaison est active : un sélecteur de période, de jours et de référence, une ligne par chiffre avec sa variation, les alertes et les listes de changements.

## Les réglages

Réglages, onglet Sentinelle, bloc Comparaison de périodes : `compare.enabled`, `compare.default_window_days`, `compare.default_days_filter`, `compare.workdays`, `compare.min_runs_per_window`, `compare.min_days_of_history`, `compare.min_resolved`, `compare.min_snapshots`, `compare.min_repo_runs`, `compare.top_changes`, `compare.include_in_report` et `compare.cache_seconds`. Une réponse est conservée `compare.cache_seconds` secondes puis recalculée.
