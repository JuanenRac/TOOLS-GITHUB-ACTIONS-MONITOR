<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->


[🇺🇸 English](DEPLOYMENT.md) | [🇪🇸 Español](DEPLOYMENT_spa.md) | [🇫🇷 Français](DEPLOYMENT_fra.md) | [🇮🇹 Italiano](DEPLOYMENT_ita.md) | [🇩🇪 Deutsch](DEPLOYMENT_deu.md) | [🇨🇳 简体中文](DEPLOYMENT_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](DEPLOYMENT_por.md)

# サービスとして動かす

モニターは、既定では `127.0.0.1` だけで待ち受け、ログインを持たないプログラムです。このドキュメントは、サービスとして動かす方法を説明します。公式イメージ、リバースプロキシ付きの Docker Compose、systemd による従来のインストール、そして GitHub がログインを失効させたときの動作です。

## どこで待ち受けるか

モニターは 3 通りのどれかで待ち受け、ページ、`GET /api/accounts`、`bin/monitor_cli.py status`、`bin/monitor_cli.py accounts` がそのどれかを示します。**このコンピューター**（`127.0.0.1` のみ。既定でログインなし）、**ネットワーク**（ネットワークモード `listen.network`: `listen.host` でも待ち受け、すべてのリクエストがアクセストークンを持つ）、または**プロキシの背後**（手前にリバースプロキシを宣言したネットワークモード: `listen.proxy_public_host`、`listen.secure_cookie`、`listen.trusted_proxy`）。イメージとサービスユニットは 2 番目と 3 番目のために作られており、手で起動したモニターは 1 番目のままです。

ネットワークモードでは、複数アカウントのスーパーバイザーも 1 アカウントのモニターと同じルールに従います。すべてのリクエストでアクセストークン（Cookie、ヘッダー、または `POST /api/access`）、誤ったトークンの後のロックアウト、`Host` の検査、お使いの証明書による任意の TLS、コンピューターの前にいる人用の 2 つ目のポート（`listen.local_port`）、そして公開範囲を決めるキー、GitHub のログイン、GitHub への操作はモニターのコンピューターからのみ（ネットワークからのリクエストはリモートと印を付けてアカウントに届きます）。

## 2つのエディションのポート

設定ファイルに別の値がなければ、Complete エディションはポート 8765、Lite エディションは 8766 で待ち受けます。設定項目は `ports.complete` と `ports.lite`(1024〜65535 の整数、再起動が必要。設定ページの「ポート」ブロックにもあります)。2つの番号は1か所で読まれるため、起動、「このポートには既にモニターがあります」の確認、`--doctor`、ヘルスチェック(`python -m github_actions_monitor.cli.healthcheck`)、コマンドライン(`--lite` は Lite のポートに接続)、ターミナル表示、ランチャーがすべて一致します。優先順位は、コマンドラインの `--port N`、次に `MONITOR_PORT`(サービスとコンテナが設定。Complete のみ)、そのエディションのファイル、もう一方のエディションのファイル(1つのメニューで両方を設定可能)、最後に既定値です。Lite は Complete のポートを使いません。両方が同じ番号なら Lite は 8766 のままで、設定ページは両方に同じ番号を保存することを拒否します。ポートが使用中なら、モニターは次の空きポート(最大10上まで)を使います。

## ブラウザーなしで、そしてヘルスチェック

`python -m github_actions_monitor.service` はサービスの入口です。環境変数からフォルダーと最初のアカウントを用意し（下の表を参照）、ブラウザーなしでモニターを起動します。自分で管理するモニターには、引き続き `python bin/actions_monitor.py --no-browser --port 8765` が使えます。

`GET /api/health` は `{"ok": true, "version": ..., "loaded": ..., "offline": ...}` に加えて、更新サイクルとアカウントの GitHub ログインの状態を返します。GitHub は呼び出しません。`GET /api/health?deep=1` は詳細チェックで、アカウントの更新サイクルが `watchdog_minutes`（0 なら 30 分）より長く動いている、またはそのスレッドが消えている場合に 503 を返します。複数アカウントのスーパーバイザーでは、監視ループ自体が止まった場合、いずれかのアカウントのサイクルが固まった場合、起動後にどのアカウントも応答しない場合にも 503 です。GitHub ログインが使えないアカウント（ブラインド）は応答に名前が出ますが、障害ではありません。再起動では失ったログインは直らず、新しいログインが必要です。

