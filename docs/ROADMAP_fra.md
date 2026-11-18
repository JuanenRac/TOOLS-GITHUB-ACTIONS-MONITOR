# Feuille de route

Ce qui est publié, ce qui vient ensuite et ce qui n'est qu'une idée, dans cet ordre de certitude. Ce sont des directions, pas des engagements ; une issue ou une pull request est le meilleur moyen d'en faire avancer une.

## Où en est le moniteur

Version 2.0.2. L'édition lite montre ce qui tourne et ce qui a échoué. L'édition complète ajoute trois sentinelles (CI, Collab et Security), une liste d'alertes, plusieurs comptes et une équipe avec des rôles, la note de chaque compte, la santé de chaque dépôt et de l'équipe, des rapports programmés, un journal des actions, des notifications (ntfy, Teams, e-mail et Apprise), un assistant d'IA facultatif avec des préréglages de services compatibles, le mode service avec Docker et une page pour toutes les tailles d'écran, du téléphone à la 4K.

## Prévu, dans cet ordre

Chaque version ne porte que du contenu réel : une version sans rien de réel à ajouter est sautée et jamais publiée vide. Rien ici n'est tenu pour prouvé sur des services réels sauf si son guide le dit.

### 2.0.2 à 2.0.9 - Après le gel

Ce qui n'apparaît qu'à l'usage réel prolongé : la migration depuis la 1.8 et la 1.9, la croissance des événements et de la base de données sur des mois, les sessions après une mise à jour, les volumes Docker, beaucoup de comptes avec trois sentinelles et le mode équipe en même temps, et ce que trouve la suite de contrat. Rien de la quatrième phase (greffons, automatisation étendue, IA avancée) n'entre dans ces versions ; une version sans contenu réel est sautée.

Les workflows du moniteur lui-même respectent ce que la sentinelle d'hygiène demandera aux autres : actions fixées à un commit, permissions minimales et une limite de temps sur chaque job.

## Fait dans la 1.8.2 à la 2.1.3

### 2.1.3 - De l'aide sur chaque réglage, un onglet pour Hier vs aujourd'hui, un menu Mises à jour plus difficile à détourner et des panneaux qui ne se chevauchent plus

L'onglet Réglages affiche une info-bulle sur chaque réglage avec ce qu'il fait, sa plage ou ses valeurs, sa valeur par défaut et ce que fait un interrupteur activé ou désactivé. Hier vs aujourd'hui a sa propre entrée de menu. Le menu Mises à jour se met en pause après une série de tentatives échouées, dit pourquoi une mise à jour est bloquée et ne lit son fichier de progression que si c'est un petit fichier ordinaire ; l'analyseur de workflows coupe les fichiers hostiles, les guides sont vérifiés pour avoir la même structure dans les huit langues et les panneaux repliables des onglets de la Sentinelle ne se dessinent plus les uns sur les autres.

### 2.1.2 - Le moniteur se met à jour depuis un menu, compare une période à la précédente, et les panneaux dépliés atteignent le bas

Le menu Mises à jour (édition Complète) montre la version installée et les versions publiées avec leurs notes, applique une mise à jour avec copie préalable, contrôle du zip par rapport à SHA256SUMS, migration de la configuration et redémarrage, et revient en arrière d'un clic si la nouvelle version ne démarre pas ; l'outil autonome reste le chemin de retour. La comparaison place une période à côté de la précédente, avec des états honnêtes quand un chiffre ne peut pas être dit, un rapport de ce qui a changé, une route, une commande, une section de l'onglet Graphiques et une section facultative du rapport planifié. Les fichiers qu'écrivent plusieurs processus utilisent le verrou du système d'exploitation, le panneau déplié d'un onglet du Sentinelle atteint le bas de sa boîte, démarrer le moniteur depuis l'outil de mise à jour n'ouvre plus une fenêtre de console pour chaque appel à git et gh, et l'image de l'architecture montre ce que le moniteur est devenu.

### 2.1.1 - Deux nouvelles sentinelles, l'une pour la chaîne d'approvisionnement et l'autre pour la livraison, et une porte de release plus stricte

