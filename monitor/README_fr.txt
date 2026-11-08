Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE

MONITEUR GITHUB ACTIONS + SENTINELLE (version 1.5.2)
====================================================
Prérequis : Python 3.11+ et GitHub CLI (`gh`) connecté (gh auth login). Rien d'autre : uniquement la bibliothèque standard de Python.
Étapes rapides pour une première utilisation : QUICKSTART_fr.txt.

DÉMARRAGE  Windows : MONITOR_GITHUB_ACTIONS.bat | Linux : ./MONITOR_GITHUB_ACTIONS.sh | macOS : double-clic sur MONITOR_GITHUB_ACTIONS.command
           (ouvre http://127.0.0.1:<port>, en local uniquement). Sur tout système, on peut aussi lancer :  python3 actions_monitor.py  (Windows : py -3 actions_monitor.py)
LOTS       BATCH_GITHUB_ACTIONS.bat / .sh / .command  (gha_dispatch_all.py : plan, dispatch, status, finalize, hygiene). Facultatif, pour ceux qui signent leurs builds en local.
CE QU'IL NE FAIT JAMAIS   Il n'écoute que sur 127.0.0.1 (ne le liez jamais à 0.0.0.0 : il n'a pas d'authentification). Il ne stocke aucun jeton (il le demande à `gh`). De lui-même il n'écrit rien sur GitHub : seules les commandes de lot `dispatch --go`, `dispatch --real` et `finalize --execute` écrivent sur GitHub (lancer des workflows, créer le brouillon non signé, publier), et seulement quand vous les exécutez.
           Il ne signe RIEN et ne publie RIEN tout seul : signer et publier sont des commandes que VOUS lancez ; le moniteur ne fait que les afficher en texte.
           Pas d'IA dans le chemin critique ; l'explicateur facultatif par IA est désactivé par défaut.

LANGUE     8 langues : en, es, de, fr, it, ja, zh, pt (portugais du Portugal). Démarrage en ANGLAIS : la langue du système ne décide pas. Choisissez-en une autre dans l'onglet RÉGLAGES de la page
           (icône d'engrenage ; le navigateur s'en souvient), ou avec "language" dans actions_monitor.json, ou la variable d'environnement MONITOR_LANG, ou --lang CODE dans les outils en ligne de commande (prioritaire).
           Les lignes lues par les scripts (SKIP, DISPATCHED, READY, FAILED, Summary:, BUILD ONLY...) sont toujours en anglais.
CONFIG     actions_monitor.json (créé à partir de actions_monitor.example.json au premier démarrage). Clés utiles : github_owner (vide = le compte de gh),
           language, ecosystems_file, targets_file, refresh_seconds, cold_refresh_seconds, max_workers, min_rate_remaining, sentinel.*
           ecosystems_file : regroupe les dépôts par préfixe de nom (voir ecosystems.example.json ; "*" = tous les dépôts). targets_file : catalogue des builds pour les
           outils de lot (voir targets.example.json). profiles_file (profiles.example.json) : profils de lot. Les clés commençant par "_" dans ces fichiers sont des métadonnées.
ESPACE DE TRAVAIL  FACULTATIF : un dossier avec des clones locaux de vos dépôts (MONITOR_ROOT, "workspace_root" dans le json, ou un dossier parent contenant un fichier .monitor-root).
           Sans lui, le moniteur démarre en MODE RÉDUIT et le dit : seulement ce que donne l'API GitHub (pas de file de signature locale, pas de rapport d'audit, pas de lecture du CHANGELOG).
           Avec lui, vous avez aussi les releases candidates, la file de signature et les outils de lot. Journaux de signature : "signed_dir" ; fichiers d'audit : "audit_dir".
