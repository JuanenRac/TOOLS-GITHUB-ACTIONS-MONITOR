<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->


[🇺🇸 English](DEPLOYMENT.md) | [🇪🇸 Español](DEPLOYMENT_spa.md) | **🇫🇷 Français** | [🇮🇹 Italiano](DEPLOYMENT_ita.md) | [🇩🇪 Deutsch](DEPLOYMENT_deu.md) | [🇨🇳 简体中文](DEPLOYMENT_zho.md) | [🇯🇵 日本語](DEPLOYMENT_jpn.md) | [🇵🇹 Português](DEPLOYMENT_por.md)

# L'exécuter comme un service

Le moniteur est un programme qui, par défaut, écoute uniquement sur `127.0.0.1` et n'a pas de connexion. Ces notes expliquent comment l'exécuter comme un service : l'image officielle, Docker Compose avec un proxy inverse, une installation classique avec systemd, et ce qui se passe quand GitHub révoque l'accès.

## Où il écoute

Le moniteur écoute de trois façons possibles, et la page, `GET /api/accounts`, `bin/monitor_cli.py status` et `bin/monitor_cli.py accounts` disent laquelle : **cet ordinateur** (uniquement `127.0.0.1` : le défaut, sans connexion), **le réseau** (le mode réseau, `listen.network` : il écoute aussi sur `listen.host` et toute requête porte le jeton d'accès) ou **derrière un proxy** (le mode réseau avec un proxy inverse déclaré devant : `listen.proxy_public_host`, `listen.secure_cookie` ou `listen.trusted_proxy`). L'image et l'unité de service sont faites pour la deuxième et la troisième ; un moniteur lancé à la main reste dans la première.

En mode réseau, le superviseur de plusieurs comptes suit les mêmes règles que le moniteur d'un compte : le jeton d'accès sur chaque requête (cookie, en-tête ou `POST /api/access`), un verrouillage après de mauvais jetons, la vérification de `Host`, un TLS facultatif avec votre certificat, le second port de la personne devant la machine (`listen.local_port`), et les clés qui décident de l'exposition, l'accès à GitHub et les actions sur GitHub uniquement depuis l'ordinateur du moniteur (une requête venue du réseau atteint le compte marquée comme distante).

## Les ports des deux éditions

L'édition complète écoute sur le port 8765 et la lite sur le 8766, sauf si le fichier de configuration en indique un autre : `ports.complete` et `ports.lite` (un entier de 1024 à 65535, redémarrage nécessaire ; ils figurent aussi dans la page Réglages, bloc Ports). Les deux numéros sont lus à un seul endroit, si bien que le démarrage, la vérification « un moniteur tourne déjà sur ce port », `--doctor`, le contrôle de santé (`python -m github_actions_monitor.cli.healthcheck`), la ligne de commande (`--lite` parle au port lite), les vues de terminal et les lanceurs s'accordent. L'ordre est : `--port N` sur la ligne de commande, puis `MONITOR_PORT` (le service et le conteneur le fixent ; édition complète seulement), puis le fichier de l'édition, puis celui de l'autre édition (un menu peut fixer les deux), puis la valeur par défaut. L'édition lite ne prend jamais le port de la complète : si les deux indiquent le même numéro, la lite garde 8766, et la page Réglages refuse d'enregistrer le même numéro pour les deux. Si le port est occupé, le moniteur prend le suivant libre, jusqu'à dix au-dessus.

## Sans navigateur, et le contrôle de santé

`python -m github_actions_monitor.service` est l'entrée d'un service : il prépare les dossiers et le premier compte à partir de l'environnement (voir le tableau ci-dessous) et lance le moniteur sans navigateur. `python bin/actions_monitor.py --no-browser --port 8765` reste valable pour un moniteur que vous gérez vous-même.

`GET /api/health` répond `{"ok": true, "version": ..., "loaded": ..., "offline": ...}` avec l'état du cycle d'actualisation et de l'accès GitHub du compte ; il n'appelle pas GitHub. `GET /api/health?deep=1` est le contrôle approfondi : il répond 503 quand le cycle d'actualisation d'un compte dure plus de `watchdog_minutes` (30 minutes si 0) ou que son fil a disparu ; dans le superviseur de plusieurs comptes aussi quand la boucle de supervision elle-même s'est arrêtée, quand le cycle de N'IMPORTE QUEL compte est bloqué, ou quand aucun compte ne répond une fois le démarrage passé. Un compte dont l'accès GitHub est inutilisable (aveugle) est nommé dans la réponse mais n'est pas une panne : un redémarrage ne répare pas un accès perdu, un nouvel accès si.

`python -m github_actions_monitor.cli.healthcheck` fait cet appel pour un conteneur ou un gestionnaire de services (code de sortie 0 sain, 1 pas sain, 2 pas de réponse, 3 refusé). Il lit le jeton d'accès dans `MONITOR_ACCESS_TOKEN`, dans le fichier nommé par `MONITOR_ACCESS_TOKEN_FILE` ou dans celui que le service garde dans `MONITOR_STATE_DIR`. `bin/monitor_cli.py health --deep` fait la même chose depuis n'importe quel ordinateur.

## L'image officielle

`ghcr.io/juanenrac/tools-github-actions-monitor` pour `linux/amd64` et `linux/arm64`, avec les étiquettes `2.1.0`, `2.1` et `latest`, construite par le workflow de publication avec une attestation de sa provenance. Elle est faite en trois étapes (`deploy/Dockerfile`) et ne contient que Python, la CLI GitHub, les certificats des CA et le code, en lecture seule et appartenant à root. Elle s'exécute avec l'utilisateur 10001 (jamais root) et n'écrit que dans deux volumes : `/config` (`actions_monitor.json`, créé au premier démarrage et jamais écrasé) et `/data` (`accounts/`, `state/` avec le jeton d'accès, `secrets/`, l'accès de `gh`). Elle écoute en mode réseau sur le port 8765 du conteneur ; toute requête exige donc le jeton d'accès, et elle ne publie aucun port d'elle-même.

```sh
docker run -d --name github-actions-monitor --restart unless-stopped \
  --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges:true \
  -e MONITOR_GITHUB_OWNER=my-org -e GH_TOKEN_FILE=/run/secrets/gh_token \
  -v "$PWD/gh_token.txt:/run/secrets/gh_token:ro" \
  -v monitor-config:/config -v monitor-data:/data \
  -p 127.0.0.1:8765:8765 \
  ghcr.io/juanenrac/tools-github-actions-monitor:latest

docker exec github-actions-monitor cat /data/state/access_token      # the access token, made on the first start
```

Au premier démarrage, elle crée la configuration, le premier compte (à partir de `MONITOR_GITHUB_OWNER` ; plusieurs avec `MONITOR_ACCOUNTS=perso:moi,travail:mon-org`) et, si `MONITOR_ACCESS_TOKEN` n'est pas donné, un jeton d'accès qu'elle garde dans `/data/state/access_token` (mode 600) et n'affiche jamais. Ouvrez la session sans mettre le jeton dans l'adresse : envoyez `POST /api/access` avec `{"token": "..."}` (le cookie revient dans la réponse) ou l'en-tête `X-Monitor-Access`. Pour l'ouvrir une fois depuis la barre d'adresse d'un navigateur, démarrez le conteneur avec `MONITOR_QUERY_ACCESS=1`, ouvrez `http://127.0.0.1:8765/?access=TOKEN` puis éteignez de nouveau la variable. Avec un bind mount au lieu d'un volume nommé, donnez le dossier à l'utilisateur 10001 (`chown -R 10001:10001`). L'édition lite n'est pas dans l'image.

## Docker Compose, avec proxy et TLS facultatifs

`deploy/compose.yaml` lance le moniteur avec le code en lecture seule, sans capacités, l'accès comme secret Docker et les deux volumes. Le profil `proxy` place Caddy (`deploy/Caddyfile`) devant : il obtient et renouvelle seul le certificat d'un nom public (`tls internal` pour un nom de votre propre réseau, `http://nom` pour aucun). Copiez `deploy/.env.example` vers `deploy/.env`, remplissez-le puis démarrez :

```sh
cp deploy/.env.example deploy/.env                                   # fill in MONITOR_GITHUB_OWNER
printf '%s' "ghp_..." > deploy/gh_token.txt && sudo chown 10001:10001 deploy/gh_token.txt && chmod 600 deploy/gh_token.txt
docker compose -f deploy/compose.yaml up -d                          # on 127.0.0.1:8765
docker compose -f deploy/compose.yaml --profile proxy up -d          # behind Caddy (deploy/Caddyfile)
```

Derrière le proxy, le moniteur doit connaître son nom public et savoir que la session est en HTTPS : `MONITOR_PROXY_PUBLIC_HOST` et `MONITOR_SECURE_COOKIE=1`. Plus rien de ce qui arrive sur le port principal ne compte alors comme l'ordinateur du moniteur : utilisez le second port (`MONITOR_LOCAL_PORT`, 8766 dans l'image, loopback seulement) avec `docker compose exec monitor python bin/monitor_cli.py ...` (l'image y fait pointer `MONITOR_URL`).

## Une installation classique avec systemd

`deploy/github-actions-monitor.service` et `deploy/github-actions-monitor.env` exécutent la version décompressée avec l'utilisateur `monitor` et le durcissement de systemd (rien d'inscriptible hors de son dossier, pas de nouveaux privilèges), la relancent en cas d'échec, vérifient la santé approfondie après le démarrage et relisent les fichiers d'identifiants sur `systemctl reload`.