Deux nouvelles sentinelles, désactivées par défaut et seulement dans l'édition Complete, lisent ce qu'un dépôt construit et ce qu'il livre sans rien écrire sur GitHub : celle de la chaîne d'approvisionnement vérifie dans les fichiers de workflow les actions non épinglées, les branches mobiles et les permissions trop larges ou absentes, et celle de la livraison compare les releases, les étiquettes, le changelog, les fichiers de version et les versions épinglées. Le doctor signale désormais en rouge un webhook entrant sans secret, la couverture du webhook ne reste plus en direct quand l'horloge est reculée, et la porte de release compare le contenu de chaque fichier du zip avec le commit, accepte une exécution verte complète d'après le nombre donné par unittest et peut indiquer l'avancement de ses suites.

### 2.1.0 - Écrans muraux avec thème, logo et mode tournant, une sauvegarde restaurable et un outil de mise à jour

Les écrans muraux portent le thème du produit et peuvent afficher le logo de l'organisation ; une fenêtre peut tourner entre les trois écrans et sauter vers un nouveau rouge ; la vue d'ensemble montre la carte de la flotte par groupes ; une mise à jour Dependabot en échec est une alerte à part ; et chaque type d'événement a aussi son son sur cet ordinateur. L'installation peut être copiée entièrement, vérifiée et restaurée, selon un calendrier si vous le souhaitez, le doctor contrôle le fonctionnement avec des codes de sortie qui ne changent pas et une purge peut être lancée à la demande. L'outil de mise à jour amène une installation à n'importe quelle version publiée, la copie d'abord et revient en arrière si quelque chose échoue. La porte de publication nomme les tests en échec et accepte un passage vert déjà vu, les étiquettes d'état des panneaux de détail restent sur une ligne, les liens de la page sont vérifiés en lisant l'adresse et le guide du conteneur explique comment ouvrir la première session.

### 2.0.9 - Un audit indépendant plus sûr, des menus avec groupes, un son par type d'événement et des commandes de chat en lecture seule

L'audit indépendant a durci le moniteur : le jeton d'accès ne circule plus dans l'adresse par défaut, une mise en silence par motif ne fait plus taire ce qui n'est pas un workflow, le nettoyeur de texte attrape plus de formes d'un vrai log, un en-tête avec un secret ne suit jamais une redirection, une livraison du webhook est vérifiée et ne peut pas être rejouée, et un fournisseur sur internet ou à une adresse privée a besoin de son propre interrupteur. Le menu de gauche a des groupes titrés, chaque type d'événement a son propre son, des commandes en lecture seule répondent dans Slack et Discord (désactivées par défaut), les écrans muraux suivent la langue de la page principale et l'IA intégrée a un seul budget qui compte aussi l'avis actif. Le journal des actions peut devenir une condition des actions et garde le nombre de fichiers tournants que vous choisissez, un cycle compte une seule fois pour toutes les étapes de la sentinelle, et un workflow pour l'audit de l'image du conteneur, avec les défauts qu'il a trouvés dans le conteneur, fait partie de la version.

### 2.0.8 - Un secret de webhook plus sûr, des check runs et un guide pour configurer le webhook (la version qui clôt la quatrième phase)

Le secret partagé du webhook entrant ne circule que dans l'environnement (ou dans un fichier que le réglage nomme), le webhook reçoit aussi les événements de check run, la vue En direct dit quelle part du temps les événements couvrent, et un guide en huit langues (`docs/WEBHOOK.md`) configure le webhook dans GitHub pas à pas. Les études de comptes réels ajoutent trois lignes : un workflow dont le fichier a été supprimé n'est pas un workflow activable, un fork jamais poussé n'est pas récemment poussé, et le runner `codspeed` est reconnu comme un runner tiers payant. Les documents ne disent plus que macOS tourne dans le CI. C'est la version qui clôt la quatrième phase : une version de stabilisation avant l'audit.

### 2.0.7 - Une API de lecture pour les clients, le dépôt d'origine de chaque fork et les workflows désactivés à la main

Une API de lecture sous `/api/v1/` pour les clients (`me`, `repos` et `openapi`, désactivée par défaut, avec un contrat figé) ; un suivi facultatif du dépôt d'origine de chaque fork (`upstream.enabled`, désactivé par défaut, avec une limite de requêtes par heure) ; et un workflow que le propriétaire a désactivé à la main n'est plus un rouge mais est présenté à part (`ci.disabled_apart`).

### 2.0.6 - Trois écrans muraux, dessinés et désactivés par défaut

