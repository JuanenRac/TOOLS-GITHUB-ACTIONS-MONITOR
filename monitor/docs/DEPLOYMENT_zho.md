<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->


[🇺🇸 English](DEPLOYMENT.md) | [🇪🇸 Español](DEPLOYMENT_spa.md) | [🇫🇷 Français](DEPLOYMENT_fra.md) | [🇮🇹 Italiano](DEPLOYMENT_ita.md) | [🇩🇪 Deutsch](DEPLOYMENT_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](DEPLOYMENT_jpn.md) | [🇵🇹 Português](DEPLOYMENT_por.md)

# 作为服务运行

监视器默认只监听 `127.0.0.1`，没有登录。本文说明如何把它作为服务运行：官方镜像、带反向代理的 Docker Compose、使用 systemd 的传统安装，以及 GitHub 撤销登录后会发生什么。

## 在哪里监听

监视器有三种监听方式，页面、`GET /api/accounts`、`monitor_cli.py status` 和 `monitor_cli.py accounts` 都会说明是哪一种：**本机**（仅 `127.0.0.1`：默认，无登录）、**网络**（网络模式 `listen.network`：同时监听 `listen.host`，每个请求都带访问令牌）或**代理之后**（前面声明了反向代理的网络模式：`listen.proxy_public_host`、`listen.secure_cookie` 或 `listen.trusted_proxy`）。镜像和服务单元是为第二种和第三种准备的；手动启动的监视器停留在第一种。

在网络模式下，多账户的监督进程遵循与单账户监视器相同的规则：每个请求都带访问令牌（Cookie、请求头或 `POST /api/access`）、令牌错误后锁定、`Host` 检查、可选的使用您证书的 TLS、本机操作者使用的第二个端口（`listen.local_port`），而决定暴露范围的键、GitHub 登录和对 GitHub 的操作只能来自监视器所在的计算机（来自网络的请求会以“远程”标记送达账户）。

## 无浏览器与健康检查

`python -m github_actions_monitor.service` 是服务的入口：它根据环境变量准备文件夹和第一个账户（见下表），并在无浏览器的情况下启动监视器。`python actions_monitor.py --no-browser --port 8765` 仍可用于您自己管理的监视器。

`GET /api/health` 返回 `{"ok": true, "version": ..., "loaded": ..., "offline": ...}`，外加刷新周期和该账户 GitHub 登录的状态；它不会调用 GitHub。`GET /api/health?deep=1` 是深度检查：当某个账户的刷新周期运行时间超过 `watchdog_minutes`（为 0 时按 30 分钟）或其线程已消失时返回 503；在多账户监督进程中，监督循环本身停止、任意账户的周期卡住，或启动完成后没有任何账户响应时也会返回 503。GitHub 登录无效（失明）的账户会在响应中列出，但不算故障：重启无法修复丢失的登录，换一个新的才行。

`python -m github_actions_monitor.cli.healthcheck` 为容器或服务管理器发出该调用（退出码 0 健康，1 不健康，2 无响应，3 被拒绝）。它从 `MONITOR_ACCESS_TOKEN`、`MONITOR_ACCESS_TOKEN_FILE` 指定的文件，或服务保存在 `MONITOR_STATE_DIR` 的文件中读取访问令牌。`monitor_cli.py health --deep` 可在任何计算机上做同样的事。

## 官方镜像

`ghcr.io/juanenrac/tools-github-actions-monitor`，支持 `linux/amd64` 和 `linux/arm64`，标签为 `1.8.2`、`1.8` 和 `latest`，由发布工作流构建并附带来源证明（attestation）。它分三个阶段构建（`deploy/Dockerfile`），只包含 Python、GitHub CLI、CA 证书和代码，只读且属于 root。它以用户 10001（从不以 root）运行，只写入两个卷：`/config`（`actions_monitor.json`，首次启动时创建，不会被覆盖）和 `/data`（`accounts/`、含访问令牌的 `state/`、`secrets/`、`gh` 的登录）。它在网络模式下监听容器的 8765 端口，因此每个请求都需要访问令牌，并且自身不会发布任何端口。

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

