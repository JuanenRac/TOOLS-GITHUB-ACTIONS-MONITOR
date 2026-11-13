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
- **Ouvrir la session par POST.** Au lieu de l'adresse avec `?access=` vous pouvez envoyer `POST /api/access` avec le JSON `{"token": "..."}` : le jeton reste hors de la barre d'adresse, de l'historique et des journaux, et le cookie revient dans la réponse. L'adresse avec `?access=` est obsolète : elle fonctionne encore par défaut (rien de ce qui est déjà en place ne casse) et seulement sur un `GET`, mais le jeton reste dans l'historique, les journaux et le `Referer`, et le moniteur répond avec un en-tête `Deprecation`. Désactivez `listen.query_access` pour la refuser et n'ouvrir la session que par `POST /api/access` ou l'en-tête `X-Monitor-Access`. Une barre rouge en haut des Réglages avertit quand `listen.host` vaut `0.0.0.0`. Tout réglage que le schéma marque comme sûr (pas seulement `listen.*`, `github_token.*`, `act.*` et `github_actions.*` : aussi le webhook, les actions de l'IA, les notifications, OpenTelemetry, le miroir, les runners et les sorties) ne se change que depuis l'ordinateur lui-même.
- **Premiers pas pour écouter sur le réseau.** Désactive d'abord `listen.query_access` (le jeton ne voyage alors jamais dans une adresse, un historique ou un journal ; ouvre la session avec `POST /api/access` ou l'en-tête) et place devant HTTPS (un certificat dans `listen.tls_cert_file` ou un proxy HTTPS) ou un VPN. La console le rappelle au démarrage du mode réseau tant que l'ancienne adresse est acceptée.

## Mode équipe : utilisateurs et rôles

Désactivé par défaut : une personne utilise le moniteur sans connexion. Avec `auth.enabled` activé (sans redémarrage), rien ne change tant que le premier administrateur n'existe pas. L'édition lite n'a jamais de connexion.

- **Premier administrateur.** Ouvrez `/login` sur l'ordinateur qui exécute le moniteur et créez-le (uniquement depuis cet ordinateur et une seule fois ; une requête qui arrive par un proxy est refusée). Ou à la console : `python -m github_actions_monitor.security.auth_cli create-admin NOM --password-env VAR` (le mot de passe ne figure jamais dans la ligne de commande). Ensuite la page demande une connexion ; `reset-password` et `revoke` du même outil récupèrent un mot de passe d'administrateur perdu.
- **Rôles.** `viewer` lit (tout GET) ; `maintainer` coupe et acquitte aussi les alertes et change le mode de travail ; `admin` modifie aussi les réglages, les utilisateurs et tout ce qui peut atteindre GitHub ou l'extérieur. Une route non listée est fermée à tous sauf à un admin. Chaque utilisateur a aussi la liste des comptes qu'il peut voir (les admins voient tout) : un autre compte demandé avec `?account=` ou `X-Account-Id` répond 403 `account_scope`, dans l'API et dans les exports.
- **Sessions.** Le navigateur reçoit le cookie `monitor_session` (HttpOnly, SameSite=Strict, Secure en HTTPS) et un jeton CSRF (`X-CSRF-Token`, renvoyé par la connexion et par `/api/auth/me`) que chaque POST doit envoyer. Un script ou une application utilise `POST /api/auth/login` avec `{"client": "api"}` et envoie le jeton reçu en `Authorization: Bearer msn_...` (`auth.allow_bearer` le désactive). Le jeton à usage unique de la page (`session_guard`) reste exigé en plus de la session.
- **Mots de passe.** Conservés uniquement sous forme de hachage scrypt salé, avec `auth.min_length` caractères au minimum. Après `auth.max_failed_logins` mots de passe erronés, l'utilisateur est bloqué `auth.lockout_minutes`, et chaque adresse a sa propre limite de requêtes. Un nouveau mot de passe, rôle ou état termine les sessions de cet utilisateur ; il reste toujours au moins un administrateur actif.
- **Points d'accès.** `/api/auth/login`, `logout`, `me`, `bootstrap`, `password` ; pour les admins `/api/auth/users` (avec `/update`, `/delete`, `/revoke`) et `/api/auth/audit`. Les erreurs sont du JSON avec un code stable : `{"error": "...", "code": "..."}`.
- **Journal.** `auth_audit.jsonl` (fichier privé ; une copie plus ancienne est conservée) enregistre les connexions, les blocages, les requêtes refusées et les changements d'utilisateurs ; jamais un mot de passe, un hachage ou un jeton. `auth.audit` le désactive.
- **Plusieurs comptes.** Avec les comptes de `ACCOUNTS.md`, `GET /api/accounts` ne liste, et `/api/accounts/<id>/status` ainsi que toute requête avec `?account=` ou `X-Account-Id` n'atteignent, que les comptes attribués à l'utilisateur (un admin les voit tous). Le moniteur d'un compte sait qui agit : une mise en sourdine de l'onglet Alertes enregistre donc qui l'a faite (`muted_by` dans `GET /api/alerts` et l'historique des sourdines).
- **Risque.** En HTTP non chiffré sur un réseau, le cookie et les mots de passe circulent en clair : utilisez HTTPS ou un VPN, comme pour le mode réseau.

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

`listen.trusted_proxy` (désactivé par défaut) : seulement si un proxy inverse À VOUS sur le même ordinateur est la seule entrée. Les échecs sont alors comptés sur la dernière adresse de `X-Forwarded-For` (celle qu'ajoute votre proxy) et non sur le proxy ; une requête qui passe par un proxy n'est toujours jamais traitée comme cet ordinateur. Si quelqu'un d'autre peut joindre directement le moniteur, laissez-le désactivé.

## La boucle de rafraîchissement : battement et chien de garde

`/api/data` renvoie aussi `loop` : la phase du cycle de rafraîchissement (`collect`, `maintain`, `publish`, `log`, `extras`, `idle`), depuis combien de temps le cycle tourne, le dernier bon cycle, la dernière erreur et la phase où elle s'est produite, les relances et tout problème d'écriture du journal ou du résumé pour l'IA. La barre du bas de la page l'affiche en rouge quand un cycle dure beaucoup trop et en avertissement quand un fichier ne peut pas être écrit. Un chien de garde relance dans un nouveau thread le cycle qui dépasse `watchdog_minutes` (10 par défaut, 0 le désactive), après avoir écrit dans `actions_monitor_log.txt` la trace de tous les threads.
