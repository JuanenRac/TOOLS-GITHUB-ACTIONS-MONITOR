<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](QUOTA.md) | [🇪🇸 Español](QUOTA_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](QUOTA_ita.md) | [🇩🇪 Deutsch](QUOTA_deu.md) | [🇨🇳 简体中文](QUOTA_zho.md) | [🇯🇵 日本語](QUOTA_jpn.md) | [🇵🇹 Português](QUOTA_por.md)

# Plus de quota, moins de dépense

GitHub donne à chaque compte un **quota limité d'appels à l'API**, partagé par tous les outils qui l'utilisent. Ce guide explique son fonctionnement et toutes les façons dont le moniteur en dépense moins.

## Comment fonctionne le quota
- **REST** : 5000 appels par heure et par utilisateur (60 sans connexion). **GraphQL** a le sien, séparé. Le `GITHUB_TOKEN` d'un workflow dans Actions a aussi le sien. Une **GitHub App** a un quota propre, séparé du vôtre, qui grandit avec les dépôts où elle est installée (environ 10 000 par heure avec 130 dépôts).
- Ce qui compte et ce qui ne compte pas : une lecture conditionnelle qui répond `304 Not Modified` (ETag) ne compte pas ; demander `rate_limit` est gratuit ; `git push`, `git fetch` et `git clone` n'utilisent pas l'API.

## Les moyens d'économiser du moniteur
1. **Lectures conditionnelles** (ETag et `304`) : `cache.etag.enabled` (activé par défaut) ; la page montre combien de lectures ont été économisées.
2. **Mode économe** : seulement les dépôts chauds toutes les 4 minutes, le reste toutes les 30 ; `modes.auto_low` (activé) s'enclenche sous 1000 appels restants et revient au-dessus de 2500 ou au renouvellement ; préréglages dans `modes.low`. La barre dit que les chiffres peuvent être anciens, et de combien.
3. **Panneau central comme base** : `central.source` (`off`, `git`, `http`) lit `data/sentinel.json` de votre dépôt de profil, rafraîchi par un workflow avec son propre jeton ; il ne dépense rien de votre quota. `central.max_age_minutes` (120) : plus ancien, il est « en retard » et n'est pas cru.
4. **Un seul avis quand le quota est épuisé** : les lectures s'arrêtent jusqu'au renouvellement, la page dit une fois « quota épuisé jusqu'à HH:MM » (pas une erreur par dépôt) et reprend toute seule.
5. **Une GitHub App pour les lectures** (`github_app.*`), ci-dessous.
6. **GraphQL pour les dépôts calmes (optionnel, désactivé par défaut)** : `network.graphql_checks` lit les dépôts qui ne sont pas chauds par lots (`network.graphql_batch`, 20 par défaut) via GraphQL, qui a un quota propre ; un appel remplace de nombreux appels REST. Il ne voit que le dernier commit de la branche par défaut (un workflow qui n'y a pas tourné n'apparaît pas) et ne donne ni durées, ni tentatives, ni autres branches ; les dépôts chauds et tout dépôt auquel GraphQL ne répond pas sont donc lus via REST dans le même cycle. La comptabilité (lots, dépôts, points, dépôts passés à REST) figure dans le résumé et dans l'état pour les outils d'IA.