`python -m github_actions_monitor.cli.healthcheck` は、コンテナーやサービスマネージャー向けにその呼び出しを行います（終了コード 0 正常、1 異常、2 応答なし、3 拒否）。アクセストークンは `MONITOR_ACCESS_TOKEN`、`MONITOR_ACCESS_TOKEN_FILE` が指すファイル、またはサービスが `MONITOR_STATE_DIR` に保持するファイルから読みます。`bin/monitor_cli.py health --deep` はどのコンピューターからでも同じことを行います。

## 公式イメージ

`ghcr.io/juanenrac/tools-github-actions-monitor`（`linux/amd64` と `linux/arm64`）。タグは `2.1.0`、`2.1`、`latest` で、リリースのワークフローが出所の証明（attestation）付きでビルドします。3 段階で作られ（`deploy/Dockerfile`）、Python、GitHub CLI、CA 証明書、コードだけを含み、読み取り専用で root の所有です。ユーザー 10001（root ではない）で動き、書き込むのは 2 つのボリュームだけです: `/config`（`actions_monitor.json`。最初の起動で作られ、上書きされません）と `/data`（`accounts/`、アクセストークンを含む `state/`、`secrets/`、`gh` のログイン）。ネットワークモードでコンテナーのポート 8765 を待ち受けるので、すべてのリクエストにアクセストークンが必要で、ポートは自分では公開しません。

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

最初の起動では、設定、最初のアカウント（`MONITOR_GITHUB_OWNER` から。複数は `MONITOR_ACCOUNTS=personal:me,work:my-org`）、そして `MONITOR_ACCESS_TOKEN` がなければアクセストークンを作り、`/data/state/access_token`（モード 600）に保存して表示しません。トークンをアドレスに入れずにセッションを開きます。`POST /api/access` に `{"token": "..."}` を送るか(Cookie は応答で返ります)、ヘッダー `X-Monitor-Access` を送ってください。ブラウザーのアドレスバーから一度だけ開くには、`MONITOR_QUERY_ACCESS=1` でコンテナーを起動し、`http://127.0.0.1:8765/?access=TOKEN` を開いてから、その変数を再びオフにします。名前付きボリュームの代わりにバインドマウントを使う場合は、フォルダーをユーザー 10001 に渡してください（`chown -R 10001:10001`）。Lite エディションはイメージに含まれません。

## Docker Compose（任意のプロキシと TLS 付き）

`deploy/compose.yaml` は、コードを読み取り専用、ケーパビリティなし、ログインを Docker シークレット、2 つのボリュームでモニターを動かします。プロファイル `proxy` は手前に Caddy（`deploy/Caddyfile`）を加え、公開名の証明書を自動で取得・更新します（自分のネットワークの名前なら `tls internal`、TLS なしなら `http://name`）。`deploy/.env.example` を `deploy/.env` にコピーして記入し、起動します:

```sh
cp deploy/.env.example deploy/.env                                   # fill in MONITOR_GITHUB_OWNER
printf '%s' "ghp_..." > deploy/gh_token.txt && sudo chown 10001:10001 deploy/gh_token.txt && chmod 600 deploy/gh_token.txt
docker compose -f deploy/compose.yaml up -d                          # on 127.0.0.1:8765
docker compose -f deploy/compose.yaml --profile proxy up -d          # behind Caddy (deploy/Caddyfile)
```

プロキシの背後では、モニターは自分の公開名とセッションが HTTPS であることを知る必要があります: `MONITOR_PROXY_PUBLIC_HOST` と `MONITOR_SECURE_COOKIE=1`。すると、メインポートに届くものはモニターのコンピューターとは見なされません。2 つ目のポート（`MONITOR_LOCAL_PORT`、イメージでは 8766、ループバックのみ）を `docker compose exec monitor python bin/monitor_cli.py ...` で使います（イメージは `MONITOR_URL` をそこに向けています）。

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

