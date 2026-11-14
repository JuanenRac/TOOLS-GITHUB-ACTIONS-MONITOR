Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE

MONITEUR GITHUB ACTIONS + SENTINELLE (version 1.8.0)
====================================================
LEQUEL LANCER ? (un nouvel utilisateur décide en deux minutes)
  COMPLET   MONITOR_GITHUB_ACTIONS.*       la page avec la sentinelle (port 8765) : alertes, file de signature, analytique. Commencez ici si vous avez plusieurs dépôts.
  LITE      MONITOR_LITE_GITHUB_ACTIONS.*  la même page sans sentinelle (port 8766) : ce qui est rouge, bloqué ou en cours. Plus légère ; cohabite avec la complète.
  LOT       BATCH_GITHUB_ACTIONS.*         seulement si vous signez et publiez vos propres builds.
  TERMINAL  python bin/tui_textual.py (ajoutez --lite pour l'édition lite)   l'application interactive de terminal ; bin/tui.py --once affiche un écran.
  VÉRIFIER  python bin/actions_monitor.py --doctor (--json pour les scripts)   dit ce qui manque et la commande exacte pour le corriger.
  ESSAYER   python bin/actions_monitor.py --demo   la page avec des données inventées : sans gh, sans connexion, rien de vous n'est touché.

Prérequis : Python 3.11+ et GitHub CLI (`gh`) connecté (gh auth login). Rien d'autre : le cœur n'a besoin d'aucun paquet (la vue console, bin/tui.py, utilise le paquet optionnel rich).
Étapes rapides pour une première utilisation : QUICKSTART_fr.txt.

DÉMARRAGE  Windows : MONITOR_GITHUB_ACTIONS.bat | Linux : ./MONITOR_GITHUB_ACTIONS.sh | macOS : double-clic sur MONITOR_GITHUB_ACTIONS.command
           (ouvre http://127.0.0.1:<port>, en local uniquement). Sur tout système, on peut aussi lancer :  python3 bin/actions_monitor.py  (Windows : py -3 bin/actions_monitor.py)
LOTS       BATCH_GITHUB_ACTIONS.bat / .sh / .command  (bin/gha_dispatch_all.py : plan, dispatch, status, finalize, hygiene). Facultatif, pour ceux qui signent leurs builds en local.
CE QU'IL NE FAIT JAMAIS   Il n'écoute que sur 127.0.0.1 sauf si vous activez le mode réseau (Réglages > Avancé : une adresse privée, un jeton d'accès pour chaque requête, un avertissement dans la page). Il ne stocke aucun jeton (il le demande à `gh`) sauf si vous activez le jeton optionnel gardé dans le coffre du système. De lui-même il n'écrit rien sur GitHub : seules les commandes de lot `dispatch --go`, `dispatch --real` et `finalize --execute` écrivent sur GitHub (lancer des workflows, créer le brouillon non signé, publier), et seulement quand vous les exécutez.
           Il ne signe RIEN et ne publie RIEN tout seul : signer et publier sont des commandes que VOUS lancez ; le moniteur ne fait que les afficher en texte.
           Pas d'IA dans le chemin critique ; l'explicateur facultatif par IA est désactivé par défaut.

LANGUE     8 langues : en, es, de, fr, it, ja, zh, pt (portugais du Portugal). Démarrage en ANGLAIS : la langue du système ne décide pas. Choisissez-en une autre dans l'onglet RÉGLAGES de la page
           (icône d'engrenage ; le navigateur s'en souvient), ou avec "language" dans actions_monitor.json, ou la variable d'environnement MONITOR_LANG, ou --lang CODE dans les outils en ligne de commande (prioritaire).
           Les lignes lues par les scripts (SKIP, DISPATCHED, READY, FAILED, Summary:, BUILD ONLY...) sont toujours en anglais.
CONFIG     actions_monitor.json (créé à partir de assets/examples/actions_monitor.example.json au premier démarrage). Clés utiles : github_owner (vide = le compte de gh),
           language, ecosystems_file, targets_file, refresh_seconds, cold_refresh_seconds, max_workers, min_rate_remaining, sentinel.*
           ecosystems_file : regroupe les dépôts par préfixe de nom (voir assets/examples/ecosystems.example.json ; "*" = tous les dépôts). targets_file : catalogue des builds pour les
           outils de lot (voir assets/examples/targets.example.json). profiles_file (assets/examples/profiles.example.json) : profils de lot. Les clés commençant par "_" dans ces fichiers sont des métadonnées.
ESPACE DE TRAVAIL  FACULTATIF : un dossier avec des clones locaux de vos dépôts (MONITOR_ROOT, "workspace_root" dans le json, ou un dossier parent contenant un fichier .monitor-root).
           Sans lui, le moniteur démarre en MODE RÉDUIT et le dit : seulement ce que donne l'API GitHub (pas de file de signature locale, pas de rapport d'audit, pas de lecture du CHANGELOG).
           Avec lui, vous avez aussi les releases candidates, la file de signature et les outils de lot. Journaux de signature : "signed_dir" ; fichiers d'audit : "audit_dir".
TESTS      py -3 -I -m unittest discover -s tests   (Linux/macOS : python3 -I -m unittest discover -s tests). Ils n'ont pas besoin du réseau.
PROBLÈMES  "API rate limit" : le quota partagé de gh (5000/heure) est épuisé ; attendez la réinitialisation (gh api rate_limit) et augmentez refresh_seconds / baissez max_workers.
           Le moniteur s'arrête au démarrage si gh ne répond pas. Un fichier de cache corrompu est ignoré ; supprimez sentinel_cache.json pour repartir d'un cache neuf.
           Redémarrez le moniteur après une mise à jour du paquet (un processus en cours garde l'ancien code).

OUTILS     bin/read_report.py [--lang CODE] [--json] [--export-status DOSSIER] [--export-sign-queue FICHIER]  affiche ce que dit le moniteur en cours (local, sans quota GitHub)
           bin/gha_dispatch_all.py [--lang CODE] plan|dispatch|status|finalize|hygiene    lot de builds GitHub Actions (rien n'est compilé sur votre PC)
           bin/release_notes.py REPO [--since ÉTIQUETTE] [--out FICHIER]    brouillon de notes de version à partir des commits (une proposition ; ne publie rien)
           bin/release_candidates.py    projets avec des entrées dans CHANGELOG [Unreleased] et une dernière release ancienne (lecture seule)
ÉVÉNEMENTS La sentinelle écrit une ligne JSON par CHANGEMENT (nouveau rouge, CI rétablie, build bloqué, nouvelles alertes...) dans events_monitor.jsonl. Chaque ligne porte un
           `code` stable (jamais dépendant de la langue), `kind`, `level`, `repo`, `args` et `text` (dans la langue configurée). `tail -F` la suit.
CI ROUGE   Un seul critère : le DERNIER run terminé de chaque workflow sur la branche par défaut. Rouge = failure, timed_out, startup_failure ou action_required.
           cancelled, skipped, neutral et stale ne comptent pas.

HISTORIQUE DES CHANGEMENTS
  Toutes les versions, de la plus récente à la plus ancienne, sont dans CHANGELOG.md (en huit langues dans docs/CHANGELOG_*.md, et dans la page : Aide > Journal des modifications).

AIDE, À PROPOS ET VÉRIFICATIONS (1.6.4)
---------------------------------------
La page a un bouton Aide (? rond) et un bouton À propos (i) ; en console : --help-topics, --help-search, --about et --doctor ; --demo montre la page avec des données inventées. L'édition lite démarre avec sa propre bannière et son titre de fenêtre (LITE, port 8766, sans sentinelle) ; la complète indique COMPLETE, port 8765, sentinelle active. L'avis de nouvelle version peut être désactivé (Réglages > Essentiel).
