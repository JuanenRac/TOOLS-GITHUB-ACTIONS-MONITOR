<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](DEPLOYMENT.md) | [🇪🇸 Español](DEPLOYMENT_spa.md) | [🇫🇷 Français](DEPLOYMENT_fra.md) | [🇮🇹 Italiano](DEPLOYMENT_ita.md) | [🇩🇪 Deutsch](DEPLOYMENT_deu.md) | **🇨🇳 简体中文** | [🇯🇵 日本語](DEPLOYMENT_jpn.md) | [🇵🇹 Português](DEPLOYMENT_por.md)

# 作为服务运行

监视器是只监听 `127.0.0.1` 的本地程序,没有登录。这些说明用于在没有浏览器的情况下,在服务器或容器中,为一个账户或一个组织运行它。

## 无浏览器

`python actions_monitor.py --no-browser --port 8765`。`GET /api/health` 返回 `{"ok": true, "version": ..., "loaded": ..., "offline": ...}`,供服务管理器或容器检查使用;它不会调用 GitHub。


## 配置与环境

- 一切都在 `actions_monitor.json` 中;环境变量可增加 `GH_HOST`(GitHub Enterprise Server 的主机名:所有调用和页面链接都会使用它)、`GH_TOKEN`(由 `gh` 读取;监视器从不保存)、`MONITOR_LANG`、`MONITOR_ECOSYSTEMS_FILE`、`MONITOR_TARGETS_FILE` 和 `MONITOR_PROFILES_FILE`。
- `github_owner` 可以是用户或组织。要监视多个账户,请为每个账户各运行一个监视器,使用各自的端口和文件夹。


## 可改用的示例

systemd:

```ini
# /etc/systemd/system/github-actions-monitor.service
[Unit]
Description=GitHub Actions monitor
After=network-online.target

[Service]
User=monitor
WorkingDirectory=/opt/github_actions_monitor
EnvironmentFile=/etc/github-actions-monitor/env     # a file with a line GH_TOKEN=... (mode 600)
ExecStart=/usr/bin/python3 actions_monitor.py --no-browser --port 8765
Restart=on-failure
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/github_actions_monitor

[Install]
WantedBy=multi-user.target
```

容器:

```dockerfile
# the same file is deploy/Dockerfile of the repository (the CI builds it)
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
 && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /usr/share/keyrings/githubcli.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/githubcli.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list \
 && apt-get update && apt-get install -y gh && rm -rf /var/lib/apt/lists/*
COPY github_actions_monitor /app
WORKDIR /app
USER 1000
CMD ["python", "actions_monitor.py", "--no-browser", "--port", "8765"]
```
```yaml
# docker-compose.yml: the monitor only listens on 127.0.0.1, so on Linux share the host network namespace
services:
  monitor:
    build: .
    network_mode: host
    environment:
      GH_TOKEN: ${GH_TOKEN}          # a token with the minimum permissions listed below
    volumes:
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8765/api/health', timeout=4)"]
```

- launchd: `~/Library/LaunchAgents/org.example.ghamon.plist`: `ProgramArguments` = `/usr/bin/python3`, `actions_monitor.py`, `--no-browser`; `WorkingDirectory` = the folder; `KeepAlive` = true; `RunAtLoad` = true.
- Windows: `schtasks /Create /SC ONLOGON /TN GhaMonitor /TR "py -3 C:/path/to/actions_monitor.py --no-browser"`


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

## 登录所需的最小权限(`gh` 或细粒度令牌)

- 运行列表、作业和 issue:Actions(读)、Issues(读)、Metadata(读)。警报:Code scanning、Dependabot 和 Secret scanning 警报(读)。拉取请求和发布:Pull requests(读)、Contents(读)。包:`read:packages`。
- 只有可选的 AI 操作会写入:重新运行工作流需要 Actions(写),关闭 issue 需要 Issues(写)。请保持关闭,只给登录读权限。


## 大量仓库

条件读取(`cache.etag`)让未变化的仓库不消耗配额;`mode: lite`、`ecosystems`、`exclude` 和 `max_workers` 限制工作量;入站 Webhook 让发送事件的仓库不再需要轮询。`discover_limit` 是每个账户列出的仓库上限(默认 1000)。

## 连续运行数月:存储与保留

把 `accounts/`(或数据库)放在容器重建后仍能保留的卷上,更新前用 `python tools/backup_storage.py backup FILE.zip --backend file`(或 `sqlite`)备份。默认情况下,一次快速清理会删除超过 90 天的事件和超过 180 天的分析;要更改请在配置中设置 `retention`,而 `MONITOR_SERVICE=1` 会让 `--doctor` 把监视器当作服务(此时若没有 `retention` 区块或事件变得很大就会警告)。使用 SQLite 时默认每个账户一个数据库;也可以使用一个共享文件,详见 [STORAGE_zho.md](STORAGE_zho.md)。