launchd（macOS）: `ProgramArguments` = `/usr/bin/python3`、`-m`、`github_actions_monitor.service`、変数は `EnvironmentVariables`、`KeepAlive` と `RunAtLoad` は true。Windows: `schtasks /Create /SC ONLOGON /TN GhaMonitor /TR "py -3 C:/path/to/bin/actions_monitor.py --no-browser"`。

## 環境変数

この表の名前だけが読み込まれます。サービスでは、読み取れない値は通知とともに無視され、何も変更しません。設定の一部を指す変数（`MONITOR_LISTEN_*`、`MONITOR_ALLOWED_HOSTS`、`MONITOR_PROXY_PUBLIC_HOST`、`MONITOR_SECURE_COOKIE`、`MONITOR_TRUSTED_PROXY`、`MONITOR_LOCAL_PORT`、`MONITOR_TLS_*`、`MONITOR_QUERY_ACCESS`、`MONITOR_TEAM_MODE`）は、サービスの起動のたびに `listen` と `auth` に書き込まれ、これらについては環境変数が優先されます。ファイルのそれ以外はあなたのものです。 プロキシの変数が設定されているのに空のままの場合 (`MONITOR_TRUSTED_PROXY`, `MONITOR_TRUSTED_PROXIES`, `MONITOR_SECURE_COOKIE`, `MONITOR_PROXY_PUBLIC_HOST`, `MONITOR_ALLOWED_HOSTS`)、起動時にそのキーはオフになります。そのため `.env` ファイルの空の行が古いプロキシ宣言を生かし続けることはありません。まったく設定されていない変数は何も変えません。

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
| `MONITOR_CONFIG_DIR` | フォルダー `config/`: 設定ファイル（`targets.json`、`quotas.json` など）と `config_backups/`（イメージでは `/config`）。 |
| `MONITOR_DATA_DIR` | フォルダー `data/`: 状態、キャッシュ、アカウント。`MONITOR_LOGS_DIR` / `MONITOR_AI_DIR` で別に指定しない限り `logs/` と `ai/` はその中に置かれます（イメージでは `/data`）。LAYOUT を参照。 |
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
| `MONITOR_TRUSTED_PROXIES` | プロキシがこのマシンにないときのそのアドレスまたはネットワーク（カンマ区切り、`listen.trusted_proxies`）。`MONITOR_TRUSTED_PROXY` と併用します。Compose ファイルは Caddy に固定アドレス `MONITOR_PROXY_IP`(既定 172.29.77.250、`MONITOR_SUBNET` の内側)を割り当てます。このアドレスだけを指定してください。 |
| `MONITOR_LOCAL_PORT` | プロキシ宣言時にコンピューターの前にいる人のための、ループバック専用の 2 つ目のポート（`listen.local_port`。イメージでは 8766）。 |
| `MONITOR_TLS_CERT_FILE` | HTTPS を直接提供するための証明書（PEM、`listen.tls_cert_file`）。鍵とともに指定します。使えない場合、モニターは平文 HTTP では起動しません。 |
| `MONITOR_TLS_KEY_FILE` | その証明書の秘密鍵（`listen.tls_key_file`）。 |
| `MONITOR_QUERY_ACCESS` | `1` = `?access=` 付きのアドレスでセッションを開けるようにします（`listen.query_access`、既定はオフ）。安全なのは `POST /api/access` です。 |
| `MONITOR_TEAM_MODE` | `1` = チームモード（`auth.enabled`）: ユーザー、ロール、セッション。 |
| `MONITOR_ADMIN_USER` | `MONITOR_ADMIN_PASSWORD_FILE` と併用: チームモードがオンでユーザーがまだいないときにサービスが作成する最初の管理者。 |
| `MONITOR_ADMIN_PASSWORD_FILE` | `MONITOR_ADMIN_USER` のパスワードを 1 行目に書いたファイル(たとえば Docker シークレット)。 |
| `MONITOR_SERVICE` | `1` = サービスとして動作: 使えないログインでも諦めず、doctor が保持設定を確認します。イメージとサービスが設定します。 |
| `MONITOR_URL` | `bin/monitor_cli.py` とヘルスチェック用: モニターのアドレス（イメージでは 2 つ目のポート）。 |
| `MONITOR_CA_FILE` | `bin/monitor_cli.py` 用: モニターの HTTPS 証明書に署名した認証局の PEM ファイル。 |
| `MONITOR_USER` | チームモードの `bin/monitor_cli.py` 用: サインインするユーザー。 |
| `MONITOR_PASSWORD_FILE` | `bin/monitor_cli.py` 用: 1 行目に `MONITOR_USER` のパスワードを書いたファイル。 |
| `MONITOR_RELEASE_TEST_TIMEOUT` | `tools/make_release.py`: ゲートが失敗するまでに通常のスイートが使える秒数（既定 3600、60〜86400）。 |
| `MONITOR_RELEASE_CLEAN_TIMEOUT` | `tools/make_release.py`: 展開した zip のスイートが使える秒数（既定 3600、60〜86400）。 |
| `MONITOR_RELEASE_LOG_DIR` | `tools/make_release.py`: 失敗したスイートの出力全体を保存するフォルダー（既定は一時フォルダー）。ゲートのメッセージは失敗したテストとこのファイルを示します。 |
| `--accept-green-suite JSON --commit SHA [--skip-clean-suite]` | `tools/make_release.py`: 通常のスイートを再実行する代わりに、まさにそのコミットの完全な成功実行の記録（完了、失敗・エラーなし、全テスト実行）を受け入れます。`--skip-clean-suite` は展開した zip のスイートも省略します（簡易チェックは実行）。その旨が表示されます。 |
| `--progress` | `tools/make_release.py`: スイートの進み具合を 250 テストごとに 1 行で表示します(クリーンインストールのスイートも同様です)。 |

