<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# 変更履歴

ツール自体(モニター + センチネル + バッチツール)のバージョンで、独自のセマンティックバージョニングです。元は英語の CHANGELOG.md で、このファイルは同じバージョンと節を持ちます。

## [1.7.0]

フル版で複数のアカウントを扱えるようになりました。各アカウントは独立したモニターで、ページはそれらを認識します。lite 版は変わりません。アカウントは 1 つで、新しいオプションも表示されません。

### 追加

- **複数のアカウント**（フル版のみ）。アカウント（個人または組織）ごとに、専用の `actions_monitor.json`、キャッシュ、イベント、分析、センチネルの状態、ログを持つフォルダー `accounts/<id>/` を用意します。`accounts/global.json` は任意（`default_account`、`enabled_accounts`）で、`MONITOR_ACCOUNTS_DIR` でフォルダーを移せます。ID は英小文字、数字、`_`、`-`（最大 40 文字）なので、常に安全なフォルダー名になります。`accounts/` フォルダーがなければ何も変わりません。アカウントは 1 つで、ファイルはコードの隣にあります。
- **スーパーバイザー**（`accounts_supervisor.py`）: `accounts/` フォルダーがあるとき、`python actions_monitor.py` はいつものポートで小さなプロセスを起動し、アカウントごとに 1 つのモニター（`account_child.py`）を、それぞれ `127.0.0.1` の専用ポートで実行します。1 つのアカウントのクラッシュ、応答の遅れ、レート制限が他に影響することはありません。停止したアカウントは待ち時間を延ばしながら（2、5、15、30、60、その後 120 秒）再起動し、その間は概要で停止中と表示します。GitHub からは何も読まず、何も書きません。停止すると、Windows でも、起動したすべてのプロセスを終了します。
- **アカウントの API**: `GET /api/accounts`（概要）、`GET /api/accounts/<id>/status`、そして `/api/` 以下のそれ以外のリクエストは、`?account=<id>` またはヘッダー `X-Account-Id` で指定したアカウントに送られます（指定がなければ既定のアカウント。不明なアカウントは 404）。アクセスのルールは単独のモニターと同じで、変更のワンタイムトークンは、その変更を送るのと同じアカウントに対して取得します。
- **すべてに 1 つの Webhook**: `POST /api/webhook` はインストール全体で単一のアドレスです。スーパーバイザーは `repository.full_name` のオーナーだけを読み、その `github_owner` がそのオーナーであるアカウントにイベントをそのまま渡します。アカウントは自分のシークレットで署名を検証します。誰も監視していないオーナーには応答して無視します。
- **`--accounts`、`--account <id>`、`--migrate-accounts [--apply]`**: アカウントを一覧表示し、1 つだけを通常のモニターとして実行し、旧レイアウトを `accounts/default/` に移します。移行は `--apply` がなければ試験実行で、元のファイルを移動も削除もせず、2 回目の実行は拒否し、lite 版のファイルには触れません。
- **複数アカウントのページ**: ヘッダーの下にアカウントの切り替えと、アカウントごとに 1 枚のカード（状態、リポジトリ、実行中、失敗中）を表示する **すべてのアカウント** という項目。各ウィンドウは自分のアカウントとビューを保持し、アドレスから読み取ります。
- **アドレスによるビュー**（`?view=now|alerts|charts|repos|settings|live` と `?chrome=0`。壁面や 2 台目のモニター向けの、ヘッダーのボタン、タブ、フィルターのない画面）。**ライブ** ビューには、GitHub が最後に送ったイベント、Webhook 受信の状態（シークレットは決して表示されません）、作業モードの選択が表示されます。`GET /api/live-status` がその取得元です。
- 画像用の `tools/demo_accounts.py`、8 言語のガイド `ACCOUNTS.md`、そしてすべての変更に対するテスト（テストは 866 件から 914 件に増えました）。

### 変更

- 複数のうちの 1 つのアカウントであるモニターの状態ファイルは、`state_dir()` を通じてそのフォルダーに置かれます。単独のモニターは、これまでどおりコードの隣に置きます。
- README の画像を撮り直し、8 言語の README にアカウントを載せました。

### セキュリティ

- スーパーバイザーとアカウントは、ネットワークモードがオンでない限り `127.0.0.1` でのみ待ち受けます。Webhook にはホストの検査もアクセストークンもなく（トンネルがホストを変えるため）、その証明は引き続き GitHub の HMAC です。セッションのクッキーがアカウントに渡されることはありません。

### 修正

- 1.6.8 のライブビューには受信側の状態がありませんでした。Webhook がオフのときや 32 文字未満のシークレットのときは何も表示されませんでしたが、今はどちらなのかが表示されます。

## [1.6.8]

1.6.7 の HTTPS プロキシを実際のプロキシで検証するようにし、画像を撮り直し、変更履歴を 1.6.3 まで翻訳しました。

### 追加

- `python tools/manual_check_live.py proxy ホスト [ポート] [接続先]`: 実際の HTTPS プロキシ(ポート 443)を通して、ページが受け入れられること(本文のアクセストークンでセッションが開き、クッキーが `Secure` と `HttpOnly` で返る)と、3 つのリクエストが拒否されたままであること(別のスキーム、別のホスト名、ポート付きの名前)を確認します。アクセストークンは `MONITOR_ACCESS_TOKEN` から読み取り、決して表示せず、引数なしで実行すると nginx や Caddy に何を設定するかを示します。
- `tools/demo_monitor.py --network` は、ネットワークモードでのページの見え方(常時表示の赤いバー、設定では全インターフェースの警告と新しいプロキシ名)を撮影できるように表示します。デモは引き続き `127.0.0.1` だけで待ち受けます。`tools/make_screenshots.py` はこれで新しい画像を 2 枚(`web_network_now` と `web_network_settings`)撮影します。
- 連鎖全体を通すテスト: 本物の TLS 上のクライアント、TLS を終端して `Host` と `Origin` をポートなしで転送するリバースプロキシ、その背後の本物のモニター。ページからの変更が設定に届くこと、`listen.proxy_public_host` がなければ同じリクエストが拒否されること、誤ったスキーム・名前・ポートが拒否されたままであること、セッションが開きクッキーが `Secure` であること、手動チェックがプロキシと一致しトークンを決して表示しないことを確認します(テストは 858 件から 866 件に増えました)。

### 変更

- 変更履歴(ヘルプ > 変更履歴)は、1.6.8 から 1.6.3 まで他の 7 言語に翻訳されました(1.6.7 と 1.6.5 は翻訳済み)。1.6.3 より前の項目は、翻訳済みの注記の下に英語のまま残ります。
- README の画像を撮り直しました(計 76 枚)。8 言語の README に、設定の「詳細」サブタブとネットワークモードの画像 2 枚を載せました。
- `docs/MIGRATING.md` に 1.6.7 から 1.6.8 へのブロックを追加し、8 言語のロードマップに残りの項目(古い変更履歴の項目と、あなた自身のサービスが必要な確認)を載せました。

### 修正

- 1.6.7 の変更履歴は、翻訳済みなのは 1.6.7 と 1.6.5 だけで、プロキシは検査ロジックでしか確認していないと述べていました。このバージョンは 1.6.3 までの残りを翻訳し、上記のとおりプロキシをエンドツーエンドで確認します。

## [1.6.7]

既定の 443 番ポートで動く HTTPS プロキシがネットワークモードで使えるようになり、変更履歴の翻訳範囲がさらに広がりました。

### 追加

- `listen.proxy_public_host`(設定 > 詳細 > ネットワーク、既定は空): 既定の 443 番ポートで `Host` と `Origin` をポートなしで転送する HTTPS プロキシの公開ホスト名です。これまでは検査が両方をモニターのポートと比較していたため、そのようなプロキシは拒否されていました。今後はこの 1 つの名前だけがそのまま受け付けられます。ネットワークモードが有効で、セッションが HTTPS(直接 TLS または `listen.secure_cookie`)のときだけ有効です。単純なホスト名でなければならず(ポート、パス、ユーザー、空白、IPv6 リテラルがあると空になります)、スキーマが `secure` とする他の設定と同じく、そのコンピューター自身からのみ変更でき、ラベルとヘルプは 8 言語で用意されています。
- このバージョンのすべての変更にテストを追加しました(テストは 843 件から 858 件に増え、新しいファイルが検査、値、スキーマ、文言を確認します)。

### セキュリティ

- 検査の例外は可能な限り狭くしています。ポートなしで受け付けるのはその名前だけで、他のホストは決して受け付けず、平文の HTTP でも受け付けません。`Origin` も同じ名前でスキームが `https` でなければならず(別のスキーム、ポート、パス、ユーザー、別のホストは引き続き拒否)、プロキシ名は検査の公開状態には現れません。

