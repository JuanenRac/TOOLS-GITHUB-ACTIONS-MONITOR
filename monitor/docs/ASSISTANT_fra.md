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
