<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->


[🇺🇸 English](DEPLOYMENT.md) | [🇪🇸 Español](DEPLOYMENT_spa.md) | [🇫🇷 Français](DEPLOYMENT_fra.md) | [🇮🇹 Italiano](DEPLOYMENT_ita.md) | [🇩🇪 Deutsch](DEPLOYMENT_deu.md) | [🇨🇳 简体中文](DEPLOYMENT_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](DEPLOYMENT_por.md)

# サービスとして動かす

モニターは、既定では `127.0.0.1` だけで待ち受け、ログインを持たないプログラムです。このドキュメントは、サービスとして動かす方法を説明します。公式イメージ、リバースプロキシ付きの Docker Compose、systemd による従来のインストール、そして GitHub がログインを失効させたときの動作です。

## どこで待ち受けるか

モニターは 3 通りのどれかで待ち受け、ページ、`GET /api/accounts`、`monitor_cli.py status`、`monitor_cli.py accounts` がそのどれかを示します。**このコンピューター**（`127.0.0.1` のみ。既定でログインなし）、**ネットワーク**（ネットワークモード `listen.network`: `listen.host` でも待ち受け、すべてのリクエストがアクセストークンを持つ）、または**プロキシの背後**（手前にリバースプロキシを宣言したネットワークモード: `listen.proxy_public_host`、`listen.secure_cookie`、`listen.trusted_proxy`）。イメージとサービスユニットは 2 番目と 3 番目のために作られており、手で起動したモニターは 1 番目のままです。

ネットワークモードでは、複数アカウントのスーパーバイザーも 1 アカウントのモニターと同じルールに従います。すべてのリクエストでアクセストークン（Cookie、ヘッダー、または `POST /api/access`）、誤ったトークンの後のロックアウト、`Host` の検査、お使いの証明書による任意の TLS、コンピューターの前にいる人用の 2 つ目のポート（`listen.local_port`）、そして公開範囲を決めるキー、GitHub のログイン、GitHub への操作はモニターのコンピューターからのみ（ネットワークからのリクエストはリモートと印を付けてアカウントに届きます）。

## ブラウザーなしで、そしてヘルスチェック

`python -m github_actions_monitor.service` はサービスの入口です。環境変数からフォルダーと最初のアカウントを用意し（下の表を参照）、ブラウザーなしでモニターを起動します。自分で管理するモニターには、引き続き `python actions_monitor.py --no-browser --port 8765` が使えます。

`GET /api/health` は `{"ok": true, "version": ..., "loaded": ..., "offline": ...}` に加えて、更新サイクルとアカウントの GitHub ログインの状態を返します。GitHub は呼び出しません。`GET /api/health?deep=1` は詳細チェックで、アカウントの更新サイクルが `watchdog_minutes`（0 なら 30 分）より長く動いている、またはそのスレッドが消えている場合に 503 を返します。複数アカウントのスーパーバイザーでは、監視ループ自体が止まった場合、いずれかのアカウントのサイクルが固まった場合、起動後にどのアカウントも応答しない場合にも 503 です。GitHub ログインが使えないアカウント（ブラインド）は応答に名前が出ますが、障害ではありません。再起動では失ったログインは直らず、新しいログインが必要です。

`python -m github_actions_monitor.cli.healthcheck` は、コンテナーやサービスマネージャー向けにその呼び出しを行います（終了コード 0 正常、1 異常、2 応答なし、3 拒否）。アクセストークンは `MONITOR_ACCESS_TOKEN`、`MONITOR_ACCESS_TOKEN_FILE` が指すファイル、またはサービスが `MONITOR_STATE_DIR` に保持するファイルから読みます。`monitor_cli.py health --deep` はどのコンピューターからでも同じことを行います。

## 公式イメージ

