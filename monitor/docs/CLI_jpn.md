<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI.md) | [🇪🇸 Español](CLI_spa.md) | [🇫🇷 Français](CLI_fra.md) | [🇮🇹 Italiano](CLI_ita.md) | [🇩🇪 Deutsch](CLI_deu.md) | [🇨🇳 简体中文](CLI_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](CLI_por.md)

# モニターのクライアントとしてのコマンドライン

`python bin/monitor_cli.py コマンド` は、実行中のモニターが把握している内容を問い合わせ（`127.0.0.1`、または `--url` / `MONITOR_URL` のアドレスへの `GET`）、表示します。ページが GitHub に対して行う処理を繰り返さず、GitHub には一切書き込まず、設定も変更しません。従来のツール（`bin/read_report.py`、`--doctor`、`bin/gha_dispatch_all.py`）はそのまま使えます。

## コマンド

| コマンド | 内容 | Lite |
|---|---|---|
| `status` | バージョン、エディション、アカウント、リポジトリ、実行中と失敗、割り当て | 可 |
| `health`（または `check`） | 重い読み取りの前の簡易確認：モニターに接続できるか、このクライアントを受け付けるか、アカウントの GitHub ログインが応答するか | 可 |
| `doctor` | この環境に対する `--doctor` の検査（モニターが動いていなくても可） | 可 |
| `backup` | インストール全体の完全バックアップ（モニターが動いていなくても可）：`backup create [FILE] [--account ID]`、`verify FILE [--deep]`、`restore FILE [--account ID] [--to-dir DIR] [--force]`、`status`、`list`。`--encrypt` と `--key-env NAME` で暗号化（任意のライブラリ）。[OPS_jpn.md](OPS_jpn.md) を参照 | 不可 |
| `accounts` | スーパーバイザーのアカウント一覧（複数アカウント時のみ） | 不可 |
| `alerts` | すべての番人のアラートを 1 つの一覧で：`--sentinel ci\|collab\|security\|supply\|delivery`、`--level info\|warning\|error`、`--muted show\|hide\|only`；`--since 90m|24h|7d|2w` はその期間のどこかで開いていたものを、閉じたものも含めて一覧にします（モニターが動作中に保持する履歴から。アラートは 10 分間見えなくなると閉じたと数えます） | 不可 |
| `proposals` | AI が提案した操作（`ai.actions.enabled`）：`proposals list`、`show ID`、`approve ID`、`reject ID`、`execute ID`（ID は短縮できます）。`approve` と `reject` は決定を記録するだけです。`execute` はページと同じ入口で実行し、`ai.actions.execute` が必要で、`ai.actions.require_approval` がオンなら先に承認が必要です。承認・却下・実行はこのコンピューターからのみ可能です 利用者が1人の場合、`approve` には `--code` とハッシュの先頭8文字が必要です。複数の場合はページの自分のセッションで承認します（2人）。 | 不可 |
| `score` | アカウントのスコア：数値、文字評価、傾向、要素、カバレッジ、リポジトリ別の内訳。`--compare` で期間の履歴と比較します | 不可 |
| `compare` | 今の期間と直前の期間の比較：数値とその変化・方向、悪化または改善したもの。`--window 7\|30d`、`--days all\|workdays\|weekend`、`--baseline previous\|year_ago`、`--format table\|json\|ndjson\|csv`。数値のデータが少ないと終了コード 4、`--fail-on` 指定で悪化があれば 5。他のコマンドでの `--format csv` は誤用（終了コード 1） | 不可 |
| `api` | クライアント向けの読み取りAPI:`api openapi` は固定された各ルートの OpenAPI 文書を出力し(ファイルにリダイレクトできます)、`api me` はモニターがこのクライアントを何者と見ているか(モード、ユーザー、ロール、セッションができること、契約のバージョン)を示します。`api.v1_enabled` が閉じているモニターはそう伝えます。`api contract-check` はクライアント向けの契約スイートをそれに対して実行します(検査が失敗すると終了コード4) | 不可 |
| `team` | リポジトリの健全性を、人の手が必要なものから順に表示します。`--severity warn\|bad` で悪いものだけに絞り、`--repo owner/name` で 1 件の詳細を表示します | 不可 |
| `live` | Webhook 受信の状態と直近のイベント | 不可 |
| `ai` | `ai models [--refresh]` は AI プロバイダーのモデルを各モデルのデータとともに一覧表示します。`ai test --provider 名前 --model 名前` は合成テキストで 1 つを試します (遅延、トークン、推定コスト)。`ai doctor` は AI が応答しない理由をキーを表示せずに説明します | 不可 |
| `lessons` | この CI の失敗が教えたこと:`lessons list`、`lessons brief --repo NAME`(push の前に読む)、`lessons failures`、`lessons close` | 不可 |
| `briefs` | AI ツールが読むタブごとのブリーフ:`briefs index`、`briefs show TAB`、`briefs all` | 可 |
| `docs` | このバージョンのガイドをインストール先から読み取ります（モニター不要）: `docs list` はタイトル付きで一覧し、`docs show NAME` は `--lang` の言語で 1 件を表示します | いいえ |
| `screens` | ページの「画面」メニュー:`screens list`(画面の種類と開けるかどうか)と `screens urls`(キオスクのコマンドにそのまま使える完全なアドレス) | 不可 |
| `keyring` | 署名できる公開鍵: `keyring list`、`add`（`--key-id`、`--public-key`、`--key-scope`、`--expires`）、`revoke --key-id`、`verify --document FILE`。モニター不要、秘密鍵は拒否 | いいえ |
| `verify-release` | ダウンロードしたリリースファイルのフォルダーをネットワークなしで SHA256SUMS と署名により確認: `verify-release --folder DIR`。信頼できない場合は終了コード 4 ほかに `--installed`（部品表とこのインストールの比較）、`--attestations`、`--fetch`（`ops.verify_release.fetch` が必要）。`doctor --verify-release DIR` はインストールを確認し、`keyring check-rotation --document FILE` は新しい鍵の告知を確認します。 | いいえ |
| `toolbox` | モニターを起動せずにこのコンピューター上で動く運用者向けの小さなツール：`toolbox limits [N]`（設定と上限の比較）、`toolbox workspaces`（ワークスペースと使用中のもの）、`toolbox ledger [--force]`（送信済み通知の台帳。`--force` で消去）、`toolbox summary`（種類・リポジトリ・日別のイベント数）、`toolbox export-events FILE`（名前の末尾に応じて jsonl、csv、parquet、duckdb でイベントを書き出し。parquet と duckdb は各パッケージが必要で、ファイルは新規であること） | いいえ |
| `credential` | すべてが動いたまま、1つのアカウントの GitHub ログインを差し替える:`credential replace\|reload [--account ID] [--new-token-file FILE\|-]`。トークンは表示しません | 不可 |
| `install-skill` | モニターのスキル(`internal` または `external`)を、AI ツールがスキルを読むフォルダーにコピーします:`install-skill external --dest FOLDER`。モニターが動いている必要はありません | 不可 |
| `gh-token` | ツールの読み取りが GitHub App の割り当てを使うよう、1時間有効な GitHub App のインストールトークンを出力します(`github_app.share_reads` がオンのときのみ)。`--json` なしで実行してください | 不可 |
| `watch` | 同じ読み取りを繰り返します（`watch status\|alerts`、`--interval`、`--once`、`--exit-on-change`）。[CLI_OPERATOR_jpn.md](CLI_OPERATOR_jpn.md) を参照 | 不可 |
| `completions` | `bash`、`zsh`、`fish`、`powershell` の補完スクリプト。実際のパーサーから作られ、出力するだけです | 不可 |
| `kiosk` | テレビや壁面向けのモニターのアドレス（`ops`、`team`、`release`、`quiet`）。[KIOSK_jpn.md](KIOSK_jpn.md) を参照 | 不可 |
| `metrics` | cron とメール向けに数値を `名前=値` の行で出力します。`--if-problem` を付けると問題がないときは何も出力しません。[CLI_OPERATOR.md](CLI_OPERATOR.md) を参照 | いいえ |
| `posture` | リポジトリと組織の体制、読み取り専用(`posture status|matrix|check --repo-name`)。[POSTURE.md](POSTURE_jpn.md) を参照 | 不可 |
| `external-ci` | 外部CIソース、読み取り専用(`external-ci list|status|probe --source`)。[EXTERNAL_CI.md](EXTERNAL_CI_jpn.md) を参照 | 不可 |
| `plugin` | プラグイン: `plugin list|validate|pack|verify|init|install|enable|disable|uninstall|audit`。参照: [PLUGINS.md](PLUGINS_jpn.md) | 不可 |