TESTS      py -3 -I -m unittest discover -s tests   (Linux/macOS : python3 -I -m unittest discover -s tests). Ils n'ont pas besoin du réseau.
PROBLÈMES  "API rate limit" : le quota partagé de gh (5000/heure) est épuisé ; attendez la réinitialisation (gh api rate_limit) et augmentez refresh_seconds / baissez max_workers.
           Le moniteur s'arrête au démarrage si gh ne répond pas. Un fichier de cache corrompu est ignoré ; supprimez sentinel_cache.json pour repartir d'un cache neuf.
           Redémarrez le moniteur après une mise à jour du paquet (un processus en cours garde l'ancien code).

OUTILS     read_report.py [--lang CODE] [--json] [--export-status DOSSIER] [--export-sign-queue FICHIER]  affiche ce que dit le moniteur en cours (local, sans quota GitHub)
           gha_dispatch_all.py [--lang CODE] plan|dispatch|status|finalize|hygiene    lot de builds GitHub Actions (rien n'est compilé sur votre PC)
           release_notes.py REPO [--since ÉTIQUETTE] [--out FICHIER]    brouillon de notes de version à partir des commits (une proposition ; ne publie rien)
           release_candidates.py    projets avec des entrées dans CHANGELOG [Unreleased] et une dernière release ancienne (lecture seule)
ÉVÉNEMENTS La sentinelle écrit une ligne JSON par CHANGEMENT (nouveau rouge, CI rétablie, build bloqué, nouvelles alertes...) dans events_monitor.jsonl. Chaque ligne porte un
           `code` stable (jamais dépendant de la langue), `kind`, `level`, `repo`, `args` et `text` (dans la langue configurée). `tail -F` la suit.
CI ROUGE   Un seul critère : le DERNIER run terminé de chaque workflow sur la branche par défaut. Rouge = failure, timed_out, startup_failure ou action_required.
           cancelled, skipped, neutral et stale ne comptent pas.

NOUVEAUTÉS 1.5.1 (historique : CHANGELOG.md)
  - Onglet RÉGLAGES : nouveau groupe « IA externe pour la sentinelle » (ai.provider none / ollama / openai-compatible, modèle, adresse d'Ollama (cet ordinateur seulement), un point d'accès https, le NOM de la variable d'environnement qui contient la clé, appels par jour). La clé elle-même n'est jamais enregistrée. Désactivée par défaut ; un service externe reçoit des données de vos dépôts.
  - migrate_state.py : amène les fichiers écrits avant la 1.5.0 aux nouveaux noms. `python migrate_state.py` est une simulation ; `--apply` copie (les anciens restent), `--move` renomme. Rien n'est écrasé. Une page dans docs/MIGRATING.md, en 8 langues.
  - Premier démarrage sans vos propres fichiers de catalogue : le moniteur indique qu'il utilise ceux d'exemple (console), et `--init-catalog` crée des copies modifiables de ecosystems.json, targets.json et profiles.json.
  - Python 3.11 ou plus récent (testé avec 3.11 et 3.13, sous Windows, Linux et macOS).

NOUVEAUTÉS 1.5.0 (historique : CHANGELOG.md)
  - Onglet RÉGLAGES : modifiez depuis la page les valeurs de actions_monitor.json (liste de clés autorisées avec type et plage, validées, copie dans config_backups/ avant chaque enregistrement, jamais de jetons ni de secrets ; docs/SETTINGS.md).
  - Boutons en relief qui s'allument et s'enfoncent, icônes SVG avec nom et infobulle en 8 langues, l'aspect du tableau de bord d'état, barres et chiffres animés (tout s'arrête avec prefers-reduced-motion).
  - Sorties facultatives, désactivées par défaut, uniquement sur 127.0.0.1 : /metrics (Prometheus), /api/outputs/grafana.json (Grafana JSON / Infinity), /api/outputs/dashboard.json (docs/OUTPUTS.md, tableau de bord d'exemple dans docs/grafana/).
  - Paquet neutre : vos écosystèmes, cibles et profils vivent à l'extérieur (ecosystems_file, targets_file, profiles_file ; tools_dir pour les outils de signature locaux) ; anglais par défaut ; noms de fichiers et de dossiers en anglais.
  EN METTANT À JOUR depuis 1.4.x : ces noms ont changé (les anciens restent lus là où un fichier peut exister ; seuls les nouveaux sont écrits) :
  leer_parte.py -> read_report.py          eventos.py -> events.py          parte_history.py -> report_history.py
  LOTE_GITHUB_ACTIONS.bat/.sh/.command -> BATCH_GITHUB_ACTIONS.bat/.sh/.command
  eventos_monitor.jsonl -> events_monitor.jsonl          eventos_estado.json -> events_state.json
  PARTE_CENTINELA_DIA_<day>.* -> SENTINEL_REPORT_DAY_<day>.*     PARTE_CENTINELA_<time>.txt -> SENTINEL_REPORT_<time>.txt     CANDIDATAS_RELEASE.txt -> RELEASE_CANDIDATES.txt
  <signed_dir>/lotes/lote_<time>.json -> <signed_dir>/batches/batch_<time>.json     parte_history_days -> report_history_days     monitor_y_centinela.zip -> github_actions_monitor.zip
  sentinel.audit_files: names of the A8 audit files (neutral defaults RECONCILIATION_TOTAL_*.txt, ROUNDS_MAP_2*.txt, ROUNDS_MAP_EXTRA_*.txt)
  ci_red.json and --export-status: unchanged (a contract).

NOUVEAUTÉS 1.4.2 (historique : CHANGELOG.md)
  Quand A2 demande le dernier run d'un workflow masqué, un run en cours ou annulé ne compte plus comme vu (il pourrait cacher un rouge antérieur) : la Sentinelle demande les
  derniers runs terminés de ce workflow et prend le premier avec une vraie conclusion (cancelled et skipped sont ignorés). S'il n'y en a aucun sur la branche par défaut, seul ce workflow reste non concluant.

NOUVEAUTÉS 1.4.1 (historique : CHANGELOG.md)
  A2 ne déclare plus un dépôt entier non concluant parce que son échantillon d'exécutions est plein : pour chaque workflow du clone absent de l'échantillon,
  il demande à GitHub la dernière exécution de ce seul workflow sur la branche par défaut (lecture seule, même barrière de quota qu'A10, limité par
  sentinel.a2_resolve_max_calls_per_tick, réponses conservées sentinel.a2_resolve_ttl_seconds). Le rouge compte comme rouge ; un workflow sans exécution sur la
  branche reste non concluant et le panneau le nomme.

NOUVEAUTÉS 1.4.0 (historique : CHANGELOG.md)
  Panneau A11 « Préparation » : préparation des releases par dépôt (CI de la branche par défaut et son commit, version au-dessus de la dernière release, build, signature,
  étape suivante), santé des écosystèmes (score fondé sur des comptes réels, retenu si trop peu de dépôts ont des données) et versions épinglées en retard sur leur fournisseur
  (lues dans les fichiers de versions des clones locaux, configurés dans sentinel.readiness.pins.sources). Lecture seule ; rien n'est estimé.

NOUVEAUTÉS 1.3.0 (historique : CHANGELOG.md)
  8 langues dans la page, la ligne de commande, les événements et les rapports ; sélecteur de langue ; écosystèmes, cibles et compte GitHub comme données (github_owner,
  ecosystems_file, targets_file) ; espace de travail facultatif avec un mode réduit honnête ; mention d'auteur et GPL-3.0-or-later dans chaque fichier ; LICENSE, NOTICE, AUTHORS ;
  README et QUICKSTART en 8 langues.
LICENCE    GPL-3.0-or-later (voir LICENSE et NOTICE). Copyright (C) 2026 JuanenRac (Electro Hobby 3D).