`ghcr.io/juanenrac/tools-github-actions-monitor`（`linux/amd64` と `linux/arm64`）。タグは `1.8.2`、`1.8`、`latest` で、リリースのワークフローが出所の証明（attestation）付きでビルドします。3 段階で作られ（`deploy/Dockerfile`）、Python、GitHub CLI、CA 証明書、コードだけを含み、読み取り専用で root の所有です。ユーザー 10001（root ではない）で動き、書き込むのは 2 つのボリュームだけです: `/config`（`actions_monitor.json`。最初の起動で作られ、上書きされません）と `/data`（`accounts/`、アクセストークンを含む `state/`、`secrets/`、`gh` のログイン）。ネットワークモードでコンテナーのポート 8765 を待ち受けるので、すべてのリクエストにアクセストークンが必要で、ポートは自分では公開しません。

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

最初の起動では、設定、最初のアカウント（`MONITOR_GITHUB_OWNER` から。複数は `MONITOR_ACCOUNTS=personal:me,work:my-org`）、そして `MONITOR_ACCESS_TOKEN` がなければアクセストークンを作り、`/data/state/access_token`（モード 600）に保存して表示しません。`http://127.0.0.1:8765/?access=TOKEN` を一度開くと、Cookie が設定されてアドレスが整理されます。名前付きボリュームの代わりにバインドマウントを使う場合は、フォルダーをユーザー 10001 に渡してください（`chown -R 10001:10001`）。Lite エディションはイメージに含まれません。

## Docker Compose（任意のプロキシと TLS 付き）

`deploy/compose.yaml` は、コードを読み取り専用、ケーパビリティなし、ログインを Docker シークレット、2 つのボリュームでモニターを動かします。プロファイル `proxy` は手前に Caddy（`deploy/Caddyfile`）を加え、公開名の証明書を自動で取得・更新します（自分のネットワークの名前なら `tls internal`、TLS なしなら `http://name`）。`deploy/.env.example` を `deploy/.env` にコピーして記入し、起動します:

```sh
cp deploy/.env.example deploy/.env                                   # fill in MONITOR_GITHUB_OWNER
printf '%s' "ghp_..." > deploy/gh_token.txt && chmod 600 deploy/gh_token.txt
docker compose -f deploy/compose.yaml up -d                          # on 127.0.0.1:8765
docker compose -f deploy/compose.yaml --profile proxy up -d          # behind Caddy (deploy/Caddyfile)
```

プロキシの背後では、モニターは自分の公開名とセッションが HTTPS であることを知る必要があります: `MONITOR_PROXY_PUBLIC_HOST` と `MONITOR_SECURE_COOKIE=1`。すると、メインポートに届くものはモニターのコンピューターとは見なされません。2 つ目のポート（`MONITOR_LOCAL_PORT`、イメージでは 8766、ループバックのみ）を `docker compose exec monitor python monitor_cli.py ...` で使います（イメージは `MONITOR_URL` をそこに向けています）。

## systemd による従来のインストール

`deploy/github-actions-monitor.service` と `deploy/github-actions-monitor.env` は、展開したリリースをユーザー `monitor` として、systemd の堅牢化（自分のフォルダー以外は書き込み不可、権限の追加なし）付きで動かし、失敗時に再起動し、起動後に詳細ヘルスを確認し、`systemctl reload` で認証情報ファイルを読み直します。

```sh
useradd --system --home-dir /var/lib/github-actions-monitor --create-home --shell /usr/sbin/nologin monitor
install -d -o monitor -g monitor -m 700 /etc/github-actions-monitor
install -m 600 -o monitor deploy/github-actions-monitor.env /etc/github-actions-monitor/env     # edit it
install -m 644 deploy/github-actions-monitor.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now github-actions-monitor
systemctl reload github-actions-monitor                              # SIGHUP: read the credential files again
```

env ファイルはデータを `/var/lib/github-actions-monitor` に、ログインを `/etc/github-actions-monitor/gh_token`（モード 600）に置きます。そこでネットワークモードを有効にしない限り、`127.0.0.1` で待ち受けます。

launchd（macOS）: `ProgramArguments` = `/usr/bin/python3`、`-m`、`github_actions_monitor.service`、変数は `EnvironmentVariables`、`KeepAlive` と `RunAtLoad` は true。Windows: `schtasks /Create /SC ONLOGON /TN GhaMonitor /TR "py -3 C:/path/to/actions_monitor.py --no-browser"`。