首次启动时，它会创建配置、第一个账户（来自 `MONITOR_GITHUB_OWNER`；多个账户用 `MONITOR_ACCOUNTS=personal:me,work:my-org`），并在未提供 `MONITOR_ACCESS_TOKEN` 时生成访问令牌，保存到 `/data/state/access_token`（权限 600），从不打印。打开一次 `http://127.0.0.1:8765/?access=TOKEN`：Cookie 会被设置并清理地址。若使用绑定挂载而非命名卷，请把文件夹交给用户 10001（`chown -R 10001:10001`）。lite 版不在镜像中。

## Docker Compose，可选代理与 TLS

`deploy/compose.yaml` 以只读代码、无任何 capability、登录作为 Docker secret 以及两个卷运行监视器。`proxy` 配置档在前面加上 Caddy（`deploy/Caddyfile`）：它会自动获取并续期公开域名的证书（自己网络内的名称用 `tls internal`，不要 TLS 则用 `http://name`）。把 `deploy/.env.example` 复制为 `deploy/.env`，填写后启动：

```sh
cp deploy/.env.example deploy/.env                                   # fill in MONITOR_GITHUB_OWNER
printf '%s' "ghp_..." > deploy/gh_token.txt && chmod 600 deploy/gh_token.txt
docker compose -f deploy/compose.yaml up -d                          # on 127.0.0.1:8765
docker compose -f deploy/compose.yaml --profile proxy up -d          # behind Caddy (deploy/Caddyfile)
```

在代理之后，监视器必须知道自己的公开名称，以及会话是 HTTPS：`MONITOR_PROXY_PUBLIC_HOST` 和 `MONITOR_SECURE_COOKIE=1`。此时到达主端口的任何请求都不再算作监视器所在的计算机：请使用第二个端口（`MONITOR_LOCAL_PORT`，镜像中为 8766，仅限回环），配合 `docker compose exec monitor python monitor_cli.py ...`（镜像已把 `MONITOR_URL` 指向它）。

## 使用 systemd 的传统安装

`deploy/github-actions-monitor.service` 和 `deploy/github-actions-monitor.env` 以用户 `monitor` 运行解压后的发布版本，并带有 systemd 加固（除自己的文件夹外不可写、无新增权限），失败时重启，启动后检查深度健康，并在 `systemctl reload` 时重新读取凭据文件。

```sh
useradd --system --home-dir /var/lib/github-actions-monitor --create-home --shell /usr/sbin/nologin monitor
install -d -o monitor -g monitor -m 700 /etc/github-actions-monitor
install -m 600 -o monitor deploy/github-actions-monitor.env /etc/github-actions-monitor/env     # edit it
install -m 644 deploy/github-actions-monitor.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now github-actions-monitor
systemctl reload github-actions-monitor                              # SIGHUP: read the credential files again
```

env 文件把数据放在 `/var/lib/github-actions-monitor`，登录放在 `/etc/github-actions-monitor/gh_token`（权限 600）。除非在其中启用网络模式，否则只监听 `127.0.0.1`。

launchd（macOS）：`ProgramArguments` = `/usr/bin/python3`、`-m`、`github_actions_monitor.service`，变量放在 `EnvironmentVariables`，`KeepAlive` 和 `RunAtLoad` 设为 true。Windows：`schtasks /Create /SC ONLOGON /TN GhaMonitor /TR "py -3 C:/path/to/actions_monitor.py --no-browser"`。

## 环境变量

只会读取本表中的名称。在服务中，无法读取的值会带提示被忽略，不改变任何内容。指向配置某一部分的变量（`MONITOR_LISTEN_*`、`MONITOR_ALLOWED_HOSTS`、`MONITOR_PROXY_PUBLIC_HOST`、`MONITOR_SECURE_COOKIE`、`MONITOR_TRUSTED_PROXY`、`MONITOR_LOCAL_PORT`、`MONITOR_TLS_*`、`MONITOR_QUERY_ACCESS`、`MONITOR_TEAM_MODE`）会在服务每次启动时写入 `listen` 和 `auth`，因此这些键以环境变量为准；文件中的其他内容归您所有。

