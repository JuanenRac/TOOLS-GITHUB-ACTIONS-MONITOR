<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI_OPERATOR.md) | [🇪🇸 Español](CLI_OPERATOR_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](CLI_OPERATOR_ita.md) | [🇩🇪 Deutsch](CLI_OPERATOR_deu.md) | [🇨🇳 简体中文](CLI_OPERATOR_zho.md) | [🇯🇵 日本語](CLI_OPERATOR_jpn.md) | [🇵🇹 Português](CLI_OPERATOR_por.md)

# La ligne de commande pour l'opérateur

Les bases de `monitor_cli.py` sont dans [CLI_fra.md](CLI_fra.md). Cette page s'adresse à celui qui vit dans un terminal : comment les réponses sont écrites (`--format`), comment surveiller (`watch`), comment compléter les commandes (`completions`), les codes de sortie et l'adresse pour une télévision (`kiosk`). Tout ce qui suit lit l'API du moniteur de cet ordinateur (ou celle de `--url`) ; rien n'écrit sur GitHub et rien ne dépense le quota.

## Formats : `--format`

| Format | Ce que vous obtenez |
|---|---|
| `text` | ce que chaque commande a toujours écrit. C'est le format par défaut. |
| `table` | les enregistrements en colonnes qui tiennent dans la largeur du terminal (les caractères japonais et chinois comptent pour deux cellules). Il n'y a pas de couleur, donc `NO_COLOR` est respecté. |
| `plain` | un enregistrement par ligne, les champs séparés par une tabulation, sans en-tête : pour `grep`, `cut` et `awk`. Une tabulation ou un saut de ligne dans un texte devient une espace. |
| `json` | le document `{"ok", "exit", "data"}`. `--json` est identique. |
| `ndjson` | un objet JSON par ligne, un par enregistrement (une alerte, un compte, un dépôt, un événement). Une commande qui répond une seule chose (`status`, `health`) donne une ligne. |

`--format` l'emporte sur `--json`, et les deux l'emportent sur le réglage `cli.default_format` (`text` par défaut). Les trois formats structurés sont tirés du même document que `--json`, ils ne se contredisent donc jamais. Une liste vide n'imprime rien en `ndjson` ni en `plain`.

## `watch` : la même lecture, encore et encore

```
python bin/monitor_cli.py watch status
python bin/monitor_cli.py watch alerts --interval 10 --format table
python bin/monitor_cli.py watch alerts --exit-on-change --format ndjson
```

`watch status|alerts` répète la lecture de la commande. Il lit l'API du moniteur, pas GitHub : un intervalle court ne dépense donc pas le quota. Les options :