## 環境変数

この表の名前だけが読み込まれます。サービスでは、読み取れない値は通知とともに無視され、何も変更しません。設定の一部を指す変数（`MONITOR_LISTEN_*`、`MONITOR_ALLOWED_HOSTS`、`MONITOR_PROXY_PUBLIC_HOST`、`MONITOR_SECURE_COOKIE`、`MONITOR_TRUSTED_PROXY`、`MONITOR_LOCAL_PORT`、`MONITOR_TLS_*`、`MONITOR_QUERY_ACCESS`、`MONITOR_TEAM_MODE`）は、サービスの起動のたびに `listen` と `auth` に書き込まれ、これらについては環境変数が優先されます。ファイルのそれ以外はあなたのものです。

| 変数 | 内容 |
|---|---|
| `MONITOR_GITHUB_OWNER` | 監視するユーザーまたは組織。最初の起動で、これから最初のアカウントが作られます。 |
| `MONITOR_ACCOUNT` | 最初のアカウントの ID（既定は `default`）。 |
| `MONITOR_ACCOUNTS` | 複数のアカウントを一度に: `personal:me,work:my-org`（id:所有者）。アカウントがまだない場合のみ。 |
| `MONITOR_LANG` | テキストの言語（`en es de fr it ja zh pt`）。 |
| `MONITOR_PORT` | コンテナー内またはサービスのポート（既定は 8765）。 |
| `MONITOR_CONFIG` | 設定ファイル（イメージでは `/config/actions_monitor.json`）。最初の起動で作られ、上書きされません。 |
| `MONITOR_ACCOUNTS_DIR` | アカウントのフォルダー。アカウントごとに 1 つ（イメージでは `/data/accounts`）。 |
| `MONITOR_STATE_DIR` | そのままではコードの隣に置かれるファイル: サービスのアクセストークン、ログインの監査（イメージでは `/data/state`）。 |
| `MONITOR_SECRET_DIR` | モニター自身が保持するトークンの置き場所（有効にした場合。イメージでは `/data/secrets`）。 |
| `GH_CONFIG_DIR` | `gh` の設定フォルダー（イメージでは `/data/gh`）。 |
| `GH_TOKEN_FILE` | 1 行目に GitHub トークンを書いたファイル（Docker シークレット、systemd の credential）。起動時と SIGHUP で読み込みます。 |
| `GH_TOKEN` | 環境変数の GitHub トークン。`gh` が読みます。ファイルのほうが安全です。環境変数はコンテナー内のすべてのプロセスから見えます。 |
| `GH_HOST` | GitHub Enterprise Server のホスト名。すべての呼び出しとページのすべてのリンクがこれを使います。 |
| `MONITOR_ACCESS_TOKEN` | ネットワークモードのアクセストークン（16 文字以上）。なければサービスが作り、`MONITOR_STATE_DIR` に保存します。 |
| `MONITOR_ACCESS_TOKEN_FILE` | 変数の代わりに、1 行目にアクセストークンを書いたファイル。 |
| `MONITOR_LISTEN_NETWORK` | `1` = ネットワークモード（`listen.network`）: `MONITOR_LISTEN_HOST` で待ち受け、すべてのリクエストにアクセストークンが必要です。イメージが設定します。 |
| `MONITOR_LISTEN_HOST` | ネットワークモードで待ち受けるアドレス（イメージでは `0.0.0.0`。それ以外ではマシンのプライベートアドレスが望ましい）。 |
| `MONITOR_ALLOWED_HOSTS` | モニター自身のアドレスのほかに受け付けるホスト名（カンマ区切り、`listen.allowed_hosts`）。 |
| `MONITOR_PROXY_PUBLIC_HOST` | リバースプロキシの公開名（`listen.proxy_public_host`）。プロキシを宣言します。 |
| `MONITOR_SECURE_COOKIE` | `1` = セッションは HTTPS（プロキシが終端）: Cookie に Secure が付きます（`listen.secure_cookie`）。 |
| `MONITOR_TRUSTED_PROXY` | `1` = プロキシは同じマシンで動いており、その `X-Forwarded-For` を信用します（`listen.trusted_proxy`）。 |
| `MONITOR_LOCAL_PORT` | プロキシ宣言時にコンピューターの前にいる人のための、ループバック専用の 2 つ目のポート（`listen.local_port`。イメージでは 8766）。 |
| `MONITOR_TLS_CERT_FILE` | HTTPS を直接提供するための証明書（PEM、`listen.tls_cert_file`）。鍵とともに指定します。使えない場合、モニターは平文 HTTP では起動しません。 |
| `MONITOR_TLS_KEY_FILE` | その証明書の秘密鍵（`listen.tls_key_file`）。 |
| `MONITOR_QUERY_ACCESS` | `0` = `?access=` 付きのアドレスではセッションを開きません（`listen.query_access`）。`POST /api/access` を使ってください。 |
| `MONITOR_TEAM_MODE` | `1` = チームモード（`auth.enabled`）: ユーザー、ロール、セッション。 |
| `MONITOR_SERVICE` | `1` = サービスとして動作: 使えないログインでも諦めず、doctor が保持設定を確認します。イメージとサービスが設定します。 |
| `MONITOR_URL` | `monitor_cli.py` とヘルスチェック用: モニターのアドレス（イメージでは 2 つ目のポート）。 |
| `MONITOR_CA_FILE` | `monitor_cli.py` 用: モニターの HTTPS 証明書に署名した認証局の PEM ファイル。 |
| `MONITOR_USER` | チームモードの `monitor_cli.py` 用: サインインするユーザー。 |
| `MONITOR_PASSWORD_FILE` | `monitor_cli.py` 用: 1 行目に `MONITOR_USER` のパスワードを書いたファイル。 |
| `MONITOR_RELEASE_TEST_TIMEOUT` | `tools/make_release.py`: ゲートが失敗するまでに通常のスイートが使える秒数（既定 3600、60〜86400）。 |
| `MONITOR_RELEASE_CLEAN_TIMEOUT` | `tools/make_release.py`: 展開した zip のスイートが使える秒数（既定 3600、60〜86400）。 |