## 外部ハートビート(既定ではオフ)

モニターは、電源を切られたり、スリープしたり、再起動したりするコンピューターで動き、そのとき誰も見ていないことを誰も知りません。`heartbeat.enabled` をオンにすると、モニターは `heartbeat.interval_seconds`(既定 300)ごとにアドレスへ ping を送り、healthchecks.io、Cronitor、Uptime Kuma のようなサービスが ping の途絶を知らせます。

- アドレスは秘密です。`heartbeat.url_env` が指す環境変数(既定は `MONITOR_HEARTBEAT_URL`)に入れてください。設定に書かれたり、表示やログに出たりすることはなく、設定画面は定義されているかどうかだけを示します。`https` である必要があり(`http` は自分のネットワーク内のサービス向けに `notify.allow_private_targets` がある場合のみ)、ユーザー名やパスワードを含めてはならず、通知と同じ保護付きで開かれます。
- ping に含まれるのは多くても `msg=<バージョン> <ok|degraded>`(`heartbeat.send_state`)で、リポジトリ、アラート、名前は含まれません。
- モニターが応答できない(更新ループが止まっている、または消えている)ときは ping を送らず、沈黙が警報になります。失敗用アドレスを持つサービス(healthchecks.io の `/fail`)には `heartbeat.fail_suffix` を指定でき、その場合はすぐに通知されます。
- 完全版では `GET /api/health` に `heartbeat`(送信、失敗、スキップ、直近の結果)が表示されます。

## GitHub がログインを失効させたとき

各アカウントは独立したプロセスなので、使えなくなったログインはそのアカウントだけに影響します。ログイン自体が使えないという拒否（401、`Bad credentials`、期限切れまたは失効したトークン、停止されたアカウント、ログインなし）が 2 回続くと、アカウントは**ブラインド**になります。ページ、詳細ヘルスチェック、`GET /api/accounts`（`state: blind`）、`bin/monitor_cli.py` がそれを示し、アラートタブに**重大なシステムアラート**（`system.credential_blind`、センチネル `system`）が開き、通知の種類 `credential_blind`（既定で有効）と `credential_back` がチャンネルに一度だけ知らせます。1 つの権限の拒否（1 つのリポジトリへの 403）ではアカウントはブラインドになりません。他のアカウントは動き続け、詳細ヘルスチェックは正常のままです。アカウントは試行を続け、最初に成功したサイクルでアラートが閉じます。

