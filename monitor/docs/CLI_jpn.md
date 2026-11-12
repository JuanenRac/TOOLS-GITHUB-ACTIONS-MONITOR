<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI.md) | [🇪🇸 Español](CLI_spa.md) | [🇫🇷 Français](CLI_fra.md) | [🇮🇹 Italiano](CLI_ita.md) | [🇩🇪 Deutsch](CLI_deu.md) | [🇨🇳 简体中文](CLI_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](CLI_por.md)

# モニターのクライアントとしてのコマンドライン

`python monitor_cli.py コマンド` は、実行中のモニターが把握している内容を問い合わせ（`127.0.0.1`、または `--url` / `MONITOR_URL` のアドレスへの `GET`）、表示します。ページが GitHub に対して行う処理を繰り返さず、GitHub には一切書き込まず、設定も変更しません。従来のツール（`read_report.py`、`--doctor`、`gha_dispatch_all.py`）はそのまま使えます。

## コマンド

| コマンド | 内容 | Lite |
|---|---|---|
| `status` | バージョン、エディション、アカウント、リポジトリ、実行中と失敗、割り当て | 可 |
| `health`（または `check`） | 重い読み取りの前の簡易確認：モニターに接続できるか、このクライアントを受け付けるか、アカウントの GitHub ログインが応答するか | 可 |
| `doctor` | この環境に対する `--doctor` の検査（モニターが動いていなくても可） | 可 |
| `accounts` | スーパーバイザーのアカウント一覧（複数アカウント時のみ） | 不可 |
| `alerts` | すべての番人のアラートを 1 つの一覧で：`--sentinel ci\|collab`、`--level info\|warning\|error`、`--muted show\|hide\|only` | 不可 |
| `live` | Webhook 受信の状態と直近のイベント | 不可 |

全コマンド共通のオプション：`--json`（応答を 1 つの JSON 文書で：`{"ok", "exit", "data"}`）、`--account ID`、`--url URL`、`--lite`（ポート 8766）、`--timeout 秒`（1〜60）、`--lang コード`。ネットワークモードではアクセストークンを、モニター自身が読む環境変数 `MONITOR_ACCESS_TOKEN` に設定します(`MONITOR_TOKEN` は別名として受け付けます。`--token TOKEN` は最後の手段で、オプションはプロセス一覧に表示されるためです)。優先順位は `MONITOR_ACCESS_TOKEN`、`MONITOR_TOKEN`、`--token` の順です。ヘッダー `X-Monitor-Access` で送られ、アドレスや画面には出ません。別のコンピューターへの暗号化されていない `http` の `--url` では stderr に警告を出します(トークンと応答が平文で送られるため)。管理下にないネットワークでは `https` を使ってください。

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

## 例

```
python monitor_cli.py health && python monitor_cli.py alerts --fail-on error
python monitor_cli.py alerts --sentinel collab --level warning --json
python monitor_cli.py status --account org-acme
MONITOR_URL=http://192.168.0.20:8765 MONITOR_ACCESS_TOKEN=... python monitor_cli.py health --json
```

`health` は 3 つを区別します：モニターが応答しない（2）、GitHub ログインが失敗（3）、割り当て切れまたは GitHub に接続できない（4）。最初の読み取りが終わっていないモニターは、空の数字ではなくそのことを伝えます（4）。

## Lite 版

`python monitor_cli.py status --lite`、`doctor --lite`、`health --lite` はポート 8766 と通信します。アカウント、番人、Webhook 受信が必要なコマンドは終了コード 1 で拒否されます。Lite 版にはアカウントもアラート API もありません。