### 変更

- 変更履歴(ヘルプ > 変更履歴)は、1.6.7 と 1.6.5 について他の 7 言語に翻訳されました(1.6.6 は翻訳済み)。それより古い項目は翻訳済みの注記の下に英語のまま残り、新しいものから順に翻訳されます。
- `docs/ADVANCED.md`(8 言語)は、既定のポートのプロキシを「未対応」とする代わりに説明するようになり、`docs/MIGRATING.md` には 1.6.6 から 1.6.7 へのブロックが加わり、設定ガイドとヘルプの索引は再生成されました。

## [1.6.6]

ネットワークモードと `act` の修正、1.6.5 の積み残し、そして変更履歴の8言語化です。

### 追加

- ネットワークモードがすべてのインターフェース(`listen.host` = `0.0.0.0`)で待ち受けているとき、設定の上部に常時表示の赤いバーを出します(8言語)。これまでは `--doctor` だけが知らせていました。
- `POST /api/access` と `{"token": "..."}`: アクセストークンを本文に入れてネットワークモードのセッションを開くため、アドレスバー・履歴・ログにトークンが残りません。他のリクエストと同じ検査(ホスト、オリジン、誤ったトークン後のロックアウト、定数時間比較)を行い、Cookie は `HttpOnly`、`SameSite=Strict`、HTTPS では `Secure` で返ります。1.6.5 の `?access=` 付きアドレスも引き続き使えます。
- モニターが意図的に握りつぶす失敗のカウンター(`degraded.py`)。1件ごとにコンソールへ構造化された1行、モニターの隣の `degraded.json` に発生元別の件数、新しい `--doctor` の `degraded` チェック、バージョン情報パネルの「握りつぶした失敗」行。動作は変わらず、これらがモニターを止めることは今後もありません。
- 変更履歴(ヘルプ > 変更履歴)に言語ごとの翻訳ファイル `docs/CHANGELOG_<言語>.md` ができ、英語の原本と同じバージョンと節を持ちます。翻訳のどれかにバージョンが欠けていると `tools/make_help_index.py --check` とテストが失敗します。未翻訳の項目はその旨を読者の言語で表示します。
- このバージョンのすべての変更にテストを追加しました(テストスイートは 811 件から 843 件に増えました)。

### 修正

- **HTTPS のネットワークモードはページから使えませんでした。** 同一オリジンの検査が `http://` のオリジンしか受け付けず、直接 TLS や HTTPS プロキシ(`listen.secure_cookie`)ではブラウザ自身の `Origin: https://...` が拒否され、すべての変更(設定、確認)が 403 になっていました。現在はセッションのスキーム(https か http、両方ではない)から許可するオリジンを作り、ホストとポートを厳密に比較し、不正な形式のオリジンを拒否します。実際の TLS サーバーと、テストが作る証明書で確認しました。
- `act`: Stop が実行を解放するようになり、プロセスが終わらなくても次の開始が永遠に `busy` を返すことはありません。遅れて戻ったワーカーが新しい実行に触れることはなく、出力パイプとタイマーはあらゆる場合(通常終了、時間切れ、Stop、予期しないエラー)で閉じられ、テストスイートは `ResourceWarning` を出さなくなりました。
- `tools/make_screenshots.py` が何も言わずに終わることがありました。ブラウザはパイプを捕捉せず時間制限付きで動き、ブラウザがない場合やデモが起動しない場合は知らせ、`MONITOR_BROWSER` で手動指定でき、画像が作れなかったときの終了コードは 1 です。

### セキュリティ

- ネットワークモードでは、スキーマが `secure` とする設定はすべて、そのコンピューター自身からのみ変更できます。以前の4系統(`listen.`、`github_token.`、`act.`、`github_actions.`)だけでなく、Webhook、AI アクション、通知、OpenTelemetry、ミラー、ランナー、出力なども対象です。一覧はスキーマから読み取るため、新しい安全設定も誰も覚えていなくても対象になり、テストがすべてを確認します。

### 変更

- README とガイドの、バージョン情報・ヘルプ・現在・基本・詳細の画像を撮り直しました。
- `docs/ADVANCED.md`(8言語): 自分の証明書またはプロキシ配下での HTTPS、オリジンの規則、POST で開くセッション、警告バー。

## [1.6.5]

整合性とセキュリティのためのバージョンで、大きな新機能はありません。証明できないものは、もう安全とはみなされません。

### 追加

- 新しい設定(すべて保守的な既定値): `dispatch.required_ci`(ファイルでは `dispatch.required_ci_repos` と `dispatch.required_ci_profiles` も)、`act.allow_symlinks`、`listen.tls_cert_file`、`listen.tls_key_file`、`listen.secure_cookie`、`listen.max_failed_attempts`、`webhook.replay_seconds`、`webhook.max_per_minute`。設定ガイドは再生成されます。
- 古いバージョンが書いたバッチ用の `finalize --accept-legacy` と、`--doctor` の `risks` および `backend` の検査(8 言語)。
- このバージョンのすべての変更にテストを追加しました(テストは 729 件から 800 件超に増えました)。

### セキュリティ

- **緑のコミットには必須の CI が必要です。** `gha_dispatch_all.py` は、必須のワークフローファイルがそのコミットで成功し(既定は `ci.yml`、`dispatch.required_ci`、`dispatch.required_ci_repos`、`dispatch.required_ci_profiles`)、失敗・タイムアウト・承認待ちのものがなく(`action_required` は失敗と同様にブロック)、実行中のものがなく、実行一覧が完全である場合(最大 5 ページを読み、それより長い一覧は緑になりません)にのみ、コミットを緑とみなします。
- **`git fetch` の失敗はそのリポジトリのディスパッチを止めます。** git コマンドには時間制限があり、コミット ID は検証され、古い `origin/main` が証拠として扱われることはありません。
- **カタログはフォルダーの外に出られず、ディスパッチも変更できません。** `tool` はツールフォルダー内にある単純なファイル名でなければならず(外に出るリンクも拒否)、`extra` には `-f key=value` 形式のワークフロー入力だけを入れられ(`dry_run`、`ref`、`-R`、`--ref` は不可)、`finalize_flags` は長いフラグだけで、`gh workflow run` の引数は検証済みの部品から作られ、バッチの実行時に再確認されます。
- **古いバッチは盲目的に署名されません。** `finalize` は、確認したコミットの上に作られたとバッチが記録している実行だけを署名に提示します。古いバージョンが書いたバッチは `needs_review` になり、`finalize --accept-legacy` は GitHub から実行を読み直し、そのコミットが記録と一致する場合にだけ受け入れ、警告し、署名のたびに LEGACY という語を求めます。
- **`act` はワークスペースの外に出ません。** クローンは解決され、ワークスペース内の実在のフォルダーでなければなりません(リンク、`..` を含む名前、別の場所を指す `.github` は拒否。`act.allow_symlinks` はクローンへのリンクを許可します)。時間制限と Stop は、実行が起動したプロセスのツリー全体(Linux と macOS ではプロセスグループ、Windows では自身の PID に対する `taskkill /T`)を終了し、その実行が作った `act-` コンテナーを削除します。
- **ネットワークモード**: 自分の証明書と鍵で直接提供する HTTPS(`listen.tls_cert_file`、`listen.tls_key_file`。TLS 1.2 以上で、使えない場合は平文の HTTP では起動しません)、または HTTPS プロキシの背後での `Secure` クッキー(`listen.secure_cookie`)。アクセストークンはすぐにアドレスバーから消えます(リダイレクト、`Referer` なし)。誤ったトークンを送りすぎたアドレスは 5 分間拒否されます(`listen.max_failed_attempts`)。ページのアドレスはサーバーが待ち受けているものです。受け付けるのは IPv4 アドレスのみで、設定でも検査でも同じです。接続が平文の HTTP のときはコンソールがそう伝えます。
- **Webhook**: 各配信には `X-GitHub-Delivery` の ID が必要で、繰り返された配信は `webhook.replay_seconds` の間無視されます。1 つのリポジトリが 1 分間に引き起こせる受け付け済みイベントは最大 `webhook.max_per_minute` 件です。`full_name` の所有者は監視対象のアカウントでなければなりません。ネットワークモードでは 1 つのアドレスは 1 分あたり 120 リクエストに制限されます。受け付けたイベントはそのリポジトリの保存済み条件付き読み取りを破棄し、次のサイクルの対象にします。異常な文字を含む署名ヘッダーは単に拒否されます。
- **MCP サーバー**: 形式が誤ったメッセージ(パラメーター、引数、id、メソッド)にはそのメッセージだけにエラーを返し、ツールの予期しない不具合は内部エラーとなってもサーバーを終了させず、64 KB を超える行は拒否されます。
- **保存された GitHub トークンは `gh` にだけ渡されます。** モニターの環境には置かれなくなったため、`act`、通知コマンド、その他の子プロセスは継承できません。
- **GET は何も書き込みません。** 監査フォルダーへの日報のコピーは、ワンタイムトークン付きの POST(`/api/sentinel/parte/save`)になり、GET の `?save=1` は廃止されました。
- `--doctor` は危険な組み合わせ(全インターフェースでのネットワークモード、ネットワークモード中に実行する AI アクション、ネットワークモード中の `act`、平文ファイルのトークン)を名指しし、トークンの保存場所を示しますが、トークン自体は決して表示しません。

