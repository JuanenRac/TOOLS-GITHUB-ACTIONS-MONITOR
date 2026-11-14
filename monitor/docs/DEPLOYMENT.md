<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->


**🇺🇸 English** | [🇪🇸 Español](DEPLOYMENT_spa.md) | [🇫🇷 Français](DEPLOYMENT_fra.md) | [🇮🇹 Italiano](DEPLOYMENT_ita.md) | [🇩🇪 Deutsch](DEPLOYMENT_deu.md) | [🇨🇳 简体中文](DEPLOYMENT_zho.md) | [🇯🇵 日本語](DEPLOYMENT_jpn.md) | [🇵🇹 Português](DEPLOYMENT_por.md)

# Running it as a service

The monitor is a program that, by default, listens on `127.0.0.1` only and has no login. These notes are for running it as a service: the official image, Docker Compose with a reverse proxy, a classic install with systemd, and what happens when GitHub revokes the login.

## Where it listens

The monitor listens in one of three ways, and the page, `GET /api/accounts`, `monitor_cli.py status` and `monitor_cli.py accounts` say which: **this computer** (only `127.0.0.1`: the default, no login), **the network** (the network mode, `listen.network`: it also listens on `listen.host` and every request carries the access token) or **behind a proxy** (the network mode with a reverse proxy declared in front: `listen.proxy_public_host`, `listen.secure_cookie` or `listen.trusted_proxy`). The image and the service unit are made for the second and the third; a monitor you start by hand stays on the first.

In the network mode the supervisor of several accounts follows the same rules as the monitor of one account: the access token on every request (cookie, header or `POST /api/access`), a lock-out after wrong tokens, the `Host` check, optional TLS with your certificate, the second port of the person at the computer (`listen.local_port`), and the keys that decide exposure, the login of GitHub and the actions on GitHub only from the computer of the monitor (a request from the network reaches the account marked as remote).

## Without a browser, and the health check

`python -m github_actions_monitor.service` is the entry of a service: it prepares the folders and the first account from the environment (see the table below) and starts the monitor without a browser. `python actions_monitor.py --no-browser --port 8765` still works for a monitor you manage yourself.

`GET /api/health` answers `{"ok": true, "version": ..., "loaded": ..., "offline": ...}` plus the state of the refresh cycle and of the GitHub login of the account; it makes no call to GitHub. `GET /api/health?deep=1` is the deep check: it answers 503 when the refresh cycle of an account has run longer than `watchdog_minutes` (30 minutes if that is 0) or its thread is gone; in the supervisor of several accounts also when the supervision loop itself has stopped, when the cycle of ANY account is stuck, or when no account answers once the start is over. An account whose GitHub login is no good (blind) is named in the answer but is not a failure: a restart does not fix a lost login, a new one does.

`python -m github_actions_monitor.cli.healthcheck` makes that call for a container or a service manager (exit code 0 healthy, 1 unhealthy, 2 no answer, 3 refused). It reads the access token from `MONITOR_ACCESS_TOKEN`, from the file named by `MONITOR_ACCESS_TOKEN_FILE` or from the file the service keeps in `MONITOR_STATE_DIR`. `monitor_cli.py health --deep` does the same from any computer.

## The official image

`ghcr.io/juanenrac/tools-github-actions-monitor` for `linux/amd64` and `linux/arm64`, with the tags `1.8.2`, `1.8` and `latest`, built by the release workflow with an attestation of its provenance. It is made in three stages (`deploy/Dockerfile`) and holds only Python, the GitHub CLI, the CA certificates and the code, read-only and owned by root. It runs as the user 10001 (never as root) and writes only in two volumes: `/config` (`actions_monitor.json`, made on the first start and never overwritten) and `/data` (`accounts/`, `state/` with the access token, `secrets/`, the login of `gh`). It listens in the network mode on port 8765 of the container, so every request needs the access token, and it publishes no port by itself.

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