全コマンド共通のオプション：`--json`（応答を 1 つの JSON 文書で：`{"ok", "exit", "data"}`）、`--account ID`、`--url URL`、`--lite`（ポート 8766）、`--timeout 秒`（1〜60）、`--lang コード`。ネットワークモードではアクセストークンを、モニター自身が読む環境変数 `MONITOR_ACCESS_TOKEN` に設定します(`MONITOR_TOKEN` は別名として受け付けます。`--token TOKEN` は最後の手段で、オプションはプロセス一覧に表示されるためです)。優先順位は `MONITOR_ACCESS_TOKEN`、`MONITOR_TOKEN`、`--token` の順です。ヘッダー `X-Monitor-Access` で送られ、アドレスや画面には出ません。別のコンピューターへの暗号化されていない `http` の `--url` では stderr に警告を出します(トークンと応答が平文で送られるため)。管理下にないネットワークでは `https` を使ってください。

どのコマンドも `--format text|table|plain|json|ndjson` を受け付けます（`--json` は `--format json`）。[CLI_OPERATOR_jpn.md](CLI_OPERATOR_jpn.md) を参照。

コマンドラインは、クライアント向け読み取りAPIのクライアントです。契約で固定されたルート(`docs/schemas/api_contract.json`)はまず `/api/v1/` に問い合わせ、モニターがそこで404を返した場合(APIが閉じている。`api.v1_enabled`)は従来のルートに問い合わせ、以後プレフィックスを試しません。どちらの経路でも文書は同じなので、どのコマンドの出力も変わりません。`cli.prefer_v1`(既定でオン)で無効にでき、環境変数 `MONITOR_CLI_PREFER_V1`(`0` または `1`)が優先されます。契約で固定されていないルートは常に従来の方法で問い合わせます。

