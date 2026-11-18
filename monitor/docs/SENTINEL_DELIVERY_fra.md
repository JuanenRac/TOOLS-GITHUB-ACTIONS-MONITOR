<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_DELIVERY.md) | [🇪🇸 Español](SENTINEL_DELIVERY_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](SENTINEL_DELIVERY_ita.md) | [🇩🇪 Deutsch](SENTINEL_DELIVERY_deu.md) | [🇨🇳 简体中文](SENTINEL_DELIVERY_zho.md) | [🇯🇵 日本語](SENTINEL_DELIVERY_jpn.md) | [🇵🇹 Português](SENTINEL_DELIVERY_por.md)

# La sentinelle de livraison

La cinquième sentinelle, à côté de celles de la CI, de Collab, de Sécurité et de Chaîne d'approvisionnement. Elle lit, sans rien écrire sur GitHub, les dernières versions publiées, les dernières étiquettes, le CHANGELOG et les fichiers de version que vous indiquez pour chaque dépôt (par l'API, sans clone) et signale ce qui a été construit mais pas livré. Elle en fait des alertes de l'onglet Alertes (origine Livraison). Elle est dans l'édition Complete, désactivée par défaut (`sentinels.delivery.enabled`) ; Lite n'a pas de sentinelles.

Elle a sa propre entrée dans le groupe Sentinelle du menu, **Sentinelle de livraison** (adresse `#sentinel-delivery`), visible tant que la sentinelle est activée : un panneau avec les constats ouverts de chaque dépôt, l'état de son cycle et ce qui n'a pas pu être lu ; le badge de l'entrée compte les erreurs.

## Ce qu'elle signale

