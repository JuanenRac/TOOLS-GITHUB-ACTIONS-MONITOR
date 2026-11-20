<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](FIRST_STEPS.md) | [🇪🇸 Español](FIRST_STEPS_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](FIRST_STEPS_ita.md) | [🇩🇪 Deutsch](FIRST_STEPS_deu.md) | [🇨🇳 简体中文](FIRST_STEPS_zho.md) | [🇯🇵 日本語](FIRST_STEPS_jpn.md) | [🇵🇹 Português](FIRST_STEPS_por.md)

# Vos cinq premières minutes

**1. Installer le nécessaire.** Python 3.11 ou plus récent et le GitHub CLI (`gh`). Puis se connecter une fois : `gh auth login`. Le moniteur ne stocke jamais de jeton : il le demande à `gh` (sauf si vous activez le jeton optionnel du moniteur dans Réglages > Avancé).

**2. Tout vérifier d'une commande.** `python bin/actions_monitor.py --doctor` indique, pour chaque problème, la commande exacte qui le corrige. Envie de regarder d'abord ? `python bin/actions_monitor.py --demo` ouvre la page avec des données inventées : sans `gh`, sans session, sans réseau.

**3. Le démarrer.** Double-clic sur `MONITOR_LITE_GITHUB_ACTIONS` pour l'édition simple (port 8766) ou `MONITOR_GITHUB_ACTIONS` pour la complète avec sentinelle (port 8765). La fenêtre de console indique l'édition, dans son titre et sa première ligne.

**4. Suivre les trois étapes de l'accueil.** La première fois, la page explique ce qu'elle fait, montre ce qu'elle a trouvé dans votre compte et renvoie aux réglages essentiels. Rien n'est caché par défaut : les dépôts qu'aucun groupe ne réclame apparaissent comme *Non classés*.

**5. Savoir où est l'aide.** Le bouton rond **?** (ou la touche `?`) ouvre l'Aide ; le bouton **i** ouvre À propos, avec votre version, vos fichiers et un bouton qui copie les informations pour le support (sans secret). En console : `--help-topics`, `--help-search MOTS`, `--about`.

**6. Enregistrer ou imprimer un rapport.** Les deux boutons en haut de la page enregistrent le rapport de l'onglet ouvert (TXT, PDF et, si vous le souhaitez, JSON, chacun par la fenêtre **Enregistrer sous** de votre navigateur) ou l'impriment comme une page propre ([Sorties pour d'autres outils](OUTPUTS.md)).

**Bon à savoir.** Si vous avez une offre avec des dépôts privés, choisissez-la dans Réglages > Essentiel pour voir vos quotas ([Quotas et offres](QUOTAS_fra.md)). La sentinelle est expliquée dans [La sentinelle](SENTINEL_fra.md). L'outil ne fait que lire GitHub ; il n'écrit qu'après votre confirmation.

## Lire confortablement

- **Densité** (`display.density`, ou `?density=dense` pour une fenêtre) : `dense` resserre les espaces et la police de chaque onglet.
- **Moins de mouvement** (`display.reduce_motion`) : `auto` suit le réglage de votre système, `on` arrête toute animation et transition. L'état d'un workflow est toujours écrit en mots et dessiné aussi avec une forme, jamais seulement en couleur.
- **Couleurs pour le daltonisme** (`display.palette`, ou `?palette=colorblind`) : bleu, vermillon, jaune et un bleu plus clair, un jeu pour le mode sombre et un autre pour le clair. La barrière de contraste (`python tools/check_contrast.py`) vérifie chaque thème et simule les trois formes de daltonisme.
- **Pas de saut pendant la lecture** (`display.live_throttle_s`) : tant que le pointeur ou le focus est dans l'onglet que vous lisez, l'actualisation périodique attend ; une actualisation que vous demandez s'applique aussitôt.
- **Nouveautés** (`display.whats_new`) : après une mise à jour, un avis propose les entrées de l'historique des changements des versions sautées ; rouvrez-le depuis la palette. `GET /api/whats-new?since=2.1.5` répond avec les entrées (lecture seule).
- **Glossaire et limites** : ouvrez-le depuis la palette. `GET /api/glossary` répond avec les chiffres écrits avec vos vrais paramètres, les attaques que cherchent les règles, les limites de l'analyse et quelques endroits pour en savoir plus. Avec `report_export.limits` activé, les rapports enregistrés et imprimés se terminent par les limites.
- **Le filtre de l'en-tête** couvre les onglets Maintenant, Alertes, Graphiques, ceux de la Sentinelle (Sentinelle, CI, Collaboration, Sécurité, Livraison, Chaîne d'approvisionnement), Dépôts et Historique ; les autres (Tendance de la Sentinelle, Équipe, Flotte, Rapports, Leçons, Mises à jour et Réglages) sont toujours globaux. Une note sous le filtre le dit.
