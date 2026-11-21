<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](API_V1.md) | [🇪🇸 Español](API_V1_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](API_V1_ita.md) | [🇩🇪 Deutsch](API_V1_deu.md) | [🇨🇳 简体中文](API_V1_zho.md) | [🇯🇵 日本語](API_V1_jpn.md) | [🇵🇹 Português](API_V1_por.md)

# L'API de lecture v1, pas à pas

Un guide pour qui écrit un client (un script, un écran mural, une application mobile, un outil d'IA) contre l'API de lecture du moniteur. La référence de chaque route est le document OpenAPI que sert le moniteur lui-même ; les règles du contrat (ce qui est figé et ce qui peut grandir) sont dans [API_fra.md](API_fra.md). Voici le chemin à suivre, avec des commandes qu'un test exécute contre un moniteur.

## 1. L'API est-elle ouverte ?

Le préfixe `/api/v1/` répond de lui-même quand le moniteur tourne comme service (un compte du mode équipe, l'image Docker, l'unité systemd) et reste fermé, avec un 404, pour une personne sur un ordinateur. Le réglage `api.v1_enabled` (`auto`, `on`, `off`) en décide. Un client commence par demander qui il est : un `404` signifie là que l'API est fermée, pas que le client est fautif.

## 2. S'identifier

Depuis le même ordinateur et sans mode réseau, aucun jeton n'est nécessaire. En mode réseau, chaque requête porte le jeton d'accès dans l'en-tête `X-Monitor-Access`, lu ici dans un fichier pour qu'il n'apparaisse jamais dans une ligne de commande conservée dans l'historique ; avec le mode équipe, un script se connecte à `POST /api/auth/login`. Un jeton de lecture suffit à un client de cette API : rien ne s'écrit sous le préfixe.

## 3. Les commandes

Dans cet ordre : qui vous êtes et la version du contrat (`/api/v1/me`), la description de chaque route figée (`/api/v1/openapi.json`), les dépôts par pages (filtres `state`, `ecosystem` et `q` ; `limit` ; `fields` ou `profile=compact` pour des lignes plus courtes ; `cursor` est le `next_cursor` de la page précédente, jusqu'à ce qu'il soit `null`), la réponse compressée en gzip et deux routes de l'ancienne API que le préfixe sert aussi avec la même réponse.

```
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/me
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/openapi.json -o openapi.json
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?state=bad&limit=20&profile=compact"
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?fields=repo,state,risk&limit=5"
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=50&cursor=THE_NEXT_CURSOR"
curl -s --compressed -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=100"
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/health
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/alerts
```

## 4. Erreurs

Une erreur des routes propres est un objet JSON à trois clés : `error` et `code` sont stables et destinés aux programmes, `message` suit la langue de `?lang=` et est destiné aux personnes. Les codes sont api.bad_cursor, api.bad_limit, api.unknown_field, api.bad_profile et api.server_error. Toute réponse du préfixe, erreurs comprises, porte l'en-tête `X-API-Version: 1`. Chaque erreur porte aussi `help`, une phrase avec la prochaine étape et le guide à lire, dans la même langue (le champ manque quand un code n'en a pas ; un programme qui l'ignore ne perd rien).

```
curl -s -i -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=0"
```

La réponse, après les en-têtes, est `{"error": "bad_request", "code": "api.bad_limit", "message": "..."}`.

## 5. La même chose depuis la ligne de commande et depuis un outil d'IA

Trois accès donnent les mêmes documents, et un test les compare : HTTP comme ci-dessus, la ligne de commande (`python bin/monitor_cli.py api me`, `api openapi`, `api contract-check` ; ajoutez `--json` pour la réponse en données) et le serveur MCP (`python bin/mcp_server.py`, en lecture seule : les outils `api_me`, `api_openapi` et `api_contract_check`).

## 6. Vérifier un serveur avant de s'y fier

`python tools/api_contract_suite.py --url URL --token-file token.txt` prend le document que sert le serveur comme description de ce qu'il faut vérifier et affiche une ligne par vérification puis `API_CONTRACT=PASS` ou `API_CONTRACT=FAIL`. `python tools/check_api_contract.py --v1` exécute la même suite et compare aussi les réponses au contrat figé. Lancez l'un ou l'autre après chaque mise à jour du moniteur ou de votre client ; la CI du moniteur exécute la suite contre une démo en mode service.
