<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_SUPPLY.md) | [🇪🇸 Español](SENTINEL_SUPPLY_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](SENTINEL_SUPPLY_ita.md) | [🇩🇪 Deutsch](SENTINEL_SUPPLY_deu.md) | [🇨🇳 简体中文](SENTINEL_SUPPLY_zho.md) | [🇯🇵 日本語](SENTINEL_SUPPLY_jpn.md) | [🇵🇹 Português](SENTINEL_SUPPLY_por.md)

# La sentinelle de chaîne d'approvisionnement

La quatrième sentinelle, à côté de celles de CI, de Collab et de Sécurité. Elle lit, sans rien écrire sur GitHub, les fichiers de workflow de chaque dépôt (`.github/workflows`, par l'API, sans clone) et signale ce qui permet à une étiquette déplacée ou à un tiers d'agir avec le jeton et le code du dépôt. Elle en fait des alertes de l'onglet Alertes (origine Chaîne d'approvisionnement). Elle fait partie de l'édition Complète, désactivée par défaut (`sentinels.supply.enabled`) ; Lite n'a pas de sentinelles.

Elle a sa propre entrée dans le groupe Sentinelle du menu, **Sentinelle de chaîne d'approvisionnement** (adresse `#sentinel-supply`), visible tant que la sentinelle est activée : un panneau avec les constats ouverts de chaque dépôt, l'état de son cycle et ce qui n'a pas pu être lu ; le badge de l'entrée compte les erreurs.

## Ce qu'elle signale

