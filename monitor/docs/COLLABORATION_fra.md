<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COLLABORATION.md) | [🇪🇸 Español](COLLABORATION_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](COLLABORATION_ita.md) | [🇩🇪 Deutsch](COLLABORATION_deu.md) | [🇨🇳 简体中文](COLLABORATION_zho.md) | [🇯🇵 日本語](COLLABORATION_jpn.md) | [🇵🇹 Português](COLLABORATION_por.md)

# Vues de collaboration et actions facultatives

Des vues de ce qui attend quelqu'un et quelques actions GitHub qui restent désactivées tant que vous ne les autorisez pas. Éditions Complete et Full.

## Activation

Activez `teamwork.enabled` (Réglages > Collaboration). Les vues des exécutions viennent de ce que le moniteur lit déjà ; pull requests, alertes et workflows sont lus quelques dépôts par cycle (`teamwork.repos_per_cycle`, `teamwork.refresh_hours`). Le cadre est à la fin de l'onglet Collaboration de la zone Sentinelle.

## Les vues

En attente d'une personne (approbation d'environnement, workflow d'un fork, action requise), à part de l'attente d'un runner. La dernière exécution de chaque voie (workflow et branche) ; un rouge peut être mis de côté `teamwork.dismiss_days` jours, cette exécution seulement, puis rétabli. Pull requests ouvertes : fusionnables, en retard, action nécessaire ou inconnu, mises à jour de bots reconnues par auteur, branche ou étiquette ; `teamwork.hide_workflows` masque des workflows. Dépôts avec alertes critiques ou hautes et âge de la plus ancienne, et les dépôts NON lus, nommés. Avec `teamwork.dismissed_alerts`, qui a écarté des alertes ; un écart hors de `teamwork.dismiss_allowed` lève une alerte.

## Écrire sur GitHub

Rien n'est écrit sauf si `github_actions.enabled` est activé, l'action figure dans `github_actions.allowed` et vous confirmez le plan, qui montre exactement l'envoi. Nouvelles actions : `update_branch`, `approve_fork`, `approve_deployment`, `force_cancel`, `enable_workflow`, `dispatch`. Les vues ne font que PROPOSER : mises à jour de bots en échec, branches en retard, exécutions trop longtemps en file ou en cours (`teamwork.queued_hours`, `teamwork.stuck_hours`), celles visées par `teamwork.cancel_policy`, workflows désactivés pour inactivité (`teamwork.inactive_workflows`). Le formulaire d'un workflow manuel lit et vérifie ses entrées. Avec `teamwork.forks_help`, des faits sur l'auteur d'une exécution de fork ; sans verdict.

## La seule action automatique

`teamwork.auto_rerun` (désactivé) relance une fois les jobs en échec d'une exécution non démarrée ou expirée, avec les mêmes contrôles. Jamais une seconde fois ; en cas de nouvel échec, une alerte est levée.

## Maintenir une planification active

GitHub coupe les workflows planifiés d'un dépôt public après 60 jours sans activité. Avec `teamwork.keep_alive_days` (0 = désactivé ; par exemple 45), un dépôt public sans push depuis ce temps et dont des workflows ont tourné selon une planification apparaît dans les propositions comme `enable_workflow`, avec les jours restants. C'est une proposition comme les autres : rien n'est envoyé avant votre confirmation. GitHub ne documente pas qu'activer un workflow déjà actif relance son décompte, et ceci n'a pas été essayé sur un dépôt réel : le moyen sûr est un nouveau commit.

## Hooks des runners auto-hébergés

Avec `teamwork.runner_hooks`, un hook d'un runner de cet ordinateur note le début et la fin :

```
# ACTIONS_RUNNER_HOOK_JOB_STARTED
python /path/to/monitor/bin/monitor_cli.py runner-hook started
```

Pour la fin, ACTIONS_RUNNER_HOOK_JOB_COMPLETED avec `completed`. Un runner d'un autre ordinateur n'est pas couvert.

## API et ligne de commande

`GET /api/actions/state`, `GET /api/actions/dispatch-form`, `GET /api/actions/environments`, `GET /api/actions/fork-facts`, `POST /api/actions/plan`, `POST /api/actions/dismiss`.

```
python bin/monitor_cli.py actions status
python bin/monitor_cli.py actions proposals
python bin/monitor_cli.py runner-hook started
python bin/monitor_cli.py runner-hook completed
```

## Non vérifié

Lectures et écritures testées uniquement avec des réponses inventées ; aucune des nouvelles actions n'a été exécutée sur un dépôt réel.

## Tous les réglages

`teamwork.enabled` `teamwork.repos_per_cycle` `teamwork.refresh_hours` `teamwork.dismiss_days` `teamwork.hide_workflows` `teamwork.bot_authors` `teamwork.bot_branches` `teamwork.bot_labels` `teamwork.dismissed_alerts` `teamwork.dismiss_allowed` `teamwork.auto_rerun` `teamwork.cancel_policy` `teamwork.queued_hours` `teamwork.stuck_hours` `teamwork.forks_help` `teamwork.inactive_workflows` `teamwork.keep_alive_days` `teamwork.runner_hooks`