### 修正

- 通知の `max_per_hour` はイベントではなくメッセージを制限するようになりました(チャンネルごとに 1 単位、1 つのロックの下で一度に予約)。送信できないチャンネルは何も予約しません。
- 設定の 2 つの同時保存で一方が失われることはなくなりました(プロセス内のロックとロックファイル)。
- 署名キューの書き出しは、単に拒否するのではなく、書かなかった理由(拒否されたドライブやネットワークパス、ファイルではなくフォルダー、システムのエラー)を伝えます。
- 二次制限の待機とタイムアウト後の再試行にランダムなジッターが付きます。
- zip をきれいなフォルダーに展開するテストは通常のテストスイートに含まれなくなりました。`make_release.py` は時間制限付きでスイートを一度実行し、その後クリーンインストールを独立した段階として実行し、どちらかが失敗したときは stdout と stderr を表示します。

### 変更

- 通知、Webhook、高度な機能、出力、AI アラート、移行のガイドが、これらすべてを 8 言語で説明しています。`docs/MIGRATING.md` には 1.6.4 から 1.6.5 へのブロックがあります。

## [1.6.4]

### 追加

- **AI 向けアラート**: モニターはローカルの読み取り専用フィード(`ai_alerts.jsonl`(1 イベント 1 行)と、サイクルごとに書き直される `ALERTS_BRIEF.md`(既定 2 KB))を書き出し、赤のワークフローごとに 1 件のアラートを出します。安定した ID、重大度、編集可能なルールによって実際のものか一時的なものかを区別した推定原因、推奨アクション、状態(未対応、確認済み、ワークフローが緑に戻ったときに自動解決)を持ちます。すべてはトークン、キー、メールアドレス、IP アドレス、ホームフォルダーを除去するクリーナーを通ります。`GET /api/ai/brief` と `GET /api/ai/alerts`、任意の読み取り専用 MCP サーバー(`mcp_server.py`: `get_alerts`、`get_red_repos`、`get_run_failure`、`get_quota`、`--allow-ack` 付きの `ack_alert`)、新しい実際のアラートが現れたときの通知、このコンピューター上のアドレスへの任意のフック(オフ)、`ci_red.json` の任意の `ai_hint`。新しいガイド `AI_ALERTS.md` を 8 言語で用意しました。
- **任意機能(すべて既定でオフ。それぞれ 設定 > 詳細 にスイッチあり)**。スイッチ、確認、トークンがなければ拒否することをテストで証明しています: ネットワークモード(プライベートアドレス、すべてのリクエストにアクセストークン、許可するホスト名、常時表示の赤いバー、そのコンピューター自身からだけ変更できる公開関連キー)、モニターがシステムの安全なストア(Windows DPAPI、macOS Keychain、Linux Secret Service、なければ権限 600 のファイル)に保管する GitHub トークン(設定、ログ、応答には決して入らず、削除ボタンあり)、GitHub 上のアクション(再実行、キャンセル、クローズ、マージ。送信内容を正確に表示してから個別に確認)、閉じたリストから `act` でここでワークフローを実行(本物のシークレットなし)、アーティファクトのローカルミラー、セルフホストランナー(アイドル、使用中、オフライン、任意でディスクと負荷)、OpenTelemetry エクスポート(トレースとメトリクス、OTLP/HTTP JSON)、ログインの組織、ジョブのラベルごとの FinOps(Linux、Windows、macOS、大型ランナー)、含まれる分を超えた分の料金、請求レポートの Codespaces、Packages、ストレージ。新しいガイド `ADVANCED.md` を 8 言語で用意し、実際のサービスを手で試す `tools/manual_check_live.py` を追加しました。
- `--doctor --json`。doctor は使用中のポート、残りの枠、独自のターゲットファイルの有無、ワンタイムトークン、公開状態も報告します。パッケージの README は起動ランチャーの選択(フル、lite、バッチ、ターミナル、doctor、デモ)から始まります。
- ターミナルアプリはシンプルな設定(セキュリティ設定は除く)を編集でき、AI タブがあります。再起動が必要な設定の持続バナーは再読み込みしても残ります。ヘッダーは、センチネルの A10 が枠のために一時停止している時と、分の予算をどれだけ使ったかを表示します。ウェルカムはサーバー側でも記憶されます。
- `redrule.py` は、ダッシュボードと同様に依存関係更新の動的な実行を無視し、ルールの共有ケースはテストのフィクスチャになりました。

### 変更

- **ヘルプが 8 言語で完全になりました**: ロードマップ、コントリビュート、セキュリティ、サポートの文書が翻訳され、変更履歴の固定ラベルも翻訳され、その項目は翻訳済みの注記付きで英語のみとして示されます。トピックに言語が欠けていると `tools/make_help_index.py --check` とテストが失敗します。検索は最大 30 件を表示し、巨大な文書がサーバースレッドを占有することもなくなりました。
- 赤いタイルは両エディションでワークフローを数え、いくつのリポジトリにまたがるかを示します。lite エディションは初回起動時にフル版の更新間隔を引き継ぎます。
- 一時的な失敗(TLS の不調、5xx)は指数バックオフで再試行され、3 サイクル連続した場合にだけエラーとして表示されます。直前の画面は残ります。
- lite エディションのターミナルビューはセンチネルを要求しなくなりました。lite エディションはセンチネルモジュールを一切読み込みません(ローカルガードは `localguard.py` に移りました)。
- `--demo` は、書き込む可能性のあるすべてのファイル(ログ、キャッシュ、イベントフィード、履歴、ウェルカム)を一時フォルダーにリダイレクトします。

### セキュリティ

- `updates.check` がオフ、または `airgapped` がオンのとき、モニターは更新通知のためのネットワークリクエストを一切行いません(テスト済み)。
- 実際の GitHub API で確認済み: トークンのスコープは正しく読み取られ、組織の一覧と請求レポートは静かに縮退します(`user` スコープのないログインは「見つかりません」を受け取り、モニターは推定値を保持します)。

## [1.6.3]

### 追加

