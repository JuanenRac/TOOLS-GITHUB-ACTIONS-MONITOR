# Feuille de route

Des idées qui n'ont pas tenu dans la version actuelle, sans ordre promis. Ce sont des directions, pas des engagements ; une issue ou une pull request est la meilleure façon d'en faire avancer une.

## Fait dans la 1.7.4

Une barre au pied de la page avec l'avis le plus important (et une fenêtre avec tous), la connexion, le quota, la dernière lecture, le mode, l'adresse et l'horloge ; un bouton plein écran ; des tableaux Dépôts et Historique qui se trient selon une ou plusieurs colonnes, avec les colonnes de votre choix ; `monitor_cli.py`, la ligne de commande comme client du moniteur en marche (`status`, `health`, `alerts`, `accounts`, `live`, `doctor`) avec `--json` et des codes de sortie stables, et son guide en huit langues ; les journaux des modifications vérifiés dans l'ordre, le README du paquet sans historique à l'intérieur et les images redessinées.

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

- **Décidé, pas fait dans la 1.6.6** : l'avis actif à une IA externe (désactivé par défaut, une première confirmation par fournisseur, seulement les champs déjà filtrés de la liste fermée, un plafond d'appels et de coût par heure, la clé par le nom d'une variable d'environnement, et l'IA n'exécute jamais d'action) avec sa variante de commande sortante (liste fermée, sans shell) ; et les dépôts de plusieurs propriétaires dans une page (le moniteur identifie un dépôt par son seul nom, il lui faut donc le propriétaire dans chaque identifiant ; c'est la base de plusieurs comptes). Chacun est une fonction à part avec sa conception et ses tests, donc la 1.6.6 a d'abord clos les corrections.
- **Les anciennes entrées du journal des modifications dans les sept autres langues** : l'Aide montre l'historique dans chaque langue, et de la 1.6.8 à la 1.6.3 sont traduites ; la 1.6.2 et les précédentes gardent le texte anglais sous un avis traduit et seront traduites version par version, de la plus récente à la plus ancienne.
- **Plusieurs propriétaires dans un processus et une page** : depuis la 1.7.0 chaque compte est un moniteur à part et la page les montre côte à côte, mais dans un moniteur un dépôt s'identifie encore par son seul nom, donc deux propriétaires dans le même moniteur se mélangeraient. Les comptes de la 1.7.0 sont le moyen de les garder séparés ; les ramener dans un seul processus, avec le propriétaire dans chaque identifiant, est ce qui reste.
- **Le rapport de facturation avec un compte qui peut le lire** : la vraie réponse pour un compte sans la portée `user` est « introuvable » et le moniteur retombe sur l'estimation (vérifié) ; les chiffres eux-mêmes n'ont pas été comparés à un compte de facturation.
- **Les prix des gros runners** de `quotas.json` viennent de la mémoire de la grille tarifaire publique et sont marqués non vérifiés ; comparez-les à la page de facturation de GitHub et modifiez le fichier.
- **`gh copilot`** : ses options se vérifient avec `gh copilot -- --help`, qui exige la ligne de commande Copilot ; elle n'est pas installée ici, donc elles restent non vérifiées.
- **Notifications, webhook, Enterprise Server et exemples de service** face à des services réels : `tools/manual_check_live.py` les vérifie à la main ; ils demandent vos canaux et hôtes, ils n'ont donc pas été lancés ici.
- **L'application de terminal** modifie les réglages simples et montre l'état de l'IA ; l'explication d'un workflow rouge précis et l'édition des listes et tables restent dans la page.
- **Une vérification de nouvelle version qui télécharge ou installe** : jamais ; le moniteur ne fait que le dire.

## Plus tard

- **Plus d'adaptateurs de notification** : ntfy, Microsoft Teams et e-mail via un relais local.
- **Plusieurs comptes dans une page** : fait dans la 1.7.0, chaque compte dans son propre moniteur sous un superviseur.
- **Télémétrie matérielle des runners** via un agent : aujourd'hui seul un point d'accès optionnel de node exporter est lu.

## Idées qui demandent d'abord une décision

- Un écran de connexion pour la page, afin que le mode réseau n'exige plus de saisir une fois le jeton d'accès. Aujourd'hui la réponse est le jeton d'accès et, pour Internet, un reverse proxy avec authentification (voir `monitor/docs/DEPLOYMENT.md`).
- Lire dans la page les journaux d'une étape en échec, avec le même nettoyage que l'assistant IA.
