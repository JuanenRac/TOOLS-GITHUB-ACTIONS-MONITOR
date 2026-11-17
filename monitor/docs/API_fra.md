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

- `docs/schemas/api_contract.json` liste chaque point d'accès en lecture avec ses clés et types dans chaque édition, et les codes d'erreur. Les routes lisibles mais non figées (flux, texte, exports d'autres outils) sont listées sous `unfrozen` dans le même fichier, chacune avec sa raison ; `/api/data`, qui donne les exécutions, les dépôts et le quota, est figée.
- `python tools/check_api_contract.py` vérifie un moniteur en marche (`--lite`, `--url`, `--token-file`) et affiche `CONTRACT=PASS` ou `CONTRACT=FAIL` ; lancez-le après chaque mise à jour du moniteur ou de votre client.

## API de lecture v1 (désactivée par défaut)

- Activez `api.v1_enabled` (Réglages, Avancé, API de lecture v1). Chaque route de lecture est alors aussi servie sous `/api/v1/` (par exemple `/api/v1/alerts`) : la même réponse et les mêmes rôles, plus l'en-tête `X-API-Version: 1`. Tant qu'elle est désactivée, dans l'édition lite et pour tout autre numéro de version, le préfixe répond 404.
- `/api/v1/me` : qui interroge : `mode` (`individual` ou `team`), `authenticated`, `user`, et le `role` et les `accounts` de la session d'équipe (null sans elle), les `limits` des listes et la version.
- `/api/v1/repos` : les dépôts que surveille le moniteur, une ligne chacun (`repo`, `ecosystem`, `state`, `risk`, `runs_24h`, `failures_24h`, `red_workflows`, `stuck_runs`, `alerts`, `last_run_at`). Filtres `state`, `ecosystem` et `q` ; `limit` (par défaut `api.default_limit`, au plus `api.max_limit`) ; `cursor` (le `next_cursor` de la page précédente, signé et valable `api.cursor_ttl_seconds`) ; `fields=a,b` ou `profile=compact` pour des lignes plus courtes. La réponse est compressée en gzip quand le client l'accepte.
- `/api/v1/openapi.json` : une description OpenAPI 3 légère de ces deux routes.
- Les deux routes propres répondent une erreur sous la forme `{"error": "bad_request", "code": "api.bad_cursor", "message": "..."}` : `error` et `code` sont stables, `message` suit la langue de `?lang=`. Codes : api.bad_cursor, api.bad_limit, api.unknown_field, api.bad_profile. Tout est en lecture seule : il n'y a aucune écriture sous `/api/v1/`. La forme est figée dans la section `v1_endpoints` du contrat et se vérifie avec `python tools/check_api_contract.py --v1` sur un moniteur dont `api.v1_enabled` est activé.

## Flux

- `GET /api/ai/stream` (les alertes) et `GET /api/live-events/stream` (les événements du webhook, `live.sse.enabled`) sont des événements envoyés par le serveur, en lecture seule et éteints par défaut ; voir [AI_ALERTS_fra.md](AI_ALERTS_fra.md) et [WEBHOOK_fra.md](WEBHOOK_fra.md).
- `POST /api/chatops/slack` et `POST /api/chatops/discord` reçoivent les commandes en lecture seule d'un chat (désactivées par défaut, `chatops.enabled`). Elles n'utilisent pas le jeton d'accès : la preuve est la signature de la plateforme, et une requête sans signature valide est refusée avant que rien ne soit lu. Voir [CHATOPS_fra.md](CHATOPS_fra.md).
