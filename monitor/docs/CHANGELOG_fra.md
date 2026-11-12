<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Journal des modifications

Version de l'outil lui-même (moniteur + sentinelle + outils par lots), avec son propre semver. La source est le CHANGELOG.md en anglais ; ce fichier contient les mêmes versions et sections.

## [Unreleased]

### Ajouté

- **Une vérification qu'aucun texte ne sort de sa case** (`tools/check_overflow.py` et un test qui s'ignore proprement sans navigateur) : la page est ouverte dans un navigateur sans fenêtre dans les huit langues, large et étroite, parcourt chaque onglet et chaque fenêtre, et échoue si un texte est plus large qu'une case avec bordure ou fond ou sort de la fenêtre.
- **`display.blink_red_tiles`** (activé par défaut, dans l'onglet Réglages, dans les huit langues) : les tuiles du haut et les éléments de la barre du bas qui passent au rouge clignotent doucement jusqu'à la résolution de la cause ; avec le mouvement réduit du système, elles affichent à la place un bord rouge fixe et plus épais.
- **Une vérification du doctor pour le fuseau horaire** : un fuseau que ni le système ni la table interne ne connaissent est signalé, et les heures sont alors affichées en UTC (elles retombaient auparavant sur le fuseau de l'ordinateur sans le dire).
- **L'onglet Historique indique « n sur N »** quand la liste est plus courte que ce que l'en-tête a compté (le moniteur garde les 600 exécutions les plus récentes ; les données portent `runs_total`).
- **Les panneaux de l'onglet Sentinelle comme données** : `GET /api/sentinel/panels` (lecture seule), l'outil MCP `sentinel_panels` et une section « Sentinel panels » du résumé donnent, pour A1..A13 et le second sentinelle, le niveau, une ligne et les lignes sur lesquelles agir avec dépôt et lien ; les lignes d'un panneau à « agir » ou « surveiller » deviennent aussi des alertes du flux (classes `real` et `watch`), si bien que le flux en direct, le hook, `alerts_open` et le compteur d'alertes réelles les incluent.
- **Un « bing bing » quand quelque chose de nouveau échoue** (les réglages `sound`, dans les huit langues) : la page joue deux courts signaux (Web Audio) uniquement pour un NOUVEAU rouge ou une connexion perdue, jamais lors d'un rafraîchissement ni pour ce qui existait déjà, avec une pause minimale, un volume et une pastille « Son » dans la barre du bas qui débloque l'audio du navigateur, le coupe et est mémorisée ; un bouton « Tester le son » dans Ce navigateur ; et `sound.server_beep` (désactivé par défaut, local uniquement) pour quand la page est fermée (bip Windows, `afplay` de macOS, `canberra-gtk-play` sous Linux ou la cloche du terminal, sans shell et sans réseau).

### Modifié

- **La barre du bas est redessinée** : chaque élément est une pastille avec sa bordure, la connexion et le quota prennent la couleur de leur état, l'horloge est un cadre avec de grands chiffres gras tabulaires, la date au-dessus et le fuseau en petits caractères, et la barre garde son ordre dans les fenêtres étroites.
- **Chaque case laisse son texte se couper au lieu de déborder** (tuiles, pastilles, badges, cellules, titres, boutons des fenêtres) : l'heure de la dernière lecture porte son fuseau à part en petits caractères, les lignes d'alertes passent sur deux colonnes dans les fenêtres étroites et les grilles de tuiles peuvent rétrécir sous leur contenu.

### Corrigé

- **Un seul chiffre pour les échecs ouverts** : la tuile « rouges sur main », la liste des alertes, la barre du bas et le résumé comptent la même chose, un workflow dont la dernière exécution sur la branche par défaut a échoué (un échec sur une branche de travail n'apparaît plus comme alerte ouverte), et la barre ne dit jamais « aucun avis » tant que des alertes sont ouvertes.
- **Le démarrage du moniteur nomme la version une seule fois** : la ligne « GitHub Actions v... » qui répétait l'en-tête disparaît ; l'auteur et la licence restent sur une ligne.
- **Fichiers d'état endommagés** (état de collaboration, cache et historique du sentinelle de mauvaise forme) : ils sont ignorés entrée par entrée au lieu d'atteindre le code qui les lit.

## [1.7.6]

La liaison entre le moniteur et un outil d'IA : le flux concorde toujours avec la page, chaque alerte dit pourquoi elle est rouge, un flux en direct et trois outils MCP poussent les nouvelles, une commande installe le script de liaison, la barre montre si une IA est connectée et tout fichier d'état est privé à son propriétaire.

### Ajouté

- **Le résumé et le flux suivent chaque actualisation de l'onglet Alertes** (et chaque lecture du flux et chaque cycle) : ils avaient un cycle de retard, si bien qu'une IA pouvait lire 10 alertes alors que la page en montrait 6. `ALERTS_BRIEF.md` porte désormais `Updated:` dans ton fuseau horaire et une ligne pour machines `updated_epoch:`, et `GET /api/ai/brief?fmt=json` ajoute `updated`, `updated_local` et `age_seconds`. Un cycle dont les données ne sont pas encore chargées ne résout jamais d'alertes.
- **`ai_alerts.diagnose`** (désactivé par défaut, dans l'onglet Réglages, en huit langues) : chaque alerte d'une nouvelle exécution rouge porte `diagnosis`, la première étape en échec et une dizaine de lignes utiles du journal, lues par des appels en lecture seule, nettoyées des secrets et bornées en taille et en exécutions par cycle ; une erreur d'infrastructure dans le journal rend l'alerte passagère.
- **`ai_alerts.cascade`** : les alertes rouges parce qu'un autre dépôt est rouge (nommé dans le journal ou dans la règle `ai_alerts.cascade.map`) sont listées sous lui dans le résumé et portent `origin`.
- **`GET /api/ai/stream`** (`ai_alerts.stream`, désactivé par défaut) : événements serveur, lecture seule, avec le jeton d'accès en mode réseau, limités en auditeurs et en durée, reprenables avec `Last-Event-ID` ; l'édition lite ne l'a pas.
- **Outils MCP `alerts_open`, `alert_diagnose` et `alert_ack`** (le dernier seulement avec `--allow-ack`), et un avis à l'IA à la connexion, dans les `instructions` et par une notification, disant combien d'alertes réelles sont ouvertes.
- **`monitor_cli.py ai-hook install|status|uninstall [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]`** et le script de liaison `ai_hook.py` (bibliothèque standard seulement) : il ajoute le résumé à la session d'IA et, seulement avec `ai_alerts.client_hook.block_on_stop` (désactivé par défaut), demande à l'IA d'examiner les alertes réelles ouvertes avant de finir un tour. Les réglages de l'outil sont fusionnés, jamais remplacés, une copie du fichier est gardée, un fichier qui n'est pas du JSON valide est refusé sans être touché, et tout ce qui est écrit est de l'ASCII pur. Les valeurs sont dans `ai_alerts.client_hook` (onglet Réglages, huit langues).
- **Un battement d'IA** (`ai_alerts.heartbeat`) : le flux, le serveur MCP, le script de liaison et les points d'accès notent leur dernière lecture dans un petit fichier local, et la barre du bas montre si une IA est connectée et depuis quand elle a lu.
- **`monitor_cli.py --token-file FICHIER`** et un avertissement sur stderr quand `--token` est utilisé (il apparaît dans la liste des processus) ou quand le fichier du jeton est lisible par d'autres utilisateurs.
- Des tests pour chaque changement, dans un dossier temporaire et hors ligne, y compris le mode de chaque fichier d'état avec un `umask` permissif.

### Modifié

- **Tout fichier d'état du moniteur est créé en mode 0600** (les dossiers créés en 0700) par un seul assistant, `private_io.py` : silences, événements, flux, résumé, caches, réglages et fichiers écrits par l'installeur du script de liaison. Sous Windows le programme ne peut pas imposer les modes (les dossiers héritent des droits de leur parent).
- **Au démarrage du mode réseau** avec `listen.query_access` encore activé, les premiers pas sont maintenant affichés (le désactiver ; utiliser HTTPS ou un VPN), et l'aide de `listen.network` et le guide avancé disent la même chose en huit langues.
- **Le flux d'alertes pour IA est désactivé par défaut** (`ai_alerts.enabled`, il était activé) : une nouvelle installation n'écrit aucun flux tant que tu ne l'actives pas. Une installation qui a déjà un flux dans son dossier le garde activé, et la console le dit une fois au démarrage ; personne qui l'utilisait volontairement n'est donc coupé.


### Sécurité

- **Les notifications sortantes ignorent les variables de proxy de l'environnement** (`http_proxy`, `https_proxy`) : un proxy faisait juger par la vérification l'adresse du proxy et non celle de la destination, et un proxy répondant par une redirection pouvait envoyer la requête vers le réseau local (y compris l'adresse de métadonnées d'un cloud). Le nouveau réglage `network.use_proxy` (désactivé par défaut, dans l'onglet Réglages, en huit langues) les réutilise, et alors la destination et la cible de chaque redirection sont vérifiées avant que le proxy ne reçoive quoi que ce soit. Testé avec un proxy qui redirige vers l'adresse de métadonnées.
- **`/api/ai/actions/confirm`, `/api/ai/actions/unlock`, `/api/ai/test` et `/api/notify/test` ne valent que pour cet ordinateur** en mode réseau (403 `local_only`), comme les autres points d'accès qui agissent.
- **Un plan `act` est lié à son workflow** : le plan garde le chemin résolu et le SHA-256 du fichier, et les deux sont revérifiés juste avant de lancer `act` ; un workflow modifié, remplacé ou supprimé après la confirmation ne s'exécute pas (`workflow_changed`, avec un texte en huit langues).
- **Le trousseau macOS ne reçoit plus le jeton sur une ligne de commande** : `security -i` lit la commande sur l'entrée standard, le jeton n'apparaît donc pas dans la liste des processus.
- **Tout ce qu'imprime `gh` est nettoyé avant d'être conservé** : le journal des actions pour IA et le détail d'une action refusée passent par le nettoyeur, qui couvre maintenant aussi les anciens jetons de 40 caractères hexadécimaux et le jeton gardé par le moniteur.
- **La liste des adresses refusées est bornée** (`localguard`) : le verrou suivant purge tous les verrous terminés, pas seulement celui de l'adresse qui demande, et ne garde jamais plus de 2000 entrées.
- **Un silence qui n'a pas pu être enregistré n'est pas annoncé comme enregistré** : `POST /api/alerts/mute` et `unmute` répondent `ok: false` quand le fichier n'a pas pu être écrit.
- **La ligne de commande n'affiche jamais de trace d'appels pour une réponse de mauvaise forme** : une liste, `null` ou un nombre au lieu d'un objet, ou un champ du mauvais type, se termine par le code de sortie 4 et un message.
- **Un client du réseau ne peut écrire qu'une courte liste de réglages** (la langue, le fuseau horaire et le rythme de la page) : chaque canal de notifications, chaque chemin, chaque nom de variable d'environnement et les fichiers auxquels se fie le flux de signature et d'envoi se changent depuis l'ordinateur du moniteur. Un réglage ajouté plus tard est local seulement tant qu'il n'est pas listé exprès.
- **Derrière un proxy inverse sur la même machine**, une requête portant un en-tête de transfert (`Forwarded`, `X-Forwarded-*`, `X-Real-IP`) ou le nom public du proxy n'est jamais « cet ordinateur », et le jeton d'accès est jugé avant le verrou par adresse, si bien qu'un déluge de mauvais jetons ne met pas le propriétaire dehors.
- **Les appels vers cet ordinateur ne passent jamais par un proxy de l'environnement** (`netguard.local_open`, utilisé par la ligne de commande, le serveur MCP, les vues de terminal et les crochets), et la ligne de commande ne suit pas les redirections : le jeton d'accès n'est donc pas renvoyé vers une autre adresse.
- **Chaque réponse interdit d'être mise dans un cadre** (`X-Frame-Options: DENY`, `frame-ancestors 'none'`, `nosniff`), la page vérifie le `Host` comme l'API, et toute réponse authentifiée par l'adresse obsolète `?access=` porte l'en-tête `Deprecation`.
- **Envoi et signature** : les exécutions qui existent avant un envoi sont notées et seule une nouvelle peut être prise pour la nôtre (sans horloges) ; deux nouvelles candidates demandent une revue ; l'entrée `ref` est le commit vérifié ; un workflow obligatoire est comparé à son FICHIER, jamais à un nom visible ; le nom d'un lot est en UTC.
- **Le nettoyeur du flux pour IA couvre plus de formats** : noms finissant par `PASSWORD`, `PWD`, `SECRET` ou `TOKEN`, identifiants dans une adresse, webhooks Slack et Discord, jetons de bot Telegram, jetons `glpat-`, `npm_` et `pypi-`, clés privées, longues chaînes hexadécimales et jeton d'accès de ce moniteur. `get_run_failure` du serveur MCP ne lit que les dépôts que le moniteur surveille (ou `ai.allowed_repos`).
- **Les fichiers modifiés à la main** (silences, état des mises à jour) ne perdent que leurs mauvaises entrées, et un mauvais état des mises à jour n'arrête plus le démarrage.
- **Fuseaux horaires** : Le Caire suit son heure d'été depuis 2023 dans la table intégrée, et un nom de fuseau inconnu du système est refusé dans l'onglet Réglages. L'édition complète donne le chiffre des workflows en rouge dans l'en-tête comme la lite, et `monitor_cli.py status` sans données se termine par le code 4 comme `health`.

## [1.7.5]

La ligne de commande prend le jeton d'accès sous son propre nom, le mode réseau est plus sûr par défaut (l'adresse de l'ordinateur est cachée au réseau, l'ancienne adresse ?access= peut être désactivée, les destinations de notification du réseau local sont refusées, avertissement sur le HTTP simple), les heures pour les personnes utilisent votre fuseau horaire, une alerte peut être mise en sourdine jusqu'à ce que l'élément change, et les comptes et vérifications qui donnaient des réponses fausses sont corrigés.

### Ajouté

- **`monitor_cli.py --token JETON`**, et le jeton d'accès de la ligne de commande porte désormais le nom que lit le moniteur lui-même : `MONITOR_ACCESS_TOKEN`, puis son alias `MONITOR_TOKEN`, puis `--token` (une option apparaît dans la liste des processus : c'est le dernier recours). Le message d'un client refusé nomme la variable. Testé contre un faux moniteur qui exige l'en-tête.
- **Un avertissement sur stderr** quand `monitor_cli.py` vise du `http` non chiffré sur un autre ordinateur (le jeton et les réponses circuleraient en clair) ; la réponse et `--json` ne sont pas touchés.
- **`listen.query_access`** (activé par défaut, dans l'onglet Réglages, en huit langues) : désactivé, l'adresse obsolète `?access=` est refusée et la session ne s'ouvre qu'avec `POST /api/access` (le jeton dans le corps) ou l'en-tête. L'adresse qui fonctionne répond avec un en-tête `Deprecation` et la console dit qu'elle est obsolète.
- **Un silence « jusqu'à ce que l'élément change »** : `POST /api/alerts/mute` accepte `until_change` pour une alerte ; le silence garde l'`updated_at` qu'avait l'issue ou la pull request et prend fin dès qu'il change (un nouveau commentaire, un push), ou à la fin des heures, selon ce qui arrive en premier. Les alertes de Collab portent maintenant `details.updated`.
- **Un contrôle du doctor pour un jeton partagé par plusieurs comptes** (`credential`) : il ne compare qu'une courte empreinte des jetons avec lesquels les comptes liraient GitHub (le jeton gardé par le moniteur, ou `GH_TOKEN` / `GITHUB_TOKEN` de l'environnement) et liste les comptes qui en partagent un ; le jeton n'est jamais affiché.
- Des tests pour chaque changement, dont un test d'hygiène du webhook : une charge avec un secret, un e-mail, un message de commit et un jeton n'arrive ni à la liste en direct, ni au flux, ni à une notification, et la liste en direct est désormais filtrée par une liste de champs autorisés.

- **`notify.allow_private_targets`** (désactivé par défaut, dans l'onglet Réglages, dans les huit langues) : une destination de notification qui est, ou se résout vers, une adresse de boucle locale, privée (10.x, 172.16-31.x, 192.168.x, fc00::/7), de lien local (169.254.x, avec l'adresse de métadonnées du cloud, fe80::/10), partagée (100.64.0.0/10) ou réservée est refusée. Le nom est résolu une fois et le socket s'ouvre vers l'adresse vérifiée (un nom qui change de réponse ne passe pas), et chaque redirection suit la même règle. Les canaux `mqtt` et `http_local` restent locaux par définition. Testé avec un faux serveur et un faux résolveur.
- **Un avertissement sur le HTTP simple en mode réseau** : l'aide de l'interrupteur `listen.network` dit désormais, dans les huit langues, que sans HTTPS le jeton et les données circulent en clair ; la console avertit déjà au démarrage en réseau sans certificat.
- **Des heures pour les personnes, dans votre propre fuseau horaire** : la ligne `Last read` et les sourdines de `monitor_cli.py`, le journal `actions_monitor_log.txt`, les rapports de la sentinelle, le résumé pour les IA et les notifications affichaient l'UTC (`...Z`) sans le dire, une ou deux heures d'écart avec l'horloge du mur. Elles se lisent maintenant `11:43:07 CET (10:43:07 UTC)` : le fuseau de l'ordinateur, son nom et l'heure UTC à côté. L'heure d'été est suivie (testée autour des deux changements de l'année et pour Madrid, UTC, Tokyo et New York).
- **`display.timezone`** (`local` par défaut, dans l'onglet Réglages et dans les huit langues) : `utc` ou un nom IANA comme `Europe/Madrid` affiche les textes et les horloges de la page dans ce fuseau ; la variable d'environnement `MONITOR_TIMEZONE` l'emporte sur le fichier. Sans base de données des fuseaux sur le système (Windows sans `tzdata`), une table intégrée des fuseaux courants est utilisée.
- **Les champs pour les machines gardent l'UTC et reçoivent un champ jumeau lisible** : `generated_local` dans `ci_red.json` et dans l'export local de la file, `updated_local` dans `monitor_cli.py status --json` et dans les données de la page, et une ligne `Updated:` dans `ALERTS_BRIEF.md`. Les horloges de la page et la barre du bas indiquent le fuseau (`CET`, `JST`...).
- **Un bouton « Jusqu'au changement » dans l'onglet Alertes** : il met en sourdine une alerte d'une issue ou d'une pull request jusqu'à ce que son `updated_at` change (nouveau commentaire, push), ou pour les heures habituelles au plus ; l'alerte en sourdine indique « en sourdine jusqu'au changement ». Textes dans les huit langues et un test de non-régression.

### Modifié

- **L'API appelle l'édition `complete`** (elle disait `full`) dans `/api/about`, `/api/statusbar`, `--doctor --json` et la ligne de commande ; `full` reste réservé à ce que la sentinelle peut exécuter. La page et la ligne de commande comprennent toujours les deux mots.
- **Les silences ne se font que depuis l'ordinateur du moniteur** (aussi en mode réseau, jusqu'aux éditions avec utilisateurs) : le guide de Collab le dit en huit langues et un test garde la route derrière cette règle.
- **Les workflows de ce dépôt utilisent des actions épinglées sur un commit complet**, avec la version en commentaire, et un test le maintient.

### Corrigé

- **Issues qu'on pourrait fermer** (contrôle de surface) : une exécution verte d'un autre workflow ne propose plus de fermer une issue ; l'issue doit nommer le workflow (par son nom ou par son fichier, « Firmware build failed » pour `firmware-build.yml`) et ce même workflow doit avoir une exécution verte plus récente sur la branche par défaut. Une issue qui ne nomme aucun workflow ne propose rien.
- **Tag face au manifeste** (contrôle de surface) : quand le tag de la dernière release devance le manifeste lu dans le clone, le manifeste de la branche par défaut sur GitHub est lu une fois pour cette release (le clone peut être en retard après une release) et l'avertissement disparaît s'il avait déjà cette version ; les tags qui ne sont pas des versions (`meshes-1`) sont ignorés.
- **Étape suivante d'un candidat à la release** : un dépôt dont la release exige une compilation signée dit maintenant « compiler dans Actions et signer », à part « monter la version », « signer » et « publier » ; les dépôts d'écosystèmes gérés ailleurs restent hors des candidats (testé).
- **Les runs en cours et en file sont comptés une seule fois** : les tuiles « en cours » et « en file », la liste « En ce moment », la barre d'état (nouvel élément « N en cours · M en file », aussi dans `/api/statusbar` sous `runs`) et `monitor_cli status` donnent les mêmes chiffres pour les mêmes données, dans les deux éditions. Quand les filtres de la page (écosystème, état, recherche, une liste issue d'une tuile) masquent des runs, les tuiles affichent « 3 sur 13 » et la liste commence par « Affichage de 3 sur 14 (filtres actifs) » : un filtre mémorisé par le navigateur ne ressemble plus à une incohérence. La liste des runs actifs écarte aussi un run lu deux fois. Textes dans les huit langues et tests pour les deux éditions.

### Sécurité

- **`/api/statusbar` ne donne plus l'adresse de l'ordinateur sur le réseau local (`lan_address`) à un client du réseau** en mode réseau ; la barre se dessine sans elle.
- L'adresse obsolète `?access=` n'est prise en compte que sur un `GET`.

## [1.7.4]

Une barre au pied de la page pour les avis et les données du moniteur, un bouton plein écran, des tableaux qui se trient selon une ou plusieurs colonnes avec les colonnes de votre choix, et la ligne de commande comme client du moniteur en marche.

### Ajouté

- **Une barre d'état au pied de la page** (toutes les éditions) à la place de la ligne d'auteur. À gauche, l'avis le plus important (rouge avant jaune) avec le nombre des autres et un bouton qui ouvre une fenêtre avec tous, le plus récent d'abord, avec un filtre par niveau ; sans avis, elle le dit. À droite, la connexion (un voyant : GitHub en ligne, hors ligne ou quota bas), le quota et son renouvellement, la dernière lecture, le mode de travail, combien de sentinelles sont actives, les dépôts surveillés, le compte, la version et l'édition, l'adresse du moniteur et la date et l'heure locales. Elle suit la largeur de la fenêtre : les données secondaires se replient sur les écrans étroits. `GET /api/statusbar` lui donne les faits que les données de GitHub ne portent pas (aucun appel à GitHub, aucun secret).
- **Un bouton plein écran** dans le coin supérieur droit (l'API Fullscreen ; un second appui en sort), avec son icône et son texte dans les huit langues.
- **Des tableaux triables** : Dépôts et Historique se trient d'un clic sur un en-tête (croissant, décroissant, aucun), selon plusieurs colonnes à la fois avec Maj+clic (chaque critère montre son numéro et son sens), les valeurs vides toujours en dernier, et le tri est mémorisé. Un sélecteur de colonnes en ajoute d'autres : numéro d'exécution, auteur, commit court, tentative, attente en file, fichier et écosystème dans l'Historique ; écosystème, numéro d'exécution, auteur, commit, tentative, attente en file, exécutions en 24 h, branche par défaut, visibilité, dernier push et pull requests ouvertes dans les Dépôts. Le moniteur envoie désormais le numéro d'exécution et l'attente en file de chaque exécution et un petit bloc de données par dépôt (tiré de ce qu'il a déjà lu ; rien de nouveau de GitHub).
- **`monitor_cli.py`**, la ligne de commande comme client du moniteur en marche (`status`, `health` ou `check`, `doctor`, `accounts`, `alerts`, `live`) : elle lit `GET /api/...` sur cet ordinateur ou à `--url` / `MONITOR_URL`, affiche du texte ou un document JSON avec `--json`, accepte `--account`, `--sentinel`, `--level`, `--muted`, `--timeout` et `--lang`, et utilise des codes de sortie stables (0 bien, 1 mauvais usage, 2 moniteur injoignable, 3 identifiant refusé, 4 dégradé, 5 alertes trouvées avec `--fail-on`). `health` distingue un moniteur qui ne répond pas d'une connexion GitHub qui a échoué et d'un quota épuisé. L'édition lite répond à `status`, `doctor` et `health`. Elle n'écrit jamais sur GitHub ; le jeton d'accès du mode réseau va dans `MONITOR_TOKEN`. Les anciens outils continuent de fonctionner. Guide en huit langues (`CLI.md`).
- Des tests pour chaque changement, dont la logique de tri exécutée pour de vrai avec Node là où il est installé, les commandes face à un faux moniteur, chaque code de sortie et un test vérifiant que chaque journal des modifications, dans chaque langue, liste ses versions de la plus récente à la plus ancienne, avec les mêmes versions que la source.

### Modifié

- **Les avis rouges et jaunes ne sont plus en haut de la page** : les mêmes avis apparaissent dans la barre du pied (le plus important) et dans sa fenêtre (tous).
- **Le README du paquet** (`README_<langue>.txt`) ne porte plus d'historique des versions : il renvoie au journal des modifications.
- Les images du README, de l'architecture et de la structure sont redessinées pour cette version, avec une image des nouveaux tableaux et de la barre.

### Supprimé

- **La ligne d'auteur au pied de la page** : l'auteur et la licence sont dans À propos.

## [1.7.3]

Une seconde sentinelle pour les issues et pull requests, un onglet avec les alertes de toutes les sentinelles et des mises en sourdine qui se terminent toutes seules. Collab ne fait que lire ; rien ici n'écrit sur GitHub.

### Ajouté

- **La sentinelle Collab** (`sentinel_collab.py`, édition complète seulement, désactivée par défaut) : les issues et pull requests ouvertes de vos dépôts, sur une horloge propre (`sentinels.collab.refresh_seconds`) qui ne modifie jamais la sentinelle CI. Six règles aux codes stables : `collab.issue.stale`, `collab.issue.critical`, `collab.issue.external`, `collab.pr.review_pending`, `collab.pr.draft_old` et `collab.pr.conflict`. Elle lit avec des requêtes conditionnelles (un dépôt inchangé ne coûte pas de quota), au plus `max_repos_per_tick` dépôts par tour, se met en pause sous `min_rate_remaining`, garde son état dans `collab_state.json` (dans le dossier de chaque compte) et n'annonce que les changements. Les robots sont exclus. Sa couche *Issues et pull requests* est dans l'onglet Sentinelle et `GET /api/sentinel/collab` la sert.
- **Deux nouveaux évènements**, `collab_new` et `collab_fixed`, pour le journal et pour tous les canaux de notification (ils figurent dans la liste des évènements des canaux et dans le schéma des évènements).
- **L'onglet Alertes** (édition complète) : une liste avec les alertes de toutes les sentinelles, chacune avec son origine (CI ou Collab) et son niveau, un filtre par origine et par niveau, un lien vers GitHub et un point rouge sur l'onglet avec les erreurs ouvertes. `?view=alerts&sentinel=collab` l'ouvre déjà filtré.
- **Mises en sourdine avec une fin** (`alert_center.py`) : depuis l'onglet Alertes, une alerte, une règle (son code) ou toute une sentinelle peut être mise en sourdine pendant `alerts.mute_hours` heures (24 par défaut, de 1 à 720). Une sourdine expire toute seule, se rétablit aussitôt, et un court historique dit ce qui a été coupé, depuis quand et jusqu'à quand. C'est une note du moniteur, gardée par compte dans `alert_mutes.json` ; rien ne change sur GitHub.
- **`ignore_labels`** dans les règles de Collab (`monitor:ignore` par défaut) : une issue ou pull request qu'une personne a ainsi étiquetée sur GitHub ne lève pas d'alerte. Le moniteur n'écrit jamais d'étiquette.
- **`GET /api/alerts`** (`?sentinel=`, `?level=`, `?muted=show|hide|only`) et **`GET /api/events`** (`?sentinel=`, `?since=`), tous deux en lecture seule et par compte ; `POST /api/alerts/mute` et `/api/alerts/unmute` (depuis cet ordinateur seulement, jeton à usage unique, comme tout autre changement).
- **Une liste de contrôle dans la vue en direct** (secret de 32 caractères ou plus, redirection ou tunnel vers `/api/webhook`, l'évènement de test de GitHub, surveiller le quota) et les mêmes étapes dans le guide du webhook.
- **Un guide de la sentinelle Collab** dans les huit langues (`COLLAB.md`), trouvé par l'aide.
- Des tests pour chaque changement : les règles et leurs codes stables, le coût (lectures conditionnelles, le plafond par tour, la pause), qu'elle ne fait que lire, les sourdines (portées, fin, bornes, historique, un fichier abîmé), l'étiquette d'exclusion, les points d'accès, que lite n'en a rien, les fichiers d'état de chaque compte et de la démo, et les textes dans les huit langues.

### Modifié

- La page des réglages compte douze réglages de Collab dans un bloc de l'onglet Sentinelle, et `alerts.mute_hours` à côté.
- Les fichiers `alert_mutes.json`, `collab_state.json`, `ai_alerts_state.json` et `ALERTS_BRIEF.md` ne sont jamais versionnés ni inclus dans un paquet.

## [1.7.2]

Un en-tête qui se lit dans l'ordre et s'adapte à la fenêtre, les commandes rapides fixes dans le coin supérieur droit, À propos dans le panneau latéral et la fin de l'avis de nouvelle version. Les tests cessent de laisser des fichiers à côté du code, ce qui avait remplacé les réglages d'une personne par le modèle neutre.

### Modifié

- **Les chiffres de l'en-tête, dans l'ordre et en grille** (toutes les éditions) : la première ligne va maintenant de ce qui se passe à ce qui demande de l'attention (en cours, en file, échecs, réussites, minutes de calcul, tickets ouverts, workflows rouges sur main, non signés) et la seconde garde la mécanique (dépôts, chauds, mode, lectures économisées, quota, connexion, mis à jour). Chaque ligne est une grille de huit colonnes, quatre ou deux selon la largeur de son propre bloc, de sorte que les deux lignes remplissent toujours leurs rangées à toute largeur de fenêtre, à partir d'un écran 1080p (une tuile n'impose jamais de largeur propre). La longue tuile du quota occupe deux colonnes.
- **Les commandes rapides restent dans le coin supérieur droit** : le bouton « seulement les chauds », la liste de vitesse (normal, rapide, turbo) et les pastilles de santé des écosystèmes (et les avis de budget et de pause) y sont fixés, dans une colonne à part, et se replient à l'intérieur sans déplacer les chiffres. Sous 1100 points de large le coin passe au-dessus des chiffres. La page de tous les comptes le masque, comme elle masque les chiffres.
- **Réglages, Aide et À propos sont seulement dans le panneau latéral** : les boutons de l'engrenage, du point d'interrogation et de l'information quittent l'en-tête. Réglages était déjà une section du panneau ; Aide de cet onglet reste en bas et **À propos** s'ajoute à côté. Le guide des Réglages le dit dans les huit langues.

### Supprimé

- **L'avis de nouvelle version dans l'en-tête** (le badge orange) avec son code et son style. Le panneau À propos dit toujours s'il existe une version plus récente, et la console aussi ; le réglage `updates.check` et le cache de 24 heures sont les mêmes.

### Corrigé

- **Le modèle neutre pouvait remplacer les réglages d'une personne.** Trois groupes de tests (l'isolation de lite, le jeton à usage unique et la partie lite des comptes) démarraient un moniteur dont le premier démarrage écrit `actions_monitor.json` ou `update_check.json` à côté du code, et rien ne les supprimait ; en copiant le dossier `monitor/` sur une installation, les réglages de la personne (son propre catalogue d'écosystèmes) étaient remplacés par le modèle, et tous les dépôts tombaient dans le groupe « Everything else » (un coin qui affichait « Everything else 54 »). Chacun de ces tests supprime maintenant ce qu'il a créé, et un test le prouve. Le paquet n'a jamais contenu les réglages ni le catalogue de personne, et n'en contient toujours pas.

## [1.7.1]

Une nouvelle page et la même sentinelle derrière un contrat. La page a un panneau latéral à gauche avec le logo, les sections en groupes et seize thèmes ; la sentinelle CI est désormais l'une des sentinelles d'un registre, ce qui permet aux suivantes d'arriver. Ce que le moniteur montre et décide ne change pas.

### Ajouté

- **Un panneau latéral** (toutes les éditions) : le logo de l'outil (un SVG qui se dessine avec les couleurs du thème et s'immobilise quand le système demande moins de mouvement), le sélecteur de comptes, les sections en trois groupes repliables (Surveiller, Données, Système) et l'aide. Le panneau se réduit à ses icônes et les deux choix sont mémorisés dans le navigateur. La barre du haut montre le nom de la section et les outils. Les flèches, aussi haut et bas, passent d'une section à l'autre. Sur un petit écran le panneau passe en haut. `?chrome=0` le masque, comme il masquait la barre d'onglets.
- **Seize thèmes** en plus d'auto, clair et sombre : ceux du Studio du système d'alarme (Armor, Aqua, Midnight, Ember, Forest, Violet, Solar, Ice, Crimson, Mono, High contrast, Metallic, Professional, Videogame, Terminal et Blueprint), choisis dans une liste sous Réglages > Ce navigateur ou avec `?theme=`. Chacun définit la page, le panneau latéral, les panneaux, les lignes, le texte, l'accent, les coins et les lettres. Le vert, le rouge, l'ambre et le bleu gardent leur sens dans tous, éclaircis ou assombris là où un thème l'exige pour que chaque chiffre se lise à 4,5:1 ou plus, et le texte d'un badge suit sa couleur.
- **`BaseSentinel`, `Alert` et `SentinelRegistry`** (`sentinel_base.py`, `sentinel_registry.py` ; édition complète seulement) : le contrat d'une sentinelle (`start`, `stop`, `tick`, `get_status`, `get_alerts`, `get_metrics`, `get_config_schema`, `refresh_seconds`), une alerte avec un code stable qui ne dépend jamais de la langue (`ci.red`, `ci.stuck`, `ci.pending_sign`) et le compte auquel elle appartient, et un registre qui donne à chaque sentinelle sa propre horloge. `sentinels.<nom>.enabled` dans `actions_monitor.json` en active ou en désactive une ; sans lui `sentinel.enabled` décide, comme toujours, et là où les deux disent quelque chose le nouveau bloc l'emporte.
- **`SentinelCI`** (`sentinel_ci.py`) : la sentinelle de toujours derrière ce contrat. Elle contient l'ancien `Sentinel` et ne change pas sa façon de décider : la même règle du rouge (le dernier run terminé de chaque workflow sur la branche par défaut), les mêmes fichiers, la même boucle, le même instantané.
- Des tests pour chaque changement de cette version : le contrat, le registre et ses interrupteurs, la sentinelle CI et ses alertes en deux langues, que l'édition lite ne charge rien de tout cela, le panneau latéral et les seize thèmes (que chacun définit toutes les variables et que le texte, le petit texte gris, l'accent et les quatre couleurs d'état se lisent à 4,5:1 sur sa page et ses panneaux).

### Modifié

- Le thème se choisit dans une liste sous Réglages > Ce navigateur (c'était un bouton qui parcourait auto, clair et sombre) ; un thème enregistré par une version antérieure est toujours compris.
- La couleur d'un badge, d'une barre et d'un avis qui était blanche sur rouge, ambre ou vert est maintenant celle qui se lit sur cette couleur dans le thème utilisé.
- La sentinelle démarre par le registre ; `SENTINEL["obj"]` reste la sentinelle CI, donc tout ce qui l'interrogeait continue de fonctionner. Les événements, les fichiers et les points d'accès sont les mêmes.

### Corrigé

- Un test de la 1.7.0 lisait la sortie de `tasklist` avec la mauvaise page de codes et pouvait échouer sur un Windows d'une autre langue.
- **Un refus pouvait se perdre en chemin** (toutes les éditions) : un POST que le moniteur refusait avant de lire son corps (jeton absent, corps trop gros) fermait la connexion avec des données non lues, et Windows, parfois Linux, répondait par une réinitialisation : le client voyait une connexion rompue au lieu du 403 qui lui était dû. Le moniteur lit et jette désormais ce qui reste du corps (jusqu'à 1 Mo, 2 secondes au plus) après avoir répondu, de sorte que la réponse arrive toujours. Le refus lui-même, son code et son texte sont les mêmes. Un test envoie les en-têtes, attend et envoie le corps, et échoue sans cela.

## [1.7.0]

Plusieurs comptes dans l'édition complète, chacun un moniteur à part, et une page qui les connaît. L'édition lite ne change pas : un compte, et elle ne montre même pas les nouvelles options.

### Ajouté

- **Plusieurs comptes** (édition complète seulement). Un dossier `accounts/<id>/` par compte (une personne ou une organisation) avec son propre `actions_monitor.json`, son propre cache, ses événements, ses analyses, l'état de sa sentinelle et ses journaux ; `accounts/global.json` est facultatif (`default_account`, `enabled_accounts`) et `MONITOR_ACCOUNTS_DIR` déplace le dossier. L'identifiant se compose de lettres minuscules, de chiffres, de `_` et de `-` (jusqu'à 40), c'est donc toujours un nom de dossier sûr. Sans dossier `accounts/`, rien ne change : un compte, ses fichiers à côté du code.
- **Un superviseur** (`accounts_supervisor.py`) : avec un dossier `accounts/`, `python actions_monitor.py` démarre un petit processus sur le port habituel qui exécute un moniteur par compte (`account_child.py`), chacun sur son propre port de `127.0.0.1`. Une panne, une réponse lente ou une limite de débit d'un compte ne touche jamais un autre ; un compte tombé est redémarré avec une attente croissante (2, 5, 15, 30, 60, puis 120 secondes) et le résumé le dit en panne entre-temps. Il ne lit rien de GitHub et n'écrit rien ; l'arrêter termine tous les processus qu'il a démarrés, y compris sous Windows.
- **L'API des comptes** : `GET /api/accounts` (le résumé), `GET /api/accounts/<id>/status`, et toute autre requête `/api/` va au compte nommé par `?account=<id>` ou l'en-tête `X-Account-Id` (le compte par défaut sans rien ; un compte inconnu donne un 404). Les règles d'accès sont celles d'un moniteur seul, et le jeton à usage unique d'une modification est demandé au compte auquel va la modification.
- **Un webhook pour tous** : `POST /api/webhook` est une adresse unique pour l'installation ; le superviseur lit seulement le propriétaire de `repository.full_name` et transmet l'événement intact au compte dont le `github_owner` est ce propriétaire, qui vérifie la signature avec son propre secret. Un propriétaire que personne ne surveille reçoit une réponse et est ignoré.
- **`--accounts`, `--account <id>` et `--migrate-accounts [--apply]`** : listent les comptes, n'exécutent qu'un compte comme moniteur ordinaire et déplacent l'ancienne organisation vers `accounts/default/`. La migration est un essai à blanc sauf avec `--apply`, ne déplace ni ne supprime jamais les originaux, refuse une seconde exécution et ne touche pas aux fichiers de l'édition lite.
- **La page avec plusieurs comptes** : un sélecteur de comptes sous l'en-tête et une entrée **Tous les comptes** avec une carte par compte (état, dépôts, en cours, en échec). Chaque fenêtre garde son propre compte et sa propre vue, lus dans l'adresse.
- **Vues par adresse** (`?view=now|alerts|charts|repos|settings|live` et `?chrome=0`, un écran sans boutons d'en-tête, onglets ni filtres pour un mur ou un second moniteur). La vue **En direct** montre les derniers événements envoyés par GitHub, l'état du récepteur de webhook (jamais le secret) et un sélecteur du mode de travail. `GET /api/live-status` en est la source.
- `tools/demo_accounts.py` pour les images, le guide `ACCOUNTS.md` en huit langues et des tests pour chaque changement (la suite est passée de 866 à 914).

### Modifié

- Les fichiers d'état d'un moniteur qui est un compte parmi plusieurs vivent dans son dossier via `state_dir()` ; un moniteur seul les garde à côté du code, comme toujours.
- Les images du README sont reprises et le README en huit langues montre les comptes.

### Sécurité

- Le superviseur et les comptes n'écoutent que sur `127.0.0.1` sauf si le mode réseau est actif. Le webhook n'a ni contrôle d'hôte ni jeton d'accès (un tunnel change l'hôte) et sa preuve reste le HMAC de GitHub ; un cookie de la session n'est jamais transmis à un compte.

### Corrigé

- La vue En direct de la 1.6.8 n'avait pas d'état du récepteur : avec le webhook désactivé ou un secret de moins de 32 caractères elle ne disait rien, et elle dit maintenant lequel des deux.

## [1.6.8]

Le proxy HTTPS de la 1.6.7 est maintenant vérifié face à un vrai proxy, les images sont reprises et l'historique des modifications est traduit jusqu'à la 1.6.3.

### Ajouté

- `python tools/manual_check_live.py proxy HÔTE [PORT] [CONNEXION]` : vérifie, à travers votre vrai proxy HTTPS sur le port 443, que la page est admise (la session s'ouvre avec le jeton d'accès dans le corps et le cookie revient `Secure` et `HttpOnly`) et que trois requêtes restent refusées (l'autre schéma, un autre nom d'hôte, le nom avec un port). Il lit le jeton d'accès dans `MONITOR_ACCESS_TOKEN`, ne l'affiche jamais et, sans argument, indique quoi mettre dans nginx ou Caddy.
- `tools/demo_monitor.py --network` montre la page telle qu'elle apparaît en mode réseau (la barre rouge persistante, et dans Réglages l'avertissement pour toutes les interfaces et le nouveau nom du proxy) pour pouvoir la photographier ; la démo n'écoute toujours que sur `127.0.0.1`. `tools/make_screenshots.py` prend avec lui deux nouvelles images : `web_network_now` et `web_network_settings`.
- Des tests qui parcourent toute la chaîne : un client sur un vrai TLS, un reverse proxy qui termine le TLS et transmet `Host` et `Origin` sans port, et le vrai moniteur derrière. Ils vérifient qu'un changement fait depuis la page atteint les réglages, que la même requête est refusée sans `listen.proxy_public_host`, qu'un mauvais schéma, nom ou port reste refusé, que la session s'ouvre et que le cookie est `Secure`, et que la vérification à la main s'accorde avec le proxy et n'affiche jamais le jeton (la suite est passée de 858 à 866).

### Modifié

- L'historique des modifications (Aide > Journal des modifications) est traduit dans les sept autres langues de la 1.6.8 à la 1.6.3 (la 1.6.7 et la 1.6.5 l'étaient déjà) ; les entrées antérieures à la 1.6.3 gardent le texte anglais sous un avis traduit.
- Les images du README sont reprises, 76 au total, et le README en huit langues montre le sous-onglet Avancé des Réglages et les deux images du mode réseau.
- `docs/MIGRATING.md` a un bloc de la 1.6.7 à la 1.6.8, et la feuille de route en huit langues recense ce qui reste : les anciennes entrées de l'historique et les vérifications qui demandent vos propres services.

### Corrigé

- L'historique de la 1.6.7 disait que seules la 1.6.7 et la 1.6.5 étaient traduites et que le proxy n'avait été vérifié qu'avec la garde ; cette version traduit le reste jusqu'à la 1.6.3 et vérifie le proxy de bout en bout, comme ci-dessus.

## [1.6.7]

Un proxy HTTPS sur le port 443 par défaut fonctionne désormais avec le mode réseau, et une partie de plus de l'historique des modifications est traduite.

### Ajouté

- `listen.proxy_public_host` (Réglages > Avancé > Réseau, vide par défaut) : le nom d'hôte public d'un proxy HTTPS sur le port 443 par défaut qui transmet `Host` et `Origin` sans port. Jusqu'ici la garde comparait les deux avec le port du moniteur, donc un tel proxy était refusé ; ce seul nom est maintenant accepté tel quel. Il ne compte que lorsque le mode réseau est actif et que la session est en HTTPS (TLS direct ou `listen.secure_cookie`), il doit être un simple nom d'hôte (un port, un chemin, un utilisateur, une espace ou un littéral IPv6 le rendent vide), comme tout réglage que le schéma marque `secure` il ne se change que depuis l'ordinateur lui-même, et son libellé et son aide existent en huit langues.
- Des tests pour chaque changement de cette version (la suite est passée de 843 à 858 et le nouveau fichier vérifie la garde, la valeur, le schéma et les textes).

### Sécurité

- L'exception de la garde est aussi étroite que possible : seul ce nom est accepté sans port, jamais un autre hôte sans port, jamais en HTTP simple, et l'`Origin` doit porter le même nom avec le schéma `https` (un autre schéma, un port, un chemin, un utilisateur ou un autre hôte restent refusés). Le nom du proxy n'apparaît jamais dans l'état public de la garde.

### Modifié

- L'historique des modifications (Aide > Journal des modifications) est traduit dans les sept autres langues pour la 1.6.7 et la 1.6.5 (la 1.6.6 l'était déjà) ; les entrées plus anciennes gardent le texte anglais sous un avis traduit et suivront, de la plus récente à la plus ancienne.
- `docs/ADVANCED.md` (huit langues) explique le proxy sur le port par défaut au lieu de dire qu'il n'est pas pris en charge, `docs/MIGRATING.md` a un bloc de la 1.6.6 à la 1.6.7, et le guide des réglages et l'index de l'Aide sont régénérés.

## [1.6.6]

Corrections du mode réseau et de `act`, les points en suspens de la 1.6.5 et l'historique des modifications en huit langues.

### Ajouté

- Une barre rouge persistante en haut des Réglages quand le mode réseau écoute sur toutes les interfaces (`listen.host` = `0.0.0.0`), en huit langues. Jusqu'ici seul `--doctor` le disait.
- `POST /api/access` avec `{"token": "..."}` : ouvre la session du mode réseau avec le jeton d'accès dans le corps, de sorte qu'il ne reste jamais dans une barre d'adresse, un historique ou un journal. Mêmes contrôles que toute requête (hôte, origine, blocage après de mauvais jetons, comparaison à temps constant) ; le cookie revient `HttpOnly`, `SameSite=Strict` et, en HTTPS, `Secure`. L'adresse avec `?access=` de la 1.6.5 continue de fonctionner.
- Un compteur des échecs que le moniteur avale volontairement (`degraded.py`) : une ligne structurée sur la console pour chacun, un décompte par origine dans `degraded.json` à côté du moniteur, la nouvelle vérification `degraded` de `--doctor` et une ligne « Erreurs avalées » dans le panneau À propos. Le comportement ne change pas : ils n'arrêtent toujours jamais le moniteur.
- L'historique des modifications (Aide > Journal des modifications) a désormais un fichier de traduction par langue, `docs/CHANGELOG_<langue>.md`, avec les mêmes versions et sections que la source anglaise ; `tools/make_help_index.py --check` et un test échouent si une version manque dans une traduction. Les entrées pas encore traduites le disent, dans la langue du lecteur.
- Des tests pour chaque changement de cette version (la suite est passée de 811 à 843).

### Corrigé

- **Le mode réseau en HTTPS était inutilisable depuis la page.** La garde de même origine n'acceptait qu'une origine `http://` ; avec TLS direct ou un proxy HTTPS (`listen.secure_cookie`), le `Origin: https://...` du navigateur était refusé et chaque modification (réglages, confirmations) recevait 403. La garde construit maintenant l'origine permise avec le schéma de la session (https ou http, jamais les deux), compare exactement l'hôte et le port et refuse une origine mal formée. Testé avec un vrai serveur TLS et un certificat créé par le test.
- `act` : Stop libère désormais l'exécution, si bien que le démarrage suivant ne répond plus `busy` pour toujours quand le processus ne se termine pas ; un worker tardif ne touche jamais une exécution plus récente ; le tube de sortie et le minuteur sont fermés dans tous les cas (fin normale, limite de temps, Stop, erreur inattendue) et la suite n'émet plus de `ResourceWarning`.
- `tools/make_screenshots.py` pouvait se terminer sans rien dire : le navigateur tourne sans tubes capturés et avec une limite de temps, l'absence de navigateur ou une démo qui ne démarre pas est signalée, `MONITOR_BROWSER` désigne un navigateur à la main et le code de sortie vaut 1 si une image n'a pas été faite.

### Sécurité

- En mode réseau, tout réglage que le schéma marque `secure` ne peut être modifié que depuis l'ordinateur lui-même, et non plus seulement les quatre familles d'avant (`listen.`, `github_token.`, `act.`, `github_actions.`) : aussi le webhook, les actions de l'IA, les notifications, OpenTelemetry, le miroir, les runners, les sorties et le reste. La liste est lue dans le schéma, donc un nouveau réglage sûr est couvert sans que personne y pense ; un test les parcourt tous.

### Modifié

- Les images de À propos, Aide, Maintenant, Basique et Avancé dans le README et les guides sont refaites.
- `docs/ADVANCED.md` (huit langues) : HTTPS avec votre certificat ou derrière un proxy, la règle de l'origine, la session ouverte par POST et la barre d'avertissement.

## [1.6.5]

Une version d'intégrité et de sécurité : aucune grande fonction nouvelle. Ce qui ne peut pas être prouvé n'est plus tenu pour sûr.

### Ajouté

- Nouveaux réglages, tous avec une valeur par défaut prudente : `dispatch.required_ci` (et, dans le fichier, `dispatch.required_ci_repos` et `dispatch.required_ci_profiles`), `act.allow_symlinks`, `listen.tls_cert_file`, `listen.tls_key_file`, `listen.secure_cookie`, `listen.max_failed_attempts`, `webhook.replay_seconds`, `webhook.max_per_minute` ; le guide des réglages est régénéré.
- `finalize --accept-legacy` pour les lots écrits par une version plus ancienne, et les contrôles `risks` et `backend` de `--doctor` (huit langues).
- Des tests pour chaque changement de cette version (la suite est passée de 729 à plus de 800).

### Sécurité

- **Un commit au vert exige la CI obligatoire.** `gha_dispatch_all.py` ne juge un commit vert que si les fichiers de workflow obligatoires ont réussi dessus (`ci.yml` par défaut ; `dispatch.required_ci`, `dispatch.required_ci_repos`, `dispatch.required_ci_profiles`), que rien n'a échoué, expiré ou n'attend une approbation (`action_required` bloque comme un échec), que rien n'est encore en cours et que la liste des exécutions est complète (il lit jusqu'à cinq pages ; une liste plus longue n'est pas verte).
- **Un `git fetch` en échec arrête l'envoi** de ce dépôt, les commandes git ont une limite de temps et les identifiants de commit sont vérifiés ; un vieux `origin/main` n'est jamais pris pour une preuve.
- **Le catalogue ne peut ni sortir de son dossier ni modifier l'envoi.** `tool` doit être un simple nom de fichier situé dans le dossier des outils (les liens qui en sortent sont aussi refusés) ; `extra` ne peut contenir que des entrées de workflow `-f clé=valeur` (jamais `dry_run`, `ref`, `-R`, `--ref`) ; `finalize_flags` seulement des options longues ; les arguments de `gh workflow run` sont construits à partir des éléments validés et revérifiés au déclenchement du lot.
- **Les anciens lots ne sont pas signés à l'aveugle.** `finalize` ne propose à la signature qu'une exécution dont le lot a enregistré qu'il a été construit sur le commit vérifié. Un lot écrit par une version plus ancienne est `needs_review` ; `finalize --accept-legacy` relit l'exécution depuis GitHub, ne l'accepte que si son commit est celui enregistré, avertit et demande le mot LEGACY avant chaque signature.
- **`act` reste dans l'espace de travail.** Le clone est résolu et doit être un vrai dossier de l'espace de travail (un lien, un nom avec `..` ou un `.github` qui pointe ailleurs est refusé ; `act.allow_symlinks` autorise un lien vers un clone). La limite de temps et Stop terminent tout l'arbre de processus lancé par l'exécution (un groupe de processus sous Linux et macOS, `taskkill /T` sur son propre PID sous Windows) et suppriment les conteneurs `act-` créés par cette exécution.
- **Mode réseau** : HTTPS servi directement avec votre propre certificat et clé (`listen.tls_cert_file`, `listen.tls_key_file` ; TLS 1.2 ou plus récent ; le moniteur ne démarre pas en HTTP simple s'ils sont inutilisables) ou le cookie `Secure` derrière un proxy HTTPS (`listen.secure_cookie`) ; le jeton d'accès quitte aussitôt la barre d'adresse (redirection, pas de `Referer`) ; une adresse qui envoie trop de jetons erronés est refusée pendant cinq minutes (`listen.max_failed_attempts`) ; l'adresse de la page est celle sur laquelle le serveur écoute ; seules les adresses IPv4 sont acceptées, dans les réglages comme dans la garde ; la console signale quand la connexion est en HTTP simple.
- **Webhook** : chaque livraison exige son identifiant `X-GitHub-Delivery` et une livraison répétée est ignorée pendant `webhook.replay_seconds` ; un dépôt peut provoquer au plus `webhook.max_per_minute` événements acceptés par minute ; le propriétaire dans `full_name` doit être le compte surveillé ; une adresse est limitée à 120 requêtes par minute en mode réseau ; un événement accepté écarte les lectures conditionnelles enregistrées de ce dépôt et le marque pour le cycle suivant ; un en-tête de signature aux caractères inhabituels est simplement refusé.
- **Serveur MCP** : un message de forme incorrecte (paramètres, arguments, id, méthode) reçoit une erreur pour ce seul message, un défaut inattendu dans un outil est une erreur interne qui ne termine pas le serveur, et une ligne de plus de 64 Ko est refusée.
- **Le jeton GitHub enregistré n'est remis qu'à `gh`.** Il n'est plus placé dans l'environnement du moniteur, si bien que `act`, votre commande de notification et tout autre processus enfant ne peuvent pas en hériter.
- **Un GET n'écrit jamais.** La copie du rapport quotidien dans le dossier d'audit est un POST avec le jeton à usage unique (`/api/sentinel/parte/save`) ; `?save=1` sur le GET a disparu.
- `--doctor` nomme les combinaisons dangereuses (mode réseau sur toutes les interfaces, actions de l'IA qui s'exécutent avec le mode réseau actif, `act` avec le mode réseau actif, le jeton dans un fichier en clair) et indique où le jeton est conservé, jamais le jeton.

### Corrigé

- `max_per_hour` des notifications limite désormais les messages (une unité par canal, réservée d'un coup sous un seul verrou) et non les événements ; un canal qui ne peut pas envoyer ne réserve rien.
- Deux enregistrements simultanés des réglages ne perdent plus l'un des deux (un verrou dans le processus et un fichier verrou).
- L'export de la file de signature dit pourquoi il n'a pas écrit (un lecteur ou un chemin réseau refusé, un dossier au lieu d'un fichier, l'erreur du système) au lieu d'un simple refus.
- L'attente de la limite secondaire et la nouvelle tentative après un délai dépassé portent une gigue aléatoire.
- Le test qui décompresse le zip dans un dossier propre ne fait plus partie de la suite ordinaire : `make_release.py` exécute la suite une fois avec une limite de temps, puis l'installation propre comme étape à part, et affiche stdout et stderr quand l'une échoue.

### Modifié

- Les guides des notifications, du webhook, des fonctions avancées, des sorties, des alertes d'IA et de la migration disent tout cela en huit langues ; `docs/MIGRATING.md` a un bloc de la 1.6.4 à la 1.6.5.

## [1.6.4]

### Ajouté

- **Alertes pour les IA** : le moniteur écrit un flux local en lecture seule (`ai_alerts.jsonl`, une ligne par événement, et `ALERTS_BRIEF.md`, réécrit à chaque cycle, 2 Ko par défaut) avec une alerte par workflow en rouge : identifiant stable, gravité, cause probable distinguée comme réelle ou passagère avec des règles modifiables, action suggérée et un état (ouverte, reconnue, résolue d'elle-même quand le workflow repasse au vert). Tout passe par un nettoyeur de jetons, clés, adresses e-mail, adresses IP et dossiers personnels. `GET /api/ai/brief` et `GET /api/ai/alerts`, un serveur MCP optionnel en lecture seule (`mcp_server.py` : `get_alerts`, `get_red_repos`, `get_run_failure`, `get_quota`, et `ack_alert` avec `--allow-ack`), une notification quand une nouvelle alerte RÉELLE apparaît, un crochet optionnel vers une adresse de cet ordinateur (désactivé) et un `ai_hint` optionnel dans `ci_red.json`. Nouveau guide `AI_ALERTS.md` en huit langues.
- **Fonctions facultatives, toutes désactivées par défaut, chacune avec son interrupteur dans Réglages > Avancé** et des tests qui prouvent qu'elles refusent sans l'interrupteur, la confirmation ou le jeton : le mode réseau (une adresse privée, un jeton d'accès pour chaque requête, des noms d'hôte acceptés, une barre rouge persistante, des clés d'exposition modifiables seulement depuis l'ordinateur lui-même) ; un jeton GitHub conservé par le moniteur dans le coffre sécurisé du système (DPAPI de Windows, Keychain de macOS, Secret Service de Linux, sinon un fichier aux droits 600) et jamais dans un réglage, un journal ou une réponse, avec un bouton de suppression ; des actions sur GitHub (relancer, annuler, fermer, fusionner), chacune confirmée séparément après avoir montré exactement ce qui sera envoyé ; l'exécution d'un workflow ici avec `act` depuis une liste fermée, sans vrais secrets ; une copie locale des artefacts ; des runners auto-hébergés (inactifs, occupés, hors ligne, disque et charge en option) ; l'export OpenTelemetry (traces et métriques, OTLP/HTTP JSON) ; les organisations du compte ; le FinOps par étiquettes de job (Linux, Windows, macOS et gros runners), le prix des minutes au-delà de celles incluses, Codespaces, Packages et stockage du rapport de facturation. Nouveau guide `ADVANCED.md` en huit langues et `tools/manual_check_live.py` pour essayer à la main les vrais services.
- `--doctor --json` ; le doctor signale aussi les ports occupés, le quota restant, si vous avez votre propre fichier de cibles, le jeton à usage unique et l'exposition. Le README du paquet commence par le choix du lanceur (complet, lite, par lots, terminal, doctor, démo).
- L'application de terminal modifie les réglages simples (pas ceux de sécurité) et a un onglet IA ; une bannière persistante pour les réglages qui demandent un redémarrage survit à un rechargement ; l'en-tête montre quand le A10 de la sentinelle est en pause pour cause de quota et quelle part du budget de minutes est utilisée ; le serveur retient aussi l'accueil.
- `redrule.py` ignore les exécutions dynamiques des mises à jour de dépendances comme le fait le tableau de bord, et les cas partagés de la règle sont désormais une fixture de test.

### Modifié

- **L'Aide est complète en huit langues** : les documents de la feuille de route, de contribution, de sécurité et de support sont traduits, les libellés fixes du journal des modifications sont traduits et ses entrées sont marquées comme uniquement en anglais, avec un avis traduit ; `tools/make_help_index.py --check` et un test échouent quand un sujet manque d'une langue. Une recherche montre au plus 30 résultats et un document énorme ne retient plus le fil du serveur.
- La tuile rouge compte les workflows dans les deux éditions et indique dans combien de dépôts. L'édition lite hérite du rythme d'actualisation de la complète à son premier démarrage.
- Un échec passager (un hoquet TLS, un 5xx) est retenté avec un délai exponentiel et n'est affiché comme une erreur qu'après trois cycles de suite ; la dernière image reste.
- La vue terminal de l'édition lite ne demande plus la sentinelle ; l'édition lite ne charge jamais le module de la sentinelle (la garde locale est passée dans `localguard.py`).
- `--demo` redirige vers son dossier temporaire tout fichier qu'il pourrait écrire (journaux, caches, flux d'événements, historique, accueil).

### Sécurité

- Avec `updates.check` désactivé ou `airgapped` activé, le moniteur ne fait aucune requête réseau pour l'avis de mise à jour (testé).
- Vérifié contre la vraie API de GitHub : les scopes du jeton sont lus correctement, la liste des organisations et le rapport de facturation se dégradent en silence (un compte sans le scope `user` reçoit « introuvable » et le moniteur garde l'estimation).

## [1.6.3]

### Ajouté

- **Panneau À propos** (le bouton **i** de l'en-tête, dans les deux éditions) : version, édition, auteur, licence, Python et système, liens (dépôt, releases, journal des modifications, documentation, tickets), les fichiers qu'il utilise (lecture seule), la santé du serveur, les crédits des bibliothèques et un bouton qui copie les informations pour le support (sans secret ni jeton, le dossier personnel affiché en `~`). `GET /api/about`, et `--about` en console.
- **Panneau d'Aide** (le bouton **?**, la touche `?`, et un « ? » dans la barre d'onglets qui ouvre la page de l'onglet où vous êtes) : toute la documentation (README, démarrage rapide, chaque guide, feuille de route, journal des modifications, contribution, sécurité) sous forme d'index consultable, dans la langue de la page et en anglais là où un document n'est pas traduit, servi par le serveur local sans Internet. Il est construit à partir des vrais documents par `tools/make_help_index.py` (`--check` dans la CI), si bien qu'aucun texte n'est écrit deux fois ; le markdown est rendu de façon sûre (tout est échappé, aucune image n'est chargée, seulement des liens `http(s)` et des liens vers d'autres documents). En console : `--help-topics [SUJET]` et `--help-search MOTS`.
- **Avis d'une version plus récente** : un badge discret dans l'en-tête, une ligne dans À propos, en console et dans `--doctor` quand une release plus récente est publiée. Une seule requête en lecture seule par jour vers la page publique des releases, avec le même client que tout le reste (lecture conditionnelle), ne télécharge ni n'installe jamais rien, n'envoie rien sur vous, ignore les préversions, compare les versions comme des nombres (1.6.10 est plus récente que 1.6.9), se tait hors ligne et s'éteint avec `updates.check` ou dans une installation isolée (`airgapped`).
- **Réglages > Essentiel**, le premier onglet : ouvrir le navigateur au démarrage, l'avis de mise à jour, l'interrupteur d'installation isolée, le jeton à usage unique, les options de découverte, les règles de cycle de vie, ainsi que le plan et les quotas. En dessous, ce que le moniteur a trouvé dans le compte (propriétaire, dépôts trouvés, surveillés, écartés), les nouveautés et les groupes suggérés.
- **`--doctor`** : Python, `gh`, le compte connecté, le quota restant, le réseau, le droit d'écriture du dossier, un port libre, et les optionnels Docker, Rich et Textual ; chaque échec vient avec la commande exacte qui le corrige, en huit langues.
- **`--demo`** : la page avec des données inventées, sans `gh`, sans connexion ni réseau ; rien de ce qui est à vous n'est lu ni écrit.
- **Un accueil en trois étapes** la première fois que la page est ouverte (ce qu'il fait, ce qu'il a trouvé dans votre compte, où aller ensuite).
- **Découverte automatique** : des événements pour un dépôt nouveau, disparu, archivé ou désarchivé (console, Réglages > Essentiel et, dans l'édition complète, les notifications) ; un groupe suggéré quand trois dépôts non classés ou plus partagent un préfixe, ajouté seulement après votre confirmation et avec une copie du fichier ; des règles de cycle de vie pour écarter les forks, les dépôts vides et privés ; une fréquence d'actualisation automatique optionnelle qui suit l'activité réelle dans le budget d'appels.
- **Un jeton à usage unique** (`session_guard`, activé par défaut) que la page demande juste avant d'enregistrer un réglage ou de confirmer une action, et une **barre de redémarrage** sur chaque onglet tant qu'un réglage enregistré attend un redémarrage.
- **Niveaux du linter de workflows** (information, avertissement, erreur) comme filtres dans la page, et `Scripts` dans l'application de terminal.
- **Quotas et plans pour tout type de compte** : votre plan dans Réglages > Essentiel ; les chiffres (minutes incluses en argent, tarifs par système, concurrence, limites d'un job et d'une exécution, quotas de l'API) vivent dans `quotas.json`, que vous pouvez modifier sans nouvelle version ; minutes facturables distinctes des minutes d'horloge (les dépôts publics ne coûtent rien, les privés utilisent le multiplicateur de Windows ou macOS), une projection mensuelle marquée comme estimation, un avertissement une fois par mois à 75 % et 90 % des minutes incluses via les notifications, jobs en cours et en file face à la limite du plan, jobs proches de la limite de 6 heures et le type de jeton lu dans les propres en-têtes de GitHub (avec le conseil de se connecter quand il ne reste que 60 appels par heure). L'usage réel vient seulement du rapport de facturation optionnel en lecture seule (`quota.billing_api`, désactivé par défaut, silencieux sur un 403 ou un 404). `GET /api/quota`.
- **Modes de travail : normal, rapide et turbo** (`modes.py`, guide `MODES`) : un sélecteur avec une icône de jauge dans l'en-tête et `--mode` / `--mode-minutes` en console, dans les deux éditions. Les préréglages vivent dans le bloc `modes` de la configuration ; avant de démarrer, la page montre les appels par heure dans le pire cas, ce que les lectures conditionnelles économisent d'ordinaire et combien de temps durerait le quota restant ; il revient à normal tout seul quand le temps est écoulé ou quand le quota passe sous `min_rate_remaining`, avec un avis ; sans connexion (60 appels par heure) rapide et turbo sont refusés avec la raison ; il exige le jeton à usage unique, vit en mémoire et la bannière de la console le nomme. `GET` et `POST /api/mode`.
- **Après une limite de débit secondaire**, le moniteur attend au moins une minute puis double l'attente jusqu'à cinq minutes au lieu de réessayer aussitôt.
- **L'application de terminal interactive** `tui_textual.py` (optionnelle, `pip install textual`) : onglets Résumé, Dépôts, Builds, Performance, Scripts et Réglages (les interrupteurs de base), un filtre, les niveaux du linter, actualiser, ouvrir dans le navigateur, À propos et Aide ; `--lite` montre les onglets de l'édition lite. La vue simple avec Rich (`tui.py`, `--once`) reste et a aussi `--about` et `--help-topics`.
- **L'édition se reconnaît d'un coup d'œil** : une bannière de démarrage (`GitHub Actions Monitor LITE 1.6.3 · port 8766 · actions_monitor_lite.json · sans sentinelle · http://127.0.0.1:8766/`, ou COMPLETE · port 8765 · sentinelle active), le titre de la fenêtre de la console et du terminal, l'étiquette `[LITE]` / `[COMPLETE]` dans les lignes d'état, dans `--doctor` et dans les vues de terminal, et le même titre dans les lanceurs.
- Nouveaux guides en huit langues : **La sentinelle et ses contrôles A1-A13** (ce qu'elle est, comment elle démarre, les fichiers qu'elle écrit, comment la lire, la règle exacte, le réglage et l'action de chaque contrôle et les vingt-cinq contrôles d'A10 ; un test garde le guide et le code d'accord), **Quotas et plans** et **Vos cinq premières minutes** (`FIRST_STEPS`) ; le guide de migration a un bloc de 1.5.x à 1.6.x et le README a un sélecteur entre les deux éditions.
- Des tests pour tout cela (les versions sémantiques, l'avis hors ligne, désactivé et en installation isolée, le markdown sûr, l'index, le jeton à usage unique, la découverte, `--doctor`, les quotas pour dépôts publics et privés, Windows et macOS, sans jeton, Enterprise et un 403 du rapport de facturation, la bannière et les lanceurs).

### Modifié

- La page des Réglages commence par l'onglet **Essentiel** ; le guide `SETTINGS` est généré avec lui.
- Le moniteur liste les dépôts du compte avec leur type (archivé, fork, privé, vide) ; un `gh` plus ancien sans ces champs revient à la liste simple.

### Sécurité

- Rien de nouveau n'écrit sur GitHub. L'avis de mise à jour, le rapport de facturation et la découverte sont en lecture seule et désactivables ; aucun n'envoie de données sur vous. Les panneaux Aide et À propos sont servis depuis cet ordinateur et le texte de support ne contient aucun secret.
- Écrire un réglage, confirmer une action de l'assistant IA et ajouter un groupe suggéré exigent le jeton à usage unique de la page.

## [1.6.2]

### Ajouté

- **Un groupe fourre-tout** `rest` (« Tout le reste », préfixe `*`) à la fin du catalogue d'exemple des écosystèmes, pour qu'une nouvelle installation ne laisse aucun dépôt de côté.
- **Un groupe automatique « Non classé »** pour les dépôts qu'aucun groupe ne revendique (réglage `show_unclassified`, activé par défaut ; un choix explicite d'écosystèmes est respecté).
- **Un avertissement quand le filtre masque des dépôts** : un bandeau (complète et lite) dit « votre filtre d'écosystèmes masque N des M dépôts du compte » et les nomme.
- **L'édition lite démarre avec ce que vous avez déjà configuré** : au premier démarrage, `actions_monitor_lite.json` copie depuis `actions_monitor.json` (s'il existe) le compte, les dépôts et écosystèmes à surveiller, les fichiers de catalogue, les exclusions, la langue et la profondeur de lecture, et le dit dans la console. Sans ce fichier, son modèle surveille tous les écosystèmes.
- **`tui.py --lite`** (ou `MONITOR_MODE=lite`) lit l'édition lite sur le port 8766.
- **`redrule.py`**, la règle unique et petite du « rouge sur main », utilisée par la sentinelle et par l'édition lite (qui marque le chiffre comme approximatif car elle devine la branche par défaut).
- **`ghamon_etag_invalid_total`**, le nombre d'entrées de cache abîmées, dans `/metrics`.
- Tests : parité des données d'en-tête entre l'édition complète et la lite, le groupe fourre-tout, le nombre de dépôts masqués, le démarrage lite, la marque chaude du webhook, l'entrée de cache abîmée, et le fait qu'importer le moniteur ou la sentinelle ne charge jamais Rich.
- Guides `LITE` et `SETTINGS` (huit langues) mis à jour.

### Modifié

- **Les deux éditions montrent les mêmes chiffres d'en-tête** : exécutions, échecs, succès, minutes de calcul, en cours et en file sont comptés une seule fois, par le serveur, sur les mêmes 24 heures et avec chaque exécution comptée une fois ; l'édition lite lit aussi profondément que la complète. L'édition lite masque la tuile « non signé ».
- **Un évènement de webhook marque le dépôt comme chaud**, de sorte que le cycle suivant le relit quoi qu'ait dit l'évènement.
- La tuile du quota GitHub est peinte dès le premier instant, pendant que les dépôts chargent encore.

### Corrigé

- Une nouvelle installation avec le catalogue d'exemple ne voyait presque aucun dépôt ; l'édition lite détectait un dépôt sur 129 parce que son modèle filtrait par écosystème.
- **Une entrée de cache abîmée n'est qu'un échec de cache** : elle est jetée et le point d'accès est relu en entier.
- « Rouge sur main » et les minutes de calcul différaient entre les deux éditions.

### Sécurité

- L'édition lite n'hérite jamais de la complète la sentinelle, l'IA, le webhook, les sorties ni les notifications, ni aucun secret ; elle n'écrit ni `ci_red.json` ni file de signature.

## [1.6.1]

### Ajouté

- **L'édition lite**, un second produit plus simple dans le même paquet : `MONITOR_LITE_GITHUB_ACTIONS.bat` / `.sh` / `.command` ou `--lite` / `MONITOR_MODE=lite`. Ce qui tourne et ce qui a échoué, échecs et succès des 24 heures, rouge sur main, l'historique et les graphiques de base ; une page de Réglages courte (compte, dépôts et écosystèmes, actualisation, langue, thème) ; son propre fichier `actions_monitor_lite.json`, ses propres fichiers d'état avec le suffixe `_lite` et le port 8766, de sorte que les deux peuvent tourner côte à côte.
- **Commande `act` dans le panneau du dépôt** : pour chaque workflow du dépôt, `act -W .github/workflows/FICHIER -j JOB` prêt à copier. Le moniteur ne l'exécute jamais (l'exécuter n'existe que comme action confirmée de l'assistant IA).
- **Un exemple de conteneur** (`deploy/Dockerfile`) que la CI construit.
- Guide `LITE` en huit langues, un tableau Lite contre Complète dans chaque README et de nouvelles captures des deux éditions en clair et en sombre.
- La feuille de route liste ce qui n'a pas tenu : miroir local des artefacts, FinOps des minutes, état des runners auto-hébergés et un export OTLP, et les notes de la vue terminal (pourquoi elle utilise Rich).

### Sécurité

- L'édition lite n'a pas de sentinelle : elle n'est pas importée et ses points d'accès répondent 404.

## [1.6.0]

### Ajouté

- **Lectures conditionnelles (ETag)** : chaque lecture des listes d'exécutions envoie `If-None-Match` ; une réponse `304 Not Modified` ne coûte pas de quota. L'en-tête et `ghamon_etag_saved_total` comptent les lectures économisées ; `cache.etag.*` dans l'onglet Réglages.
- **Résistance aux coupures réseau** : quand toutes les lectures d'un cycle échouent sur un problème de connexion, la page garde la dernière image avec un bandeau hors ligne et reprend toute seule ; évènements `offline` et `online` (ils peuvent être notifiés) et `ghamon_offline`.
- **Analytique** (section A12 de l'onglet Sentinelle, `/api/analytics`, `/metrics`, la source JSON de Grafana) : p50 / p95 de la durée de chaque workflow, du temps en file de ses jobs et de chaque étape ; workflows devenus plus lents que d'habitude ; workflows **instables** (échoué puis réussi sur le même commit, ou ayant demandé une autre tentative), simple étiquette qui ne change jamais ce qui compte comme rouge.
- **Webhook entrant en temps réel** : un évènement `workflow_run` signé met à jour la liste des exécutions de son dépôt sans lire GitHub, les évènements `workflow_job` apportent les temps de file et d'étape ; seuls des champs courts validés sont conservés (`/api/live-events`).
- **Linter de workflows** : `lint_workflows.py` (actions non épinglées par SHA, permissions absentes ou larges, secrets en clair, injection, `pull_request_target` avec le code de la PR), règles activables avec leur propre gravité, une ligne dans le rapport du jour et la section A13. Un commentaire `# monitor-lint: ignore RÈGLE motif` ou le réglage `lint.ignore` fait taire une trouvaille.
- **Notifications** (désactivées par défaut) : Telegram, Discord, Slack, Matrix, MQTT et une adresse HTTP locale, une limite par heure, un bouton de test et un contrat d'adaptateurs documenté (`monitor/docs/schemas/notification_event.schema.json`).
- **Assistant IA** : nouveaux fournisseurs `anthropic` (API Messages, le modèle est à vous de choisir) et `copilot` (`gh copilot` avec votre propre connexion, texte seulement, sans outils) ; nouvelles tâches (rapport du jour, notes de version, une question sur un dépôt) ; réglages pour les types d'évènement, les dépôts, la langue et les limites, un bouton de test et l'usage du jour. Une liste fermée d'actions (`gh run rerun`, `gh issue close`, `act`), seulement PROPOSÉES par défaut.
- **Les chiffres de l'en-tête sont des tuiles** avec une icône, un grand chiffre et une petite étiquette, colorées selon l'état, avec une infobulle, un clic qui mène à l'onglet, des chiffres qui comptent et un squelette qui montre aussitôt les dernières valeurs connues ; la seconde ligne (dépôts, chauds, mode, lectures économisées, quota GitHub avec une barre et un compte à rebours en direct, connexion, dernière mise à jour et progression du chargement) est faite de tuiles aussi.
- **Vue terminal** : `tui.py` dessine une grille en direct dans la console (lecture seule, optionnelle, demande le paquet `rich` ; le moniteur et ses tests n'ont besoin d'aucun paquet).
- **Pour les serveurs et les grands comptes** : `GET /api/health`, `GH_HOST` pour GitHub Enterprise Server (tous les liens de la page le suivent), `discover_limit`, permissions minimales par fonction, et un guide pour l'exécuter comme service (systemd, launchd, une tâche planifiée, un conteneur) et derrière un proxy inverse.
- Schémas JSON publiés de `ci_red.json`, de l'export public et de l'évènement de notification (`monitor/docs/schemas`), et une feuille de route publique (`docs/ROADMAP.md`).
- Nouveaux guides en huit langues : notifications, l'assistant IA, analytique, outils de console et déploiement ; le guide du webhook couvre les évènements en temps réel. Toutes les captures ont été refaites (clair et sombre, outils de console compris) avec `tools/make_screenshots.py` et des données inventées.

### Modifié

- **Réglages** : nouveaux sous-onglets pour lectures et cache, notifications, analytique, le linter et la vue terminal ; les sous-onglets IA et webhook ont toutes leurs options.

### Corrigé

- **Le linter ne crie plus au loup sur les valeurs de remplissage** : une valeur qui ressemble à un secret est classée (un format de jeton connu ou une longue chaîne à forte entropie est grave, un remplissage lisible comme `placeholder` ou `changeme` n'est qu'une information, tout le reste un avertissement ; les références et les valeurs vides ne sont pas une trouvaille) et sa valeur n'est jamais affichée ni stockée.
- **Un navigateur qui ferme ou recharge son onglet pendant le chargement de la page n'affiche plus de traceback** (`ConnectionAbortedError`, `ConnectionResetError`, `BrokenPipeError`) : ils sont comptés dans `ghamon_client_disconnects_total` ; une vraie erreur est toujours montrée.

### Sécurité

- Le webhook entrant reste désactivé par défaut, sur `127.0.0.1`, avec un HMAC obligatoire.
- Les secrets des notifications vivent seulement dans des variables d'environnement ; les hôtes sont fixes ; les notifications n'écrivent jamais sur GitHub.
- Actions de l'IA : en exécuter une demande son propre interrupteur et une confirmation de la commande complète à chaque fois, seulement sur des cibles que le moniteur surveille déjà, avec une limite par heure, un journal local et un verrouillage après deux échecs de suite.

## [1.5.2]

### Ajouté

- **L'onglet Réglages est organisé en sous-onglets**, ordonnés du courant à l'avancé (Ce navigateur, Général, Actualisation et limites, Sentinelle, Contrôles de surface A10, Préparation A11, Dossiers et fichiers, Sorties, IA externe, Webhook entrant). Dans un sous-onglet, les réglages sont dans des blocs titrés dont le premier champ est l'interrupteur principal (le reste du bloc est estompé tant qu'il est désactivé). Chaque champ montre son unité et sa plage, un badge (redémarrage nécessaire / s'applique tout de suite), un badge pour les options de sécurité qui démarrent dans leur état conservateur et une ligne d'aide. Une zone de recherche filtre tous les sous-onglets, chaque sous-onglet compte ses modifications non enregistrées, Enregistrer et Annuler restent visibles, les flèches, Début et Fin se déplacent entre les onglets et le navigateur retient le dernier sous-onglet utilisé.
- **Tous les réglages du fichier de configuration sont désormais dans la page** : les contrôles A10 (un interrupteur par contrôle et ses limites), les poids du score de santé de l'écosystème, les sources des versions épinglées, les plafonds de minutes Actions, les fichiers requis, les motifs de fichiers d'audit, la période chaude de la sentinelle, la règle d'échantillon inconnu de A2, les préfixes de candidats, la liste des dépôts et l'interrupteur du webhook entrant.
- **File de signature par confiance** : chaque ligne dit `verified`, `unknown` ou `failed` ; l'onglet Sentinelle a un filtre Signature avec le nombre de chaque sorte ; `read_report.py --sign-trust` filtre la liste de la console et l'export, et les lignes exportées portent `trust`.
- **Pastilles de préparation dans l'en-tête** : une pastille colorée par écosystème avec son score de santé.
- **Un tableau Grafana minimal** (`red_by_ecosystem.json`) et un test qui vérifie chaque métrique des deux tableaux par rapport à ce que sert `/metrics`.
- Nouveau guide `WEBHOOK` (mode actualisation seule) et un exemple commenté des sources d'épinglage, en huit langues.
- `tools/make_settings_doc.py` écrit le tableau des réglages des guides à partir du schéma et des textes de la page, et la CI le vérifie.

### Modifié

- **Le rapport du jour regroupe les suggestions de fermeture d'issues** en une ligne par dépôt (le moniteur ne ferme toujours rien).
- **Le contrat du tableau de bord du profil** est documenté et vérifié par un test (`/api/outputs/dashboard.json` est exactement le document de `ci_red.json` ; l'export public ne porte jamais le côté signature).

### Sécurité

- Le secret partagé du webhook n'est jamais affiché dans la page : elle dit seulement s'il est défini.

## [1.5.1]

### Ajouté

- **La page des réglages peut configurer l'IA externe de la sentinelle** (groupe « IA externe pour la sentinelle ») : `ai.provider` (`none` / `ollama` / `openai-compatible`), `ai.model`, `ai.ollama_url` (cet ordinateur seulement), `ai.base_url` (https seulement), `ai.api_key_env` et `ai.daily_limit`. Désactivée par défaut ; un service extérieur reçoit des données de vos dépôts.
- **`migrate_state.py`** : amène aux nouveaux noms les fichiers écrits avant la 1.5.0 (évènements, historique des rapports, candidats de version, enregistrements de lots, le réglage `report_history_days`). Un essai à blanc par défaut ; `--apply` copie et garde les anciens, `--move` les renomme ; rien de ce qui existe n'est écrasé. Guide d'une page dans `docs/MIGRATING.md`, en huit langues.
- **`--init-catalog`** crée des `ecosystems.json`, `targets.json` et `profiles.json` modifiables à partir des exemples.
- Un test s'assure qu'aucun document n'envoie le lecteur vers une commande renommée en 1.5.0 (seuls les tableaux des anciens et nouveaux noms et les guides de migration peuvent les nommer).
- La version dans chaque README.

### Modifié

- **Premier démarrage sans fichiers de catalogue à soi** : la console dit que les fichiers d'exemple sont utilisés.
- Python 3.11 ou plus récent est le minimum documenté (testé sur 3.11 et 3.13 sous Windows, Linux et macOS).

### Sécurité

- Seul le NOM de la variable d'environnement qui contient la clé de l'IA peut être indiqué : la clé elle-même n'est jamais affichée ni enregistrée.

## [1.5.0]

**Avis de mise à jour (à lire d'abord).** Plusieurs fichiers et réglages ont maintenant des noms anglais. Rien n'est perdu : les anciens noms sont encore LUS là où un fichier écrit par une version antérieure peut exister, et les nouveaux noms sont les seuls écrits.

| Avant la 1.5.0 | Depuis la 1.5.0 |
|---|---|
| `leer_parte.py` | `read_report.py` |
| `eventos.py` | `events.py` |
| `parte_history.py` | `report_history.py` |
| `LOTE_GITHUB_ACTIONS.bat` / `.sh` / `.command` | `BATCH_GITHUB_ACTIONS.bat` / `.sh` / `.command` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` (copiez-les ou renommez-les pour garder l'historique des évènements) |
| `PARTE_CENTINELA_DIA_<day>.txt/.json` (historique des rapports) | `SENTINEL_REPORT_DAY_<day>.txt/.json` (les anciens sont encore lus) |
| `PARTE_CENTINELA_<time>.txt` (rapport enregistré) | `SENTINEL_REPORT_<time>.txt` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_<time>.json` | `<signed_dir>/batches/batch_<time>.json` (les anciens enregistrements sont encore lus) |
| `parte_history_days` (réglage) | `report_history_days` (l'ancien nom est encore lu) |
| `monitor_y_centinela.zip` et dossier | `github_actions_monitor.zip` et dossier ; `LEEME_CORREO.txt` devient `README_MAIL.txt` |
| A8 cherchait `RECONCILIACION_TOTAL_AUDITORIAS_*.txt`, `MAPA_DE_RONDAS_*` | les noms sont `sentinel.audit_files` (valeurs neutres par défaut `RECONCILIATION_TOTAL_*.txt`, `ROUNDS_MAP_2*.txt`, `ROUNDS_MAP_EXTRA_*.txt`) ; indiquez-y les vôtres |
| `ci_red.json`, son schéma et les fichiers de `--export-status` | inchangés (ils sont un contrat) |

- **Anglais par défaut.** La langue du système ne décide plus : les outils démarrent en anglais tant que vous n'en choisissez pas une autre dans l'onglet Réglages, avec `language` dans `actions_monitor.json`, `MONITOR_LANG` ou `--lang`.
- **Un paquet propre et neutre.** `ecosystems.json`, `targets.json` et `profiles.json` ne font plus partie du paquet : seuls les fichiers `*.example.json` voyagent, et un fichier par défaut absent retombe sur son exemple. Vos propres fichiers vivent où vous voulez et sont nommés par `ecosystems_file`, `targets_file` et le nouveau `profiles_file` ; le dossier de vos outils de signature locaux est le nouveau `tools_dir`. Les tests utilisent leurs propres données (`tests/fixtures`).
- **Onglet Réglages.** Un nouvel onglet modifie les valeurs de `actions_monitor.json` depuis la page : une liste blanche de clés avec leur type et leur plage, une requête refusée en bloc quand une valeur est invalide, une copie du fichier précédent dans `config_backups/` avant chaque enregistrement (les dix dernières sont gardées), une écriture atomique, seulement sur 127.0.0.1 avec les mêmes contrôles d'Host et d'Origin que tout autre point d'accès, JSON seulement. Les jetons, secrets, clés de signature et la commande de la sentinelle ne sont pas dans la liste : ils ne sont jamais affichés ni écrits, et toutes les autres clés du fichier sont conservées telles quelles. Chaque réglage dit s'il demande un redémarrage. Le sélecteur de langue, le thème et la vue dense y ont déménagé.
- **Boutons et icônes.** Les boutons ont du relief, s'éclairent au survol et s'enfoncent quand on appuie ; les boutons d'icône sont du SVG en ligne avec un nom accessible et une infobulle dans les 8 langues. Les couleurs, la typographie, les cartes, les barres et l'anneau suivent le tableau d'état du dépôt du profil.
- **De la vie dans les graphiques.** Les barres poussent à l'apparition, ce qui est rouge ou en cours a une pulsation discrète, les chiffres de l'en-tête comptent vers le haut, survoler une barre la met en valeur et donne son texte en infobulle, les largeurs changent en douceur ; tout s'arrête avec `prefers-reduced-motion`.
- **Sorties pour d'autres outils (désactivées par défaut, 127.0.0.1 seulement, aucun nouveau jeton).** `/metrics` au format Prometheus (workflows rouges par écosystème et dépôt, séries et heures de rouge, builds en attente de signature, A10 en pause, quota restant, instantané incomplet...), `/api/outputs/grafana.json` pour la source JSON / Infinity de Grafana et `/api/outputs/dashboard.json` (le document `ci_red.json`) pour le tableau d'état. Un tableau Grafana importable est dans `docs/grafana/` et les détails dans `docs/OUTPUTS.md`.
- **Rapport :** une ligne (code `tag_vs_manifest`) quand une étiquette de version devance la version du manifeste ; le chiffre des non signés est ordonné par l'attente la plus longue et dit combien ; le panneau du dépôt suggère la commande `gh issue close` (jamais exécutée) pour une issue d'échec dont le workflow est redevenu vert ; le profil de lot `hil` est documenté dans `profiles.example.json` ; tests pour `finalize` et pour `monitor_link`.
- **Docs :** `docs/SETTINGS.md`, `docs/OUTPUTS.md`, README et QUICKSTART dans les 8 langues mis à jour, captures faites avec des dépôts inventés.

## [1.4.5]

- **Le rapport dit quand l'instantané est incomplet :** une ligne au code stable `incomplete` (chargement en cours, pas d'espace de travail local, erreurs de lecture) juste après le titre, pour que personne n'agisse sur une liste à moitié lue de dépôts rouges ou de file de signature.
- **Résumé de signature :** une ligne indiquant combien de versions attendent d'être signées (vérifiées / non contrôlées / contrôle échoué) et combien de builds sont volontairement sans signature, pour ne pas confondre « non signé volontairement » et « signature manquante » (code `sign_summary`).
- **A10 en pause à cause du quota est dit dans le rapport** (code `a10_paused`) avec le quota restant et nécessaire, et les trois réglages qui le commandent.
- Textes dans les 8 langues ; tests des trois lignes.

## [1.4.4]

- **L'auteur et la licence sont toujours visibles :** le panneau web a un pied de page avec l'auteur et la licence, `read_report.py --version` et le nouveau `gha_dispatch_all.py --version` les impriment sous la version, et le moniteur imprime la même ligne au démarrage. Le texte est dans les 8 langues (`ui.about`) ; l'auteur et la licence viennent de `tool_version.py`.
- **Le pont vers le tableau de bord, par écrit :** `docs/CI_RED_BRIDGE.md` dit ce que contient `ci_red.json` (schéma 2, `complete`), comment l'exporter et ce qu'un lecteur doit vérifier ; le moniteur ne pousse ni ne valide toujours rien.
- Tests de la ligne d'auteur dans les 8 langues, du pied de page, des deux options `--version` et de la ligne de démarrage.

## [1.4.3]

- **Un workflow qui ne tourne que sur les pull requests ne rend plus A2 non concluant :** `pull_request` et `pull_request_target` rejoignent les évènements dont les exécutions ne sont jamais sur la branche par défaut (comme `workflow_dispatch`, `release` et `workflow_call`), si bien qu'un workflow tel qu'un contrôle d'intégration de contrat qui ne tourne que sur les pull requests ne se voit pas réclamer une dernière exécution sur main. Un workflow qui a aussi `push` ou `schedule` compte toujours. Tests des deux cas.

## [1.4.2]

- **A2 ne compte plus une exécution en cours ni une annulée comme vue :** en résolvant un workflow caché, la sentinelle demande désormais les dernières exécutions terminées de ce workflow sur la branche par défaut (`gh run list -w <fichier> --branch <défaut> --status completed -L 10`, lecture seule) et prend la première avec une vraie conclusion. Une exécution annulée ou ignorée (et toute exécution sans conclusion) est écartée, si bien qu'elle ne peut plus masquer un rouge antérieur ; un workflow sans exécution terminée avec conclusion sur la branche reste non concluant à lui seul. Même barrière de quota, même limite d'appels et même cache qu'avant.

## [1.4.1]

- **A2 résout un workflow caché au lieu d'abandonner tout le dépôt :** quand un dépôt a un échantillon complet d'exécutions et qu'un workflow de son clone (un qui peut tourner sur la branche par défaut) y manque, la sentinelle demande à GitHub la dernière exécution de CE workflow sur la branche par défaut (`gh run list -w <fichier> --branch <défaut> -L 1`, lecture seule). Une réponse rouge compte comme rouge dans A2 ; une verte retire le workflow de la liste des non concluants ; un workflow sans exécution sur la branche reste non concluant à lui seul et le panneau le nomme (`repo/fichier.yml (aucune exécution sur la branche par défaut)`) au lieu de ne nommer que le dépôt. Sans quota (même barrière que A10 : `min_rate_remaining` x `surface.min_rate_factor`, plus le budget horaire) le workflow reste non concluant et le panneau dit pourquoi. Nouvelles options `sentinel.a2_resolve_max_calls_per_tick` (4 ; 0 = ne jamais demander) et `sentinel.a2_resolve_ttl_seconds` (3600, combien de temps une réponse est gardée ; elle est aussi enregistrée dans le fichier de cache). L'instantané porte `a2.inconclusive_workflows` (étiquettes) et `a2.inconclusive_details` ; `a2.inconclusive` reste la liste des dépôts. 5 nouveaux textes dans les 8 langues et un `ui.a2_inconclusive` reformulé.

## [1.4.0]

- **Nouvelle couche A11 « Préparation » (lecture seule, données réelles seulement) :** un panneau de l'onglet Sentinelle, un feu tricolore dans son en-tête et deux lignes du rapport. Elle s'active avec `sentinel.readiness.enabled` et se décrit dans `readiness.py`.
  - **Préparation de version :** une ligne par dépôt ayant au moins `candidate_min_entries` entrées dans `[Unreleased]` (écosystèmes externes exclus) : la CI de la branche par défaut (la règle unique de A2) avec le commit sur lequel elle a tourné, si la version que le clone déclare (`*.project.json`, sinon `pyproject.toml`, sinon le premier titre du CHANGELOG) dépasse déjà la dernière version publiée, s'il existe un build postérieur à cette version, s'il est signé (les états de A5) et l'étape suivante (`corriger la CI rouge`, `attendre les données d'exécution`, `monter la version`, `compiler dans Actions`, `signer`, `publier`, `couper et publier`). Une CI verte sur un échantillon d'exécutions complet qui peut cacher un workflow plus ancien le dit.
  - **Santé de l'écosystème :** par écosystème, 100 moins des comptes pondérés de CI rouge, builds bloqués, secrets, alertes graves, autres alertes, PR Dependabot plus vieilles que `stale_pr_days`, builds en attente de signature et dépôts avec des problèmes d'hygiène (`sentinel.readiness.health.weights`) ; les éléments qui font baisser le score sont listés. Aucun score n'est affiché (`?`) quand moins de `min_coverage` (0,5) des dépôts de l'écosystème ont des données d'exécution et d'alertes. Le rapport avertit quand un score est sous `warn_below` (70).
  - **Épinglages de dépendances :** dépôts qui épinglent une version plus ancienne que celle du dépôt fournisseur du contrat ou de la bibliothèque. L'endroit où vivent les épinglages est une donnée (`sentinel.readiness.pins.sources`) : une table JSON d'épinglages chez le fournisseur (`pin_table`) ou des fichiers de verrouillage chez les consommateurs (`lock_files`, le plus ancien trouvé compte). Simples lectures de fichiers des clones locaux, en cache `pins.refresh_seconds` ; un écosystème sans source configurée est listé comme n'en ayant aucune, et rien n'est deviné. L'exemple fourni n'a pas de source.
  - 60 nouveaux textes dans les 8 langues ; `tests/test_readiness.py` (règles, poids, couverture, épinglages sur un arbre temporaire, la page et les 8 catalogues).
- **`docs/CI_RED_SCHEMA.md` :** dit explicitement que le PC ne publie ni `ci_red.json` ni `pending_sign` vers aucun dépôt ni tableau de bord (le côté signature est local par décision) ; un consommateur public recalcule la règle à partir des exécutions publiques ou utilise `read_report.py --export-status`.
- **Réglage du quota d'après le journal (`actions_monitor_log.txt`, 3 jours, 889 mesures) :** le quota partagé était sous le seuil (`min_rate_remaining` 1500) dans 11 % des mesures depuis le 5 novembre et sous 3000 dans 45 % ; la consommation horaire était de 3000 à 5000 appels la plupart des heures et atteignait la limite certaines heures. Dans le `actions_monitor.json` du mainteneur : `refresh_seconds` 120 -> 180 (le cycle réel avait une médiane de 139 s) et `sentinel.surface.min_rate_factor` 2,0 -> 1,5 (les appels à froid de A10 sont d'environ 260 par jour, ils peuvent donc passer au-dessus de 2250 ; avec 3000 ils attendaient presque la moitié du temps). `max_repos_per_tick` (6) et le cycle quotidien à froid restent : ils coûtent moins de 1 % du quota. L'exemple fourni garde ses valeurs neutres par défaut.

## [1.3.3]

- **A2 ignore les workflows qui ne tournent jamais sur la branche par défaut :** pour décider si un échantillon complet d'exécutions cache un workflow, les fichiers du clone dont le `on:` n'a ni `push`, ni `pull_request`, ni `schedule` pour la branche (seulement `workflow_dispatch`, `release`, un `push` d'étiquettes seul sans `branches`, ou `workflow_call`) ne sont plus attendus dans l'échantillon. `on:` est lu avec la seule bibliothèque standard (chaîne, liste, table, et la clé YAML `true`) ; s'il ne peut pas être analysé, le workflow compte comme avant. L'analyse des workflows porte le nouveau champ `main_triggered` (`true`/`false`/`null`).

## [1.3.2]

- **A2 montre `unknown` au lieu de vert quand son échantillon est plein et non concluant :** un dépôt dont la liste d'exécutions est aussi longue que l'échantillon demandé (`runs_per_repo` / `cold_runs_per_repo` du moniteur, que le contrôle ne voyait pas avant) et dont le clone a un fichier de workflow sans exécution dans cet échantillon (ou n'a pas de clone) est listé comme non concluant, et A2 est `unknown` sauf si quelque chose est rouge. Nouvelle option `sentinel.a2_full_sample_unknown` (par défaut `true` ; `false` = seulement informatif comme avant). La page liste les dépôts.
- **`profiles.example.json` :** un modèle neutre de profils de lot qui correspond à `targets.example.json` et `ecosystems.example.json`. Un test (et la barrière de version) le valide contre ces catalogues, pas ceux du mainteneur, et vérifie que chaque profil sélectionne au moins une cible.
- **Contrôle d'installation propre dans `make_release` :** avant de laisser quoi que ce soit dans le dossier de sortie, le zip est extrait dans un nouveau répertoire temporaire vide et, de là avec `python -I`, chaque membre doit être présent, chaque module compiler, `read_report.py --version` fonctionner et toute la suite passer ; tout manque fait échouer la version.
- **Formulation :** README et QUICKSTART dans les 8 langues disent désormais que le paquet n'écrit rien sur GitHub de lui-même et que seuls `dispatch --go`, `dispatch --real` et `finalize --execute` (que vous lancez) le font.
- **Quota de A10 :** la part du budget d'appels par cycle de la sentinelle que A10 peut utiliser est désormais `sentinel.surface.budget_share` (par défaut `0.5`, comme avant mais configurable) ; la page affiche « A10 en pause pour le quota » avec le quota restant et celui qui est nécessaire (`min_rate_remaining` x `min_rate_factor`) pendant que les appels à froid attendent.

## [1.3.1]

- **Une exécution construite sur un autre commit n'est jamais proposée à la signature :** quand `dispatch` n'a pu trouver qu'une exécution récente d'un autre commit (`sha_matched` faux), `finalize` la liste désormais comme non prête avec la raison et ne donne aucune commande de signature ; un ancien lot sans ce champ se comporte comme avant. Tests avec deux exécutions concurrentes de commits différents.
- **`/api/data` passe par la même garde Host/Origin que les autres routes** du serveur local (DNS rebinding).

## [1.3.0]

Conçue pour être partagée : huit langues, paternité et licence dans chaque fichier, aucune donnée privée et rien lié à un compte GitHub.

- **8 langues** (en, es, de, fr, it, ja, zh, pt = portugais du Portugal) pour la page, les outils en ligne de commande, les lanceurs, les évènements, les rapports et les messages d'erreur. `i18n.py` + `locales/<langue>.json` (un catalogue plat par langue, bibliothèque standard seulement, `t("clé", nom=valeur)` avec repli sur l'anglais). La langue est `language` dans `actions_monitor.json` (par défaut : la langue du système, l'anglais si elle n'est pas prise en charge), un sélecteur dans l'en-tête de la page (le navigateur s'en souvient), `MONITOR_LANG` / `JUANENRAC_LANG`, ou `--lang CODE` dans chaque outil (il l'emporte sur le reste). Les noms techniques, commandes, chemins et les marqueurs que lisent les scripts (`SKIP`, `DISPATCHED`, `READY`, `FAILED`, `Summary:`, `BUILD ONLY`, `WOULD DISPATCH`...) ne sont jamais traduits. Les évènements de `events_monitor.jsonl` portent désormais un `code` stable (et `args`) à côté du texte, pour que personne n'ait à analyser une langue.
- Un test vérifie que les 8 catalogues ont exactement les mêmes clés, aucune vide, les mêmes `{marqueurs}`, que chaque clé utilisée par le code et la page existe et qu'aucun texte visible du code ne contourne `t()`.
- README et QUICKSTART dans les 8 langues (`README_<langue>.txt`, `QUICKSTART_<langue>.txt`) ; `README.txt` est désormais un court sélecteur de langue avec le démarrage rapide.
- **Paternité et licence** : chaque fichier source porte « Copyright (C) 2026 JuanenRac (Electro Hobby 3D) » et « GPL-3.0-or-later - see LICENSE » ; les fichiers de données JSON portent `_author` / `_license` ; `LICENSE` (texte de la GPL-3.0), `NOTICE` et `AUTHORS` voyagent dans le zip. `make_release.py` refuse de construire quand un fichier en manque, quand des données privées voyageraient, quand les locales diffèrent ou quand un lanceur perd son bit d'exécution.
- **Partageable** : `github_owner` dans la configuration (par défaut : le compte de `gh`) remplace la constante qui était répartie dans trois modules ; les préfixes d'écosystème et les outils de signature sont des données (`ecosystems.json`, neutre `ecosystems.example.json` ; `"*"` = tous les dépôts ; `"external": true` = seulement signalé) et les cibles aussi (`targets.json` est le vrai catalogue du mainteneur, `targets.example.json` le neutre ; `targets_file` / `ecosystems_file` les choisissent ; les clés qui commencent par `_` sont des métadonnées). La configuration d'exemple est neutre. Rien de cela n'ajoute d'appel au cycle chaud.
- **L'espace de travail est facultatif** : sans clones locaux, le moniteur démarre en mode réduit (seulement ce que donne l'API GitHub : pas de file de signature locale, pas de rapport d'audits, pas d'analyse du CHANGELOG) et le dit dans la page, dans le rapport et au démarrage, au lieu de s'arrêter. `MONITOR_ROOT` / `MONITOR_AUDIT_DIR` / `MONITOR_SIGNED_DIR` et `signed_dir` ont été ajoutés à côté des anciens noms. La couche de feuille de route (A9) est facultative aussi.
- Lanceurs : les menus et messages viennent de `launcher_msg.py` (votre langue) ; commentaires en anglais ; en-tête dans chaque fichier.
- Correction : `workspace_root()` ne termine plus le moniteur quand la sentinelle démarre sans espace de travail.

## [1.2.0]

Ce qui manquait et ce qu'on peut faire d'autre sur GitHub, le tout en lecture seule et local.

**Partie A - ce qui manquait**
- Le schéma 2 de `ci_red.json` est désormais un contrat documenté : `docs/CI_RED_SCHEMA.md` (forme, la règle unique du « rouge », ce qui est réservé au propriétaire). Rien n'est publié depuis le PC. Exports facultatifs et explicites (jamais un commit ni un push) : `read_report.py --export-status DIR` écrit SEULEMENT la liste rouge (`ci_status_public.json/.md`) ; `read_report.py --export-sign-queue FILE` (.json/.csv) écrit la file de signature globale avec les commandes locales.
- Attestation : la file de signature montre si le build a une attestation (existence par empreinte des fichiers signés, une requête par entrée, sans vérification de signature ; interrupteur `sentinel.surface.checks.attestation`). Une absente est une ligne du rapport.
- Plus de formats vérifiés : HYDRA `hydra-sign` (`FICHIER.sig` = Ed25519 en base64 sur les octets du fichier, la clé de version épinglée, lu par blocs) est vérifié définitivement ; URTC `.imgsig` a son format strict vérifié (152 chiffres hexadécimaux + LF ; mal formé = invalide) et reste « unknown » quand il est bien formé (le message signé demande aussi l'en-tête du build, que le dossier des signés ne porte pas) ; les APK d'ARMOR sont signés dans l'APK par apksigner et restent « unknown ».
- `HYDRA-UMC-OS` est étiqueté volontairement dans `targets.json` (`"build_only": true` + `reason`) : `plan` le liste sous BUILD ONLY et il n'est plus orphelin. Les outils de signature n'ont pas été touchés (son workflow prend d'autres entrées et un autre schéma de signature).
- Correction : `ci_red.target_path` refusait tout chemin Windows écrit avec des barres obliques inverses (`C:\...`) ; seules les barres obliques normales étaient acceptées.

**Partie B - la couche A10 « surface Actions et versions »** (`surface.py`, nouvelle section de l'onglet, un interrupteur et un seuil par contrôle sous `sentinel.surface`)
- Actions : workflows désactivés à la main, planifications sans exécution depuis N jours (seulement quand l'échantillon d'exécutions couvre la fenêtre), `uses:` non épinglés par SHA (les workflows réutilisables signalés à part), `permissions: write-all`, `pull_request_target` avec checkout de la PR, files de concurrence bloquées, échecs sur un seul OS d'une matrice, coût et rétention des artefacts, contrôles d'état requis rouges ou absents (GraphQL), `dispatch --profile release|nightly|hil` avec un canari (la première cible seule, les autres seulement si elle est verte) et une barrière de quota (`--min-rate`, échoue fermée). Les profils vivent dans `profiles.json`.
- Versions : actifs attendus par type de cible (alerte quand une version a été publiée incomplète), étiquette contre manifeste contre CHANGELOG, GitHub Packages, brouillons et préversions oubliés, `release_notes.py` (un BROUILLON de notes d'après les commits depuis la dernière étiquette ; il ne publie rien).
- Sécurité : alertes critiques/hautes par ancienneté avec un classement des dépôts, couverture (une pile sans CodeQL/Dependabot), analyse des secrets ouverts contre résolus, Dependabot par priorité (majeures de runtime d'abord, CI seule en dernier).
- Issues et PR : suggestion de `gh issue close` pour les issues de build dont la CI est redevenue verte (un évènement avec le texte ; rien n'est jamais fermé), jalons en retard, vieilles PR humaines, PR qui touchent des workflows ou CODEOWNERS, la file de fusion (approuvées avec contrôles verts). Cartes de tableau périmées : EN ATTENTE (demande des lectures par élément et un seuil).
- Manifeste contre preuve (maturité), échecs de parité du README en 8 langues, minutes Actions par écosystème dans l'en-tête, le rapport et A7.
- `finalize --execute` dit désormais au moniteur en marche (127.0.0.1) de rafraîchir juste les dépôts signés et de réécrire `ci_red.json` aussitôt (`monitor_link.py`).
- Récepteur facultatif de webhook signé (`webhook.enabled`, désactivé par défaut, 127.0.0.1 seulement, HMAC avec un secret partagé de la configuration, jamais un jeton GitHub).
- Coût : rien dans le cycle chaud. À froid, réparti sur les cycles et dans le budget horaire : 2 appels REST par dépôt et par jour, une requête GraphQL par 15 dépôts et par jour, 3 pour Packages, plus les jobs des exécutions rouges et les requêtes d'attestation de la file de signature, et seulement tant que le quota dépasse le double de `min_rate_remaining`. Le passage GraphQL chaud demande 3 champs de plus par nœud (dates d'alertes, décision de revue, état des contrôles) : aucun appel en plus.
- La barrière compare aussi `sentinel.surface` du fichier d'exemple avec les valeurs par défaut et valide `profiles.json`.

## [1.1.1]

- **Multiplateforme :** le moniteur et les outils de lots fonctionnent sous Windows, macOS et Linux. Lanceurs `MONITOR_GITHUB_ACTIONS.sh`/`.command` et `BATCH_GITHUB_ACTIONS.sh`/`.command` (le zip garde la permission d'exécution et make_release rejette les fins de ligne Windows dedans).
- Nouveau `platform_compat.py` : la commande qui démarre un outil enfant (`py -3` sous Windows, l'interpréteur courant ailleurs), le texte des commandes que montre `finalize` (guillemets cmd/PowerShell ou POSIX), console UTF-8 et un avis avec la façon d'installer `gh` sur chaque système.
- Nouveaux tests de la partie multiplateforme (Windows et POSIX simulés depuis n'importe quel système).

## [1.1.0]

Confiance dans les signatures, un pont stable vers le tableau de bord, orphelins et conventions dans les outils de lots, et une page plus utile.

- Confiance dans la signature : `sigverify.py` (bibliothèque standard, lecture seule, sans réseau) vérifie le dossier des signés `_firmados/<REPO>/release-<version>/` contre la clé PUBLIQUE que chaque écosystème épingle (URTC `release_sign.py`, l'assistant ARMOR `PACKAGE_PUBLIC_KEY`, l'updater HYDRA `RELEASES_PUBLIC_KEY`, ou `sentinel.signature_pubkeys`). Chaque état porte désormais `signature_kind` (none | dev | release) et `signature_verified` (true | false | "unknown") ; seule une signature de version qui se vérifie (`trusted`) abaisse l'alerte de signature en attente, en plus de « publié ». Une signature qui ne se vérifie pas garde l'alerte et le dit dans le rapport. `sentinel.require_verified_signature` (par défaut true ; false = la règle de la 1.0.0). Les formats que ce module ne peut pas vérifier (.sig2, .hdr2, .imgsig, APK, hydra-sign) sont « unknown », jamais « false ». L'attestation du build demande toujours le réseau et reste aux outils de signature.
- Schéma 2 de `ci_red.json` : par dépôt une liste `pending_sign` (workflow, heures, état, signature_kind, signature_verified, last_build_at, url) à côté des workflows rouges, plus `schema`, `pending_sign_repos` et le seuil ; le format est documenté dans `ci_red.py` et n'est qu'étendu.
- Une seule définition de « dernière exécution sur main » (`signstate.completed_runs`) partagée par le contrôle du rouge, celui du vert sans version et les états des cibles.
- `ci_red.target_path` refuse les chemins D:, les formes WSL/Git Bash de D: et les chemins de lecteur/UNC que le système en marche ne peut pas utiliser ; les tests simulent les deux systèmes et toute la suite passe désormais sous Linux.
- `gha_dispatch_all.py plan` se termine toujours par la section « Orphelins de signature » (CI verte + `*-build.yml` connu + pas de cible) ; la couverture est par dépôt ET workflow.
- Convention pour les cibles (préfixe d'écosystème -> outil de signature par défaut, workflow dans la liste connue) ; `targets.json` ne contient que les exceptions et l'emporte toujours. `hygiene --write-candidates` écrit les entrées proposées dans `targets.candidates.json` (jamais appliquées d'elles-mêmes, jamais empaquetées).
- Page : compteurs d'en-tête cliquables « rouge sur main » et « non signé » (ils filtrent les dépôts ; le second met aussi en avant la file de signature), la file de signature avec ses commandes et un bouton de copie, panneau du dépôt avec construit / signé / publié, type de signature et vérification, et la commande suggérée ; un badge dans l'en-tête quand un budget de minutes atteint 80 % (rouge s'il est dépassé) ; « hier contre aujourd'hui » compare aussi les avertissements de budget et les lignes du rapport.

Non fait : lire l'attestation du build / SBOM (réseau) ; `HYDRA-UMC-OS` a un workflow de build mais son outil de signature ne le prend pas encore en charge (listé comme orphelin).

## [1.0.0]

Première version numérotée. Ce que fait le paquet :

- Moniteur de GitHub Actions pour les quatre écosystèmes (page web locale, cache des exécutions, builds bloqués, issues build-failed/build-stuck).
- Couche A de la sentinelle (lecture seule, sans IA) : A1 builds bloqués, A2 CI rouge (un seul critère : la dernière exécution terminée de chaque workflow sur la branche par défaut), A3 alertes CodeQL/Dependabot/secrets, A4 pull requests Dependabot, A5 versions (candidates, builds verts sans version, signature en attente), A6 hygiène, A7 consommation (minutes et quota de l'API), A8 audits et tournées, A9 tableaux de feuille de route.
- État explicite de chaque cible de build : built_on_gha -> signed_local (none | dev | release) -> published, avec `last_build_at`, `last_signed_at`, `signature_kind` et les heures réelles d'attente ; les enregistrements locaux de lots et du dossier des signés abaissent l'alerte de signature en attente sans attendre GitHub.
- File de signature du jour (`a5.sign_queue`) : le plus urgent d'abord, avec la commande finalize exacte de chaque cible.
- Budget de minutes Actions par écosystème (`sentinel.minutes_budget`, vide par défaut) : avertissement à 80 % dans le rapport et comme évènement.
- Flux d'évènements (`events_monitor.jsonl`) et `ci_red.json` (dépôt -> workflows rouges + heures en attente de signature), écrits de façon atomique.
- Outils de lots : `gha_dispatch_all.py plan|dispatch|status|finalize|hygiene` avec `--only` ou `--ecosystem`, `plan --json`, `finalize --json`, une nouvelle tentative d'un dispatch échoué à la fin du lot, cibles en données dans `targets.json`.
- `read_report.py` : le rapport en texte brut depuis le moniteur en marche, sans consommer de quota d'API.
- `make_release.py` : barrière de qualité (tests unitaires, zip propre, configuration d'exemple complète, accord version/changelog) et SHA256SUMS.

Non fait dans cette version : vérifier les signatures des versions contre la clé publique et l'attestation du build depuis la sentinelle (formats de signature différents par écosystème ; l'attestation demande le réseau ; les outils de signature vérifient les deux avant de publier).

