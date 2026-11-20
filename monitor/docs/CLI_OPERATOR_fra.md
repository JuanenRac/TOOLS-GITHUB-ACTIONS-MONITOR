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

## Ce que cette version ne fait pas

- `completions` n'a pas de `--install` : il n'écrit jamais dans les fichiers d'un utilisateur.
- Il n'y a pas de commande `proposals` : le moniteur n'a pas encore de route de propositions sur laquelle agir.

## `metrics` : les chiffres pour cron et pour le courrier

`monitor_cli.py metrics` écrit les chiffres du moniteur à raison d'une ligne `nom=valeur` chacun, dans un ordre fixe et sans rien d'autre sur la sortie standard : `repos`, `active`, `queued`, `failures_24h`, `successes_24h`, `red_workflows`, `alerts`, `alerts_info`, `alerts_warning`, `alerts_error`, `alerts_critical`, `allowance_remaining`, `allowance_limit` et `offline`. Un chiffre inconnu est omis, jamais écrit comme 0. Elle lit le moniteur, jamais GitHub.

Avec `--if-problem` elle n'écrit rien et sort avec 0 quand aucun workflow n'est rouge et qu'aucune alerte de niveau `--fail-on` (error par défaut) ou pire n'existe ; sinon elle écrit les chiffres et sort avec 5. cron envoie par courrier toute sortie : cette ligne n'envoie donc un message que le jour où quelque chose ne va pas : `*/15 * * * * py -3 /opt/monitor/bin/monitor_cli.py metrics --if-problem`. Un moniteur injoignable n'est jamais un silence : l'erreur va sur la sortie d'erreur et le code est 2.
