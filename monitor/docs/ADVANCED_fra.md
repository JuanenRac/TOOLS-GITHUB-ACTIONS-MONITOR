<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Fonctions avancées (toutes désactivées par défaut)

Tout ce qui figure sur cette page est **désactivé tant que vous ne l'activez pas** dans *Réglages > Avancé* (ou dans `actions_monitor.json`), et les clés qui décident qui peut atteindre le moniteur ou ce qu'il peut faire sur GitHub sont marquées comme options de sécurité. N'activez que ce dont vous avez besoin.

## Écouter sur le réseau

Par défaut la page ne répond que sur `127.0.0.1`. Avec `listen.network` activé (redémarrage nécessaire) elle écoute aussi sur `listen.host` : une adresse privée de cet ordinateur, ou `0.0.0.0` pour toutes les interfaces. Une adresse publique est refusée.

- **Chaque requête exige le jeton d'accès** (cookie, en-tête `X-Monitor-Access` ou `Authorization: Bearer`). Le jeton est la valeur de la variable d'environnement nommée dans `listen.token_env` (16 caractères ou plus) ; sans elle, un jeton aléatoire est créé à chaque démarrage et montré une fois dans la console. Ouvrez une fois l'adresse qui y est affichée : elle pose le cookie et passe à l'adresse propre.
- Le jeton à usage unique de la page est imposé, la page affiche une barre rouge sur chaque onglet tant que le mode est actif, et les clés de `listen.*`, `github_token.*`, `act.*` et `github_actions.*` ne peuvent être modifiées que depuis l'ordinateur lui-même.
- `listen.allowed_hosts` liste les noms avec lesquels la page peut s'ouvrir (protection contre le DNS rebinding).
- **Risques.** Le trafic est en HTTP clair : quiconque peut lire votre réseau peut lire le jeton et les données. Utilisez-le seulement sur un réseau de confiance, ou placez devant un reverse proxy en HTTPS (voir `DEPLOYMENT.md`). Ne l'exposez jamais à Internet. L'édition lite n'écoute jamais au-delà de cet ordinateur.
- **HTTPS.** Avec votre propre certificat et clé (`listen.tls_cert_file`, `listen.tls_key_file`) le moniteur sert lui-même le HTTPS ; derrière un proxy qui le fait pour vous, activez `listen.secure_cookie`. Dans les deux cas le navigateur envoie `Origin: https://hôte:port` à chaque modification, et la garde accepte exactement le schéma de la session (l'autre schéma, un autre hôte, un autre port ou une origine mal formée sont refusés). L'adresse utilisée par le navigateur doit porter le port du moniteur, sauf derrière un proxy HTTPS sur le port 443 par défaut qui transmet `Host` et `Origin` sans port : indiquez son nom public dans `listen.proxy_public_host` (un nom d'hôte seulement, vide par défaut). Il ne compte qu'en HTTPS, seul ce nom est accepté sans port, et il ne se change que depuis le même ordinateur.
- **Ouvrir la session par POST.** Au lieu de l'adresse avec `?access=` vous pouvez envoyer `POST /api/access` avec le JSON `{"token": "..."}` : le jeton reste hors de la barre d'adresse, de l'historique et des journaux, et le cookie revient dans la réponse. L'adresse avec `?access=` fonctionne toujours. Une barre rouge en haut des Réglages avertit quand `listen.host` vaut `0.0.0.0`. Tout réglage que le schéma marque comme sûr (pas seulement `listen.*`, `github_token.*`, `act.*` et `github_actions.*` : aussi le webhook, les actions de l'IA, les notifications, OpenTelemetry, le miroir, les runners et les sorties) ne se change que depuis l'ordinateur lui-même.

## Un jeton GitHub conservé par le moniteur

Le défaut reste votre propre connexion `gh`. Avec `github_token.enabled` activé vous pouvez coller un jeton dans Réglages > Avancé : il est conservé dans le coffre sécurisé du système (DPAPI Windows, Trousseau macOS, Secret Service Linux) et, seulement s'il manque, dans un fichier en permissions 600 (la page le dit). Il n'est jamais écrit dans `actions_monitor.json`, un journal, le panneau À propos ni le texte pour l'assistance, et n'atteint `gh` que par l'environnement du processus. Le bouton **Supprimer le jeton** l'efface partout.

## Actions sur GitHub

Avec `github_actions.enabled` activé, le moniteur peut relancer une exécution en échec (`rerun_failed`, `rerun_run`, `rerun_job`), annuler une exécution (`cancel`), fermer une issue ou une pull request (`close_issue`, `close_pr`) et en fusionner une (`merge_pr`, avec `github_actions.merge_method`). Seuls les noms de `github_actions.allowed` sont utilisables (par défaut `rerun_failed` et `cancel`). **Chaque action est confirmée séparément** : la page montre exactement ce qui sera envoyé (méthode et point d'accès) et n'envoie rien tant que vous n'avez pas confirmé ce plan avec le jeton à usage unique. Le jeton GitHub doit avoir la permission (`workflow` pour les exécutions, `repo` pour les issues et pull requests ; sinon le refus de GitHub est affiché). Chaque tentative est écrite dans `github_actions_log.jsonl`. L'assistant IA n'a aucun moyen d'en lancer une.

## Exécuter un workflow ici avec act

Avec `act.enabled` activé et des entrées `dépôt:fichier.yml:évènement` dans `act.allowed` (les trois exactes), un bouton exécute `act` sur le clone local après confirmation de la ligne de commande exacte. Aucun vrai secret n'est fourni (fichiers de secrets, variables, environnement et entrées vides, et un environnement minimal sans jeton), la sortie s'affiche au fil de l'eau, une exécution à la fois, avec la limite de durée `act.timeout_seconds`, et vous pouvez l'arrêter.

## Copie locale des artefacts

Avec `mirror.enabled` activé et un `mirror.folder` sur cet ordinateur, les artefacts des exécutions terminées y sont copiés (`mirror.max_per_cycle` par cycle, `mirror.max_mb` pour le dossier, `mirror.keep_days` de conservation), une fois chacun, avec des noms nettoyés dans le dossier.

## Runners auto-hébergés

Avec `runners.enabled` activé, Réglages > Avancé montre chaque runner comme libre, occupé ou hors ligne. Le disque et la charge ne sont montrés que pour les runners listés dans `runners.metrics` ({nom : adresse d'un node exporter sur cet ordinateur ou d'une adresse privée}).

## OpenTelemetry

Avec `otlp.enabled` activé et un `otlp.endpoint` (HTTPS, ou HTTP sur cet ordinateur), les exécutions terminées partent en traces et les chiffres d'en-tête en métriques (OTLP/HTTP en JSON), chaque exécution une fois. Seuls dépôt, workflow, branche, évènement, conclusion et durée sont envoyés.

## Organisations et coûts

- `organizations.discover` liste les organisations du compte dans Réglages > Basique. Pour en surveiller une, lancez un second moniteur avec `github_owner` réglé dessus.
- `finops.jobs_per_cycle` supérieur à 0 lit les étiquettes des jobs d'autant d'exécutions privées terminées par cycle, pour que les minutes utilisent le bon multiplicateur (Linux, Windows, macOS et les gros runners de `quotas.json`) au lieu d'un système supposé. Avec le rapport de facturation activé (`quota.billing_api`) s'affichent aussi les dollars de Codespaces et Packages, le stockage utilisé et le prix des minutes au-delà de celles incluses.

## Vérifier face aux services réels

`python tools/manual_check_live.py` (dans le dépôt) lit les portées de votre jeton, le rapport de facturation, les organisations, les runners et les options de `gh copilot`, et demande à un moniteur en marche d'envoyer un message de test par vos canaux. Il ne demande jamais de secret.

## Notes de sécurité (à lire avant d'activer quoi que ce soit)

- **Mode réseau** : à n'utiliser que sur un réseau de confiance. Le jeton d'accès ne remplace pas le chiffrement ; en HTTP simple, le jeton et les données circulent en clair. Placez un proxy HTTPS devant (et activez `listen.secure_cookie`) ou donnez au moniteur votre propre certificat et sa clé (`listen.tls_cert_file`, `listen.tls_key_file`) : il sert alors lui-même le HTTPS (TLS 1.2 ou plus récent) et refuse de démarrer si les fichiers sont inutilisables. Préférez UNE adresse privée de cet ordinateur à toutes les interfaces. Seules les adresses IPv4 sont acceptées. Après la première visite, la barre d'adresse est débarrassée du jeton et le cookie est HttpOnly, SameSite=Strict (et Secure en HTTPS). Une adresse qui envoie `listen.max_failed_attempts` jetons erronés en une minute est refusée cinq minutes. `/metrics` et `dashboard.json` listent vos dépôts : en mode réseau, ils exigent aussi le jeton.
- **Actions sur GitHub** : **désactivées par défaut, une confirmation par action, liste fermée** (relancer une exécution ou un job, annuler, fermer une issue ou une pull request, fusionner une pull request si vous l'ajoutez). Supprimer des branches ou des dépôts, les secrets et les réglages n'y sont **pas**. L'IA peut proposer une liste plus courte (`rerun_failed`, `rerun_run`, `close_issue`) et ne fusionne jamais.
- **act** : désactivé par défaut, chaque exécution confirmée, liste fermée `dépôt:fichier:événement`, aucun vrai secret. Le clone doit être un vrai dossier dans l'espace de travail : un dossier qui est un lien vers un autre endroit est refusé sauf si `act.allow_symlinks` est activé. La limite de temps et Stop terminent tout l'arbre de processus lancé par l'exécution et suppriment les conteneurs `act-` qu'elle a créés.
- **Votre propre jeton** est gardé dans le magasin du système s'il existe ; le simple fichier (droits 600) est le magasin le plus faible. Il va à `gh` seulement, jamais à `act` ni à vos commandes. `--doctor` montre le magasin, jamais le jeton.
- **Combinaisons à éviter** (`--doctor` les nomme) : mode réseau sur toutes les interfaces ; actions de l'IA qui s'exécutent avec le mode réseau actif ; `act` avec le mode réseau actif ; le jeton dans un simple fichier.
- Le serveur MCP parle uniquement sur l'entrée et la sortie standard ; ne le placez jamais derrière un port réseau.