Les trois écrans muraux sont dessinés : Vue générale (score, lampes de la flotte, graphiques, carte de chaleur, runners et le quota), Maintenant (exécutions en cours, file, approbations, échecs récents et une ligne en direct) et Sentinelles (une carte par sentinelle avec un radar animé). La page dessine elle-même chaque graphique, un nouvel échec clignote une fois puis se calme, rien ne bouge pour qui a demandé moins de mouvement, tout se décale un peu chaque minute contre la rémanence, la page peut s'assombrir la nuit, une fenêtre peut tourner entre les trois pages, et un test de navigateur les vérifie en 1080p, en 4K et pivotées dans les huit langues. Les écrans sont désactivés par défaut (`screens.enabled`), et le README et le guide des écrans les montrent désormais.

### 2.0.5 - Moins de faux rouges, des dépôts dormants et des questions visibles en plein écran

Un rouge compte désormais selon l'origine de l'événement : les workflows que GitHub crée pour lui-même (`dynamic/`) ne sont ni du CI rouge ni des fichiers, la recherche d'un workflow caché suit la même règle d'origine, les exécutions en file pendant des jours sont reconnues comme une file fantôme (7 jours par défaut) et un rouge dont personne ne s'occupe vieillit après 30 jours et devient inactif ; les dépôts dormants et inactifs sont un état à part, ni verts ni rouges ; les forks n'entrent dans l'hygiène, le lint et le score que s'ils ont leur propre CI dans les 90 derniers jours ; la protection de la branche par défaut est jugée par défaut sur ce qui est en vigueur, depuis toutes les sources publiques ; et les cinq confirmations de la page utilisent un dialogue de la page visible en plein écran.

### 2.0.4 - Un modèle par tâche, des menus indépendants et une aide qui ouvre le bon sujet

L'IA du moniteur peut utiliser un modèle pour chaque type de tâche, une chaîne de secours quand le modèle principal échoue et un budget pour chaque modèle, le tout désactivé tant que ce n'est pas écrit dans les réglages ; Alertes, Rapports et Leçons sont trois entrées indépendantes du menu, chacune avec son panneau, son badge, son sujet d'aide et son adresse ; l'onglet Historique garde un seul compteur au lieu d'accumuler des copies à chaque rafraîchissement ; le bouton « Aide de cet onglet » ouvre dans chaque onglet le sujet de l'onglet ouvert ; et les tests du navigateur sont ignorés proprement quand le dossier des outils est absent.

### 2.0.3 - Gros comptes, moins de faux rouges, lint sans clones et stockage plus sûr

Une vue de flotte, des listes paginées, un budget de requêtes et une couverture honnête de la liste des exécutions pour les comptes de centaines de dépôts ; un rouge ne compte que si le dépôt lui-même l'a causé, et les exécutions en attente d'approbation, les workflows abandonnés, ceux qui ne réagissent qu'aux issues, la file de fusion et les branches de maintenance ont chacun leur place ; le linter de workflows et les contrôles de surface fonctionnent par l'API ou un clone partiel sans cloner ; les modèles du fournisseur d'IA sont lus et vérifiés, et chaque lien de la page passe par le filtre d'adresses ; les verrous et le journal des actions sont plus sûrs sous Windows et le registre de score n'est jamais écrasé ; des écrans muraux pour un moniteur ou un téléviseur, désactivés par défaut ; les tests du dépôt ne tournent plus sur macOS pour l'instant.

### 2.0.2 - Des journaux plus sûrs, un texte d'IA plus propre et un score plus juste

Tout ce qu'une IA peut lire passe par un seul nettoyeur qui connaît plus de formes de secret, l'assistant intégré garde sa clé et ne suit plus les redirections ni les proxys, le journal des actions est une chaîne dans un fichier par compte et un lecteur ne peut pas le lire, l'image et les processus des comptes ne portent plus de secrets, le score pénalise une panne jamais réparée et ne compte plus une source illisible comme propre, et une longue liste de corrections du stockage, des sauvegardes, de la migration, des vues de terminal et du lanceur.

### 2.0.1 - Empaquetage et une clé manquante

Le zip publié contient désormais le fichier des préréglages d'IA et tout autre fichier de données du paquet, et la porte de publication échoue si l'un manque dans le zip ; la page de tous les comptes n'affiche plus de clé d'état non traduite, et un test vérifie que chaque clé utilisée par la page existe dans les huit catalogues.

### 2.0.0 - Maturité

