<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Journal des modifications

Version de l'outil lui-même (moniteur + sentinelle + outils par lots), avec son propre semver. La source est le CHANGELOG.md en anglais ; ce fichier contient les mêmes versions et sections.

## [Unreleased]

### Sécurité

- **Le jeton d'accès ne voyage plus dans l'adresse par défaut (`listen.query_access` est maintenant désactivé)** : en mode réseau, l'adresse avec `?access=` ouvrait la session, mais le jeton restait dans l'historique, les journaux et le `Referer`. Le réglage est désormais désactivé tant que vous ne l'activez pas (la valeur par défaut, le fichier d'exemple et l'aide des Réglages le disent) ; la session s'ouvre par `POST /api/access` (le jeton dans le corps) ou par l'en-tête `X-Monitor-Access`. Une installation qui a écrit `listen.query_access` elle-même garde sa valeur ; celle qui comptait sur l'ancienne valeur et ouvre le moniteur depuis une adresse avec `?access=` doit activer le réglage ou utiliser `POST /api/access`. La variable d'environnement `MONITOR_QUERY_ACCESS=1` l'active pour un service.

### Corrigé

- **La branche, la marque de fork, le dernier push et les PR d'un dépôt parviennent à tous les dépôts, pas seulement au premier** : une fois les exécutions en mémoire (dès le premier cycle), une variable réutilisée dans le tableau des colonnes des dépôts faisait perdre à tous les dépôts sauf le premier ce que la sentinelle savait d'eux. Les forks sans CI propre n'étaient pas reconnus comme tels, leurs crons hérités entraient donc dans la note et le chiffre des forks inactifs valait 1 ; et une CI rouge sur une branche par défaut autre que main ou master pouvait manquer dans la liste des échecs ouverts et dans la santé de l'équipe. La note écarte désormais l'ensemble des forks inactifs (pas seulement les 200 que montre la page).

- **La santé de l'équipe et de la flotte compte toutes les exécutions du cycle, pas seulement les 600 plus récentes du compte** : avec 250 dépôts actifs, 215 affichaient « pas de données » parce que leurs exécutions ne tenaient pas dans la coupe reçue par la page. Les exécutions, les échecs des dernières 24 heures et les exécutions de la semaine sont désormais comptés par dépôt avant la coupe : un compte très actif montre ses dépôts sains comme sains.

- **Un rouge dont le workflow continue de s'exécuter ne vieillit plus jusqu'à « inactif »** : un échec plus ancien que l'âge (30 jours par défaut) était masqué même si des exécutions ultérieures du même workflow avaient été annulées, étaient en cours ou attendaient une approbation. Désormais seul vieillit un workflow qui ne s'est plus du tout exécuté depuis l'échec, et un workflow dont la période naturelle dépasse l'âge (un cron mensuel qui échoue toujours) attend le double de son intervalle habituel avant de le faire.

- **Restes du stockage sous Windows et avec des fichiers endommagés** : l'état des rapports n'est plus réécrit après une lecture qui a échoué (il perdait les autres comptes et leur mémoire) ; un document qui existe et n'est pas compris (un octet endommagé, un fichier coupé) est gardé comme copie .damaged avant d'en écrire un nouveau, au lieu d'être effacé ; un verrou dont le propriétaire est encore vivant n'est pas volé après peu de temps et une suppression refusée ne fait plus tourner à vide le processus qui attend sans regarder son délai ; et le journal des actions et l'audit des accès enregistrent toujours une action quand la rotation est refusée parce qu'un lecteur a le fichier ouvert (les rotations échouées sont comptées).

- **La porte d'empaquetage prouve que le zip est le commit** : en plus de comparer les noms des fichiers avec les fichiers versionnés, elle échoue désormais quand un fichier versionné a été modifié sans être validé (il voyagerait avec la modification), quand deux noms ne diffèrent que par les majuscules (l'un écraserait l'autre sous Windows et macOS) et quand git ne répond pas dans le dossier, au lieu d'ignorer la comparaison sans rien dire (avec --allow-no-git on construit depuis un zip extrait ; la porte signale alors que la comparaison n'a pas été faite).

- **Quatre petites règles font désormais ce que dit leur texte** : la part du budget de requêtes réservée aux dépôts dont la CI est rouge appartient à l'heure et n'est plus accordée de nouveau à chaque cycle (un budget de 100 par heure avec douze dépôts rouges en dépensait environ 880) ; une exécution qui attend un runner à vous éteint reste une panne au lieu de devenir un fantôme au bout de sept jours ; une liste lue par pages garde les pages déjà lues quand une page suivante échoue et dit qu'elle est coupée (les jobs d'une exécution de 240 jobs n'apparaissaient pas) ; et un workflow exécuté après la lecture de ses permissions n'est plus mis à part comme désactivé à la main.

### Modifié

- **Un échec que personne ne répare continue de peser sur la note, et les alertes de collaboration ouvertes comptent avec leur âge** : un workflow resté rouge baissait la part de récupération pendant sept jours, puis la part revenait à 100 quand l'exécution en échec sortait de la fenêtre. On mesure désormais le tronçon du rouge situé dans la fenêtre (la fenêtre précédente a compté le sien, aucun jour n'est compté deux fois) et le registre garde le dernier échec d'un workflow non réparé tant que la règle du rouge le montre. Une alerte de la sentinelle de collaboration encore ouverte à la fin de la fenêtre compte avec le temps écoulé depuis son ouverture : laisser des alertes sans réponse baisse la part collaboration au lieu de la laisser sans données. Après la mise à jour, les notes peuvent être plus basses qu'avant ; le guide de la note l'explique.

- **Un déploiement enchaîné qui échoue sur la branche par défaut est rouge** : les exécutions des événements workflow_run et repository_dispatch comptent désormais dans le rouge d'un dépôt, mais seulement sur la branche par défaut et jamais quand elles viennent d'un fork. Un déploiement enchaîné à la CI qui échouait sur main n'apparaissait dans aucune liste. Le réglage qui nomme les événements (ci.red_events) décide toujours, et sa valeur par défaut et son aide en huit langues le disent.

### Ajouté

- **Les rouges vieillis en inactif sont listés dans la vue de ce qui se passe maintenant** : un rouge qu'aucun des événements qui décident n'a touché pendant le nombre de jours de l'âge (30 par défaut) quitte toujours la liste des rouges, mais une ligne indique désormais combien il y en a et leur liste s'ouvre à partir d'elle (dépôt, workflow et date de l'échec) : un échec ne disparaît jamais sans laisser de trace.

- **Les workflows inactifs sont aussi listés dans la vue de ce qui se passe maintenant** : un workflow qui a échoué et ne s'est pas exécuté pendant les jours de ci.inactive_days (90 par défaut) ne compte plus comme rouge, et une deuxième ligne indique combien il y en a et ouvre leur liste, à côté de celle des rouges vieillis.

## [2.0.8]

### Sécurité

- **Le secret partagé du webhook entrant ne circule que par l'environnement (`webhook.secret_env`, `MONITOR_WEBHOOK_SECRET` par défaut)** : c'était un texte dans `actions_monitor.json`, où une sauvegarde, une configuration copiée ou un écran partagé pouvaient le divulguer. Le récepteur le lit maintenant dans la variable d'environnement indiquée par `webhook.secret_env` (ou dans le fichier nommé par cette variable plus `_FILE`, comme un conteneur remet un secret), le moniteur le retire de son propre environnement une fois lu pour que les programmes qu'il lance ne l'héritent pas, et un secret écrit dans le fichier est ignoré. L'ancienne méthode peut être gardée pour une migration avec `webhook.allow_config_secret` (dans le fichier seulement, éteint par défaut) et la vue En direct avertit tant qu'elle sert. L'onglet Réglages montre le nom de la variable et si le secret est défini, jamais le secret.

### Ajouté

- **Le webhook accepte aussi les événements `check_run` et la vue En direct dit quelle part du temps les événements couvrent l'état** : `check_run` entre dans la liste fermée des événements (`workflow_run`, `workflow_job`, `check_run`, `push`, `release`, `check_suite` et `ping`) ; comme les autres, il marque seulement le dépôt pour une lecture et ne garde aucun texte. La vue En direct et `/api/live-status` (avec les nouveaux `coverage` et `secret_source`) disent si l'état est couvert par des événements (le dernier est plus récent que `savings.webhook_window_minutes`), reste sans événement depuis un moment (dépôt calme ou tunnel perdu) ou attend le premier. L'interrogation reste le secours : un envoi qui n'est jamais arrivé est rattrapé à la lecture suivante.
- **Un guide pour monter le webhook dans GitHub, en huit langues** : `docs/WEBHOOK.md` détaille pas à pas comment créer le secret, le donner au moniteur dans PowerShell, un shell, un service ou un conteneur, quoi remplir sur la page des webhooks de GitHub (adresse, type de contenu, secret, événements) et ce que signifie chaque réponse (`404`, `401`, `413`, `400`, `202` et `429`).

### Modifié

- **Les runners payants d'une autre société que le modèle reconnaît par défaut incluent `codspeed`** (`runners.model.thirdparty_labels`) : les dépôts publics l'utilisent pour leurs mesures de performance et ses jobs étaient comptés comme un runner que personne ne connaissait. Une liste que vous avez écrite vous-même n'est pas touchée.

### Corrigé

- **Les documents ne disent plus que macOS tourne dans le CI** : le README et ses sept traductions disaient que les tests tournent dans le CI sur trois systèmes et que Linux et macOS sont testés dans le CI ; comme le CI ne teste que sous Ubuntu et Windows (macOS sera repris plus tard), ils le disent désormais ainsi.
- **Un workflow dont le fichier a été supprimé ne compte pas parmi les workflows que l'on peut activer** : GitHub garde dans la liste l'historique d'un workflow supprimé avec un chemin vide (six des 96 dépôts publics étudiés en ont un), et la vérification d'hygiène le proposait comme un workflow désactivé à la main. Il reste maintenant hors des listes qui ont besoin d'un fichier.
- **Un fork qui n'a jamais reçu de push n'est pas « poussé récemment »** : un fork hérite de la date de push de son amont à sa création (693 des 722 forks d'un compte mesuré l'ont antérieure à leur propre création), si bien que la sentinelle prenait chaque nouveau fork pour le dépôt le plus actif du compte et le lisait comme chaud. La date de push d'un fork est maintenant ignorée tant qu'elle n'est pas postérieure à sa création.

## [2.0.7]

### Ajouté

- **Une API de lecture sous `/api/v1/` pour les clients (réglage `api.v1_enabled`, désactivé par défaut)** : chaque route de lecture est aussi servie sous le préfixe (même réponse et mêmes rôles, plus l'en-tête `X-API-Version: 1`) et trois routes sont nouvelles : `/api/v1/me` (qui interroge : le mode, l'utilisateur, le rôle et les comptes de la session d'équipe), `/api/v1/repos` (les dépôts surveillés, une ligne chacun, par pages avec un curseur signé, `fields=` et `profile=compact`, gzip quand le client l'accepte) et `/api/v1/openapi.json`. Les nouvelles routes répondent les erreurs dans une seule enveloppe (`error`, un `code` stable comme `api.bad_cursor` et un `message` dans la langue demandée). Tout est en lecture seule, à partir de ce que le moniteur détient déjà. La forme est figée dans la nouvelle section `v1_endpoints` du contrat (`python tools/check_api_contract.py --v1`) ; les limites sont les réglages `api.default_limit`, `api.max_limit`, `api.cursor_ttl_seconds` et `api.gzip_min_bytes`. Textes en huit langues, guide de l'API mis à jour dans toutes et un test avec le vrai serveur.
- **Un workflow que le propriétaire a désactivé à la main n'est plus un rouge (réglage `ci.disabled_apart`, activé par défaut)** : un fork copie le travail nocturne du projet qu'il suit, le travail échoue faute de secrets, le propriétaire désactive le workflow et son dernier run restait en « failure » pour toujours (deux comptes de l'étude l'ont montré). Désormais un workflow à l'état `disabled_manually` sort de la liste des rouges et est compté à part dans le panneau (« désactivés à la main »). Un workflow que GitHub a désactivé pour inactivité n'est pas touché, car ce n'est pas une décision du propriétaire. Texte en huit langues et un test.
- **Le dépôt d'origine de chaque fork peut être suivi (réglage `upstream.enabled`, désactivé par défaut)** : pour un compte qui collectionne les forks, la question utile est ce qui se passe dans les projets suivis, pas de savoir si sa propre CI est verte. Avec l'interrupteur activé, le moniteur lit l'original de chaque fork (l'état des vérifications du dernier commit de sa branche par défaut et sa dernière release) et l'affiche dans le panneau d'hygiène de la Sentinelle ; avec `upstream.notify`, il donne en plus un avis d'information quand l'original est rouge ou a publié une release. Le coût est borné par des réglages du fichier de configuration : `upstream.requests_per_hour` (6), `upstream.forks_per_request` (8), `upstream.refresh_hours` (12), `upstream.news_days` (7) et `upstream.repos` (les forks à suivre ; vide signifie tous). Une requête lit plusieurs forks, les moins récemment lus passent d'abord et rien n'est écrit nulle part. Textes en huit langues et un test avec les cas de l'étude.

## [2.0.6]

### Ajouté

- **Les trois écrans muraux sont dessinés** : Vue d'ensemble (anneau et lettre du score, voyants du parc, graphiques en aires sur 24 heures et 7 jours, une carte thermique par dépôt et par heure, ce qui est rouge depuis le plus longtemps, runners et minutes, les derniers événements et le quota sous forme de jauge), En ce moment (exécutions en cours avec progression, la file, les exécutions en attente d'approbation, les échecs récents, les fusions et versions, et une ligne en direct des deux dernières heures) et Sentinelles (une carte par sentinelle avec son niveau, les constats ouverts, lisible ou non et le dernier balayage, un radar animé et les alertes par gravité). La page dessine elle-même tous les graphiques (sans bibliothèque), les compteurs et les anneaux s'animent, un nouvel échec produit un éclair et les anciens se calment (`screens.blink_calm_minutes`), rien ne bouge pour qui a demandé moins de mouvement, un moniteur qui ne répond pas atténue la page et est réessayé avec des attentes de plus en plus longues, tout se déplace de quelques pixels chaque minute contre la rémanence (`screens.burn_in_protection`), la page peut s'atténuer la nuit (`screens.night_dim`) et une fenêtre peut parcourir les trois pages avec `?rotate=30`. L'onglet Réglages les ouvre par un lien, et un test de navigateur vérifie les trois pages en 1080p, 4K et tournées, dans les huit langues, avec et sans moins de mouvement.

## [2.0.5]

### Ajouté

