<p align="center">
  <img src="images/GITHUB_ACTIONS_MONITOR_BANNER.svg" alt="GitHub Actions Monitor" width="100%">
</p>

# GitHub Actions Monitor

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <b>🇫🇷 Français</b> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

<p align="center">
  <a href="https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases/latest"><img src="https://img.shields.io/github/v/release/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR?label=version&color=2EE6A6" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL-3.0-or-later">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Dependencies-none-2EE6A6.svg" alt="No dependencies">
  <img src="https://img.shields.io/badge/Languages-8-FFB300.svg" alt="8 languages">
</p>

> Surveille les workflows de tous vos dépôts et vous dit, sur une page locale, ce qui est rouge, ce qui est bloqué et ce qui vous attend.

**GitHub Actions Monitor** est un petit programme qui tourne sur votre propre ordinateur. Il interroge GitHub, avec votre propre connexion `gh`, sur les dernières exécutions de chaque workflow de vos dépôts, décide ce qui est vraiment rouge, signale l'important (sécurité, hygiène, versions prêtes, quota) et affiche tout sur une page web que seul votre ordinateur peut ouvrir. Il ne demande que Python et `gh`, ne stocke jamais de jeton et, par défaut, il ne fait que lire.

## En un coup d'œil

| | |
|---|---|
| **Version** | **1.7.9** · [toutes les versions](https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases) |
| **Prérequis** | Python 3.11+ et la CLI GitHub (`gh auth login`) ; rien d'autre (la vue console utilise le paquet optionnel `rich`) |
| **S'ouvre** | sur une page `127.0.0.1` uniquement, en huit langues |
| **Écrit sur GitHub** | jamais seul : seulement les commandes par lots que vous lancez avec un `--go` explicite |
| **Exporte** | `ci_red.json`, des métriques Prometheus et du JSON pour Grafana (tout désactivé tant que vous ne l'activez pas) |

<!-- glance:begin -->

**Mesuré aujourd'hui** (v1.7.9)

| | |
|---|---|
| **Maturité** | functional |
| **Tests** | 1415 méthodes de test (`python -m unittest discover -s monitor/tests`) |
| **Réglages** | 291 réglages, tous avec aide |
| **Langues** | 8 (anglais, espagnol, allemand, français, italien, japonais, chinois et portugais) |
| **Testé dans le CI sur** | ubuntu, windows, macos, Python 3.11, 3.13 |

## État du projet

Chaque ligne est une partie de ce dépôt et le voyant dit où elle en est aujourd'hui : ce que les tests et le CI peuvent montrer et ce qui a tourné pour de vrai, pas ce qui est prévu.

🟢 Fait et vérifié · 🟡 Fonctionne, avec des limites connues · 🟠 En partie fait ou pas encore vérifié · 🔴 Pas fait ou ne fonctionne pas

| Domaine | État | Ce que cela veut dire ici |
|---|---|---|
| Moniteur et page | 🟢 | Tourne chaque jour sur un vrai compte ; les tests tournent dans le CI sur trois systèmes. |
| Sentinelle (A1..A13) | 🟢 | Tourne chaque jour sur un vrai compte ; ses niveaux et lignes sont testés avec des fixtures. |
| Notifications | 🟡 | Testées contre des serveurs simulés ; tous les canaux n'ont pas été essayés avec le vrai service. |
| Connexion à un outil d'IA et MCP | 🟡 | Le flux, l'état, le flux en direct, le hook et les outils MCP sont testés avec un vrai serveur et un client simulé ; aucun utilisateur indépendant ne les a encore utilisés. |
| Édition lite | 🟡 | Testée dans le CI et partage les canaux et réglages de la complète ; peu d'usage réel jusqu'ici. |
| GitHub App, panneau central et mode économe | 🟠 | Nouveau : testé avec des serveurs et fichiers simulés ; pas encore tourné longtemps avec le vrai service. |
| Linux et macOS | 🟠 | Testés seulement dans le CI ; l'usage quotidien est sous Windows. |

<!-- glance:end -->

## Captures d'écran

### La page

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_now_light.png"><img src="docs/screenshots/web_now_dark.png" alt="Maintenant" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_alerts_light.png"><img src="docs/screenshots/web_alerts_dark.png" alt="Alertes : toutes les sentinelles dans une liste, avec des sourdines locales" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_light.png"><img src="docs/screenshots/web_sentinel_dark.png" alt="Sentinelle" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_queue_light.png"><img src="docs/screenshots/web_sentinel_queue_dark.png" alt="File de signature (le plus urgent d'abord)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_analytics_light.png"><img src="docs/screenshots/web_sentinel_analytics_dark.png" alt="A12 · Analyses : durées, temps en file, étapes et workflows instables" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_charts_light.png"><img src="docs/screenshots/web_charts_dark.png" alt="Graphiques" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_repositories_light.png"><img src="docs/screenshots/web_repositories_dark.png" alt="Dépôts" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_history_light.png"><img src="docs/screenshots/web_history_dark.png" alt="Historique" width="92%"></picture></p>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_about_light.png"><img src="docs/screenshots/web_about_dark.png" alt="À propos" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_help_light.png"><img src="docs/screenshots/web_help_dark.png" alt="Aide, avec recherche et hors ligne" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_basic_light.png"><img src="docs/screenshots/web_settings_basic_dark.png" alt="Réglages · Essentiel : offre, quotas et découverte" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_network_now_light.png"><img src="docs/screenshots/web_network_now_dark.png" alt="Le mode réseau : la barre rouge persistante" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_network_notices_light.png"><img src="docs/screenshots/web_network_notices_dark.png" alt="La barre du pied : l'avis le plus important et la fenêtre avec tous" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_network_settings_light.png"><img src="docs/screenshots/web_network_settings_dark.png" alt="Réglages · le mode réseau avec son avertissement et le nom du proxy HTTPS" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_accounts_all_light.png"><img src="docs/screenshots/web_accounts_all_dark.png" alt="Tous les comptes : une carte par compte" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_accounts_one_light.png"><img src="docs/screenshots/web_accounts_one_dark.png" alt="La page d'un compte, avec le sélecteur" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_accounts_live_light.png"><img src="docs/screenshots/web_accounts_live_dark.png" alt="Vue En direct : le récepteur de webhook et le mode de travail" width="92%"></picture></p>

<details><summary><b>Réglages, sous-onglet par sous-onglet</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_interface_light.png"><img src="docs/screenshots/web_settings_interface_dark.png" alt="Réglages · Ce navigateur" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_general_light.png"><img src="docs/screenshots/web_settings_general_dark.png" alt="Réglages · Général" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_polling_light.png"><img src="docs/screenshots/web_settings_polling_dark.png" alt="Réglages · Actualisation et limites" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_cache_light.png"><img src="docs/screenshots/web_settings_cache_dark.png" alt="Réglages · Lectures et cache" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_sentinel_light.png"><img src="docs/screenshots/web_settings_sentinel_dark.png" alt="Réglages · Sentinelle" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_surface_light.png"><img src="docs/screenshots/web_settings_surface_dark.png" alt="Réglages · Contrôles de surface (A10)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_readiness_light.png"><img src="docs/screenshots/web_settings_readiness_dark.png" alt="Réglages · Préparation (A11)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_paths_light.png"><img src="docs/screenshots/web_settings_paths_dark.png" alt="Réglages · Dossiers et fichiers" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_outputs_light.png"><img src="docs/screenshots/web_settings_outputs_dark.png" alt="Réglages · Sorties pour d'autres outils" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_ai_light.png"><img src="docs/screenshots/web_settings_ai_dark.png" alt="Réglages · IA externe pour la sentinelle" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_webhook_light.png"><img src="docs/screenshots/web_settings_webhook_dark.png" alt="Réglages · Webhook entrant" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_notify_light.png"><img src="docs/screenshots/web_settings_notify_dark.png" alt="Réglages · Notifications" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_analytics_light.png"><img src="docs/screenshots/web_settings_analytics_dark.png" alt="Réglages · Analyses" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_lint_light.png"><img src="docs/screenshots/web_settings_lint_dark.png" alt="Réglages · Linter de workflows" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_console_light.png"><img src="docs/screenshots/web_settings_console_dark.png" alt="Réglages · Vue console" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_advanced_light.png"><img src="docs/screenshots/web_settings_advanced_dark.png" alt="Réglages · Avancé (optionnel)" width="92%"></picture></p>

</details>

<details><summary><b>Outils console</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_read_report_light.png"><img src="docs/screenshots/console_read_report_dark.png" alt="read_report.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_migrate_state_light.png"><img src="docs/screenshots/console_migrate_state_dark.png" alt="migrate_state.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_plan_light.png"><img src="docs/screenshots/console_plan_dark.png" alt="gha_dispatch_all.py plan" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_lint_light.png"><img src="docs/screenshots/console_lint_dark.png" alt="lint_workflows.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_tui_light.png"><img src="docs/screenshots/console_tui_dark.png" alt="tui.py" width="92%"></picture></p>

</details>

<details><summary><b>L'édition lite</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_now_light.png"><img src="docs/screenshots/web_lite_now_dark.png" alt="lite · Maintenant" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_charts_light.png"><img src="docs/screenshots/web_lite_charts_dark.png" alt="lite · Graphiques" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_history_light.png"><img src="docs/screenshots/web_lite_history_dark.png" alt="lite · Historique" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_settings_light.png"><img src="docs/screenshots/web_lite_settings_dark.png" alt="lite · Réglages" width="92%"></picture></p>

</details>

Chaque image suit le thème clair ou sombre de votre page GitHub.

*Données de démonstration : les dépôts et noms des images sont inventés.*

## Ce qu'il fait

- **Rouge ou non, avec une seule règle** : la dernière exécution terminée de chaque workflow sur la branche par défaut. Les exécutions annulées ou ignorées ne masquent jamais un échec antérieur.
- **Sentinelle** : alertes de sécurité, hygiène des dépôts, pull requests anciennes, versions prêtes à publier, builds en attente de signature et rapport en langage clair.
- **Sentinelle Collab et une seule liste d'alertes** : issues et pull requests ouvertes qui demandent une personne (oubliées, critiques, revues en attente, vieux brouillons, conflits), en lecture seule et sur une horloge propre, et un onglet Alertes avec toutes les sentinelles dans une liste, un filtre par origine et des mises en sourdine locales qui se terminent seules.
- **Une barre d'état, le plein écran et des tableaux triables** : l'avis le plus important (et une fenêtre avec tous), la connexion, le quota, la dernière lecture, le mode, l'adresse et l'horloge au pied de la page ; un bouton plein écran ; Dépôts et Historique se trient selon une ou plusieurs colonnes, avec les colonnes de votre choix.
- **La ligne de commande comme client** : `monitor_cli.py` (`status`, `health`, `alerts`, `accounts`, `live`, `doctor`) lit ce que dit le moniteur en marche, avec `--json` et des codes de sortie stables ; elle n'écrit jamais sur GitHub.
- **Page de réglages** : modifiez chemins, intervalles, quotas et interrupteurs depuis le navigateur ; seulement une liste fixe de clés validées, avec sauvegarde avant chaque enregistrement.
- **Graphiques et historique** : minutes de calcul, échecs et succès avec des barres animées et un historique quotidien (respecte la réduction des animations).
- **Huit langues** (en, es, de, fr, it, ja, zh, pt) avec l'anglais comme base ; changement dans les réglages.
- **Sorties pour tableaux de bord** : `ci_red.json`, un point d'accès Prometheus et une source JSON pour Grafana, avec un tableau Grafana importable.
- **Outils par lots** : planifient et lancent plusieurs builds à la fois ; rien n'est lancé sans `--go`.
- **À propos et Aide dans la page** : le bouton **i** montre la version, l'édition, les liens, les fichiers, l'état de santé et un bouton qui copie les informations pour le support ; le bouton **?** (ou la touche `?`) ouvre toute la documentation, avec recherche et dans votre langue, sans Internet. La console offre `--about` et `--help-topics`, et une application interactive de terminal par onglets (`textual` facultatif).
- **Avis de nouvelle version** : un badge discret quand une version plus récente est publiée ; il ne lit la page publique des versions qu'une fois par jour, n'installe jamais rien et peut être désactivé (toujours désactivé sur une installation isolée).
- **Quotas pour tout compte** : offre, minutes facturables (les dépôts publics ne coûtent rien), quota de l'API lu dans les en-têtes de GitHub, concurrence et jobs proches de la limite de 6 heures ; les chiffres sont dans un fichier modifiable.

## Architecture

<p align="center"><img src="images/architecture.svg" alt="Architecture" width="100%"></p>

## Commencez ici : quelle édition ?

| Si vous voulez... | Démarrage | Port |
|---|---|---|
| voir ce qui tourne et ce qui échoue, rien de plus (**commencez ici**) | `MONITOR_LITE_GITHUB_ACTIONS` | 8766 |
| tout le compte surveillé pour vous : alertes, releases, signature, préparation, analytique | `MONITOR_GITHUB_ACTIONS` (avec la [sentinelle](monitor/docs/SENTINEL_fra.md)) | 8765 |

La fenêtre de console indique laquelle tourne, dans son titre et sa première ligne. Encore un doute ? `python actions_monitor.py --demo` ouvre la page avec des données inventées et `--doctor` vérifie votre installation. [Vos cinq premières minutes](monitor/docs/FIRST_STEPS_fra.md)

## Démarrage rapide

1. Installez Python 3.11 ou plus récent et la [CLI GitHub](https://cli.github.com/), puis lancez `gh auth login`.
2. Téléchargez ce dépôt (ou le zip de la dernière release) et ouvrez le dossier `monitor`.
3. Démarrez-le : Windows `MONITOR_GITHUB_ACTIONS.bat`, Linux `./MONITOR_GITHUB_ACTIONS.sh`, macOS double-clic sur `MONITOR_GITHUB_ACTIONS.command`, ou `python actions_monitor.py` partout.
4. Ouvrez l'adresse affichée (`http://127.0.0.1:<port>`). Au premier démarrage, il crée `actions_monitor.json` à partir de l'exemple.
5. Ouvrez **Réglages** pour indiquer votre compte GitHub, les écosystèmes (groupes de dépôts par préfixe de nom) et le reste.

> Vous mettez à jour depuis une version antérieure à la 1.5.0 ? [`monitor/docs/MIGRATING_fra.md`](monitor/docs/MIGRATING_fra.md)

## L'édition lite

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

[`monitor/docs/LITE_fra.md`](monitor/docs/LITE_fra.md)

## Réglages

Tout vit dans `actions_monitor.json` (créé depuis `monitor/assets/examples/actions_monitor.example.json`). L'onglet **Réglages** le modifie en toute sécurité ; les jetons et secrets ne sont jamais affichés ni enregistrés. Les écosystèmes, cibles de build et profils de lot sont des fichiers séparés que vous indiquez (`ecosystems_file`, `targets_file`, `profiles_file`) ; des modèles neutres `*.example.json` sont fournis. Référence complète : [`monitor/docs/SETTINGS_fra.md`](monitor/docs/SETTINGS_fra.md).

## Sorties pour Grafana et tableaux de bord

Tout est désactivé par défaut, local uniquement (`127.0.0.1`) et sans jeton supplémentaire. Une fois activé dans les réglages : `/metrics` (format Prometheus), `/api/outputs/grafana.json` et `/api/outputs/dashboard.json`, plus un tableau Grafana importable dans [`monitor/docs/grafana`](monitor/docs/grafana). Détails : [`monitor/docs/OUTPUTS_fra.md`](monitor/docs/OUTPUTS_fra.md). Le format de `ci_red.json` : [`monitor/docs/CI_RED_SCHEMA_fra.md`](monitor/docs/CI_RED_SCHEMA_fra.md).

## Sécurité

- Il n'écoute que sur `127.0.0.1` et refuse les requêtes dont le `Host` ou l'`Origin` n'est pas local. Ne le liez jamais à `0.0.0.0` : il n'a pas de connexion.
- Il ne stocke aucun jeton : il utilise votre propre `gh` (sauf si vous activez le jeton optionnel du moniteur dans Réglages > Avancé).
- Il n'écrit rien sur GitHub de lui-même. Seuls `dispatch --go`, `dispatch --real` et `finalize --execute` écrivent, et seulement quand vous les lancez.
- **Analyses** : p50 / p95 de la durée, du temps en file et de chaque étape de chaque workflow, workflows instables (échoués puis réussis sur le même commit) et workflows devenus plus lents ; export vers Prometheus et Grafana.
- **Économise le quota et survit à une coupure** : lectures conditionnelles (un 304 ne coûte rien) et un mode dernière image avec bandeau hors ligne qui reprend seul.
- **Webhook entrant et notifications** : des événements signés mettent un dépôt à jour en temps réel ; messages optionnels vers Telegram, Discord, Slack, Matrix, MQTT ou une adresse locale (jamais une écriture sur GitHub).
- **Linter de workflows et vue console** : `lint_workflows.py` contrôle `.github/workflows` avant le push ; `tui.py` (optionnel, avec `rich`) affiche une grille en direct dans la console.
- **Assistant IA (désactivé par défaut)** : résumés, tri et explications avec Ollama, un service compatible OpenAI, Anthropic ou `gh copilot` ; commandes uniquement d'une liste fermée, exécutées seulement après confirmation de chacune.
- La page de réglages écrit une liste fixe de clés validées, après avoir enregistré une copie de sauvegarde.

## Tests

Ils n'ont besoin ni de réseau ni de paquet supplémentaire :

```
python -m unittest discover -s monitor/tests
```

## Structure du dépôt

<p align="center"><img src="images/repository-structure.svg" alt="Structure du dépôt" width="100%"></p>

```
TOOLS-GITHUB-ACTIONS-MONITOR/
├── monitor/                                le programme
├── docs/                                   architecture, captures, feuille de route
├── tools/                                  images, guides et démo
├── deploy/                                 exemple de conteneur
├── images/                                 bannière et images
├── .github/                                CI et formulaires
├── CHANGELOG.md                            changements par version
├── LICENSE NOTICE AUTHORS                  licences et auteur
├── CONTRIBUTING.md SECURITY.md             aider, signaler
├── SUPPORT.md CODE_OF_CONDUCT.md           aide et conduite
└── monitor/
    ├── MONITOR_GITHUB_ACTIONS.*            les lanceurs (double clic)
    ├── MONITOR_LITE_GITHUB_ACTIONS.*       l'édition lite
    ├── BATCH_GITHUB_ACTIONS.*              le menu des builds par lots
    ├── src/                                le paquet importable
    ├── assets/                             exemples, page, langues
    ├── actions_monitor.py read_report.py   points d'entrée des outils
    ├── tests/                              tests hors ligne
    ├── docs/                               guides, schémas, Grafana
    └── tools/                              scripts de version et de migration
```

## Documentation

- [`monitor/docs/SETTINGS_fra.md`](monitor/docs/SETTINGS_fra.md): tous les réglages
- [`monitor/docs/OUTPUTS_fra.md`](monitor/docs/OUTPUTS_fra.md): métriques, Grafana et exports
- [`monitor/docs/CI_RED_SCHEMA_fra.md`](monitor/docs/CI_RED_SCHEMA_fra.md): le format de ci_red.json
- [`monitor/docs/CI_RED_BRIDGE_fra.md`](monitor/docs/CI_RED_BRIDGE_fra.md): amener ci_red.json vers un tableau de bord
- [`monitor/docs/WEBHOOK_fra.md`](monitor/docs/WEBHOOK_fra.md): le webhook entrant
- [`monitor/docs/LITE_fra.md`](monitor/docs/LITE_fra.md): L'édition lite
- [`monitor/docs/NOTIFICATIONS_fra.md`](monitor/docs/NOTIFICATIONS_fra.md): notifications et contrat des adaptateurs
- [`monitor/docs/AI_fra.md`](monitor/docs/AI_fra.md): l'assistant IA : fournisseurs, sécurité et actions
- [`monitor/docs/ANALYTICS_fra.md`](monitor/docs/ANALYTICS_fra.md): analyses, lectures conditionnelles et connexion perdue
- [`monitor/docs/CONSOLE_TOOLS_fra.md`](monitor/docs/CONSOLE_TOOLS_fra.md): le linter de workflows et la vue console
- [`monitor/docs/DEPLOYMENT_fra.md`](monitor/docs/DEPLOYMENT_fra.md): l'exécuter comme service, derrière un proxy, permissions
- [`monitor/QUICKSTART_fr.txt`](monitor/QUICKSTART_fr.txt): premiers pas, en huit langues
- [`monitor/docs/FIRST_STEPS_fra.md`](monitor/docs/FIRST_STEPS_fra.md) : vos cinq premières minutes
- [`monitor/docs/SENTINEL_fra.md`](monitor/docs/SENTINEL_fra.md) : la sentinelle et ses contrôles A1-A13
- [`monitor/docs/COLLAB_fra.md`](monitor/docs/COLLAB_fra.md) : la sentinelle Collab, l'onglet Alertes et les sourdines
- [`monitor/docs/CLI_fra.md`](monitor/docs/CLI_fra.md) : la ligne de commande comme client du moniteur
- [`monitor/docs/ACCOUNTS_fra.md`](monitor/docs/ACCOUNTS_fra.md) : plusieurs comptes, un processus chacun
- [`monitor/docs/QUOTAS_fra.md`](monitor/docs/QUOTAS_fra.md) : quotas et offres de GitHub
- [`monitor/docs/MODES_fra.md`](monitor/docs/MODES_fra.md) : modes de travail : normal, rapide et turbo
- [`monitor/docs/AI_CONNECTION_fra.md`](monitor/docs/AI_CONNECTION_fra.md): Connecter un outil d'IA : tout ce que dit le moniteur, en signaux, dans le résumé, le point d'accès, les outils MCP et le hook
- [`monitor/docs/QUOTA_fra.md`](monitor/docs/QUOTA_fra.md): Plus de quota, moins de dépense : mode économe, le panneau central, une GitHub App et comment partager le quota

## Contribuer

Lisez [CONTRIBUTING.md](CONTRIBUTING.md). Signalez bogues et idées avec les formulaires d'issues ; les problèmes de sécurité comme décrit dans [SECURITY.md](SECURITY.md).

## Auteur

Écrit par **JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## Licence

Le code est sous GPL-3.0-or-later ; la documentation sous CC BY-SA 4.0. Voir [LICENSE](LICENSE) et [NOTICE](NOTICE).