- `--interval SECONDES` : la pause entre deux lectures. Le plancher est le réglage `cli.watch.min_interval_seconds` (2 par défaut) : un intervalle plus court est relevé jusque-là. Sans `--interval`, la pause est `cli.watch.default_interval_seconds` (5).
- `--once` : une lecture puis sortie (le code de sortie est celui de la commande).
- `--exit-on-change` : la boucle se termine avec le code de sortie **6** quand ce qu'elle surveille n'est plus ce qu'il était à la première lecture (l'ensemble des alertes ou les chiffres de l'état). Une horloge qui avance n'est pas un changement. Sans l'option, le code 6 n'apparaît jamais.
- `--no-clear` : ne pas effacer l'écran entre deux lectures (l'écran n'est effacé que sur un terminal et seulement en `text` et `table`).
- Un moniteur qui ne peut pas être lu est réessayé avec une pause de plus en plus longue (l'intervalle doublé, au plus une minute) et l'erreur va sur la sortie d'erreur. **Ctrl-C** termine la boucle avec le code 0.

## `watch branch` : le commit que vous venez de pousser

```
git push && python bin/monitor_cli.py watch branch
python bin/monitor_cli.py watch branch --repo acme/widgets --branch main --wait 300
python bin/monitor_cli.py watch branch --single-pass --format json
```

`watch branch` demande à git sur quel dépôt (`origin`), quelle branche et quel commit se trouve le dossier courant, et suit dans le moniteur les workflows de ce commit : il attend qu'ils apparaissent, les montre pendant qu'ils tournent et se termine tout seul. Le code de sortie est **0** quand tous les workflows ont réussi et **1** quand l'un a échoué, a été annulé ou n'a pas fini à temps (un échec ne se distingue pas d'un délai dépassé, pour que `git push && monitor_cli.py watch branch` serve dans un script). Il lit les exécutions que le moniteur détient déjà, jamais GitHub, donc il ne consomme pas de quota ; le dépôt doit être l'un de ceux que le moniteur surveille. L'adresse du remote n'est lue que pour trouver propriétaire et nom et n'est jamais affichée (elle peut contenir un jeton).

- `--repo PROPRIÉTAIRE/NOM` et `--branch NOM` remplacent ce que dit git. Avec l'un des deux (ou sans commit), on suit la dernière exécution de chaque workflow de la branche au lieu de celles d'un commit.
- `--single-pass` (ou `--once`) : une lecture puis fin, avec le code de ce moment (1 tant que les exécutions ne sont pas finies).
- `--wait SECONDES` : combien de temps attendre la fin des exécutions avant d'abandonner avec 1 (10 à 86400). Sans lui, l'attente est le réglage `cli.watch.branch_timeout_seconds` (900).
- Un commit détaché n'a pas de branche : indiquez `--branch`. Un dossier sans remote nommé `origin` sur GitHub demande `--repo`.

## `monitor N` : un écran qui se rafraîchit

`monitor_cli.py monitor [N]` est `watch status` qui relit toutes les N secondes (un nombre de 1 à 9999, relevé à `cli.watch.min_interval_seconds` ; sans N, la valeur par défaut de `cli.watch.default_interval_seconds`). Les autres options fonctionnent comme dans `watch` (`--format`, `--no-clear`, `--url`, `--status-codes operator` ...) et Ctrl-C l'arrête avec 0.

## `doctor --latency` : le retard des événements

`monitor_cli.py doctor --latency` ajoute un contrôle au doctor. Il lit les événements du compte (la même liste que le détecteur gratuit de changements `events_feed`) et, pour les derniers pushes, l'exécution de ce même commit, puis indique l'aller-retour, la médiane et le pire retard entre le début de l'exécution et l'événement, et combien de temps un changement peut attendre au pire avec votre `events_feed.interval_seconds` (dans le champ `data` de `--json`). Il ne fait que lire : rien n'est créé sur GitHub, ni ticket ni exécution de test. Une lecture qui échoue donne un avertissement « non évaluable » avec sa cause, jamais une panne du moniteur. Au-delà de 120 secondes de retard, le contrôle avertit.

## `completions` : compléter les commandes

```
python bin/monitor_cli.py completions bash > ~/.local/share/bash-completion/completions/monitor_cli.py
python bin/monitor_cli.py completions zsh  > "${fpath[1]}/_monitor_cli"
python bin/monitor_cli.py completions fish > ~/.config/fish/completions/monitor_cli.py.fish
python bin/monitor_cli.py completions powershell | Out-String | Invoke-Expression
```

Le script est écrit à partir de l'analyseur réel de la ligne de commande : il propose exactement les commandes, mots et options qui existent. Une nouvelle option ne peut pas être oubliée, et un test compare les deux. La commande se contente d'**afficher** ; elle ne modifie aucun de vos fichiers et n'a pas besoin du moniteur. Placez la sortie là où votre shell lit les complétions, comme ci-dessus.

## Codes de sortie

| Code | Signification |
|---|---|
| 0 | tout va bien (aussi Ctrl-C dans `watch`) |
| 1 | mauvais usage de la commande |
| 2 | le moniteur est injoignable |
| 3 | le moniteur ou GitHub refuse l'identifiant |
| 4 | le moniteur répond mais est dégradé (hors ligne, quota épuisé, pas encore de données) ou la réponse est illisible |
| 5 | `alerts --fail-on NIVEAU` a trouvé des alertes de ce niveau ou pire |
| 6 | `watch --exit-on-change` a vu un changement (seulement quand cette option est donnée) |

Les codes 0 à 5 sont ceux de [CLI_fra.md](CLI_fra.md) ; un test garde ce tableau et le code d'accord.

### Les codes de sortie de `status` pour un opérateur

Par défaut `status` garde les codes du tableau ci-dessus, aucun script ne change. Avec `--status-codes operator` (ou le réglage `cli.status_codes` sur `operator`) la commande ne dit que trois choses : **0** sain, **1** rien ne sert (le moniteur est injoignable ou refuse l'identifiant) et **2** en marche mais demande de l'attention. Demande de l'attention signifie : le moniteur n'atteint pas GitHub, pas encore de données, l'identifiant est aveugle, l'actualisation est en pause car le quota est sous son plancher, la réponse porte une erreur, une réponse qui n'est pas celle d'un moniteur, ou **le code sur le disque est d'une autre version que le processus en marche** (une mise à jour a été appliquée sans redémarrer le moniteur ; `/api/health` le dit par `code_stale` et `--doctor` a la vérification `running`). Une erreur d'usage reste 1. Les raisons sont dans le champ `attention` de `--json`. Les échecs de workflows rouges n'en font pas partie : pour eux, utilisez `alerts --fail-on`. `watch status` suit les mêmes codes aussi quand une lecture échoue : un moniteur injoignable ou qui refuse l'identifiant termine la boucle avec 1, une réponse illisible avec 2.

## Exemples avec `jq`

Ces exemples n'utilisent que des champs qui font partie de la forme stable des réponses, et un test les exécute contre un faux moniteur (quand `jq` est installé).

```
monitor_cli.py alerts --json | jq -r '.data.alerts[] | select(.level=="critical") | .repo'
monitor_cli.py alerts --format ndjson | jq -r '.code'
monitor_cli.py status --json | jq '.data.red_workflows'
monitor_cli.py team --json | jq -r '.data.ranking[] | .repo'
```

## `kiosk` : l'adresse pour une télévision ou un mur

`monitor_cli.py kiosk [ops|team|release|quiet]` affiche l'adresse du moniteur pour un écran que personne ne touche. Voir [KIOSK_fra.md](KIOSK_fra.md).

## Réglages

| Réglage | Défaut | Signification |
|---|---|---|
| `cli.default_format` | `text` | le format quand ni `--format` ni `--json` ne sont donnés : `text`, `table`, `plain`, `json` ou `ndjson` |
| `cli.watch.min_interval_seconds` | 2 | la pause la plus courte de `watch` (de 1 à 3600) |
| `cli.watch.default_interval_seconds` | 5 | la pause de `watch` quand `--interval` n'est pas donné (de 1 à 3600) |
| `cli.status_codes` | `classic` | les codes de sortie de `status` : `classic` (ceux du tableau) ou `operator` (0 sain, 1 rien ne sert, 2 en marche mais demande de l'attention) |
| `cli.watch.branch_timeout_seconds` | 900 | combien de temps `watch branch` attend la fin des exécutions du commit (10 à 86400) |

## Ce que cette version ne fait pas

- `completions` n'a pas de `--install` : il n'écrit jamais dans les fichiers d'un utilisateur.
- Il n'y a pas de commande `proposals` : le moniteur n'a pas encore de route de propositions sur laquelle agir.

## Sortie redirigée, couleur et largeur

- Sans terminal (une redirection, `tee`, un tube, cron) la commande n'écrit aucune séquence d'échappement, prend la largeur de `COLUMNS` quand c'est un nombre et 80 sinon, et le texte venu de GitHub (un titre, un nom) est débarrassé des séquences d'échappement qu'il pourrait porter.
- `--color auto|always|never` (par défaut `auto`) : `auto` n'écrit la couleur que dans un terminal et jamais quand `NO_COLOR` est définie (et non vide) ou `TERM=dumb` ; `always` l'écrit quelle que soit la destination ; `never` n'en écrit aucune. Seul l'en-tête de `--format table` est coloré (en gras) ; `json` et `ndjson` ne sont jamais touchés.
- Un lecteur qui se ferme plus tôt (`monitor_cli.py alerts --format plain | head -1`) termine la commande en silence : ni trace d'erreur ni texte d'erreur.

## `metrics` : les chiffres pour cron et pour le courrier

`monitor_cli.py metrics` écrit les chiffres du moniteur à raison d'une ligne `nom=valeur` chacun, dans un ordre fixe et sans rien d'autre sur la sortie standard : `repos`, `active`, `queued`, `failures_24h`, `successes_24h`, `red_workflows`, `alerts`, `alerts_info`, `alerts_warning`, `alerts_error`, `alerts_critical`, `allowance_remaining`, `allowance_limit` et `offline`. Un chiffre inconnu est omis, jamais écrit comme 0. Elle lit le moniteur, jamais GitHub.

Avec `--if-problem` elle n'écrit rien et sort avec 0 quand aucun workflow n'est rouge et qu'aucune alerte de niveau `--fail-on` (error par défaut) ou pire n'existe ; sinon elle écrit les chiffres et sort avec 5. cron envoie par courrier toute sortie : cette ligne n'envoie donc un message que le jour où quelque chose ne va pas : `*/15 * * * * py -3 /opt/monitor/bin/monitor_cli.py metrics --if-problem`. Un moniteur injoignable n'est jamais un silence : l'erreur va sur la sortie d'erreur et le code est 2.