すでに使えないログインで起動したサービスは、諦めずにブラインドのまま動き続けるので、置き換える対象があります。アカウントのトークンは、最初に見つかったものが優先されます: そのフォルダーのファイル `credential`（置き換えで書かれる）、`GH_TOKEN_FILE` が指すファイル、そして `gh` が使うもの（`GH_TOKEN` または自身のログイン）。置き換えにはスーパーバイザーやアカウントの再起動は不要で、方法は 3 つです:

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

新しいトークンは、保持される前に GitHub で確認されます（`rate_limit` の呼び出し、無料）。GitHub が拒否するトークンは何も変更せず 422（`rejected`）を返します。有効なトークンはそのアカウントのフォルダーだけに書かれ（モード 600）、すぐに使われ、アカウントは待たずに読み直します。チームモードでは、このエンドポイントは `admin` セッション（Cookie セッションの CSRF トークン付き）用で、監査には誰が行ったかが記録され、トークンは記録されません。チームモードなしでネットワークモードが有効な場合は、モニターのコンピューターだけが行えます。トークンが応答、ログ、アラート、ページに現れることはありません。

## コンテナでの最初の管理者

`MONITOR_TEAM_MODE=1` ではイメージはネットワークで待ち受け、最初の管理者(モニターのあるコンピューターからしか作成できません)が存在するまでモニターはネットワークを開きません。コンテナ内では `/login` で作成できず、ネットワークモードも切れない(イメージが起動のたびに設定します)ため、サービスは最初の起動で終了コード 1 で止まります。サービスを起動する前に、同じボリュームで最初の管理者を一度作成してください(パスワードはコンソールで尋ねられ、コマンドラインには書きません):

```sh
docker compose run --rm --entrypoint python monitor -m github_actions_monitor.security.auth_cli create-admin NAME
docker compose up -d
```

または、サービスに作成させることもできます。`MONITOR_ADMIN_USER` と `MONITOR_ADMIN_PASSWORD_FILE`(たとえば Docker シークレットなど、1 行目にパスワードを書いたファイル)を設定すると、チームモードがオンでユーザーがまだいないとき、最初の起動でその管理者が作成されます。パスワードは表示されません。

## 最初の起動、バックアップ、アップグレード

サービスとしての最初の起動: 所有者とログイン（`GH_TOKEN_FILE`）を設定して起動し、アクセストークンを一度読み（`/data/state/access_token`）、ページを開いて `bin/monitor_cli.py health --deep` を実行します。`MONITOR_SERVICE=1` での `python bin/actions_monitor.py --doctor` は、保持設定のブロックがないことや、同じトークンを共有するアカウントについても警告します。

バックアップ: 保持すべきものはすべて 2 つのボリュームにあります。アップグレード前にストレージの整合したコピーと、ボリュームのコピーを取ってください:

```sh
docker compose exec monitor python /app/tools/backup_storage.py backup /data/state/backup.zip --backend file
docker cp github-actions-monitor:/data/state/backup.zip .
docker run --rm -v monitor-data:/data -v "$PWD":/backup alpine tar czf /backup/monitor-data.tgz -C /data .
```

アップグレード: データはボリュームにあるので残ります。本番ではバージョンを固定し（`:2.1.0`）、pull して再作成し、イメージの attestation を確認します。古いモニターが新しいストレージを開くことはない（`STORAGE.md` を参照）ので、新しいバージョンが動くまでバックアップを残してください。