| Signal | Alerte | Niveau | Active par défaut |
|---|---|---|---|
| Un `uses:` d'une action ou d'un workflow réutilisable non épinglé à un SHA de commit complet (son propriétaire peut déplacer l'étiquette) | `actions.supply.unpinned` | warning | oui |
| Un `uses:` qui suit une branche qui bouge toute seule (`@main`, `@master`...) : pire qu'une étiquette | `actions.supply.mutable_ref` | warning | oui |
| Un workflow avec `permissions: write-all` | `actions.supply.permissions_wide` | warning | oui |
| Un workflow sans bloc `permissions:` (le jeton reçoit la permission par défaut, plus large) | `actions.supply.permissions_missing` | warning | oui |
| `pull_request_target` avec la récupération du code de la pull request | `actions.supply.pr_target_checkout` | error | oui |

Il y a une alerte par dépôt et par signal, avec le nombre de constats, les fichiers concernés et quelques exemples (le nom d'une action) dans ses détails. Chaque signal peut être désactivé (`sentinels.supply.signals.<signal>.enabled`) et recevoir un autre niveau (`info`, `warning`, `error`, `critical`). Un `uses:` d'un workflow du même dépôt n'est pas un tiers et est laissé de côté.

## Une seule source de vérité

Elle n'a pas de règles propres : les constats viennent du linter de workflows (`bin/lint_workflows.py`, le même que l'onglet Sentinelle et la ligne de commande), seules `unpinned_uses`, `permissions` et `pr_target` sont actives ici et toutes les autres règles restent désactivées. En particulier la règle qui cherche des secrets écrits dans un fichier est désactivée : **la valeur d'un secret n'est jamais lue, conservée ni affichée**. Les réglages `lint.own_owners` et `lint.unpinned_own` décident toujours du traitement d'une action de votre propre compte, et un commentaire `# monitor-lint: ignore RÈGLE` dans un workflow fait taire un constat à l'endroit même.

## Un propriétaire pour chaque constat

`security.workflow_write` (sentinelle Sécurité) est la permission par défaut du dépôt, un réglage de GitHub ; les signaux d'ici portent sur le contenu de chaque fichier de workflow, si bien qu'un dépôt ne lève jamais le même constat depuis les deux. Le panneau du lint de l'onglet Sentinelle reste un panneau ; les alertes de l'onglet Alertes sur ces signaux viennent uniquement d'ici.

## Ce qu'elle n'a pas pu vérifier

Un dépôt dont les workflows ne peuvent pas être lus (pas d'accès, SSO non autorisé, quota épuisé, dossier avec trop de fichiers) n'est **pas** une alerte et n'est **pas** un certificat de bonne santé. Il est listé dans l'état sous `unavailable`, avec la raison et le nombre de dépôts, et un niveau `ok` s'affiche `unknown` quand la plupart de ce qui a été regardé n'a pas pu être lu. Si un dépôt cesse de répondre alors qu'il a des alertes, elles restent une semaine (marquées `unread_since`) et ne sont jamais annoncées comme résolues. Un dépôt sans dossier `.github/workflows` est lu et n'a simplement rien à signaler. Un dépôt dont les lectures échouent attend 5 minutes, 30 minutes puis 6 heures avant le prochain essai.

## Coût

Une ronde lit au plus `sentinels.supply.max_repos_per_tick` dépôts (10 par défaut) et fait au plus `sentinels.supply.max_calls_per_tick` appels (60) : un pour lister les workflows d'un dépôt et un de plus pour chaque fichier nouveau ou modifié, car un fichier dont le SHA n'a pas changé n'est jamais relu. Les dépôts lus il y a le plus longtemps passent en premier, ceux qui ont une alerte ouverte un peu avant ; un cycle toutes les `sentinels.supply.refresh_seconds` (une heure par défaut). La sentinelle se met en pause tant que le quota restant est inférieur à `sentinels.supply.min_rate_remaining`. Son état (`supply_state.json`) garde les alertes ouvertes : un redémarrage n'annonce donc rien de nouveau, et le premier regard sur un dépôt n'écrit aucun événement. `sentinels.supply.max_files_per_repo` limite les fichiers lus dans un dépôt ; un dépôt au-dessus de la limite est lu en partie et compté comme partiel. Un tour cesse aussi de commencer de nouveaux dépôts après `sentinels.supply.deadline_s` secondes (30 par défaut ; 0 = aucun plafond) : ceux qui n'ont pas été atteints attendent le tour suivant et l'état les liste par nom comme `unchecked` (avec `round_cut`) au lieu de les compter pour zéro alerte.

## Ignorer un constat

`sentinels.supply.ignore` accepte des motifs `dépôt:fichier:règle` (avec `*` pour tout) qui nomment la règle du linter, par exemple `monrepo:release.yml:unpinned_uses` ; notez que `unpinned_uses` est la règle derrière `unpinned` et `mutable_ref`, et `permissions` celle des deux signaux de permissions. Les motifs de `lint.ignore` ne s'appliquent pas ici.

`sentinels.supply.ignore_uses` accepte des noms `propriétaire/dépôt` (avec `*` pour tout, par exemple `other-org/*`) d'actions ou de workflows réutilisables d'une autre organisation privée que l'accès ne peut pas voir et dont le moniteur ne peut pas juger la référence : leurs références non épinglées ou mobiles sortent des constats et sont comptées à part comme `uses_left_out` dans l'état, donc ni signalées sur supposition ni cachées.

## Événements, notifications et score

Un nouveau constat écrit l'événement `security_new` et un constat clos `security_fixed` (l'événement porte `sentinel: supply` et le code de l'alerte) ; la case Sécurité des préférences de notification de chaque utilisateur et les canaux décident donc qui est prévenu. Rien n'est annoncé la première fois qu'un dépôt est regardé. Les métriques portent `supply_alerts`, `supply_findings`, `supply_penalty` (informative : `sentinels.supply.penalty.per_finding`, 2, et `cap_per_repo`, 10, sont lus dans le fichier), `supply_repos_checked`, `supply_repos_unreadable` et `supply_calls_last_hour`. Le score n'utilise pas la pénalité. L'API répond à `GET /api/sentinel/supply`, et l'onglet Alertes comme `monitor_cli.py alerts --sentinel supply` filtrent dessus.

## Les réglages

Dans la page Réglages, sous-onglet Sentinelle, bloc Chaîne d'approvisionnement : `sentinels.supply.enabled`, `sentinels.supply.refresh_seconds`, `sentinels.supply.max_repos_per_tick`, `sentinels.supply.max_calls_per_tick`, `sentinels.supply.max_files_per_repo`, `sentinels.supply.min_rate_remaining`, `sentinels.supply.repos`, `sentinels.supply.ignore`, `sentinels.supply.ignore_uses`, `sentinels.supply.signals.unpinned.enabled`, `sentinels.supply.signals.unpinned.level`, `sentinels.supply.signals.mutable_ref.enabled`, `sentinels.supply.signals.mutable_ref.level`, `sentinels.supply.signals.permissions_wide.enabled`, `sentinels.supply.signals.permissions_wide.level`, `sentinels.supply.signals.permissions_missing.enabled`, `sentinels.supply.signals.permissions_missing.level`, `sentinels.supply.signals.pr_target_checkout.enabled`, `sentinels.supply.signals.pr_target_checkout.level`.

## Ce qu'elle ne fait pas

Elle n'écrit pas sur GitHub (ni pull request, ni étiquette, ni ticket), ne propose pas le SHA auquel épingler une action et ne lit la valeur d'aucun secret.