L'API de lecture et les interfaces publiques sont figées : un fichier de contrat avec les clés et les types de chaque point d'accès en lecture et les codes d'erreur, une suite de tests et un outil qui le vérifient contre n'importe quel moniteur en marche, un test qui fixe les champs d'une alerte et les méthodes d'une sentinelle et d'un stockage, et un guide pour chaque usage (lite, une personne, service, équipe) et pour les clients de l'API, en huit langues. Les versions 1.9.6 à 1.9.9 n'avaient rien de réel à ajouter après les revues de clôture et ont été sautées.

### 1.9.5 - Flux des événements en direct

Un flux des événements en direct du webhook entrant pour les clients et les écrans muraux qui ne peuvent pas interroger, désactivé par défaut, en lecture seule, avec une limite d'écouteurs et une durée maximale pour chacun.

### 1.9.4 - Préréglages d'IA

Un tableau de douze services hébergés et de six serveurs locaux qui parlent un protocole que le moniteur connaît déjà, un sélecteur dans les réglages de l'IA qui remplit l'adresse, le nom de la variable de la clé et un modèle d'exemple, des serveurs locaux qui fonctionnent sans clé et les adresses des principaux services lues dans leur documentation publique.

### 1.9.3 - Rapports programmés et journal d'audit

Des modèles de rapport en HTML et Markdown (PDF facultatif) avec le score, les principales alertes et les changements, un planificateur et un journal d'audit en ajout seul de qui a fait quoi et quand, sans aucun secret dedans. Facultatif, dans la même version : une vue « version prête / bloquée » avec le dernier commit vert de chaque dépôt.

### 1.9.2 - Santé du dépôt et de l'équipe

Une vue de santé de chaque dépôt (CI, tickets et pull requests, sécurité, préparation à une version, activité) et une de l'équipe avec classement, totaux et filtres ; des pages pour les deux avec des liens directs pour écrans muraux. Facultatif, dans la même version : un panneau de benchmarks de nuit face à un budget (médiane face à une référence par classe de machine) et un panneau de nomenclatures logicielles et d'attestations de chaque version.

### 1.9.1 - Sentinelle de sécurité

La troisième sentinelle : Dependabot, analyse de code, analyse des secrets, protection des branches, permissions des workflows et propriétaires du code, avec des règles par type de signal, le même filtre dans l'onglet Alertes et une pénalité dans le score pour les alertes critiques ouvertes. Facultatif, dans la même version : hygiène des workflows (actions non fixées à un commit, jobs sans limite de temps, workflows sans permissions ou sans concurrence, usage dangereux de pull_request_target), sur le vérificateur de workflows que le projet a déjà.

### 1.9.0 - Un score

Des collecteurs de métriques par compte et par sentinelle (taux de réussite, durée, temps de rétablissement, débit), un moteur de score aux seuils modifiables, une tendance par rapport à la période précédente, des instantanés gardés dans le stockage, un widget de score avec sa courbe, des alertes quand le score baisse et un verbe de ligne de commande qui l'affiche.

### 1.8.4 - Stabilisation

Pas de grandes fonctions. Isolation entre comptes, la page, le stockage, connexion et rôles, notifications, un GitHub qui flanche par moments, le démarrage après une migration interrompue, la reprise après une coupure, un doctor élargi, les endroits qui écrivent sur GitHub, des journaux sans jetons, une liste de contrôle de sécurité du mode équipe et des documents conformes au comportement. La série ne va jusqu'à la 1.8.9 que si nécessaire.

### 1.8.3 - Notifications par utilisateur

Préférences par utilisateur (canal, sentinelle, niveau minimal), un répartiteur qui décide qui prévenir d'après les préférences et les rôles, des canaux comme simples modules et des synthèses des alertes pas encore lues. Aussi : un rapport du temps que les jobs attendent en file pour chaque runner, et un job sauté à cause des chemins surveillés est montré à part d'un job rouge.

### 1.8.2 - Image Docker officielle et mode service

Une image multi-étapes avec un utilisateur sans privilèges, des volumes pour les données et la configuration, des variables d'environnement documentées, un exemple de compose avec proxy inverse et TLS facultatifs, une unité systemd pour qui préfère l'installation classique et un contrôle de santé profond qui échoue si le superviseur ou le cycle d'un compte est bloqué. Un identifiant que GitHub révoque ou laisse expirer marque seulement ce compte comme aveugle, déclenche une alerte système critique et peut être remplacé sans redémarrer le superviseur. Sauvegarde, mise à jour et premier démarrage en service sont documentés ; la page dit si elle écoute sur cet ordinateur, sur le réseau ou derrière un proxy ; la ligne de commande fonctionne contre un moniteur distant. L'édition lite reste locale.

