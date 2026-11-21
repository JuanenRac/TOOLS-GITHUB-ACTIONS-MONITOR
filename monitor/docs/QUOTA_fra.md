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
6. **GraphQL pour les dépôts calmes (activé par défaut)** : `network.graphql_checks` lit les dépôts qui ne sont pas chauds par lots (`network.graphql_batch`, 20 par défaut) via GraphQL, qui a un quota propre ; un appel remplace de nombreux appels REST. Il ne voit que le dernier commit de la branche par défaut (un workflow qui n'y a pas tourné n'apparaît pas) et ne donne ni durées, ni tentatives, ni autres branches ; les dépôts chauds et tout dépôt auquel GraphQL ne répond pas sont donc lus via REST dans le même cycle. La comptabilité (lots, dépôts, points, dépôts passés à REST) figure dans le résumé et dans l'état pour les outils d'IA. Il est activé par défaut depuis une mesure sur un compte réel : 40 dépôts lus en deux lots ont coûté 2 appels au lieu de 40 (95 % de moins), chaque dépôt a obtenu une réponse et il n'y a eu aucune erreur. Mettez `network.graphql_checks` à false pour tout lire via REST.

## Une GitHub App, pas à pas
1. Dans GitHub, *Settings*, *Developer settings*, *GitHub Apps*, *New GitHub App*. Pas de webhook. Permissions **en lecture seule** : Actions, Checks, Code scanning alerts, Commit statuses, Contents, Dependabot alerts, Issues, Pull requests, Secret scanning alerts et Metadata.
2. *Generate a private key* et gardez le `.pem` **hors de tout dépôt**, lisible par vous seul.
3. *Install App* sur votre compte, sur tous les dépôts à surveiller.
4. Dans le moniteur : `github_app.enabled` activé, `github_app.app_id` (le numéro de l'App) et `github_app.key_path` (seulement le CHEMIN de la clé). `github_app.installation_id` peut rester vide.
5. Vérifiez avec `GET /api/github-app/status` (cet ordinateur seulement) : il montre le nom, l'installation, les permissions accordées et le quota de l'App, jamais la clé ni un jeton. Le doctor vérifie `openssl`, le fichier de clé et ses droits.
6. Tester les identifiants : l'**onglet Quota > Tester le jeton** (ou `POST /api/credential/probe`, cet ordinateur seulement) dit qui est l'accès du moniteur, s'il s'agit d'un jeton classique (et quels scopes lui manquent pour votre compte) ou d'un jeton à granularité fine ou d'une App, combien de dépôts il voit (et si l'authentification unique coupe la liste) et combien de quota il reste. Avec une GitHub App, il donne aussi son nom, son installation et les permissions qui lui manquent, et quand l'App est installée sur plusieurs comptes dont aucun n'est le vôtre, il liste les installations pour que vous en écriviez une dans `github_app.installation_id`. Laissé vide, ce réglage se trouve tout seul : l'installation du compte que surveille le moniteur, ou la seule. Au plus une vraie vérification toutes les 10 secondes ; rien n'est écrit dans GitHub et aucun jeton ni clé n'est montré.

