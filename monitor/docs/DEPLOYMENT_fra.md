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

## Sans navigateur, et le contrôle de santé

`python -m github_actions_monitor.service` est l'entrée d'un service : il prépare les dossiers et le premier compte à partir de l'environnement (voir le tableau ci-dessous) et lance le moniteur sans navigateur. `python bin/actions_monitor.py --no-browser --port 8765` reste valable pour un moniteur que vous gérez vous-même.

`GET /api/health` répond `{"ok": true, "version": ..., "loaded": ..., "offline": ...}` avec l'état du cycle d'actualisation et de l'accès GitHub du compte ; il n'appelle pas GitHub. `GET /api/health?deep=1` est le contrôle approfondi : il répond 503 quand le cycle d'actualisation d'un compte dure plus de `watchdog_minutes` (30 minutes si 0) ou que son fil a disparu ; dans le superviseur de plusieurs comptes aussi quand la boucle de supervision elle-même s'est arrêtée, quand le cycle de N'IMPORTE QUEL compte est bloqué, ou quand aucun compte ne répond une fois le démarrage passé. Un compte dont l'accès GitHub est inutilisable (aveugle) est nommé dans la réponse mais n'est pas une panne : un redémarrage ne répare pas un accès perdu, un nouvel accès si.

`python -m github_actions_monitor.cli.healthcheck` fait cet appel pour un conteneur ou un gestionnaire de services (code de sortie 0 sain, 1 pas sain, 2 pas de réponse, 3 refusé). Il lit le jeton d'accès dans `MONITOR_ACCESS_TOKEN`, dans le fichier nommé par `MONITOR_ACCESS_TOKEN_FILE` ou dans celui que le service garde dans `MONITOR_STATE_DIR`. `bin/monitor_cli.py health --deep` fait la même chose depuis n'importe quel ordinateur.

## L'image officielle

`ghcr.io/juanenrac/tools-github-actions-monitor` pour `linux/amd64` et `linux/arm64`, avec les étiquettes `1.8.2`, `1.8` et `latest`, construite par le workflow de publication avec une attestation de sa provenance. Elle est faite en trois étapes (`deploy/Dockerfile`) et ne contient que Python, la CLI GitHub, les certificats des CA et le code, en lecture seule et appartenant à root. Elle s'exécute avec l'utilisateur 10001 (jamais root) et n'écrit que dans deux volumes : `/config` (`actions_monitor.json`, créé au premier démarrage et jamais écrasé) et `/data` (`accounts/`, `state/` avec le jeton d'accès, `secrets/`, l'accès de `gh`). Elle écoute en mode réseau sur le port 8765 du conteneur ; toute requête exige donc le jeton d'accès, et elle ne publie aucun port d'elle-même.

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

Au premier démarrage, elle crée la configuration, le premier compte (à partir de `MONITOR_GITHUB_OWNER` ; plusieurs avec `MONITOR_ACCOUNTS=perso:moi,travail:mon-org`) et, si `MONITOR_ACCESS_TOKEN` n'est pas donné, un jeton d'accès qu'elle garde dans `/data/state/access_token` (mode 600) et n'affiche jamais. Ouvrez `http://127.0.0.1:8765/?access=TOKEN` une fois : le cookie est posé et l'adresse nettoyée. Avec un bind mount au lieu d'un volume nommé, donnez le dossier à l'utilisateur 10001 (`chown -R 10001:10001`). L'édition lite n'est pas dans l'image.

## Docker Compose, avec proxy et TLS facultatifs

`deploy/compose.yaml` lance le moniteur avec le code en lecture seule, sans capacités, l'accès comme secret Docker et les deux volumes. Le profil `proxy` place Caddy (`deploy/Caddyfile`) devant : il obtient et renouvelle seul le certificat d'un nom public (`tls internal` pour un nom de votre propre réseau, `http://nom` pour aucun). Copiez `deploy/.env.example` vers `deploy/.env`, remplissez-le puis démarrez :

