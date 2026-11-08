<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](QUOTAS.md) | [🇪🇸 Español](QUOTAS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](QUOTAS_ita.md) | [🇩🇪 Deutsch](QUOTAS_deu.md) | [🇨🇳 简体中文](QUOTAS_zho.md) | [🇯🇵 日本語](QUOTAS_jpn.md) | [🇵🇹 Português](QUOTAS_por.md)

# Quotas et offres

Le moniteur est utilisé par tous les types de comptes, il n'en suppose donc aucun. Les chiffres ci-dessous sont dans `monitor/quotas.json` (modifiez-le pour suivre les changements de GitHub sans nouvelle version du moniteur) et ont été confrontés à la documentation publique de GitHub ; ils évoluent, prenez-les comme point de départ et consultez les pages citées dans le fichier. Choisissez votre offre dans **Réglages > Essentiel** (`account.plan`) ; tant qu'elle est *inconnue*, aucun chiffre de quota n'est affiché.

## Le quota de l'API

| Connexion | Appels par heure |
|---|---|
| Sans connexion | 60 par heure et par adresse |
| Votre session (`gh auth login`) ou un jeton personnel | 5 000 |
| Le jeton d'un workflow (dans Actions) | 1 000 par dépôt (15 000 sur Enterprise Cloud) |
| Une application sur Enterprise Cloud | 15 000 |
| Une GitHub App ailleurs | 5 000, augmente avec l'installation jusqu'à 12 500 |

La page affiche la vraie limite lue dans les en-têtes de GitHub (`X-RateLimit-*`), jamais un 5 000 supposé : c'est aussi ce qui fait fonctionner GitHub Enterprise Server (`GH_HOST`). Sans connexion (60 par heure) elle conseille `gh auth login`. Il existe aussi une limite *secondaire* (pas plus de 100 requêtes simultanées et rafales) : quand GitHub répond ainsi, le moniteur attend au moins une minute, double l'attente jusqu'à cinq minutes et n'insiste jamais.

## Minutes Actions

| Offre | Inclus par mois (en argent) | En minutes Linux | Stockage d'artefacts |
|---|---|---|---|
| Free | 12 $ | 2 000 | 500 Mo |
| Pro | 18 $ | 3 000 | 1 Go |
| Team | 18 $ | 3 000 | 2 Go |
| Enterprise Cloud | 300 $ | 50 000 | 50 Go |

**Les dépôts publics ne coûtent aucune minute, quelle que soit l'offre** (les runners auto-hébergés non plus) ; les runners plus grands sont toujours facturés. Une minute est multipliée par le tarif de son système : Windows vaut environ 1,67 minute Linux et macOS environ 10,3 (tarifs par minute dans `quotas.json` : 0,006 $ Linux, 0,010 $ Windows, 0,062 $ macOS). Ce que le moniteur montre dans **Réglages > Essentiel > Offre et quotas** est une **estimation** : la durée des runs des dernières 24 heures, arrondie à la minute, pour les seuls dépôts privés, avec le système supposé dans `quota.default_runner`, et le rythme d'un jour multiplié par les jours du mois. Les chiffres réels ne viennent que de l'interrupteur facultatif `quota.billing_api` (désactivé par défaut, lecture seule, nécessite une session autorisée à voir la facturation ; sur un 403 ou 404 l'estimation reste et le dit). Un avertissement part par les notifications une fois par mois à `quota.warn_percent` (75 %) et `quota.alert_percent` (90 %) des minutes incluses.

## Concurrence et limites

| Offre | Jobs simultanés | dont macOS |
|---|---|---|
| Free | 20 | 5 |
| Pro | 40 | 5 |
| Team | 60 | 5 |
| Enterprise | 500 | 50 |

Le panneau compare les jobs en cours et en file à la limite de votre offre et avertit à 90 % ou quand des jobs attendent alors que la limite est pleine. Un job dure au plus 6 heures sur un runner GitHub (le panneau liste ceux au-delà de 80 % de cela), un run de workflow dure au plus 35 jours et une matrice compte jusqu'à 256 jobs.

## Ce qui n'est pas couvert

Les prix par minute supplémentaire, les runners plus grands, le stockage utilisé, Codespaces et Packages ne sont pas suivis ; le tableau des offres est un point de départ et les limites de macOS changent. Rien de tout cela n'a encore été essayé sur un vrai rapport de facturation : la lecture de `usageItems` suit la description publique et se dégrade en silence.
