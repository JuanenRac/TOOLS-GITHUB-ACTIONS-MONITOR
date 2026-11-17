<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](WEBHOOK.md) | [🇪🇸 Español](WEBHOOK_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](WEBHOOK_ita.md) | [🇩🇪 Deutsch](WEBHOOK_deu.md) | [🇨🇳 简体中文](WEBHOOK_zho.md) | [🇯🇵 日本語](WEBHOOK_jpn.md) | [🇵🇹 Português](WEBHOOK_por.md)

# Webhook entrant

Optionnel et **désactivé par défaut**. Il permet à GitHub de signaler au moniteur qu'un changement a eu lieu, pour que le dépôt soit actualisé au prochain cycle au lieu d'attendre la prochaine interrogation.

## Ce qu'il fait (actualiser seulement)

Un événement accepté marque seulement le dépôt nommé pour une actualisation au prochain cycle. Rien n'est écrit sur GitHub ni sur le disque, aucun texte de l'événement n'est conservé ni affiché, et seuls les dépôts déjà surveillés sont acceptés. Événements compris : `workflow_run`, `workflow_job`, `push`, `release`, `check_run`, `check_suite` et `ping` ; tout autre reçoit `202` et est ignoré.

## Sécurité

- Le moniteur n'écoute toujours que sur `127.0.0.1`. GitHub ne peut l'atteindre que par un tunnel que vous montez volontairement ; l'outil n'en ouvre jamais.
- Éteint tant que `webhook.enabled` n'est pas activé **et** que le secret partagé (32 caractères ou plus) n'est pas dans la variable d'environnement indiquée par `webhook.secret_env` (`MONITOR_WEBHOOK_SECRET` par défaut ; `MONITOR_WEBHOOK_SECRET_FILE` peut nommer un fichier dont la première ligne est le secret, comme les secrets d'un conteneur). Le secret n'est jamais écrit dans `actions_monitor.json`, ni affiché, ni journalisé, ni hérité par les programmes que le moniteur lance ; l'onglet Réglages dit seulement s'il est défini. L'ancienne méthode (un `secret` dans le fichier) n'est lue que si `webhook.allow_config_secret` est vrai, et la vue En direct avertit tant qu'elle sert.
- Chaque requête doit porter `X-Hub-Signature-256: sha256=<hmac>`, calculé avec ce secret et comparé en temps constant ; toute autre reçoit `401`, et rien du contenu n'est regardé avant la vérification de la signature.
- Un corps de plus de 256 Ko reçoit `413`, avant tout calcul.
- Les listes sont fermées : seuls `workflow_run`, `workflow_job`, `check_run`, `push`, `release`, `check_suite` et `ping` sont traités, seuls des champs courts et validés d'un événement sont conservés (jamais un message de commit ni un texte libre), et tout le reste reçoit `202` et est écarté.

## Comment l'activer