人向けに書かれる時刻（`Last read` 行、ミュート、ログ、レポート、通知）は、このコンピューターのゾーンを使い、その名前と UTC 時刻を併記します（`11:43:07 CET (10:43:07 UTC)`）。別のゾーンは `display.timezone`（`local`、`utc`、または `Europe/Madrid` のような名前）で選びます。環境変数 `MONITOR_TIMEZONE` はファイルより優先されます。`--json` は UTC のままで `updated_local` を追加します。

## 終了コード（固定）

| コード | 意味 |
|---|---|
| 0 | 正常 |
| 1 | コマンドの使い方が誤り（完全版が必要なコマンドに `--lite` を付けた場合も） |
| 2 | モニターに接続できない |
| 3 | モニターがこのクライアントを拒否、またはアカウントの GitHub ログインが失敗・期限切れ（資格情報の問題で、割り当て切れではありません） |
| 4 | モニターは応答するが劣化している：オフライン、割り当て切れ、まだデータなし、そのエンドポイントがない、または JSON でない応答 |
| 5 | `alerts --fail-on レベル` がそのレベル以上の未解決アラートを見つけた（ミュート中は数えません） |
| 6 | `watch --exit-on-change` が変化を検出した（このオプションを付けたときだけ）。[CLI_OPERATOR_jpn.md](CLI_OPERATOR_jpn.md) を参照 |

すべてのエラーには `help` が付きます。次の手順を示す 1 文で、読むべきガイドの名前（`docs show FIRST_STEPS`）が入ることもあります。テキスト形式では `ヘルプ:` で始まる最後の行、`--json` では `error` の隣の `help` フィールドです: `{"ok": false, "exit": 2, "error": "...", "help": "..."}`。

## 例

