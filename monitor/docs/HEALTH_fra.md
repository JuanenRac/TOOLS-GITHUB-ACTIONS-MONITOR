<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](HEALTH.md) | [🇪🇸 Español](HEALTH_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](HEALTH_ita.md) | [🇩🇪 Deutsch](HEALTH_deu.md) | [🇨🇳 简体中文](HEALTH_zho.md) | [🇯🇵 日本語](HEALTH_jpn.md) | [🇵🇹 Português](HEALTH_por.md)

# La santé d'un dépôt et de l'équipe

Complete seulement. Deux vues en lecture seule, faites avec ce que le moniteur détient déjà (exécutions, workflows rouges et bloqués, alertes ouvertes de chaque sentinelle et préparation des versions). Elles n'appellent jamais GitHub.

## De quoi est faite la santé d'un dépôt

| Partie | Ce qu'elle dit |
|---|---|
| CI | succès et échecs des dernières 24 heures, les workflows rouges maintenant, les exécutions bloquées |
| Alertes | toutes les alertes ouvertes des sentinelles CI, Collab et Sécurité, par sentinelle et par niveau |
| Version | la ligne de préparation des versions, si le dépôt en a une |
| Activité | quand la dernière exécution a commencé et combien il y en a eu en 7 jours |
| Qui l'a regardé | le cycle de vie de chaque sentinelle : sain, dégradé, en pause, en erreur ou éteint |

L'état est **mauvais** (un workflow rouge, ou une alerte de niveau critique ou erreur), **avertissement** (une alerte d'avertissement ou une exécution bloquée), **bon** ou **non vu** (rien pour juger). Un dépôt qu'aucune sentinelle n'a regardé, ou qu'une sentinelle n'a pas pu lire, n'est jamais montré comme bon : il dit « pas entièrement vu par » et liste qui. Le risque est le nombre qui trie le classement : chaque workflow rouge (30), exécution bloquée (10), alerte critique (25), d'erreur (10), d'avertissement (3) et d'information (1) ajoute des points, les mêmes pour tous les dépôts. Quand toutes les sentinelles sont en erreur, en pause ou dégradées (ou toutes éteintes et que rien n'a tourné depuis une semaine), un dépôt calme est affiché comme non vu, jamais comme OK, et sa ligne dans le classement porte un astérisque et nomme les sentinelles qui n'ont pas pu le lire (`not_fully_seen` ; les totaux les comptent aussi).

## Où la voir

- L'onglet **Équipe** : le classement (d'abord les dépôts qui demandent une personne), les totaux, les chiffres par écosystème et par sentinelle, et trois filtres : écosystème, gravité minimale et un morceau du nom. Cliquez sur un dépôt pour son détail.
- Liens directs pour écrans muraux : `?view=team&chrome=0`, `?view=repos&chrome=0` et `?view=repo&repo=owner/name&chrome=0`.
- L'API : `GET /api/team/health?ecosystem=&severity=&q=&label=` et `GET /api/repos/<owner>/<repo>/health`. Toutes deux demandent le droit de voir le compte ; les réponses portent `schema: 1`. Un dépôt inconnu répond 404 avec `code: repo_unknown`.
- L'édition Lite garde sa vue simple des exécutions et n'a ni l'onglet ni les routes.

## Des milliers de dépôts et une horloge reculée

La santé de l'équipe regroupe une seule fois par dépôt les exécutions, les workflows rouges, les exécutions en cours et les alertes ; le coût croît donc avec la quantité de données et non avec dépôts fois exécutions ; demander un seul dépôt ne construit que sa vue.

Un instant enregistré qui se trouve dans le futur (un ordinateur sans horloge à pile qui démarre avec une vieille date, ou une horloge corrigée à la main) n'est pas cru : la note, la purge des anciennes données et les rapports programmés sont dus aussitôt et écrivent un bon instant, au lieu d'attendre que la vieille horloge soit atteinte.

## La vue de flotte (des centaines de dépôts)

L'onglet **Équipe** a une seconde section, *Flotte*, pour les comptes de centaines de dépôts. Elle groupe les dépôts (`fleet.group_by` : écosystème, étiquette, état ou aucun), trie chaque groupe (`fleet.sort` : risque, nom, dernière exécution ou état) et dessine `fleet.page_size` lignes à la fois (50 par défaut) avec Précédent et Suivant. La page reçoit toutes les lignes une fois de `GET /api/team/fleet?ecosystem=&severity=&q=&label=&group=&sort=&saved=` (lecture seule, 5 000 lignes au plus ; `truncated` signale une coupure) et ne dessine qu'une page, la taille du compte ne la ralentit donc pas.

Une *étiquette* est un motif de noms de dépôt : `fleet.labels` accepte des lignes comme `team-*=backend` ; le premier motif qui correspond donne l'étiquette, et grouper par étiquette permet de distinguer organisations ou équipes dans un seul moniteur. `fleet.saved_filters` accepte des lignes comme `attention=bad||backend|` (nom, gravité minimale, écosystème, étiquette, texte ; toute partie après le nom peut être vide) et les affiche comme filtres prêts à l'emploi. Le classement au-dessus de la flotte ne change pas.

**Toutes les exécutions en cours.** La santé d'un dépôt (`active`, dans la fenêtre du dépôt sous *En cours maintenant*) compte les exécutions encore en cours workflow par workflow : deux exécutions du même workflow qui tournent en même temps (publications en parallèle, une exécution par branche) sont toutes deux comptées, avec combien tournent et combien attendent et l'exécution la plus récente de chaque branche, et les lignes de la flotte portent `running` et `queued`. Avec `fleet.show_all_active` désactivé, un workflow n'affiche que son exécution la plus récente.
