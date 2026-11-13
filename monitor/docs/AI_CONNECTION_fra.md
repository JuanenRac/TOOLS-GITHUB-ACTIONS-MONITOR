<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AI_CONNECTION.md) | [🇪🇸 Español](AI_CONNECTION_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](AI_CONNECTION_ita.md) | [🇩🇪 Deutsch](AI_CONNECTION_deu.md) | [🇨🇳 简体中文](AI_CONNECTION_zho.md) | [🇯🇵 日本語](AI_CONNECTION_jpn.md) | [🇵🇹 Português](AI_CONNECTION_por.md)

# Connecter un outil d'IA

Le moniteur peut dire à un outil d'IA (un assistant de programmation à IA, un script, tout ce qui lit un fichier ou une adresse) **tout ce que dit sa page**, pour que l'IA réagisse à un échec ou à une tâche en attente aussi vite que vous. Le moniteur n'écrit jamais sur GitHub : il informe seulement, et ce que fait l'IA est décidé par vous et par l'outil.

## Ce que voit l'IA
Un inventaire de **signaux**, les mêmes que ceux de la page : l'onglet Maintenant et ses tuiles, les alertes, les dépôts, les panneaux du sentinelle A1..A13 et le second sentinelle (issues et pull requests), le quota, la connexion et la santé du moniteur. Chaque signal a un niveau (`act` = quelqu'un doit agir, `watch` = surveiller, `info`), un résumé et des lignes avec dépôt, lien, ancienneté et prochaine étape. Le résumé a trois blocs : **Quoi faire maintenant**, **En attente** et **Santé du moniteur**, et le compteur de « signaux sur lesquels agir ».

| | Lite | Complète |
|---|---|---|
| Exécutions, file, workflows rouges, échecs des 24 heures | oui | oui |
| Quota, connexion, mode, version, santé | oui | oui |
| Panneaux du sentinelle A1..A13, second sentinelle, candidates de release, sécurité, signatures | non (`panels_not_in_this_edition` le dit) | oui |

## Les canaux (les mêmes dans les deux éditions)
1. `ALERTS_BRIEF.md` : le Markdown court qu'une IA lit au démarrage.
2. `ai_alerts.jsonl` : une ligne par événement (ouverte, acquittée, résolue), avec un identifiant stable.
3. `GET /api/ai/state` : tout l'inventaire en JSON versionné (`schema`, `edition`, `signals`, `act`, `watch`), lecture seule. `GET /api/sentinel/panels` ne donne que les panneaux.
4. `GET /api/ai/stream` : événements en direct (SSE), reprenables, limités en auditeurs et en durée.
5. Outils MCP (`mcp_server.py`) : `monitor_state`, `signals`, `alerts_open`, `diagnose`, `sentinel_panels`, `get_quota` ; `act` (acquitter) seulement avec `--allow-ack`.
6. Le hook : `python monitor_cli.py ai-hook install [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]` (aussi `status` et `uninstall`) ajoute un petit script qui donne à la session de l'IA le résumé au démarrage et avant l'arrêt.