- **Les forks n'entrent dans l'hygiène, le lint des workflows et le score que s'ils ont leur propre CI (réglages `ci.forks_need_own_ci` et `ci.fork_own_ci_days`, 90 jours par défaut)** : un fork copie les fichiers, les rulesets, les releases et les workflows d'un projet qui appartient à quelqu'un d'autre ; juger son hygiène (pas de ruleset, pas de release, la licence de l'upstream) ou ses fichiers de workflow, c'est juger l'upstream, et un compte qui collectionne des forks (722 dépôts sur 727 dans celui qui a été mesuré, aucun avec ruleset, protection ou release) affichait des centaines d'avertissements et un score fait de bruit. Un fork compte désormais s'il a eu dans la fenêtre une exécution propre par push, pull request, manuelle ou de file de fusion ; une planification héritée ne compte pas, ni la pull request d'un autre fork, ni les exécutions que GitHub crée pour lui-même. Quand la liste de ses exécutions est pleine et ne remonte pas jusqu'au début de la fenêtre, le fork reste dedans, car une exécution propre peut se cacher plus loin. Les forks écartés sont comptés à part (`a6.forks_idle` de la sentinelle, le chiffre d'en-tête `forks_idle`, une pastille dans le panneau d'hygiène), leurs exécutions n'entrent pas dans le score, et avec l'interrupteur désactivé chaque fork est jugé comme avant.
- **Les dépôts dormants et inactifs sont un état à part, ni vert ni rouge (réglage `ci.dormant_repos`)** : un compte qui collectionne des forks a des centaines de dépôts qui n'ont jamais rien exécuté (724 sur 727 dans le compte mesuré), et un dépôt dont l'exécution la plus récente date de plusieurs mois n'est pas sain non plus. Chaque dépôt surveillé est désormais actif, dormant (il n'a jamais rien exécuté de lui-même, sa liste d'exécutions est complète et vide), inactif (son exécution la plus récente est plus ancienne que `ci.inactive_days`) ou inconnu (la lecture a échoué ou la liste est coupée). Ils sont comptés à part dans les chiffres de l'en-tête (`dormant`, `inactive_repos`), dans les données du moniteur et dans l'instantané du score (`activity`), et l'infobulle de la pastille du score dit combien il y en a. Le score est calculé seulement à partir de ce qui tourne. Les workflows que GitHub crée pour lui-même ne sont pas des exécutions du dépôt.
- **Les exécutions en file depuis des jours sont distinguées comme une file fantôme (réglage `ci.stuck.ghost_enabled`, jours dans `ci.stuck.ghost_days`, 7 par défaut)** : sur les dépôts publics, GitHub laisse des exécutions dans la file pendant des semaines ou des mois (une pull request fermée, un job qui demande un runner inexistant ; 280 jours au pire, dans 8 dépôts actifs sur 10). Ces exécutions gonflaient le nombre d'exécutions en file, étaient signalées comme des builds bloqués et alimentaient toute limite apprise depuis la file. Une exécution en file du premier essai plus ancienne que la limite n'est désormais ni en file ni bloquée : elle sort de la liste « Maintenant » et des comptes, une ligne dit combien il y en a, et la sentinelle les liste à part et donne un avis d'information par dépôt (`ci.ghost_queue`), jamais une erreur. L'interrupteur est activé par défaut ; désactivé, toute exécution en file est traitée comme avant.

### Modifié

- **Un rouge non traité vieillit après 30 jours et devient inactif (réglages `ci.red_ages` et `ci.red_age_days`)** : un fork copie le job nocturne du projet qu'il suit, le job échoue chaque nuit faute des secrets, le propriétaire désactive le workflow, et la dernière exécution reste « échec » pour toujours, si bien que le dépôt était rouge pour toujours (41 exécutions sur 42 et 26 sur 27 dans les deux cas mesurés, la dernière datant de presque un an). Jusqu'ici seul un workflow qui ne s'était pas exécuté du tout pendant `ci.inactive_days` (90) jours cessait d'être rouge, et un workflow qui continuait à exécuter des pull requests ne le faisait jamais. Désormais une exécution échouée de plus de `ci.red_age_days` jours (30 par défaut), sans rien de plus récent parmi les événements qui décident, quitte la liste des rouges et est listée comme inactive ; les lignes disent qu'elle a vieilli. L'interrupteur est activé par défaut ; désactivé, un rouge reste rouge jusqu'à ce que le workflow repasse au vert.
- **Le contrôle d'hygiène de la branche par défaut juge par défaut les règles en vigueur (`sentinel.hygiene.ruleset_mode` vaut maintenant `effective`)** : auparavant la branche n'était protégée que si un ruleset actif portait un nom exact (`protect-main`), ce qu'aucun compte étudié n'utilisait (aucun des comptes étudiés ne nommait ainsi ses rulesets, et 32 dépôts sur 96 protègent la branche de façon classique). Par défaut, une branche compte désormais comme protégée quand GitHub signale une règle ou une protection pour elle, quel que soit son nom. Le contrôle lit la branche et ses règles, deux requêtes de plus par dépôt à chaque renouvellement de l'hygiène. Mettez `name` pour rétablir l'ancienne règle. Un profil qui demande l'ancienne règle la garde.

### Corrigé

- **La protection de la branche par défaut est jugée sur toutes les sources publiques, pas seulement sur les règles des rulesets** : 32 des 96 dépôts publics étudiés ont une branche par défaut protégée de façon classique, ce que `rules/branches` ne montre pas, si bien qu'une liste de règles vide était lue comme « sans protection ». En mode `effective`, la réponse de la branche donne désormais aussi sa `protection` classique (si elle est activée et avec quelle rigueur s'appliquent ses vérifications de statut, lisible sans droits d'administrateur) et les trois sources sont jointes ; une branche n'est non protégée que si elles ont répondu et qu'aucune ne la protège, et une réponse qui n'est pas venue (délai dépassé, lecture refusée, champ absent) reste « non évaluable ». Chaque ligne du panneau d'hygiène dit ce qui protège la branche (`protection` : ruleset, classic, both ou none).
- **Les workflows que GitHub crée pour lui-même ne sont ni une CI en rouge ni des fichiers** : les entrées dont le chemin commence par `dynamic/` (mises à jour de Dependabot, graphe de dépendances, CodeQL par défaut, revue et agent de Copilot) échouaient indéfiniment dans 20 des 96 dépôts publics étudiés et étaient comptées comme des workflows du dépôt (rouges, abandonnés, « désactivés »). Le moniteur ne gardait que le nom de fichier d'une exécution, si bien que le test du chemin ne correspondait jamais ; désormais le chemin entier est retenu à la lecture de l'exécution. Ces workflows ne décident jamais de la couleur d'une branche, ne comptent pas comme workflows à vérifier et ne figurent pas parmi les workflows désactivés à la main ou par inactivité. Une mise à jour de Dependabot qui échoue est listée à part comme avertissement, et les autres (Copilot, CodeQL, graphe de dépendances) comme information, dans `a2.services` de la sentinelle et dans le chiffre d'en-tête `services_failing`.
- **La recherche d'un workflow masqué (A2) suit la même règle d'origine que le reste du rouge** : quand l'échantillon d'exécutions est plein, la dernière exécution d'un workflow est demandée à part, et cette réponse prenait n'importe quelle exécution de la branche, y compris celle d'une pull request d'un fork, d'une issue ou d'un commentaire (le filtre `exclude_pull_requests` de GitHub ne les retire pas, car l'exécution d'un fork n'a pas de pull request associée). Désormais la réponse ne garde que les exécutions d'un événement de `ci.red_events` qui ne viennent pas d'un fork, les exécutions que GitHub crée pour lui-même ne sont plus prises pour des workflows du dépôt, et l'événement est conservé avec la réponse. Les tests utilisent les formes mesurées sur sept dépôts publics.
- **Les questions se posent dans la page et s'affichent donc en plein écran** : les cinq confirmations de la page (changement de mode, exécution d'une commande proposée par l'IA, une action GitHub, un lancement de workflow local, suppression d'un utilisateur) utilisaient la boîte de dialogue du navigateur, qui ne s'affiche pas en plein écran (il fallait appuyer sur Échap pour la voir) et bloque la page. Elles utilisent maintenant une seule boîte de dialogue de la page (`askConfirm`) avec Accepter et Annuler, Échap et Tab, le focus sur Annuler pour une action dangereuse et rendu ensuite. Un test échoue si un `confirm`, `alert` ou `prompt` natif revient, et un test dans un navigateur pose la question et répond à la souris et au clavier.

## [2.0.4]

### Ajouté

- **Un modèle pour chaque tâche, une chaîne de secours et un budget pour chaque modèle, pour l'IA du moniteur** (tout est désactivé tant que ce n'est pas écrit dans les réglages, et seulement parmi les fournisseurs que vous nommez) : `ai.tasks.build.model` (et de même pour `codeql`, `report`, `diagnose` et `alert`, chacun avec son fournisseur et ses limites) fait répondre un autre modèle à ce type de question ; `ai.fallback` liste les modèles essayés dans l'ordre quand le principal échoue (toute erreur, une clé refusée, un modèle inexistant, une erreur de quota, ou une réponse lente si `ai.fallback_after_seconds` est défini) ou a quitté le catalogue, et `ai.fallback_max_attempts` borne toute la chaîne ; les appels par jour de chaque modèle (`ai.model_daily_limit`) et le coût estimé de chaque modèle et au total (`ai.model_cost_limit_daily`, `ai.cost_limit_daily`, seulement quand les prix sont connus) sont des budgets en plus de `ai.daily_limit`, et un modèle dont le budget est épuisé est ignoré, jamais dépassé. Le premier échec du modèle principal est écrit dans le journal et dans le résumé avec sa raison. Sans rien de réglé, le seul modèle général répond comme avant.
- **Alertes, Rapports et Leçons sont trois entrées du menu de gauche** : les rapports facultatifs et les leçons tirées des échecs étaient des sections au bas de l'onglet Alertes ; chacun a maintenant sa propre entrée avec son icône, son badge (rapports : dépôts avec des constats et releases bloquées ; leçons : celles qui s'appliquent maintenant) et son adresse (`#reports`, `#lessons`, aussi `?view=reports` et `?view=lessons`). Rien n'a été perdu ni répété, les anciennes adresses (`#alerts`, `#alerts/reports`, `#al/lessons`) ouvrent le bon panneau, un panneau de rapports sans aucun activé le dit au lieu de disparaître, et les écrans peuvent lister les nouveaux onglets dans `ui.screen1_tabs` (`rep`, `les`). Les guides nomment les nouvelles entrées du menu dans les huit langues.

### Corrigé

- **« Aide de cet onglet » ouvre dans chaque onglet le sujet de l'onglet ouvert** : la table d'onglet à sujet n'avait pas les onglets Alertes et Équipe et envoyait Dépôts et Historique vers le premier sujet de l'aide (« GitHub Actions Monitor »). C'est maintenant une seule table (`TAB_TOPICS`) avec une entrée pour chaque onglet du menu latéral, et un test échoue si un onglet n'a pas de sujet ou en a un qui n'existe pas. Un test dans un navigateur parcourt tous les onglets et appuie sur le bouton.
- **L'onglet Historique n'accumule plus son compteur** : « Affichage de 200 sur N » s'ajoutait aux outils du tableau à chaque rafraîchissement alors que les outils n'étaient redessinés que lorsque l'ordre ou les colonnes changeaient, si bien que des milliers de copies s'accumulaient à côté de la liste des colonnes. Le compteur est maintenant un seul élément qui est remplacé ou retiré. Un test ouvre la page dans un navigateur, dessine le tableau de nombreuses fois (rafraîchissement, filtres, toutes les colonnes, un ordre) et vérifie qu'il y a un compteur et une indication.

## [2.0.3]

### Sécurité

- **Chaque lien que la page construit à partir de données passe par le filtre d'adresses** : les liens vers la dernière exécution, le dépôt, le tableau, l'issue, l'échec non résolu et l'avis de mise à jour n'ouvrent qu'une adresse `https` de GitHub ou de l'hôte configuré ; tout le reste devient un `#` inerte.

### Ajouté