- **バージョン情報パネル**(ヘッダーの **i** ボタン、両エディション): バージョン、エディション、作者、ライセンス、Python とシステム、リンク(リポジトリ、リリース、変更履歴、ドキュメント、Issue)、使用するファイル(読み取り専用)、サーバーの状態、ライブラリのクレジット、そしてサポート用に情報をコピーするボタン(シークレットやトークンは含まず、ホームフォルダーは `~` と表示)。`GET /api/about` と、コンソールの `--about`。
- **ヘルプパネル**(**?** ボタン、`?` キー、開いているタブのページを開くタブバーの「?」): すべてのドキュメント(README、クイックスタート、各ガイド、ロードマップ、変更履歴、コントリビュート、セキュリティ)を検索できる索引として、ページの言語で、翻訳されていない文書は英語で、インターネットなしにローカルサーバーから提供します。実際の文書から `tools/make_help_index.py`(CI で `--check`)が作るため、同じ文章を二度書くことはありません。Markdown は安全に表示されます(すべてエスケープ、画像は読み込まず、`http(s)` リンクと他の文書へのリンクのみ)。コンソールでは `--help-topics [トピック]` と `--help-search 単語`。
- **新しいバージョンのお知らせ**: 新しいリリースが公開されたとき、ヘッダーの控えめなバッジ、バージョン情報の 1 行、コンソール、`--doctor` に表示します。公開リリースページへの読み取り専用リクエストを 1 日 1 回、他のすべてと同じクライアントで(条件付き読み取り)行い、何もダウンロードやインストールをせず、あなたに関する情報を送らず、プレリリースは無視し、バージョンを数値として比較し(1.6.10 は 1.6.9 より新しい)、オフラインでは何も出さず、`updates.check` またはエアギャップ環境(`airgapped`)ではオフになります。
- **設定 > 基本**(最初のタブ): 起動時にブラウザーを開く、更新のお知らせ、エアギャップのスイッチ、ワンタイムトークン、検出オプション、ライフサイクルルール、プランとクォータ。その下に、モニターがアカウントで見つけたもの(オーナー、見つかったリポジトリ、監視中、除外したもの)、新着、提案されたグループ。
- **`--doctor`**: Python、`gh`、ログイン、残りの枠、ネットワーク、フォルダーの書き込み権限、空きポート、任意の Docker、Rich、Textual。失敗ごとに、直すための正確なコマンドを 8 言語で示します。
- **`--demo`**: 架空のデータでページを表示します。`gh`、ログイン、ネットワークは不要で、あなたのものは何も読み書きされません。
- **3 ステップのウェルカム**(ページを初めて開いたとき): 何をするか、アカウントで何を見つけたか、次にどこへ進むか。
- **自動検出**: 新規、消失、アーカイブ、アーカイブ解除されたリポジトリのイベント(コンソール、設定 > 基本、フル版では通知にも)。未分類のリポジトリが 3 つ以上同じ接頭辞を共有するときの提案グループ(確認後にのみ、ファイルのコピーを取って追加)。フォーク、空、プライベートのリポジトリを除外するライフサイクルルール。呼び出し予算の範囲で実際の活動に追従する任意の自動更新頻度。
- **ワンタイムトークン**(`session_guard`、既定でオン): 設定を保存する、またはアクションを確認する直前にページが要求します。また、保存した設定が再起動を待っている間、各タブに**再起動バー**を表示します。
- **ワークフローリンターのレベル**(情報、警告、エラー)をページのフィルターとして、ターミナルアプリには `Scripts` を追加しました。
- **あらゆる種類のアカウントに対応するクォータとプラン**: 設定 > 基本でのプラン。数値(含まれる分を金額で、システムごとの料金、同時実行数、ジョブと実行の上限、API の枠)は `quotas.json` にあり、新バージョンなしで編集できます。課金対象の分は実時間の分とは別に数えられ(パブリックリポジトリは無料、プライベートは Windows や macOS の倍率を使用)、月次の見込みは推定と明記され、含まれる分の 75 % と 90 % で月に 1 回通知による警告が出ます。プランの上限に対する実行中と待機中のジョブ、6 時間の上限に近いジョブ、GitHub 自身のヘッダーから読み取るトークンの種類(1 時間 60 回しか残っていないときはログインを勧めます)。実際の使用量は、任意で読み取り専用の請求レポート(`quota.billing_api`、既定でオフ、403 や 404 では何も出さない)からのみ得ます。`GET /api/quota`。
- **作業モード: 通常、高速、ターボ**(`modes.py`、ガイド `MODES`): ヘッダーのゲージアイコン付きセレクターと、コンソールの `--mode` / `--mode-minutes`(両エディション)。プリセットは設定の `modes` ブロックにあります。開始前に、ページは最悪の場合の 1 時間あたりの呼び出し数、条件付き読み取りが通常節約する量、残りの枠がどれだけ持つかを表示します。時間が尽きたとき、または枠が `min_rate_remaining` を下回ったときは、お知らせとともに自動で通常に戻ります。ログインなし(1 時間 60 回)では高速とターボは理由付きで拒否されます。ワンタイムトークンが必要で、メモリ上にのみ存在し、コンソールのバナーに名前が表示されます。`GET` と `POST /api/mode`。
- **セカンダリレート制限の後**、モニターはすぐに再試行する代わりに、最低 1 分待ち、その後は待ち時間を 5 分まで倍にします。
- **対話型ターミナルアプリ** `tui_textual.py`(任意、`pip install textual`): 概要、リポジトリ、ビルド、パフォーマンス、スクリプト、設定(基本のスイッチ)のタブ、フィルター、リンターのレベル、更新、ブラウザーで開く、バージョン情報、ヘルプ。`--lite` は lite のタブを表示します。シンプルな Rich ビュー(`tui.py`、`--once`)は残り、`--about` と `--help-topics` も使えます。
- **エディションが一目で分かります**: 起動バナー(`GitHub Actions Monitor LITE 1.6.3 · ポート 8766 · actions_monitor_lite.json · センチネルなし · http://127.0.0.1:8766/`、または COMPLETE · ポート 8765 · センチネル有効)、コンソールとターミナルのウィンドウタイトル、ステータス行、`--doctor`、ターミナルビューの `[LITE]` / `[COMPLETE]` タグ、ランチャーでの同じタイトル。
- 8 言語の新しいガイド: **センチネルとその検査 A1-A13**(それが何か、どう起動するか、書き出すファイル、読み方、各検査の正確なルール、設定、アクション、A10 の 25 の検査。テストがガイドとコードの一致を保ちます)、**クォータとプラン**、**最初の 5 分**(`FIRST_STEPS`)。移行ガイドには 1.5.x から 1.6.x へのブロックがあり、README には 2 つのエディションの選択表があります。
- これらすべてのテスト(セマンティックバージョン、オフライン・オフ・エアギャップでのお知らせ、安全な Markdown、索引、ワンタイムトークン、検出、`--doctor`、パブリックとプライベートのリポジトリ・Windows と macOS・トークンなし・Enterprise・請求レポートの 403 のクォータ、バナーとランチャー)。

### 変更

- 設定ページは **基本** タブから始まります。ガイド `SETTINGS` はそれに合わせて生成されます。
- モニターはアカウントのリポジトリを種類(アーカイブ、フォーク、プライベート、空)付きで一覧にします。それらのフィールドがない古い `gh` では単純な一覧に戻ります。

### セキュリティ

- GitHub に新しく書き込むものはありません。更新のお知らせ、請求レポート、検出は読み取り専用で切り替え可能で、どれもあなたに関するデータを送りません。ヘルプとバージョン情報のパネルはこのコンピューターから提供され、サポート用テキストにシークレットは含まれません。
- 設定の書き込み、AI アシスタントのアクションの確認、提案グループの追加には、ページのワンタイムトークンが必要です。

## [1.6.2]

> このバージョンの記載は現在英語のみです。翻訳は今後のバージョンで追加されます。

### 追加

- **A catch-all group** `rest` ("Everything else", prefix `*`) at the end of the example catalogue of ecosystems, so a new installation leaves no repository out.
- **An automatic group "Unclassified"** for the repositories that no group claims (setting `show_unclassified`, on by default; an explicit choice of ecosystems is respected).
- **A warning when the filter hides repositories**: a banner (complete and lite) says "your ecosystem filter hides N of the M repositories of the account" and names them.
- **The lite edition starts with what you already set up**: on its first start `actions_monitor_lite.json` copies from `actions_monitor.json` (when it exists) the account, the repositories and ecosystems to watch, the catalogue files, the exclusions, the language and the reading depth, and says so on the console. Without such a file its template watches all the ecosystems.
- **`tui.py --lite`** (or `MONITOR_MODE=lite`) reads the lite edition on port 8766.
- **`redrule.py`**, the single small rule of "red on main", used by the sentinel and by the lite edition (which marks the figure as approximate because it guesses the default branch).
- **`ghamon_etag_invalid_total`**, the count of damaged cache entries, in `/metrics`.
- Tests: header-data parity between the complete and the lite edition, the catch-all group, the hidden-repository count, the lite start, the webhook hot mark, the damaged cache entry, and that importing the monitor or the sentinel never loads Rich.
- Guides `LITE` and `SETTINGS` (eight languages) updated.

### 変更

- **Both editions show the same header figures**: runs, failures, successes, compute minutes, running and queued are counted once, by the server, over the same 24 hours with each run counted once; the lite edition reads as deep as the complete one. The lite edition hides the "unsigned" tile.
- **A webhook event marks the repository as hot**, so the next cycle reads it again whatever the event said.
- The GitHub allowance tile is painted from the first moment, while the repositories are still loading.

### 修正

- A new installation with the example catalogue saw almost no repository; the lite edition detected one repository out of 129 because its template filtered by ecosystem.
- **A damaged cache entry is only a miss**: it is thrown away and the endpoint is read again in full.
- "Red on main" and the compute minutes differed between the two editions.

### セキュリティ

- The lite edition never inherits the sentinel, the AI, the webhook, the outputs or the notifications, nor any secret, from the complete one; it writes neither `ci_red.json` nor a signing queue.

## [1.6.1]

> このバージョンの記載は現在英語のみです。翻訳は今後のバージョンで追加されます。

### 追加