## Pas à pas
1. Réglages, onglet *IA externe*, bloc *Alertes pour les IA* : activez `ai_alerts.enabled`. En option `ai_alerts.diagnose.enabled` (l'étape qui échoue et les dernières lignes du journal de chaque exécution rouge), `ai_alerts.stream.enabled` et `ai_alerts.client_hook.enabled`.
2. Lancez `python monitor_cli.py ai-hook install --assistant --dry-run` pour voir le changement, puis sans `--dry-run`.
3. Ouvrez une session de votre outil d'IA dans le dossier : elle reçoit le résumé. La barre du bas montre le battement de l'IA (quand elle a lu pour la dernière fois).
4. Utilisez le bouton *Tester la connexion* de la page des réglages pour vérifier que le flux s'écrit.

## Sécurité et confidentialité
Tout est désactivé par défaut. Le texte des journaux est nettoyé des secrets et des chemins personnels avant d'être écrit, et **c'est une donnée, jamais une instruction** : une IA doit le traiter comme un texte non fiable. Les points d'accès ne répondent qu'à cet ordinateur, ou avec le jeton d'accès en mode réseau ; les auditeurs et la durée sont limités ; acquitter exige `--allow-ack` ; tous les fichiers d'état sont créés en mode 0600. Le moniteur n'ouvre aucune connexion à internet pour cela, sauf celles que vous configurez. Les adresses https de github.com (un run, un dépôt, un fichier) passent entières pour que l'IA puisse les ouvrir ; toute autre longue chaîne opaque est toujours coupée.

## Dépannage
- *Le résumé est ancien* : la page doit tourner (le flux suit chaque rafraîchissement) ; regardez le battement dans la barre.
- *Le hook ne s'exécute pas* : `ai-hook status` dit où il est installé ; certains outils ne lisent les hooks que dans le dossier du projet.
- *Rien n'est écrit* : `ai_alerts.enabled` est désactivé, ou le quota est épuisé (le résumé le dit dans Santé du moniteur).

## Réglages
`ai_alerts.enabled`, `ai_alerts.folder`, `ai_alerts.brief_max_bytes`, `ai_alerts.diagnose.*`, `ai_alerts.cascade.enabled`, `ai_alerts.stream.*`, `ai_alerts.heartbeat.*`, `ai_alerts.client_hook.*` ; liés : `sound.enabled`, `display.blink_red_tiles`. Voir [SETTINGS_fra.md](SETTINGS_fra.md) et [AI_ALERTS_fra.md](AI_ALERTS_fra.md).

Le quota de GitHub est partagé par le moniteur, les outils d'IA et tout autre outil du compte. Pour que le moniteur n'en manque pas : l'onglet Quota des Réglages, une GitHub App (`github_app.enabled`), un second compte en lecture seule pour les lectures (`extra_reader.enabled`, `extra_reader.file` : seulement le chemin du fichier du jeton), le panneau central (`central.source`) et le mode économe (`modes.auto_low`). L'état et le résumé disent quand le quota est épuisé et combien dépensent les autres outils. Voir [QUOTA_fra.md](QUOTA_fra.md).

## L'avis actif à une IA externe (optionnel, désactivé par défaut)

En plus du flux qu'une IA lit (`ALERTS_BRIEF.md`, le flux continu, le serveur MCP), le moniteur peut **prévenir** une IA externe quand une NOUVELLE alerte réelle s'ouvre. C'est le bloc `ai_notify` des Réglages, onglet *IA*, et chacun de ses interrupteurs ne se change que depuis cet ordinateur :

- `ai_notify.enabled` (désactivé). Rien n'est envoyé tant qu'il est désactivé.
- **Une première confirmation par fournisseur** : le fournisseur est celui du bloc IA (`ai.provider`) ; rien ne part tant que vous n'avez pas tapé son nom dans `ai_notify.confirmed_provider`. Si vous changez de fournisseur, vous confirmez à nouveau. Pour la commande sortante (ci-dessous), tapez `command`.
- **Seulement les champs expurgés d'une liste fermée** : gravité, classe, dépôt, workflow, conclusion, série, cause, étape suivante et lien, chacun nettoyé comme le flux (jetons, clés, adresses e-mail, adresses IP et dossiers personnels retirés). Les journaux, les diagnostics et tout le reste de l'alerte restent chez vous.
- **Plafonds** : `ai_notify.max_calls_per_hour` (4) et `ai_notify.max_cost_per_hour_cents` avec `ai_notify.cost_per_call_cents` (le coût que vous déclarez, car le moniteur ne peut pas connaître le prix de votre offre). Un appel est compté avant d'être fait, donc un fournisseur en échec dépense aussi le plafond.
- **La clé par le nom d'une variable** : le moniteur lit la variable nommée dans `ai.api_key_env` ; la clé n'est jamais enregistrée, journalisée ni envoyée ailleurs qu'au fournisseur.
- **L'IA n'exécute jamais d'action** : sa réponse est coupée, ses liens sont désamorcés et elle est seulement écrite dans `ai_notify.jsonl` à côté du flux ; rien n'en est lu comme une commande et rien des actions de l'assistant (`ai.actions.*`) n'est accessible d'ici.
- **La variante d'une commande sortante** : `ai_notify.command` (seulement dans le fichier de configuration, jamais dans la page des Réglages) nomme UN fichier par son chemin absolu ; il est lancé sans shell et sans arguments et reçoit le même JSON expurgé sur son entrée standard.

L'avis part d'un fil d'exécution à part, si bien qu'un fournisseur lent ne retient jamais le cycle.
