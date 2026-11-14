# Feuille de route

Des idées qui n'ont pas tenu dans la version actuelle, sans ordre promis. Ce sont des directions, pas des engagements ; une issue ou une pull request est la meilleure façon d'en faire avancer une.

## Dans la 1.8.0 (la prochaine version)

Tout ce qui suit est écrit et testé ; c'est soit déjà dans la branche principale, soit en attente dans une pull request. Rien n'est présenté comme prouvé sur de vrais services (voir « Ensuite »).

### Déjà dans la branche principale

- Une nouvelle organisation des dossiers (le paquet dans `src/`, la page, les exemples et les langues dans `assets/`), avec un outil de migration qui déplace une ancienne installation à plat sans rien supprimer.
- Une couche de stockage derrière une seule interface, avec le support fichiers qui garde la disposition de `accounts/<id>/`, des écritures atomiques et des sauvegardes que n'importe quel support peut restaurer.
- Un support SQLite facultatif (désactivé par défaut), une base par compte, des migrations versionnées, un délai d'attente réglable et des outils pour déplacer l'état entre le support fichiers et SQLite dans les deux sens, avec une simulation d'abord.
- L'historique des changements est traduit dans les huit langues jusqu'à la 1.0.0, et un test le garde complet.
- Rétention et rotation de l'historique (événements et analyses pendant un nombre de jours, supprimer ou archiver, une ligne d'audit par passage, un avertissement de taille dans le doctor ; l'état des sentinelles et la configuration ne sont jamais touchés).

### Terminé et en attente de fusion

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

### Encore en finition

- Des silences qui retiennent qui les a posés (demande le mode équipe).

## Prévu, dans cet ordre

Chaque version porte tout ce qui est de son tronçon du plan : rien ne reste suspendu à une version antérieure et rien n'est repoussé à la suivante. Après la 1.8.3 et après la 1.9.3, le produit passe une revue indépendante dont les constats sont clos dans la version de stabilisation suivante. Il n'y a pas de 1.8.1 : utilisateurs, rôles et sessions arrivent avec la 1.8.0.

### 1.8.2 - Image Docker officielle et mode service

Une image multi-étapes avec un utilisateur sans privilèges, des volumes pour les données et la configuration, des variables d'environnement documentées, un exemple de compose avec proxy inverse et TLS facultatifs, une unité systemd pour qui préfère l'installation classique et un contrôle de santé profond qui échoue si le superviseur ou le cycle d'un compte est bloqué. Un identifiant que GitHub révoque ou laisse expirer marque seulement ce compte comme aveugle, déclenche une alerte système critique et peut être remplacé sans redémarrer le superviseur. Sauvegarde, mise à jour et premier démarrage en service sont documentés ; la page dit si elle écoute sur cet ordinateur, sur le réseau ou derrière un proxy ; la ligne de commande fonctionne contre un moniteur distant. L'édition lite reste locale.

### 1.8.3 - Notifications par utilisateur

Préférences par utilisateur (canal, sentinelle, niveau minimal), un répartiteur qui décide qui prévenir d'après les préférences et les rôles, des canaux comme simples modules et des synthèses des alertes pas encore lues. Aussi : un rapport du temps que les jobs attendent en file pour chaque runner, et un job sauté à cause des chemins surveillés est montré à part d'un job rouge.

### 1.8.4 - Stabilisation

Pas de grandes fonctions. Isolation entre comptes, la page, le stockage, connexion et rôles, notifications, un GitHub qui flanche par moments, le démarrage après une migration interrompue, la reprise après une coupure, un doctor élargi, les endroits qui écrivent sur GitHub, des journaux sans jetons, une liste de contrôle de sécurité du mode équipe et des documents conformes au comportement. La série ne va jusqu'à la 1.8.9 que si nécessaire.

### 1.9.0 - Un score

Des collecteurs de métriques par compte et par sentinelle (taux de réussite, durée, temps de rétablissement, débit), un moteur de score aux seuils modifiables, une tendance par rapport à la période précédente, des instantanés gardés dans le stockage, un widget de score avec sa courbe, des alertes quand le score baisse et un verbe de ligne de commande qui l'affiche.

### 1.9.1 - Sentinelle de sécurité

La troisième sentinelle : Dependabot, analyse de code, analyse des secrets, protection des branches, permissions des workflows et propriétaires du code, avec des règles par type de signal, le même filtre dans l'onglet Alertes et une pénalité dans le score pour les alertes critiques ouvertes. Facultatif, dans la même version : hygiène des workflows (actions non fixées à un commit, jobs sans limite de temps, workflows sans permissions ou sans concurrence, usage dangereux de pull_request_target), sur le vérificateur de workflows que le projet a déjà.

### 1.9.2 - Santé du dépôt et de l'équipe

Une vue de santé de chaque dépôt (CI, tickets et pull requests, sécurité, préparation à une version, activité) et une de l'équipe avec classement, totaux et filtres ; des pages pour les deux avec des liens directs pour écrans muraux. Facultatif, dans la même version : un panneau de benchmarks de nuit face à un budget (médiane face à une référence par classe de machine) et un panneau de nomenclatures logicielles et d'attestations de chaque version.

### 1.9.3 - Rapports programmés et journal d'audit

Des modèles de rapport en HTML et Markdown (PDF facultatif) avec le score, les principales alertes et les changements, un planificateur et un journal d'audit en ajout seul de qui a fait quoi et quand, sans aucun secret dedans. Facultatif, dans la même version : une vue « version prête / bloquée » avec le dernier commit vert de chaque dépôt.

### 1.9.4 - Stabilisation de la troisième phase

La même sorte de clôture que la 1.8.4 pour le score, la sentinelle de sécurité, les vues de santé, les rapports et le journal d'audit ; le coût en appels d'API avec trois sentinelles actives ; un score qui reste cohérent quand une sentinelle est éteinte.

### 2.0.0 - Maturité

Une version majeure qui nettoie la dette technique et fige les interfaces publiques : sentinelles, stockage, alertes, le schéma d'événements et l'API de lecture, avec une suite de tests de contrat que les clients peuvent lancer contre n'importe quelle version. Un guide pour chaque façon d'utiliser le produit (lite, individuel, service, équipe) et une référence des réglages, événements, métriques et API. À partir de la 2.0.1, un coussin pour ce qui n'apparaît qu'à l'usage réel prolongé.

Les workflows du moniteur lui-même respectent ce que la sentinelle d'hygiène demandera aux autres : actions fixées à un commit, permissions minimales et une limite de temps sur chaque job.

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

- **Plus d'adaptateurs de notification** : ntfy, Microsoft Teams et e-mail via un relais local.
- **Plusieurs comptes dans une page** : fait dans la 1.7.0, chaque compte dans son propre moniteur sous un superviseur.
- **Télémétrie matérielle des runners** via un agent : aujourd'hui seul un point d'accès optionnel de node exporter est lu.

## Idées qui demandent d'abord une décision

- Lire dans la page les journaux d'une étape en échec, avec le même nettoyage que l'assistant IA.
