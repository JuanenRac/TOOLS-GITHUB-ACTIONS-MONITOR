<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Alertes pour les IA

Un workflow rouge ne sert à rien si personne de ceux qui travaillent sur le dépôt ne l'apprend. Le moniteur écrit un petit flux que n'importe quel outil d'IA (Codex, Gemini CLI, Copilot) ou script peut lire.

## Ce qu'il écrit (local, lecture seule, sans réseau)
- `ai_alerts.jsonl` : une ligne par évènement (ouvert, acquitté, résolu) avec identifiant stable, gravité, dépôt, workflow, conclusion, depuis quand, série, lien, une cause probable (**réelle** ou **passagère**), une action suggérée et l'état.
- `ALERTS_BRIEF.md` : réécrit à chaque cycle et court (`ai_alerts.brief_max_bytes`, 2 Ko par défaut). Les alertes réelles viennent d'abord.
- Les causes passagères (502/503/504, délais dépassés, limites de débit, échecs de téléchargement, une exécution qui n'a pas démarré) se distinguent des vrais échecs par des règles modifiables dans `ai_alerts.transient_patterns`. Une alerte se résout seule quand le workflow repasse au vert, et vous pouvez l'acquitter (`ack`), ce qui ne change que cet état local.
- Tout passe d'abord par un nettoyeur : jetons, clés, adresses e-mail, adresses IP et votre dossier personnel n'atteignent jamais les fichiers, les points d'accès ni le hook.
- Le dossier est `ai_alerts.folder` (par défaut à côté du moniteur) ; choisissez-en un que lisent vos sessions IA. `ci_red.json` porte un `ai_hint` optionnel (classe, cause, action) dans chaque workflow rouge.

## Comment une IA le lit
- Mettez ceci dans les instructions de votre projet ou skill : *« Au début, lis ALERTS_BRIEF.md (chemin) et dis quelles alertes réelles sont ouvertes. »*
- Ou interrogez le moniteur en marche : `GET /api/ai/brief` (Markdown, ou `?fmt=json`) et `GET /api/ai/alerts?since=SECONDES`. Mêmes règles que le reste de la page (cet ordinateur ; avec le mode réseau, le jeton d'accès).
- Ou ajoutez le serveur MCP (lecture seule) : `python mcp_server.py`, outils `get_alerts`, `get_red_repos`, `get_run_failure`, `get_quota` ; `--allow-ack` ajoute `ack_alert` (état local seulement). Gemini CLI, Codex et VS Code (Copilot) : ajoutez la même commande comme serveur stdio dans leurs réglages MCP.

## Avertissements qui vous parviennent
- Une NOUVELLE alerte réelle va aux canaux de notification que vous avez déjà configurés (Réglages > Notifications).
- Optionnel, désactivé par défaut : `ai_alerts.hook` envoie en POST la nouvelle alerte réelle (liste fermée de champs nettoyés) à une adresse de cet ordinateur, au plus `max_per_hour` fois par heure, pour qu'un de vos scripts réveille une session IA.
- Rien de cela n'envoie de données à un fournisseur d'IA, n'exécute de commande ni n'écrit sur GitHub.

## Le serveur MCP est local

`mcp_server.py` parle JSON sur l'entrée et la sortie standard avec l'outil d'IA qui le lance : il n'a pas de port réseau et ne doit jamais être placé derrière un port. Un message mal formé reçoit une erreur pour ce message seulement, une ligne de plus de 64 Ko est refusée, et `ack_alert` (seulement avec `--allow-ack`) ne change que l'état local du flux. Le flux peut contenir des noms de dépôts et de courts messages d'erreur de la CI ; tout est nettoyé des jetons, clés, adresses e-mail, adresses IP et du dossier d'une personne avant de sortir.
