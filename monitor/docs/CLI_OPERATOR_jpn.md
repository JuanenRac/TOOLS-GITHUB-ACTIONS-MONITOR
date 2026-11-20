<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI_OPERATOR.md) | [🇪🇸 Español](CLI_OPERATOR_spa.md) | [🇫🇷 Français](CLI_OPERATOR_fra.md) | [🇮🇹 Italiano](CLI_OPERATOR_ita.md) | [🇩🇪 Deutsch](CLI_OPERATOR_deu.md) | [🇨🇳 简体中文](CLI_OPERATOR_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](CLI_OPERATOR_por.md)

# オペレーター向けコマンドライン

`monitor_cli.py` の基本は [CLI_jpn.md](CLI_jpn.md) にあります。このページは、ターミナルで作業する方のためのものです。応答の書き方（`--format`）、監視の仕方（`watch`）、コマンドの補完（`completions`）、終了コード、テレビ用のアドレス（`kiosk`）を説明します。ここにあるものはすべて、このコンピューターのモニター（または `--url` で指定したモニター）の API を読むだけで、GitHub には何も書き込まず、クォータも消費しません。

## 形式：`--format`

| 形式 | 得られるもの |
|---|---|
| `text` | 各コマンドが従来から書いてきたもの。既定です。 |
| `table` | ターミナルの幅に収まる列にしたレコード（日本語と中国語の文字は2セル分として数えます）。色は付かないので `NO_COLOR` は尊重されます。 |
| `plain` | 1行に1レコード、フィールドはタブ区切り、ヘッダーなし。`grep`、`cut`、`awk` 向けです。テキスト内のタブや改行は空白になります。 |
| `json` | ドキュメント `{"ok", "exit", "data"}`。`--json` と同じです。 |
| `ndjson` | 1行に1つの JSON オブジェクト、レコードごとに1つ（アラート、アカウント、リポジトリ、イベント）。1つの内容だけを返すコマンド（`status`、`health`）は1行になります。 |

`--format` は `--json` より優先され、両方とも設定 `cli.default_format`（既定は `text`）より優先されます。3つの構造化形式は `--json` と同じドキュメントから作られるため、食い違うことはありません。空のリストは `ndjson` と `plain` では何も出力しません。

## `watch`：同じ読み取りを繰り返す

```
python bin/monitor_cli.py watch status
python bin/monitor_cli.py watch alerts --interval 10 --format table
python bin/monitor_cli.py watch alerts --exit-on-change --format ndjson
```

`watch status|alerts` はコマンドの読み取りを繰り返します。読むのはモニターの API であり GitHub ではないので、短い間隔でもクォータは消費されません。オプション：

- `--interval 秒`：2回の読み取りの間隔。下限は設定 `cli.watch.min_interval_seconds`（既定は2）で、それより短い間隔はこの値に引き上げられます。`--interval` がない場合の間隔は `cli.watch.default_interval_seconds`（5）です。
- `--once`：1回読み取って終了（終了コードはコマンドのものです）。
- `--exit-on-change`：監視している内容が最初の読み取り時と変わると、ループは終了コード **6** で終わります（アラートの集合、またはステータスの数値）。時計が進むだけでは変化とみなしません。このオプションがなければ、コード6は現れません。
- `--no-clear`：読み取りの間に画面を消さない（画面を消すのはターミナル上で、かつ `text` と `table` のときだけです）。
- 読み取れないモニターは、そのたびに長くなる間隔（間隔を倍にし、最大1分）で再試行され、エラーは標準エラー出力に出ます。**Ctrl-C** でループは終了コード0で終わります。

## `completions`：コマンドの補完

```
python bin/monitor_cli.py completions bash > ~/.local/share/bash-completion/completions/monitor_cli.py
python bin/monitor_cli.py completions zsh  > "${fpath[1]}/_monitor_cli"
python bin/monitor_cli.py completions fish > ~/.config/fish/completions/monitor_cli.py.fish
python bin/monitor_cli.py completions powershell | Out-String | Invoke-Expression
```

スクリプトはコマンドラインの実際のパーサーから作られるため、存在するコマンド、語、オプションをそのまま提示します。新しいオプションを忘れることはなく、テストが両者を比較します。このコマンドは**出力するだけ**で、あなたのファイルを編集せず、モニターも不要です。出力は、上のようにお使いのシェルが補完を読み込む場所に置いてください。

## 終了コード

| コード | 意味 |
|---|---|
| 0 | 正常（`watch` での Ctrl-C も含む） |
| 1 | コマンドの使い方の誤り |
| 2 | モニターに接続できない |
| 3 | モニターまたは GitHub が資格情報を拒否した |
| 4 | モニターは応答するが劣化している（オフライン、クォータ切れ、まだデータなし）、または応答を読み取れない |
| 5 | `alerts --fail-on レベル` がそのレベル以上のアラートを見つけた |
| 6 | `watch --exit-on-change` が変化を検出した（このオプションを付けたときだけ） |

0〜5 は [CLI_jpn.md](CLI_jpn.md) のコードと同じです。この表とコードが一致していることをテストが保っています。

## `jq` の例

これらの例は、応答の安定した形に含まれるフィールドだけを使い、（`jq` がインストールされていれば）テストが偽のモニターに対して実行します。

```
monitor_cli.py alerts --json | jq -r '.data.alerts[] | select(.level=="critical") | .repo'
monitor_cli.py alerts --format ndjson | jq -r '.code'
monitor_cli.py status --json | jq '.data.red_workflows'
monitor_cli.py team --json | jq -r '.data.ranking[] | .repo'
```

## `kiosk`：テレビや壁面用のアドレス

`monitor_cli.py kiosk [ops|team|release|quiet]` は、誰も触れない画面向けのモニターのアドレスを出力します。[KIOSK_jpn.md](KIOSK_jpn.md) を参照してください。

## 設定

| 設定 | 既定 | 意味 |
|---|---|---|
| `cli.default_format` | `text` | `--format` も `--json` もないときの形式：`text`、`table`、`plain`、`json`、`ndjson` |
| `cli.watch.min_interval_seconds` | 2 | `watch` の最短の間隔（1〜3600） |
| `cli.watch.default_interval_seconds` | 5 | `--interval` がないときの `watch` の間隔（1〜3600） |

## このバージョンでしないこと

- `completions` に `--install` はありません。ユーザーのファイルには決して書き込みません。
- `proposals` コマンドはありません。モニターには、操作の対象となる提案用のルートがまだありません。

## `metrics`：cron とメール向けの数値

`monitor_cli.py metrics` はモニターの数値を 1 行に 1 つの `名前=値` として、決まった順序で、標準出力にほかの文字を混ぜずに書きます：`repos`、`active`、`queued`、`failures_24h`、`successes_24h`、`red_workflows`、`alerts`、`alerts_info`、`alerts_warning`、`alerts_error`、`alerts_critical`、`allowance_remaining`、`allowance_limit`、`offline`。わからない数値は 0 として書かず省きます。読むのはモニターだけで、GitHub には問い合わせません。

`--if-problem` を付けると、赤いワークフローがなく `--fail-on`（既定は error）以上のアラートもないときは何も書かず 0 で終了し、あるときは数値を書いて 5 で終了します。cron は出力があればメールを送るので、次の 1 行は問題がある日だけメールを送ります：`*/15 * * * * py -3 /opt/monitor/bin/monitor_cli.py metrics --if-problem`。モニターに届かないときは沈黙せず、エラーは標準エラー出力に出て終了コードは 2 です。