## Fait dans la 1.8.0

Tout ce qui suit a été livré dans la série 1.8 et est testé ; rien n'est donné pour prouvé avec de vrais services.

- Une nouvelle organisation des dossiers (le paquet dans `src/`, la page, les exemples et les langues dans `assets/`), avec un outil de migration qui déplace une ancienne installation à plat sans rien supprimer.
- Une couche de stockage derrière une seule interface, avec le support fichiers qui garde la disposition de `accounts/<id>/`, des écritures atomiques et des sauvegardes que n'importe quel support peut restaurer.
- Un support SQLite facultatif (désactivé par défaut), une base par compte, des migrations versionnées, un délai d'attente réglable et des outils pour déplacer l'état entre le support fichiers et SQLite dans les deux sens, avec une simulation d'abord.
- L'historique des changements est traduit dans les huit langues jusqu'à la 1.0.0, et un test le garde complet.
- Rétention et rotation de l'historique (événements et analyses pendant un nombre de jours, supprimer ou archiver, une ligne d'audit par passage, un avertissement de taille dans le doctor ; l'état des sentinelles et la configuration ne sont jamais touchés).
- Mode réseau : le frein de verrouillage agit de nouveau avant d'examiner le jeton, un proxy inverse déclaré n'est jamais pris pour cet ordinateur, les lectures distantes des réglages se limitent à ce qu'un client distant peut changer et le guide de déploiement donne la recette complète.
- Le flux pour l'IA est nettoyé champ par champ, seules passent les adresses GitHub de formes fermées et le crochet ne livre aucun texte de journal, seulement le dépôt, le workflow, le résultat et le lien.
- Les lectures d'identité sont toujours celles de l'utilisateur, une lecture est jugée sur une liste blanche et le fichier de jeton du second compte reste dans le dossier des comptes.
- Un test de fumée de la page dans un vrai navigateur met la CI en rouge quand un onglet se casse ou qu'une fonction est définie deux fois.
- Une barre inférieure d'une seule ligne qui ne dit que ce que les cadres du haut ne disent pas, un résumé pour les outils d'IA et un journal en accord avec le moniteur en marche, une page qui signale quand elle est en décalage avec le moniteur et un son qui se débloque d'un clic et survit à un rechargement.
- Une lecture facultative des dépôts calmes par GraphQL (désactivée par défaut) avec sa comptabilité.
- L'avis actif à une IA externe (désactivé par défaut, une première confirmation par fournisseur, seulement les champs expurgés d'une liste fermée, un plafond d'appels et de coût par heure, la clé par le nom d'une variable, et l'IA n'exécute jamais d'action).
- L'application de terminal édite les listes et les tables.
- Mode équipe (désactivé par défaut) : utilisateurs, rôles (admin, maintainer, viewer) et sessions gardés dans le stockage, une page de connexion, un jeton Bearer pour les clients qui ne sont pas un navigateur, des erreurs JSON stables et une récupération d'un administrateur depuis la console de cet ordinateur. Le mode individuel continue sans connexion et l'édition lite n'en a jamais.
- Une page plus vivante : icônes animées, voyants d'état dont le mouvement suit l'état, réponses au survol, au focus et au clic ; tout s'éteint avec le mouvement réduit et reste léger dans l'édition lite.

## Fait dans la 1.7.9

### Corrigé

## Fait dans la 1.7.8

### Ajouté

## Fait dans la 1.7.7

### Ajouté

## Fait dans la 1.7.6

La liaison entre le moniteur et un outil d'IA : le flux concorde toujours avec la page, chaque alerte dit pourquoi elle est rouge, un flux en direct et trois outils MCP poussent les nouvelles, une commande installe le script de liaison, la barre montre si une IA est connectée et tout fichier d'état est privé à son propriétaire.

## Fait dans la 1.7.5