```sh
cp deploy/.env.example deploy/.env                                   # fill in MONITOR_GITHUB_OWNER
printf '%s' "ghp_..." > deploy/gh_token.txt && chmod 600 deploy/gh_token.txt
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

Seuls les noms de ce tableau sont lus. Dans le service, une valeur illisible est ignorée avec un avertissement et ne change rien. Celles qui nomment une partie de la configuration (`MONITOR_LISTEN_*`, `MONITOR_ALLOWED_HOSTS`, `MONITOR_PROXY_PUBLIC_HOST`, `MONITOR_SECURE_COOKIE`, `MONITOR_TRUSTED_PROXY`, `MONITOR_LOCAL_PORT`, `MONITOR_TLS_*`, `MONITOR_QUERY_ACCESS`, `MONITOR_TEAM_MODE`) sont écrites dans `listen` et `auth` à chaque démarrage du service : l'environnement reste donc l'autorité pour elles ; tout le reste du fichier vous appartient.

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
| `MONITOR_LOCAL_PORT` | Un second port, loopback seulement, pour la personne devant la machine quand un proxy est déclaré (`listen.local_port` ; 8766 dans l'image). |
| `MONITOR_TLS_CERT_FILE` | Un certificat (PEM) pour servir directement en HTTPS (`listen.tls_cert_file`) ; avec sa clé. S'il est inutilisable, le moniteur ne démarre pas en HTTP simple. |
| `MONITOR_TLS_KEY_FILE` | La clé privée de ce certificat (`listen.tls_key_file`). |
| `MONITOR_QUERY_ACCESS` | `0` = l'adresse avec `?access=` n'ouvre plus de session (`listen.query_access`) ; utilisez `POST /api/access`. |
| `MONITOR_TEAM_MODE` | `1` = le mode équipe (`auth.enabled`) : utilisateurs, rôles et sessions. |
| `MONITOR_SERVICE` | `1` = il tourne comme un service : il n'abandonne pas devant un accès inutilisable, et le doctor vérifie la rétention. L'image et le service l'activent. |
| `MONITOR_URL` | Pour `bin/monitor_cli.py` et le contrôle de santé : l'adresse du moniteur (l'image : le second port). |
| `MONITOR_CA_FILE` | Pour `bin/monitor_cli.py` : un fichier PEM avec l'autorité qui a signé le certificat HTTPS du moniteur. |
| `MONITOR_USER` | Pour `bin/monitor_cli.py` en mode équipe : l'utilisateur avec lequel se connecter. |
| `MONITOR_PASSWORD_FILE` | Pour `bin/monitor_cli.py` : un fichier avec le mot de passe de `MONITOR_USER` sur sa première ligne. |
| `MONITOR_RELEASE_TEST_TIMEOUT` | `tools/make_release.py` : secondes dont la suite ordinaire dispose avant que la porte échoue (par défaut 3600 ; de 60 à 86400). |
| `MONITOR_RELEASE_CLEAN_TIMEOUT` | `tools/make_release.py` : secondes dont dispose la suite du zip extrait (par défaut 3600 ; de 60 à 86400). |

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

## Premier démarrage, sauvegarde et mise à jour

Premier démarrage comme service : indiquez le propriétaire et l'accès (`GH_TOKEN_FILE`), démarrez, lisez une fois le jeton d'accès (`/data/state/access_token`), ouvrez la page et lancez `bin/monitor_cli.py health --deep`. `python bin/actions_monitor.py --doctor` avec `MONITOR_SERVICE=1` avertit aussi d'un bloc de rétention absent et de comptes qui partagent un même jeton.

Sauvegarde : tout ce qu'il faut garder est dans les deux volumes. Faites une copie cohérente du stockage avant une mise à jour, et une copie des volumes :

```sh
docker compose exec monitor python /app/tools/backup_storage.py backup /data/state/backup.zip --backend file
docker cp github-actions-monitor:/data/state/backup.zip .
docker run --rm -v monitor-data:/data -v "$PWD":/backup alpine tar czf /backup/monitor-data.tgz -C /data .
```

Mise à jour : les données survivent car elles vivent dans les volumes. Fixez une version (`:1.8.2`) en production, téléchargez, recréez et vérifiez l'attestation de l'image. Un moniteur plus ancien n'ouvre jamais un stockage plus récent (voir `STORAGE.md`) ; gardez donc la sauvegarde jusqu'à ce que la nouvelle version ait tourné.

```sh
docker compose pull && docker compose up -d
gh attestation verify oci://ghcr.io/juanenrac/tools-github-actions-monitor:1.8.2 --owner JuanenRac
```

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

`listen.trusted_proxy` suppose que le proxy tourne sur le MÊME ordinateur que le moniteur (le moniteur croit `X-Forwarded-For` sur toute connexion arrivant par la boucle locale) : ne l'utilisez pas avec un proxy sur une autre machine. Les mauvais jetons de tous les clients du proxy sont aussi comptés ensemble (trois fois la limite d'une adresse), pour que changer l'en-tête à chaque essai n'annule pas le verrouillage.

## La ligne de commande contre un autre ordinateur

`bin/monitor_cli.py` fonctionne contre un moniteur d'une autre machine : `--url https://monitor.example.org` (ou `MONITOR_URL`), le jeton d'accès de `MONITOR_ACCESS_TOKEN` ou `--token-file`, `--ca-file` (ou `MONITOR_CA_FILE`) pour faire confiance à l'autorité qui a signé un certificat HTTPS à vous et, en mode équipe, `--user NOM` avec `--password-file FICHIER` (ou `MONITOR_USER`, `MONITOR_PASSWORD_FILE`), qui se connecte avec une session Bearer (`auth.allow_bearer`). `status`, `accounts`, `alerts`, `health` (`--deep`) et `credential` fonctionnent de même et les codes de sortie sont les mêmes (3 = refusé, aussi pour un compte aveugle dans `status` et `accounts`). Le HTTP simple vers un autre ordinateur affiche un avertissement.