| 变量 | 作用 |
|---|---|
| `MONITOR_GITHUB_OWNER` | 要监视的用户或组织；首次启动时据此创建第一个账户。 |
| `MONITOR_ACCOUNT` | 第一个账户的 id（默认 `default`）。 |
| `MONITOR_ACCOUNTS` | 一次创建多个账户：`personal:me,work:my-org`（id:所有者）。仅在尚无账户时生效。 |
| `MONITOR_LANG` | 文本语言（`en es de fr it ja zh pt`）。 |
| `MONITOR_PORT` | 容器内或服务的端口（默认 8765）。 |
| `MONITOR_CONFIG` | 配置文件（镜像中为 `/config/actions_monitor.json`）；首次启动时创建，之后不会被覆盖。 |
| `MONITOR_ACCOUNTS_DIR` | 账户文件夹，每个账户一个文件夹（镜像中为 `/data/accounts`）。 |
| `MONITOR_STATE_DIR` | 否则会放在代码旁边的文件：服务的访问令牌、登录审计（镜像中为 `/data/state`）。 |
| `MONITOR_SECRET_DIR` | 若启用，监视器自己保存的令牌所在位置（镜像中为 `/data/secrets`）。 |
| `GH_CONFIG_DIR` | `gh` 的配置文件夹（镜像中为 `/data/gh`）。 |
| `GH_TOKEN_FILE` | 第一行为 GitHub 令牌的文件（Docker secret、systemd credential）。启动时读取，收到 SIGHUP 时再读。 |
| `GH_TOKEN` | 环境变量中的 GitHub 令牌；`gh` 会读取。文件更好：容器内的任何进程都能看到环境变量。 |
| `GH_HOST` | GitHub Enterprise Server 的主机名：所有调用和页面上的所有链接都会使用它。 |
| `MONITOR_ACCESS_TOKEN` | 网络模式的访问令牌（至少 16 个字符）。没有时服务会生成一个并保存在 `MONITOR_STATE_DIR`。 |
| `MONITOR_ACCESS_TOKEN_FILE` | 第一行为访问令牌的文件，用来代替该变量。 |
| `MONITOR_LISTEN_NETWORK` | `1` = 网络模式（`listen.network`）：监听 `MONITOR_LISTEN_HOST`，每个请求都需要访问令牌。镜像已设置。 |
| `MONITOR_LISTEN_HOST` | 网络模式下监听的地址（镜像中为 `0.0.0.0`；其他场合最好用本机的私有地址）。 |
| `MONITOR_ALLOWED_HOSTS` | 除自身地址外，监视器接受的主机名，用逗号分隔（`listen.allowed_hosts`）。 |
| `MONITOR_PROXY_PUBLIC_HOST` | 反向代理的公开名称（`listen.proxy_public_host`）；声明代理的存在。 |
| `MONITOR_SECURE_COOKIE` | `1` = 会话为 HTTPS（由代理终止）：Cookie 带 Secure（`listen.secure_cookie`）。 |
| `MONITOR_TRUSTED_PROXY` | `1` = 代理运行在同一台机器上，并信任其 `X-Forwarded-For`（`listen.trusted_proxy`）。 |
| `MONITOR_LOCAL_PORT` | 声明了代理时，供本机操作者使用的第二个端口，仅限回环（`listen.local_port`；镜像中为 8766）。 |
| `MONITOR_TLS_CERT_FILE` | 直接提供 HTTPS 的证书（PEM，`listen.tls_cert_file`），需配合密钥。若无法使用，监视器不会退回明文 HTTP 启动。 |
| `MONITOR_TLS_KEY_FILE` | 该证书的私钥（`listen.tls_key_file`）。 |
| `MONITOR_QUERY_ACCESS` | `0` = 带 `?access=` 的地址不再打开会话（`listen.query_access`）；请使用 `POST /api/access`。 |
| `MONITOR_TEAM_MODE` | `1` = 团队模式（`auth.enabled`）：用户、角色和会话。 |
| `MONITOR_SERVICE` | `1` = 以服务方式运行：登录无效时不放弃，doctor 会检查保留策略。镜像和服务单元已设置。 |
| `MONITOR_URL` | 供 `monitor_cli.py` 和健康检查使用：监视器的地址（镜像中为第二个端口）。 |
| `MONITOR_CA_FILE` | 供 `monitor_cli.py` 使用：签发监视器 HTTPS 证书的颁发机构的 PEM 文件。 |
| `MONITOR_USER` | 团队模式下供 `monitor_cli.py` 使用：要登录的用户。 |
| `MONITOR_PASSWORD_FILE` | 供 `monitor_cli.py` 使用：第一行为 `MONITOR_USER` 密码的文件。 |
| `MONITOR_RELEASE_TEST_TIMEOUT` | `tools/make_release.py`：常规测试套件在闸门失败之前可用的秒数（默认 3600；60 到 86400）。 |
| `MONITOR_RELEASE_CLEAN_TIMEOUT` | `tools/make_release.py`：解压后的 zip 中测试套件可用的秒数（默认 3600；60 到 86400）。 |