On the first start it makes the configuration, the first account (from `MONITOR_GITHUB_OWNER`; several with `MONITOR_ACCOUNTS=personal:me,work:my-org`) and, when `MONITOR_ACCESS_TOKEN` is not given, an access token that it keeps in `/data/state/access_token` (mode 600) and never prints. Open `http://127.0.0.1:8765/?access=TOKEN` once: the cookie is set and the address is cleaned. With a bind mount instead of a named volume, give the folder to the user 10001 (`chown -R 10001:10001`). The lite edition is not in the image.

## Docker Compose, with an optional proxy and TLS

`deploy/compose.yaml` runs the monitor with the code read-only, no capabilities, the login as a Docker secret and the two volumes. The profile `proxy` adds Caddy (`deploy/Caddyfile`) in front: it gets and renews the certificate of a public name by itself (`tls internal` for a name of your own network, `http://name` for none). Copy `deploy/.env.example` to `deploy/.env`, fill it in and start:

```sh
cp deploy/.env.example deploy/.env                                   # fill in MONITOR_GITHUB_OWNER
printf '%s' "ghp_..." > deploy/gh_token.txt && chmod 600 deploy/gh_token.txt
docker compose -f deploy/compose.yaml up -d                          # on 127.0.0.1:8765
docker compose -f deploy/compose.yaml --profile proxy up -d          # behind Caddy (deploy/Caddyfile)
```

Behind the proxy the monitor must know its public name and that the session is HTTPS: `MONITOR_PROXY_PUBLIC_HOST` and `MONITOR_SECURE_COOKIE=1`. Nothing that arrives on the main port then counts as the computer of the monitor: use the second port (`MONITOR_LOCAL_PORT`, 8766 in the image, loopback only) with `docker compose exec monitor python monitor_cli.py ...` (the image sets `MONITOR_URL` to it).

## A classic install with systemd

`deploy/github-actions-monitor.service` and `deploy/github-actions-monitor.env` run the unzipped release as the user `monitor` with the hardening of systemd (nothing writable but its own folder, no new privileges), restart it on failure, check the deep health after the start and read the credential files again on `systemctl reload`.

```sh
useradd --system --home-dir /var/lib/github-actions-monitor --create-home --shell /usr/sbin/nologin monitor
install -d -o monitor -g monitor -m 700 /etc/github-actions-monitor
install -m 600 -o monitor deploy/github-actions-monitor.env /etc/github-actions-monitor/env     # edit it
install -m 644 deploy/github-actions-monitor.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now github-actions-monitor
systemctl reload github-actions-monitor                              # SIGHUP: read the credential files again
```

The env file keeps the data in `/var/lib/github-actions-monitor` and the login in `/etc/github-actions-monitor/gh_token` (mode 600). It listens on `127.0.0.1` unless you turn the network mode on there.

launchd (macOS): `ProgramArguments` = `/usr/bin/python3`, `-m`, `github_actions_monitor.service`, the variables in `EnvironmentVariables`, `KeepAlive` and `RunAtLoad` true. Windows: `schtasks /Create /SC ONLOGON /TN GhaMonitor /TR "py -3 C:/path/to/actions_monitor.py --no-browser"`.

## Environment variables

Only the names in this table are read. In the service a value that cannot be read is ignored with a notice and changes nothing. The ones that name a part of the configuration (`MONITOR_LISTEN_*`, `MONITOR_ALLOWED_HOSTS`, `MONITOR_PROXY_PUBLIC_HOST`, `MONITOR_SECURE_COOKIE`, `MONITOR_TRUSTED_PROXY`, `MONITOR_LOCAL_PORT`, `MONITOR_TLS_*`, `MONITOR_QUERY_ACCESS`, `MONITOR_TEAM_MODE`) are written into `listen` and `auth` at every start of the service, so the environment stays the authority for them; everything else in the file is yours.

