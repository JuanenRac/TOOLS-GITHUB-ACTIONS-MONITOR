<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](FIRST_STEPS.md) | [🇪🇸 Español](FIRST_STEPS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](FIRST_STEPS_ita.md) | [🇩🇪 Deutsch](FIRST_STEPS_deu.md) | [🇨🇳 简体中文](FIRST_STEPS_zho.md) | [🇯🇵 日本語](FIRST_STEPS_jpn.md) | [🇵🇹 Português](FIRST_STEPS_por.md)

# Vos cinq premières minutes

**1. Installer le nécessaire.** Python 3.11 ou plus récent et le GitHub CLI (`gh`). Puis se connecter une fois : `gh auth login`. Le moniteur ne stocke jamais de jeton : il le demande à `gh` (sauf si vous activez le jeton optionnel du moniteur dans Réglages > Avancé).

**2. Tout vérifier d'une commande.** `python actions_monitor.py --doctor` indique, pour chaque problème, la commande exacte qui le corrige. Envie de regarder d'abord ? `python actions_monitor.py --demo` ouvre la page avec des données inventées : sans `gh`, sans session, sans réseau.

**3. Le démarrer.** Double-clic sur `MONITOR_LITE_GITHUB_ACTIONS` pour l'édition simple (port 8766) ou `MONITOR_GITHUB_ACTIONS` pour la complète avec sentinelle (port 8765). La fenêtre de console indique l'édition, dans son titre et sa première ligne.

**4. Suivre les trois étapes de l'accueil.** La première fois, la page explique ce qu'elle fait, montre ce qu'elle a trouvé dans votre compte et renvoie aux réglages essentiels. Rien n'est caché par défaut : les dépôts qu'aucun groupe ne réclame apparaissent comme *Non classés*.

**5. Savoir où est l'aide.** Le bouton rond **?** (ou la touche `?`) ouvre l'Aide ; le bouton **i** ouvre À propos, avec votre version, vos fichiers et un bouton qui copie les informations pour le support (sans secret). En console : `--help-topics`, `--help-search MOTS`, `--about`.

**Bon à savoir.** Si vous avez une offre avec des dépôts privés, choisissez-la dans Réglages > Essentiel pour voir vos quotas ([Quotas et offres](QUOTAS_fra.md)). La sentinelle est expliquée dans [La sentinelle](SENTINEL_fra.md). L'outil ne fait que lire GitHub ; il n'écrit qu'après votre confirmation.
