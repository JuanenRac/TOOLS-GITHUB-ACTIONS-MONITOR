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
- Le secret partagé est la seule barrière : GitHub ne peut pas envoyer de jeton d'accès, le récepteur n'en demande donc pas et ne se fie qu'à la signature. Avec le récepteur activé et sans secret, il refuse toute livraison avec `401`, et le doctor le signale en rouge. Gardez l'adresse derrière un tunnel ou un proxy que vous contrôlez.
- Chaque requête doit porter `X-Hub-Signature-256: sha256=<hmac>`, calculé avec ce secret et comparé en temps constant ; toute autre reçoit `401`, et rien du contenu n'est regardé avant la vérification de la signature.
- Un corps de plus de `webhook.max_body_kb` (1 Mio par défaut, jusqu'à 25 Mio) reçoit `413`, avant toute lecture ou tout calcul ; les refus sont comptés dans `stats.too_big`.
- Les listes sont fermées : seuls `workflow_run`, `workflow_job`, `check_run`, `push`, `release`, `check_suite` et `ping` sont traités, seuls des champs courts et validés d'un événement sont conservés (jamais un message de commit ni un texte libre), et tout le reste reçoit `202` et est écarté.

## Comment l'activer

1. Créez un secret de 32 caractères aléatoires ou plus, par exemple `python -c "import secrets; print(secrets.token_hex(32))"`.
2. Donnez-le au moniteur par son environnement, jamais par le fichier : `$env:MONITOR_WEBHOOK_SECRET = "<le secret>"` dans PowerShell avant de lancer le moniteur, `export MONITOR_WEBHOOK_SECRET=...` dans un shell, `Environment=` ou `EnvironmentFile=` (un fichier que vous seul pouvez lire) dans un service, `-e` ou un fichier de secret nommé par `MONITOR_WEBHOOK_SECRET_FILE` dans un conteneur.
3. Activez le récepteur (Réglages > Webhook entrant > Récepteur activé, ou `"webhook": {"enabled": true}` dans `actions_monitor.json`) et redémarrez le moniteur.
4. Rendez l'adresse joignable : GitHub n'atteint pas `127.0.0.1`. Utilisez un tunnel que vous montez volontairement (une adresse HTTPS terminée par `/api/webhook`) ou, sur cet ordinateur, `gh webhook forward` vers `http://127.0.0.1:PORT/api/webhook` (voir la documentation de la CLI GitHub pour lui donner le même secret sans l'écrire sur la ligne de commande).
5. Dans GitHub, ouvrez le dépôt (ou l'organisation) > Settings > Webhooks > Add webhook. **Payload URL** : l'adresse de votre tunnel terminée par `/api/webhook`. **Content type** : `application/json`. **Secret** : le même secret. **SSL verification** : activée. **Events** : « Let me select individual events », puis Workflow runs et Workflow jobs, et en option Check runs, Pushes et Releases. **Active** : activé. Un webhook d'organisation couvre tous ses dépôts ; le moniteur ignore ceux qu'il ne surveille pas.
6. Vérifiez : dans GitHub, Recent deliveries doit montrer `200` pour le premier `ping` ; dans le moniteur, la vue En direct montre le récepteur actif, les compteurs et la couverture.

## Événements en temps réel

- Quand `webhook.record_events` est actif (par défaut), un événement `workflow_run` signé met aussitôt à jour la liste des runs de ce dépôt, sans lire d'abord GitHub : le run garde le type d'événement qu'il avait déjà, donc sa couleur ne change pas, et le dépôt est relu au cycle suivant pour le confirmer (une lecture par événement accepté). Un événement `workflow_job` apporte aussi le temps en file et le temps de chaque étape pour les analyses.
- Seuls de courts champs validés sont gardés (workflow, run, état, conclusion, branche, commit court, lien du run, durées) ; jamais le message du commit ni l'auteur. Les noms courts du workflow, de la branche, du job et des étapes sont aussi gardés, sur une ligne et nettoyés comme tout texte qui sort du moniteur. Les `webhook.live_events_keep` événements les plus récents se lisent sur `GET /api/live-events` (en mode réseau, avec le jeton d'accès).
- Quand `webhook.record_events` est actif (par défaut), un événement `workflow_run` signé met aussitôt à jour la liste des runs de ce dépôt, sans lire GitHub : le dépôt est quand même relu au cycle suivant (l'événement est la nouvelle, la lecture est la preuve) : une livraison montre le changement aussitôt mais n'économise pas une lecture. Un événement `workflow_job` apporte aussi le temps en file et le temps de chaque étape pour les analyses.
- Seuls de courts champs validés sont gardés (workflow, run, état, conclusion, branche, commit court, lien du run, durées) ; jamais le message du commit. Les noms du workflow, de la branche et du job sont du texte de tiers jusqu'à 100 caractères : ils sont gardés et affichés comme texte brut, et les noms des étapes vont aux statistiques. Les `webhook.live_events_keep` événements les plus récents se lisent sur `GET /api/live-events` (qui peut ouvrir la page : le jeton d'accès en mode réseau, une session en mode équipe).
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
| `413` | Le corps dépasse `webhook.max_body_kb` (1 Mio par défaut). |
| `503` | La file d'événements est pleine : GitHub ou vous la renvoyez plus tard (`Retry-After`) ; la livraison n'est pas retenue comme doublon. |
| `400` | Pas d'identifiant `X-GitHub-Delivery` valide, ou contenu incompréhensible. |
| `202` | Accepté et ignoré : dépôt non surveillé, événement hors liste, envoi répété ou dépôt au-delà de sa limite par minute. |
| `429` | Une adresse a envoyé plus de 120 requêtes correctement signées en une minute, ou plus de `webhook.max_bad_per_minute` (120 par défaut) dont la signature ne se vérifie pas. |

## Rejeux et inondations

Une requête signée valide qu'on a capturée puis renvoyée reçoit une réponse mais n'est pas exécutée : chaque livraison a besoin de son identifiant `X-GitHub-Delivery`, les identifiants déjà acceptés, ainsi que le corps signé lui-même, sont mémorisés pendant `webhook.replay_seconds` (une heure par défaut, mémoire bornée) : une requête capturée et renvoyée avec un autre identifiant est donc la même livraison, et une répétition reçoit `202 {"duplicate": true}`. (Une nouvelle livraison manuelle depuis la page GitHub répète le même corps : elle est donc ignorée dans cette fenêtre.) Un dépôt peut provoquer au plus `webhook.max_per_minute` événements acceptés par minute ; les autres reçoivent une réponse et sont ignorés. Si la charge indique `full_name`, son propriétaire doit être le compte surveillé (ou l'un de `webhook.allowed_owners`). Une adresse peut envoyer 120 requêtes correctement signées par minute et `webhook.max_bad_per_minute` dont la signature ne se vérifie pas ; les deux sont comptées à part, dans tous les modes, si bien que les requêtes parasites n'entament jamais le quota des vraies livraisons (avec `listen.trusted_proxy`, l'adresse est celle que le proxy a vue). Après un événement accepté, les lectures conditionnelles mémorisées de ce dépôt sont supprimées et il est relu au cycle suivant : un événement en direct est toujours réconcilié avec GitHub. La mémoire des livraisons est gardée dans un fichier privé du dossier de données (`webhook.persist_deliveries`, actif par défaut ; bornée, et un fichier abîmé donne une mémoire vide) : un redémarrage ne rend donc pas sa validité à une livraison capturée. Avec `webhook.reject_stale` actif (désactivé par défaut), un événement de workflow signé dont l'heure propre est plus ancienne que `webhook.replay_seconds` reçoit une réponse et est ignoré. Le quota de requêtes correctement signées d'une adresse est `webhook.max_verified_per_minute` (120). `webhook.secret_env` n'accepte jamais une variable du système ou de votre connexion à GitHub (PATH, GH_TOKEN...) ni un secret qui appartient à un autre réglage, et un nom ne peut être écrit que dans un seul réglage.

L'horloge utilisée est toujours celle de cet ordinateur, jamais celle de la livraison. `webhook.clock_skew_s` (300 secondes par défaut, de 0 à 3600) est l'écart que deux horloges peuvent avoir : un événement qui paraît aussi ancien par rapport à la fenêtre n'est pas périmé pour autant (`webhook.reject_stale`), et un événement marqué quand l'horloge de cet ordinateur était en avance puis reculée compte quand même comme arrivé, de sorte qu'un dépôt n'apparaît pas mort à cause d'une horloge ; il vieillit à partir du moment où on le remarque. Une marque en avance de plus d'un jour n'est pas crue. `webhook.reject_stale` est activé par défaut : un événement de run ou de job dont l'heure propre est plus ancienne que `webhook.replay_seconds` plus cet écart reçoit `202` et n'est pas exécuté, et une livraison est mémorisée exactement aussi longtemps plus l'écart (la mémoire est bornée par le temps, avec un filet de sécurité de 20000 entrées) ; une livraison capturée ne peut donc plus être acceptée une fois que la mémoire l'a laissée partir. Le lien d'un run (`html_url`) n'est gardé que s'il pointe vers github.com ou vers l'hôte de `GH_HOST`.

## Ordre, file d'attente et livraisons perdues

- **Ordre.** GitHub ne promet pas l'ordre des livraisons. Une exécution ou un job ne fait qu'avancer (en file, en cours, terminé) : un événement qui en dit moins que ce que l'on sait déjà de la même exécution (ce que le dernier cycle a lu compte aussi) ne change rien et est compté dans `stats.out_of_order` de `GET /api/live-status`. Une nouvelle tentative d'une exécution repart de zéro.
- **File d'attente.** Un événement accepté attend dans une file d'au plus `webhook.queue_max` événements (500 par défaut, de 1 à 10000) et un travailleur l'applique, si bien que GitHub reçoit vite une réponse. Quand la file est pleine, le récepteur répond `503` avec `Retry-After` et oublie la livraison, de sorte que celle que GitHub renvoie est acceptée : un événement n'est jamais abandonné en silence. La profondeur est `queue` dans `GET /api/live-status` et les refus sont `stats.queue_full`.
- **Livraisons perdues.** Une exécution qu'un événement a laissée ouverte (en file ou en cours) et qui ne reçoit aucun événement final dans les `webhook.stale_after_h` heures (6 par défaut, de 1 à 168) est marquée `stale` dans la liste des exécutions et son dépôt est relu au cycle suivant (`stats.stale` ; `open_runs` compte les exécutions tenues ouvertes).
- **Prêt.** `GET /readyz` (cet ordinateur seulement) répond `200` quand le moniteur peut prendre du travail et `503` sinon, avec le contrôle qui échoue : `loaded` (une première lecture est faite), `cycle` (la boucle d'actualisation n'est ni bloquée ni arrêtée), `store` (le dossier de données est inscriptible) et `queue` (la file a de la place). `GET /api/health` dit seulement que le processus vit.

## Sans webhook : les événements du compte (désactivé par défaut)

Avec `events_feed.enabled` activé, le moniteur lit les événements du compte (`GET /orgs/OWNER/events`, ou `/users/OWNER/events` ; `events_feed.owner_kind` dit lequel, et `auto` essaie d'abord l'organisation) tous les `events_feed.interval_seconds` (60 par défaut ; `X-Poll-Interval` l'emporte s'il est plus long) avec un ETag. Une lecture qui ne trouve rien de nouveau répond `304` et ne coûte aucun quota ; quand quelque chose a changé (un push, une pull request, un tag ou une release), seul le dépôt nommé dans l'événement est relu au cycle suivant, au plus `events_feed.max_per_tick` par tour. La première lecture apprend seulement où en est la liste. Il ne demande ni webhook ni tunnel et peut fonctionner à côté d'un. Les compteurs sont `feed` dans `GET /api/live-status`.

## Sans adresse publique : le WebSocket de GitHub (désactivé par défaut)

GitHub ne peut pas joindre un moniteur à la maison, derrière un routeur. Avec `webhook.transport` sur `websocket`, la CLI GitHub fait l'inverse : `gh webhook forward` crée un webhook temporaire, garde une connexion ouverte depuis cet ordinateur et remet chaque livraison au récepteur du moniteur, donc rien n'est exposé et aucun tunnel n'est nécessaire.

- `webhook.ws_targets` liste ce qu'il faut transférer : `propriétaire/dépôt` pour un dépôt ou `propriétaire` pour toute une organisation (un compte personnel demande une entrée par dépôt, au plus `webhook.ws_max_targets`). Vide par défaut : changer seulement le transport ne démarre rien. Le récepteur doit être actif (`webhook.enabled` et le secret partagé) et le moniteur redémarré.
- Il **écrit dans GitHub** (les hooks temporaires) et demande un jeton qui peut gérer les webhooks (`admin:repo_hook`, `admin:org_hook`). Avec un jeton qui ne le peut pas, l'état de la cible dit `forbidden` et il n'est réessayé que toutes les quelques minutes.
- Les livraisons sont signées avec un secret créé à chaque démarrage, gardé en mémoire et passé à `gh` sur sa ligne de commande ; un autre processus du même utilisateur sur cet ordinateur pourrait le lire, et il permet seulement à cet utilisateur d'envoyer des événements à un récepteur qui est sur cet ordinateur. Le secret partagé lui-même ne quitte jamais l'environnement. GitHub ne signe pas chaque trame du WebSocket séparément : la connexion est authentifiée par le jeton.
- Un transfert qui se termine est relancé avec une attente de plus en plus longue (de 5 secondes à 5 minutes). Un hook accepte un seul abonné : ne lancez pas `gh webhook forward` à la main pour la même cible. Les livraisons de ce transport n'apparaissent pas comme renvoyables dans la page du hook dans GitHub, donc la récupération ci-dessous ne marche qu'avec le transport `http`.
- `webhook.ws_cleanup` (désactivé) supprime au démarrage les hooks qui pointent vers le transfert de GitHub dans les cibles indiquées, ce qui nettoie ce qu'un plantage a laissé ; il supprime des hooks, donc ne l'activez que si vous savez qu'aucune autre session ne les utilise.
- L'état de chaque transfert est `forwarders` dans `GET /api/live-status`.

## Livraisons qui ne sont jamais arrivées (désactivé par défaut)

Un moniteur à la maison n'est pas toujours allumé : l'ordinateur est éteint la nuit, le tunnel tombe. GitHub garde les livraisons récentes d'un webhook, dit lesquelles ont échoué et permet de renvoyer une livraison échouée. Avec `webhook.redeliver.enabled` activé, le moniteur examine les webhooks que vous nommez dans `webhook.redeliver.hooks` (`repo:PROPRIÉTAIRE/DÉPÔT#ID` ou `org:PROPRIÉTAIRE#ID`, où ID est le nombre à la fin de l'adresse du webhook dans GitHub) une minute après le démarrage puis toutes les `webhook.redeliver.interval_minutes` (60 par défaut), et demande à GitHub de renvoyer les livraisons qu'aucune tentative n'a eu de 2xx.

- **Il écrit dans GitHub** (la demande de renvoi) et demande un jeton qui peut gérer le webhook. Désactivé par défaut ; les livraisons d'une GitHub App ne sont pas couvertes.
- Au plus `webhook.redeliver.max_per_run` (20) livraisons par passage, aucune plus ancienne que `webhook.redeliver.max_age_hours` (24 ; GitHub les garde trois jours), celles jamais redemandées d'abord. Une livraison est redemandée avec une attente croissante (5, 10, 20, 40, 80, 160 et 300 secondes) et abandonnée (`dead`) après la huitième fois. Ce qui a été demandé est gardé dans un fichier privé du dossier de données (l'identifiant de la livraison et le compte, jamais une charge), donc un redémarrage ne redemande pas aussitôt.
- Une livraison qui arrive de nouveau est traitée comme un doublon par le récepteur : demander deux fois ne fait pas de mal.
- `POST /api/webhook/redeliver` (administrateurs, cet ordinateur seulement, avec le jeton à usage unique) examine tout de suite, quel que soit l'horaire, et laisse une ligne dans le journal des actions. Les compteurs sont `redelivery` dans `GET /api/live-status`.

## Liste de contrôle de la vue en direct

1. Mettez un secret d'au moins 32 caractères dans la variable d'environnement indiquée par `webhook.secret_env` et activez le webhook.
2. Redirigez le port (`gh webhook forward`) ou ouvrez un tunnel et utilisez son adresse terminée par `/api/webhook` dans GitHub.
3. Lancez un workflow (ou faites un push dans un dépôt surveillé) et cherchez l'évènement dans `?view=live`. Le `ping` de GitHub ne prouve que la signature : il reçoit `200` et n'est pas listé, et un renvoi depuis GitHub est ignoré comme une répétition.
4. Surveillez le quota dans l'en-tête : avec les webhooks, un cycle plus lent suffit.
