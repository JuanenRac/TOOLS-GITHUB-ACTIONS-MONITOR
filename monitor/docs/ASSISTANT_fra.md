<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# L'assistant

Des questions fixes à l'IA que vous avez déjà configurée, répondues avec les données du moniteur, en lecture seule. Désactivé par défaut.

## L'activer

1. Configurez un fournisseur d'IA (`ai.provider` ; voir [AI_CONNECTION_fra.md](AI_CONNECTION_fra.md)).
2. Dans les Réglages, IA, activez `ai.assistant.enabled`. Le panneau apparaît dans l'onglet Alertes. Il n'existe pas dans l'édition Lite.
3. Posez une question ; la réponse montre ses sources, ce qui a été envoyé et les appels du jour.

## Les cinq questions

- `explain_alert` : pourquoi une alerte est ouverte (il faut l'alerte).
- `summarize_week` : la situation du compte.
- `why_slow` : pourquoi la CI d'un dépôt est lente ou bloquée (il faut le dépôt).
- `explain_repo` : la situation d'un dépôt, ses exécutions et ses alertes ouvertes.
- `prioritize` : les alertes ouvertes, l'état et le score mis en ordre, avec leurs identifiants.

Il n'y a pas de chat libre.

## Ce qu'il lit

Quatre outils, une liste fermée que `ai.assistant.tools` peut réduire : `status`, `alerts`, `runs` et `score`. Au plus `ai.assistant.max_tool_calls` lectures par question et `ai.assistant.max_context` de texte envoyé. Avec `ai.similar.enabled`, « expliquer cette alerte » liste aussi des alertes semblables, trouvées en comparant des mots, sans modèle.

## Ce qu'il ne fait jamais

Il n'écrit rien et ne touche à rien sur GitHub. Ce qu'un dépôt a écrit (un titre, le nom d'un workflow) est coupé, nettoyé des secrets et des mots que vous avez cachés, et remis comme donnée entre des marques, jamais comme instruction. Chaque question dépense l'unique budget quotidien de l'IA (`ai.daily_limit`). Avec `ai.airgapped`, seul un modèle de cet ordinateur ou de votre réseau privé est utilisé.

## Le vérifier

`GET /api/assistant` dit ce qu'il est et ses limites ; `POST /api/assistant/ask` prend `action` et, selon le cas, `alert` ou `repo`. Les deux répondent 404 tant qu'il est désactivé. La question figure dans le journal des actions (jamais son texte) ; avec `ai.prompt_log.enabled`, les prompts nettoyés sont gardés dans un journal local que vous pouvez voir et vider dans les Réglages.

## Propositions approuvées par des personnes

Chaque commande proposée par une IA (`ai.actions.enabled`) est marquée comme venant d'une IA, porte l'empreinte (SHA-256) de ce qui s'exécuterait et est conservée jusqu'à expiration, même après un redémarrage. Elle ne s'exécute jamais seule. L'approuver est une décision de personnes : à deux utilisateurs ou plus il faut deux personnes (celle qui a interrogé l'IA en compte pour une et ne peut approuver la sienne) ; seul, vous saisissez les huit premiers caractères de l'empreinte. Une personne suffit pour rejeter. Avec `ai.assistant.can_propose` (désactivé), une réponse de la discussion peut aussi devenir une proposition. L'onglet Alertes les montre.

## Discussion libre

`ai.chat.enabled` (désactivé) ajoute une discussion dans l'onglet Alertes. L'IA ne peut que lire, avec les quatre outils ci-dessus ; elle les demande et le moniteur décide. Même budget, même nettoyage, mêmes marques ; chaque réponse liste ce qui a été lu. Aucun outil n'écrit.

## Alertes similaires avec un modèle local

Avec `ai.rag.enabled` (désactivé) et `ai.rag.model`, « expliquer cette alerte » classe selon les embeddings d'un modèle tournant sur cet ordinateur (API d'Ollama ; adresse locale uniquement). L'index garde des vecteurs et des empreintes, jamais le texte, jusqu'à `ai.rag.max_mb` ; supprimer `ai_rag_index.json` ne fait rien perdre. Sans modèle, la comparaison de mots est utilisée. Testé seulement avec un serveur factice.

## Rapport d'un dépôt

Avec `ui.copy_report.enabled`, l'onglet Alertes copie le rapport d'un dépôt en Markdown, ou un brouillon de triage, à coller à la main. Sans IA, sans requête à GitHub, rien n'est publié.

Routes : `GET /api/assistant/extras`, `GET /api/assistant/repo-report?repo=`, `POST /api/assistant/chat`. Pour les clients MCP, les résumés sont aussi des ressources : `resources/list`, `resources/read`, `monitor://briefs/index`, `monitor://briefs/<tab>`.
