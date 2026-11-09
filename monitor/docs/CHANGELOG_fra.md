<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Journal des modifications

Version de l'outil lui-même (moniteur + sentinelle + outils par lots), avec son propre semver. La source est le CHANGELOG.md en anglais ; ce fichier contient les mêmes versions et sections.

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
- `tools/demo_accounts.py` pour les images, le guide `ACCOUNTS.md` en huit langues et des tests pour chaque changement (la suite est passée de 866 à 913).

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

> Cette version n'est disponible qu'en anglais pour l'instant ; la traduction viendra dans une version ultérieure.

### Ajouté

- **A catch-all group** `rest` ("Everything else", prefix `*`) at the end of the example catalogue of ecosystems, so a new installation leaves no repository out.
- **An automatic group "Unclassified"** for the repositories that no group claims (setting `show_unclassified`, on by default; an explicit choice of ecosystems is respected).
- **A warning when the filter hides repositories**: a banner (complete and lite) says "your ecosystem filter hides N of the M repositories of the account" and names them.
- **The lite edition starts with what you already set up**: on its first start `actions_monitor_lite.json` copies from `actions_monitor.json` (when it exists) the account, the repositories and ecosystems to watch, the catalogue files, the exclusions, the language and the reading depth, and says so on the console. Without such a file its template watches all the ecosystems.
- **`tui.py --lite`** (or `MONITOR_MODE=lite`) reads the lite edition on port 8766.
- **`redrule.py`**, the single small rule of "red on main", used by the sentinel and by the lite edition (which marks the figure as approximate because it guesses the default branch).
- **`ghamon_etag_invalid_total`**, the count of damaged cache entries, in `/metrics`.
- Tests: header-data parity between the complete and the lite edition, the catch-all group, the hidden-repository count, the lite start, the webhook hot mark, the damaged cache entry, and that importing the monitor or the sentinel never loads Rich.
- Guides `LITE` and `SETTINGS` (eight languages) updated.

### Modifié

- **Both editions show the same header figures**: runs, failures, successes, compute minutes, running and queued are counted once, by the server, over the same 24 hours with each run counted once; the lite edition reads as deep as the complete one. The lite edition hides the "unsigned" tile.
- **A webhook event marks the repository as hot**, so the next cycle reads it again whatever the event said.
- The GitHub allowance tile is painted from the first moment, while the repositories are still loading.

### Corrigé

- A new installation with the example catalogue saw almost no repository; the lite edition detected one repository out of 129 because its template filtered by ecosystem.
- **A damaged cache entry is only a miss**: it is thrown away and the endpoint is read again in full.
- "Red on main" and the compute minutes differed between the two editions.

### Sécurité

- The lite edition never inherits the sentinel, the AI, the webhook, the outputs or the notifications, nor any secret, from the complete one; it writes neither `ci_red.json` nor a signing queue.

## [1.6.1]

> Cette version n'est disponible qu'en anglais pour l'instant ; la traduction viendra dans une version ultérieure.

### Ajouté

- **The lite edition**, a second and simpler product in the same package: `MONITOR_LITE_GITHUB_ACTIONS.bat` / `.sh` / `.command` or `--lite` / `MONITOR_MODE=lite`. What is running and what failed, failures and successes of 24 hours, red on main, the history and the basic charts; a short Settings page (account, repositories and ecosystems, refresh, language, theme); its own file `actions_monitor_lite.json`, its own state files with the suffix `_lite` and port 8766, so both can run side by side.
- **`act` command in the repository panel**: for each workflow of the repository, `act -W .github/workflows/FILE -j JOB` ready to copy. The monitor never runs it (running it exists only as a confirmed action of the AI assistant).
- **A container example** (`deploy/Dockerfile`) that the CI builds.
- Guide `LITE` in eight languages, a Lite-versus-Complete table in every README and new screenshots of both editions in light and dark.
- The roadmap lists what did not fit: local mirror of artifacts, FinOps of the minutes, self-hosted runner status and an OTLP export, and the notes of the terminal view (why it uses Rich).

### Sécurité

- The lite edition has no sentinel: it is not imported and its endpoints answer 404.

## [1.6.0]

> Cette version n'est disponible qu'en anglais pour l'instant ; la traduction viendra dans une version ultérieure.

### Ajouté