```sh
useradd --system --home-dir /var/lib/github-actions-monitor --create-home --shell /usr/sbin/nologin monitor
install -d -o monitor -g monitor -m 700 /etc/github-actions-monitor
install -m 600 -o monitor deploy/github-actions-monitor.env /etc/github-actions-monitor/env     # edit it
install -m 644 deploy/github-actions-monitor.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now github-actions-monitor
systemctl reload github-actions-monitor                              # SIGHUP: read the credential files again
```

Le fichier env garde les données dans `/var/lib/github-actions-monitor` et l'accès dans `/etc/github-actions-monitor/gh_token` (mode 600). Il écoute sur `127.0.0.1` sauf si vous y activez le mode réseau.

launchd (macOS) : `ProgramArguments` = `/usr/bin/python3`, `-m`, `github_actions_monitor.service`, les variables dans `EnvironmentVariables`, `KeepAlive` et `RunAtLoad` à true. Windows : `schtasks /Create /SC ONLOGON /TN GhaMonitor /TR "py -3 C:/chemin/vers/bin/actions_monitor.py --no-browser"`.

## Variables d'environnement

Seuls les noms de ce tableau sont lus. Dans le service, une valeur illisible est ignorée avec un avertissement et ne change rien. Celles qui nomment une partie de la configuration (`MONITOR_LISTEN_*`, `MONITOR_ALLOWED_HOSTS`, `MONITOR_PROXY_PUBLIC_HOST`, `MONITOR_SECURE_COOKIE`, `MONITOR_TRUSTED_PROXY`, `MONITOR_LOCAL_PORT`, `MONITOR_TLS_*`, `MONITOR_QUERY_ACCESS`, `MONITOR_TEAM_MODE`) sont écrites dans `listen` et `auth` à chaque démarrage du service : l'environnement reste donc l'autorité pour elles ; tout le reste du fichier vous appartient. Une variable du proxy définie mais laissée vide (`MONITOR_TRUSTED_PROXY`, `MONITOR_TRUSTED_PROXIES`, `MONITOR_SECURE_COOKIE`, `MONITOR_PROXY_PUBLIC_HOST`, `MONITOR_ALLOWED_HOSTS`) désactive sa clé au démarrage, de sorte qu'une ligne vide du fichier `.env` ne maintient jamais en vie une ancienne déclaration du proxy ; une variable absente ne change rien.

