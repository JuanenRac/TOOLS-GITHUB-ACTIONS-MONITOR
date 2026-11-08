<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](WEBHOOK.md) | [🇪🇸 Español](WEBHOOK_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](WEBHOOK_ita.md) | [🇩🇪 Deutsch](WEBHOOK_deu.md) | [🇨🇳 简体中文](WEBHOOK_zho.md) | [🇯🇵 日本語](WEBHOOK_jpn.md) | [🇵🇹 Português](WEBHOOK_por.md)

# Webhook entrant

Optionnel et **désactivé par défaut**. Il permet à GitHub de signaler au moniteur qu'un changement a eu lieu, pour que le dépôt soit actualisé au prochain cycle au lieu d'attendre la prochaine interrogation.

## Ce qu'il fait (actualiser seulement)

Un événement accepté marque seulement le dépôt nommé pour une actualisation au prochain cycle. Rien n'est écrit sur GitHub ni sur le disque, aucun texte de l'événement n'est conservé ni affiché, et seuls les dépôts déjà surveillés sont acceptés. Événements compris : `workflow_run`, `workflow_job`, `push`, `release`, `check_suite` et `ping` ; tout autre reçoit `202` et est ignoré.

## Sécurité

- Le moniteur n'écoute toujours que sur `127.0.0.1`. GitHub ne l'atteint que par un tunnel que vous montez volontairement ; l'outil n'en ouvre jamais.
- Désactivé tant que `webhook.enabled` n'est pas actif **et** que le secret partagé de `actions_monitor.json` n'a pas au moins 32 caractères (sinon le point d'accès reste fermé).
- Toute requête doit porter `X-Hub-Signature-256: sha256=<hmac>`, calculé avec ce secret ; le reste reçoit `401`. Le secret n'est jamais affiché : l'onglet Réglages indique seulement s'il est défini.
- Un corps de plus de 256 Ko reçoit `413`.

## Comment l'activer

Dans `actions_monitor.json` : `"webhook": {"enabled": true, "secret": "<32 caractères aléatoires ou plus>"}` ; l'interrupteur est aussi dans l'onglet Réglages (sous-onglet Webhook entrant), le secret seulement dans le fichier. Redémarrez le moniteur. Dans les réglages du webhook GitHub : type de contenu `application/json`, le même secret et l'URL de votre tunnel terminée par `/api/webhook`.

## Événements en temps réel

- Quand `webhook.record_events` est actif (par défaut), un événement `workflow_run` signé met aussitôt à jour la liste des runs de ce dépôt, sans lire GitHub : le dépôt ne coûte aucun quota jusqu'à sa prochaine lecture programmée. Un événement `workflow_job` apporte aussi le temps en file et le temps de chaque étape pour les analyses.
- Seuls de courts champs validés sont gardés (workflow, run, état, conclusion, branche, commit court, lien du run, durées) ; jamais le message du commit ni aucun texte libre. Les `webhook.live_events_keep` événements les plus récents se lisent sur `GET /api/live-events` (cet ordinateur seulement).
- Un run qui se termine en rouge envoie aussi la notification `workflow_failed` si les notifications sont actives. Avec `webhook.record_events` désactivé, le webhook revient au mode d'actualisation seule décrit plus haut.
- GitHub ne peut pas joindre `127.0.0.1` : utilisez `gh webhook forward` (voir la documentation de la CLI GitHub) ou un tunnel que vous montez volontairement, vers `http://127.0.0.1:PORT/api/webhook`.
