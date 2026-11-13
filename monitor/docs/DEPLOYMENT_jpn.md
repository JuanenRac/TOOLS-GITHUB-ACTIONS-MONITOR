<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](DEPLOYMENT.md) | [🇪🇸 Español](DEPLOYMENT_spa.md) | [🇫🇷 Français](DEPLOYMENT_fra.md) | [🇮🇹 Italiano](DEPLOYMENT_ita.md) | [🇩🇪 Deutsch](DEPLOYMENT_deu.md) | [🇨🇳 简体中文](DEPLOYMENT_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](DEPLOYMENT_por.md)

# サービスとして動かす

モニターは `127.0.0.1` だけで待ち受けるローカルプログラムで、ログインはありません。ここでは、ブラウザーなしでサーバーやコンテナー上で、1 つのアカウントまたは組織向けに動かす方法を説明します。

## ブラウザーなし

`python actions_monitor.py --no-browser --port 8765`。`GET /api/health` はサービスマネージャーやコンテナーのチェック向けに `{"ok": true, "version": ..., "loaded": ..., "offline": ...}` を返し、GitHub は呼び出しません。


## 設定と環境

- すべて `actions_monitor.json` にあります。環境変数では `GH_HOST`(GitHub Enterprise Server のホスト名。すべての呼び出しとページのリンクがこれを使います)、`GH_TOKEN`(`gh` が読み取ります。モニターは保存しません)、`MONITOR_LANG`、`MONITOR_ECOSYSTEMS_FILE`、`MONITOR_TARGETS_FILE`、`MONITOR_PROFILES_FILE` を追加できます。
- `github_owner` はユーザーでも組織でも構いません。複数のアカウントを監視するには、アカウントごとに別のポートとフォルダーでモニターを動かします。


## 調整して使う例

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

コンテナー:

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


## リバースプロキシの背後で

既定では、モニターは `127.0.0.1` だけで待ち受けます。別のマシンから接続する必要がある場合は、TLS 付きのリバースプロキシを前段に置き、ネットワークモードをオンにし(`listen.network`:すべてのリクエストがアクセストークンを持つ必要があります)、プロキシを宣言してください(公開名を指定した `listen.proxy_public_host`、`listen.secure_cookie`、または `listen.trusted_proxy`)。モニターは `Host` が自身のアドレスでもその公開名でもないリクエストを拒否します。そのためプロキシは `Host` を送り、さらにクライアントの実際のアドレスを追加する必要があります。

```nginx
location / {
    proxy_pass           http://127.0.0.1:8765;
    proxy_set_header     Host $host;                                  # the public name: set it in listen.proxy_public_host
    proxy_set_header     X-Forwarded-For $proxy_add_x_forwarded_for;  # APPENDS the real address of the client; never copy the one the client sent
    proxy_set_header     X-Forwarded-Proto $scheme;
}
```

プロキシを宣言すると、メインポートに届くものはヘッダーの内容にかかわらず「このコンピューター」とは見なされません(ヘッダーを付け忘れるプロキシがあると、インターネット上のすべてのクライアントがローカルに見えてしまうためです)。そのため、公開範囲を決めるキー、GitHub 上の操作、チャンネルのテストはそこからは使えません。使うには、`listen.local_port`(1024〜65535 の数値)で `127.0.0.1` だけで待ち受ける第2のポートを開き、モニターのあるコンピューターからそれを使ってください。同じアクセストークンが必要です。

`listen.trusted_proxy` は、プロキシがモニターと「同じ」コンピューター上で動いていることを前提とします(モニターはループバックで届くあらゆる接続の `X-Forwarded-For` を信じます)。別のマシン上のプロキシでは使わないでください。プロキシのすべてのクライアントの誤ったトークンは合計でも数えられます(1つのアドレスの上限の3倍)。試行のたびにヘッダーを変えてもロックアウトは無効になりません。

## ログインに必要な最小限の権限(`gh` または細粒度トークン)

- 実行リスト・ジョブ・issue:Actions(読み取り)、Issues(読み取り)、Metadata(読み取り)。アラート:Code scanning、Dependabot、Secret scanning のアラート(読み取り)。プルリクエストとリリース:Pull requests(読み取り)、Contents(読み取り)。パッケージ:`read:packages`。
- 書き込むのは任意の AI アクションだけです。ワークフローの再実行には Actions(書き込み)、issue のクローズには Issues(書き込み)が必要です。これらはオフのままにして、ログインには読み取りだけを与えてください。


## 多数のリポジトリ

条件付き読み取り(`cache.etag`)により、変更のないリポジトリは割り当てを消費しません。`mode: lite`、`ecosystems`、`exclude`、`max_workers` で作業量を制限でき、受信 Webhook はイベントを送るリポジトリの定期取得を不要にします。`discover_limit` はアカウントごとに一覧するリポジトリの最大数です(既定 1000)。

## 何か月も動かす場合:保存と保持

`accounts/`(またはデータベース)はコンテナがなくなっても残るボリュームに置き、更新の前に `python tools/backup_storage.py backup FILE.zip --backend file`(または `sqlite`)でバックアップを取ってください。初期状態では、短い処理が90日より古いイベントと180日より古い分析を削除します。変更するには設定の `retention` を使い、`MONITOR_SERVICE=1` を付けると `--doctor` がモニターをサービスとして扱います(その場合、`retention` ブロックがない、またはイベントが大きくなっていると警告します)。SQLiteでは1アカウント1データベースが既定で、共有ファイル1つも可能です([STORAGE_jpn.md](STORAGE_jpn.md) を参照)。