La ligne de commande prend le jeton d'accès sous son propre nom, le mode réseau est plus sûr par défaut (l'adresse de l'ordinateur est cachée au réseau, l'ancienne adresse ?access= peut être désactivée, les destinations de notification du réseau local sont refusées, avertissement sur le HTTP simple), les heures pour les personnes utilisent votre fuseau horaire, une alerte peut être mise en sourdine jusqu'à ce que l'élément change, et les comptes et vérifications qui donnaient des réponses fausses sont corrigés.

## Fait dans la 1.7.4

Une barre au pied de la page avec l'avis le plus important (et une fenêtre avec tous), la connexion, le quota, la dernière lecture, le mode, l'adresse et l'horloge ; un bouton plein écran ; des tableaux Dépôts et Historique qui se trient selon une ou plusieurs colonnes, avec les colonnes de votre choix ; `bin/monitor_cli.py`, la ligne de commande comme client du moniteur en marche (`status`, `health`, `alerts`, `accounts`, `live`, `doctor`) avec `--json` et des codes de sortie stables, et son guide en huit langues ; les journaux des modifications vérifiés dans l'ordre, le README du paquet sans historique à l'intérieur et les images redessinées.

## Fait dans la 1.7.3

Une seconde sentinelle pour les issues et pull requests (Collab, désactivée par défaut, lecture seule, horloge propre), un onglet Alertes avec les alertes de toutes les sentinelles et un filtre par origine et niveau, des mises en sourdine locales qui se terminent seules (une alerte, une règle ou une sentinelle ; `alerts.mute_hours`), l'étiquette qui fait ignorer un élément, `GET /api/alerts` et `GET /api/events`, une liste de contrôle de la vue en direct, un guide de la sentinelle Collab en huit langues et les images redessinées.

## Fait dans la 1.7.2

L'en-tête avec ses chiffres dans un ordre qui se lit et dans une grille qui suit la largeur ; les commandes rapides (seulement les chauds, vitesse, santé des écosystèmes) fixes en haut à droite ; Réglages, Aide et À propos seulement dans le panneau latéral ; l'avis de nouvelle version hors de l'en-tête ; et les tests qui ne laissent plus de fichiers à côté du code.

## Fait dans la 1.7.1

