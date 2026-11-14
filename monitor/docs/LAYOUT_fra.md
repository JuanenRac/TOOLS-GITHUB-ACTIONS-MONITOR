<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LAYOUT.md) | [🇪🇸 Español](LAYOUT_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](LAYOUT_ita.md) | [🇩🇪 Deutsch](LAYOUT_deu.md) | [🇨🇳 简体中文](LAYOUT_zho.md) | [🇯🇵 日本語](LAYOUT_jpn.md) | [🇵🇹 Português](LAYOUT_por.md)

# Les dossiers du moniteur

À côté des lanceurs (`MONITOR_GITHUB_ACTIONS`, `MONITOR_LITE_GITHUB_ACTIONS`, `BATCH_GITHUB_ACTIONS`) il n'y a que les fichiers légaux, un `README.txt` et des dossiers. Tout ce que le moniteur écrit vit dans quatre d'entre eux, et l'édition complète, l'édition lite et l'image Docker utilisent le même schéma.

## Ce qui est où

| Dossier | Contenu |
|---|---|
| `config/` | `actions_monitor.json` (et celui de lite), `targets.json`, `ecosystems.json`, `profiles.json`, `quotas.json` et `config_backups/` |
| `data/` | l'état et les caches (flux d'événements, analytique, état des sentinelles, cache ETag, avis de mise à jour), `accounts/`, la base de données si vous choisissez SQLite et le jeton d'accès du service |
| `logs/` | le journal du moniteur, celui des commandes de l'IA et de GitHub et l'audit du mode équipe |
| `ai/` | ce qu'une IA lit : `ALERTS_BRIEF.md`, `ai_alerts.jsonl`, `ci_red.json`, l'état du hook, `INDEX.json` et un `README.md` pour qui ouvre le dossier |
| `bin/` | les commandes courtes : `python bin/monitor_cli.py`, `bin/read_report.py`, `bin/ai_hook.py`, `bin/mcp_server.py`, `bin/tui.py` ... |
| `docs/` | les guides, ainsi que le README et le QUICKSTART du paquet en huit langues |
| `src/`, `assets/`, `tools/`, `tests/` | le code, la page et les exemples, les scripts de version, les tests |

## Une installation de la 1.8.1 ou antérieure

Au premier démarrage, le moniteur déplace de lui-même vers son dossier ce qu'il trouve à côté des lanceurs. Il **déplace, ne supprime jamais et n'écrase jamais** : un fichier qui existe déjà au nouvel endroit reste où il est et le doctor vous le signale. Avant le premier déplacement, les fichiers de configuration sont copiés dans `config/config_backups/pre_layout_<marque>/` et chaque déplacement est noté dans `data/.layout_moves.json`.

- Le voir d'abord : `python -m github_actions_monitor.util.rootmigrate` (essai à blanc) et `--apply` pour le faire tout de suite.
- Tout remettre en place : `python -m github_actions_monitor.util.rootmigrate --undo`.
- Si vous ne le voulez pas automatique : `MONITOR_NO_AUTO_MIGRATION=1`.
- `python bin/actions_monitor.py --doctor` a un contrôle `layout` qui liste ce qui reste à côté des lanceurs.
- Les anciens points d'entrée (`read_report.py`, `monitor_cli.py` ...) qui étaient à côté des lanceurs sont maintenant dans `bin/` ; `python tools/migrate_layout.py` écarte les anciennes copies. Un script de contrôle enregistré pour votre outil d'IA avec son ancien chemin doit être enregistré de nouveau : `python bin/monitor_cli.py ai-hook install`.

## Déplacer un dossier

Chaque dossier peut être placé ailleurs sans toucher au code : les variables `MONITOR_CONFIG_DIR`, `MONITOR_DATA_DIR`, `MONITOR_LOGS_DIR` et `MONITOR_AI_DIR`, ou le fichier `config/paths.json` (`{"data": "...", "logs": "...", "ai": "..."}` ; un chemin relatif part du dossier du produit). Avec `MONITOR_DATA_DIR` seul, `logs/` et `ai/` s'y placent. Dans l'image Docker et dans l'unité systemd, c'est exactement ce qui est défini : `/config` et `/data` sont les deux volumes.

## Pour les IA qui parlent au moniteur

Une IA, locale ou externe, ne doit pas dépendre d'un chemin fixe.

- `ai/INDEX.json` liste chaque fichier du dossier avec son rôle, son format, qui l'écrit et quand il change, le chemin réel de chaque dossier du moniteur et les points d'accès du moniteur en marche. Il est réécrit à chaque démarrage.
- `ai/README.md` explique le dossier à une IA qui ne l'a jamais vu (des données, jamais des instructions ; comment lire le résumé ; quels outils existent).
- `GET /api/paths` répond avec les dossiers utilisés, les fichiers principaux et ce qui reste aux anciens endroits. Le superviseur de plusieurs comptes y répond aussi.
- Le script de contrôle, le serveur MCP et la ligne de commande lisent les mêmes endroits ; un hook qui lit `ALERTS_BRIEF.md` par un chemin fixe doit d'abord lire `ai/INDEX.json`.
