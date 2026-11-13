<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CONSOLE_TOOLS.md) | [🇪🇸 Español](CONSOLE_TOOLS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](CONSOLE_TOOLS_ita.md) | [🇩🇪 Deutsch](CONSOLE_TOOLS_deu.md) | [🇨🇳 简体中文](CONSOLE_TOOLS_zho.md) | [🇯🇵 日本語](CONSOLE_TOOLS_jpn.md) | [🇵🇹 Português](CONSOLE_TOOLS_por.md)

# Outils console : linter de workflows et vue console

Deux outils en ligne de commande, optionnels. Le moniteur lui-même n'a besoin d'aucun paquet ; la vue console utilise Rich quand vous la demandez.

## Le linter de workflows : `lint_workflows.py`

- `py -3 lint_workflows.py [CHEMIN ...] [--json] [--fail-on info|warn|bad]` contrôle `.github/workflows/*.yml` avant le push. Sans chemin, il regarde le dossier courant. Il ouvre seulement des fichiers.
- Règles (chacune peut être désactivée et recevoir une autre gravité dans l'onglet Réglages, sous-onglet Linter de workflows) : `unpinned_uses` (une action non épinglée sur un SHA de commit complet), `permissions` (pas de bloc `permissions:`, ou `write-all`), `secrets_in_clear` (ce qui ressemble à un jeton ou une clé écrit dans le fichier), `injection` (texte d'un tiers collé dans un script `run:`) et `pr_target` (`pull_request_target` avec récupération du code de la pull request).
- Le code de sortie est 1 quand un constat atteint `--fail-on` (par défaut `bad`) : il peut donc servir de hook avant push. Quand le moniteur voit vos clones, il ajoute aussi une ligne au rapport quotidien.
- Une valeur qui ressemble à un secret est classée sans jamais être affichée ni enregistrée : un format de jeton connu ou une longue chaîne à forte entropie est grave (`bad`), un remplissage lisible comme `placeholder`, `dummy`, `changeme` ou `ci` n'est qu'une information, tout le reste est un avertissement, et `${{ secrets.X }}`, `${X}` ou une valeur vide n'est pas un constat. Pour taire un constat, écrivez un commentaire sur sa ligne ou la précédente : `# monitor-lint: ignore secrets_in_clear car c'est un remplissage pour docker compose config` (un nom de règle ou `all`) ; ou listez des motifs `dépôt:fichier:règle`, avec `*`, dans le réglage `lint.ignore`.


## La vue console : `tui.py`

- `pip install rich`, puis `py -3 tui.py [--port 8765] [--refresh 5] [--once] [--theme dark|light]`. Elle dessine une grille en direct de ce qui tourne, des workflows rouges, de la file de signature et du rapport, lus sur le moniteur en marche à `127.0.0.1` (aucun quota GitHub).
- Elle est en lecture seule : aucune touche ne relance, ne ferme ni n'écrit rien. Sans Rich, elle indique comment l'installer et sort avec le code 3 ; le moniteur et ses tests n'ont jamais besoin de Rich.
- L'application interactive de terminal `tui_textual.py` (`pip install textual` ; ajoutez `--lite` pour l'édition lite) modifie dans l'onglet Réglages les réglages simples des groupes qu'elle liste, les **listes** (éléments séparés par des virgules : `a, b, c`) et les **tables de nombres** (`name=3, other=5`) ; le serveur revérifie chaque valeur, et les options de sécurité ne se changent que dans la page.