Sécurité : le moniteur lit la clé en mémoire seulement pour signer un JWT de dix minutes au plus (avec la bibliothèque standard, sans besoin de `openssl` ; `openssl` n'est que le recours) et ne la copie, ne l'imprime ni ne la journalise jamais. Le jeton d'installation dure une heure, reste en mémoire et est renouvelé cinq minutes avant. **Seules les lectures** l'utilisent ; les écritures et actions gardent votre jeton. Si l'App échoue ou n'a pas une permission, la lecture est refaite avec votre jeton. La page montre les deux quotas.

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

## Répartition du quota : source préférée et réserve

Par défaut chaque lecture va à la source (utilisateur, GitHub App, second compte) qui a le plus d'appels libres. Le bloc `readpool` le modifie, dans l'onglet Quota des réglages, avec les valeurs prudentes d'avant (`auto`, réserve 0) :

- `readpool.prefer.<type>` (`auto`, `user`, `app`, `extra`) : la source qui répond d'abord à un TYPE de lecture. Les types viennent de l'appel : `runs` (exécutions, workflows, checks), `security` (code scanning, Dependabot, secret scanning), `issues` (issues et pull requests), `history` (versions, commits, étiquettes, contenu), `discovery` (organisations, recherche, listes de dépôts) et `other`. Si la source préférée échoue ou est sous sa réserve, les autres répondent, l'utilisateur en dernier.
- `readpool.reserve.<source>` (0 à 4000) : appels laissés libres dans cette source. Tant qu'une source a au plus les appels de sa réserve, le moniteur ne lit pas avec elle si une autre peut. Utilisez `readpool.reserve.user` pour laisser des appels au `gh` de vos outils et agents.
- `quota.failover` (désactivé par défaut) : une lecture qui répond 429 ou « rate limit exceeded » est refaite une fois avec une autre source capable de lire, et la source épuisée compte comme dépensée jusqu'à sa prochaine vérification gratuite. Quand toutes les sources sont dépensées, la dernière bonne copie de cette lecture est montrée avec son âge au lieu d'une erreur (`quota.failover_max_age_minutes`, 60 par défaut, de 1 à 1440 ; une copie plus ancienne n'est pas montrée). Une limite n'est jamais prise pour un refus de permission, une écriture ne change jamais de source, et `GET /api/quota-pool/status` a le bloc `failover` avec le nombre d'interventions.

Les écritures et actions utilisent toujours le jeton de l'utilisateur. La barre de quota et les modes de travail (rapide et turbo) comptent la SOMME de toutes les sources : la tuile montre la somme et son infobulle le chiffre de chaque source, et l'onglet Quota (État) ajoute une ligne avec le total à côté du quota de l'utilisateur, de l'App et du second compte.

## Lire moins : le webhook d'abord et les sources gratuites

Les deux voies sont **désactivées par défaut** et ne touchent que les dépôts calmes (ceux dont les dernières exécutions sont toutes terminées et vertes). Un dépôt en cours d'exécution, rouge ou touché par un événement est lu comme d'habitude.

- `savings.webhook_first` : tant que le webhook entrant est vivant (il a livré un événement dans les `savings.webhook_window_minutes` dernières minutes), un dépôt calme n'est pas lu à son tour lent : GitHub prévient quand il se passe quelque chose. Il est quand même lu en entier toutes les `savings.webhook_full_minutes`. Sans webhook vivant, rien ne change.
- `savings.webhook_live_per_repo` : fait de « vivant » l'affaire de chaque dépôt. Seul un dépôt calme dont les événements PROPRES sont arrivés dans les derniers `savings.webhook_window_minutes` minutes saute sa lecture lente ; un dépôt dont le webhook n'a jamais été installé, ou est tombé, est lu comme toujours pendant que les autres sont épargnés. Cela économise moins de lectures, et le panneau Webhook compte les dépôts vivants par eux-mêmes. Désactivé par défaut ; fonctionne avec `savings.webhook_first`.
- `savings.feeds.enabled` : avant de lire un dépôt calme avec l'API, le dernier commit de sa branche par défaut est demandé à une source qui ne coûte pas de quota - le flux Atom public des commits, `git ls-remote`, ou l'un ou l'autre (`savings.feeds.method` : `atom`, `git`, `auto`). Si c'est le commit de la dernière lecture complète, le dépôt reste tel quel. Toutes les `savings.feeds.max_age_minutes`, il est lu en entier de toute façon. Dépôts publics seulement : pour un dépôt privé, une erreur ou une réponse étrange, le dépôt est lu avec l'API comme d'habitude. Seules des requêtes GET vers github.com quittent l'ordinateur, jamais un mot de passe, et rien n'est écrit. Non utilisé quand le moniteur est isolé du réseau (air-gapped).

Ce que cela coûte : une exécution qui démarre sans push (une planification, une relance) sur un dépôt calme est vue à la prochaine lecture complète, pas aussitôt. L'onglet Quota (État) montre les lectures évitées par chaque voie depuis le démarrage du moniteur (environ un appel de l'API chacune) : lectures conditionnelles, GraphQL, webhook d'abord, flux Atom, git et panneau central.

## Grands comptes : ce que couvre la liste d'exécutions, et un budget

Un dépôt qui lance des centaines d'exécutions par heure remplit en quelques minutes une liste de 20 à 100 exécutions ; un échec plus ancien ou un workflow qui tourne rarement n'y figure tout simplement pas. Le moniteur le dit au lieu d'avoir l'air vert :

- **Couverture** : le tableau des dépôts montre jusqu'où remonte chaque liste. Une liste pleine qui remonte moins de `sampling.min_coverage_minutes` est marquée *couverture faible* ; une liste plus courte que demandé est *complète* (elle contient tout l'historique) ; un total de 2 500 ou 40 000 est l'endroit où GitHub cesse de compter, il est donc affiché comme *au moins*. Le bloc `sampling` de `GET /api/data` porte les mêmes chiffres.
- **Second regard** : avec `sampling.default_branch_probe` activé, une liste pleine demande aussi les push vers la branche par défaut (sans pull requests), une requête de plus par lecture, afin que les exécutions qui décident du rouge sur main ne soient pas chassées par les pull requests et les planifications.
- **Regard sur les exécutions en cours** : avec `sampling.active_probe` activé, une liste pleine demande aussi, en deux requêtes légères, les exécutions encore `in_progress` et celles `queued`, pour qu'une longue exécution commencée avant la fenêtre de la liste ne soit ni perdue ni affichée comme terminée. Deux requêtes de plus par dépôt plein et par lecture ; désactivé par défaut.
- **A2 en une fois** : pour un dépôt ayant `sentinel.a2_resolve_batch_min` workflows ou plus à rechercher, on demande une seule fois ses exécutions terminées les plus récentes de la branche par défaut (`sentinel.a2_resolve_batch_pages` pages de 100 au plus) et on les règle ensemble ; ce que cette liste ne montre pas est demandé un par un. Avec 100 workflows ou plus, il faut quelques cycles au lieu de quatre workflows par cycle.
- **Budget** : `sampling.api_budget_per_hour` (0 = aucun) limite les requêtes de listes d'exécutions par heure. Au-delà, les dépôts avec un workflow rouge sont lus en premier, un dixième du budget leur est toujours réservé et les autres attendent ; la page dit combien. L'estimation des requêtes par heure pour le nombre de dépôts et les intervalles s'affiche à partir de 3 500 (GitHub autorise 5 000 par heure) ou dès qu'un budget est fixé.

Les valeurs par défaut ne changent rien pour un compte de quelques dépôts : le second regard et le budget sont désactivés, et la marque de couverture faible n'apparaît que lorsqu'une liste pleine remonte moins d'une demi-heure.

## Quand l'App est activée et n'est pas utilisée

Si `github_app.enabled` est activé mais que l'App ne peut pas donner de jeton, les lectures continuent avec votre jeton et le quota est le plus petit, celui de l'utilisateur. Ce n'est jamais silencieux : le doctor passe à l'orange avec la cause, un échec est noté une fois dans la liste des échecs avalés et l'onglet Quota montre une ligne `GitHub App` avec la cause et la limite utilisée. Les causes : la clé est illisible ou n'est pas une clé RSA sans phrase secrète (`key_unreadable`), la clé n'a pas pu signer (`sign_failed`), l'App n'est pas installée sur le compte (`app_not_installed`), GitHub a refusé le jeton (`token_refused`) et l'App est activée sans son numéro ou son fichier de clé (`not_configured`). La même note est dans `GET /api/quota` sous `app` et dans `GET /api/github-app/status` sous `signer` et `code`.
