<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_INDIVIDUAL.md) | [🇪🇸 Español](COMPLETE_INDIVIDUAL_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](COMPLETE_INDIVIDUAL_ita.md) | [🇩🇪 Deutsch](COMPLETE_INDIVIDUAL_deu.md) | [🇨🇳 简体中文](COMPLETE_INDIVIDUAL_zho.md) | [🇯🇵 日本語](COMPLETE_INDIVIDUAL_jpn.md) | [🇵🇹 Português](COMPLETE_INDIVIDUAL_por.md)

# Édition complète pour une personne

L'édition complète sur votre propre ordinateur est la façon habituelle d'utiliser le moniteur : une personne, un compte GitHub, aucune connexion et une page qui ne s'ouvre que sur `127.0.0.1`. L'édition simple pour qui veut seulement voir ses exécutions est [LITE_fra.md](LITE_fra.md).

## Démarrer

- Connectez-vous une fois à GitHub avec `gh auth login`, puis lancez `MONITOR_GITHUB_ACTIONS` (`.bat`, `.sh` ou `.command`). La page s'ouvre sur le port 8765 (`ports.complete`).
- Choisissez dans les Réglages les dépôts et écosystèmes à surveiller. Les cinq premières minutes sont dans [FIRST_STEPS_fra.md](FIRST_STEPS_fra.md).

## Ce que vous obtenez

- Trois sentinelles (CI activée ; Collab et Security éteintes tant que vous ne les allumez pas) et une liste d'alertes que vous pouvez mettre en sourdine depuis votre ordinateur.
- Le score du compte, la santé de chaque dépôt, des rapports programmés (éteints par défaut) et un journal des actions effectuées (activé par défaut, `audit_log.enabled`).
- Les modes de travail normal, rapide et turbo ([MODES_fra.md](MODES_fra.md)) et le mode Bas quand le quota manque ([QUOTA_fra.md](QUOTA_fra.md)).

## Le garder sur cet ordinateur

- Avec `auth.enabled` éteint (par défaut) il n'y a ni utilisateurs ni rien à retenir : n'activez le mode équipe que si plusieurs personnes utilisent le moniteur ([COMPLETE_TEAM_fra.md](COMPLETE_TEAM_fra.md)).
- `listen.network` est éteint par défaut : la page et l'API ne répondent qu'à `127.0.0.1`. Pour le laisser tourner en permanence, lisez [COMPLETE_SERVICE_fra.md](COMPLETE_SERVICE_fra.md).

## Au quotidien

- `python bin/monitor_cli.py status`, `doctor` et `health` interrogent le moniteur en marche ([CLI_fra.md](CLI_fra.md)). Pour mettre à jour, lisez [MIGRATING_fra.md](MIGRATING_fra.md).
- Vos propres scripts peuvent lire l'API : [API_fra.md](API_fra.md) indique ce qui est promis stable.