## Une GitHub App, pas à pas
1. Dans GitHub, *Settings*, *Developer settings*, *GitHub Apps*, *New GitHub App*. Pas de webhook. Permissions **en lecture seule** : Actions, Checks, Code scanning alerts, Commit statuses, Contents, Dependabot alerts, Issues, Pull requests, Secret scanning alerts et Metadata.
2. *Generate a private key* et gardez le `.pem` **hors de tout dépôt**, lisible par vous seul.
3. *Install App* sur votre compte, sur tous les dépôts à surveiller.
4. Dans le moniteur : `github_app.enabled` activé, `github_app.app_id` (le numéro de l'App) et `github_app.key_path` (seulement le CHEMIN de la clé). `github_app.installation_id` peut rester vide.
5. Vérifiez avec `GET /api/github-app/status` (cet ordinateur seulement) : il montre le nom, l'installation, les permissions accordées et le quota de l'App, jamais la clé ni un jeton. Le doctor vérifie `openssl`, le fichier de clé et ses droits.

Sécurité : le moniteur ne lit, ne copie, n'imprime ni ne journalise jamais la clé ; il passe son chemin à `openssl`, qui signe un JWT de dix minutes au plus. Le jeton d'installation dure une heure, reste en mémoire et est renouvelé cinq minutes avant. **Seules les lectures** l'utilisent ; les écritures et actions gardent votre jeton. Si l'App échoue ou n'a pas une permission, la lecture est refaite avec votre jeton. La page montre les deux quotas.

## Quand plusieurs outils partagent le même quota
Tous les outils du compte dépensent les mêmes 5000 appels par heure. Un bon schéma : un petit enveloppeur de `gh` avec un **cache partagé** de quelques minutes, une **réserve** (il refuse d'appeler quand il reste moins d'environ 1000, sauf pour l'urgent), le travail qui exige des données fraîches **juste après le renouvellement**, et jamais `gh run watch` (il interroge en boucle). Par exemple, un enveloppeur qui stocke la réponse de chaque lecture dans un fichier temporaire nommé d'après la commande et la ressert pendant 120 secondes, et vérifie `gh api rate_limit` avant tout autre appel.

## Ce qu'il ne faut PAS faire
N'utilisez pas plusieurs comptes ni plusieurs jetons du même utilisateur pour contourner la limite : c'est contraire aux règles de GitHub et le compte peut être bloqué. Utilisez une App, le panneau central et le mode économe.

## Réglages
| Réglage | Défaut |
|---|---|
| `cache.etag.enabled` | activé |
| `modes.auto_low` / `modes.auto_low_enter` / `modes.auto_low_exit` | activé / 1000 / 2500 |
| `modes.low.*` (`refresh_seconds`, `cold_refresh_seconds`, `runs_per_repo`, `hot_hours`) | 240 / 1800 / 10 / 2 |
| `min_rate_remaining` | 800 |
| `central.source` / `central.max_age_minutes` | off / 120 |
| `github_app.enabled` / `github_app.app_id` / `github_app.key_path` / `github_app.installation_id` | off / vide / vide / vide |

## Dépannage et FAQ
- *« quota épuisé jusqu'à HH:MM »* : attendez ; le moniteur reprend tout seul. D'autres outils le dépensent peut-être : regardez les leurs.
- *Les chiffres sont anciens* : le mode économe est actif (choisi ou automatique) ; la barre le dit.
- *L'App ne marche pas* : regardez `/api/github-app/status` et le doctor : openssl, le chemin de la clé, les permissions.
- *`git fetch` coûte-t-il du quota ?* Non. Voir aussi [QUOTAS_fra.md](QUOTAS_fra.md) (plans et minutes) et [MODES_fra.md](MODES_fra.md).

## L'onglet Quota et un second compte
Tout ce qui concerne le quota est au même endroit : *Réglages*, onglet *Quota*. Il regroupe les modes (`modes.auto_low`, `modes.auto_low_enter`, `modes.auto_low_exit` et les valeurs du mode économe dans `modes.low.*`), l'économie (`network.etag`, avec `cache.etag.enabled`), le panneau central (`central.source`, `central.max_age_minutes`), la GitHub App (`github_app.*`) et un **second compte pour les lectures**. Les boutons de l'onglet montrent le quota de chaque source (votre connexion, l'App, le second compte) avec l'heure de renouvellement, testent l'App et le second compte, listent les permissions qui manquent à l'App et appliquent les valeurs recommandées ou celles par défaut.

Le second compte (`extra_reader.enabled`, `extra_reader.file`) est un compte en lecture seule dont le jeton à granularité fine se trouve dans un fichier texte hors de tout dépôt, lisible par vous seul ; le réglage ne contient QUE le chemin de ce fichier. Le moniteur lit le jeton au moment de l'utiliser, le garde en mémoire et ne le stocke, imprime ni journalise jamais. Les lectures sont réparties entre votre connexion, l'App et le second compte selon les appels restants de chacun (le chiffre de l'appel gratuit `rate_limit`, moins les lectures faites depuis) ; une source refusée est laissée de côté cinq minutes et la lecture est refaite avec la suivante. Les écritures et actions ne l'utilisent jamais. Il s'agit d'un compte à vous (par exemple un second compte personnel avec accès en lecture aux dépôts), pas d'un moyen de contourner la limite avec les comptes d'autrui. Le fichier doit se trouver dans le dossier des comptes du moniteur (`accounts/`, ou le dossier indiqué par `MONITOR_ACCOUNTS_DIR`) et n'est jamais lu par un lien ; `extra_reader.any_folder` (désactivé par défaut) lève la règle du dossier. Ce qui dépend de celui qui demande (votre compte, ses organisations, les notifications, une recherche de `@me`, `gh auth`, `gh repo list` sans propriétaire) est toujours servi par votre propre login, et seule une lecture simple `gh api ENDPOINT` (avec au plus les options `--jq`, `--paginate`, `-H`, `-i` et `--cache`) est répartie entre les sources : tout autre appel va à votre login.

## Le programme openssl et un moniteur par port

Le moniteur cherche `openssl` dans le PATH et, s'il n'y est pas, là où Git for Windows le range (`Git\usr\bin`, `Git\mingw64\bin` dans Program Files et dans les Programmes de l'utilisateur) et dans les dossiers habituels de macOS et Linux ; un moniteur lancé depuis un `.bat` ou un service le trouve donc. `github_app.openssl_path` (chemin absolu du programme) en choisit un à la main. `/api/github-app/status` montre `openssl` et `openssl_path`, et le doctor dit lequel signe quand ce n'est pas celui du PATH.

Sous Windows le port du moniteur est ouvert en exclusivité (SO_EXCLUSIVEADDRUSE) : deux processus ne peuvent plus écouter sur le 8765 en même temps. Et un moniteur qui démarre alors qu'un autre répond déjà sur son port le dit et s'arrête au lieu de chercher un autre port.
