<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COLLAB.md) | [🇪🇸 Español](COLLAB_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](COLLAB_ita.md) | [🇩🇪 Deutsch](COLLAB_deu.md) | [🇨🇳 简体中文](COLLAB_zho.md) | [🇯🇵 日本語](COLLAB_jpn.md) | [🇵🇹 Português](COLLAB_por.md)

# La sentinelle Collab : issues et pull requests

Une seconde sentinelle à côté de celle de la CI. Elle regarde les **issues et pull requests ouvertes** de vos dépôts et vous dit ce qui demande une personne : issues oubliées, étiquettes critiques, revues que personne ne fait, brouillons sans fin, conflits qui restent. Elle a sa propre horloge, ne change jamais ce que décide la sentinelle CI et **n'écrit jamais sur GitHub**. Elle fait partie de l'édition complète ; l'édition lite ne la charge pas.

## L'activer

Elle est désactivée par défaut. Réglages > Sentinelle > Issues et pull requests, ou dans `actions_monitor.json` :

```
"sentinels": {"collab": {"enabled": true, "refresh_seconds": 600, "max_repos_per_tick": 10, "repos": "all",
  "rules": {"issue_stale_days": 14, "issue_critical_labels": ["security", "critical"], "pr_review_pending_days": 3,
            "pr_draft_max_days": 30, "pr_conflict_days": 7, "watch_external_comments": false, "ignore_labels": ["monitor:ignore"]}}}
```

`repos` vaut `"all"`, une liste de dépôts ou `{"ecosystems": [...]}`.

## Les règles (codes stables)

| Code | Niveau | Quand |
|---|---|---|
| `collab.issue.stale` | avertissement | une issue ouverte sans activité depuis `issue_stale_days` |
| `collab.issue.critical` | erreur | une issue ouverte avec une étiquette de `issue_critical_labels`, quel que soit son âge |
| `collab.issue.external` | avertissement | (seulement avec `watch_external_comments`) une issue d'une personne extérieure à l'équipe à laquelle personne n'a répondu après un jour |
| `collab.pr.review_pending` | avertissement | une pull request avec une revue demandée qui attend depuis `pr_review_pending_days` |
| `collab.pr.draft_old` | info | une pull request en brouillon ouverte depuis `pr_draft_max_days` |
| `collab.pr.conflict` | avertissement | une pull request en conflit depuis `pr_conflict_days` |

Les robots sont exclus. Les valeurs par défaut sont lentes à dessein : un brouillon qui attend des mois est normal dans beaucoup d'équipes.

## Ce que cela coûte

Un tour lit au plus `max_repos_per_tick` dépôts, avec deux requêtes conditionnelles chacun (un dépôt inchangé ne coûte pas de quota) et jusqu'à six détails de pull request par tour. Elle s'arrête tant que le quota est sous `min_rate_remaining`. L'état est gardé dans `collab_state.json` (dans le dossier du compte s'il y en a plusieurs) : un redémarrage n'annonce rien deux fois. Un tour cesse aussi de commencer de nouveaux dépôts après `sentinels.collab.deadline_s` secondes (30 par défaut ; 0 = aucun plafond) : ceux qui n'ont pas été atteints attendent le tour suivant et l'état les liste par nom comme `unchecked` (avec `round_cut`) au lieu de les compter comme zéro alerte.

## Moins de bruit : ignorer et mettre en sourdine