- **Les écrans muraux sont désactivés par défaut** : `screens.enabled` reste désactivé tant qu'il n'est pas activé dans les Réglages ; `/screen/overview`, `/screen/now` et `/screen/sentinels` répondent donc 404 sur une nouvelle installation.
- **Écrans muraux : les adresses, les réglages et les données** (les trois pages sont `/screen/overview`, `/screen/now` et `/screen/sentinels`, pour un moniteur ou un téléviseur que personne ne touche) : elles ne lisent que ce que le moniteur détient déjà via `/api/screens/data` (une liste fermée de champs : jamais GitHub, jamais un lien, un titre de commit, un nom de job ou d'utilisateur), elles se désactivent avec `screens.enabled` (toutes les adresses répondent alors 404), les noms des dépôts privés suivent `screens.show_repo_names` (masqués par défaut), les échecs clignotent moins de deux fois par seconde et se calment après `screens.blink_calm_minutes` (`screens.blink`), et une fenêtre ne peut qu'être rendue plus calme par son adresse (`?blink=off` ; `?sound=on` seulement si `screens.sound` l'autorise) ou réglée avec `?monitor`, `?theme`, `?density`, `?refresh`, `?lang`, `?scale` et `?rotate`. Aussi `screens.default_theme`, `screens.default_density`, `screens.refresh_seconds`, `screens.rotate_seconds`, `screens.burn_in_protection` et `screens.night_dim` (docs/SCREENS.md).
- **Vue de flotte pour des centaines de dépôts** : l'onglet Équipe a une nouvelle section qui groupe les dépôts (par écosystème, par étiquette, par état ou pas du tout), les trie (par risque, nom, dernière exécution ou état) et les dessine page par page, de sorte qu'un compte de 250 dépôts garde la page légère. Les étiquettes sont des motifs de noms de dépôt (`fleet.labels`, par exemple `team-*=backend`), ce qui permet aussi de distinguer organisations ou équipes ; `fleet.saved_filters` garde des filtres prêts à l'emploi ; `fleet.group_by`, `fleet.sort` et `fleet.page_size` fixent les valeurs par défaut. Elle lit `GET /api/team/fleet` (lecture seule, la même santé que le classement de l'équipe) ; le classement au-dessus ne change pas.
- **Types de runner, leur file et leur coût, workflows emballés et runners auto-hébergés en panne** : avec `runners.model.enabled` activé, les étiquettes (`runs-on`) des jobs distinguent les runners hébergés par GitHub, grands, payants de tiers et auto-hébergés (`runners.model.thirdparty_labels`, `runners.model.large_labels` et `runners.model.self_labels` rendent la taxonomie vôtre). Réglages > Avancé montre la file par type, les minutes et le coût par type (une minute de tiers n'est chiffrée que si `runners.model.thirdparty_usd_per_minute` est défini, et GitHub ne la facture jamais), les workflows démarrés au moins `runners.model.runaway_runs_per_hour` fois dans la dernière heure et les jobs qui attendent un runner auto-hébergé `runners.model.queue_warn_minutes` minutes ou plus avec la raison (aucun runner en ligne n'a leurs étiquettes, tous ceux qui conviennent sont occupés, ou un runner libre ne les prend pas). Les deux avertissements sont des alertes (`runners.model.alerts`, niveau `runners.model.alert_level`, `warning` par défaut) ; lecture seule, désactivé par défaut, il lit `runners.model.jobs_per_cycle` exécutions par cycle via `GET /api/runners/model`. Avec `finops.jobs_per_cycle` activé, un job sur un runner de tiers n'est plus chiffré comme un job hébergé par GitHub.
- **Les entrées d'un workflow lancé à la main sont listées avant de lancer quoi que ce soit** : `plan --inputs` du répartiteur par lots montre, sous chaque cible, les entrées que demande son workflow (nom, type, obligatoire ou facultative, valeur par défaut, options d'un choix et description), lues dans le fichier du workflow à `origin/main` du clone. Rien n'est déclenché ni envoyé ; `--json` ajoute une liste `inputs` à chaque ligne (`null` si elle n'a pu être lue). Une nouvelle section du guide recense les limites connues : échantillons d'exécutions, plan qui reste `unknown` pour les dépôts privés et gratuits, un propriétaire par moniteur et la file de fusion.
- **Couverture honnête de la liste d'exécutions** : le tableau des dépôts a une nouvelle colonne, *L'échantillon remonte*, qui dit jusqu'où dans le temps va la liste d'exécutions de chaque dépôt. Une liste pleine qui remonte moins de `sampling.min_coverage_minutes` (30 par défaut ; 0 le désactive) est marquée *couverture faible* au lieu de paraître complète, une liste plus courte que demandé est *complète*, et un total où GitHub cesse de compter (2 500 ou 40 000) est affiché comme *au moins*. Un avis au-dessus du tableau compte les dépôts à couverture faible ; le bloc `sampling` de `GET /api/data` porte les mêmes chiffres.
- **Second regard sur la branche par défaut** (`sampling.default_branch_probe`, désactivé par défaut) : quand la liste d'exécutions d'un dépôt est pleine, une requête de plus demande les push vers sa branche par défaut sans les pull requests, afin que les exécutions qui décident du rouge sur main ne soient pas chassées par les pull requests et les planifications. Les exécutions que seul le second regard a trouvées ne font jamais compter une liste comme pleine.
- **Budget de requêtes par heure** (`sampling.api_budget_per_hour`, 0 = aucun) : au-delà, les dépôts avec un workflow rouge sont lus en premier et les autres attendent l'heure suivante, et la page dit combien attendent. La page montre aussi les requêtes par heure qu'exigent le nombre de dépôts et les intervalles (à partir de 3 500, ou dès qu'un budget est fixé), pour avertir un grand compte avant qu'il n'épuise son quota.
- **Les longues listes sont lues jusqu'au bout, et une coupure est dite** : les workflows d'un dépôt (148 ou 348 sont des cas réels), les jobs d'une exécution (une matrice de plus de 100) et les issues et pull requests ouvertes d'un dépôt sont désormais lus page par page tant que la dernière était pleine, jusqu'à `pagination.workflow_pages`, `pagination.job_pages` et `pagination.collab_pages` pages de 100. Un dépôt qui tient dans une page coûte les mêmes requêtes qu'avant. Quand quelque chose reste dehors, la page dit « N vus sur M » : sous l'exécution pour ses jobs, dans l'hygiène du dépôt pour ses workflows, et dans le pied de l'onglet Équipe pour les dépôts qui ont plus d'éléments ouverts que ceux lus et pour le compte quand l'API de recherche a plus que ses 1000 résultats.
- **Un test de charge avec un compte synthétique** : 250 dépôts et 1 250 workflows, sans réseau, mesure les requêtes d'un cycle, le temps du cycle et de la santé de l'équipe, la mémoire des données gardées et le nombre de requêtes que demandent les recherches A2, avec des bornes larges pour qu'un ordinateur chargé réussisse.
- **Renovate compte comme Dependabot, et le linter distingue vos actions de celles de tiers** : les pull requests de `renovate` sont listées dans A4 comme mises à jour de dépendances (`sentinel.dependency_bots` nomme les comptes), et un dépôt avec une configuration Renovate n'est pas signalé comme dépourvu de bot de mise à jour. `lint.own_owners` et `lint.unpinned_own` marquent une action non épinglée comme à vous ou de tiers et peuvent abaisser ou masquer les vôtres ; trois règles optionnelles, désactivées par défaut, trouvent un job sans `timeout-minutes` (`lint.rules.no_timeout`), `secrets: inherit` (`lint.rules.secrets_inherit`) et une action à vous qui suit `@main` (`lint.rules.own_action_main`).
- **Les bots à part des personnes** : avec `sentinel.bots_apart` activé, les pull requests des comptes que GitHub marque lui-même comme bots (type Bot, pas une supposition d'après le nom) sont comptées à part dans A4 (`other_bots`) et écartées du contrôle des vieilles pull requests en attente d'une personne ; les exécutions portent désormais `actor_bot`. La valeur par défaut ne change rien.
- **Profils** : Réglages > Base et la troisième étape du guide de premier démarrage proposent trois groupes de réglages prêts (propriétaire ou équipe, organisation open source, développeur solo) qui fixent en un clic le contrôle d'hygiène, les forks et dépôts archivés, le linter, le contrôle des fichiers des releases et le comptage à part des bots ; les valeurs suivent le même chemin contrôlé que le bouton Enregistrer, rien ne change tant qu'un profil n'est pas choisi, et `GET /api/settings` les liste comme `presets`. Une recette pour les grands comptes se trouve dans le nouveau guide `docs/LARGE_ACCOUNTS.md`.
- **Les skills pour les IA ne nomment aucun assistant, expliquent comment se connecter selon le type d'outil et portent la version du moniteur** : une nouvelle référence et un tableau du guide *Connecter un outil d'IA* disent quelle voie convient à quel outil ; `GET /api/skills` répond `monitor_version`.
- **Les modèles du fournisseur d'IA sont lus, vérifiés et mesurés au lieu d'être saisis à l'aveugle** : Réglages > IA externe charge la liste du fournisseur par une requête en lecture seule, vérifie le nom, garde fenêtre de contexte, prix et outils de chaque modèle et peut tester un modèle avec un échec synthétique ; `monitor_cli.py ai models`, `ai test` et `ai doctor` font de même.
- **Les rouges à cause racine unique sont annoncés une fois, et une exécution rouge dit quels jobs ont échoué** (désactivé par défaut) : `ci.group.reusable` regroupe en une ligne et une notification les workflows rouges qui appellent le même workflow réutilisable ; `ci.failed_jobs` nomme les jobs en échec par plateforme.
- **Un long build n'est pas « bloqué » parce qu'il est long, et une exécution bloquée dit pourquoi elle attend** : `ci.stuck` peut apprendre la limite de chaque workflow de ses propres exécutions, fixer des limites par workflow ou par étiquette de runner et donner leur propre limite aux exécutions qui attendent un runner ; tout est désactivé par défaut.
- **Moins de bruit quand il y a beaucoup d'alertes** (bloc `alerts`, désactivé par défaut) : silences permanents par motif avec raison et date de revue, une classe pour les services qui échouent de temps en temps, une notification par commit et un résumé périodique.
- **Le linter de workflows et les contrôles de surface fonctionnent sans cloner les dépôts** : `lint.source` sur `auto` lit `.github/workflows` par l'API de contenu et `sparse` utilise un clone partiel ; la valeur par défaut reste `clone` ; le panneau A13 dit ce qui a été lu et ce qui n'a pas pu être évalué.
- **`lint_workflows.py --remote OWNER/REPO`** lit les fichiers de workflow d'un dépôt depuis GitHub avec `gh`, sans clone, et dit pourquoi quand il ne peut pas.
- **Aide pour les organisations et les gros comptes** : `--doctor` dit pourquoi la lecture d'une organisation revient vide et estime les lectures par heure face au quota ; un nouveau guide, `ORGANIZATIONS.md`, donne le jeton minimal et les étapes SSO.
- **File de fusion** : une exécution échouée de la file de fusion de la branche par défaut est un rouge à part, affiché « (merge queue) », et s'efface avec la prochaine exécution verte de la file.
- **Branches de maintenance** : `ci.extra_branches` accepte des motifs comme `release-*` de branches supplémentaires dont la dernière exécution compte aussi ; un rouge d'une telle branche porte son nom.

### Modifié

- **Les tests du dépôt ne s'exécutent plus sous macOS pour le moment** : le job macOS a été retiré du workflow de CI (chaque pull request, chaque push sur main, chaque étiquette et l'exécution nocturne testent sous Ubuntu et Windows), et le workflow indique que la prise en charge de macOS sera reprise plus tard. Rien ne change dans le moniteur.
- **A2 règle beaucoup de workflows avec une seule requête** : pour un dépôt ayant au moins `sentinel.a2_resolve_batch_min` workflows à rechercher (2 par défaut ; 0 = un par un), on demande une seule fois ses exécutions terminées les plus récentes de la branche par défaut, sans pull requests, et tous les workflows qui y figurent sont réglés ensemble (`sentinel.a2_resolve_batch_pages` pages de 100 au plus) ; ce que la liste ne montre pas est demandé un par un comme avant, si bien qu'un dépôt de 100 workflows ou plus converge en quelques cycles au lieu de quatre workflows par cycle.
- **Les forks et les dépôts archivés se choisissent par un réglage, et un fork entretenu n'est jamais perdu** : `discovery.skip_archived` (activé par défaut) décide si les dépôts archivés sont surveillés ; `discovery.fork_policy` peut écarter les forks (`skip`) ou ne garder que ceux qui ont une CI propre (`skip_unless_ci` : un workflow activé et une exécution dans `discovery.fork_ci_days`), et `auto` fait de même avec une fenêtre deux fois plus longue pour une organisation, dont le type est lu une fois par jour ; `discovery.fork_checks_per_pass` limite les requêtes dépensées. La valeur par défaut (`show`) ne change rien.
- **La vérification des fichiers d'une release s'adapte au projet** : `sentinel.surface.checks.release_assets.require_sha256` et `.require_signature` cessent d'exiger un fichier de somme ou de signature, `.allow_empty` accepte une release sans fichiers (projets qui publient dans un registre de paquets), `sentinel.surface.checks.tag_vs_version.prefixes` compare des étiquettes comme `cli-v1.2.0` au manifeste, et `.prerelease_ok` traite les bêtas d'un jour d'une version calendaire comme la même version ; `sentinel.require_verified_signature` était déjà désactivable. Les valeurs par défaut exigent la même chose qu'avant.
- **La santé de l'équipe est rapide avec des milliers de dépôts** : les exécutions, les workflows rouges, les exécutions en cours et les alertes sont regroupés une seule fois par dépôt, si bien qu'une requête de santé de l'équipe ne les parcourt plus tous pour chaque dépôt (2 000 dépôts prenaient environ huit secondes), et la santé d'un dépôt ne construit que sa propre vue.
- **La forme figée de l'API descend d'un niveau** : les clés des objets imbriqués des réponses en lecture, le `code` de l'erreur d'un dépôt inconnu et l'enveloppe des réponses des sentinelles font partie du contrat ; l'outil de contrôle suit les objets imbriqués.
- **Un rouge sur la branche par défaut ne compte que si le dépôt lui-même l'a causé** : seules les exécutions des événements `push`, `schedule`, `workflow_dispatch` et `merge_group` décident (`ci.red_events`), et une exécution de pull request venant d'un fork jamais (`ci.count_fork_runs`).
- **Une exécution qui attend une approbation est un état à part, ni un rouge ni une file** : `action_required` et un job retenu par un environnement ne rendent plus un workflow rouge ; l'onglet Maintenant affiche une ligne « en attente d'approbation ».
- **Un workflow abandonné est « inactif », pas rouge pour toujours** : un workflow dont la dernière exécution a échoué et qui ne s'est pas exécuté depuis `ci.inactive_days` jours (90 par défaut) quitte la liste des rouges.
- **Les workflows qui ne réagissent qu'aux issues, commentaires ou étiquettes ne comptent pas comme CI rouge** : ils se distinguent par leurs événements (`ci.automation_counts`, désactivé par défaut) ; chaque ligne rouge dit de quel type de workflow il s'agit.
- **La porte de release vérifie le zip contre les fichiers versionnés** : le zip doit contenir exactement les fichiers que le dépôt versionne dans le dossier du produit ; un fichier versionné qui ne voyagerait pas ou un fichier en trop arrêtent la release.
- **L'hygiène (A6) ne suppose plus les conventions d'un seul propriétaire** : le nom du ruleset est un réglage (`sentinel.hygiene.ruleset_names`), la branche par défaut peut être jugée d'après les règles en vigueur, un contrôle peut être omis et ce que le jeton ne peut pas savoir est affiché comme non évaluable ; les valeurs par défaut gardent l'ancienne règle.

### Corrigé

- **Un groupe des pastilles de préparation dit pourquoi il n'a pas de chiffre, et un dépôt sans aucun workflow ne baisse plus sa couverture** : un dépôt dont le clone n'a aucun fichier de workflow et qui n'a aucune exécution est « non applicable » : il est exclu de la couverture de son groupe (un groupe de cinq dont deux sont neufs et vides se mesure donc sur les trois autres) et listé à part dans l'infobulle et dans le tableau. Un groupe encore sous `sentinel.readiness.min_coverage` affiche les mots « données insuffisantes » (et non un « ? » muet) et son infobulle dit combien de dépôts ont des données face au minimum et lesquels en manquent. Le minimum par défaut ne change pas.
- **Le score du compte dit combien dure le calibrage et pourquoi il manque quelque chose** : pendant le calibrage, la pastille indique ce qu'il reste de `score.calibrating_hours` avec une barre et le jour et l'heure où le chiffre apparaîtra (`data_quality.calibrating_hours` est nouveau) ; « données insuffisantes » indique la condition qui échoue (exécutions ou couverture), et `GET /api/score` porte `missing_detail` avec la raison pour laquelle une partie n'est pas comptée (sa sentinelle est éteinte, elle n'a pas fini son premier balayage et combien de dépôts elle a lus, elle en a lu trop peu, ses sources sont illisibles, ou les données sont prêtes pour le prochain passage).
- **L’anneau des dernières 24 heures compte à partir d’une seule source et n’affiche jamais un nombre négatif** : le total au centre et les trois chiffres de la légende (réussies, en échec, annulées ou autres) viennent du serveur (`figures.done24` est nouveau) et leur somme est toujours exacte ; avant, le total était compté sur la liste des exécutions reçue par la page, qui ne contient que les plus récentes, et « annulées ou autres » devenait négatif. Un chiffre négatif ou qui n’est pas un nombre est dessiné comme 0, et si le serveur n’envoie pas le total, les trois chiffres sont comptés sur la liste et la carte indique qu’il s’agit d’un échantillon. Le taux de réussite par dépôt le dit aussi lorsque sa liste est un échantillon.
- **Une horloge reculée n'arrête plus la note, la purge ni les rapports programmés** : un instant enregistré qui se trouve dans le futur (un ordinateur sans horloge à pile qui démarre avec une vieille date, ou une horloge corrigée à la main) n'est plus cru ; le passage est dû aussitôt et écrit un bon instant, au lieu d'attendre des jours que la vieille horloge l'atteigne.
- Le job en échec d'une exécution de plus de 30 jobs est trouvé : les listes de jobs que lisent l'avis pour une IA, l'assistant et l'outil par lots étaient coupées à 30 et le sont maintenant à 100 (la même requête unique).
- **Un registre de score illisible n'est jamais écrasé** : quand le registre existe mais reste illisible après les nouvelles tentatives, le passage horaire ne fait rien et note le problème dans la santé ; le dernier bon registre est conservé.
- **Le calendrier des rapports à ses limites** : l'heure qui se produit deux fois en automne ne produit plus deux rapports, un rapport mensuel ou annuel dû est tout de même écrit, et un rapport dont le second format échoue ne laisse pas le fichier du premier.
- **Le journal des actions note aussi ce qui est confirmé sur GitHub et sur cet ordinateur** : relances, annulations, déclenchements et fusions, une exécution avec `act`, changements de jeton, découverte, leçons, rapports, changements de connexion et actions de l'IA ; chaque route POST est journalisée ou listée comme exemptée, sinon un test échoue.
- **Plusieurs processus qui écrivent le même fichier refonctionnent sous Windows** : le propriétaire d'un fichier de verrou réessaie de le supprimer pendant environ une seconde et un verrou de moins d'une seconde n'est pas ouvert ; les écrivains du flux, du journal et des rapports n'échouent plus sous charge.
- **Un fichier de verrou laissé par un écrivain mort est repris aussitôt** : le verrou porte le numéro de son processus ; quand il n'existe plus, l'écrivain suivant prend le verrou immédiatement et la reprise est journalisée (sinon l'âge décide, réglable avec `MONITOR_LOCK_STALE`).
- **Les durées et attentes des workflows relancés ne sont plus absurdes** : elles se mesurent sur la dernière tentative (`run_attempt`) ; une durée supérieure aux 35 jours que peut durer une exécution reste vide ; `ci.rerun_timing` (désactivé par défaut) demande à GitHub la durée réelle.
- **Un essai après une approbation n'est pas « instable »** : une exécution qui a eu besoin d'une approbation puis a réussi, et les exécutions de pull requests de forks, ne comptent plus comme workflows instables.

## [2.0.2]

### Sécurité

- **Un seul nettoyeur pour tout ce qu'une IA peut lire** : le texte que l'assistant intégré envoie à un fournisseur, le dépôt, le workflow, le lien et la conclusion de chaque alerte, `GET /api/ai/state`, `GET /api/ai/alerts`, `GET /api/ai/brief?fmt=json`, le fichier du flux, son fichier d'état et le corps du hook passent par le même nettoyeur (avant, un mot de passe dans `DB_PASSWORD=...`, un utilisateur et une clé dans une adresse, une clé `sk-`, un jeton, une adresse e-mail, une adresse IP ou le dossier personnel pouvaient sortir). Un test plante un secret de chaque sorte et échoue si l'un apparaît dans l'une de ces sorties.
- **L'assistant intégré garde sa clé et reste sur cet ordinateur** : un appel à un fournisseur ne suit plus une redirection (la clé serait partie vers l'autre adresse ; la redirection est signalée comme la réponse du fournisseur) et n'utilise plus les variables de proxy de l'environnement, de sorte qu'un serveur local comme Ollama est vraiment appelé en direct. Un fournisseur distant passe par le proxy seulement avec `network.use_proxy`.
- **Le nettoyeur connaît plus de formes de secret** : blocs de clé PGP, `--password valeur` et `mysql -phunter2` dans une ligne de commande, cookies, `Authorization: Basic ...`, `ENCRYPTION_KEY=`, `SENTRY_DSN=` et `AWS_CREDS=`, une valeur avec guillemets échappés, une phrase après `password:`, un jeton coupé par un saut de ligne, clés `sk_live_`, adresses IPv6 compressées, partages réseau et dossier de root ; le texte caché derrière un encodage (codes de pourcentage, caractères de largeur nulle, lettres pleine chasse) est aussi nettoyé, et une paire dont la clé dit que c'est un secret (`{"password": ...}`) est remplacée en entier. C'est un nettoyeur par motifs : le guide et les skills ne promettent plus que rien ne peut passer.
- **Le texte de tiers est une donnée, pas une instruction** : la ligne que le script de porte d'un outil d'IA copie pour chaque alerte ne garde le nom du dépôt que s'il en est un et réduit le nom du workflow à un texte court et simple ; une leçon écrite par une IA se place entre les délimiteurs de données non fiables dans le prompt de l'assistant intégré ; le texte d'un inconnu (le titre d'une issue) ne mentionne personne dans Discord et est échappé pour Slack.
- **Apprise** : les dossiers restants avec les adresses des services sont balayés au premier envoi, une virgule dans une adresse ne la coupe plus et chaque adresse est écrite entre guillemets.
- **Le fichier de préréglages est validé comme la page des réglages** : seuls les champs de la liste sont servis, les adresses doivent être acceptées par la page, un préréglage cloud ne peut pas pointer vers cet ordinateur ni vers une adresse privée, et la variable de la clé ne peut pas être une variable du système ou du moniteur (`GH_TOKEN`, `PATH`, `MONITOR_*`...) ; la même règle s'applique au réglage `ai.api_key_env`.
- **Le processus de chaque compte ne garde plus dans son environnement la clé du superviseur ni le jeton d'accès** : les deux quittent l'environnement dès le début de chaque processus (moniteur, superviseur et compte), avant le lancement du premier `gh` ou d'un autre programme, même quand le jeton d'accès porte un autre nom. Le commentaire qui promettait de cacher les secrets de la liste des processus de Linux indique maintenant sa vraie limite.
- **L'image ne peut plus emporter les données de celui qui la construit** : le contexte de construction excluait les fichiers isolés de l'ancienne structure mais pas les dossiers `config/`, `data/`, `logs/` et `ai/` où vivent maintenant les jetons, utilisateurs, sessions et réglages ; ils sont exclus, l'étape applicative du Dockerfile les supprime aussi et un test vérifie les deux contre la liste des dossiers du produit.
- **Trois visiteurs avec de mauvais jetons ne peuvent plus bloquer tout le monde derrière le proxy inverse** : le verrou partagé par tout le proxy ne compte que les requêtes qui arrivent sans `X-Forwarded-For` exploitable ; une requête qui porte l'adresse de son visiteur est comptée contre cette seule adresse, le verrou partagé prend fin après la durée de blocage et n'arrête jamais une requête qui porte le bon jeton d'accès.
- **La durée d'une connexion ne révèle plus quels noms sont des utilisateurs** : un utilisateur verrouillé coûte le même travail qu'un nom qui n'existe pas, donc « verrouillé » répond dans le même temps pour les deux.
- **Un chemin sous `/api/accounts/` que le superviseur ne filtre pas est jugé comme n'importe quelle autre route** : seuls la liste, l'état et l'identifiant d'un compte sautent la vérification de compte de la porte, et l'identifiant d'un compte est refusé à un utilisateur qui ne peut pas voir ce compte.
- **Le journal des actions garde une seule chaîne quand plusieurs processus écrivent le même fichier** : chaque ligne est chaînée à la dernière ligne réellement présente dans le fichier, lue sous un verrou entre processus (seule la fin du fichier est lue), et ce verrou attend aussi quand Windows répond « accès refusé » pendant qu'un autre processus supprime le fichier de verrou.
- **Le journal des actions est un fichier par compte** : dans l'édition Complète avec plusieurs comptes, les processus de comptes différents écrivaient le même `audit_actions.jsonl` (et un administrateur d'un compte pouvait lire des lignes d'un autre) ; chaque compte garde maintenant son propre fichier dans son dossier et `GET /api/audit-log` ne garde que les lignes du compte qui répond. Les lignes écrites avant restent dans l'ancien fichier partagé, que le superviseur lit toujours.
- **La vérification du journal des actions couvre aussi le fichier tourné** : `chain` vérifie `audit_actions.jsonl.1` et le lien entre lui et le fichier actif, nomme le segment (`segment`) quand une ligne est rompue, indique combien de segments il a vérifiés (`segments`) et si la chaîne commence à son premier maillon (`complete`).
- **Le journal des actions ne peut plus être lu par un lecteur, et il enregistre davantage de l'essentiel** : la route exige à la porte au moins le rôle de mainteneur (un administrateur, ou un mainteneur quand `audit_log.maintainers_can_read` est activé, décide encore à l'intérieur), éteindre le journal écrit sa propre dernière ligne, une ligne qui ne peut pas être écrite est comptée et montrée (`write_failures`, `last_write_error_at` dans `GET /api/audit-log` et un avis de dégradation), et les changements ratés de son propre mot de passe restent dans l'audit des accès au lieu de remplir le journal des actions.

