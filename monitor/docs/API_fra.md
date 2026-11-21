<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](API.md) | [🇪🇸 Español](API_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](API_ita.md) | [🇩🇪 Deutsch](API_deu.md) | [🇨🇳 简体中文](API_zho.md) | [🇯🇵 日本語](API_jpn.md) | [🇵🇹 Português](API_por.md)

# L'API pour les clients

Ce sur quoi un script, un écran mural ou un client mobile peut compter. Depuis la 2.0.0 les points d'accès en lecture sont figés : une clé du contrat garde son nom et son type, de nouvelles clés peuvent apparaître et rien n'est retiré ni changé sans une nouvelle version majeure.

## Interroger

- En mode normal l'API répond sur `127.0.0.1` sans connexion. En mode réseau chaque requête porte le jeton d'accès dans l'en-tête `X-Monitor-Access` (ou le cookie de session, ou `POST /api/access` une fois). Avec le mode équipe un script se connecte à `POST /api/auth/login`.
- Un mot de la requête qu'un point d'accès ne connaît pas est ignoré. Les réponses sont du JSON en UTF-8, sauf le résumé en Markdown et les flux.

## Erreurs

- Une erreur est du JSON `{"error": "mot"}`, parfois avec un `code`. `401 access` signifie que le jeton manque ou est faux, `403 forbidden` que la requête ne vient pas d'où elle est permise (aussi un `Host` étranger), `404` que le chemin n'existe pas dans cette édition (la lite répond 404 pour ce que seule la complète a), `429` que l'adresse est bloquée ou que les écouteurs sont pleins.
- Une écriture refusée ne change jamais rien. Les écritures ne font pas partie du contrat.

## Le contrat

