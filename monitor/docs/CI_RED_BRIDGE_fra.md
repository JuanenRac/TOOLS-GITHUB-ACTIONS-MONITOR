<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CI_RED_BRIDGE.md) | [🇪🇸 Español](CI_RED_BRIDGE_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](CI_RED_BRIDGE_ita.md) | [🇩🇪 Deutsch](CI_RED_BRIDGE_deu.md) | [🇨🇳 简体中文](CI_RED_BRIDGE_zho.md) | [🇯🇵 日本語](CI_RED_BRIDGE_jpn.md) | [🇵🇹 Português](CI_RED_BRIDGE_por.md)

# Du moniteur au tableau de bord : `ci_red.json`

Ce que le moniteur écrit, comment l'exporter et ce dont a besoin le lecteur du fichier. Le moniteur se contente de lire GitHub et d'écrire des fichiers locaux : il ne fait jamais de push, jamais de commit et ne ferme jamais rien de lui-même.

## Ce que le moniteur écrit

`ci_red.json` à côté de `actions_monitor.py`, actualisé après chaque passage de la sentinelle (schéma 2) :

| Champ | Signification |
|---|---|
| `schema` | `2`. Les champs sont seulement ajoutés, jamais renommés. |
| `generated` | Heure UTC du passage. |
| `tool_version` | Version de l'outil qui a écrit le fichier. |
| `complete` | `true` lorsque chaque dépôt surveillé a été lu lors de ce passage. `false` pendant le chargement, lorsque le quota de l'API a manqué ou lorsque des clones sont absents : n'agissez pas sur la liste des dépôts rouges ni sur la file de signature tant que ce n'est pas `true`. |
| `red_repos` / `pending_sign_repos` | Compteurs. |
| `repos.<NAME>.ecosystem` | `armor`, `urtc`, `hydra`, `eh3d` ou `other`. |
| `repos.<NAME>.red[]` | Une entrée par workflow dont la dernière exécution terminée sur la branche par défaut a échoué : `workflow`, `conclusion`, `since`, `streak`, `url`. |
| `repos.<NAME>.pending_sign[]` et `pending_sign_hours` | Versions compilées et pas encore signées, et l'ancienneté de la plus ancienne. |

## Comment l'exporter

```
py -3 read_report.py --export-status DIR          # ci_status_public.json + .md, uniquement ce qui peut être publié
py -3 read_report.py --export-sign-queue FILE     # la file de signature
```

Les deux lisent le moniteur en cours d'exécution sur `127.0.0.1` (sans quota GitHub). Ils refusent d'écrire tant que l'instantané se charge et en indiquent la raison ; le code de sortie n'est alors pas nul.

## Ce dont a besoin un lecteur (le générateur de tableau de bord)

1. Lire `schema` ; accepter toute valeur `>= 2` et ignorer les champs inconnus.
2. Lire `complete` ; lorsque c'est `false`, conserver le dernier export complet au lieu de le remplacer.
3. Afficher `generated` à côté des chiffres afin qu'un fichier périmé se remarque.
4. Utiliser `repos.<NAME>.red[].url` comme lien ; ne jamais le reconstruire.

## Ce que le moniteur ne fait pas

Il ne publie pas le fichier, ne pousse rien vers le dépôt du profil et ne touche à aucun workflow. Acheminer l'export vers le tableau de bord est une étape du propriétaire (ou d'un workflow du dépôt du profil qui lit le fichier exporté).

## Le tableau d'état du profil (contrat du consommateur)

Le tableau d'état d'un dépôt de profil peut lire le même document de deux façons : depuis le moniteur en marche (`GET /api/outputs/dashboard.json`, désactivé tant que `outputs.dashboard.enabled` ne l'est pas, cet ordinateur seulement) ou depuis le fichier écrit par `py -3 read_report.py --export-status DIR` (workflows rouges seulement, jamais le côté signature). Ce sur quoi le tableau peut compter, vérifié par un test de ce dépôt :

1. `schema` vaut `2` et les champs ne font que s'ajouter.
2. Le document servi est exactement celui de `ci_red.json`.
3. `complete: false` signifie : gardez votre dernière image complète.
4. L'export public a les clés `schema`, `generated`, `tool_version`, `complete`, `red_repos` et `red`, et rien de l'état de signature.

Le moniteur ne pousse jamais le fichier vers le dépôt du profil ; l'y amener est une étape de son propriétaire.