| Variable | What it does |
|---|---|
| `MONITOR_GITHUB_OWNER` | The user or organisation to watch; the first account is made from it on the first start. |
| `MONITOR_ACCOUNT` | The id of the first account (default `default`). |
| `MONITOR_ACCOUNTS` | Several accounts at once: `personal:me,work:my-org` (id:owner). Only when there is no account yet. |
| `MONITOR_LANG` | The language of the texts (`en es de fr it ja zh pt`). |
| `MONITOR_PORT` | The port inside the container or of the service (default 8765). |
| `MONITOR_CONFIG` | The configuration file (the image: `/config/actions_monitor.json`); made on the first start and never overwritten. |
| `MONITOR_ACCOUNTS_DIR` | The folder of the accounts, one folder each (the image: `/data/accounts`). |
| `MONITOR_STATE_DIR` | Files that would otherwise sit next to the code: the access token of the service, the audit of the logins (the image: `/data/state`). |
| `MONITOR_SECRET_DIR` | Where the token kept by the monitor itself lives, if you turn that on (the image: `/data/secrets`). |
| `GH_CONFIG_DIR` | The configuration folder of `gh` (the image: `/data/gh`). |
| `GH_TOKEN_FILE` | A file with the GitHub token on its first line (a Docker secret, a systemd credential). Read at the start and again on SIGHUP. |
| `GH_TOKEN` | A GitHub token in the environment; `gh` reads it. A file is better: the environment is visible to every process of the container. |
| `GH_HOST` | A GitHub Enterprise Server host name: every call and every link of the page then use it. |
| `MONITOR_ACCESS_TOKEN` | The access token of the network mode (at least 16 characters). Without it the service makes one and keeps it in `MONITOR_STATE_DIR`. |
| `MONITOR_ACCESS_TOKEN_FILE` | A file with the access token on its first line, instead of the variable. |
| `MONITOR_LISTEN_NETWORK` | `1` = the network mode (`listen.network`): it listens on `MONITOR_LISTEN_HOST` and every request needs the access token. The image sets it. |
| `MONITOR_LISTEN_HOST` | The address it listens on in the network mode (`0.0.0.0` in the image; a private address of the machine is better elsewhere). |
| `MONITOR_ALLOWED_HOSTS` | Host names the monitor accepts besides its own address, comma separated (`listen.allowed_hosts`). |
| `MONITOR_PROXY_PUBLIC_HOST` | The public name of the reverse proxy (`listen.proxy_public_host`); it declares the proxy. |
| `MONITOR_SECURE_COOKIE` | `1` = the session is HTTPS (a proxy terminates it): the cookie is marked Secure (`listen.secure_cookie`). |
| `MONITOR_TRUSTED_PROXY` | `1` = the proxy runs on the SAME machine and its `X-Forwarded-For` is believed (`listen.trusted_proxy`). |
| `MONITOR_LOCAL_PORT` | A second port, loopback only, for the person at the computer when a proxy is declared (`listen.local_port`; 8766 in the image). |
| `MONITOR_TLS_CERT_FILE` | A certificate (PEM) to serve HTTPS directly (`listen.tls_cert_file`); with the key. If it cannot be used the monitor does not start on plain HTTP. |
| `MONITOR_TLS_KEY_FILE` | The private key of that certificate (`listen.tls_key_file`). |
| `MONITOR_QUERY_ACCESS` | `0` = the address with `?access=` no longer opens a session (`listen.query_access`); use `POST /api/access`. |
| `MONITOR_TEAM_MODE` | `1` = the team mode (`auth.enabled`): users, roles and sessions. |
| `MONITOR_SERVICE` | `1` = it runs as a service: it does not give up on a login that is no good, and the doctor checks retention. The image and the service set it. |
| `MONITOR_URL` | For `monitor_cli.py` and the health check: the address of the monitor (the image: the second port). |
| `MONITOR_CA_FILE` | For `monitor_cli.py`: a PEM file with the authority that signed the HTTPS certificate of the monitor. |
| `MONITOR_USER` | For `monitor_cli.py` in the team mode: the user to sign in as. |
| `MONITOR_PASSWORD_FILE` | For `monitor_cli.py`: a file with the password of `MONITOR_USER` on its first line. |
| `MONITOR_RELEASE_TEST_TIMEOUT` | `tools/make_release.py`: seconds the ordinary suite may take before the gate fails (default 3600; 60 to 86400). |
| `MONITOR_RELEASE_CLEAN_TIMEOUT` | `tools/make_release.py`: seconds the suite of the extracted zip may take (default 3600; 60 to 86400). |