## GitHub がログインを失効させたとき

各アカウントは独立したプロセスなので、使えなくなったログインはそのアカウントだけに影響します。ログイン自体が使えないという拒否（401、`Bad credentials`、期限切れまたは失効したトークン、停止されたアカウント、ログインなし）が 2 回続くと、アカウントは**ブラインド**になります。ページ、詳細ヘルスチェック、`GET /api/accounts`（`state: blind`）、`monitor_cli.py` がそれを示し、アラートタブに**重大なシステムアラート**（`system.credential_blind`、センチネル `system`）が開き、通知の種類 `credential_blind`（既定で有効）と `credential_back` がチャンネルに一度だけ知らせます。1 つの権限の拒否（1 つのリポジトリへの 403）ではアカウントはブラインドになりません。他のアカウントは動き続け、詳細ヘルスチェックは正常のままです。アカウントは試行を続け、最初に成功したサイクルでアラートが閉じます。

すでに使えないログインで起動したサービスは、諦めずにブラインドのまま動き続けるので、置き換える対象があります。アカウントのトークンは、最初に見つかったものが優先されます: そのフォルダーのファイル `credential`（置き換えで書かれる）、`GH_TOKEN_FILE` が指すファイル、そして `gh` が使うもの（`GH_TOKEN` または自身のログイン）。置き換えにはスーパーバイザーやアカウントの再起動は不要で、方法は 3 つです:

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

新しいトークンは、保持される前に GitHub で確認されます（`rate_limit` の呼び出し、無料）。GitHub が拒否するトークンは何も変更せず 422（`rejected`）を返します。有効なトークンはそのアカウントのフォルダーだけに書かれ（モード 600）、すぐに使われ、アカウントは待たずに読み直します。チームモードでは、このエンドポイントは `admin` セッション（Cookie セッションの CSRF トークン付き）用で、監査には誰が行ったかが記録され、トークンは記録されません。チームモードなしでネットワークモードが有効な場合は、モニターのコンピューターだけが行えます。トークンが応答、ログ、アラート、ページに現れることはありません。