```sh
docker compose pull && docker compose up -d
gh attestation verify oci://ghcr.io/juanenrac/tools-github-actions-monitor:2.1.0 --owner JuanenRac
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

`listen.trusted_proxy` は、プロキシがモニターと「同じ」コンピューター上で動いていることを前提とします(モニターはループバックで届くあらゆる接続の `X-Forwarded-For` を信じます)。別のマシン上のプロキシでは使わないでください。利用できる `X-Forwarded-For` のないリクエストの誤ったトークンは合計でも数えられます(1つのアドレスの上限の3倍)。この共通のロックが、正しいトークンを持つリクエストを止めることはありません。 プロキシが別のコンテナや別のマシンにある場合は、そのアドレスまたはネットワークを `listen.trusted_proxies`（`MONITOR_TRUSTED_PROXIES`。Docker Compose ファイルでは Caddy の固定アドレス `MONITOR_PROXY_IP`。ネットワーク `MONITOR_SUBNET` 全体ではありません。Caddy を迂回するコンテナも信用されてしまうためです）に列挙してください。それらのアドレスまたはこのコンピューターからの接続では、試行回数の集計に `X-Forwarded-For` が信用されます。リクエストがこのコンピューターとして扱われることはありません。

## 別のコンピューターに対するコマンドライン

`bin/monitor_cli.py` は別のマシンのモニターに対しても動きます: `--url https://monitor.example.org`（または `MONITOR_URL`）、アクセストークンは `MONITOR_ACCESS_TOKEN` または `--token-file`、独自の HTTPS 証明書に署名した認証局を信頼するための `--ca-file`（または `MONITOR_CA_FILE`）、そしてチームモードでは `--user 名前` と `--password-file ファイル`（または `MONITOR_USER`、`MONITOR_PASSWORD_FILE`）で Bearer セッションによりサインインします（`auth.allow_bearer`）。`status`、`accounts`、`alerts`、`health`（`--deep`）、`credential` も同様に動作し、終了コードも同じです（3 = 拒否。`status` と `accounts` ではブラインドのアカウントも 3）。別のコンピューターへの平文 HTTP は警告を表示します。

## ログインに必要な最小限の権限(`gh` または細粒度トークン)

- 実行リスト・ジョブ・issue:Actions(読み取り)、Issues(読み取り)、Metadata(読み取り)。アラート:Code scanning、Dependabot、Secret scanning のアラート(読み取り)。プルリクエストとリリース:Pull requests(読み取り)、Contents(読み取り)。パッケージ:`read:packages`。
- 書き込むのは任意の AI アクションだけです。ワークフローの再実行には Actions(書き込み)、issue のクローズには Issues(書き込み)が必要です。これらはオフのままにして、ログインには読み取りだけを与えてください。

## 多数のリポジトリ

条件付き読み取り(`cache.etag`)により、変更のないリポジトリは割り当てを消費しません。`mode: lite`、`ecosystems`、`exclude`、`max_workers` で作業量を制限でき、受信 Webhook はイベントを送るリポジトリの定期取得を不要にします。`discover_limit` はアカウントごとに一覧するリポジトリの最大数です(既定 1000)。

## 何か月も動かす場合:保存と保持

`accounts/`(またはデータベース)はコンテナがなくなっても残るボリュームに置き、更新の前に `python tools/backup_storage.py backup FILE.zip --backend file`(または `sqlite`)でバックアップを取ってください。初期状態では、短い処理が90日より古いイベントと180日より古い分析を削除します。変更するには設定の `retention` を使い、`MONITOR_SERVICE=1` を付けると `--doctor` がモニターをサービスとして扱います(その場合、`retention` ブロックがない、またはイベントが大きくなっていると警告します)。SQLiteでは1アカウント1データベースが既定で、共有ファイル1つも可能です([STORAGE_jpn.md](STORAGE_jpn.md) を参照)。

## バックアップ、ボリューム、アップグレード

サービスでは、`deploy/github-actions-monitor-backup.service` と `deploy/github-actions-monitor-backup.timer` が毎日完全バックアップ (`monitor_cli.py backup create`) を作成し、`deploy/compose.yaml` は専用のボリューム (`monitor-backups`) にバックアップを保存します。アップグレードの前にバックアップを作って検証し、後に doctor を実行してください。手順、復元、doctor の終了コードは [OPS_jpn.md](OPS_jpn.md) にあります。