| Signal | Alerte | Niveau | Activé par défaut |
|---|---|---|---|
| Le CHANGELOG a des entrées sous `[Unreleased]` et la dernière version publiée a plus de `sentinels.delivery.unreleased_days` jours (14) | `release.unreleased_pending` | info | oui |
| Une étiquette de version plus récente que la dernière version publiée et sans version à elle (un brouillon ne compte pas comme livré) | `release.tag_without_release` | warning | oui |
| La dernière version publiée a une description vide | `release.release_without_notes` | info | oui |
| Les fichiers de version de `version_files` et le premier titre versionné du CHANGELOG ne disent pas tous la même version (`1.2` et `1.2.0` sont la même) | `release.version_mismatch` | warning | oui |
| Un dépôt fige une version plus ancienne que la dernière du dépôt qui fournit un contrat partagé (les tables d'épinglage de `sentinel.readiness.pins.sources`, type `pin_table`) | `release.ecosystem_drift` | warning | oui |
| La dernière version publiée n'a pas de fichier pour l'un des motifs de `expected_assets` (par exemple `*.zip`, `SHA256SUMS*`) | `release.assets_missing` | warning | oui |

Il y a une alerte par dépôt et par signal, avec les nombres et quelques étiquettes, motifs ou versions dans ses détails. Chaque signal peut être désactivé (`sentinels.delivery.signals.<signal>.enabled`) et recevoir un autre niveau (`info`, `warning`, `error`, `critical`). Un dépôt sans aucune version publiée n'est pas jugé par les signaux sur les versions : il ne les utilise pas. Les préversions et les brouillons ne sont jamais pris pour la dernière version.

## Un propriétaire pour chaque constat

Le panneau de préparation de l'onglet Sentinelle (A11) est une ligne par dépôt tirée de clones locaux ; cette sentinelle produit des alertes à identifiant stable, avec silences, événements et cycle propre, lues par l'API sans clone. Les signaux sur les workflows d'un dépôt appartiennent à la sentinelle de Chaîne d'approvisionnement et ceux sur les réglages de GitHub à Sécurité : rien n'est levé deux fois. Le plugin optionnel « Releases » de la feuille de route est remplacé par cette sentinelle.

## Ce qu'elle n'a pas pu vérifier

Un dépôt qui ne peut pas être lu (pas d'accès, SSO non autorisé, quota épuisé, un tour avec moins d'appels que n'en demande un dépôt) n'est **pas** une alerte et n'est **pas** un bilan propre. Il est listé dans l'état sous `unavailable`, avec la raison et le nombre, et un niveau `ok` s'affiche `unknown` quand la plupart de ce qui a été regardé n'a pas pu être lu. Si un dépôt cesse de répondre alors qu'il a des alertes, elles restent une semaine (marquées `unread_since`) et ne sont jamais annoncées comme résolues. Un fichier qui n'existe pas (pas de CHANGELOG à ce chemin, pas de tel fichier de version) est simplement absent. Les tables d'épinglage sont lues une fois par cycle ; une table illisible garde ses alertes et est aussi listée.

## Coût

Un tour lit au plus `sentinels.delivery.max_repos_per_tick` dépôts (10 par défaut) et fait au plus `sentinels.delivery.max_calls_per_tick` appels (60) : un pour les versions et un pour les étiquettes, un pour le CHANGELOG (plus si vous indiquez plusieurs chemins et que les premiers n'existent pas) et un par fichier de version. Un signal désactivé n'est pas lu du tout. Les dépôts lus il y a le plus longtemps passent d'abord et ceux qui ont une alerte ouverte un peu plus tôt ; un cycle toutes les `sentinels.delivery.refresh_seconds` (une heure par défaut). Il n'y a pas de requêtes conditionnelles : le coût est borné par ces réglages, pas par une réponse 304. La sentinelle se met en pause tant que le quota restant est inférieur à `sentinels.delivery.min_rate_remaining`. Son état (`delivery_state.json`) garde les alertes ouvertes : un redémarrage n'annonce donc rien de nouveau, et le premier regard sur un dépôt n'écrit aucun événement.

## Événements, notifications et score

Un nouveau constat écrit l'événement `delivery_new` et un constat clos `delivery_fixed` (l'événement dit `sentinel: delivery` et le code de l'alerte). Ils appartiennent à la famille des versions : seuls les mainteneurs et les administrateurs peuvent les choisir, et le choix de la sentinelle `ci` dans les préférences de notification de chaque utilisateur décide qui les reçoit ; ils ne figurent dans aucune liste d'événements par défaut. Les métriques portent `delivery_alerts`, `delivery_unreleased_repos`, `delivery_unreleased_days_max`, `delivery_repos_checked`, `delivery_repos_unreadable` et `delivery_calls_last_hour`. Le score ne les utilise pas. L'API répond à `GET /api/sentinel/delivery` et l'onglet Alertes ainsi que `monitor_cli.py alerts --sentinel delivery` filtrent par elle.

## Les réglages

Dans la page Réglages, sous-onglet Sentinelle, bloc Livraison : `sentinels.delivery.enabled`, `sentinels.delivery.refresh_seconds`, `sentinels.delivery.max_repos_per_tick`, `sentinels.delivery.max_calls_per_tick`, `sentinels.delivery.min_rate_remaining`, `sentinels.delivery.repos`, `sentinels.delivery.unreleased_days`, `sentinels.delivery.unreleased_min_entries`, `sentinels.delivery.changelog_paths`, `sentinels.delivery.version_files`, `sentinels.delivery.expected_assets`, `sentinels.delivery.signals.unreleased_pending.enabled`, `sentinels.delivery.signals.unreleased_pending.level`, `sentinels.delivery.signals.tag_without_release.enabled`, `sentinels.delivery.signals.tag_without_release.level`, `sentinels.delivery.signals.release_without_notes.enabled`, `sentinels.delivery.signals.release_without_notes.level`, `sentinels.delivery.signals.version_mismatch.enabled`, `sentinels.delivery.signals.version_mismatch.level`, `sentinels.delivery.signals.ecosystem_drift.enabled`, `sentinels.delivery.signals.ecosystem_drift.level`, `sentinels.delivery.signals.assets_missing.enabled`, `sentinels.delivery.signals.assets_missing.level`.

## Ce qu'elle ne fait pas

Elle n'écrit rien sur GitHub (ni étiquette, version, label, pull request ou issue), ne publie ni ne signe rien, ne crée pas de propositions à partir de ses alertes et ne lit le contenu d'aucun fichier hormis le CHANGELOG et les fichiers de version que vous indiquez.