## 最初の起動、バックアップ、アップグレード

サービスとしての最初の起動: 所有者とログイン（`GH_TOKEN_FILE`）を設定して起動し、アクセストークンを一度読み（`/data/state/access_token`）、ページを開いて `monitor_cli.py health --deep` を実行します。`MONITOR_SERVICE=1` での `python actions_monitor.py --doctor` は、保持設定のブロックがないことや、同じトークンを共有するアカウントについても警告します。

バックアップ: 保持すべきものはすべて 2 つのボリュームにあります。アップグレード前にストレージの整合したコピーと、ボリュームのコピーを取ってください:

```sh
docker compose exec monitor python /app/tools/backup_storage.py backup /data/state/backup.zip --backend file
docker cp github-actions-monitor:/data/state/backup.zip .
docker run --rm -v monitor-data:/data -v "$PWD":/backup alpine tar czf /backup/monitor-data.tgz -C /data .
```

アップグレード: データはボリュームにあるので残ります。本番ではバージョンを固定し（`:1.8.2`）、pull して再作成し、イメージの attestation を確認します。古いモニターが新しいストレージを開くことはない（`STORAGE.md` を参照）ので、新しいバージョンが動くまでバックアップを残してください。

```sh
docker compose pull && docker compose up -d
gh attestation verify oci://ghcr.io/juanenrac/tools-github-actions-monitor:1.8.2 --owner JuanenRac
```

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

## 別のコンピューターに対するコマンドライン

`monitor_cli.py` は別のマシンのモニターに対しても動きます: `--url https://monitor.example.org`（または `MONITOR_URL`）、アクセストークンは `MONITOR_ACCESS_TOKEN` または `--token-file`、独自の HTTPS 証明書に署名した認証局を信頼するための `--ca-file`（または `MONITOR_CA_FILE`）、そしてチームモードでは `--user 名前` と `--password-file ファイル`（または `MONITOR_USER`、`MONITOR_PASSWORD_FILE`）で Bearer セッションによりサインインします（`auth.allow_bearer`）。`status`、`accounts`、`alerts`、`health`（`--deep`）、`credential` も同様に動作し、終了コードも同じです（3 = 拒否。`status` と `accounts` ではブラインドのアカウントも 3）。別のコンピューターへの平文 HTTP は警告を表示します。

## ログインに必要な最小限の権限(`gh` または細粒度トークン)

- 実行リスト・ジョブ・issue:Actions(読み取り)、Issues(読み取り)、Metadata(読み取り)。アラート:Code scanning、Dependabot、Secret scanning のアラート(読み取り)。プルリクエストとリリース:Pull requests(読み取り)、Contents(読み取り)。パッケージ:`read:packages`。
- 書き込むのは任意の AI アクションだけです。ワークフローの再実行には Actions(書き込み)、issue のクローズには Issues(書き込み)が必要です。これらはオフのままにして、ログインには読み取りだけを与えてください。

## 多数のリポジトリ

条件付き読み取り(`cache.etag`)により、変更のないリポジトリは割り当てを消費しません。`mode: lite`、`ecosystems`、`exclude`、`max_workers` で作業量を制限でき、受信 Webhook はイベントを送るリポジトリの定期取得を不要にします。`discover_limit` はアカウントごとに一覧するリポジトリの最大数です(既定 1000)。

## 何か月も動かす場合:保存と保持

`accounts/`(またはデータベース)はコンテナがなくなっても残るボリュームに置き、更新の前に `python tools/backup_storage.py backup FILE.zip --backend file`(または `sqlite`)でバックアップを取ってください。初期状態では、短い処理が90日より古いイベントと180日より古い分析を削除します。変更するには設定の `retention` を使い、`MONITOR_SERVICE=1` を付けると `--doctor` がモニターをサービスとして扱います(その場合、`retention` ブロックがない、またはイベントが大きくなっていると警告します)。SQLiteでは1アカウント1データベースが既定で、共有ファイル1つも可能です([STORAGE_jpn.md](STORAGE_jpn.md) を参照)。