Une page avec un panneau latéral (le logo, le sélecteur de comptes, les sections en groupes repliables, l'aide) et seize thèmes en plus d'auto, clair et sombre, ceux du Studio du système d'alarme ; et la sentinelle CI derrière un contrat (`BaseSentinel`, `Alert`, `SentinelRegistry`, `SentinelCI`), pour pouvoir ajouter les sentinelles suivantes sans que le moniteur sache ce que fait chacune. Ce qui est montré et décidé ne change pas.

## Fait dans la 1.7.0

Plusieurs comptes dans l'édition complète, chacun un moniteur à part sous un superviseur (`accounts/<id>/`, `--accounts`, `--account`, `--migrate-accounts`), l'API des comptes, un webhook pour tous, la page avec un sélecteur et les cartes de tous les comptes, les vues par adresse (`?view=` et `?chrome=0`) et la vue En direct avec l'état du récepteur de webhook. L'édition lite ne change pas.

## Fait dans la 1.6.8

Le proxy HTTPS de la 1.6.7 est vérifié face à un vrai proxy sur le port 443 (`tools/manual_check_live.py proxy`, et des tests qui parcourent un client sur TLS, un reverse proxy et le moniteur), les images sont reprises avec deux nouvelles du mode réseau, et l'historique des modifications est traduit dans les sept autres langues jusqu'à la 1.6.3.

## Fait dans la 1.6.7

Un proxy HTTPS sur le port 443 par défaut fonctionne désormais avec le mode réseau (`listen.proxy_public_host`, vide par défaut : le seul nom public du proxy est accepté sans port, uniquement en HTTPS, et il ne se change que depuis l'ordinateur lui-même), et l'historique des modifications est traduit dans les sept autres langues pour la 1.6.7, la 1.6.6 et la 1.6.5.

## Fait dans la 1.6.6

Corrections après la 1.6.5 : le mode réseau fonctionne maintenant en HTTPS depuis la page (la garde d'origine suit le schéma de la session), tout réglage que le schéma marque sûr ne se change que depuis l'ordinateur lui-même, `act` libère son exécution après Stop et ferme son tube, une barre rouge dans les Réglages quand le mode réseau écoute sur toutes les interfaces, la session peut s'ouvrir par POST au lieu de l'adresse, un compteur d'échecs avalés dans `--doctor` et À propos, `tools/make_screenshots.py` dit ce qu'il fait et les images sont refaites, et l'historique des modifications est traduit en huit langues.

## Fait dans la 1.6.5

Une version d'intégrité et de sécurité, sans grosse nouveauté : un commit vert exige le workflow obligatoire du dépôt, un fetch en échec arrête le lancement, le catalogue ne peut pas nommer un outil hors du dossier des outils ni changer `dry_run`/`ref`, et un lot sans vérification de commit enregistrée n'est plus proposé à la signature ; `act` reste dans l'espace de travail et Stop termine tout l'arbre de processus et les conteneurs de l'exécution ; le mode réseau peut servir du HTTPS, bloque les jetons erronés et n'accepte que l'IPv4 ; le webhook refuse rejeux et inondations ; le serveur MCP survit aux messages mal formés ; `max_per_hour` compte les messages ; les réglages sont enregistrés sous verrou ; le jeton conservé n'atteint que `gh` ; `--doctor` signale les combinaisons dangereuses ; le test d'installation propre est une étape à part du contrôle de publication.

## Fait dans la 1.6.4

Tests d'isolation de l'édition lite et de la démo, aucune requête réseau quand la vérification de version est désactivée ou l'installation isolée, un README qui commence par le choix du lanceur, `--doctor --json`, une barre persistante pour le mode réseau, l'aide et ses documents en huit langues, et les fonctions optionnelles (mode réseau, un jeton conservé par le moniteur, actions sur GitHub, `act`, copie locale des artefacts, runners auto-hébergés, OpenTelemetry, FinOps par étiquettes de job) ; voir le journal des modifications et `ADVANCED.md`.

## Prochainement

Ce que la 1.6.4 n'a pas atteint, et pourquoi :

- **Plusieurs propriétaires dans un processus et une page** : depuis la 1.7.0 chaque compte est un moniteur à part et la page les montre côte à côte, mais dans un moniteur un dépôt reste identifié par son seul nom, si bien que deux propriétaires dans le même moniteur se mélangeraient. Les réunir dans un seul processus exige le propriétaire dans chaque identifiant (les lectures, les identifiants d'alerte, les listes des réglages, les sentinelles et la page) ; cela n'a pas pu être démontré sans les dépôts de deux vrais propriétaires, donc les comptes de la 1.7.0 restent le moyen de les séparer.
- **Le rapport de facturation avec un compte qui peut le lire** : la vraie réponse pour un compte sans la portée `user` est « introuvable » et le moniteur retombe sur l'estimation (vérifié) ; les chiffres eux-mêmes n'ont pas été comparés à un compte de facturation.
- **Les prix des gros runners** de `quotas.json` viennent de la mémoire de la grille tarifaire publique et sont marqués non vérifiés ; comparez-les à la page de facturation de GitHub et modifiez le fichier.
- **`gh copilot`** : ses options se vérifient avec `gh copilot -- --help`, qui exige la ligne de commande Copilot ; elle n'est pas installée ici, donc elles restent non vérifiées.
- **Notifications, webhook, Enterprise Server et exemples de service** face à des services réels : `tools/manual_check_live.py` les vérifie à la main ; ils demandent vos canaux et hôtes, ils n'ont donc pas été lancés ici.
- **L'application de terminal** modifie les réglages simples, les listes et les tables de nombres et montre l'état de l'IA ; l'explication d'un workflow rouge précis reste dans la page.
- **Seul le propriétaire peut les démontrer sur une vraie installation** : plusieurs comptes avec la sentinelle Collab sur de vrais dépôts, une GitHub App et un second compte en lecture seule avec de vraies clés, et le proxy HTTPS avec un vrai certificat. Ils se vérifient à la main (`tools/manual_check_live.py`) et ne sont pas donnés pour faits.
- **Une vérification de nouvelle version qui télécharge ou installe** : jamais ; le moniteur ne fait que le dire.

## Plus tard

- **Télémétrie matérielle des runners** par un agent : aujourd'hui seul un point d'accès facultatif de node exporter est lu.
- **Une quatrième phase** (plugins, automatisation plus large, IA avancée) seulement après plusieurs semaines de 2.0.x stable et une décision explicite.

## Idées qui demandent d'abord une décision

- Une version PDF des rapports programmés (aujourd'hui HTML et Markdown).
- Une vue des versions prêtes ou bloquées, une par dépôt, dans l'onglet Équipe.
