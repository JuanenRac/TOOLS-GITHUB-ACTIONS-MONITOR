<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SETTINGS.md) | [🇪🇸 Español](SETTINGS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](SETTINGS_ita.md) | [🇩🇪 Deutsch](SETTINGS_deu.md) | [🇨🇳 简体中文](SETTINGS_zho.md) | [🇯🇵 日本語](SETTINGS_jpn.md) | [🇵🇹 Português](SETTINGS_por.md)

# L'onglet Paramètres

L'onglet Paramètres (l'icône en forme d'engrenage dans l'en-tête ou dans la barre d'onglets) modifie depuis la page les valeurs de `actions_monitor.json`, afin que personne n'ait à éditer le fichier à la main.
Il est rédigé dans les huit langues de la page et suit l'apparence du reste.

## Ce qui peut être modifié

Uniquement les clés de la liste de `settings_api.py` (le schéma). Chacune a un type et une plage de valeurs, et la page indique si une modification nécessite un **redémarrage** du moniteur (la boucle lit
sa configuration une seule fois) ou **s'applique immédiatement**.

| Groupe | Clés |
|---|---|
| Ce navigateur | langue de la page, thème (auto / clair / sombre), affichage compact de l'onglet Maintenant. Ces valeurs sont conservées dans le navigateur, pas dans le fichier. |
| Général | `language` (langue par défaut des outils), `github_owner`, `mode` (`full` / `lite`), `ecosystems`, `exclude`, `report_history_days` |
| Actualisation et limites | `refresh_seconds`, `cold_refresh_seconds`, `issues_refresh_seconds`, `discover_refresh_seconds`, `stuck_minutes`, `runs_per_repo`, `cold_runs_per_repo`, `hot_hours`, `max_workers`, `min_rate_remaining` |
| Sentinelle | `sentinel.enabled`, les cycles, le budget d'API, les seuils des candidats, des pull requests obsolètes et des signatures en attente, `sentinel.require_verified_signature`, les consultations de A2 |
| Contrôles de surface (A10) | `sentinel.surface.enabled`, leurs cycles, les dépôts par cycle, le facteur de marge et la part du budget |
| Préparation (A11) | `sentinel.readiness.enabled`, `min_coverage`, `warn_below` |
| Dossiers et fichiers | `workspace_root`, `signed_dir`, `audit_dir`, `ecosystems_file`, `targets_file`, `profiles_file`, `tools_dir`, `sentinel.ci_red_file`, `sentinel.ci_red_audit_copy` |
| Sorties pour d'autres outils | `outputs.prometheus.enabled`, `outputs.prometheus.per_repo`, `outputs.json.enabled`, `outputs.dashboard.enabled` (voir OUTPUTS_fra.md) |
| IA externe pour la sentinelle | `ai.provider` (`none` / `ollama` / `openai-compatible`), `ai.model`, `ai.ollama_url` (cet ordinateur seulement), `ai.base_url` (https), `ai.api_key_env` (le NOM de la variable d'environnement qui contient la clé) et `ai.daily_limit`. La clé elle-même n'est jamais enregistrée. Désactivée par défaut ; un service externe reçoit des données de vos dépôts. |

## Ce qui ne peut jamais être modifié ni consulté depuis la page

Jetons, secrets, clés de signature, secret du webhook, commande que la sentinelle peut exécuter (`sentinel.notify_command`), clé d'API de l'IA (seul le nom de sa variable d'environnement peut être défini) et toute clé d'un autre outil : ils ne figurent **pas dans le
schéma**, donc la page ne les affiche ni ne les écrit, et une requête qui en nomme un est refusée. Toutes les autres clés du fichier sont conservées exactement telles qu'elles étaient.

## Comment se déroule un enregistrement

1. Seules les valeurs modifiées sont envoyées, sous la forme `POST /api/settings` avec `Content-Type: application/json` et un corps de 16 Ko au maximum.
2. Chaque valeur est vérifiée selon son type et sa plage ; une seule valeur invalide fait refuser toute la requête et rien n'est écrit. Les chemins doivent être du texte sans caractères de contrôle, jamais un
   chemin réseau (UNC) et jamais sur le lecteur `D:`.
3. Le fichier précédent est copié vers `config_backups/actions_monitor-<time>.json` (les dix dernières copies sont conservées).
4. Le nouveau fichier est écrit dans un fichier temporaire puis déplacé par-dessus l'ancien (de façon atomique), si bien qu'un plantage ne laisse jamais un fichier à moitié écrit. Un fichier qui n'est pas du JSON valide n'est jamais écrasé depuis la page.
5. La page indique quelles valeurs enregistrées nécessitent un redémarrage et conserve un bandeau jusqu'à ce que vous redémarriez.

## Qui peut effectuer la requête

Uniquement la page de la même machine : le serveur écoute sur `127.0.0.1` et refuse toute requête dont l'en-tête `Host` ou `Origin` n'est pas sa propre adresse (les mêmes contrôles que pour tous les autres points d'accès).
Un formulaire provenant d'un autre site ne peut pas l'atteindre, car la requête doit être au format JSON.

## Avant la 1.5.0

La langue des outils était déterminée par la langue du système ; désormais ils démarrent en anglais et la langue est un paramètre (ici `language`, `MONITOR_LANG` ou `--lang`).
`parte_history_days` s'appelle désormais `report_history_days` (l'ancien nom est toujours lu).