### Ajouté

- **L'événement de notification `ai_alert`** : une nouvelle alerte réelle d'un panneau ou d'un signal du moniteur peut atteindre les canaux de notification (ajoutez `ai_alert` à `notify.events` ; désactivé par défaut). Un workflow rouge garde son propre événement, `red_new`.

### Modifié

- **Le score pénalise maintenant une panne qui n'est pas réparée** : la part de récupération compte un workflow encore rouge à la fin de la fenêtre avec le temps pendant lequel il est rouge jusqu'ici (une borne inférieure qui grandit tant que le rouge dure), au lieu de l'écarter. Avant, un compte qui ne réparait jamais son rouge pouvait avoir un meilleur score qu'un compte qui le réparait en un jour. Attendez-vous à des nombres plus bas pour les comptes qui ont un workflow rouge à la mise à jour. `docs/SCORE.md` l'explique dans les huit langues.

### Corrigé

- **Le score et le registre du score** : une relance d'une exécution compte comme une exécution de plus (GitHub garde l'id, donc la première conclusion restait pour toujours) ; le calcul ne divise plus par zéro quand aucune part n'a de données (la réponse est `insufficient_data` avec la raison `no_data`) ; quand le registre abandonne des exécutions au-delà de 20000 et que cela atteint la fenêtre actuelle, l'instantané le dit (`data_quality.truncated`) ; la moyenne de `GET /api/score/global` écarte les instantanés périmés (comptés dans `accounts_stale`) et `/metrics` n'exporte pas `ghamon_score` pour eux ; et le guide du score décrit maintenant cinq parts, avec `score.weights.security`, dans les huit langues.
- **La sentinelle Sécurité ne prend plus « illisible » pour « propre »** : quand la plupart des sources qui pèsent dans la pénalité (Dependabot, analyse de code, secrets) répondent 403 ou 404 pour chaque dépôt, le niveau est `unknown` au lieu de `ok` et la part sécurité du score est écartée au lieu de compter 100 (l'état porte `sources_readable` et `sources_total`). Une source qui cesse de répondre alors qu'une alerte est ouverte garde l'alerte une semaine, marquée comme non lue, et ne l'annonce jamais comme corrigée ; un `gh` qui n'imprime rien est une lecture échouée, et une branche par défaut avec une barre oblique dans son nom est demandée encodée.
- **Quelques dépôts qui échouent toujours n'affament plus la sentinelle Sécurité** : un dépôt dont les lectures échouent attend 5 minutes, 30 minutes puis 6 heures avant l'essai suivant, et ceux qui n'ont pas encore été essayés passent en premier, si bien que le reste du compte est regardé.
- **Un dépôt que les sentinelles n'ont pas pu regarder n'est plus affiché OK dans la santé de l'équipe** : quand chaque sentinelle est en erreur, en pause ou dégradée (ou toutes éteintes sans rien d'exécuté depuis une semaine), un dépôt calme est `unknown` (« Non vu »), les lignes du classement portent `not_fully_seen` avec les noms des sentinelles qui n'ont pas pu le lire, les totaux les comptent, et l'onglet Équipe marque l'état d'un astérisque et d'une info-bulle. Un workflow rouge ou une alerte le laissent en `warn` ou `bad`.
- **Un octet endommagé dans le flux d'événements n'arrête plus les notifications** : au-delà de 512 Ko le flux était relu en UTF-8 strict pour le réduire, un seul octet invalide levait une erreur qui s'échappait, le flux grandissait sans limite et chaque nouvel événement échouait avant d'atteindre les canaux. La réduction lit maintenant avec tolérance et ne peut jamais arrêter les canaux.
- **Un fichier en cours d'utilisation n'est plus lu comme vide dans le stockage de fichiers** : sous Windows une sauvegarde, un antivirus ou un éditeur peut retenir un fichier un instant ; le lecteur le prenait pour vide et l'enregistrement suivant écrivait par-dessus (utilisateurs, enregistrements du registre du score, instantanés du score, analyses). Un fichier qui existe est relu plusieurs fois, et celui qui lit pour modifier et enregistrer s'arrête avec une erreur au lieu d'écraser. Plusieurs processus qui ajoutent au même flux d'événements prennent un verrou entre processus, si bien qu'aucune ligne n'est perdue ou coupée sous Windows.
- **Répéter `migrate_storage` ne remplace plus des données plus récentes dans la cible** : un compte dont la cible a des événements ou instantanés plus récents est signalé `target newer`, refusé sans rien écrire, et le code de sortie est 1 ; `--force` fait gagner la source. L'exécution imprime aussi un avertissement avec le nombre de lignes endommagées du flux d'événements qu'elle ne peut pas copier (la source les garde).
- **Une sauvegarde est vérifiée entièrement avant qu'une restauration n'écrive quoi que ce soit** : un id de compte ou un nom invalide n'importe où dans la copie fait échouer `verify`, si bien qu'une restauration ne peut plus s'arrêter à mi-chemin avec les premiers comptes déjà écrits.
- **Une réponse du serveur MCP plus longue que sa limite reste un document valide** : des lignes de la plus longue liste sont écartées au lieu de couper le texte, la réponse indique `truncated` et combien de lignes manquent, et les signaux de santé (données anciennes, moniteur dégradé, quota) partent en dernier.
- **Un nombre qui n'est pas un nombre ne coupe plus la connexion** : `?since=`, `?limit=` et `Last-Event-ID` n'acceptent que les chiffres 0-9 (et au plus 15) ; tout le reste est la valeur par défaut.
- **L'état des rapports planifiés est partagé en sécurité par plusieurs comptes** : chaque compte modifie son entrée sous un verrou, et un remplacement qu'un lecteur bloque un instant sous Windows est réessayé.
- **Les tableaux des skills disent quels appels sont réservés à cet ordinateur** : le tableau est généré à partir des mêmes listes que celles du serveur, et `/api/ai/failures` liste son POST. Un rapport ne porte plus de titres bruts : les titres des alertes passent par le nettoyeur et Markdown ne transforme pas une adresse en lien de lui-même.
- **Le contrat de l'API couvre maintenant `/api/data` et ne peut pas être amputé** : la route qui donne les exécutions, les dépôts et le quota n'était pas dans le contrat gelé. Elle l'est maintenant, les routes lisibles mais non gelées sont listées sous `unfrozen` avec leur raison, un test échoue quand une nouvelle route GET n'est dans aucune des deux listes, et un autre compare le contrat à celui de la première version 2.x pour qu'un chemin, une clé ou un type ne puisse pas disparaître dans le même commit qui casse l'API.
- **La fenêtre d'un dépôt ouverte depuis l'onglet Équipe n'affichait rien** : une ligne du classement ne porte que le nom, et la page demandait la santé du dépôt avec un propriétaire vide ; elle utilise maintenant le propriétaire de la page. Le lien direct `?view=repo&repo=owner/name` ne remplit plus non plus le filtre de texte de l'onglet Maintenant avec le dépôt, ce qui laissait cet onglet vide.
- **Un nom de workflow, de job ou de dépôt avec des crochets ne casse plus les vues de terminal** : `test [ubuntu, 3.13]` s'affichait `test`, `docs [/api]` terminait la vue sur une erreur, et un nom pouvait porter des styles ou des liens du terminal. Les noms sont dessinés en texte simple dans les deux vues, et une image qui ne peut pas être dessinée est ignorée au lieu de terminer la vue.
- **Une touche Entrée vide dans le menu du lanceur par lots Windows répétait la dernière option** : choisir 2 puis appuyer à nouveau sur Entrée relançait tout le lot une seconde fois, car `set /p` garde l'ancienne valeur quand rien n'est saisi. La variable est vidée avant chaque question, et un test exécute le vrai lanceur.
- **Les scripts avec shebang avaient des fins de ligne Windows dans le zip publié** : les 33 fichiers `.py` qui commencent par `#!` (dont les points d'entrée de `bin/`) ne pouvaient pas être exécutés directement sous Linux ou macOS quand le zip était construit sous Windows. Le zip les porte maintenant avec LF et la porte de publication échoue si l'un a encore un CR sur sa première ligne.

## [2.0.1]

### Corrigé

- **Le zip publié n'avait pas le fichier des préréglages d'IA** : l'empaquetage inclut désormais tous les fichiers de données du paquet et la porte de publication échoue si l'un manque dans le zip.

- **Une clé d'état non traduite sur la page de tous les comptes** : les deux clés manquantes sont maintenant dans les huit catalogues, et un test vérifie que chaque clé `ui` utilisée par la page existe dans les huit catalogues.

## [2.0.0]

### Ajouté

- **Le contrat de l'API de lecture, figé à partir de maintenant** : `docs/schemas/api_contract.json` liste les 37 points d'accès en lecture avec les clés et les types de leurs réponses dans chaque édition (et lesquels l'édition Lite refuse avec `404`) et les codes d'erreur de la porte (`401 access`, `403 forbidden`, `404`). Une clé listée garde son nom et son type pendant toute la 2.x ; de nouvelles clés peuvent apparaître et rien n'est retiré sans nouvelle version majeure. La suite `test_200_contract.py` le vérifie contre un vrai serveur de chaque édition, ainsi que les règles de la porte : un `Host` étranger donne `403`, le mode réseau demande le jeton dans l'en-tête `X-Monitor-Access` et répond `401 access` sans lui, les mots d'une requête que personne ne lit sont ignorés et toute réponse est du JSON en UTF-8.

- **Un outil pour vérifier n'importe quel moniteur en marche contre le contrat** : `python tools/check_api_contract.py` (`--lite`, `--url`, `--token-file`) lit le contrat, interroge le moniteur avec `GET` seulement, affiche une ligne pour chaque clé manquante ou d'un autre type et finit par `CONTRACT=PASS` ou `CONTRACT=FAIL` (code de sortie 0, 1, ou 2 si personne ne répond). Il s'adresse à ceux dont les scripts, écrans muraux ou clients mobiles dépendent des réponses, après chaque mise à jour du moniteur ou du client. Il n'appelle pas GitHub.

- **Les interfaces des sentinelles et des stockages sont aussi figées par un test** : `test_200_interfaces.py` fixe les neuf champs d'une `Alert`, les méthodes de `BaseSentinel` et de `Storage` avec les noms de leurs paramètres, les types d'enregistrement et le fait que les deux stockages et les trois sentinelles implémentent chaque méthode. Un changement ici est un changement de contrat.

- **Un guide pour chaque usage, en huit langues** : Complète pour une personne (`COMPLETE_INDIVIDUAL.md`), Complète en service (`COMPLETE_SERVICE.md`), Complète pour une équipe (`COMPLETE_TEAM.md`) et l'API pour les clients (`API.md`), à côté du guide court de l'édition Lite. Ils sont dans le panneau d'aide et dans la liste des guides du README, et un test vérifie qu'ils existent en huit langues, que leurs liens se résolvent et que chaque réglage et point d'accès cité existe. Un second test lit chaque guide de la documentation dans les huit langues et échoue si l'un nomme une route que le code n'a pas.

### Modifié

- **Version 2.0.0, le moniteur est déclaré mûr** : désormais les points d'accès en lecture, l'`Alert`, `BaseSentinel` et `Storage` ne changent qu'avec une nouvelle version majeure (un ajout que les anciens clients peuvent ignorer est permis et noté ici). Le message du produit est le même dans le README, les guides et l'aide : Lite est l'édition simple pour une personne sur un ordinateur, Complète est le centre de contrôle (plusieurs comptes, une équipe, un service et des clients). Rien d'autre ne change dans le comportement du moniteur dans cette version.

## [1.9.5]

### Ajouté

- **Les événements en direct comme flux (Complete, désactivé par défaut)** : avec `live.sse.enabled` actif, `GET /api/live-events/stream` envoie les événements du webhook entrant dès leur acceptation, en événements envoyés par le serveur : une trame `hello` (combien sont gardés), une trame `live` par événement avec un `id` croissant (reprise via `Last-Event-ID` ou `?since=` ; seule la liste fermée de champs de `GET /api/live-events` est envoyée), un commentaire de maintien et un `bye` final. Lecture seule, il demande le jeton d'accès en mode réseau comme toute requête, accepte au plus `live.sse.max_clients` écouteurs (les suivants reçoivent `429`), chacun pendant `live.sse.max_seconds`, et l'édition Lite ne l'a pas. Les trois réglages sont dans l'onglet Réglages (sous-onglet Webhook entrant) avec leur aide en huit langues, le guide du webhook entrant l'explique et les références des deux skills listent le point d'accès. Un test avec un vrai serveur couvre le désactivé par défaut, la limite d'écouteurs et un événement accepté qui atteint l'écouteur.

### Modifié

- **`/api/health` en dit plus, et `?deep=1` en demande plus** : en plus de `ok`, `version`, `loaded` et `offline`, la réponse porte l'état du cycle d'actualisation (`cycle`), de l'accès GitHub (`credential`) du compte et l'endroit où le moniteur écoute (`listening`) ; le superviseur répond avec les mêmes mots. `/api/health?deep=1` est le contrôle approfondi : 503 quand le cycle d'actualisation d'un compte est bloqué ou a disparu et, dans le superviseur, aussi quand sa boucle s'est arrêtée, quand le cycle d'un compte quelconque est bloqué ou quand aucun compte ne répond après le démarrage. Sans `deep`, rien n'échoue qui n'échouait pas avant.

- Les types de notification `credential_blind` et `credential_back` sont nouveaux ; `credential_blind` figure dans la liste par défaut et dans la configuration d'exemple. L'onglet Alertes, `/api/alerts` et la ligne de commande connaissent le niveau `critical` et la sentinelle `system`, et une alerte critique est listée en premier.

- `--doctor` distingue aussi l'accès de chaque compte par son propre fichier d'identifiants, de sorte que deux comptes ayant chacun reçu un remplacement ne sont pas signalés comme partageant un jeton.

- Les délais de la porte de publication sont de 3600 secondes par défaut (ils étaient de 900 et 1800, trop courts pour un ordinateur chargé). `MONITOR_RELEASE_TEST_TIMEOUT` et `MONITOR_RELEASE_CLEAN_TIMEOUT` les modifient (de 60 à 86400 secondes), et la valeur par défaut est lue quand la porte s'exécute, pas au chargement du module.

### Ajouté

- **Image Docker officielle et mode service** : `deploy/Dockerfile` est en plusieurs étapes (la CLI GitHub depuis son dépôt apt signé, le code compilé sans les tests, et une image finale avec seulement Python, `gh`, les certificats des CA et le code, en lecture seule et appartenant à root). Elle s'exécute avec l'utilisateur 10001, jamais root, avec deux volumes (`/config` et `/data`), `tini` comme init et un contrôle de santé qui est l'approfondi. `python -m github_actions_monitor.service` prépare à partir de variables d'environnement documentées tout ce qu'une personne fait à la main avant le premier démarrage : la configuration, le premier compte (ou plusieurs avec `MONITOR_ACCOUNTS`), les clés de `listen` et `auth` et un jeton d'accès créé une fois, conservé en mode 600 et jamais affiché. `MONITOR_CONFIG` place le fichier de configuration hors du code.

- **Compose avec proxy inverse, et systemd** : `deploy/compose.yaml` (code en lecture seule, sans capacités, l'accès comme secret Docker) avec un Caddy facultatif devant (`deploy/Caddyfile` ; TLS automatique pour un nom public, son autorité pour un nom privé, ou aucun), `deploy/.env.example` et, pour une installation classique, `deploy/github-actions-monitor.service` avec son fichier env (durci, relancé en cas d'échec, contrôle la santé approfondie après le démarrage, relit les fichiers d'identifiants sur `systemctl reload`). Le guide `DEPLOYMENT.md` dans les huit langues liste chaque variable d'environnement, le premier démarrage comme service, la sauvegarde, la mise à jour et la vérification de l'attestation de l'image.

- **Image pour `linux/amd64` et `linux/arm64` dans ghcr.io** : le workflow `release-image.yml` la construit et la publie quand une version est publiée (ou à la main), avec les permissions minimales de chaque job, chaque action épinglée par commit, une limite de temps sur chaque job, les étiquettes `X.Y.Z`, `X.Y` et `latest` et une attestation de la provenance. Publier est une étape à part que seule une version déclenche : le même workflow construit sans publier quand il est lancé à la main avec `push` désactivé, et la CI construit l'image à chaque changement.

- **Un contrôle de santé approfondi** : `/api/health?deep=1` (voir plus haut), `python -m github_actions_monitor.cli.healthcheck` pour un conteneur ou un gestionnaire de services (codes de sortie 0, 1, 2 et 3) et `monitor_cli.py health --deep` depuis n'importe quel ordinateur. Un compte dont l'accès GitHub est inutilisable est nommé mais n'est pas une panne : un redémarrage ne répare pas un accès perdu.

- **Un accès que GitHub révoque ou laisse expirer rend aveugle ce seul compte** : après deux refus de suite disant que l'accès lui-même est inutilisable (401, `Bad credentials`, jeton expiré ou révoqué, compte suspendu, aucun accès), le compte est aveugle ; les autres continuent. La page, `/api/accounts` (`state: blind`), le contrôle de santé et la ligne de commande le disent, une alerte critique du système (`system.credential_blind`) s'ouvre une fois, les canaux sont prévenus une fois (`credential_blind`, et `credential_back` quand cela refonctionne) et le compte continue d'essayer. Le refus d'une permission (un 403 pour un dépôt) ne rend pas un compte aveugle. Un service qui démarre avec un accès déjà inutilisable reste actif et aveugle au lieu d'abandonner.

- **L'accès peut être remplacé sans rien redémarrer** : le point d'accès `/api/accounts/<id>/credential` (une session `admin` en mode équipe ; sinon l'ordinateur du moniteur), `monitor_cli.py credential replace --account ID --new-token-file FICHIER` (ou `-` pour l'entrée standard ; un jeton n'est jamais pris dans une option) et SIGHUP là où le système l'a (chaque compte relit ses fichiers d'identifiants). Le nouveau jeton est vérifié auprès de GitHub AVANT d'être gardé, donc un jeton que GitHub refuse ne change rien ; un bon jeton est gardé seulement dans le dossier de ce compte (mode 600) et utilisé aussitôt. `GH_TOKEN_FILE` nomme un fichier pour l'accès de tous les comptes, lu au démarrage et sur SIGHUP. Le jeton n'est jamais dans une réponse, un journal, une alerte ni l'audit.

- **Le superviseur de plusieurs comptes écoute en mode réseau** comme le moniteur d'un compte : le jeton d'accès sur chaque requête (cookie, en-tête ou `/api/access`), verrouillage après de mauvais jetons, la vérification de `Host`, un TLS facultatif avec votre certificat, le second port de la personne devant la machine (`listen.local_port`), et les clés qui décident de l'exposition, l'accès à GitHub et les actions sur GitHub seulement depuis l'ordinateur du moniteur (le compte traite une requête venue du réseau comme distante).

- **La page et les outils disent où le moniteur écoute** : cet ordinateur, le réseau ou derrière un proxy (`listen.proxy_public_host`, `listen.secure_cookie`, `listen.trusted_proxy`), dans la barre du bas de la page, dans `/api/accounts`, `/api/health` et les premières lignes de `monitor_cli.py status` et `monitor_cli.py accounts`.

- **La ligne de commande fonctionne contre un moniteur d'un autre ordinateur** : `--url` ou `MONITOR_URL`, `--ca-file` ou `MONITOR_CA_FILE` pour faire confiance à l'autorité d'un certificat HTTPS à vous et, en mode équipe, `--user` avec `--password-file` (ou `MONITOR_USER`, `MONITOR_PASSWORD_FILE`) pour se connecter avec une session Bearer (`auth.allow_bearer`). `status` et `accounts` se terminent par le code de sortie 3 pour un compte aveugle.

- **Tests** : un test du conteneur dans la CI qui construit l'image, la démarre en lecture seule et sans root, révoque l'accès de l'un de deux comptes et vérifie que seul ce compte devient aveugle, que l'alerte critique s'ouvre, que le contrôle de santé approfondi reste au vert, qu'un jeton refusé ne change rien, qu'un bon jeton ramène le compte sans redémarrage et que SIGHUP fait de même ; et un test de régression pour chaque comportement d'un accès révoqué (le compte, les autres comptes, l'alerte, l'avis, le remplacement, le fichier, SIGHUP, les rôles, l'audit et le jeton qui n'apparaît jamais).

### Corrigé

- Le test d'un compte qui meurt aussitôt ne dépend plus de la vitesse de l'ordinateur : l'attente avant de relancer un compte est vérifiée avec une horloge que donne le test lui-même, et un second test vérifie le calendrier des attentes sans lire l'heure réelle (l'ancien échouait sous charge dans la porte d'une version).

## [1.9.4]

### Ajouté

- **Préréglages de fournisseurs d'IA et un tableau d'IA compatibles** : un fichier de données versionné (`ai_presets.json`, servi en lecture seule sur `GET /api/ai/presets`) liste douze services hébergés (OpenAI, Anthropic, Google Gemini, xAI Grok, Mistral, DeepSeek, Groq, OpenRouter, Together AI, Fireworks AI, Perplexity, Cohere) et six serveurs locaux (Ollama, LM Studio, serveur llama.cpp, vLLM, LocalAI, Jan) avec des modèles d'exemple modifiables (Llama, Mistral, Qwen, DeepSeek, Gemma, Phi, gpt-oss ; ni poids ni téléchargements). Dans les réglages de l'IA, un sélecteur remplit le fournisseur, l'adresse, le NOM de la variable d'environnement de la clé et un modèle, montre la confidentialité du choix (texte envoyé par internet ou gardé sur cet ordinateur) et indique « compatible par protocole, non testé avec cet outil » quand c'est le cas ; aucun n'est actif par défaut et la clé ne quitte jamais sa variable d'environnement. Un serveur de cet ordinateur (`http://127.0.0.1:...`) peut être enregistré comme `ai.base_url` et fonctionner sans clé ; une adresse distante exige toujours https et sa clé. Les trois guides de l'IA portent le tableau dans les huit langues, et un faux serveur au protocole OpenAI teste les réponses 200, 401, 429 et un délai dépassé, la clé étant absente de toute sortie.

## [1.9.3]

### Ajouté

- **Apprise comme canal de notifications (Complete, désactivé par défaut)** : `notify.channels.apprise` confie le message à la commande `apprise`, si elle est installée, pour atteindre tout service qu'Apprise connaît. Les adresses (elles contiennent les secrets de ces services) sont lues dans la variable d'environnement que désigne `urls_env`, écrites dans un fichier temporaire privé le temps de l'appel puis supprimées, jamais mises dans les arguments, et la commande reçoit un environnement sans les clés du moniteur. Apprise ouvre ses propres connexions : la protection du moniteur contre les adresses privées ne s'applique donc pas ; le canal a son propre interrupteur, marqué comme réglage de sécurité. Si la commande manque, la raison est `not_installed` ; un échec est compté et n'arrête jamais le moniteur.

- **Un journal des actions (Complete seulement, activé par défaut)** : à côté de l'audit des accès, `logs/audit_actions.jsonl` garde une ligne JSON pour chaque changement (qui, quoi, quand, sur quel compte) : un changement de réglages (les noms, jamais les valeurs), un silence et sa levée, un changement d'utilisateurs, de mots de passe, de préférences de notification ou d'identifiants. Chaque ligne porte le hachage de la précédente, si bien qu'une ligne modifiée, retirée ou insérée après coup est repérée (`GET /api/audit-log` dit où la chaîne se rompt) ; au-delà de `audit_log.max_mb`, l'ancienne partie est gardée dans un fichier de plus et la chaîne continue. Aucune valeur ni aucun secret n'est jamais écrit. Un administrateur le lit, un mainteneur seulement si `audit_log.maintainers_can_read` est activé. Trois réglages dans l'onglet Sentinelle et le guide AUDIT_LOG.md dans les huit langues.

- **Rapports planifiés (Complete seulement, désactivés par défaut)** : le moniteur écrit un rapport du compte selon un horaire cron (`report_schedule.cron`, cinq champs en heure locale, `0 8 * * 1` par défaut) ou quand un administrateur le demande sur cet ordinateur : le score (sans nombre pendant le calibrage ou avec trop peu de données), ce qui a changé depuis le dernier rapport, les dépôts qui demandent une personne et les alertes ouvertes, sous forme de page HTML avec style d'impression (un PDF est l'impression en PDF du navigateur) et de Markdown. Il est fait avec ce que le moniteur détient déjà, ne demande rien à GitHub et n'envoie rien : les fichiers restent dans `data/reports/`, les séries les plus anciennes disparaissent après `report_schedule.keep`, un rapport est écrit par minute planifiée (un long arrêt en donne un, pas un tas), le premier attend la première minute planifiée après l'activation, un échec est noté et retenté à la suivante, et tout texte venant des données est échappé. L'onglet Équipe liste les fichiers et a le bouton « Écrire un rapport maintenant » ; les routes sont `GET /api/report-files`, `GET /api/report-files/file?name=` et `POST /api/report-files/run`. Cinq réglages et le guide REPORT_SCHEDULE.md dans les huit langues.

- **Un banc et les reproductions de la revue indépendante, dans le dépôt** : `tools/audit_harness.py --check` démarre, sans GitHub, un superviseur avec trois comptes (alpha, beta, default) et quatre utilisateurs (administrateur, mainteneur d'alpha seulement, lecteur de beta seulement et un désactivé), interroge les routes qui décident l'isolement des comptes et imprime ce que reçoit chaque utilisateur ; `tests/test_193_regressions.py` garde les reproductions de la revue de la 1.8.3 (comptes d'une requête, comptes conservés au changement d'un mot de passe, silences d'un mainteneur distant, le message d'essai et sa limite horaire, une copie restaurée et les sessions révoquées, le verrouillage et l'administrateur, les clés qu'un programme lancé n'hérite pas).

- **Un test ne lit plus un fichier de celui qui l'a écrit** : la vérification avec le vrai fichier du dépôt de profil ne s'exécute que lorsque `MONITOR_REAL_CENTRAL_FILE` dit où il est, et les tests qui lisent les outils de la racine du dépôt sont ignorés quand ils ne sont pas dans le dossier du produit.

## [1.9.2]

### Ajouté

- **La santé de chaque dépôt et de l'équipe (Complete seulement)** : à partir de ce que le moniteur détient déjà (exécutions, workflows rouges et bloqués, alertes ouvertes des trois sentinelles et préparation des versions), on calcule un état par dépôt (mauvais, avertissement, bon ou non vu) et un nombre de risque ; un dépôt qu'aucune sentinelle n'a regardé ou qu'une n'a pas pu lire n'apparaît jamais comme bon et dit par qui il n'a pas été entièrement vu. `GET /api/repos/<owner>/<repo>/health` donne le détail et `GET /api/team/health` le classement, les totaux, les chiffres par écosystème et par sentinelle et les filtres (écosystème, gravité minimale, morceau du nom). Elles n'appellent jamais GitHub.

- **L'onglet Équipe et le détail d'un dépôt** : le classement avec les dépôts qui demandent une personne en premier, trois filtres, et au clic sur un dépôt une fenêtre avec sa CI, ses alertes, la version et l'activité ; les liens directs `?view=team`, `?view=repos` et `?view=repo&repo=owner/name` (avec `chrome=0` pour les écrans muraux) ouvrent chaque vue. L'édition Lite ne l'a pas.

- **La commande `team`** : `monitor_cli.py team` affiche le classement (`--severity warn|bad`) et `team --repo owner/name` le détail d'un dépôt, avec `--json` ; en lecture seule et depuis les mêmes routes que la page. Le guide HEALTH.md, dans les huit langues, explique tout.

## [1.9.1]

### Ajouté

- La sentinelle de sécurité (Complete seulement, désactivée par défaut) : la troisième sentinelle lit, sans rien écrire sur GitHub, les alertes ouvertes de Dependabot, de l'analyse de code et de l'analyse des secrets, si la branche par défaut est protégée, si les workflows reçoivent l'écriture par défaut et, si on le demande, s'il y a un fichier CODEOWNERS, et lève une alerte par dépôt et par signal dans l'onglet Alertes (origine Sécurité), avec les décomptes par gravité. Une source que GitHub ne renvoie pas pour un dépôt est listée comme illisible et n'est jamais prise pour un certificat de bonne santé. Elle a son propre cycle, un plafond de dépôts par tour, des lectures conditionnelles et une pause tant que le quota est bas, écrit les évènements security_new et security_fixed pour les canaux de notification, a une boîte dans l'onglet Sentinelle, dans les préférences de chaque utilisateur et dans les réglages, une route /api/sentinel/security et un guide dans les huit langues.

- Chaque sentinelle indique son cycle de vie : sain, dégradé, en pause, en erreur ou désactivé, pour qu'« aucune alerte » ne soit pas confondu avec « n'a pas pu regarder ».

- La sécurité est une partie du score : les points que les constats ouverts de la sentinelle de sécurité retirent à 100 forment la cinquième partie, avec son poids (`score.weights.security`, 25 par défaut) et ses propres limites ; elle ne compte que tant que la sentinelle est active et a examiné assez de dépôts, et sans elle la réponse dit que le nombre n'est pas complet et les autres parties sont remises à l'échelle.

- Les poids par défaut du score deviennent 30, 15, 15, 15 et 25 (fiabilité, rapidité, rétablissement, collaboration, sécurité).

- Une fenêtre avec des exécutions et aucun échec n'a rien à rétablir : la partie rétablissement est pleine, comme un fait et non plus comme une donnée manquante.

## [1.9.0]

### Ajouté

- Le score de chaque compte (Complete seulement) : un nombre de 0 à 100, une lettre de A à E et une tendance, construits à partir de la fiabilité de la CI, de la rapidité, du rétablissement et de la collaboration. Quand il ne peut pas justifier un nombre, il dit « calibrage » ou « données insuffisantes », et il donne toujours la couverture, la qualité des données et ce qui ne compte pas encore (la sécurité), si bien qu'un 85 ne se lit pas comme « tout va bien ».

- Les réglages du score dans la page des réglages (fenêtre en jours choisie par l'utilisateur, calibrage, minimum d'exécutions et de couverture, poids, seuils des lettres et alerte en cas de baisse), dans les huit langues.

- Un instantané du score chaque heure dans les deux stockages (schéma 2 de la base, la migration se fait en une seule transaction), inclus dans l'export, la sauvegarde, la migration entre stockages et la rétention.

- `GET /api/score` et `GET /api/score/history` : le nombre, la lettre, la tendance, les parties, la couverture, la qualité des données, ce qui manque et la ventilation par dépôt ; qui peut voir un compte lit son score, et seul un administrateur change les réglages.

- Une pastille dans l'en-tête de la page avec le nombre, la lettre, la tendance et une petite courbe des derniers jours ; neutre et avec la raison quand il n'y a pas de nombre, et avec une étoile tant qu'une partie ne compte pas.

- La commande `score` de la ligne de commande, avec `--compare` pour la comparer à l'historique de la fenêtre.

- L'alerte `score.dropped` quand le score baisse de 10 points ou passe à une lettre inférieure (critique à E) : elle apparaît dans l'onglet Alertes, peut être mise en sourdine et ne sort par les canaux de notification externes que si on le demande.

- `GET /api/score/global` du superviseur : la moyenne des comptes notés que le demandeur peut voir, à titre d'information seulement et avec qui y entre.

- Le score pour d'autres outils : trois séries sans étiquettes dans les métriques, l'outil `get_score` du serveur MCP, des panneaux du score dans le tableau Grafana d'exemple et un score inventé dans `--demo`.

- Un guide du score dans les huit langues.

### Modifié

- L'aide est à jour de toute la série 1.8 et de la 1.9.0 : le README du dépôt et ses sept traductions disaient la version 1.8.1 et rien de ce qui a suivi ; maintenant la version du tableau En un coup d'œil est écrite par le générateur à partir de la version de l'outil, Ce qu'il fait nomme le mode service et l'image Docker, plusieurs comptes et l'équipe, le stockage, les listes qui se trient et se plient et le score, le tableau d'état a les lignes des nouveautés, la section Sécurité dit comment les modes réseau et équipe sont protégés, la Documentation liste tous les guides, les guides de la ligne de commande, des outils d'IA et des métriques nomment le score, et la feuille de route ne présente plus la série 1.8 comme la prochaine version. Un nouveau test et une vérification de la porte de la version refusent une aide qui dit une autre version, un guide que le README ne liste pas et un README du paquet avec un vieux titre, et le guide de contribution demande à chaque version de relire toute l'aide.

### Corrigé

- Les images de l'onglet Graphiques s'ajustent de nouveau : l'anneau du résultat des dernières 24 h était coupé par sa boîte et sa légende sortait du dessin, les barres des durées étaient un peu plus hautes que leur cadre et la dernière heure de la frise dépassait à droite. Les lignes de l'onglet ne rétrécissent plus en dessous de ce dont une image a besoin (l'onglet défile à la place), la légende de l'anneau est mesurée d'après ses mots et passe sous l'anneau quand elle ne tient pas à côté, et les marges contiennent la moitié de la dernière étiquette. Une nouvelle vérification ouvre l'onglet dans les huit langues, large et étroit, clair et sombre, et mesure chaque image.

## [1.8.4]

### Ajouté

- « En cours » se trie de sept façons et la liste de l'onglet Alertes de neuf, avec des boutons pour déplier ou replier tous les dépôts ; le choix est mémorisé pour chaque utilisateur.

- Les ports du moniteur complet et du moniteur lite sont des réglages du fichier de configuration et du menu Réglages (les valeurs par défaut ne changent pas).

- Le premier administrateur d'un conteneur : le message du service donne la commande exacte, et le guide, le fichier d'exemple et le test du conteneur l'expliquent.

### Corrigé

- Une requête du mode équipe avec plusieurs comptes est attribuée à un seul compte ; l'annulation de la migration des dossiers fonctionne même après une interruption ; la sauvegarde ne contient pas de sessions ; un lien symbolique n'est pas déplacé ; le proxy de Compose ne bloque plus tout le monde à cause des essais d'une seule personne.

## [1.8.3]

### Ajouté

- Notifications pour chaque utilisateur (ntfy, Teams, e-mail, résumés) avec un panneau dans la page ; un job ignoré est montré à part d'un échec ; la page dans toutes les tailles et un moniteur pour plusieurs écrans.

- Un livre des échecs et une bibliothèque de leçons, deux skills pour les IA et un paquet pour l'auditeur.

- Lire moins de quota (webhook d'abord, sources gratuites, API de recherche) et des rapports facultatifs, tout désactivé.

## [1.8.2]

### Ajouté

- Image Docker officielle, Compose et systemd pour faire tourner le moniteur comme un service, un contrôle de santé approfondi, et un accès révoqué par GitHub rend aveugle seulement son compte.

- Dossier du produit rangé : configuration, données, journaux et fichiers pour les IA dans leurs dossiers, avec un déplacement automatique et réversible, et une carte pour les IA (`ai/INDEX.json`).

- Durcissement : le mode réseau ne démarre pas sans premier administrateur, chaque compte a son propre flux pour les IA, les fichiers partagés changent pas à pas, et le quota de GitHub est réparti par type de lecture.

## [1.8.1]

### Corrigé

- Le cadre « chargement des dépôts » restait sur la page après la lecture du dernier dépôt : l’image terminée arrive désormais sur la page dès la fin de la lecture, sans attendre l’entretien qui suit (le résumé pour les outils d’IA, le centre d’alertes), et une longue liste de panneaux du Sentinel ne peut plus faire boucler ce résumé sans fin (cette boucle maintenait la dernière image partielle, 131 / 131, à l’écran).

- Recharger la page (F5) ne prend plus des minutes pour obtenir les données : la boucle sans fin du résumé consommait tout le processeur du moniteur et la page abandonnait avec une interruption ; de plus, la réponse du point d’accès aux données était écrite dans la connexion alors que le verrou global était tenu, si bien qu’une connexion bloquée (un onglet fermé) gelait toutes les autres pages et le cycle d’actualisation. Le verrou n’est plus tenu que le temps de prendre l’image. Un test de navigateur vérifie que le cadre s’affiche pendant le chargement et disparaît avec le dernier dépôt, et des tests du serveur vérifient que le résumé se termine, que l’image terminée est publiée avant l’entretien et qu’une connexion bloquée n’empêche pas un rechargement.

## [1.8.0]

### Modifié

- **Nouvelle arborescence, même comportement** : le code est désormais un paquet importable dans `src/github_actions_monitor/` (`app`, `accounts`, `sentinels`, `security`, `data_pipeline`, `integrations`, `cli`, `ui`, `i18n`, `util`) ; la page, les exemples neutres avec `quotas.json` et les huit catalogues de langues sont dans `assets/` (`static`, `examples`, `locales`) ; `make_release.py` est dans `tools/`. Les lanceurs restent dans le dossier du produit et exécutent `python -m github_actions_monitor` (complet) ou `python -m github_actions_monitor.lite` (lite) : même adresse, même port. Les données de la personne qui l'utilise (`actions_monitor.json`, caches, journaux, `accounts/`, catalogues) restent à côté des lanceurs, jamais dans `src/`.

- Les commandes des guides (`python read_report.py`, `python actions_monitor.py --doctor`, `python monitor_cli.py status` ...) continuent de fonctionner : un petit fichier d'entrée du même nom reste dans le dossier du produit, donc les hooks et serveurs MCP déjà enregistrés par chemin fonctionnent aussi. Le zip de la version garde le nom de son dossier et contient maintenant `src/`, `assets/` et `tools/`.

- **La feuille de route dit ce que contient la 1.8.0 et ce qu'apportera chaque version suivante** : ce qui est déjà dans la branche principale, ce qui est terminé et attend la fusion, ce qui reste à finir, et le plan de la 1.8.2 à la 2.0.0 dans l'ordre où il sera réalisé, dans les huit langues.

### Ajouté

- `tools/migrate_layout.py` pour un dossier qui était une installation plate : simulation par défaut ; `--apply` copie votre configuration vers `layout_backup_<horodatage>/config/` et DÉPLACE (jamais supprimer ni écraser) les anciens modules, page, exemples et `locales/` vers `layout_backup_<horodatage>/old_code/`. `--doctor` avertit tant que de tels restes existent. `MIGRATING.md` le décrit dans les huit langues.

- **Couche de stockage** (`src/github_actions_monitor/storage/`) : une interface `Storage` (configuration, état des sentinelles, flux d'événements, analyses, petits documents et enregistrements globaux des utilisateurs, de leurs comptes et sessions) qui tient pour tout stockage la règle « une écriture est atomique, un élément abîmé se lit comme vide ». `FileStorage` est le premier et garde la disposition de `accounts/<id>/` exactement comme avant (et l'installation à plat à côté des lanceurs) : les mêmes fichiers avec les mêmes noms, écrits via un fichier temporaire vidé sur le disque puis renommé. `create_storage` est le seul endroit qui choisit le stockage ; l'édition lite reçoit toujours des fichiers.

- Des sauvegardes de stockage que n'importe quel stockage peut restaurer : un `.zip` avec un vidage et un manifeste (comptes, taille, SHA-256) ; la restauration vérifie d'abord la copie et refuse d'écrire sur un stockage qui contient déjà des comptes sauf si on le force.

- **Stockage SQLite** (optionnel, désactivé par défaut) : les mêmes données dans une base, un fichier par compte (`accounts/<id>/storage.sqlite3`), que seul le processus de ce compte écrit. Journal WAL et délai d'attente, chaque écriture est une courte transaction, migrations de schéma versionnées exécutées dans la même transaction que le changement de version (une migration interrompue laisse la base comme elle était ; une base d'une version plus récente est refusée), un index des événements d'un compte par heure, et un processus tué en pleine écriture se rétablit au démarrage suivant. Passent dans la base : le flux d'événements, ce que le flux a annoncé, les analyses, l'état des sentinelles, les mises en sourdine et l'avis de mise à jour ; la configuration reste un fichier JSON, caches et journaux restent des fichiers. L'édition lite n'a pas cette option.

- Une base partagée pour toute l'installation (plusieurs comptes et processus dans un fichier) est prête et testée : WAL, délai d'attente, deux processus qui font leur cycle en même temps et une page qui répond en HTTP sans attendre celui qui écrit.

- `tools/migrate_storage.py` déplace l'état entre fichiers et SQLite dans les deux sens : simulation par défaut ; `--apply` copie chaque compte en une étape puis compare chaque élément et chaque événement ; vos fichiers ne sont jamais modifiés ni supprimés ; une exécution interrompue laisse chaque compte entier ou tel qu'il était et la même commande reprend. `tools/backup_storage.py` fait, vérifie et restaure les sauvegardes de l'un ou l'autre.

- **Conservation et rotation** (complète) : `retention.events_days` (90) et `retention.analytics_days` (180) fixent la durée de conservation des événements et des jours d'historique d'analyses ; `retention.mode` vaut `archive` (défaut ; les anciens événements sont d'abord écrits dans un `.gz` de `events/archive/` du compte, puis retirés du flux) ou `delete` ; `retention.enabled` est l'interrupteur et `retention.interval_hours` (24) dit la fréquence d'un court passage à la fin d'une actualisation. Chaque passage laisse une ligne d'audit (quand, événements supprimés et conservés, fichier d'archive, jours d'analyses, erreur). La purge ne touche jamais la configuration, l'état des sentinelles, les mises en sourdine ni un événement sans heure. `retention.events_max_kb` (512, comme avant) est le plafond de taille du fichier du flux. Les réglages sont dans l'onglet Dossiers et fichiers ; l'édition lite ne les a pas.

- `--doctor` a deux nouvelles vérifications : le stockage (la base SQLite existe, passe son contrôle d'intégrité et a un schéma que cette version comprend ; lecture seule) et la conservation (la taille des événements de chaque compte face à `retention.warn_events_mb` et un avertissement pour un moniteur qui tourne comme service sans bloc de conservation).

- **Mode équipe : utilisateurs, rôles et sessions** (`src/github_actions_monitor/security/auth.py`, `auth_http.py`, `auth_cli.py` ; désactivé par défaut avec `auth.enabled`, une personne seule ne remarque donc rien) : dès que le premier administrateur existe (créé sur `/login` ou à la console, uniquement depuis l'ordinateur qui exécute le moniteur et une seule fois), chaque requête exige une session. Rôles `viewer` (lit), `maintainer` (coupe, acquitte et change aussi le mode de travail) et `admin` (aussi réglages, utilisateurs et tout ce qui peut atteindre GitHub) ; une route que personne n'a listée est fermée à tous sauf à un admin. Chaque utilisateur a les comptes qu'il peut voir : un autre compte demandé avec `?account=`, `X-Account-Id` ou un export répond 403. Les mots de passe sont conservés sous forme de hachage scrypt salé ; la session est un cookie HttpOnly, SameSite=Strict (Secure en HTTPS) avec un jeton CSRF sur chaque POST, ou un jeton Bearer pour scripts et applications (`auth.allow_bearer`) ; un utilisateur est bloqué après `auth.max_failed_logins` mots de passe erronés, chaque adresse est limitée, un nouveau mot de passe, rôle ou état termine les sessions de l'utilisateur et il reste toujours un administrateur actif. Les points d'accès `/api/auth/login`, `/api/auth/users` et `/api/auth/audit` répondent les erreurs sous la forme `{"error", "code"}` ; `auth_audit.jsonl` enregistre connexions, blocages, requêtes refusées et changements d'utilisateurs sans aucun secret. L'édition lite n'a jamais de connexion, le jeton à usage unique de la page s'applique toujours, et `python -m github_actions_monitor.security.auth_cli` récupère un mot de passe d'administrateur perdu. Sept réglages (`auth.*`) avec leur aide dans les huit langues et une section de `docs/ADVANCED.md` dans les huit langues ; `tests/test_auth.py` couvre les règles, les rôles de chaque type de route, la portée entre comptes, le cookie, le CSRF, le Bearer, les blocages et le journal sur le vrai serveur.

- Le superviseur de comptes filtre par utilisateur : `GET /api/accounts`, `/api/accounts/<id>/status`, la page d'un compte et toute requête avec `?account=` ou `X-Account-Id` ne montrent et n'atteignent que les comptes attribués à l'utilisateur (un admin les voit tous), et le moniteur d'un compte sait qui agit. Une mise en sourdine de l'onglet Alertes conserve désormais qui l'a faite : `muted_by` dans `GET /api/alerts` et dans l'historique des sourdines.

- **La page du mode équipe montre qui est connecté** : une boîte dans l'en-tête avec le nom et le rôle (un texte, pas seulement une couleur) qui ouvre un menu pour changer le mot de passe, voir et gérer les utilisateurs et le journal (administrateurs seulement) et se déconnecter ; la première fois, avec le mode activé et sans utilisateur, elle renvoie à `/login`. Chaque modification envoyée par la page porte le jeton CSRF, une session terminée mène à `/login` et un jeton erroné est renouvelé et essayé une fois. En mode individuel et dans l'édition lite, la page ne dessine ni ne demande rien de nouveau ; `tests/test_auth_page.py` exécute l'enveloppe de `fetch` dans Node contre un faux réseau.

### Sécurité

- **Le verrouillage des mauvais jetons freine de nouveau (mode réseau)** : une adresse qui n'est pas cet ordinateur et qui est verrouillée est refusée AVANT que son jeton soit jugé, quelle que soit la façon de le présenter (en-tête, cookie, `?access=` et `POST /api/access`) ; jusqu'ici une adresse verrouillée pouvait continuer à deviner et le bon jeton entrait quand même. La personne devant cet ordinateur n'est jamais verrouillée hors de son propre moniteur.

- **Un reverse proxy déclaré fait que la boucle locale ne veut plus dire « cet ordinateur »** (`listen.proxy_public_host`, `listen.secure_cookie` ou `listen.trusted_proxy`) : un proxy qui oublie ses en-têtes de transfert ne peut plus transformer n'importe quel client d'internet en propriétaire. La personne devant l'ordinateur du moniteur utilise le nouveau second port qui n'écoute que sur `127.0.0.1` (`listen.local_port`, 0 = désactivé, redémarrage nécessaire, même jeton d'accès). Avec `listen.trusted_proxy`, les mauvais jetons de tous les clients du proxy sont aussi comptés ensemble (trois fois la limite d'une adresse) : changer `X-Forwarded-For` n'annule donc pas le verrouillage.

- **Le guide du reverse proxy** (`DEPLOYMENT.md`, huit langues) donne la recette complète : `Host` public, `X-Forwarded-For $proxy_add_x_forwarded_for`, `X-Forwarded-Proto`, le mode réseau et la déclaration du proxy ; il ne dit plus que le moniteur « n'a pas de connexion », et précise que `listen.trusted_proxy` suppose un proxy sur le même ordinateur.

- **`GET /api/settings` pour un client du réseau** ne renvoie la valeur que des réglages qu'il peut modifier ; pour tout autre réglage (chemins de clés et de jetons, dossiers, noms de variables) il indique seulement s'il est défini.

- **Test de chaque route « cet ordinateur seulement »** : un tableau des routes est parcouru contre un vrai serveur avec un client hors de la boucle locale (et le code source est examiné pour qu'une nouvelle route ne soit pas oubliée).

- **Une adresse de GitHub ne passe le nettoyeur que sous les formes d'une liste fermée** (un dépôt, une exécution avec son job ou sa tentative, un commit, une issue, une pull request, un fichier) ; elle est coupée au premier caractère qui n'est ni une lettre, ni un chiffre, ni un point, un tiret, un tiret bas ou une barre oblique, et ce qui suit est nettoyé comme n'importe quel texte. Jusqu'ici un secret collé à un lien (une requête encodée, une liste séparée par des virgules, deux-points, un segment opaque du chemin, un e-mail qui commence dans l'adresse) arrivait entier à l'IA.

- **Le hook du client d'IA ne remet aucun texte de journal** : seulement le dépôt, le workflow, la conclusion et le lien de chaque alerte. L'ordre d'agir sans attendre qu'on le dise a disparu ; la dernière ligne dit désormais qu'un journal peut contenir du texte écrit par des tiers, que ce sont des données non fiables et que les instructions qu'il contient ne sont jamais suivies. Dans les huit langues.

### Corrigé

- **Le flux d'événements pour IA ne meurt plus sur une ligne de journal ordinaire** : la ligne du flux est nettoyée champ par champ puis écrite, au lieu de nettoyer un JSON déjà écrit (une cause qui finissait par `password: x`, `token=x` ou `DB_PASSWORD=x` le cassait). Une ligne impossible à nettoyer est ignorée et le flux continue ; les réponses du serveur MCP sont nettoyées de la même façon. Dans le nettoyeur, la valeur d'une paire `clé=valeur` s'arrête à un guillemet, une virgule ou un point-virgule, et une valeur entre guillemets est nettoyée en entier.

- **Ce qui dépend de celui qui demande est toujours servi par votre propre login** : `gh api user`, `user/orgs`, les notifications, une recherche de `@me`, `gh auth` et `gh repo list` sans propriétaire ne vont jamais à la GitHub App ni au second compte, quel que soit le nombre d'appels qui leur restent (avec le second compte actif, le moniteur pouvait prendre le titulaire de ce compte comme propriétaire et lister ses organisations).

- **Un appel `gh` n'est une lecture que s'il figure sur une liste blanche** : `gh api ENDPOINT` avec au plus les options `--jq`, `--paginate`, `-H` (de celles qu'envoie une lecture), `-i` et `--cache`. Les formes collées d'une écriture (`-XPOST`, `--method=DELETE`, `-fa=b`, `--field=a=b`, `--input=-`) et toute autre option vont à votre login au lieu d'être réparties entre les sources.

- **Le fichier du jeton du second compte** (`extra_reader.file`) doit se trouver dans le dossier des comptes du moniteur (`accounts/`, ou `MONITOR_ACCOUNTS_DIR`) et s'ouvre sans suivre de lien et seulement s'il s'agit d'un petit fichier ordinaire ; hors de ce dossier le réglage est vide. Le nouvel interrupteur `extra_reader.any_folder` (désactivé par défaut, local seulement) lève la règle du dossier pour un fichier qui doit rester ailleurs.

- **Un panneau central daté du futur n'est plus cru** : son âge était ramené à zéro et il comptait comme frais pour toujours ; il est maintenant en retard, le résumé dit que la date n'est pas fiable et une horloge en avance de cinq minutes au plus est tolérée.

- **Le test des ports des comptes n'échoue plus quand plusieurs suites tournent en même temps** : le superviseur peut recevoir le point de départ de la recherche de ports libres (la valeur par défaut reste 18800) et les tests demandent au système une plage inutilisée au lieu d'une plage fixe.

- **Une page cassée met la CI au rouge** : un nouveau job (`page`, sans `continue-on-error`) ouvre la page du moniteur de démonstration dans un vrai navigateur (`tools/check_page.py`), parcourt chaque onglet et chaque sous-onglet des Réglages, exige un minimum de champs dans chacun et échoue à la moindre erreur de la page, promesse non gérée ou console.error. Une page cassée exprès (une seconde définition, une affectation au nom d'une fonction, un appel à une fonction qui n'existe pas) doit le faire échouer. Le test qui cherche les fonctions définies deux fois voit désormais aussi une déclaration indentée, une déclaration avec `async` et une affectation au nom d'une fonction.

## [1.7.9]

### Corrigé

- Les liens des runs reçus par les outils d'IA (flux, résumé, état, hook) étaient coupés en « https://github.[blob] » : le rédacteur prenait l'adresse pour une chaîne opaque. Les adresses https complètes de github.com passent désormais intactes ; jetons, clés, e-mails, IP et chemins personnels restent nettoyés, y compris dans un lien.

## [1.7.8]

### Ajouté

- **`listen.trusted_proxy`** (désactivé par défaut, local uniquement, dans les huit langues) : derrière un proxy inverse à vous sur le même ordinateur, un échec est compté sur la dernière adresse de `X-Forwarded-For` et non sur le proxy, pour que les jetons erronés d'une personne ne bloquent pas tout le monde. Cela ne change que ce comptage : une requête qui passe par un proxy n'est toujours jamais traitée comme cet ordinateur.

### Corrigé

- La page Réglages affichait « Le moniteur local ne répond pas » et aucun onglet : la boîte de l'onglet Quota portait le même nom qu'une fonction plus ancienne de l'onglet Base et celle-ci la remplaçait. La boîte du Quota est renommée, et un test échoue désormais si une fonction de la page est définie deux fois.

## [1.7.7]

### Ajouté

- **Une vérification qu'aucun texte ne sort de sa case** (`tools/check_overflow.py` et un test qui s'ignore proprement sans navigateur) : la page est ouverte dans un navigateur sans fenêtre dans les huit langues, large et étroite, parcourt chaque onglet et chaque fenêtre, et échoue si un texte est plus large qu'une case avec bordure ou fond ou sort de la fenêtre.
- **`display.blink_red_tiles`** (activé par défaut, dans l'onglet Réglages, dans les huit langues) : les tuiles du haut et les éléments de la barre du bas qui passent au rouge clignotent doucement jusqu'à la résolution de la cause ; avec le mouvement réduit du système, elles affichent à la place un bord rouge fixe et plus épais.
- **Une vérification du doctor pour le fuseau horaire** : un fuseau que ni le système ni la table interne ne connaissent est signalé, et les heures sont alors affichées en UTC (elles retombaient auparavant sur le fuseau de l'ordinateur sans le dire).
- **L'onglet Historique indique « n sur N »** quand la liste est plus courte que ce que l'en-tête a compté (le moniteur garde les 600 exécutions les plus récentes ; les données portent `runs_total`).
- **Les panneaux de l'onglet Sentinelle comme données** : `GET /api/sentinel/panels` (lecture seule), l'outil MCP `sentinel_panels` et une section « Sentinel panels » du résumé donnent, pour A1..A13 et le second sentinelle, le niveau, une ligne et les lignes sur lesquelles agir avec dépôt et lien ; les lignes d'un panneau à « agir » ou « surveiller » deviennent aussi des alertes du flux (classes `real` et `watch`), si bien que le flux en direct, le hook, `alerts_open` et le compteur d'alertes réelles les incluent.
- **Un « bing bing » quand quelque chose de nouveau échoue** (les réglages `sound`, dans les huit langues) : la page joue deux courts signaux (Web Audio) uniquement pour un NOUVEAU rouge ou une connexion perdue, jamais lors d'un rafraîchissement ni pour ce qui existait déjà, avec une pause minimale, un volume et une pastille « Son » dans la barre du bas qui débloque l'audio du navigateur, le coupe et est mémorisée ; un bouton « Tester le son » dans Ce navigateur ; et `sound.server_beep` (désactivé par défaut, local uniquement) pour quand la page est fermée (bip Windows, `afplay` de macOS, `canberra-gtk-play` sous Linux ou la cloche du terminal, sans shell et sans réseau).
- **Tout ce que dit le moniteur, en signaux pour un outil d'IA** : un inventaire unique (`signals.py`) avec niveau (agir / surveiller / info), résumé et lignes avec dépôt, lien, ancienneté et prochaine étape pour l'onglet Maintenant et ses tuiles, les alertes, les dépôts, les panneaux du sentinelle A1..A13 et le second sentinelle, le quota, la connexion et la santé du moniteur ; `GET /api/ai/state` (versionné, lecture seule), un résumé avec « Quoi faire maintenant », « En attente » et « Santé du moniteur » et le compteur de signaux sur lesquels agir, et les outils MCP `monitor_state`, `signals`, `diagnose` et `act`. Un test parcourt la page et échoue pour une tuile ou un onglet qui n'est ni dans l'inventaire ni marqué décoratif.
- **La connexion avec un outil d'IA est la même dans l'édition lite et dans la complète** : mêmes canaux (résumé, flux, `/api/ai/state`, flux en direct, outils MCP, `ai-hook`), même code et mêmes réglages dans les deux ; l'état dit `edition` et liste les panneaux qui n'existent pas en lite, pour qu'un panneau absent ne soit pas pris pour des données manquantes.
- **Un mode économe (économie extrême du quota)** : à côté de Normal, Rapide et Turbo, `low` ne lit que les dépôts chauds toutes les 4 minutes et le reste toutes les 30, avec des listes d'exécutions courtes, et indique dans la barre et dans le résumé que ses chiffres peuvent être anciens et de combien ; `modes.auto_low` (activé par défaut) s'enclenche tout seul sous 1000 appels restants et revient au-dessus de 2500 ou au renouvellement du quota (deux nombres différents, sans oscillation) ; les valeurs sont dans `modes.low` du fichier.
- **Le panneau central comme base qui ne dépense pas de quota** (`central.source` : désactivé par défaut, `git` ou `http` ; `central.max_age_minutes`, dans les huit langues) : le moniteur lit `data/sentinel.json` du dépôt de profil (rafraîchi toutes les demi-heures par un workflow avec son propre jeton) avec un simple git fetch ou le fichier brut, affiche « source : panneau central, il y a N min » dans l'état et le résumé, ignore un fichier en retard (plus de deux heures) et le dit, et en mode économe n'interroge l'API en direct que pour les dépôts que le panneau dit rouges, ceux avec une exécution en cours et ce que le panneau ne contient pas.
- **Une GitHub App facultative pour les lectures** (`github_app.enabled`, désactivé par défaut, avec `app_id`, `key_path` et un `installation_id` facultatif, dans les huit langues) : les lectures du moniteur utilisent le jeton d'installation d'une App, dont le quota est séparé de celui de l'utilisateur et plus grand quand elle couvre plus de dépôts ; le JWT (dix minutes au plus) est signé par `openssl` à partir du chemin de la clé, que le moniteur ne lit, ne copie, n'imprime ni ne journalise jamais ; le jeton dure une heure, reste en mémoire et est renouvelé cinq minutes avant ; les écritures et actions gardent le jeton de l'utilisateur ; si l'App échoue ou n'a pas une permission, la lecture est refaite avec le jeton de l'utilisateur ; `GET /api/github-app/status` (cet ordinateur seulement) montre le nom, l'installation, les permissions accordées et le quota de l'App, jamais la clé ni le jeton ; les données portent le quota de l'utilisateur à côté de celui de l'App, et le doctor vérifie openssl, le fichier de clé et ses droits.
- **Deux nouveaux guides, dans les huit langues** : `docs/AI_CONNECTION.md` (connecter un outil d'IA : ce qu'il voit, les cinq canaux, pas à pas, sécurité, dépannage, ce que montre chaque édition) et `docs/QUOTA.md` (« Plus de quota, moins de dépense » : comment fonctionne le quota, tous les moyens d'économie du moniteur, une GitHub App pas à pas, partager le quota entre outils, ce qu'il ne faut pas faire) ; les deux sont liés depuis le README et l'index d'aide, et un test vérifie que chaque réglage cité existe.
- **L'aide est vérifiée à chaque changement** : un réglage sans son libellé et son aide dans les huit langues, un onglet sans sujet d'aide ou une ligne du journal des modifications qui nomme un réglage ou un point d'accès absent de l'aide et des guides font maintenant échouer les tests ; une liste de contrôle de l'aide figure dans CONTRIBUTING et dans le modèle de pull request.
- **Un onglet Quota dans les Réglages** (dans les huit langues, aussi dans l'édition lite) : les modes et les valeurs du mode économe (`modes.*`), l'économie (`network.etag`, un alias qui fonctionne avec `cache.etag.enabled`), le panneau central, la GitHub App et un second compte pour les lectures au même endroit, avec des boutons qui montrent le quota de chaque source et son heure de renouvellement, testent l'App et le second compte, listent les permissions qui manquent à l'App et appliquent les valeurs recommandées ou celles par défaut.
- **Un second compte en lecture seule pour les lectures** (`extra_reader.enabled`, `extra_reader.file`) : le réglage ne contient que le CHEMIN d'un fichier avec un jeton à granularité fine, que le moniteur lit au moment de l'utiliser, garde en mémoire et ne stocke, imprime ni journalise jamais ; les lectures sont réparties entre votre connexion, l'App et le second compte selon les appels restants de chacun, une source refusée est laissée de côté cinq minutes et la lecture est refaite avec la suivante, et les écritures et actions ne l'utilisent jamais.
- **Comptabilité des lectures** : l'état, le résumé et les données disent combien d'appels conditionnels ont été faits et combien ont répondu 304 (sans dépenser de quota) et le quota de chaque source.
- **Qui dépense le quota** : le moniteur compare, dans chaque fenêtre horaire, ce que tout le compte a dépensé avec ses propres appels et dit dans l'onglet Quota, l'état et le résumé combien dépensent les autres outils, avec un avertissement quand ils en dépensent l'essentiel (GitHub ne dit pas lequel).
- **Le flux en direct porte aussi les autres signaux** : le quota épuisé, la connexion qui tombe, les données qui vieillissent, un panneau central en retard et les avertissements de santé deviennent des événements du flux (et du hook) quand ils apparaissent, changent ou se résolvent, pas seulement les workflows rouges et les panneaux de l'onglet Sentinelle.
- **L'envoi par lots garde la tentative de l'exécution trouvée** (`run_attempt` dans l'enregistrement du lot, depuis le champ `attempt` de `gh run list` ; vide si `gh` ne le donne pas), et les guides de la connexion à un outil d'IA et du quota décrivent le second compte en lecture seule.

### Modifié

- **La barre du bas est redessinée** : chaque élément est une pastille avec sa bordure, la connexion et le quota prennent la couleur de leur état, l'horloge est un cadre avec de grands chiffres gras tabulaires, la date au-dessus et le fuseau en petits caractères, et la barre garde son ordre dans les fenêtres étroites.
- **Chaque case laisse son texte se couper au lieu de déborder** (tuiles, pastilles, badges, cellules, titres, boutons des fenêtres) : l'heure de la dernière lecture porte son fuseau à part en petits caractères, les lignes d'alertes passent sur deux colonnes dans les fenêtres étroites et les grilles de tuiles peuvent rétrécir sous leur contenu.
- **Les tuiles d'une ligne ont la même hauteur**, quoi que demande leur petit texte.

### Corrigé

- **Un seul chiffre pour les échecs ouverts** : la tuile « rouges sur main », la liste des alertes, la barre du bas et le résumé comptent la même chose, un workflow dont la dernière exécution sur la branche par défaut a échoué (un échec sur une branche de travail n'apparaît plus comme alerte ouverte), et la barre ne dit jamais « aucun avis » tant que des alertes sont ouvertes.
- **Le démarrage du moniteur nomme la version une seule fois** : la ligne « GitHub Actions v... » qui répétait l'en-tête disparaît ; l'auteur et la licence restent sur une ligne.
- **Fichiers d'état endommagés** (état de collaboration, cache et historique du sentinelle de mauvaise forme) : ils sont ignorés entrée par entrée au lieu d'atteindre le code qui les lit.
- **Un quota GitHub épuisé est UN avis, pas une erreur par dépôt** : les lectures des dépôts s'arrêtent jusqu'au renouvellement (et reprennent seules), la liste des alertes dit « Quota de GitHub épuisé jusqu'à HH:MM ... (N dépôts non rafraîchis) », la barre du bas aussi, rien ne passe au rouge et rien n'arrive au flux, au son ni au résumé comme un échec ; les textes d'erreur de `gh` sont coupés à une ligne (sans paragraphe juridique ni identifiant de requête) et beaucoup de dépôts avec le même type d'erreur sont groupés sur une ligne.
- **À propos (et toute page) n'attend plus le réseau** : la vérification d'une nouvelle version du moniteur était lue dans la requête de /api/about quand sa réponse avait plus d'un jour, si bien qu'un `gh` sans connexion ou un réseau lent faisait durer la fenêtre À propos de 10 à 25 secondes ; la réponse du cache est maintenant renvoyée aussitôt et la lecture est faite par un fil en arrière-plan, un seul à la fois.

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