| Variable | Ce qu'elle fait |
|---|---|
| `MONITOR_GITHUB_OWNER` | L'utilisateur ou l'organisation à surveiller ; le premier compte en est créé au premier démarrage. |
| `MONITOR_ACCOUNT` | L'identifiant du premier compte (par défaut `default`). |
| `MONITOR_ACCOUNTS` | Plusieurs comptes à la fois : `perso:moi,travail:mon-org` (id:propriétaire). Seulement s'il n'y a encore aucun compte. |
| `MONITOR_LANG` | La langue des textes (`en es de fr it ja zh pt`). |
| `MONITOR_PORT` | Le port dans le conteneur ou du service (par défaut 8765). |
| `MONITOR_CONFIG` | Le fichier de configuration (l'image : `/config/actions_monitor.json`) ; créé au premier démarrage et jamais écrasé. |
| `MONITOR_ACCOUNTS_DIR` | Le dossier des comptes, un dossier par compte (l'image : `/data/accounts`). |
| `MONITOR_STATE_DIR` | Les fichiers qui resteraient sinon à côté du code : le jeton d'accès du service, l'audit des connexions (l'image : `/data/state`). |
| `MONITOR_CONFIG_DIR` | Le dossier `config/` : les fichiers de configuration (`targets.json`, `quotas.json` ...) et `config_backups/` (l'image : `/config`). |
| `MONITOR_DATA_DIR` | Le dossier `data/` : l'état, les caches et les comptes ; `logs/` et `ai/` y sont placés, sauf si `MONITOR_LOGS_DIR` / `MONITOR_AI_DIR` disent autre chose (l'image : `/data`). Voir LAYOUT. |
| `MONITOR_SECRET_DIR` | L'endroit où vit le jeton conservé par le moniteur lui-même, si vous l'activez (l'image : `/data/secrets`). |
| `GH_CONFIG_DIR` | Le dossier de configuration de `gh` (l'image : `/data/gh`). |
| `GH_TOKEN_FILE` | Un fichier avec le jeton GitHub sur sa première ligne (un secret Docker, un credential systemd). Lu au démarrage et de nouveau sur SIGHUP. |
| `GH_TOKEN` | Un jeton GitHub dans l'environnement ; `gh` le lit. Un fichier vaut mieux : l'environnement est visible de tout processus du conteneur. |
| `GH_HOST` | Le nom d'un hôte GitHub Enterprise Server : tous les appels et tous les liens de la page l'utilisent. |
| `MONITOR_ACCESS_TOKEN` | Le jeton d'accès du mode réseau (16 caractères au moins). Sans lui, le service en crée un et le garde dans `MONITOR_STATE_DIR`. |
| `MONITOR_ACCESS_TOKEN_FILE` | Un fichier avec le jeton d'accès sur sa première ligne, à la place de la variable. |
| `MONITOR_LISTEN_NETWORK` | `1` = le mode réseau (`listen.network`) : il écoute sur `MONITOR_LISTEN_HOST` et toute requête exige le jeton d'accès. L'image l'active. |
| `MONITOR_LISTEN_HOST` | L'adresse d'écoute en mode réseau (`0.0.0.0` dans l'image ; ailleurs, mieux vaut une adresse privée de la machine). |
| `MONITOR_ALLOWED_HOSTS` | Les noms d'hôte que le moniteur accepte en plus de sa propre adresse, séparés par des virgules (`listen.allowed_hosts`). |
| `MONITOR_PROXY_PUBLIC_HOST` | Le nom public du proxy inverse (`listen.proxy_public_host`) ; il déclare le proxy. |
| `MONITOR_SECURE_COOKIE` | `1` = la session est en HTTPS (un proxy la termine) : le cookie porte Secure (`listen.secure_cookie`). |
| `MONITOR_TRUSTED_PROXY` | `1` = le proxy tourne sur la MÊME machine et son `X-Forwarded-For` est cru (`listen.trusted_proxy`). |
| `MONITOR_TRUSTED_PROXIES` | Adresses ou réseaux du proxy quand il n'est pas sur cette machine, séparés par des virgules (`listen.trusted_proxies`) ; seulement avec `MONITOR_TRUSTED_PROXY`. Le fichier Compose donne à Caddy l'adresse fixe `MONITOR_PROXY_IP` (172.29.77.250 par défaut, dans `MONITOR_SUBNET`) : indiquez cette seule adresse. |
| `MONITOR_LOCAL_PORT` | Un second port, loopback seulement, pour la personne devant la machine quand un proxy est déclaré (`listen.local_port` ; 8766 dans l'image). |
| `MONITOR_TLS_CERT_FILE` | Un certificat (PEM) pour servir directement en HTTPS (`listen.tls_cert_file`) ; avec sa clé. S'il est inutilisable, le moniteur ne démarre pas en HTTP simple. |
| `MONITOR_TLS_KEY_FILE` | La clé privée de ce certificat (`listen.tls_key_file`). |
| `MONITOR_QUERY_ACCESS` | `1` = l'adresse avec `?access=` peut ouvrir une session (`listen.query_access`, désactivé par défaut) ; la voie sûre est `POST /api/access`. |
| `MONITOR_TEAM_MODE` | `1` = le mode équipe (`auth.enabled`) : utilisateurs, rôles et sessions. |
| `MONITOR_ADMIN_USER` | Avec `MONITOR_ADMIN_PASSWORD_FILE` : le premier administrateur que le service crée quand le mode équipe est actif et qu'il n'y a pas encore d'utilisateur. |
| `MONITOR_ADMIN_PASSWORD_FILE` | Le fichier (par exemple un secret Docker) avec le mot de passe de `MONITOR_ADMIN_USER` sur sa première ligne. |
| `MONITOR_WEBHOOK_SECRET_FILE` | Le fichier (par exemple un secret Docker) avec le secret partagé du webhook entrant sur sa première ligne, à la place de `MONITOR_WEBHOOK_SECRET`. Avec Docker Compose, ajoutez `deploy/compose.webhook.yaml` et placez le secret dans `deploy/webhook_secret.txt`. |
| `MONITOR_SERVICE` | `1` = il tourne comme un service : il n'abandonne pas devant un accès inutilisable, et le doctor vérifie la rétention. L'image et le service l'activent. |
| `MONITOR_URL` | Pour `bin/monitor_cli.py` et le contrôle de santé : l'adresse du moniteur (l'image : le second port). |
| `MONITOR_CA_FILE` | Pour `bin/monitor_cli.py` : un fichier PEM avec l'autorité qui a signé le certificat HTTPS du moniteur. |
| `MONITOR_USER` | Pour `bin/monitor_cli.py` en mode équipe : l'utilisateur avec lequel se connecter. |
| `MONITOR_PASSWORD_FILE` | Pour `bin/monitor_cli.py` : un fichier avec le mot de passe de `MONITOR_USER` sur sa première ligne. |
| `MONITOR_RELEASE_TEST_TIMEOUT` | `tools/make_release.py` : secondes dont la suite ordinaire dispose avant que la porte échoue (par défaut 3600 ; de 60 à 86400). |
| `MONITOR_RELEASE_CLEAN_TIMEOUT` | `tools/make_release.py` : secondes dont dispose la suite du zip extrait (par défaut 3600 ; de 60 à 86400). |
| `MONITOR_RELEASE_LOG_DIR` | `tools/make_release.py` : dossier où est enregistrée TOUTE la sortie d'une suite en échec (par défaut, le dossier temporaire) ; le message de la porte nomme les tests en échec et ce fichier. Le même dossier garde `make_release_suite_skips.json` et `make_release_clean_skips.json` : les tests IGNORÉS, comptés par cause (navigateur, hors du zip, outil facultatif, plateforme, cet ordinateur, autre) et par motif, et la ligne de résultat de chaque suite répète le décompte, si bien que 24 ignorés dans l'arbre et davantage depuis le zip s'expliquent d'eux-mêmes. |
| `--accept-green-suite JSON --commit SHA [--skip-clean-suite]` | `tools/make_release.py` : au lieu de relancer la suite ordinaire, accepte l'enregistrement d'une exécution verte complète de ce même commit (terminée, sans échec ni erreur, tous les tests exécutés) ; `--skip-clean-suite` ne relance pas non plus la suite du zip extrait (ses contrôles rapides restent faits) et le dit. |
| `--progress` | `tools/make_release.py` : indique l'avancement des suites, une ligne tous les 250 tests, y compris dans la suite de l'installation propre. |

## Un battement externe (désactivé par défaut)

Le moniteur tourne sur un ordinateur qui peut être éteint, mis en veille ou redémarré, et alors personne n'apprend que personne ne surveille. Avec `heartbeat.enabled` activé, le moniteur envoie un ping à une adresse tous les `heartbeat.interval_seconds` (300 par défaut) et un service comme healthchecks.io, Cronitor ou Uptime Kuma vous dit quand les pings s'arrêtent.

- L'adresse est un secret : mettez-la dans la variable d'environnement que nomme `heartbeat.url_env` (`MONITOR_HEARTBEAT_URL` par défaut). Elle n'est jamais écrite dans la configuration, affichée ni journalisée, et les Réglages disent seulement si une est définie. Elle doit être en `https` (`http` seulement avec `notify.allow_private_targets`, pour un service de votre propre réseau), ne porter ni nom d'utilisateur ni mot de passe, et s'ouvre avec la même protection que les notifications.
- Le ping porte au plus `msg=<version> <ok|degraded>` (`heartbeat.send_state`) : jamais un dépôt, une alerte ou un nom.
- Quand le moniteur n'est pas en état de servir (sa boucle d'actualisation est bloquée ou absente), le ping n'est pas envoyé et le silence est l'alarme. Un service avec une adresse d'échec (healthchecks.io : `/fail`) peut recevoir `heartbeat.fail_suffix` et est alors prévenu aussitôt.
- Dans l'édition complète, `GET /api/health` montre `heartbeat` (envoyés, échoués, omis et le dernier résultat).

## Quand GitHub révoque l'accès ou qu'il expire

Chaque compte est un processus à part : un accès qui cesse de fonctionner ne touche que ce compte. Après deux refus de suite qui disent que l'accès lui-même est inutilisable (un 401, `Bad credentials`, un jeton expiré ou révoqué, un compte suspendu, aucun accès), le compte est **aveugle** : la page, le contrôle de santé approfondi, `GET /api/accounts` (`state: blind`) et `bin/monitor_cli.py` le disent, une **alerte critique du système** (`system.credential_blind`, sentinelle `system`) s'ouvre dans l'onglet Alertes, et les types de notification `credential_blind` (activé par défaut) et `credential_back` préviennent les canaux une fois. Le refus d'une seule permission (un 403 pour un dépôt) ne rend pas un compte aveugle. Les autres comptes continuent et le contrôle de santé approfondi reste au vert. Le compte continue d'essayer, et le premier bon cycle ferme l'alerte.

Un service qui démarre avec un accès déjà inutilisable reste actif et aveugle au lieu d'abandonner, pour qu'il y ait quelque chose à remplacer. Le jeton d'un compte vient de, le premier trouvé l'emporte : le fichier `credential` de son dossier (écrit par un remplacement), le fichier nommé par `GH_TOKEN_FILE`, puis ce qu'utilise `gh` (`GH_TOKEN` ou sa propre connexion). Un remplacement n'exige aucun redémarrage du superviseur ni du compte, de trois façons :

```sh
# 1. the command line (a token is read from a file or the standard input, never from a flag)
docker compose exec -T monitor python bin/monitor_cli.py credential replace --account default --new-token-file - < new_token.txt
python bin/monitor_cli.py credential replace --url https://monitor.example.org --user ann --password-file pw.txt --account default --new-token-file new_token.txt

# 2. the administrator endpoint (an administrator session in the team mode, or the computer of the monitor)
#    POST /api/accounts/<id>/credential   {"action": "replace", "token": "..."}   or   {"action": "reload"}
#    (a monitor without a supervisor: POST /api/credential, from its own computer)

# 3. replace the file and send SIGHUP: every account reads its credential files again
docker kill --signal HUP github-actions-monitor
systemctl reload github-actions-monitor
```

Le nouveau jeton est vérifié auprès de GitHub (l'appel `rate_limit`, gratuit) AVANT d'être gardé : un jeton que GitHub refuse ne change rien et répond 422 (`rejected`). Un bon jeton est écrit dans le dossier de ce compte seulement (mode 600), utilisé aussitôt, et le compte relit sans attendre. En mode équipe, le point d'accès est réservé à une session `admin` (avec le jeton CSRF d'une session par cookie) et l'audit enregistre qui l'a fait, jamais le jeton ; sans mode équipe, avec le mode réseau actif, seul l'ordinateur du moniteur le peut. Le jeton n'apparaît jamais dans une réponse, un journal, une alerte ni la page.

## Le premier administrateur dans un conteneur

Avec `MONITOR_TEAM_MODE=1`, l'image écoute sur le réseau, et le moniteur n'ouvre pas le réseau avant que le premier administrateur existe (qui ne peut être créé que depuis l'ordinateur du moniteur). Dans un conteneur, cela ne peut pas se faire sur `/login` et le mode réseau ne peut pas être désactivé (l'image le fixe à chaque démarrage) : le service s'arrêterait donc avec le code de sortie 1 dès son premier démarrage. Créez le premier administrateur une fois, sur les mêmes volumes, avant de démarrer le service (le mot de passe est demandé dans la console, jamais passé dans la ligne de commande) :

```sh
docker compose run --rm --entrypoint python monitor -m github_actions_monitor.security.auth_cli create-admin NAME
docker compose up -d
```

Ou laissez le service le créer : définissez `MONITOR_ADMIN_USER` et `MONITOR_ADMIN_PASSWORD_FILE` (un fichier, par exemple un secret Docker, avec le mot de passe sur sa première ligne) ; le premier démarrage crée cet administrateur quand le mode équipe est actif et qu'aucun utilisateur n'existe, et n'affiche jamais le mot de passe.

## Premier démarrage, sauvegarde et mise à jour

Premier démarrage comme service : indiquez le propriétaire et l'accès (`GH_TOKEN_FILE`), démarrez, lisez une fois le jeton d'accès (`/data/state/access_token`), ouvrez la page et lancez `bin/monitor_cli.py health --deep`. `python bin/actions_monitor.py --doctor` avec `MONITOR_SERVICE=1` avertit aussi d'un bloc de rétention absent et de comptes qui partagent un même jeton.

Sauvegarde : tout ce qu'il faut garder est dans les deux volumes. Faites une copie cohérente du stockage avant une mise à jour, et une copie des volumes :

```sh
docker compose exec monitor python /app/tools/backup_storage.py backup /data/state/backup.zip --backend file
docker cp github-actions-monitor:/data/state/backup.zip .
docker run --rm -v monitor-data:/data -v "$PWD":/backup alpine tar czf /backup/monitor-data.tgz -C /data .
```

Mise à jour : les données survivent car elles vivent dans les volumes. Fixez une version (`:2.1.0`) en production, téléchargez, recréez et vérifiez l'attestation de l'image. Un moniteur plus ancien n'ouvre jamais un stockage plus récent (voir `STORAGE.md`) ; gardez donc la sauvegarde jusqu'à ce que la nouvelle version ait tourné.

```sh
docker compose pull && docker compose up -d
gh attestation verify oci://ghcr.io/juanenrac/tools-github-actions-monitor:2.1.0 --owner JuanenRac
```

À partir de la 2.2.0, l'image est aussi signée avec Cosign sans clé (identité du workflow de publication) :

```sh
cosign verify ghcr.io/juanenrac/tools-github-actions-monitor:2.2.0 \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  --certificate-identity-regexp '^https://github\.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/\.github/workflows/release-image\.yml@refs/tags/v'
```

**Ce qui est testé et où** : le conteneur (utilisateur non root, système de fichiers en lecture seule, volumes, secrets, webhook derrière un proxy) par le workflow Docker audit ; l'unité de service sur un vrai systemd et une base de plus de 1 Go par le workflow Cross-cutting, qui restaure aussi une sauvegarde et exécute un cycle d'un compte avec une doublure de GitHub. Les systèmes de fichiers réseau (NFS) et d'autres architectures matérielles ne sont pas testés.

## Derrière un reverse proxy

Par défaut, le moniteur n'écoute que sur `127.0.0.1`. Si vous devez l'atteindre depuis une autre machine, placez devant un reverse proxy avec TLS, activez le mode réseau (`listen.network` : chaque requête doit alors porter le jeton d'accès) et DÉCLAREZ le proxy (`listen.proxy_public_host` avec son nom public, `listen.secure_cookie` ou `listen.trusted_proxy`). Le moniteur refuse toute requête dont le `Host` n'est ni sa propre adresse ni ce nom public ; le proxy doit donc l'envoyer, et il doit ajouter l'adresse réelle du client :

```nginx
location / {
    proxy_pass           http://127.0.0.1:8765;
    proxy_set_header     Host $host;                                  # the public name: set it in listen.proxy_public_host
    proxy_set_header     X-Forwarded-For $proxy_add_x_forwarded_for;  # APPENDS the real address of the client; never copy the one the client sent
    proxy_set_header     X-Forwarded-Proto $scheme;
}
```

Dès qu'un proxy est déclaré, rien de ce qui arrive sur le port principal ne compte comme « cet ordinateur », quoi que disent les en-têtes (un proxy qui oublie un en-tête ferait sinon passer pour locaux tous les clients d'internet). Les clés qui décident de l'exposition, les actions sur GitHub et les tests des canaux ne peuvent donc pas être utilisés depuis ce port. Pour les utiliser, ouvrez avec `listen.local_port` (un nombre de 1024 à 65535) un second port qui n'écoute que sur `127.0.0.1` et servez-vous-en depuis l'ordinateur du moniteur : il demande le même jeton d'accès.

`listen.trusted_proxy` suppose que le proxy tourne sur le MÊME ordinateur que le moniteur (le moniteur croit `X-Forwarded-For` sur toute connexion arrivant par la boucle locale) : ne l'utilisez pas avec un proxy sur une autre machine. Les mauvais jetons des requêtes qui arrivent sans `X-Forwarded-For` utilisable sont aussi comptés ensemble (trois fois la limite d'une adresse) ; ce verrou commun n'arrête jamais une requête qui porte le bon jeton. Si le proxy est dans un autre conteneur ou sur une autre machine, indiquez son adresse ou son réseau dans `listen.trusted_proxies` (`MONITOR_TRUSTED_PROXIES` ; dans le fichier Docker Compose, l'adresse fixe de Caddy `MONITOR_PROXY_IP`, pas tout le réseau `MONITOR_SUBNET` : un conteneur qui contourne Caddy serait cru lui aussi) : pour une connexion venant de ces adresses, ou de cet ordinateur, son `X-Forwarded-For` est cru pour compter les tentatives ; cela ne fait jamais passer une requête pour cet ordinateur.

## La ligne de commande contre un autre ordinateur

`bin/monitor_cli.py` fonctionne contre un moniteur d'une autre machine : `--url https://monitor.example.org` (ou `MONITOR_URL`), le jeton d'accès de `MONITOR_ACCESS_TOKEN` ou `--token-file`, `--ca-file` (ou `MONITOR_CA_FILE`) pour faire confiance à l'autorité qui a signé un certificat HTTPS à vous et, en mode équipe, `--user NOM` avec `--password-file FICHIER` (ou `MONITOR_USER`, `MONITOR_PASSWORD_FILE`), qui se connecte avec une session Bearer (`auth.allow_bearer`). `status`, `accounts`, `alerts`, `health` (`--deep`) et `credential` fonctionnent de même et les codes de sortie sont les mêmes (3 = refusé, aussi pour un compte aveugle dans `status` et `accounts`). Le HTTP simple vers un autre ordinateur affiche un avertissement.

## Permissions minimales de la connexion (`gh` ou un jeton à granularité fine)

- Listes de runs, jobs et issues : Actions (lecture), Issues (lecture), Metadata (lecture). Alertes : alertes Code scanning, Dependabot et Secret scanning (lecture). Pull requests et releases : Pull requests (lecture), Contents (lecture). Paquets : `read:packages`.
- Seules les actions optionnelles de l'IA écrivent : relancer un workflow demande Actions (écriture) et fermer une issue demande Issues (écriture). Laissez-les désactivées et ne donnez à la connexion que la lecture.

## Beaucoup de dépôts

Les lectures conditionnelles (`cache.etag`) font qu'un dépôt inchangé ne coûte aucun quota ; `mode: lite`, `ecosystems`, `exclude` et `max_workers` limitent le travail ; le webhook entrant supprime l'interrogation des dépôts qui envoient des événements. `discover_limit` est le nombre maximal de dépôts listés pour un compte (1000 par défaut).

## Tourner pendant des mois : stockage et conservation

Gardez `accounts/` (ou la base) sur un volume qui survit au conteneur et faites une sauvegarde avec `python tools/backup_storage.py backup FICHIER.zip --backend file` (ou `sqlite`) avant une mise à jour. Par défaut, un court passage supprime les événements de plus de 90 jours et les analyses de plus de 180 jours ; réglez `retention` dans la configuration pour changer cela, et `MONITOR_SERVICE=1` fait traiter le moniteur comme un service par `--doctor` (qui avertit alors s'il n'y a pas de bloc `retention` ou si les événements deviennent gros). Avec SQLite, une base par compte est le défaut ; un fichier partagé est possible et décrit dans [STORAGE_fra.md](STORAGE_fra.md).

## Sauvegardes, volumes et mises à jour

Pour un service, `deploy/github-actions-monitor-backup.service` et `deploy/github-actions-monitor-backup.timer` font chaque jour une sauvegarde complète (`monitor_cli.py backup create`) ; `deploy/compose.yaml` garde les sauvegardes dans un volume à part (`monitor-backups`). Avant une mise à jour, faites une sauvegarde et vérifiez-la, après, lancez le doctor. Les étapes, la restauration et les codes de sortie du doctor sont dans [OPS_fra.md](OPS_fra.md).

## Vérifier l'image dans de vrais conteneurs

Le dépôt contient un workflow, `docker-audit.yml`, qui construit sur GitHub l'image de n'importe quelle version (une étiquette ou un commit) et la vérifie dans de vrais conteneurs : le démarrage et le contrôle de santé, le contrat de l'API, le mode équipe avec son premier administrateur, Caddy comme proxy de confiance avec son propre TLS, le durcissement (pas de root, système de fichiers en lecture seule, aucune capacité), les volumes avec sauvegarde, restauration et passage depuis la version précédente, les secrets, l'arrêt et le webhook entrant derrière le proxy. Il n'exécute rien sur votre ordinateur, ne publie rien et n'utilise aucun secret. Lancez-le à la main et lisez le tableau du résumé de l'exécution et l'artefact `docker-audit-<version>` :

```sh
gh workflow run docker-audit.yml -f ref=<tag>
```

Les mêmes scripts s'exécutent sur une machine Linux avec Docker (`tools/docker_audit/run_all.sh`) ; `tools/docker_audit/LEEME.txt` explique comment lire chaque résultat.

## Le moniteur sur le téléphone

Tout ce qui figure dans cette section est désactivé ou inoffensif par défaut.

- **Application installable** (`pwa.enabled`) : la page propose un manifeste, deux icônes et un petit service worker, afin qu'un navigateur puisse installer le moniteur comme une application. Les fichiers sont `/manifest.webmanifest`, `/sw.js`, `/pwa/offline`, `/pwa/icon-192.png` et `/pwa/icon-512.png` ; en mode réseau ils sont servis derrière le jeton d'accès comme n'importe quelle page. Le worker ne garde que la page hors ligne et les icônes : jamais la page, jamais une réponse de l'API. Quand l'application revient au premier plan, ou que le réseau revient, la page demande aussitôt des données fraîches (`pwa.refresh_on_return`).
- **Vue compacte** (`ui.compact`) : `auto` l'utilise dans une fenêtre étroite, `on` toujours, `off` jamais ; `?compact=1` ou `?compact=0` la change pour une fenêtre. Le menu passe en haut comme une rangée d'onglets, les tableaux défilent latéralement, un écran tactile reçoit des cibles d'au moins 44 pixels et les boîtes de dialogue suivent la hauteur que laisse le clavier à l'écran. Sur un téléphone, en portrait ou en paysage, les chiffres de l'en-tête sont repliés derrière un bouton qui les ouvre, et ce navigateur retient le choix. Dans une fenêtre basse, la page défile jusqu'à l'onglet ouvert au lieu de le laisser sans hauteur, et à partir de 701 pixels de large les groupes de réglages forment une liste à gauche de leur panneau.
- **Appairage avec un code QR** (`pairing.enabled`, mode réseau uniquement) : ouvrez la palette (Ctrl+K) et choisissez « Appairer un téléphone », puis « Nouveau code QR ». Le code ne sert qu'une fois et pendant `pairing.code_minutes` minutes ; un nouveau code annule le précédent. Le téléphone le scanne, appuie sur le bouton de la page qui s'ouvre et reçoit son propre jeton (un cookie), jamais le jeton d'accès. La même fenêtre liste les appareils appairés et en retire un : son jeton cesse de fonctionner aussitôt. Au plus `pairing.max_devices` appareils ; un appareil doit être appairé de nouveau après `pairing.device_days` jours (0 = jamais). Le moniteur ne garde que le hachage de chaque jeton dans `devices.json` du dossier de données, un mauvais code compte contre l'adresse comme un mauvais jeton d'accès, et chaque appairage et chaque révocation laissent une ligne dans le journal des actions.

| Route | Ce qu'elle fait |
|---|---|
| `GET /api/devices` | les appareils appairés et si l'appairage est activé (cet ordinateur seulement) |
| `POST /api/pair/start` | ouvre un code à usage unique et répond avec son adresse et son code QR (cet ordinateur seulement, avec le jeton à usage unique de la page) |
| `POST /api/pair/redeem` | le téléphone utilise le code (`{"code": "..."}`) et reçoit son cookie |
| `POST /api/devices/revoke` | retire un appareil (`{"id": "..."}` ; cet ordinateur seulement) |

- **Palette et raccourcis** (`ui.palette`) : Ctrl+K ouvre une zone de recherche d'onglets, de dépôts et d'actions ; `?` liste les raccourcis, `/` va à la recherche de l'onglet, `r` actualise et `[` `]` changent d'onglet.
