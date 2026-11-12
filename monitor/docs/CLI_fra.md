<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI.md) | [🇪🇸 Español](CLI_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](CLI_ita.md) | [🇩🇪 Deutsch](CLI_deu.md) | [🇨🇳 简体中文](CLI_zho.md) | [🇯🇵 日本語](CLI_jpn.md) | [🇵🇹 Português](CLI_por.md)

# La ligne de commande comme client du moniteur

`python monitor_cli.py COMMANDE` demande au moniteur en marche ce qu'il sait (un `GET` sur `127.0.0.1`, ou sur l'adresse de `--url` / `MONITOR_URL`) et l'affiche. Elle ne refait pas le travail de la page auprès de GitHub, n'écrit jamais sur GitHub et ne change aucun réglage. Les anciens outils (`read_report.py`, `--doctor`, `gha_dispatch_all.py`) continuent de fonctionner comme avant.

## Commandes

| Commande | Ce qu'elle montre | Lite |
|---|---|---|
| `status` | version, édition, compte, dépôts, ce qui tourne et échoue, le quota | oui |
| `health` (ou `check`) | un contrôle rapide avant de lire quoi que ce soit de lourd : le moniteur est-il joignable, accepte-t-il ce client, la connexion GitHub du compte répond-elle ? | oui |
| `doctor` | les contrôles de `--doctor` pour cette installation (le moniteur n'a pas besoin de tourner) | oui |
| `accounts` | les comptes du superviseur (plusieurs comptes seulement) | non |
| `alerts` | les alertes de toutes les sentinelles dans une liste : `--sentinel ci\|collab`, `--level info\|warning\|error`, `--muted show\|hide\|only` | non |
| `live` | l'état du récepteur de webhook et les derniers évènements | non |

Options de toutes les commandes : `--json` (la réponse comme un document JSON : `{"ok", "exit", "data"}`), `--account ID`, `--url URL`, `--lite` (port 8766), `--timeout SECONDES` (1 à 60), `--lang CODE`. En mode réseau, mettez le jeton d'accès dans la variable d'environnement `MONITOR_ACCESS_TOKEN`, celle que lit le moniteur lui-même (`MONITOR_TOKEN` est accepté comme alias ; `--token JETON` est le dernier recours, car une option apparaît dans la liste des processus). L'ordre : `MONITOR_ACCESS_TOKEN`, puis `MONITOR_TOKEN`, puis `--token`. Il voyage dans l'en-tête `X-Monitor-Access`, jamais dans l'adresse ni à l'écran. Un `--url` en `http` non chiffré vers un autre ordinateur affiche un avertissement sur stderr (le jeton et les réponses circuleraient en clair) : utilisez `https` hors d'un réseau que vous contrôlez.

Les heures écrites pour les personnes (la ligne `Last read`, les sourdines, le journal, les rapports, les notifications) utilisent le fuseau de cet ordinateur et le nomment, avec l'heure UTC à côté (`11:43:07 CET (10:43:07 UTC)`). Choisissez un autre fuseau avec `display.timezone` (`local`, `utc` ou un nom comme `Europe/Madrid` ; la variable d'environnement `MONITOR_TIMEZONE` l'emporte sur le fichier). `--json` garde l'UTC et ajoute `updated_local`.

## Codes de sortie (stables)

| Code | Signification |
|---|---|
| 0 | tout va bien |
| 1 | mauvais usage de la commande (aussi `--lite` avec une commande qui demande l'édition complète) |
| 2 | le moniteur est injoignable |
| 3 | le moniteur refuse ce client, ou la connexion GitHub du compte a échoué ou expiré (un problème d'identifiant, pas un quota épuisé) |
| 4 | le moniteur répond mais est dégradé : hors ligne, quota épuisé, pas encore de données, un point d'accès qu'il n'a pas, ou une réponse qui n'est pas du JSON |
| 5 | `alerts --fail-on NIVEAU` a trouvé une alerte ouverte de ce niveau ou pire (une alerte en sourdine ne compte pas) |

## Exemples

```
python monitor_cli.py health && python monitor_cli.py alerts --fail-on error
python monitor_cli.py alerts --sentinel collab --level warning --json
python monitor_cli.py status --account org-acme
MONITOR_URL=http://192.168.0.20:8765 MONITOR_ACCESS_TOKEN=... python monitor_cli.py health --json
```

`health` distingue trois choses : le moniteur ne répond pas (2), la connexion GitHub échoue (3), et le quota est épuisé ou GitHub est injoignable (4) ; un moniteur qui n'a pas fini sa première lecture le dit (4) au lieu de montrer des chiffres vides.

## L'édition lite

`python monitor_cli.py status --lite`, `doctor --lite` et `health --lite` parlent au port 8766. Les commandes qui demandent des comptes, des sentinelles ou le récepteur de webhook sont refusées avec le code de sortie 1. L'édition lite n'a ni comptes ni API d'alertes.

## `ai-hook` : dire à un outil d'IA ce que voit le moniteur

`python monitor_cli.py ai-hook install|status|uninstall [--cursor|--generic] [--scope project|user] [--project-dir DIR] [--dry-run] [--json]` n'a pas besoin d'un moniteur en marche. Il ajoute, montre ou retire le script de liaison `ai_hook.py` dans les réglages de crochets d'un outil d'IA (voir le guide des alertes pour IA) : le fichier de réglages est fusionné, une copie est gardée et la réponse de `--json` est de l'ASCII pur. `status` est l'action par défaut.

## Le jeton d'accès en ligne de commande

En mode réseau le jeton est lu dans `MONITOR_ACCESS_TOKEN`, puis `MONITOR_TOKEN`, puis la première ligne de `--token-file FICHIER` (garde ce fichier lisible par toi seul : sur un système avec des modes de fichier la commande avertit si d'autres peuvent le lire) et enfin `--token`, qui apparaît dans la liste des processus et affiche donc un avertissement sur stderr.
