<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_SECURITY.md) | [🇪🇸 Español](SENTINEL_SECURITY_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](SENTINEL_SECURITY_ita.md) | [🇩🇪 Deutsch](SENTINEL_SECURITY_deu.md) | [🇨🇳 简体中文](SENTINEL_SECURITY_zho.md) | [🇯🇵 日本語](SENTINEL_SECURITY_jpn.md) | [🇵🇹 Português](SENTINEL_SECURITY_por.md)

# La sentinelle de sécurité

La troisième sentinelle, à côté de celle de la CI et de Collab. Elle lit, sans rien écrire sur GitHub, ce que GitHub lui-même dit d'ouvert ou de manquant en matière de sécurité pour chaque dépôt, et en fait des alertes de l'onglet Alertes (origine Sécurité). Elle existe dans l'édition Complete, désactivée par défaut (`sentinels.security.enabled`) ; Lite n'a pas de sentinelles.

Le même onglet porte un cadre facultatif avec la [posture des dépôts et de l'organisation face à OWASP et CIS](POSTURE_fra.md).

## Ce qu'elle lit et ce qu'elle signale

| Signal | Alerte | Niveau | Actif par défaut |
|---|---|---|---|
| Alertes Dependabot ouvertes de gravité `min_severity` ou plus (high par défaut) | `security.dependabot` | critique si l'une est critique, erreur si l'une est élevée, sinon avertissement | oui |
| Alertes d'analyse de code ouvertes de gravité `min_severity` ou plus | `security.code_scanning` | idem | oui |
| Alertes d'analyse des secrets ouvertes | `security.secret` | toujours critique (un secret trouvé par GitHub est un secret exposé) | oui |
| La branche par défaut n'a aucune protection | `security.branch_unprotected` | avertissement | oui |
| Les workflows reçoivent l'écriture par défaut | `security.workflow_write` | avertissement | oui |
| Il n'y a pas de fichier CODEOWNERS | `security.codeowners_missing` | information | non |
| Une exécution importante (push sur la branche par défaut, exécution manuelle, exécution `pull_request_target`) vue par le moniteur a été supprimée | `security.runs_deleted` | error | non |

**Exécutions supprimées** (`security.runs_deleted`, désactivé par défaut) : après une fuite de secrets, supprimer l'exécution qui les a affichés est le moyen habituel d'effacer la trace, et GitHub n'en laisse aucune trace visible. Avec `sentinels.security.signals.runs_deleted.enabled`, la sentinelle garde une courte liste privée des exécutions importantes qu'elle a vues et, quand l'une ne figure plus dans la liste des exécutions, interroge cette seule exécution : un 404 explicite est une suppression ; un refus (403), une erreur réseau ou un 5xx ne compte jamais. Une exécution plus ancienne que `sentinels.security.signals.runs_deleted.check_window_days` (14) n'est pas interrogée (la rétention du compte a pu la purger) et une suppression constatée reste signalée pendant le même nombre de jours. Au plus `sentinels.security.signals.runs_deleted.max_checks` (50) exécutions isolées sont interrogées par dépôt et par tour. L'alerte nomme le workflow, qui l'a lancé et la branche, jamais le contenu de l'exécution.

Il y a une alerte par dépôt et par signal, avec le décompte par gravité dans ses détails. Chaque signal peut être désactivé (`sentinels.security.signals.<signal>.enabled`) et, pour Dependabot et l'analyse de code, recevoir une autre gravité minimale. D'un dépôt archivé, on ne demande rien d'autre.

## Ce qu'elle n'a pas pu vérifier

Une source que GitHub ne renvoie pas pour un dépôt (la fonction y est désactivée, ou le compte ne peut pas la lire : 403, 404) n'est **pas** une alerte et n'est **pas** un certificat de bonne santé. Elle est listée dans l'état sous `unavailable`, avec le nombre de dépôts concernés, et la page le dit. La seule exception est la protection de la branche par défaut : GitHub répond 404 pour une branche qui n'en a aucune, et c'est le constat ; un 403 n'y est que « illisible ».

Quand la plus grande partie de ce qui pèse dans la pénalité (Dependabot, analyse de code, secrets) ne peut pas être lue, le niveau est `unknown` et non `ok`, et la part sécurité du score est écartée au lieu de compter pour 100 ; l'état montre `sources_readable` et `sources_total`. Si une source cesse de répondre alors qu'une alerte est ouverte, l'alerte reste une semaine (marquée `unread_since`) et n'est jamais annoncée comme corrigée. Un dépôt dont les lectures échouent toujours attend 5 minutes, 30 minutes puis 6 heures avant le prochain essai, de sorte que quelques dépôts cassés n'épuisent jamais toute la ronde.

Une source que l'offre du compte n'a pas (protection de branche ou analyse de code d'un dépôt privé avec l'offre gratuite : GitHub répond que la fonction demande une autre offre) se distingue d'un refus et d'une fonction désactivée : la page et `unavailable_why` de l'état disent `N/A (offre)`, `N/A (pas d'accès)` ou `N/A (désactivé)`. Avec `sentinels.security.plan_na` activé (par défaut), les sources du premier type sortent du décompte du lisible et de la couverture de la note et sont comptées à part comme `sources_na_plan` ; aucun des trois cas n'est un constat ni un brevet de propreté, et une sentinelle dont l'offre n'a rien de ce qui pèse est `unknown` et ne donne aucune partie sécurité à la note. Désactivé, elles comptent comme des sources illisibles.

Chaque sentinelle indique désormais son **cycle de vie** : `healthy` (sain), `degraded` (dégradé : certaines lectures échouent, une source est illisible ou le premier passage n'est pas terminé), `paused` (en pause, en attente du quota GitHub), `error` (elle échoue et n'a encore rien lu) ou `off` (désactivée). « Aucune alerte » ne signifie quelque chose que si le cycle de vie est `healthy`.

## Coût

Un tour lit au plus `sentinels.security.max_repos_per_tick` dépôts (5 par défaut), les moins récemment vus d'abord et ceux qui ont une alerte ouverte un peu plus tôt, avec un cycle toutes les `sentinels.security.refresh_seconds` (30 minutes par défaut). Chaque dépôt coûte au plus sept lectures, presque toutes conditionnelles : un dépôt inchangé ne consomme pas de quota ; le fichier CODEOWNERS, quand il est demandé, n'est cherché qu'une fois par jour. La sentinelle se met en pause tant que le quota restant est inférieur à `sentinels.security.min_rate_remaining`. Son état (`security_state.json`) garde les alertes ouvertes : un redémarrage n'annonce rien de nouveau, et le premier passage sur un dépôt n'écrit aucun évènement. Un tour cesse aussi de commencer de nouveaux dépôts après `sentinels.security.deadline_s` secondes (30 par défaut ; 0 = aucun plafond) : ceux qui n'ont pas été atteints attendent le tour suivant et l'état les liste par nom comme `unchecked` (avec `round_cut`) au lieu de les compter pour zéro alerte.

## Un seul propriétaire par constat

Les panneaux de l'onglet Sentinelle qui montraient déjà des chiffres de sécurité (alertes par dépôt, alertes anciennes, couverture de Dependabot et CodeQL, pull requests Dependabot) restent des panneaux. Les alertes de l'onglet Alertes sur ces signaux viennent uniquement de cette sentinelle : rien n'est levé deux fois. Le contenu de chaque fichier de workflow (actions non épinglées à un commit, `write-all`, pas de bloc de permissions, `pull_request_target` avec récupération) relève de la [sentinelle de chaîne d'approvisionnement](SENTINEL_SUPPLY_fra.md) ; `security.workflow_write` reste ici car c'est un réglage du dépôt.

## Évènements et notifications

Un nouveau constat écrit l'évènement `security_new` et un constat clos `security_fixed` dans le flux, auquel sont accrochés les canaux de notification ; ce sont deux types que la personne peut demander dans les réglages des notifications, et les préférences par utilisateur ont une case Sécurité. Rien n'est annoncé la première fois qu'un dépôt est examiné.

## Les réglages

Dans la page des réglages, sous-onglet Sentinelle, bloc Sécurité : `sentinels.security.enabled`, `sentinels.security.refresh_seconds`, `sentinels.security.max_repos_per_tick`, `sentinels.security.min_rate_remaining`, `sentinels.security.repos`, `sentinels.security.plan_na`, `sentinels.security.signals.dependabot.enabled`, `sentinels.security.signals.dependabot.min_severity`, `sentinels.security.signals.code_scanning.enabled`, `sentinels.security.signals.code_scanning.min_severity`, `sentinels.security.signals.secret.enabled`, `sentinels.security.signals.branch.enabled`, `sentinels.security.signals.workflow.enabled` et `sentinels.security.signals.codeowners.enabled`, `sentinels.security.signals.runs_deleted.enabled`, `sentinels.security.signals.runs_deleted.check_window_days`, `sentinels.security.signals.runs_deleted.max_checks`. Les points que chaque constat retire à la partie sécurité du score (`sentinels.security.penalty`) sont lus dans le fichier ; voir le fichier d'exemple.

## Protection de branche par ruleset

Une branche par défaut compte comme protégée si elle a la protection classique de branche **ou** un ruleset actif (GitHub répond 404 au point d'accès classique pour un dépôt protégé uniquement par ruleset ; la sentinelle lit donc aussi l'indicateur `protected` de la branche et les règles actives de la branche). `signals.branch.require` peut lister des types de règle (par exemple `pull_request`, `required_status_checks`) que les règles doivent avoir ; une branche protégée à laquelle il en manque est signalée avec celles qui manquent. Par défaut la liste est vide : toute protection suffit. Un dépôt qui n'a pas pu être lu parce que l'appel a dépassé le délai est listé avec sa cause (`timeout`, `rate`, `network`, `error`) dans `errors` et `error_kinds` de l'état ; ce n'est jamais un constat.