## Permissions minimales de la connexion (`gh` ou un jeton à granularité fine)

- Listes de runs, jobs et issues : Actions (lecture), Issues (lecture), Metadata (lecture). Alertes : alertes Code scanning, Dependabot et Secret scanning (lecture). Pull requests et releases : Pull requests (lecture), Contents (lecture). Paquets : `read:packages`.
- Seules les actions optionnelles de l'IA écrivent : relancer un workflow demande Actions (écriture) et fermer une issue demande Issues (écriture). Laissez-les désactivées et ne donnez à la connexion que la lecture.

## Beaucoup de dépôts

Les lectures conditionnelles (`cache.etag`) font qu'un dépôt inchangé ne coûte aucun quota ; `mode: lite`, `ecosystems`, `exclude` et `max_workers` limitent le travail ; le webhook entrant supprime l'interrogation des dépôts qui envoient des événements. `discover_limit` est le nombre maximal de dépôts listés pour un compte (1000 par défaut).

## Tourner pendant des mois : stockage et conservation

Gardez `accounts/` (ou la base) sur un volume qui survit au conteneur et faites une sauvegarde avec `python tools/backup_storage.py backup FICHIER.zip --backend file` (ou `sqlite`) avant une mise à jour. Par défaut, un court passage supprime les événements de plus de 90 jours et les analyses de plus de 180 jours ; réglez `retention` dans la configuration pour changer cela, et `MONITOR_SERVICE=1` fait traiter le moniteur comme un service par `--doctor` (qui avertit alors s'il n'y a pas de bloc `retention` ou si les événements deviennent gros). Avec SQLite, une base par compte est le défaut ; un fichier partagé est possible et décrit dans [STORAGE_fra.md](STORAGE_fra.md).
