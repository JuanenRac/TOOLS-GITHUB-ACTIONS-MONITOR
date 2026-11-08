<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LITE.md) | [🇪🇸 Español](LITE_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](LITE_ita.md) | [🇩🇪 Deutsch](LITE_deu.md) | [🇨🇳 简体中文](LITE_zho.md) | [🇯🇵 日本語](LITE_jpn.md) | [🇵🇹 Português](LITE_por.md)

# L'édition lite

Un second produit, plus simple, dans le même paquet : la page de ce qui tourne et de ce qui échoue, sans la sentinelle. Pour qui veut seulement surveiller ses runs.

|  | Complète | Lite |
|---|---|---|
| Démarrage | `MONITOR_GITHUB_ACTIONS` (`.bat` / `.sh` / `.command`) | `MONITOR_LITE_GITHUB_ACTIONS` (les trois mêmes) |
| Port | 8765 | 8766 |
| Onglets | Maintenant, Sentinelle, Graphiques, Dépôts, Historique, Réglages | Maintenant, Graphiques, Dépôts, Historique, des Réglages courts |
| En-tête | toutes les tuiles, préparation, signature | en cours, en file, échecs et succès de 24 h, minutes de calcul, issues, rouges sur main, dépôts, quota, connexion |
| Sentinelle (alertes, releases, file de signature, préparation, linter) | oui | non : elle n'est même pas importée |
| Analyses, notifications, webhook, IA, sorties Prometheus / Grafana | oui, désactivés tant que vous ne les activez pas | non : ces chemins répondent 404 |
| Configuration | `actions_monitor.json` | `actions_monitor_lite.json` (créé au premier démarrage ; la sentinelle y est désactivée) |
| Fichiers d'état | `etag_cache.json`, `analytics_history.json`... | les mêmes noms avec le suffixe `_lite` |

Comment la démarrer : `MONITOR_LITE_GITHUB_ACTIONS.bat` sous Windows, `./MONITOR_LITE_GITHUB_ACTIONS.sh` sous Linux, double-clic sur `MONITOR_LITE_GITHUB_ACTIONS.command` sous macOS, ou `python actions_monitor.py --lite` (aussi `MONITOR_MODE=lite`). Elle écoute sur `127.0.0.1:8766` ; la complète peut donc tourner en même temps.

Les Réglages courts contiennent le compte (`github_owner`), les dépôts et écosystèmes à surveiller (`repos`, `ecosystems`, `exclude`), le délai d'actualisation (`refresh_seconds`), la langue et le thème. « Rouges sur main » compte les workflows dont le dernier run terminé a échoué. Pour avoir ensuite la sentinelle et le reste, lancez la complète : rien à migrer.