- **The lite edition**, a second and simpler product in the same package: `MONITOR_LITE_GITHUB_ACTIONS.bat` / `.sh` / `.command` or `--lite` / `MONITOR_MODE=lite`. What is running and what failed, failures and successes of 24 hours, red on main, the history and the basic charts; a short Settings page (account, repositories and ecosystems, refresh, language, theme); its own file `actions_monitor_lite.json`, its own state files with the suffix `_lite` and port 8766, so both can run side by side.
- **`act` command in the repository panel**: for each workflow of the repository, `act -W .github/workflows/FILE -j JOB` ready to copy. The monitor never runs it (running it exists only as a confirmed action of the AI assistant).
- **A container example** (`deploy/Dockerfile`) that the CI builds.
- Guide `LITE` in eight languages, a Lite-versus-Complete table in every README and new screenshots of both editions in light and dark.
- The roadmap lists what did not fit: local mirror of artifacts, FinOps of the minutes, self-hosted runner status and an OTLP export, and the notes of the terminal view (why it uses Rich).

### セキュリティ

- The lite edition has no sentinel: it is not imported and its endpoints answer 404.

## [1.6.0]

> このバージョンの記載は現在英語のみです。翻訳は今後のバージョンで追加されます。

### 追加

- **Conditional reads (ETag)**: every read of the run lists sends `If-None-Match`; a `304 Not Modified` answer costs no quota. The header and `ghamon_etag_saved_total` count the reads saved; `cache.etag.*` in the Settings tab.
- **Resilience to network cuts**: when every read of a cycle fails with a connection problem the page keeps the last picture with an offline banner and resumes by itself; `offline` and `online` events (they can be notified) and `ghamon_offline`.
- **Analytics** (section A12 of the Sentinel tab, `/api/analytics`, `/metrics`, the Grafana JSON source): p50 / p95 of the duration of each workflow, of the queue time of its jobs and of each step; workflows that got slower than usual; **flaky** workflows (failed, then passed on the same commit, or needed another attempt), only a label that never changes what counts as red.
- **Incoming webhook in real time**: a signed `workflow_run` event updates the run list of its repository without reading GitHub, `workflow_job` events bring queue and step times; only short validated fields are kept (`/api/live-events`).
- **Workflow linter**: `lint_workflows.py` (actions not pinned by SHA, missing or broad permissions, secrets in clear text, injection, `pull_request_target` with the PR's code), rules switchable with their own severity, a line in the daily report and the section A13. A comment `# monitor-lint: ignore RULE reason` or the setting `lint.ignore` silences a finding.
- **Notifications** (off by default): Telegram, Discord, Slack, Matrix, MQTT and a local HTTP address, a limit per hour, a test button and a documented adapter contract (`monitor/docs/schemas/notification_event.schema.json`).
- **AI assistant**: new providers `anthropic` (Messages API, the model is yours to choose) and `copilot` (`gh copilot` with your own login, text only, no tools); new tasks (daily report, release notes, a question about a repository); settings for the kinds of event, the repositories, the language and the limits, a test button and the use of the day. A closed list of actions (`gh run rerun`, `gh issue close`, `act`), only PROPOSED by default.
- **The figures of the header are tiles** with an icon, a big figure and a small label, coloured by state, with a tooltip, a click that leads to the tab, counting figures and a skeleton that shows the last known values at once; the second line (repositories, hot, mode, reads saved, GitHub allowance with a bar and a live countdown, connection, last update and the loading progress) is made of tiles too.
- **Terminal view**: `tui.py` draws a live grid in the console (read-only, optional, needs the package `rich`; the monitor and its tests need no package).
- **For servers and bigger accounts**: `GET /api/health`, `GH_HOST` for GitHub Enterprise Server (every link of the page follows it), `discover_limit`, minimum permissions per feature, and a guide to run it as a service (systemd, launchd, a scheduled task, a container) and behind a reverse proxy.
- Published JSON schemas of `ci_red.json`, of the public export and of the notification event (`monitor/docs/schemas`), and a public roadmap (`docs/ROADMAP.md`).
- New guides in eight languages: notifications, the AI assistant, analytics, console tools and deployment; the webhook guide covers the real-time events. All screenshots were redone (light and dark, console tools included) with `tools/make_screenshots.py` and invented data.

### 変更

- **Settings**: new sub-tabs for reads and cache, notifications, analytics, the linter and the terminal view; the AI and webhook sub-tabs have all their options.

### 修正

- **The linter no longer cries wolf on placeholders**: a value that looks like a secret is classified (a known token format or a long high-entropy string is serious, a readable filler such as `placeholder` or `changeme` is only information, anything else a warning; references and empty values are no finding) and its value is never printed or stored.
- **A browser that closes or reloads its tab while the page is loading no longer prints a traceback** (`ConnectionAbortedError`, `ConnectionResetError`, `BrokenPipeError`): they are counted in `ghamon_client_disconnects_total`; a real error is still shown.

### セキュリティ

- The incoming webhook stays off by default, on `127.0.0.1`, with a mandatory HMAC.
- Notification secrets live only in environment variables; hosts are fixed; notifications never write to GitHub.
- AI actions: running one needs its own switch and a confirmation of the full command each time, only on targets the monitor already watches, with a limit per hour, a local log and a lock after two failures in a row.

## [1.5.2]

> このバージョンの記載は現在英語のみです。翻訳は今後のバージョンで追加されます。

### 追加

- **The Settings tab is organised in sub-tabs**, ordered from the common to the advanced (This browser, General, Refresh and limits, Sentinel, Surface checks A10, Readiness A11, Folders and files, Outputs, External AI, Incoming webhook). Inside a sub-tab the settings sit in titled blocks whose first field is the main switch (the rest of the block dims while it is off). Every field shows its unit and range, a badge (needs a restart / applies now), a badge for the safety options that start in their conservative state, and one line of help. A search box filters all the sub-tabs, each sub-tab counts its unsaved changes, Save and Discard stay visible, the arrow keys, Home and End move between the tabs and the last sub-tab used is remembered by the browser.
- **Every setting of the configuration file is in the page now**: the A10 checks (a switch per check and its limits), the weights of the ecosystem health score, the sources of the pinned versions, the Actions-minutes ceilings, the required files, the audit file patterns, the hot period of the sentinel, the unknown-sample rule of A2, the candidate prefixes, the list of repositories and the switch of the incoming webhook.
- **Signing queue by trust**: each row says `verified`, `unknown` or `failed`; the Sentinel tab has a Signature filter with the count of each kind; `read_report.py --sign-trust` filters the console list and the export, and the exported rows carry `trust`.
- **Readiness chips in the header**: one coloured chip per ecosystem with its health score.
- **A minimal Grafana board** (`red_by_ecosystem.json`) and a test that checks every metric of both boards against what `/metrics` serves.
- New guide `WEBHOOK` (refresh-only mode) and a commented example of the pin sources, in eight languages.
- `tools/make_settings_doc.py` writes the settings table of the guides from the schema and the texts of the page, and the CI checks it.

### 変更

- **The daily report groups the issue-closing suggestions** in one line per repository (the monitor still closes nothing).
- **The contract of the profile dashboard** is documented and checked by a test (`/api/outputs/dashboard.json` is exactly the document of `ci_red.json`; the public export never carries the signing side).

### セキュリティ

- The shared secret of the webhook is never shown in the page: it only says whether it is defined.

## [1.5.1]

> このバージョンの記載は現在英語のみです。翻訳は今後のバージョンで追加されます。

### 追加

- **The settings page can set the external AI of the sentinel** (group "External AI for the sentinel"): `ai.provider` (`none` / `ollama` / `openai-compatible`), `ai.model`, `ai.ollama_url` (only this computer), `ai.base_url` (https only), `ai.api_key_env` and `ai.daily_limit`. Off by default; an outside service receives data of your repositories.
- **`migrate_state.py`**: brings the files written before 1.5.0 to the new names (events, report history, release candidates, batch records, the `report_history_days` setting). A dry run by default; `--apply` copies and keeps the old files, `--move` renames them; nothing that exists is overwritten. One-page guide in `docs/MIGRATING.md`, in eight languages.
- **`--init-catalog`** creates editable `ecosystems.json`, `targets.json` and `profiles.json` from the examples.
- A test makes sure no document sends the reader to a command that was renamed in 1.5.0 (only the tables of old and new names and the migration guides may name them).
- The version in every README.

### 変更

- **First start without catalogue files of your own**: the console says the example files are in use.
- Python 3.11 or newer is the documented minimum (tested on 3.11 and 3.13 on Windows, Linux and macOS).

### セキュリティ

- Only the NAME of the environment variable that holds the AI key can be set: the key itself is never shown or saved.

## [1.5.0]

> このバージョンの記載は現在英語のみです。翻訳は今後のバージョンで追加されます。

**Update notice (read this first).** Several files and settings have English names now. Nothing is lost: the old names are still READ where a file written by an earlier version may exist, and the new names are the only ones written.

| Before 1.5.0 | From 1.5.0 |
|---|---|
| `leer_parte.py` | `read_report.py` |
| `eventos.py` | `events.py` |
| `parte_history.py` | `report_history.py` |
| `LOTE_GITHUB_ACTIONS.bat` / `.sh` / `.command` | `BATCH_GITHUB_ACTIONS.bat` / `.sh` / `.command` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` (copy or rename them to keep the history of events) |
| `PARTE_CENTINELA_DIA_<day>.txt/.json` (report history) | `SENTINEL_REPORT_DAY_<day>.txt/.json` (the old ones are still read) |
| `PARTE_CENTINELA_<time>.txt` (saved report) | `SENTINEL_REPORT_<time>.txt` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_<time>.json` | `<signed_dir>/batches/batch_<time>.json` (the old records are still read) |
| `parte_history_days` (setting) | `report_history_days` (the old name is still read) |
| `monitor_y_centinela.zip` and folder | `github_actions_monitor.zip` and folder; `LEEME_CORREO.txt` is `README_MAIL.txt` |
| A8 looked for `RECONCILIACION_TOTAL_AUDITORIAS_*.txt`, `MAPA_DE_RONDAS_*` | the names are `sentinel.audit_files` (neutral defaults `RECONCILIATION_TOTAL_*.txt`, `ROUNDS_MAP_2*.txt`, `ROUNDS_MAP_EXTRA_*.txt`); set your own there |
| `ci_red.json`, its schema and the `--export-status` files | unchanged (they are a contract) |

- **English by default.** The language of the system no longer decides: the tools start in English until you choose another one in the Settings tab, with `language` in `actions_monitor.json`, `MONITOR_LANG` or `--lang`.
- **A clean, neutral package.** `ecosystems.json`, `targets.json` and `profiles.json` are no longer part of the package: only the `*.example.json` files travel, and a missing default file falls back to its example. Your own files live anywhere and are named by `ecosystems_file`, `targets_file` and the new `profiles_file`; the folder of your local signing tools is the new `tools_dir`. The tests use their own fixtures (`tests/fixtures`).
- **Settings tab.** A new tab changes the values of `actions_monitor.json` from the page: a whitelist of keys with their type and range, one request refused as a whole when a value is invalid, a copy of the previous file in `config_backups/` before every save (the last ten are kept), an atomic write, only on 127.0.0.1 with the same Host and Origin checks as every other endpoint, JSON only. Tokens, secrets, signature keys and the command of the sentinel are not in the list: they are never shown and never written, and every other key of the file is kept as it was. Each setting says whether it needs a restart. The language selector, the theme and the dense view moved there.
- **Buttons and icons.** Buttons have relief, light up on hover and sink when pressed; the icon buttons are inline SVG with an accessible name and a tooltip in the 8 languages. Colours, type, cards, bars and the ring follow the status dashboard of the profile repository.
- **Life in the charts.** Bars grow in, what is red or running has a discreet pulse, the figures of the header count up, hovering a bar highlights it and gives its text as a tooltip, widths change smoothly; all of it stops with `prefers-reduced-motion`.
- **Outputs for other tools (off by default, 127.0.0.1 only, no new token).** `/metrics` in the Prometheus format (red workflows per ecosystem and repository, red streaks and hours, builds waiting for a signature, A10 paused, allowance left, incomplete snapshot...), `/api/outputs/grafana.json` for the Grafana JSON / Infinity source and `/api/outputs/dashboard.json` (the `ci_red.json` document) for the status dashboard. An importable Grafana dashboard is in `docs/grafana/` and the details in `docs/OUTPUTS.md`.
- **Report:** a line (code `tag_vs_manifest`) when a release tag is ahead of the version of the manifest; the unsigned figure is ordered by the longest wait and says how long it is; the repository panel suggests the `gh issue close` command (never run) for a failure issue whose workflow is green again; the `hil` batch profile is documented in `profiles.example.json`; tests for `finalize` and for `monitor_link`.
- **Docs:** `docs/SETTINGS.md`, `docs/OUTPUTS.md`, README and QUICKSTART in the 8 languages updated, screenshots made with invented repositories.

## [1.4.5]

> このバージョンの記載は現在英語のみです。翻訳は今後のバージョンで追加されます。

- **The report says when the snapshot is incomplete:** a line with the stable code `incomplete` (still loading, no local workspace, errors while reading) right after the headline, so nobody acts on a half-read list of red repositories or signing queue.
- **Signing summary:** one line with how many releases wait to be signed (verified / not checked / failed the check) and how many builds are build-only on purpose, so "not signed on purpose" is not confused with "signature missing" (code `sign_summary`).
- **A10 paused for the quota is said in the report** (code `a10_paused`) with the allowance left and needed, and the three knobs that control it.
- Texts in the 8 languages; tests for the three lines.

## [1.4.4]

> このバージョンの記載は現在英語のみです。翻訳は今後のバージョンで追加されます。

- **Author and licence are always visible:** the web panel has a footer with the author and the licence, `read_report.py --version` and the new `gha_dispatch_all.py --version` print them under the version, and the monitor prints the same line when it starts. The text is in the 8 languages (`ui.about`); the author and the licence come from `tool_version.py`.
- **Bridge to the dashboard written down:** `docs/CI_RED_BRIDGE.md` says what `ci_red.json` contains (schema 2, `complete`), how to export it and what a reader must check; the monitor still never pushes or commits.
- Tests for the author line in the 8 languages, the footer, both `--version` flags and the start-up line.

## [1.4.3]

> このバージョンの記載は現在英語のみです。翻訳は今後のバージョンで追加されます。

- **A workflow that only runs on pull requests no longer makes A2 inconclusive:** `pull_request` and `pull_request_target` join the events whose runs never sit on the default branch (like `workflow_dispatch`, `release` and `workflow_call`), so a workflow such as a contract integration check that only runs on pull requests is not asked for a last run on main. A workflow that also has `push` or `schedule` still counts. Tests for both cases.

## [1.4.2]

> このバージョンの記載は現在英語のみです。翻訳は今後のバージョンで追加されます。

- **A2 no longer counts a run in progress or a cancelled one as seen:** when it resolves a hidden workflow, the Sentinel now asks for the last completed runs of that workflow on the default branch (`gh run list -w <file> --branch <default> --status completed -L 10`, read only) and uses the first one with a real conclusion. A cancelled or skipped run (and anything without a conclusion) is ignored, so it can no longer hide an earlier red; a workflow with no completed run with a conclusion on the branch stays inconclusive on its own. Same quota gate, call limit and cache as before.

## [1.4.1]

> このバージョンの記載は現在英語のみです。翻訳は今後のバージョンで追加されます。

- **A2 resolves a hidden workflow instead of giving up on the whole repository:** when a repository has a full run sample and a workflow of its clone (one that can run on the default branch) is missing from it, the Sentinel asks GitHub for the last run of THAT workflow on the default branch (`gh run list -w <file> --branch <default> -L 1`, read only). A red answer counts as red in A2; a green one removes the workflow from the inconclusive list; a workflow with no run on the branch stays inconclusive on its own and the panel names it (`repo/file.yml (no run on the default branch)`) instead of only the repository. Without quota (same gate as A10: `min_rate_remaining` x `surface.min_rate_factor`, plus the hourly budget) the workflow stays inconclusive and the panel says why. New options `sentinel.a2_resolve_max_calls_per_tick` (4; 0 = never ask) and `sentinel.a2_resolve_ttl_seconds` (3600, how long an answer is kept; it is also saved in the cache file). The snapshot carries `a2.inconclusive_workflows` (labels) and `a2.inconclusive_details`; `a2.inconclusive` is still the list of repositories. 5 new texts in the 8 languages and a reworded `ui.a2_inconclusive`.

## [1.4.0]

> このバージョンの記載は現在英語のみです。翻訳は今後のバージョンで追加されます。

- **New layer A11 "Readiness" (read only, real data only):** a panel of the Sentinel tab, a traffic light in its header and two lines of the report. It is switched with `sentinel.readiness.enabled` and described in `readiness.py`.
  - **Release readiness:** one row per repository with at least `candidate_min_entries` entries in `[Unreleased]` (external ecosystems excluded): CI of the default branch (the single rule of A2) with the commit it ran on, whether the version the clone declares (`*.project.json`, else `pyproject.toml`, else the first CHANGELOG heading) is already above the last release, whether a build exists after that release, whether it is signed (the states of A5), and the next step (`fix the red CI`, `wait for run data`, `bump the version`, `build in Actions`, `sign`, `publish`, `cut and publish`). A green CI over a full run sample that may hide an older workflow says so.
  - **Ecosystem health:** per ecosystem, 100 minus weighted counts of red CI, stuck builds, secrets, serious alerts, other alerts, Dependabot PRs older than `stale_pr_days`, builds waiting for signing and repositories with hygiene problems (`sentinel.readiness.health.weights`); the parts that lower the score are listed. No score is shown (`?`) when fewer than `min_coverage` (0.5) of the repositories of the ecosystem have run data and alerts. The report warns when a score is under `warn_below` (70).
  - **Dependency pins:** repositories that pin an older version than the one of the repository that provides the contract or library. Where the pins live is data (`sentinel.readiness.pins.sources`): a JSON table of pins in the provider (`pin_table`) or lock files in the consumers (`lock_files`, the oldest one found counts). Plain file reads of the local clones, cached `pins.refresh_seconds`; an ecosystem without a configured source is listed as having none, and nothing is guessed. The shipped example has no source.
  - 60 new texts in the 8 languages; `tests/test_readiness.py` (rules, weights, coverage, pins on a temporary tree, the page and the 8 catalogues).
- **`docs/CI_RED_SCHEMA.md`:** says explicitly that the PC publishes neither `ci_red.json` nor `pending_sign` to any repository or dashboard (the signing side is local by decision); a public consumer recomputes the rule from the public runs or uses `read_report.py --export-status`.
- **Quota tuning from the log (`actions_monitor_log.txt`, 3 days, 889 samples):** the shared allowance was under the floor (`min_rate_remaining` 1500) in 11% of the samples since 5 November and under 3000 in 45%; the hourly burn was 3000-5000 calls in most hours and reached the limit in some. In the maintainer's `actions_monitor.json`: `refresh_seconds` 120 -> 180 (the real cycle was a median of 139 s) and `sentinel.surface.min_rate_factor` 2.0 -> 1.5 (the cold calls of A10 are about 260 a day, so they can run above 2250; with 3000 they waited almost half of the time). `max_repos_per_tick` (6) and the daily cold cycle stay: they cost less than 1% of the allowance. The shipped example keeps its neutral defaults.

## [1.3.3]

> このバージョンの記載は現在英語のみです。翻訳は今後のバージョンで追加されます。

- **A2 ignores workflows that never run on the default branch:** when deciding whether a full run sample hides a workflow, the files of the clone whose `on:` has no `push`, `pull_request` or `schedule` for the branch (only `workflow_dispatch`, `release`, tag-only `push` without `branches`, or `workflow_call`) are no longer expected in the sample. `on:` is read with the standard library only (string, list, map, and the YAML `true` key); if it cannot be parsed the workflow counts as before. The workflow scan carries the new field `main_triggered` (`true`/`false`/`null`).

## [1.3.2]

> このバージョンの記載は現在英語のみです。翻訳は今後のバージョンで追加されます。

- **A2 shows `unknown` instead of green when its sample is full and inconclusive:** a repository whose list of runs is as long as the sample asked for (`runs_per_repo` / `cold_runs_per_repo` of the monitor, which the check did not see before) and whose clone has a workflow file with no run in that sample (or that has no clone) is listed as inconclusive, and A2 is `unknown` unless something is red. New option `sentinel.a2_full_sample_unknown` (default `true`; `false` = only informative as before). The page lists the repositories.
- **`profiles.example.json`:** a neutral batch-profiles template that matches `targets.example.json` and `ecosystems.example.json`. A test (and the release gate) validates it against those catalogues, not the maintainer's, and checks that every profile selects at least one target.
- **Clean-install check in `make_release`:** before anything is left in the output folder the zip is extracted into a new, empty temporary directory and, from there with `python -I`, every member must be present, every module must compile, `read_report.py --version` must run and the whole suite must pass; any gap fails the release.
- **Wording:** README and QUICKSTART in the 8 languages now say that the package writes nothing to GitHub on its own and that only `dispatch --go`, `dispatch --real` and `finalize --execute` (which you run) do.
- **A10 quota:** the share of the sentinel's per-tick call budget that A10 may use is now `sentinel.surface.budget_share` (default `0.5`, as before but configurable); the page shows "A10 paused for quota" with the allowance left and the one needed (`min_rate_remaining` x `min_rate_factor`) while the cold calls wait.

## [1.3.1]

> このバージョンの記載は現在英語のみです。翻訳は今後のバージョンで追加されます。

- **A run built on another commit is never offered for signing:** when `dispatch` could only find a recent run of another commit (`sha_matched` false), `finalize` now lists it as not ready with the reason and gives no signing command; an old batch without the field behaves as before. Tests with two concurrent runs of different commits.
- **`/api/data` goes through the same Host/Origin guard as the other routes** of the local server (DNS rebinding).

## [1.3.0]

> このバージョンの記載は現在英語のみです。翻訳は今後のバージョンで追加されます。

Made to be shared: eight languages, authorship and licence in every file, no private data, and nothing tied to one GitHub account.

- **8 languages** (en, es, de, fr, it, ja, zh, pt = European Portuguese) for the page, the command line tools, the launchers, the events, the reports and the error
  messages. `i18n.py` + `locales/<lang>.json` (one flat catalogue per language, standard library only, `t("key", name=value)` with a fallback to English). The language
  is `language` in `actions_monitor.json` (default: the system language, English if unsupported), a selector in the header of the page (remembered by the browser),
  `MONITOR_LANG` / `JUANENRAC_LANG`, or `--lang CODE` in every tool (it wins over the rest). Technical names, commands, paths and the markers that scripts read
  (`SKIP`, `DISPATCHED`, `READY`, `FAILED`, `Summary:`, `BUILD ONLY`, `WOULD DISPATCH`...) are never translated. Events in `events_monitor.jsonl` now carry a stable
  `code` (and `args`) next to the text, so nobody has to parse a language.
- A test checks that the 8 catalogues have exactly the same keys, none empty, the same `{placeholders}`, that every key used by the code and the page exists, and that no
  visible string in the code bypasses `t()`.
- README and QUICKSTART in the 8 languages (`README_<lang>.txt`, `QUICKSTART_<lang>.txt`); `README.txt` is now a short language chooser with the quick start.
- **Authorship and licence**: every source file carries "Copyright (C) 2026 JuanenRac (Electro Hobby 3D)" and "GPL-3.0-or-later - see LICENSE"; JSON data files carry
  `_author` / `_license`; `LICENSE` (GPL-3.0 text), `NOTICE` and `AUTHORS` travel in the zip. `make_release.py` refuses to build when a file lacks them, when private data
  would travel, when the locales differ, or when a launcher loses its executable bit.
- **Shareable**: `github_owner` in the configuration (default: the account of `gh`) replaces the constant that was spread over three modules; the ecosystem prefixes and the
  signing tools are data (`ecosystems.json`, neutral `ecosystems.example.json`; `"*"` = every repository; `"external": true` = only reported) and so are the targets (`targets.json`
  is the maintainer's real catalogue, `targets.example.json` the neutral one; `targets_file` / `ecosystems_file` choose them; keys that start with `_` are metadata).
  The example configuration is neutral. Nothing of this adds a call to the hot cycle.
- **The workspace is optional**: without local clones the monitor starts in a reduced mode (only what the GitHub API gives: no local signing queue, no audit report, no
  CHANGELOG scan) and says so on the page, in the report and at start, instead of stopping. `MONITOR_ROOT` / `MONITOR_AUDIT_DIR` / `MONITOR_SIGNED_DIR` and `signed_dir`
  were added next to the old names. The roadmap layer (A9) is optional too.
- Launchers: menus and messages come from `launcher_msg.py` (your language); comments in English; header on every file.
- Fix: `workspace_root()` no longer ends the monitor when the sentinel starts without a workspace.

## [1.2.0]

> このバージョンの記載は現在英語のみです。翻訳は今後のバージョンで追加されます。

What was missing and what else can be done on GitHub, all of it read only and local.

**Part A - what was missing**
- `ci_red.json` schema 2 is now a documented contract: `docs/CI_RED_SCHEMA.md` (shape, the one rule of "red", what is for the owner only). Nothing is
  published from the PC. Optional, explicit exports (never a commit or a push): `read_report.py --export-status DIR` writes ONLY the red list
  (`ci_status_public.json/.md`); `read_report.py --export-sign-queue FILE` (.json/.csv) writes the global signing queue with the local commands.
- Attestation: the signing queue shows whether the build has an attestation (existence by digest of the signed files, one lookup per entry, no signature
  check; switch `sentinel.surface.checks.attestation`). A missing one is a line in the report.
- More verified formats: HYDRA `hydra-sign` (`FILE.sig` = base64 Ed25519 over the bytes of the file, the pinned release key, read in blocks) is checked
  definitively; URTC `.imgsig` has its strict format checked (152 hex digits + LF; malformed = not valid) and stays "unknown" when well formed (the signed
  message also needs the build header, which the signed folder does not carry); ARMOR APKs are signed inside the APK by apksigner and stay "unknown".
- `HYDRA-UMC-OS` is labelled on purpose in `targets.json` (`"build_only": true` + `reason`): `plan` lists it under BUILD ONLY and it is no longer an orphan.
  The signing tools were not touched (its workflow takes other inputs and a different signature scheme).
- Fix: `ci_red.target_path` refused every Windows path written with backslashes (`C:\...`); only forward slashes were accepted.

**Part B - the A10 layer "Actions & releases surface"** (`surface.py`, new section of the tab, a switch and a threshold per check under `sentinel.surface`)
- Actions: workflows disabled by hand, schedules with no run in N days (only when the sample of runs covers the window), `uses:` not pinned by SHA
  (reusable workflows flagged apart), `permissions: write-all`, `pull_request_target` with a checkout of the PR, stuck concurrency queues, failures on only one
  OS of a matrix, artifact cost and retention, required status checks that are red or missing (GraphQL), `dispatch --profile release|nightly|hil` with a canary
  (the first target alone, the rest only if it is green) and a quota gate (`--min-rate`, fails closed). Profiles live in `profiles.json`.
- Releases: expected assets per kind of target (alert when a release was published incomplete), tag vs manifest vs CHANGELOG, GitHub Packages, forgotten drafts
  and pre-releases, `release_notes.py` (a DRAFT of notes from the commits since the last tag; it publishes nothing).
- Security: critical/high alerts by age with a ranking of repositories, coverage (a stack without CodeQL/Dependabot), secret scanning open vs resolved,
  Dependabot by priority (runtime major first, CI-only last).
- Issues and PRs: suggestion of `gh issue close` for build issues whose CI is green again (an event with the text; nothing is ever closed), overdue milestones,
  old human PRs, PRs that touch workflows or CODEOWNERS, the merge queue (approved with green checks). Stale board cards: PENDING (needs per-item reads and a threshold).
- Manifest vs evidence (maturity), 8-language README parity failures, Actions minutes per ecosystem in the header, the report and A7.
- `finalize --execute` now tells the running monitor (127.0.0.1) to refresh just the signed repositories and rewrite `ci_red.json` at once (`monitor_link.py`).
- Optional signed webhook receiver (`webhook.enabled`, off by default, 127.0.0.1 only, HMAC with a shared secret from the config, never a GitHub token).
- Cost: nothing in the hot cycle. Cold, spread over ticks and inside the hourly budget: 2 REST calls per repository per day, one GraphQL query per 15
  repositories per day, 3 for Packages, plus the jobs of red runs and the attestation lookups of the signing queue, and only while the allowance is above
  twice `min_rate_remaining`. The hot GraphQL pass asks for 3 more fields per node (alert dates, review decision, checks state): no extra call.
- The gate also compares `sentinel.surface` of the example file with the defaults and validates `profiles.json`.

## [1.1.1]

> このバージョンの記載は現在英語のみです。翻訳は今後のバージョンで追加されます。

- **Cross-platform:** the monitor and the batch tools work on Windows, macOS and Linux. Launchers `MONITOR_GITHUB_ACTIONS.sh`/`.command` and `BATCH_GITHUB_ACTIONS.sh`/`.command` (the zip keeps the executable permission and make_release rejects Windows line endings in them).
- New `platform_compat.py`: the command that starts a child tool (`py -3` on Windows, the current interpreter elsewhere), the text of the commands that `finalize` shows (cmd/PowerShell or POSIX quoting), UTF-8 console and a notice with the way to install `gh` on each system.
- New tests of the cross-platform part (Windows and POSIX simulated from any system).

## [1.1.0]

> このバージョンの記載は現在英語のみです。翻訳は今後のバージョンで追加されます。

Signature trust, a stable bridge to the dashboard, orphans and conventions in the batch tools, and a more useful page.

- Signature trust: `sigverify.py` (standard library, read only, no network) checks the signed folder `_firmados/<REPO>/release-<version>/` against the PUBLIC
  key each ecosystem pins (URTC `release_sign.py`, ARMOR helper `PACKAGE_PUBLIC_KEY`, HYDRA updater `RELEASES_PUBLIC_KEY`, or `sentinel.signature_pubkeys`).
  Every state now carries `signature_kind` (none | dev | release) and `signature_verified` (true | false | "unknown"); only a release signature that verifies
  (`trusted`) lowers the pending-signature alert, besides "published". A signature that does not verify keeps the alert and says so in the report.
  `sentinel.require_verified_signature` (default true; false = the 1.0.0 rule). Formats this module cannot check (.sig2, .hdr2, .imgsig, APK, hydra-sign) are
  "unknown", never "false". The build attestation still needs the network and stays with the signing tools.
- `ci_red.json` schema 2: per repository a `pending_sign` list (workflow, hours, state, signature_kind, signature_verified, last_build_at, url) next to the red
  workflows, plus `schema`, `pending_sign_repos` and the threshold; the format is documented in `ci_red.py` and is only ever extended.
- One definition of "last run on main" (`signstate.completed_runs`) shared by the red check, the green-without-release check and the target states.
- `ci_red.target_path` refuses D: paths, WSL/Git Bash forms of D: and drive/UNC paths that the running system cannot use; the tests simulate both systems
  and the whole suite now passes on Linux.
- `gha_dispatch_all.py plan` always ends with the section "Signature orphans" (green CI + known `*-build.yml` + no target); coverage is by repository AND workflow.
- Convention for targets (ecosystem prefix -> default signing tool, workflow in the known list); `targets.json` only holds the overrides and always wins.
  `hygiene --write-candidates` writes the proposed entries to `targets.candidates.json` (never applied by itself, never packaged).
- Page: clickable header counters "red on main" and "unsigned" (filter the repositories; the second one also focuses the signing queue), the signing queue
  with its commands and a copy button, repository panel with build / signed / published, signature kind and verification, and the suggested command;
  a header badge when a minutes budget reaches 80 % (red when exceeded); "yesterday vs today" also compares budget warnings and the lines of the report.

Not done: reading the build attestation / SBOM (network); `HYDRA-UMC-OS` has a build workflow but its signing tool does not support it yet (listed as an orphan).

## [1.0.0]

> このバージョンの記載は現在英語のみです。翻訳は今後のバージョンで追加されます。

First numbered version. What the package does:

- Monitor of GitHub Actions for the four ecosystems (local web page, run cache, stuck builds, build-failed/build-stuck issues).
- Sentinel layer A (read only, no AI needed): A1 stuck builds, A2 red CI (one criterion: last completed run of each workflow on the default
  branch), A3 CodeQL/Dependabot/secret alerts, A4 Dependabot pull requests, A5 releases (candidates, green builds without a release,
  pending signature), A6 hygiene, A7 consumption (minutes and API allowance), A8 audits and rounds, A9 roadmap boards.
- Explicit state of each build target: built_on_gha -> signed_local (none | dev | release) -> published, with `last_build_at`,
  `last_signed_at`, `signature_kind` and the real hours waiting; local batch and signed-folder records lower the pending-signature
  alert without waiting for GitHub.
- Signing queue of the day (`a5.sign_queue`): most urgent first, with the exact finalize command of each target.
- Budget of Actions minutes per ecosystem (`sentinel.minutes_budget`, empty by default): warning at 80 % in the report and as an event.
- Event feed (`events_monitor.jsonl`) and `ci_red.json` (repository -> red workflows + hours pending signature), written atomically.
- Batch tools: `gha_dispatch_all.py plan|dispatch|status|finalize|hygiene` with `--only` or `--ecosystem`, `plan --json`,
  `finalize --json`, one retry of a failed dispatch at the end of the batch, targets as data in `targets.json`.
- `read_report.py`: the report as plain text from the running monitor, without spending API quota.
- `make_release.py`: quality gate (unit tests, clean zip, complete example configuration, version/changelog agreement) and SHA256SUMS.

Not done in this version: verifying release signatures against the public key and the build attestation from the sentinel
(different signature formats per ecosystem; the attestation needs the network; the signing tools verify both before publishing).