- `docs/schemas/api_contract.json` liste chaque point d'accès en lecture avec ses clés et types dans chaque édition, et les codes d'erreur. Les routes lisibles mais non figées (flux, texte, exports d'autres outils) sont listées sous `unfrozen` dans le même fichier, chacune avec sa raison ; `/api/data`, qui donne les exécutions, les dépôts et le quota, est figée. Ses clés descendent jusqu'aux éléments des listes : une liste écrite `[{...}]` dans le fichier décrit ses éléments (les trois premiers sont vérifiés), de sorte que les exécutions, les dépôts et le quota de `/api/data`, les alertes de `/api/alerts` et `/api/auth/me` ne peuvent pas changer sans que la vérification échoue.
- `python tools/check_api_contract.py` vérifie un moniteur en marche (`--lite`, `--url`, `--token-file`) et affiche `CONTRACT=PASS` ou `CONTRACT=FAIL` ; lancez-le après chaque mise à jour du moniteur ou de votre client.

## API de lecture v1 (automatique par défaut)

- Réglez `api.v1_enabled` (Réglages, Avancé, API de lecture v1) : `auto` (par défaut) répond quand le moniteur tourne comme service (un compte du mode équipe, l'image Docker, l'unité systemd) et reste fermée pour une personne sur un seul ordinateur ; `on` toujours ; `off` jamais (les anciens true et false valent on et off). Quand elle répond, chaque route de lecture est aussi servie sous `/api/v1/` (par exemple `/api/v1/alerts`) : la même réponse et les mêmes rôles, plus l'en-tête `X-API-Version: 1`. Tant qu'elle est fermée, dans l'édition lite et pour tout autre numéro de version, le préfixe répond 404.
- `/api/v1/me` : qui interroge : `mode` (`individual` ou `team`), `authenticated`, `user`, et le `role` et les `accounts` de la session d'équipe (null sans elle), ce que la session peut faire (`capabilities` : `read`, `write`, `admin` et `v1_write`, toujours faux car le préfixe est en lecture seule), les `limits` des listes, la version du moniteur et la version du contrat (`contract`, `1.0` : il grandit à chaque clé ajoutée et n'en perd jamais).
- `/api/v1/repos` : les dépôts que surveille le moniteur, une ligne chacun (`repo`, `ecosystem`, `state`, `risk`, `runs_24h`, `failures_24h`, `red_workflows`, `stuck_runs`, `alerts`, `last_run_at`). Filtres `state`, `ecosystem` et `q` ; `limit` (par défaut `api.default_limit`, au plus `api.max_limit`) ; `cursor` (le `next_cursor` de la page précédente, signé et valable `api.cursor_ttl_seconds`) ; `fields=a,b` ou `profile=compact` pour des lignes plus courtes. La réponse est compressée en gzip quand le client l'accepte.
- `/api/v1/openapi.json` : la description OpenAPI 3 de toute l'API de lecture figée, construite depuis le contrat (`docs/schemas/api_contract.json`) et jamais écrite à la main : chaque route figée avec les clés et les types qu'elle promet, `x-lite` (ce que répond l'édition lite) et `x-local-only`. Les routes que le contrat ne fige pas sont expérimentales : elles répondent 404 sous `/api/v1/` et ne sont pas dans le document, sauf si `api.experimental_routes` est activé (elles y figurent alors avec `x-experimental`). Les anciennes routes sous `/api/` ne changent jamais. Téléchargez-le avec `python bin/monitor_cli.py api openapi`.
- Un guide pas à pas pour qui écrit un client, avec les commandes dans l'ordre et les erreurs : [API_V1_fra.md](API_V1_fra.md).
- `python tools/api_contract_suite.py` est la suite de contrat pour les clients externes (seulement la bibliothèque standard, seulement en lecture) : donnez-lui l'adresse d'un serveur (`--url`) et un jeton de lecture (`--token-file`) ; elle prend le document que sert le serveur comme description de ce qu'il faut vérifier : la forme de chaque route sans paramètre, l'en-tête `X-API-Version`, l'enveloppe d'erreur et ses codes stables, les pages et leurs curseurs, `fields` et `profile=compact`, gzip et que rien ne peut être écrit sous le préfixe. Elle affiche une ligne par vérification et `API_CONTRACT=PASS` ou `API_CONTRACT=FAIL` (`--json` pour un document) ; le code de sortie est 0, 1 ou 2 (rien ne répond). `python bin/monitor_cli.py api contract-check` la lance contre le moniteur de la ligne de commande.
- Les trois mêmes choses sont des outils du serveur MCP (`python bin/mcp_server.py`, en lecture seule, sans option) : `api_me` (qui le moniteur pense être le client), `api_openapi` (le document, ou une route avec `path`) et `api_contract_check` (la suite de contrat, réponse `{ok, checks, failed, rows}`). HTTP, la ligne de commande (`api me`, `api openapi`, `api contract-check`) et MCP donnent le même document ; un test les compare. Tant que le préfixe est fermé, les outils le disent en une ligne.
- Les deux routes propres répondent une erreur sous la forme `{"error": "bad_request", "code": "api.bad_cursor", "message": "..."}` : `error` et `code` sont stables, `message` suit la langue de `?lang=`. Codes : api.bad_cursor, api.bad_limit, api.unknown_field, api.bad_profile, api.server_error. Tout est en lecture seule : il n'y a aucune écriture sous `/api/v1/`. La forme est figée dans la section `v1_endpoints` du contrat et se vérifie avec `python tools/check_api_contract.py --v1` sur un moniteur dont `api.v1_enabled` est activé.

### Exemples avec curl

Le jeton est le jeton d'accès du mode réseau (ou utilisez une session du mode équipe) ; sans mode réseau, aucun jeton n'est nécessaire depuis le même ordinateur. Un client suit `next_cursor` jusqu'à ce qu'il vaille `null` et lit d'abord `/api/v1/me` pour connaître la version du contrat et ce que la session peut faire.

```
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/me
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?state=bad&limit=20&profile=compact"
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/openapi.json -o openapi.json
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=50&cursor=THE_NEXT_CURSOR"
```

## Flux

- `GET /api/ai/stream` (les alertes) et `GET /api/live-events/stream` (les événements du webhook, `live.sse.enabled`) sont des événements envoyés par le serveur, en lecture seule et éteints par défaut ; voir [AI_ALERTS_fra.md](AI_ALERTS_fra.md) et [WEBHOOK_fra.md](WEBHOOK_fra.md).
- `POST /api/chatops/slack` et `POST /api/chatops/discord` reçoivent les commandes en lecture seule d'un chat (désactivées par défaut, `chatops.enabled`). Elles n'utilisent pas le jeton d'accès : la preuve est la signature de la plateforme, et une requête sans signature valide est refusée avant que rien ne soit lu. Voir [CHATOPS_fra.md](CHATOPS_fra.md).

## Autres routes de la page

Ces routes servent la page et les outils de cet ordinateur. Elles ne font pas partie du contrat figé et peuvent changer d'une version à l'autre. POST modifie quelque chose ; « cet ordinateur » signifie que seul l'ordinateur qui exécute le moniteur peut l'utiliser.

| Route | Ce qu'elle fait |
| --- | --- |
| `/api/about` | Le panneau À propos : versions, liens, fichiers, santé, crédits et l'avis d'une mise à jour ; aucun secret. |
| `/api/act/plan` | POST, cet ordinateur. Prépare ce que ferait une exécution locale avec `act` ; rien ne s'exécute encore. |
| `/api/act/confirm` | POST, cet ordinateur. Exécute un workflow sur cet ordinateur avec `act` après son plan ; l'exécution est consignée. |
| `/api/act/status` | L'état de l'exécution locale en cours. |
| `/api/act/stop` | POST, cet ordinateur. Arrête l'exécution locale. |
| `/api/advanced` | L'état des fonctions que l'on active par choix : le réseau, le coffre du jeton GitHub, les actions sur GitHub, l'exécution locale et le mode démo ; jamais un jeton. |
| `/api/ai/actions` | L'état des actions de l'IA (verrouillées ou non), leur journal, les propositions en attente (`proposals`) et l'état de l'IA. |
| `/api/ai/actions/confirm` | POST, cet ordinateur. Exécute une action proposée par l'IA, après votre confirmation ; consignée. |
| `/api/ai/actions/review` | POST, cet ordinateur. Approuve ou rejette une proposition de l'IA (`id`, `decision`) ; consigné. Rien n'est exécuté. |
| `/api/ai/actions/unlock` | POST, cet ordinateur. Déverrouille les actions de l'IA pour une durée limitée ; consigné. |
| `/api/ai/budget` | Les appels et le coût estimé d'aujourd'hui pour chaque modèle d'IA, les limites et les dernières pannes ; n'interroge aucun fournisseur. |
| `/api/ai/test` | POST, cet ordinateur. Teste la connexion de l'IA configurée ; ne change rien. |
| `/api/alerts/unmute` | POST. Lève le silence d'une alerte ; consigné. |
| `/api/analytics` | Le résumé de l'analyse des exécutions : durées, file d'attente, étapes, tests instables et exécutions plus lentes, ainsi que l'estimation du temps gagné quand elle est activée. |
| `/api/discovery` | Ce qu'a trouvé la découverte : l'encadré avec le compte et les dépôts affichés et masqués, les derniers événements, les groupes suggérés, ses réglages, les forks et les organisations. |
| `/api/discovery/group` | POST. Ajoute un groupe suggéré au fichier des écosystèmes, en gardant une copie du fichier. |
| `/api/gh-action/plan` | POST, cet ordinateur. Prépare ce qui serait envoyé à GitHub (une relance, une annulation, un dispatch ou une fusion) ; rien n'est encore envoyé. |
| `/api/gh-action/confirm` | POST, cet ordinateur. Envoie à GitHub ce que disait le plan, après votre confirmation ; consigné. Si GitHub refuse, la réponse porte `reason` : forbidden, not_found, method, conflict ou invalid. |
| `/api/github-token` | Cet ordinateur seulement. L'état du coffre du jeton GitHub (le moteur et s'il y en a un d'enregistré) ; jamais sa valeur. |
| `/api/help/search` | Cherche un mot dans les sujets d'aide et renvoie ceux qui correspondent. |
| `/api/help/topic` | Le texte d'un sujet d'aide (`id=`) dans la langue de la page. |
| `/api/help/topics` | La liste des sujets d'aide avec leurs titres. |
| `/api/hot-only` | POST, cet ordinateur. L'interrupteur « seulement le chaud » de la page ; ne change aucun état enregistré. |
| `/api/mirror` | L'état du miroir des dépôts (désactivé par défaut). |
| `/api/mode` | GET : le mode de travail, l'estimation de chaque mode et le temps restant. POST, cet ordinateur : change le mode. |
| `/api/notify/test` | POST. Envoie un message d'essai à un canal de notification ; ne change rien. |
| `/api/quota-pool/status` | Cet ordinateur seulement. Le quota de chaque source de lectures et ce qui manque à la GitHub App ; jamais une clé ni un jeton. |
| `/api/refresh-repos` | POST, cet ordinateur. Rafraîchit seulement les dépôts indiqués et réécrit le fichier des rouges (utilisé par `finalize --execute`). |
| `/api/screens/logo` | GET : le logo de l'organisation en image. POST : en enregistre un nouveau (1 Mo au plus, vérifié par son vrai type). |
| `/api/screens/logo/remove` | POST. Retire le logo de l'organisation ; consigné. |
| `/api/sentinel/ai` | POST. Demande à l'IA d'expliquer une alerte ou un build ; la requête est petite et la question est d'abord nettoyée des secrets. N'existe pas tant que l'IA est désactivée. |
| `/api/sentinel/historial` | Hier contre aujourd'hui : les rouges et les signatures en attente qui apparaissent ou disparaissent. |
| `/api/sentinel/parte/save` | POST. Enregistre une copie du rapport quotidien dans le dossier d'audit ; un GET n'écrit jamais. |
| `/api/sentinel/security` | Ce que GitHub dit d'ouvert ou de manquant en sécurité (la sentinelle Sécurité ; désactivée par défaut ; lecture seule). |
| `/api/session-token` | Un jeton à usage unique pour le prochain changement d'un réglage ; la page le demande juste avant d'écrire. |
| `/api/statusbar` | Ce que montre la barre en bas de la page : édition, adresse, compte et sentinelles ; aucun secret et aucun appel à GitHub. |
| `/api/welcome` | GET : si le guide du premier démarrage est terminé. POST, cet ordinateur : le marque comme terminé ou non. |
