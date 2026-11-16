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

- `docs/schemas/api_contract.json` liste chaque point d'accès en lecture avec ses clés et types dans chaque édition, et les codes d'erreur.
- `python tools/check_api_contract.py` vérifie un moniteur en marche (`--lite`, `--url`, `--token-file`) et affiche `CONTRACT=PASS` ou `CONTRACT=FAIL` ; lancez-le après chaque mise à jour du moniteur ou de votre client.

## Flux

- `GET /api/ai/stream` (les alertes) et `GET /api/live-events/stream` (les événements du webhook, `live.sse.enabled`) sont des événements envoyés par le serveur, en lecture seule et éteints par défaut ; voir [AI_ALERTS_fra.md](AI_ALERTS_fra.md) et [WEBHOOK_fra.md](WEBHOOK_fra.md).