```
python bin/monitor_cli.py health && python bin/monitor_cli.py alerts --fail-on error
python bin/monitor_cli.py alerts --sentinel collab --level warning --json
python bin/monitor_cli.py status --account org-acme
MONITOR_URL=http://192.168.0.20:8765 MONITOR_ACCESS_TOKEN=... python bin/monitor_cli.py health --json
```

`health` は 3 つを区別します：モニターが応答しない（2）、GitHub ログインが失敗（3）、割り当て切れまたは GitHub に接続できない（4）。最初の読み取りが終わっていないモニターは、空の数字ではなくそのことを伝えます（4）。

## Lite 版

`python bin/monitor_cli.py status --lite`、`doctor --lite`、`health --lite` はポート 8766 と通信します。アカウント、番人、Webhook 受信が必要なコマンドは終了コード 1 で拒否されます。Lite 版にはアカウントもアラート API もありません。

## `ai-hook`: モニターが見ているものを AI ツールに伝える

`python bin/monitor_cli.py ai-hook install|status|uninstall [--assistant|--cursor|--generic] [--scope project|user] [--project-dir DIR] [--dry-run] [--json]` は、モニターが動いていなくても使えます。AI ツールのフック設定に連携スクリプト `bin/ai_hook.py` を追加・表示・削除します (AI 向けアラートのガイドを参照)。設定ファイルはマージされ、コピーが保存され、`--json` の出力は純粋な ASCII です。既定の動作は `status` です。

## コマンドラインでのアクセストークン

ネットワークモードでは、トークンは `MONITOR_ACCESS_TOKEN`、次に `MONITOR_TOKEN`、次に `--token-file FILE` の 1 行目から読み取り (このファイルは自分だけが読めるようにしてください。ファイルモードのあるシステムでは、他のユーザーが読めると警告します)、最後に `--token` から読み取ります。`--token` はプロセス一覧に表示されるため、stderr に警告を出します。

## 保存用のツール

`python tools/migrate_storage.py` は状態をファイルとSQLiteの間で移し、`python tools/backup_storage.py` はどちらのバックアップも作成・検証・復元します(どちらも [STORAGE_jpn.md](STORAGE_jpn.md) で説明しています)。`--doctor` にはそのための2つの検査(保存と保持)があります。

## バッチディスパッチャー:ワークフローの入力

`python bin/gha_dispatch_all.py plan --inputs` は、各ターゲットの下に、手動で起動するときにそのワークフローが要求する入力(名前、型、必須か任意か、既定値、選択肢、説明)も一覧表示します。入力はローカルクローンの `origin/main` にあるワークフローファイルから `git show` で読み取ります。何も起動せず、何も送信せず、`gh` も呼び出しません。`--json` は各行に `inputs` リストを追加します。ファイルが `origin/main` にない場合や、リーダーが知らない書式(フロースタイルの `inputs: {…}`)の場合は `null`、ワークフローが入力を要求しない場合は `[]` です。

## バックアップと doctor

`backup` と `doctor` はインストールのフォルダを対象に動作するため、モニターが動いている必要はありません。`doctor` は、すべて正常なら (警告があっても) `0`、チェックが失敗したら `1`、警告のみで `--strict` (または `ops.doctor.strict_exit`) がオンなら `3`、doctor 自体を実行できなければ `4` で終了します。これは doctor のコードで、他のコマンドは上の終了コードのままです。`backup` は完了すれば `0`、拒否された場合やパッケージの検証に失敗した場合は `1` で終了します。チェック、復元、定期バックアップは [OPS_jpn.md](OPS_jpn.md) のガイドにあります。 doctor には `compare_window`（2 期間の比較が、必要とし保持する履歴で期間 2 つ分さかのぼれるか）と `etag`（ここで動いているモニターで条件付き読み取りが 304 で返された割合と、GitHub の応答が ETag なしで届いていないか）もあります。

## リポジトリの識別と複数の所有者

コマンドライン：`identity status`、`identity plan`、`identity apply`。

```
python bin/monitor_cli.py identity plan
```

## コマンド: actions, runner-hook

```
python bin/monitor_cli.py actions proposals
python bin/monitor_cli.py runner-hook started
```

[COLLABORATION_jpn.md](COLLABORATION_jpn.md)