- **Conditional reads (ETag)**: every read of the run lists sends `If-None-Match`; a `304 Not Modified` answer costs no quota. The header and `ghamon_etag_saved_total` count the reads saved; `cache.etag.*` in the Settings tab.
- **Resilience to network cuts**: when every read of a cycle fails with a connection problem the page keeps the last picture with an offline banner and resumes by itself; `offline` and `online` events (they can be notified) and `ghamon_offline`.
- **Analytics** (section A12 of the Sentinel tab, `/api/analytics`, `/metrics`, the Grafana JSON source): p50 / p95 of the duration of each workflow, of the queue time of its jobs and of each step; workflows that got slower than usual; **flaky** workflows (failed, then passed on the same commit, or needed another attempt), only a label that never changes what counts as red.
- **Incoming webhook in real time**: a signed `workflow_run` event updates the run list of its repository without reading GitHub, `workflow_job` events bring queue and step times; only short validated fields are kept (`/api/live-events`).
- **Workflow linter**: `lint_workflows.py` (actions not pinned by SHA, missing or broad permissions, secrets in clear text, injection, `pull_request_target` with the PR's code), rules switchable with their own severity, a line in the daily report and the section A13. A comment `# monitor-lint: ignore RULE reason` or the setting `lint.ignore` silences a finding.
- **Notifications** (off by default): Telegram, Discord, Slack, Matrix, MQTT and a local HTTP address, a limit per hour, a test button and a documented adapter contract (`monitor/docs/schemas/notification_event.schema.json`).
- **AI assistant**: new providers `anthropic` (Messages API, the model is yours to choose) and `copilot` (`gh copilot` with your own login, text only, no tools); new tasks (daily report, release notes, a question about a repository); settings for the kinds of event, the repositories, the language and the limits, a test button and the use of the day. A closed list of actions (`gh run rerun`, `gh issue close`, `act`), only PROPOSED by default.
- **The figures of the header are tiles** with an icon, a big figure and a small label, coloured by state, with a tooltip, a click that leads to the tab, counting figures and a skeleton that shows the last known values at once; the second line (repositories, hot, mode, reads saved, GitHub allowance with a bar and a live countdown, connection, last update and the loading progress) is made of tiles too.
- **Terminal view**: `tui.py` draws a live grid in the console (read-only, optional, needs the package `rich`; the monitor and its tests need no package).
- **For servers and bigger accounts**: `GET /api/health`, `GH_HOST` for GitHub Enterprise Server (every link of the page follows it), `discover_limit`, minimum permissions per feature, and a guide to run it as a service (systemd, launchd, a scheduled task, a container) and behind a reverse proxy.
- Published JSON schemas of `ci_red.json`, of the public export and of the notification event (`monitor/docs/schemas`), and a public roadmap (`docs/ROADMAP.md`).
- New guides in eight languages: notifications, the AI assistant, analytics, console tools and deployment; the webhook guide covers the real-time events. All screenshots were redone (light and dark, console tools included) with `tools/make_screenshots.py` and invented data.

### Modifié

- **Settings**: new sub-tabs for reads and cache, notifications, analytics, the linter and the terminal view; the AI and webhook sub-tabs have all their options.

### Corrigé

- **The linter no longer cries wolf on placeholders**: a value that looks like a secret is classified (a known token format or a long high-entropy string is serious, a readable filler such as `placeholder` or `changeme` is only information, anything else a warning; references and empty values are no finding) and its value is never printed or stored.
- **A browser that closes or reloads its tab while the page is loading no longer prints a traceback** (`ConnectionAbortedError`, `ConnectionResetError`, `BrokenPipeError`): they are counted in `ghamon_client_disconnects_total`; a real error is still shown.

### Sécurité

- The incoming webhook stays off by default, on `127.0.0.1`, with a mandatory HMAC.
- Notification secrets live only in environment variables; hosts are fixed; notifications never write to GitHub.
- AI actions: running one needs its own switch and a confirmation of the full command each time, only on targets the monitor already watches, with a limit per hour, a local log and a lock after two failures in a row.

## [1.5.2]

> Cette version n'est disponible qu'en anglais pour l'instant ; la traduction viendra dans une version ultérieure.

### Ajouté

- **The Settings tab is organised in sub-tabs**, ordered from the common to the advanced (This browser, General, Refresh and limits, Sentinel, Surface checks A10, Readiness A11, Folders and files, Outputs, External AI, Incoming webhook). Inside a sub-tab the settings sit in titled blocks whose first field is the main switch (the rest of the block dims while it is off). Every field shows its unit and range, a badge (needs a restart / applies now), a badge for the safety options that start in their conservative state, and one line of help. A search box filters all the sub-tabs, each sub-tab counts its unsaved changes, Save and Discard stay visible, the arrow keys, Home and End move between the tabs and the last sub-tab used is remembered by the browser.
- **Every setting of the configuration file is in the page now**: the A10 checks (a switch per check and its limits), the weights of the ecosystem health score, the sources of the pinned versions, the Actions-minutes ceilings, the required files, the audit file patterns, the hot period of the sentinel, the unknown-sample rule of A2, the candidate prefixes, the list of repositories and the switch of the incoming webhook.
- **Signing queue by trust**: each row says `verified`, `unknown` or `failed`; the Sentinel tab has a Signature filter with the count of each kind; `read_report.py --sign-trust` filters the console list and the export, and the exported rows carry `trust`.
- **Readiness chips in the header**: one coloured chip per ecosystem with its health score.
- **A minimal Grafana board** (`red_by_ecosystem.json`) and a test that checks every metric of both boards against what `/metrics` serves.
- New guide `WEBHOOK` (refresh-only mode) and a commented example of the pin sources, in eight languages.
- `tools/make_settings_doc.py` writes the settings table of the guides from the schema and the texts of the page, and the CI checks it.

### Modifié

- **The daily report groups the issue-closing suggestions** in one line per repository (the monitor still closes nothing).
- **The contract of the profile dashboard** is documented and checked by a test (`/api/outputs/dashboard.json` is exactly the document of `ci_red.json`; the public export never carries the signing side).

### Sécurité

- The shared secret of the webhook is never shown in the page: it only says whether it is defined.

## [1.5.1]

> Cette version n'est disponible qu'en anglais pour l'instant ; la traduction viendra dans une version ultérieure.

### Ajouté

- **The settings page can set the external AI of the sentinel** (group "External AI for the sentinel"): `ai.provider` (`none` / `ollama` / `openai-compatible`), `ai.model`, `ai.ollama_url` (only this computer), `ai.base_url` (https only), `ai.api_key_env` and `ai.daily_limit`. Off by default; an outside service receives data of your repositories.
- **`migrate_state.py`**: brings the files written before 1.5.0 to the new names (events, report history, release candidates, batch records, the `report_history_days` setting). A dry run by default; `--apply` copies and keeps the old files, `--move` renames them; nothing that exists is overwritten. One-page guide in `docs/MIGRATING.md`, in eight languages.
- **`--init-catalog`** creates editable `ecosystems.json`, `targets.json` and `profiles.json` from the examples.
- A test makes sure no document sends the reader to a command that was renamed in 1.5.0 (only the tables of old and new names and the migration guides may name them).
- The version in every README.

### Modifié

- **First start without catalogue files of your own**: the console says the example files are in use.
- Python 3.11 or newer is the documented minimum (tested on 3.11 and 3.13 on Windows, Linux and macOS).

### Sécurité

- Only the NAME of the environment variable that holds the AI key can be set: the key itself is never shown or saved.

## [1.5.0]

> Cette version n'est disponible qu'en anglais pour l'instant ; la traduction viendra dans une version ultérieure.

**Update notice (read this first).** Several files and settings have English names now. Nothing is lost: the old names are still READ where a file written by an earlier version may exist, and the new names are the only ones written.

| Before 1.5.0 | From 1.5.0 |
|---|---|
| `leer_parte.py` | `read_report.py` |
| `eventos.py` | `events.py` |
| `parte_history.py` | `report_history.py` |
| `LOTE_GITHUB_ACTIONS.bat` / `.sh` / `.command` | `BATCH_GITHUB_ACTIONS.bat` / `.sh` / `.command` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` (copy or rename them to keep the history of events) |
| `PARTE_CENTINELA_DIA_<day>.txt/.json` (report history) | `SENTINEL_REPORT_DAY_<day>.txt/.json` (the old ones are still read) |
| `PARTE_CENTINELA_<time>.txt` (saved report) | `SENTINEL_REPORT_<time>.txt` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_<time>.json` | `<signed_dir>/batches/batch_<time>.json` (the old records are still read) |
| `parte_history_days` (setting) | `report_history_days` (the old name is still read) |
| `monitor_y_centinela.zip` and folder | `github_actions_monitor.zip` and folder; `LEEME_CORREO.txt` is `README_MAIL.txt` |
| A8 looked for `RECONCILIACION_TOTAL_AUDITORIAS_*.txt`, `MAPA_DE_RONDAS_*` | the names are `sentinel.audit_files` (neutral defaults `RECONCILIATION_TOTAL_*.txt`, `ROUNDS_MAP_2*.txt`, `ROUNDS_MAP_EXTRA_*.txt`); set your own there |
| `ci_red.json`, its schema and the `--export-status` files | unchanged (they are a contract) |

- **English by default.** The language of the system no longer decides: the tools start in English until you choose another one in the Settings tab, with `language` in `actions_monitor.json`, `MONITOR_LANG` or `--lang`.
- **A clean, neutral package.** `ecosystems.json`, `targets.json` and `profiles.json` are no longer part of the package: only the `*.example.json` files travel, and a missing default file falls back to its example. Your own files live anywhere and are named by `ecosystems_file`, `targets_file` and the new `profiles_file`; the folder of your local signing tools is the new `tools_dir`. The tests use their own fixtures (`tests/fixtures`).
- **Settings tab.** A new tab changes the values of `actions_monitor.json` from the page: a whitelist of keys with their type and range, one request refused as a whole when a value is invalid, a copy of the previous file in `config_backups/` before every save (the last ten are kept), an atomic write, only on 127.0.0.1 with the same Host and Origin checks as every other endpoint, JSON only. Tokens, secrets, signature keys and the command of the sentinel are not in the list: they are never shown and never written, and every other key of the file is kept as it was. Each setting says whether it needs a restart. The language selector, the theme and the dense view moved there.
- **Buttons and icons.** Buttons have relief, light up on hover and sink when pressed; the icon buttons are inline SVG with an accessible name and a tooltip in the 8 languages. Colours, type, cards, bars and the ring follow the status dashboard of the profile repository.
- **Life in the charts.** Bars grow in, what is red or running has a discreet pulse, the figures of the header count up, hovering a bar highlights it and gives its text as a tooltip, widths change smoothly; all of it stops with `prefers-reduced-motion`.
- **Outputs for other tools (off by default, 127.0.0.1 only, no new token).** `/metrics` in the Prometheus format (red workflows per ecosystem and repository, red streaks and hours, builds waiting for a signature, A10 paused, allowance left, incomplete snapshot...), `/api/outputs/grafana.json` for the Grafana JSON / Infinity source and `/api/outputs/dashboard.json` (the `ci_red.json` document) for the status dashboard. An importable Grafana dashboard is in `docs/grafana/` and the details in `docs/OUTPUTS.md`.
- **Report:** a line (code `tag_vs_manifest`) when a release tag is ahead of the version of the manifest; the unsigned figure is ordered by the longest wait and says how long it is; the repository panel suggests the `gh issue close` command (never run) for a failure issue whose workflow is green again; the `hil` batch profile is documented in `profiles.example.json`; tests for `finalize` and for `monitor_link`.
- **Docs:** `docs/SETTINGS.md`, `docs/OUTPUTS.md`, README and QUICKSTART in the 8 languages updated, screenshots made with invented repositories.

## [1.4.5]

> Cette version n'est disponible qu'en anglais pour l'instant ; la traduction viendra dans une version ultérieure.

- **The report says when the snapshot is incomplete:** a line with the stable code `incomplete` (still loading, no local workspace, errors while reading) right after the headline, so nobody acts on a half-read list of red repositories or signing queue.
- **Signing summary:** one line with how many releases wait to be signed (verified / not checked / failed the check) and how many builds are build-only on purpose, so "not signed on purpose" is not confused with "signature missing" (code `sign_summary`).
- **A10 paused for the quota is said in the report** (code `a10_paused`) with the allowance left and needed, and the three knobs that control it.
- Texts in the 8 languages; tests for the three lines.

## [1.4.4]

> Cette version n'est disponible qu'en anglais pour l'instant ; la traduction viendra dans une version ultérieure.

- **Author and licence are always visible:** the web panel has a footer with the author and the licence, `read_report.py --version` and the new `gha_dispatch_all.py --version` print them under the version, and the monitor prints the same line when it starts. The text is in the 8 languages (`ui.about`); the author and the licence come from `tool_version.py`.
- **Bridge to the dashboard written down:** `docs/CI_RED_BRIDGE.md` says what `ci_red.json` contains (schema 2, `complete`), how to export it and what a reader must check; the monitor still never pushes or commits.
- Tests for the author line in the 8 languages, the footer, both `--version` flags and the start-up line.

## [1.4.3]

> Cette version n'est disponible qu'en anglais pour l'instant ; la traduction viendra dans une version ultérieure.

- **A workflow that only runs on pull requests no longer makes A2 inconclusive:** `pull_request` and `pull_request_target` join the events whose runs never sit on the default branch (like `workflow_dispatch`, `release` and `workflow_call`), so a workflow such as a contract integration check that only runs on pull requests is not asked for a last run on main. A workflow that also has `push` or `schedule` still counts. Tests for both cases.

## [1.4.2]

> Cette version n'est disponible qu'en anglais pour l'instant ; la traduction viendra dans une version ultérieure.

- **A2 no longer counts a run in progress or a cancelled one as seen:** when it resolves a hidden workflow, the Sentinel now asks for the last completed runs of that workflow on the default branch (`gh run list -w <file> --branch <default> --status completed -L 10`, read only) and uses the first one with a real conclusion. A cancelled or skipped run (and anything without a conclusion) is ignored, so it can no longer hide an earlier red; a workflow with no completed run with a conclusion on the branch stays inconclusive on its own. Same quota gate, call limit and cache as before.

## [1.4.1]

> Cette version n'est disponible qu'en anglais pour l'instant ; la traduction viendra dans une version ultérieure.

- **A2 resolves a hidden workflow instead of giving up on the whole repository:** when a repository has a full run sample and a workflow of its clone (one that can run on the default branch) is missing from it, the Sentinel asks GitHub for the last run of THAT workflow on the default branch (`gh run list -w <file> --branch <default> -L 1`, read only). A red answer counts as red in A2; a green one removes the workflow from the inconclusive list; a workflow with no run on the branch stays inconclusive on its own and the panel names it (`repo/file.yml (no run on the default branch)`) instead of only the repository. Without quota (same gate as A10: `min_rate_remaining` x `surface.min_rate_factor`, plus the hourly budget) the workflow stays inconclusive and the panel says why. New options `sentinel.a2_resolve_max_calls_per_tick` (4; 0 = never ask) and `sentinel.a2_resolve_ttl_seconds` (3600, how long an answer is kept; it is also saved in the cache file). The snapshot carries `a2.inconclusive_workflows` (labels) and `a2.inconclusive_details`; `a2.inconclusive` is still the list of repositories. 5 new texts in the 8 languages and a reworded `ui.a2_inconclusive`.

## [1.4.0]

> Cette version n'est disponible qu'en anglais pour l'instant ; la traduction viendra dans une version ultérieure.

- **New layer A11 "Readiness" (read only, real data only):** a panel of the Sentinel tab, a traffic light in its header and two lines of the report. It is switched with `sentinel.readiness.enabled` and described in `readiness.py`.
  - **Release readiness:** one row per repository with at least `candidate_min_entries` entries in `[Unreleased]` (external ecosystems excluded): CI of the default branch (the single rule of A2) with the commit it ran on, whether the version the clone declares (`*.project.json`, else `pyproject.toml`, else the first CHANGELOG heading) is already above the last release, whether a build exists after that release, whether it is signed (the states of A5), and the next step (`fix the red CI`, `wait for run data`, `bump the version`, `build in Actions`, `sign`, `publish`, `cut and publish`). A green CI over a full run sample that may hide an older workflow says so.
  - **Ecosystem health:** per ecosystem, 100 minus weighted counts of red CI, stuck builds, secrets, serious alerts, other alerts, Dependabot PRs older than `stale_pr_days`, builds waiting for signing and repositories with hygiene problems (`sentinel.readiness.health.weights`); the parts that lower the score are listed. No score is shown (`?`) when fewer than `min_coverage` (0.5) of the repositories of the ecosystem have run data and alerts. The report warns when a score is under `warn_below` (70).
  - **Dependency pins:** repositories that pin an older version than the one of the repository that provides the contract or library. Where the pins live is data (`sentinel.readiness.pins.sources`): a JSON table of pins in the provider (`pin_table`) or lock files in the consumers (`lock_files`, the oldest one found counts). Plain file reads of the local clones, cached `pins.refresh_seconds`; an ecosystem without a configured source is listed as having none, and nothing is guessed. The shipped example has no source.
  - 60 new texts in the 8 languages; `tests/test_readiness.py` (rules, weights, coverage, pins on a temporary tree, the page and the 8 catalogues).
- **`docs/CI_RED_SCHEMA.md`:** says explicitly that the PC publishes neither `ci_red.json` nor `pending_sign` to any repository or dashboard (the signing side is local by decision); a public consumer recomputes the rule from the public runs or uses `read_report.py --export-status`.
- **Quota tuning from the log (`actions_monitor_log.txt`, 3 days, 889 samples):** the shared allowance was under the floor (`min_rate_remaining` 1500) in 11% of the samples since 5 November and under 3000 in 45%; the hourly burn was 3000-5000 calls in most hours and reached the limit in some. In the maintainer's `actions_monitor.json`: `refresh_seconds` 120 -> 180 (the real cycle was a median of 139 s) and `sentinel.surface.min_rate_factor` 2.0 -> 1.5 (the cold calls of A10 are about 260 a day, so they can run above 2250; with 3000 they waited almost half of the time). `max_repos_per_tick` (6) and the daily cold cycle stay: they cost less than 1% of the allowance. The shipped example keeps its neutral defaults.

## [1.3.3]

> Cette version n'est disponible qu'en anglais pour l'instant ; la traduction viendra dans une version ultérieure.

- **A2 ignores workflows that never run on the default branch:** when deciding whether a full run sample hides a workflow, the files of the clone whose `on:` has no `push`, `pull_request` or `schedule` for the branch (only `workflow_dispatch`, `release`, tag-only `push` without `branches`, or `workflow_call`) are no longer expected in the sample. `on:` is read with the standard library only (string, list, map, and the YAML `true` key); if it cannot be parsed the workflow counts as before. The workflow scan carries the new field `main_triggered` (`true`/`false`/`null`).

## [1.3.2]

> Cette version n'est disponible qu'en anglais pour l'instant ; la traduction viendra dans une version ultérieure.

- **A2 shows `unknown` instead of green when its sample is full and inconclusive:** a repository whose list of runs is as long as the sample asked for (`runs_per_repo` / `cold_runs_per_repo` of the monitor, which the check did not see before) and whose clone has a workflow file with no run in that sample (or that has no clone) is listed as inconclusive, and A2 is `unknown` unless something is red. New option `sentinel.a2_full_sample_unknown` (default `true`; `false` = only informative as before). The page lists the repositories.
- **`profiles.example.json`:** a neutral batch-profiles template that matches `targets.example.json` and `ecosystems.example.json`. A test (and the release gate) validates it against those catalogues, not the maintainer's, and checks that every profile selects at least one target.
- **Clean-install check in `make_release`:** before anything is left in the output folder the zip is extracted into a new, empty temporary directory and, from there with `python -I`, every member must be present, every module must compile, `read_report.py --version` must run and the whole suite must pass; any gap fails the release.
- **Wording:** README and QUICKSTART in the 8 languages now say that the package writes nothing to GitHub on its own and that only `dispatch --go`, `dispatch --real` and `finalize --execute` (which you run) do.
- **A10 quota:** the share of the sentinel's per-tick call budget that A10 may use is now `sentinel.surface.budget_share` (default `0.5`, as before but configurable); the page shows "A10 paused for quota" with the allowance left and the one needed (`min_rate_remaining` x `min_rate_factor`) while the cold calls wait.

## [1.3.1]

> Cette version n'est disponible qu'en anglais pour l'instant ; la traduction viendra dans une version ultérieure.

- **A run built on another commit is never offered for signing:** when `dispatch` could only find a recent run of another commit (`sha_matched` false), `finalize` now lists it as not ready with the reason and gives no signing command; an old batch without the field behaves as before. Tests with two concurrent runs of different commits.
- **`/api/data` goes through the same Host/Origin guard as the other routes** of the local server (DNS rebinding).

## [1.3.0]

> Cette version n'est disponible qu'en anglais pour l'instant ; la traduction viendra dans une version ultérieure.

Made to be shared: eight languages, authorship and licence in every file, no private data, and nothing tied to one GitHub account.

- **8 languages** (en, es, de, fr, it, ja, zh, pt = European Portuguese) for the page, the command line tools, the launchers, the events, the reports and the error
  messages. `i18n.py` + `locales/<lang>.json` (one flat catalogue per language, standard library only, `t("key", name=value)` with a fallback to English). The language
  is `language` in `actions_monitor.json` (default: the system language, English if unsupported), a selector in the header of the page (remembered by the browser),
  `MONITOR_LANG` / `JUANENRAC_LANG`, or `--lang CODE` in every tool (it wins over the rest). Technical names, commands, paths and the markers that scripts read
  (`SKIP`, `DISPATCHED`, `READY`, `FAILED`, `Summary:`, `BUILD ONLY`, `WOULD DISPATCH`...) are never translated. Events in `events_monitor.jsonl` now carry a stable
  `code` (and `args`) next to the text, so nobody has to parse a language.
- A test checks that the 8 catalogues have exactly the same keys, none empty, the same `{placeholders}`, that every key used by the code and the page exists, and that no
  visible string in the code bypasses `t()`.
- README and QUICKSTART in the 8 languages (`README_<lang>.txt`, `QUICKSTART_<lang>.txt`); `README.txt` is now a short language chooser with the quick start.
- **Authorship and licence**: every source file carries "Copyright (C) 2026 JuanenRac (Electro Hobby 3D)" and "GPL-3.0-or-later - see LICENSE"; JSON data files carry
  `_author` / `_license`; `LICENSE` (GPL-3.0 text), `NOTICE` and `AUTHORS` travel in the zip. `make_release.py` refuses to build when a file lacks them, when private data
  would travel, when the locales differ, or when a launcher loses its executable bit.
- **Shareable**: `github_owner` in the configuration (default: the account of `gh`) replaces the constant that was spread over three modules; the ecosystem prefixes and the
  signing tools are data (`ecosystems.json`, neutral `ecosystems.example.json`; `"*"` = every repository; `"external": true` = only reported) and so are the targets (`targets.json`
  is the maintainer's real catalogue, `targets.example.json` the neutral one; `targets_file` / `ecosystems_file` choose them; keys that start with `_` are metadata).
  The example configuration is neutral. Nothing of this adds a call to the hot cycle.
- **The workspace is optional**: without local clones the monitor starts in a reduced mode (only what the GitHub API gives: no local signing queue, no audit report, no
  CHANGELOG scan) and says so on the page, in the report and at start, instead of stopping. `MONITOR_ROOT` / `MONITOR_AUDIT_DIR` / `MONITOR_SIGNED_DIR` and `signed_dir`
  were added next to the old names. The roadmap layer (A9) is optional too.
- Launchers: menus and messages come from `launcher_msg.py` (your language); comments in English; header on every file.
- Fix: `workspace_root()` no longer ends the monitor when the sentinel starts without a workspace.

## [1.2.0]

> Cette version n'est disponible qu'en anglais pour l'instant ; la traduction viendra dans une version ultérieure.

What was missing and what else can be done on GitHub, all of it read only and local.

**Part A - what was missing**
- `ci_red.json` schema 2 is now a documented contract: `docs/CI_RED_SCHEMA.md` (shape, the one rule of "red", what is for the owner only). Nothing is
  published from the PC. Optional, explicit exports (never a commit or a push): `read_report.py --export-status DIR` writes ONLY the red list
  (`ci_status_public.json/.md`); `read_report.py --export-sign-queue FILE` (.json/.csv) writes the global signing queue with the local commands.
- Attestation: the signing queue shows whether the build has an attestation (existence by digest of the signed files, one lookup per entry, no signature
  check; switch `sentinel.surface.checks.attestation`). A missing one is a line in the report.
- More verified formats: HYDRA `hydra-sign` (`FILE.sig` = base64 Ed25519 over the bytes of the file, the pinned release key, read in blocks) is checked
  definitively; URTC `.imgsig` has its strict format checked (152 hex digits + LF; malformed = not valid) and stays "unknown" when well formed (the signed
  message also needs the build header, which the signed folder does not carry); ARMOR APKs are signed inside the APK by apksigner and stay "unknown".
- `HYDRA-UMC-OS` is labelled on purpose in `targets.json` (`"build_only": true` + `reason`): `plan` lists it under BUILD ONLY and it is no longer an orphan.
  The signing tools were not touched (its workflow takes other inputs and a different signature scheme).
- Fix: `ci_red.target_path` refused every Windows path written with backslashes (`C:\...`); only forward slashes were accepted.

**Part B - the A10 layer "Actions & releases surface"** (`surface.py`, new section of the tab, a switch and a threshold per check under `sentinel.surface`)
- Actions: workflows disabled by hand, schedules with no run in N days (only when the sample of runs covers the window), `uses:` not pinned by SHA
  (reusable workflows flagged apart), `permissions: write-all`, `pull_request_target` with a checkout of the PR, stuck concurrency queues, failures on only one
  OS of a matrix, artifact cost and retention, required status checks that are red or missing (GraphQL), `dispatch --profile release|nightly|hil` with a canary
  (the first target alone, the rest only if it is green) and a quota gate (`--min-rate`, fails closed). Profiles live in `profiles.json`.
- Releases: expected assets per kind of target (alert when a release was published incomplete), tag vs manifest vs CHANGELOG, GitHub Packages, forgotten drafts
  and pre-releases, `release_notes.py` (a DRAFT of notes from the commits since the last tag; it publishes nothing).
- Security: critical/high alerts by age with a ranking of repositories, coverage (a stack without CodeQL/Dependabot), secret scanning open vs resolved,
  Dependabot by priority (runtime major first, CI-only last).
- Issues and PRs: suggestion of `gh issue close` for build issues whose CI is green again (an event with the text; nothing is ever closed), overdue milestones,
  old human PRs, PRs that touch workflows or CODEOWNERS, the merge queue (approved with green checks). Stale board cards: PENDING (needs per-item reads and a threshold).
- Manifest vs evidence (maturity), 8-language README parity failures, Actions minutes per ecosystem in the header, the report and A7.
- `finalize --execute` now tells the running monitor (127.0.0.1) to refresh just the signed repositories and rewrite `ci_red.json` at once (`monitor_link.py`).
- Optional signed webhook receiver (`webhook.enabled`, off by default, 127.0.0.1 only, HMAC with a shared secret from the config, never a GitHub token).
- Cost: nothing in the hot cycle. Cold, spread over ticks and inside the hourly budget: 2 REST calls per repository per day, one GraphQL query per 15
  repositories per day, 3 for Packages, plus the jobs of red runs and the attestation lookups of the signing queue, and only while the allowance is above
  twice `min_rate_remaining`. The hot GraphQL pass asks for 3 more fields per node (alert dates, review decision, checks state): no extra call.
- The gate also compares `sentinel.surface` of the example file with the defaults and validates `profiles.json`.

## [1.1.1]

> Cette version n'est disponible qu'en anglais pour l'instant ; la traduction viendra dans une version ultérieure.

- **Cross-platform:** the monitor and the batch tools work on Windows, macOS and Linux. Launchers `MONITOR_GITHUB_ACTIONS.sh`/`.command` and `BATCH_GITHUB_ACTIONS.sh`/`.command` (the zip keeps the executable permission and make_release rejects Windows line endings in them).
- New `platform_compat.py`: the command that starts a child tool (`py -3` on Windows, the current interpreter elsewhere), the text of the commands that `finalize` shows (cmd/PowerShell or POSIX quoting), UTF-8 console and a notice with the way to install `gh` on each system.
- New tests of the cross-platform part (Windows and POSIX simulated from any system).

## [1.1.0]

> Cette version n'est disponible qu'en anglais pour l'instant ; la traduction viendra dans une version ultérieure.

Signature trust, a stable bridge to the dashboard, orphans and conventions in the batch tools, and a more useful page.

- Signature trust: `sigverify.py` (standard library, read only, no network) checks the signed folder `_firmados/<REPO>/release-<version>/` against the PUBLIC
  key each ecosystem pins (URTC `release_sign.py`, ARMOR helper `PACKAGE_PUBLIC_KEY`, HYDRA updater `RELEASES_PUBLIC_KEY`, or `sentinel.signature_pubkeys`).
  Every state now carries `signature_kind` (none | dev | release) and `signature_verified` (true | false | "unknown"); only a release signature that verifies
  (`trusted`) lowers the pending-signature alert, besides "published". A signature that does not verify keeps the alert and says so in the report.
  `sentinel.require_verified_signature` (default true; false = the 1.0.0 rule). Formats this module cannot check (.sig2, .hdr2, .imgsig, APK, hydra-sign) are
  "unknown", never "false". The build attestation still needs the network and stays with the signing tools.
- `ci_red.json` schema 2: per repository a `pending_sign` list (workflow, hours, state, signature_kind, signature_verified, last_build_at, url) next to the red
  workflows, plus `schema`, `pending_sign_repos` and the threshold; the format is documented in `ci_red.py` and is only ever extended.
- One definition of "last run on main" (`signstate.completed_runs`) shared by the red check, the green-without-release check and the target states.
- `ci_red.target_path` refuses D: paths, WSL/Git Bash forms of D: and drive/UNC paths that the running system cannot use; the tests simulate both systems
  and the whole suite now passes on Linux.
- `gha_dispatch_all.py plan` always ends with the section "Signature orphans" (green CI + known `*-build.yml` + no target); coverage is by repository AND workflow.
- Convention for targets (ecosystem prefix -> default signing tool, workflow in the known list); `targets.json` only holds the overrides and always wins.
  `hygiene --write-candidates` writes the proposed entries to `targets.candidates.json` (never applied by itself, never packaged).
- Page: clickable header counters "red on main" and "unsigned" (filter the repositories; the second one also focuses the signing queue), the signing queue
  with its commands and a copy button, repository panel with build / signed / published, signature kind and verification, and the suggested command;
  a header badge when a minutes budget reaches 80 % (red when exceeded); "yesterday vs today" also compares budget warnings and the lines of the report.

Not done: reading the build attestation / SBOM (network); `HYDRA-UMC-OS` has a build workflow but its signing tool does not support it yet (listed as an orphan).

## [1.0.0]

> Cette version n'est disponible qu'en anglais pour l'instant ; la traduction viendra dans une version ultérieure.

First numbered version. What the package does:

- Monitor of GitHub Actions for the four ecosystems (local web page, run cache, stuck builds, build-failed/build-stuck issues).
- Sentinel layer A (read only, no AI needed): A1 stuck builds, A2 red CI (one criterion: last completed run of each workflow on the default
  branch), A3 CodeQL/Dependabot/secret alerts, A4 Dependabot pull requests, A5 releases (candidates, green builds without a release,
  pending signature), A6 hygiene, A7 consumption (minutes and API allowance), A8 audits and rounds, A9 roadmap boards.
- Explicit state of each build target: built_on_gha -> signed_local (none | dev | release) -> published, with `last_build_at`,
  `last_signed_at`, `signature_kind` and the real hours waiting; local batch and signed-folder records lower the pending-signature
  alert without waiting for GitHub.
- Signing queue of the day (`a5.sign_queue`): most urgent first, with the exact finalize command of each target.
- Budget of Actions minutes per ecosystem (`sentinel.minutes_budget`, empty by default): warning at 80 % in the report and as an event.
- Event feed (`events_monitor.jsonl`) and `ci_red.json` (repository -> red workflows + hours pending signature), written atomically.
- Batch tools: `gha_dispatch_all.py plan|dispatch|status|finalize|hygiene` with `--only` or `--ecosystem`, `plan --json`,
  `finalize --json`, one retry of a failed dispatch at the end of the batch, targets as data in `targets.json`.
- `read_report.py`: the report as plain text from the running monitor, without spending API quota.
- `make_release.py`: quality gate (unit tests, clean zip, complete example configuration, version/changelog agreement) and SHA256SUMS.

Not done in this version: verifying release signatures against the public key and the build attestation from the sentinel
(different signature formats per ecosystem; the attestation needs the network; the signing tools verify both before publishing).