## 当 GitHub 撤销登录或登录过期时

每个账户都是独立的进程，所以登录失效只影响该账户。连续两次被拒绝，且拒绝表明登录本身无效（401、`Bad credentials`、令牌过期或被撤销、账户被停用、根本没有登录）后，该账户进入**失明**状态：页面、深度健康检查、`GET /api/accounts`（`state: blind`）和 `monitor_cli.py` 都会说明，警报标签页会打开一条**严重的系统警报**（`system.credential_blind`，哨兵 `system`），通知类型 `credential_blind`（默认开启）和 `credential_back` 会各通知渠道一次。仅某一项权限被拒绝（某个仓库的 403）不会让账户失明。其他账户继续运行，深度健康检查保持正常。该账户会继续尝试，第一个成功的周期会关闭警报。

以已经失效的登录启动的服务不会放弃，而是保持运行并处于失明状态，这样才有东西可以替换。账户的令牌来源按先到先得：其文件夹中的 `credential` 文件（由替换写入）、`GH_TOKEN_FILE` 指定的文件，然后是 `gh` 使用的登录（`GH_TOKEN` 或其自身登录）。替换无需重启监督进程或账户，有三种方式：

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

新令牌在保存之前会先向 GitHub 验证（调用 `rate_limit`，免费）：GitHub 拒绝的令牌不会改变任何内容，并返回 422（`rejected`）。有效的令牌只写入该账户的文件夹（权限 600），立即使用，账户无需等待就会重新读取。在团队模式下，该端点仅限 `admin` 会话（Cookie 会话需带 CSRF 令牌），审计会记录是谁操作的，但绝不记录令牌；没有团队模式且网络模式开启时，只有监视器所在的计算机可以操作。令牌绝不会出现在响应、日志、警报或页面中。

## 首次启动、备份与升级

作为服务首次启动：设置所有者和登录（`GH_TOKEN_FILE`），启动，读取一次访问令牌（`/data/state/access_token`），打开页面并运行 `monitor_cli.py health --deep`。设置 `MONITOR_SERVICE=1` 后运行 `python actions_monitor.py --doctor`，还会提示缺少保留策略块以及共用同一令牌的账户。

备份：需要保留的内容都在两个卷里。升级前请对存储做一份一致的备份，并备份这些卷：

```sh
docker compose exec monitor python /app/tools/backup_storage.py backup /data/state/backup.zip --backend file
docker cp github-actions-monitor:/data/state/backup.zip .
docker run --rm -v monitor-data:/data -v "$PWD":/backup alpine tar czf /backup/monitor-data.tgz -C /data .
```

升级：数据保存在卷中，所以不会丢失。生产环境请固定版本（`:1.8.2`），拉取、重建，并校验镜像的来源证明。较旧的监视器绝不会打开较新的存储（见 `STORAGE.md`），所以请在新版本运行稳定之前保留备份。

```sh
docker compose pull && docker compose up -d
gh attestation verify oci://ghcr.io/juanenrac/tools-github-actions-monitor:1.8.2 --owner JuanenRac
```

## 置于反向代理之后