## 実際のコンテナーでイメージを検証する

リポジトリにはワークフロー `docker-audit.yml` があり、GitHub 上で任意のバージョン（タグまたはコミット）のイメージをビルドし、実際のコンテナーで検証します。対象は、起動とヘルスチェック、API の契約、最初の管理者を含むチームモード、独自の TLS を持つ Caddy を信頼済みプロキシとした構成、堅牢化（root なし、読み取り専用ファイルシステム、ケイパビリティなし）、バックアップ・リストア・前バージョンからの移行を含むボリューム、シークレット、シャットダウン、プロキシの背後にある受信 Webhook です。お使いのコンピューターでは何も実行せず、何も公開せず、シークレットも使いません。手動で起動し、実行のサマリーの表とアーティファクト `docker-audit-<バージョン>` を読みます。

```sh
gh workflow run docker-audit.yml -f ref=<tag>
```

同じスクリプトは Docker のある Linux マシンでも実行できます（`tools/docker_audit/run_all.sh`）。各結果の読み方は `tools/docker_audit/LEEME.txt` に説明があります。

## スマートフォンでモニターを使う

このセクションの機能は、すべて既定ではオフか、害のないものです。

- **インストール可能なアプリ**(`pwa.enabled`): ページはマニフェスト、2つのアイコン、小さなサービスワーカーを提供し、ブラウザーがモニターをアプリとしてインストールできます。ファイルは `/manifest.webmanifest`、`/sw.js`、`/pwa/offline`、`/pwa/icon-192.png`、`/pwa/icon-512.png` で、ネットワークモードでは他のページと同様にアクセストークンの内側で配信されます。ワーカーが保持するのはオフラインページとアイコンだけで、ページもAPIの応答も保持しません。アプリが前面に戻ったりネットワークが復旧したりすると、ページはすぐに最新データを要求します(`pwa.refresh_on_return`)。
- **コンパクト表示**(`ui.compact`): `auto` は狭いウィンドウで、`on` は常に、`off` は使いません。`?compact=1` または `?compact=0` で1つのウィンドウだけ変更できます。メニューはタブの行として上に移り、表は横にスクロールし、タッチ画面では44ピクセル以上の操作領域になり、ダイアログは画面キーボードが残す高さに従います。
- **QRコードでのペアリング**(`pairing.enabled`、ネットワークモードのみ): パレット(Ctrl+K)を開いて「スマートフォンをペアリング」、続いて「新しいQRコード」を選びます。コードは1回だけ、`pairing.code_minutes` 分間有効で、新しいコードを作ると前のコードは無効になります。スマートフォンで読み取り、開いたページのボタンを押すと、アクセストークンではなく専用のトークン(クッキー)を受け取ります。同じウィンドウにペアリング済みデバイスが並び、1台を取り消すとそのトークンはすぐに使えなくなります。デバイスは最大 `pairing.max_devices` 台で、`pairing.device_days` 日後に再ペアリングが必要です(0 = 無期限)。モニターはデータフォルダーの `devices.json` に各トークンのハッシュだけを保存し、誤ったコードは誤ったアクセストークンと同様にアドレスに対して数えられ、ペアリングも取り消しも操作ログに1行残ります。

| ルート | 内容 |
|---|---|
| `GET /api/devices` | ペアリング済みデバイスと、ペアリングが有効かどうか(このコンピューターのみ) |
| `POST /api/pair/start` | 1回限りのコードを開き、そのアドレスとQRコードを返します(このコンピューターのみ、ページの1回限りトークン付き) |
| `POST /api/pair/redeem` | スマートフォンがコード(`{"code": "..."}`)を使い、クッキーを受け取ります |
| `POST /api/devices/revoke` | デバイスを取り消します(`{"id": "..."}`、このコンピューターのみ) |

- **パレットとショートカット**(`ui.palette`): Ctrl+K でタブ、リポジトリ、操作の検索ボックスを開きます。`?` でショートカット一覧、`/` でタブの検索ボックス、`r` で更新、`[` `]` でタブ切り替え。