- **Étiquette d'exclusion** : posez sur GitHub une étiquette de `ignore_labels` (`monitor:ignore` par défaut) sur l'issue ou la pull request et Collab ne lève plus d'alerte pour elle. Le moniteur n'écrit jamais d'étiquette lui-même.
- **Sourdine dans le moniteur** : dans l'onglet Alertes, chaque alerte a des boutons pour mettre en sourdine cette alerte, sa règle ou toute la sentinelle pendant `alerts.mute_hours` heures (24 par défaut, de 1 à 720). Elle expire seule, se rétablit à tout moment, et l'onglet garde un court historique de ce qui a été coupé et jusqu'à quand. C'est une note de ce moniteur ; rien ne change sur GitHub. En mode réseau, un silence ne peut être posé (et levé) que depuis l'ordinateur où tourne le moniteur (`this_computer`) ; un client du réseau voit les silences mais ne peut pas les changer. Cela reste ainsi jusqu'à ce qu'une édition ultérieure ait ses propres utilisateurs. Le silence d'une alerte peut aussi durer « jusqu'à ce que l'élément change » (`until_change` dans la requête de `POST /api/alerts/mute`) : il prend fin dès que l'`updated_at` de l'issue ou de la pull request change, ou à la fin des heures, selon ce qui arrive en premier. Dans l'onglet Alertes, c'est le bouton **Jusqu'au changement**, affiché sur les alertes qui portent le `updated_at` de leur élément (celles de la sentinelle Collab) ; l'alerte en sourdine indique alors « en sourdine jusqu'au changement ».

## Où le voir

- L'onglet **Alertes** : une liste pour toutes les sentinelles, un filtre par origine (CI, Collab) et par niveau, et les alertes en sourdine sur demande.
- L'onglet Sentinelle : la couche *Issues et pull requests*.
- `GET /api/alerts?sentinel=collab&level=&muted=show|hide|only` et `GET /api/sentinel/collab` ; `GET /api/events?sentinel=collab&since=` pour les évènements (`collab_new`, `collab_fixed`, que les canaux de notification envoient aussi si vous les choisissez ; voir NOTIFICATIONS).

## Limites

Seules les 100 premières issues ouvertes et les 100 premières pull requests ouvertes de chaque dépôt sont lues, les plus récemment mises à jour d'abord. Collab ne propose rien et n'exécute rien ; les actions sur les issues et les pull requests relèvent d'une édition ultérieure.

## Lecture avec l'API de recherche

Avec `sentinels.collab.search_api` activé (désactivé par défaut), le sentinelle Collab demande les tickets et pull requests ouverts de tout le compte en quelques appels de l'API de recherche au lieu de deux listes par dépôt. L'API de recherche a son propre quota (30 appels par minute) que le quota REST ne paie pas. Ensuite, seuls les conflits des pull requests modifiés sont lus. Les alertes sont les mêmes des deux façons, un test les compare ; si l'API de recherche échoue, la ronde lit chaque dépôt comme avant. Un pull request trouvé ainsi ne dit pas si une revue a été demandée, donc la règle des revues en attente ne compte que ce que donnent les listes.

## Longues listes : pages et ce qui est coupé

Une page de GitHub compte 100 éléments. Un dépôt peut avoir des centaines d'issues et de pull requests ouvertes, 148 ou 348 workflows, ou une matrice de plus de 100 jobs ; le moniteur lit donc la page suivante tant que la dernière était pleine et dit quand quelque chose reste dehors :

- **Issues et pull requests** (cet onglet) : jusqu'à `pagination.collab_pages` pages de 100 pour chaque liste d'un dépôt (la première page garde sa lecture conditionnelle et un dépôt de moins de 100 ne coûte rien de plus). Un dépôt qui a plus que ce qui a été lu est compté dans le pied de l'onglet ; avec l'API de recherche (`sentinels.collab.search_api`) le pied dit « N vus sur M » quand le compte a plus que les 1000 résultats de la recherche.
- **Workflows d'un dépôt** (hygiène) : jusqu'à `pagination.workflow_pages` pages de 100. Si la liste reste coupée, l'hygiène de ce dépôt dit « N vus sur M » au lieu de paraître complète.
- **Jobs d'une exécution** (onglet Maintenant) : jusqu'à `pagination.job_pages` pages de 100 ; une matrice coupée affiche « jobs : N vus sur M » sous l'exécution.

Les valeurs par défaut ne lisent rien de plus pour un dépôt qui tient dans une page.