默认情况下,监控只监听 `127.0.0.1`。如果必须从另一台机器访问,请在前面放一个带 TLS 的反向代理,开启网络模式(`listen.network`:此时每个请求都必须带访问令牌),并声明该代理(带公开名称的 `listen.proxy_public_host`、`listen.secure_cookie` 或 `listen.trusted_proxy`)。监控会拒绝 `Host` 既不是自己的地址也不是该公开名称的任何请求,因此代理必须发送它,并且必须追加客户端的真实地址:

```nginx
location / {
    proxy_pass           http://127.0.0.1:8765;
    proxy_set_header     Host $host;                                  # the public name: set it in listen.proxy_public_host
    proxy_set_header     X-Forwarded-For $proxy_add_x_forwarded_for;  # APPENDS the real address of the client; never copy the one the client sent
    proxy_set_header     X-Forwarded-Proto $scheme;
}
```

一旦声明了代理,无论请求头怎么写,从主端口到达的任何请求都不算作“本机”(否则忘记加请求头的代理会让互联网上的所有客户端看起来都是本地的)。因此决定暴露范围的键、对 GitHub 的操作和通道测试无法从那里使用。要使用它们,请用 `listen.local_port`(1024 到 65535 之间的数字)再打开一个只监听 `127.0.0.1` 的端口,并在运行监控的这台电脑上使用它:它要求同一个访问令牌。

`listen.trusted_proxy` 假定代理与监控运行在同一台电脑上(监控会相信任何经回环地址到达的连接上的 `X-Forwarded-For`):不要用于位于另一台机器上的代理。代理所有客户端的错误令牌还会合计计数(为单个地址上限的三倍),这样每次尝试都更换请求头也无法绕过锁定。

## 针对另一台计算机的命令行

`monitor_cli.py` 可以对另一台机器上的监视器工作：`--url https://monitor.example.org`（或 `MONITOR_URL`），访问令牌来自 `MONITOR_ACCESS_TOKEN` 或 `--token-file`，用 `--ca-file`（或 `MONITOR_CA_FILE`）信任签发您自有 HTTPS 证书的机构；在团队模式下，用 `--user 名称` 配合 `--password-file 文件`（或 `MONITOR_USER`、`MONITOR_PASSWORD_FILE`），以 Bearer 会话登录（`auth.allow_bearer`）。`status`、`accounts`、`alerts`、`health`（`--deep`）和 `credential` 的工作方式相同，退出码也相同（3 = 被拒绝；在 `status` 和 `accounts` 中，失明的账户同样返回 3）。通过明文 HTTP 连接到另一台计算机时会打印警告。

## 登录所需的最小权限(`gh` 或细粒度令牌)

- 运行列表、作业和 issue:Actions(读)、Issues(读)、Metadata(读)。警报:Code scanning、Dependabot 和 Secret scanning 警报(读)。拉取请求和发布:Pull requests(读)、Contents(读)。包:`read:packages`。
- 只有可选的 AI 操作会写入:重新运行工作流需要 Actions(写),关闭 issue 需要 Issues(写)。请保持关闭,只给登录读权限。

## 大量仓库

条件读取(`cache.etag`)让未变化的仓库不消耗配额;`mode: lite`、`ecosystems`、`exclude` 和 `max_workers` 限制工作量;入站 Webhook 让发送事件的仓库不再需要轮询。`discover_limit` 是每个账户列出的仓库上限(默认 1000)。

## 连续运行数月:存储与保留

把 `accounts/`(或数据库)放在容器重建后仍能保留的卷上,更新前用 `python tools/backup_storage.py backup FILE.zip --backend file`(或 `sqlite`)备份。默认情况下,一次快速清理会删除超过 90 天的事件和超过 180 天的分析;要更改请在配置中设置 `retention`,而 `MONITOR_SERVICE=1` 会让 `--doctor` 把监视器当作服务(此时若没有 `retention` 区块或事件变得很大就会警告)。使用 SQLite 时默认每个账户一个数据库;也可以使用一个共享文件,详见 [STORAGE_zho.md](STORAGE_zho.md)。