## When GitHub revokes or expires the login

Every account is a process of its own, so a login that stops working touches only that account. After two refusals in a row that say the login itself is no good (a 401, `Bad credentials`, an expired or revoked token, a suspended account, no login at all) the account is **blind**: the page, the deep health check, `GET /api/accounts` (`state: blind`) and `monitor_cli.py` say so, a **critical system alert** (`system.credential_blind`, sentinel `system`) opens in the Alerts tab, and the notification kinds `credential_blind` (on by default) and `credential_back` tell the channels once. A refusal of a single permission (a 403 for one repository) does not make an account blind. The other accounts go on and the deep health check stays green. The account keeps trying, and the first good cycle closes the alert.

A service that starts with a login that is already no good stays up and blind instead of giving up, so there is something to replace. The token of an account comes from, first match wins: the file `credential` in its folder (written by a replacement), the file named by `GH_TOKEN_FILE`, then what `gh` uses (`GH_TOKEN` or its own login). A replacement needs no restart of the supervisor or of the account, in three ways:

```sh
# 1. the command line (a token is read from a file or the standard input, never from a flag)
docker compose exec -T monitor python monitor_cli.py credential replace --account default --new-token-file - < new_token.txt
python monitor_cli.py credential replace --url https://monitor.example.org --user ann --password-file pw.txt --account default --new-token-file new_token.txt

# 2. the administrator endpoint (an administrator session in the team mode, or the computer of the monitor)
#    POST /api/accounts/<id>/credential   {"action": "replace", "token": "..."}   or   {"action": "reload"}
#    (a monitor without a supervisor: POST /api/credential, from its own computer)

# 3. replace the file and send SIGHUP: every account reads its credential files again
docker kill --signal HUP github-actions-monitor
systemctl reload github-actions-monitor
```

The new token is checked against GitHub (the `rate_limit` call, free) BEFORE it is kept: a token GitHub refuses changes nothing and answers 422 (`rejected`). A good one is written to the folder of that account only (mode 600), used at once, and the account reads again without waiting. In the team mode the endpoint is for an `admin` session (with the CSRF token of a cookie session) and the audit records who did it, never the token; without the team mode, while the network mode is on, only the computer of the monitor may. The token is never in an answer, a log, an alert or the page.

## First start, backup and upgrade

First start as a service: set the owner and the login (`GH_TOKEN_FILE`), start it, read the access token once (`/data/state/access_token`), open the page and run `monitor_cli.py health --deep`. `python actions_monitor.py --doctor` with `MONITOR_SERVICE=1` also warns about a missing retention block and about accounts that share one token.

Backup: everything to keep is in the two volumes. Make a consistent copy of the storage before an upgrade, and a copy of the volumes:

```sh
docker compose exec monitor python /app/tools/backup_storage.py backup /data/state/backup.zip --backend file
docker cp github-actions-monitor:/data/state/backup.zip .
docker run --rm -v monitor-data:/data -v "$PWD":/backup alpine tar czf /backup/monitor-data.tgz -C /data .
```

Upgrade: the data survive because they live in the volumes. Pin a version (`:1.8.2`) in production, pull, recreate and check the attestation of the image. A newer storage is never opened by an older monitor (see `STORAGE.md`), so keep the backup until the new version has run.

