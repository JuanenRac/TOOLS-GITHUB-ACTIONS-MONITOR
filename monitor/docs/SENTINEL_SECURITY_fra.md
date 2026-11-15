<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_SECURITY.md) | [🇪🇸 Español](SENTINEL_SECURITY_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](SENTINEL_SECURITY_ita.md) | [🇩🇪 Deutsch](SENTINEL_SECURITY_deu.md) | [🇨🇳 简体中文](SENTINEL_SECURITY_zho.md) | [🇯🇵 日本語](SENTINEL_SECURITY_jpn.md) | [🇵🇹 Português](SENTINEL_SECURITY_por.md)

# La sentinelle de sécurité

La troisième sentinelle, à côté de celle de la CI et de Collab. Elle lit, sans rien écrire sur GitHub, ce que GitHub lui-même dit d'ouvert ou de manquant en matière de sécurité pour chaque dépôt, et en fait des alertes de l'onglet Alertes (origine Sécurité). Elle existe dans l'édition Complete, désactivée par défaut (`sentinels.security.enabled`) ; Lite n'a pas de sentinelles.

## Ce qu'elle lit et ce qu'elle signale

| Signal | Alerte | Niveau | Actif par défaut |
|---|---|---|---|
| Alertes Dependabot ouvertes de gravité `min_severity` ou plus (high par défaut) | `security.dependabot` | critique si l'une est critique, erreur si l'une est élevée, sinon avertissement | oui |
| Alertes d'analyse de code ouvertes de gravité `min_severity` ou plus | `security.code_scanning` | idem | oui |
| Alertes d'analyse des secrets ouvertes | `security.secret` | toujours critique (un secret trouvé par GitHub est un secret exposé) | oui |
| La branche par défaut n'a aucune protection | `security.branch_unprotected` | avertissement | oui |
| Les workflows reçoivent l'écriture par défaut | `security.workflow_write` | avertissement | oui |
| Il n'y a pas de fichier CODEOWNERS | `security.codeowners_missing` | information | non |

Il y a une alerte par dépôt et par signal, avec le décompte par gravité dans ses détails. Chaque signal peut être désactivé (`sentinels.security.signals.<signal>.enabled`) et, pour Dependabot et l'analyse de code, recevoir une autre gravité minimale. D'un dépôt archivé, on ne demande rien d'autre.

## Ce qu'elle n'a pas pu vérifier

Une source que GitHub ne renvoie pas pour un dépôt (la fonction y est désactivée, ou le compte ne peut pas la lire : 403, 404) n'est **pas** une alerte et n'est **pas** un certificat de bonne santé. Elle est listée dans l'état sous `unavailable`, avec le nombre de dépôts concernés, et la page le dit. La seule exception est la protection de la branche par défaut : GitHub répond 404 pour une branche qui n'en a aucune, et c'est le constat ; un 403 n'y est que « illisible ».

Chaque sentinelle indique désormais son **cycle de vie** : `healthy` (sain), `degraded` (dégradé : certaines lectures échouent, une source est illisible ou le premier passage n'est pas terminé), `paused` (en pause, en attente du quota GitHub), `error` (elle échoue et n'a encore rien lu) ou `off` (désactivée). « Aucune alerte » ne signifie quelque chose que si le cycle de vie est `healthy`.

## Coût

Un tour lit au plus `sentinels.security.max_repos_per_tick` dépôts (5 par défaut), les moins récemment vus d'abord et ceux qui ont une alerte ouverte un peu plus tôt, avec un cycle toutes les `sentinels.security.refresh_seconds` (30 minutes par défaut). Chaque dépôt coûte au plus sept lectures, presque toutes conditionnelles : un dépôt inchangé ne consomme pas de quota ; le fichier CODEOWNERS, quand il est demandé, n'est cherché qu'une fois par jour. La sentinelle se met en pause tant que le quota restant est inférieur à `sentinels.security.min_rate_remaining`. Son état (`security_state.json`) garde les alertes ouvertes : un redémarrage n'annonce rien de nouveau, et le premier passage sur un dépôt n'écrit aucun évènement.

## Un seul propriétaire par constat

Les panneaux de l'onglet Sentinelle qui montraient déjà des chiffres de sécurité (alertes par dépôt, alertes anciennes, couverture de Dependabot et CodeQL, pull requests Dependabot) restent des panneaux. Les alertes de l'onglet Alertes sur ces signaux viennent uniquement de cette sentinelle : rien n'est levé deux fois.

## Évènements et notifications

Un nouveau constat écrit l'évènement `security_new` et un constat clos `security_fixed` dans le flux, auquel sont accrochés les canaux de notification ; ce sont deux types que la personne peut demander dans les réglages des notifications, et les préférences par utilisateur ont une case Sécurité. Rien n'est annoncé la première fois qu'un dépôt est examiné.

## Les réglages

Dans la page des réglages, sous-onglet Sentinelle, bloc Sécurité : `sentinels.security.enabled`, `sentinels.security.refresh_seconds`, `sentinels.security.max_repos_per_tick`, `sentinels.security.min_rate_remaining`, `sentinels.security.repos`, `sentinels.security.signals.dependabot.enabled`, `sentinels.security.signals.dependabot.min_severity`, `sentinels.security.signals.code_scanning.enabled`, `sentinels.security.signals.code_scanning.min_severity`, `sentinels.security.signals.secret.enabled`, `sentinels.security.signals.branch.enabled`, `sentinels.security.signals.workflow.enabled` et `sentinels.security.signals.codeowners.enabled`. Les points que chaque constat retire à la partie sécurité du score (`sentinels.security.penalty`) sont lus dans le fichier ; voir le fichier d'exemple.