1. Créez un secret de 32 caractères aléatoires ou plus, par exemple `python -c "import secrets; print(secrets.token_hex(32))"`.
2. Donnez-le au moniteur par son environnement, jamais par le fichier : `$env:MONITOR_WEBHOOK_SECRET = "<le secret>"` dans PowerShell avant de lancer le moniteur, `export MONITOR_WEBHOOK_SECRET=...` dans un shell, `Environment=` ou `EnvironmentFile=` (un fichier que vous seul pouvez lire) dans un service, `-e` ou un fichier de secret nommé par `MONITOR_WEBHOOK_SECRET_FILE` dans un conteneur.
3. Activez le récepteur (Réglages > Webhook entrant > Récepteur activé, ou `"webhook": {"enabled": true}` dans `actions_monitor.json`) et redémarrez le moniteur.
4. Rendez l'adresse joignable : GitHub n'atteint pas `127.0.0.1`. Utilisez un tunnel que vous montez volontairement (une adresse HTTPS terminée par `/api/webhook`) ou, sur cet ordinateur, `gh webhook forward` vers `http://127.0.0.1:PORT/api/webhook` (voir la documentation de la CLI GitHub pour lui donner le même secret sans l'écrire sur la ligne de commande).
5. Dans GitHub, ouvrez le dépôt (ou l'organisation) > Settings > Webhooks > Add webhook. **Payload URL** : l'adresse de votre tunnel terminée par `/api/webhook`. **Content type** : `application/json`. **Secret** : le même secret. **SSL verification** : activée. **Events** : « Let me select individual events », puis Workflow runs et Workflow jobs, et en option Check runs, Pushes et Releases. **Active** : activé. Un webhook d'organisation couvre tous ses dépôts ; le moniteur ignore ceux qu'il ne surveille pas.
6. Vérifiez : dans GitHub, Recent deliveries doit montrer `200` pour le premier `ping` ; dans le moniteur, la vue En direct montre le récepteur actif, les compteurs et la couverture.

## Événements en temps réel

- Quand `webhook.record_events` est actif (par défaut), un événement `workflow_run` signé met aussitôt à jour la liste des runs de ce dépôt, sans lire GitHub : le dépôt ne coûte aucun quota jusqu'à sa prochaine lecture programmée. Un événement `workflow_job` apporte aussi le temps en file et le temps de chaque étape pour les analyses.
- Seuls de courts champs validés sont gardés (workflow, run, état, conclusion, branche, commit court, lien du run, durées) ; jamais le message du commit ni aucun texte libre. Les `webhook.live_events_keep` événements les plus récents se lisent sur `GET /api/live-events` (cet ordinateur seulement).
- Optionnel, désactivé par défaut : avec `live.sse.enabled` actif, `GET /api/live-events/stream` envoie ces mêmes événements dès leur acceptation, sous forme d'événements serveur (`hello`, puis une trame `live` par événement, avec un `id` croissant pour reprendre via `Last-Event-ID` ou `?since=`, un commentaire de maintien et un `bye` final). Lecture seule ; en mode réseau, il demande le jeton d'accès comme toute requête ; au plus `live.sse.max_clients` écouteurs, chacun pendant `live.sse.max_seconds`. L'édition Lite ne l'a pas.
- Un run qui se termine en rouge envoie aussi la notification `workflow_failed` si les notifications sont actives. Avec `webhook.record_events` désactivé, le webhook revient au mode d'actualisation seule décrit plus haut.
- GitHub ne peut pas joindre `127.0.0.1` : utilisez `gh webhook forward` (voir la documentation de la CLI GitHub) ou un tunnel que vous montez volontairement, vers `http://127.0.0.1:PORT/api/webhook`.

## Couverture dans le temps

La vue En direct indique quelle part du temps les événements couvrent l'état : **couvert par des événements** (le dernier événement est plus récent que `savings.webhook_window_minutes`, 60 minutes par défaut), **aucun événement depuis ...** (plus ancien : un dépôt calme ou un tunnel perdu) ou **en attente du premier événement**. L'interrogation reste toujours le secours : un envoi qui n'est jamais arrivé (moniteur éteint, tunnel coupé) est rattrapé par la lecture suivante du dépôt ; les événements réduisent donc les lectures sans jamais les remplacer. Les mêmes chiffres sont dans `GET /api/live-status`, sous `coverage` et `secret_source` (`env`, `config` ou `none` ; jamais le secret).

## Si cela ne marche pas

| Réponse | Signification |
|---|---|
| `404` | Le récepteur est éteint, ou le secret manque ou fait moins de 32 caractères dans la variable d'environnement. |
| `401` | La signature ne correspond pas : même secret des deux côtés et type de contenu `application/json`. |
| `413` | Le corps dépasse 256 Ko. |
| `400` | Pas d'identifiant `X-GitHub-Delivery` valide, ou contenu incompréhensible. |
| `202` | Accepté et ignoré : dépôt non surveillé, événement hors liste, envoi répété ou dépôt au-delà de sa limite par minute. |
| `429` | Une adresse a envoyé plus de 120 requêtes en une minute (mode réseau). |

## Rejeux et inondations

Une requête signée valide qu'on a capturée puis renvoyée reçoit une réponse mais n'est pas exécutée : chaque livraison a besoin de son identifiant `X-GitHub-Delivery`, les identifiants déjà acceptés sont mémorisés pendant `webhook.replay_seconds` (une heure par défaut, mémoire bornée) et une répétition reçoit `202 {"duplicate": true}`. (Une nouvelle livraison manuelle depuis la page GitHub réutilise l'identifiant : elle est donc ignorée dans cette fenêtre.) Un dépôt peut provoquer au plus `webhook.max_per_minute` événements acceptés par minute ; les autres reçoivent une réponse et sont ignorés. Si la charge indique `full_name`, son propriétaire doit être le compte surveillé (ou l'un de `webhook.allowed_owners`). En mode réseau, une adresse peut envoyer 120 requêtes par minute. Après un événement accepté, les lectures conditionnelles mémorisées de ce dépôt sont supprimées et il est relu au cycle suivant : un événement en direct est toujours réconcilié avec GitHub.

## Liste de contrôle de la vue en direct

1. Mettez un secret d'au moins 32 caractères dans la variable d'environnement indiquée par `webhook.secret_env` et activez le webhook.
2. Redirigez le port (`gh webhook forward`) ou ouvrez un tunnel et utilisez son adresse terminée par `/api/webhook` dans GitHub.
3. Lancez un workflow (ou faites un push dans un dépôt surveillé) et cherchez l'évènement dans `?view=live`. Le `ping` de GitHub ne prouve que la signature : il reçoit `200` et n'est pas listé, et un renvoi depuis GitHub est ignoré comme une répétition.
4. Surveillez le quota dans l'en-tête : avec les webhooks, un cycle plus lent suffit.