```sh
docker compose pull && docker compose up -d
gh attestation verify oci://ghcr.io/juanenrac/tools-github-actions-monitor:1.8.2 --owner JuanenRac
```

## Behind a reverse proxy

By default the monitor only listens on `127.0.0.1`. If you must reach it from another machine, put a reverse proxy with TLS in front, turn the network mode on (`listen.network`: then every request must carry the access token) and DECLARE the proxy (`listen.proxy_public_host` with its public name, `listen.secure_cookie`, or `listen.trusted_proxy`). The monitor refuses any request whose `Host` is not its own address or that public name, so the proxy must send it, and it must add the real address of the client:

```nginx
location / {
    proxy_pass           http://127.0.0.1:8765;
    proxy_set_header     Host $host;                                  # the public name: set it in listen.proxy_public_host
    proxy_set_header     X-Forwarded-For $proxy_add_x_forwarded_for;  # APPENDS the real address of the client; never copy the one the client sent
    proxy_set_header     X-Forwarded-Proto $scheme;
}
```

Once a proxy is declared, nothing that arrives on the main port counts as "this computer", whatever its headers say (a proxy that forgets a header would otherwise make every client of the internet look local). The keys that decide exposure, the actions on GitHub and the tests of the channels therefore cannot be used from there. To use them, open a second port that only listens on `127.0.0.1` with `listen.local_port` (a number from 1024 to 65535) and use it from the computer of the monitor: it asks for the same access token.

`listen.trusted_proxy` assumes that the proxy runs on the SAME computer as the monitor (the monitor believes `X-Forwarded-For` on any connection that arrives over loopback): do not use it with a proxy on another machine. The wrong tokens of all the clients of the proxy are also counted together (three times the limit of one address), so that changing the header at every attempt does not defeat the lock-out.

## The command line against another computer

`monitor_cli.py` works against a monitor on another machine: `--url https://monitor.example.org` (or `MONITOR_URL`), the access token from `MONITOR_ACCESS_TOKEN` or `--token-file`, `--ca-file` (or `MONITOR_CA_FILE`) to trust the authority that signed an HTTPS certificate of your own and, in the team mode, `--user NAME` with `--password-file FILE` (or `MONITOR_USER`, `MONITOR_PASSWORD_FILE`), which signs in with a Bearer session (`auth.allow_bearer`). `status`, `accounts`, `alerts`, `health` (`--deep`) and `credential` work the same way and the exit codes are the same (3 = refused, also for a blind account in `status` and `accounts`). Plain HTTP to another computer prints a warning.

## Minimum permissions of the login (`gh` or a fine-grained token)

- Run lists, jobs and issues: Actions (read), Issues (read), Metadata (read). Alerts: Code scanning, Dependabot and Secret scanning alerts (read). Pull requests and releases: Pull requests (read), Contents (read). Packages: `read:packages`.
- Only the optional AI actions write: re-running a workflow needs Actions (write) and closing an issue needs Issues (write). Leave them off and give the login read access only.

## Many repositories

Conditional reads (`cache.etag`) make an unchanged repository cost no quota; `mode: lite`, `ecosystems`, `exclude` and `max_workers` limit the work; the incoming webhook removes the polling of the repositories that send events. `discover_limit` is the most repositories listed for an account (default 1000).

## Running for months: storage and retention

Keep `accounts/` (or the database) on a volume that survives the container, and make a backup with `python tools/backup_storage.py backup FILE.zip --backend file` (or `sqlite`) before an update. Out of the box a short pass removes events older than 90 days and analytics older than 180 days; set `retention` in the configuration to change that, and `MONITOR_SERVICE=1` makes `--doctor` treat the monitor as a service (it then warns when there is no `retention` block or the events grow large). With SQLite, one database per account is the default; one shared file is possible and documented in [STORAGE.md](STORAGE.md).
