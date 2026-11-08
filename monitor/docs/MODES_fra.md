<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](MODES.md) | [🇪🇸 Español](MODES_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](MODES_ita.md) | [🇩🇪 Deutsch](MODES_deu.md) | [🇨🇳 简体中文](MODES_zho.md) | [🇯🇵 日本語](MODES_jpn.md) | [🇵🇹 Português](MODES_por.md)

# Modes de travail : normal, rapide et turbo

Quand vous voulez surveiller quelque chose de plus près pendant un moment (une heure, par exemple), vous pouvez passer le moniteur dans un mode plus rapide même s'il épuise plus vite le quota de l'API. Le sélecteur à l'icône de jauge est dans l'en-tête ; en console, utilisez `--mode fast` ou `--mode turbo` avec `--mode-minutes 60`.

| Mode | Ce qui change | Valeurs par défaut |
|---|---|---|
| **normal** | rien : votre propre configuration | les vôtres |
| **fast** (rapide) | actualisation, actualisation à froid, runs par dépôt, fenêtre chaude | 30 s, 300 s, 30 runs, 6 h |
| **turbo** | idem, en plus | 15 s, 90 s, 50 runs, 12 h |

Les préréglages sont le bloc `modes` de `actions_monitor.json` (`modes.fast`, `modes.turbo`, `modes.default_minutes`, `modes.start`) ; modifiez-les à votre goût. Un préréglage ne rend jamais une valeur plus lente ou plus petite que la vôtre, et rien ne descend sous 10 secondes, pour rester loin des limites secondaires de GitHub (après l'une d'elles, le moniteur attend au moins une minute puis davantage).

**Avant de démarrer**, la page montre les appels par heure du mode dans le pire des cas, ce que le cache économise d'habitude (une lecture conditionnelle qui répond `304` ne coûte pas de quota primaire) et combien de temps durerait le quota restant. **Il revient seul en normal** à la fin du temps (l'en-tête fait le compte à rebours) et quand le quota restant passe sous `min_rate_remaining` ; un avis dit pourquoi et la console l'affiche. **Sans connexion GitHub ne donne que 60 appels par heure**, donc rapide et turbo sont désactivés avec la raison (lancez `gh auth login`).

Changer de mode est un réglage local : il demande le jeton à usage unique de la page comme tout changement, ne vit qu'en mémoire (un redémarrage revient en normal sauf si vous écrivez `modes.start` vous-même) et n'envoie rien nulle part. Il fonctionne dans les deux éditions ; la sentinelle de l'édition complète garde ses propres intervalles et son propre budget d'appels (`sentinel.budget_per_hour`), décrits dans [La sentinelle](SENTINEL_fra.md). La bannière de la console et les lignes d'état indiquent le mode actif.
