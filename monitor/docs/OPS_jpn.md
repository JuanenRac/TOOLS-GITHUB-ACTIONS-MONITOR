<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](OPS.md) | [🇪🇸 Español](OPS_spa.md) | [🇫🇷 Français](OPS_fra.md) | [🇮🇹 Italiano](OPS_ita.md) | [🇩🇪 Deutsch](OPS_deu.md) | [🇨🇳 简体中文](OPS_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](OPS_por.md)

# インストールの運用

数か月動かしっぱなしにするモニター (Complete エディション) のためのガイドです。完全なバックアップ、復元、定期バックアップ、cron が頼れる終了コードを持つ doctor、そしてアプライアンス (systemd または Docker) としての設定を扱います。Lite エディションにはこれらはありません。

## バックアップパッケージ

`python bin/monitor_cli.py backup create [FILE]` は `.zip` を 1 つ (フォーマット 2) 書き出し、所定の場所に置く前に検証します。`FILE` を省略すると、データフォルダの `backups` フォルダ (`ops.backup.dir`) に `ghamon-backup-<UTC 時刻>.zip` という名前で保存されます。モニターを止める必要はありません。データはストレージ (ファイルまたは SQLite) のアトミックな読み取りで取得し、書き込み中のデータベースを丸ごとコピーすることはありません。

| メンバー | 内容 |
|---|---|
| `dump.jsonl` | 各アカウント (設定、センチネルの状態、小さなドキュメント、イベント、分析、スコアのスナップショット) と、グローバルな記録 (ユーザーと閲覧できるアカウント。セッションは含まない) |
| `files.json` | 画面の設定とインストールの一覧 (`targets.json`、`ecosystems.json`、`profiles.json`、サイレンス) を無害化したもの。任意のモジュールのストアも、存在する場合は含まれます (`proposals.json`, `devices.json`) |
| `manifest.json` | フォーマット、製品のバージョン、スキーマ、件数、各メンバーのサイズと SHA-256 |

**絶対に含まれないもの:** GitHub や App のトークンと鍵、パスワード、`*_env` 変数の値 (名前のみ)、webhook のシークレット、AI プロバイダーの鍵、セッション、シークレットストアの内容。設定はホワイトリスト (設定画面が表示できるキーと同じもの) を通り、次にシークレットらしいキーやトークン・秘密鍵らしい文字列をすべて取り除く処理を通ります。`ops.backup.include_config` をオフにすると、設定と一覧は完全に除外されます。復元しても資格情報は戻りません。GitHub のログインを設定し直してください (復元後のチェックリストにも出ます)。

バックアップは所有者だけが読めます (モード 600)。パッケージは、頼まない限り暗号化されません。下を参照してください。

### 1 アカウントのパッケージ

`backup create --account ID [FILE]` は、1 つのアカウントだけのパッケージを書き出します。そのダンプ (設定も同じ方法で無害化) だけで、ユーザーもセッションも、インストールの設定や一覧も含みません。マニフェストには `scope: account` と記録されます。`backup verify` はそのアカウントだけを含むことを確認し、`backup restore FILE` はそのアカウントを復元します (`--account` は不要)。他のアカウント、ユーザー、復元先のファイルには触れず、そのアカウントがすでに存在して `--force` がない場合のみ拒否されます。1 つのアカウントを移したり復旧したりする方法です。

### バックアップの暗号化 (任意)

`ops.backup.encrypt` (1 回だけなら `--encrypt`) は、`ops.backup.key_env` が指す環境変数 (`--key-env NAME`) から取った鍵で、パッケージを AES-256-GCM で暗号化します。鍵は設定にならず、どこにも書かれず、コマンドラインにも現れません。任意のライブラリ `cryptography` が必要です (`pip install cryptography`。モニターの中核は標準ライブラリのみのままです)。ライブラリがない場合や、鍵が 12 文字未満の場合、バックアップは明確なメッセージとともに**拒否**され、何も書き込まれません。暗号化を頼んだのに平文で作られることも、より弱い方式で暗号化されることもありません。暗号化したファイルは `.enc` で終わり、`verify` と `restore` は同じ変数で開きます。鍵はファイルとは別に保管してください。鍵がなければ開けません。

## 検証・一覧・状態

- `backup verify FILE` はパッケージを読み直し、各サイズと SHA-256、件数を確認します。変更された 1 バイト、欠けたメンバー、マニフェストに載っていないメンバーが報告されます。`--deep` は一時フォルダに復元して結果も確認します。
- `backup list` はフォルダ内のバックアップを表示し、`backup status` は最後の正常なバックアップ、その経過時間、スケジュール、直近の失敗を表示します。
- 最初のフォーマット (2.1.0 より前に作成) のパッケージも、引き続き検証・復元できます。

## 復元

`python bin/monitor_cli.py backup restore FILE`: 先にモニターを停止してください (ポートで応答するモニターがある間、復元は拒否されます)。パッケージを検証してから、アカウントとファイルを書き込みます。

- すでにアカウントがあるストレージは、`--force` を付けない限り拒否されます (付けるとパッケージのアカウントが上書きされます。設定は**マージ**され、パッケージにないキーが削除されることはありません)。
- `--account ID` はそのアカウントだけを復元し、他のアカウントとグローバルなファイルはそのままです (そのアカウントが存在して `--force` がない場合のみ拒否)。
- `--to-dir DIR` はインストールに触れず、空のフォルダ (ファイルバックエンド) に復元します。バックアップを確認したり、別のマシンへ移したりする方法です。
- データフォルダに `ops/restore_report.json` を書き、残りの作業を表示します: GitHub のログインを設定し直す、パッケージが除いた設定を再設定する、スーパーバイザーが各アカウントを起動するようモニターを再起動する、doctor を実行する。

## 定期バックアップ

方法は 2 つあります。どちらか一方を使ってください。

1. モニター内: `ops.backup.enabled` (既定はオフ) は `ops.backup.interval_hours` ごとに専用スレッドでバックアップを作り、新しい `ops.backup.keep` 件を残し (削除されるのはバックアップ名のファイルだけ)、結果を `ops/backup_status.json` に記録します。失敗 (ディスク満杯、鍵なし) は記録され、情報パネルと doctor に表示されます。モニターを止めることはありません。
2. systemd: `deploy/github-actions-monitor-backup.service` と `deploy/github-actions-monitor-backup.timer` (下を参照)。

情報パネルには、モード (サービスまたはローカル)、最後の正常なバックアップ、スケジュール、適用中の保持期間、**今すぐバックアップ** ボタン (管理者、このコンピューターから) を持つ**運用**カードがあります。`GET /api/ops/status` が同じデータを返し、`POST /api/ops/backup` がバックアップを作成します。

## オンデマンドの削除

保持期間の削除は `retention.interval_hours` ごとに自動で実行されます。今すぐ実行するボタン (と `POST /api/ops/purge`) は、`ops.purge.enabled` をオンにするまで**存在しません** (既定はオフ)。リクエストは、`dry_run` に false を指定しない限りドライラン (適用中のポリシーと削除されるイベント数) で、実際の削除は `ops.purge.require_backup_hours` (既定 24。0 は確認しない) より新しい正常なバックアップがないと拒否されます。保持期間の監査と操作ログに記録が残ります。

## doctor と終了コード

`python bin/monitor_cli.py doctor [--strict] [--json]` (または `python bin/actions_monitor.py --doctor`) はインストールを確認します。何も変更せず、シークレットも表示しません。Complete エディションは通常のチェックの後に次を追加します。

| チェック | 見るもの |
|---|---|
| `volumes` | データ・ログ・バックアップのフォルダで、ファイルを実際に書き込み、読み、削除できる (root でマウントされた、または読み取り専用の Docker ボリュームはここで失敗) |
| `supervisor` | 動作中のモニター: スーパーバイザーと各更新サイクルの詳細な健全性 (何も起動しません) |
| `limits` | webhook のシークレットが設定済みで `ops.doctor.webhook_min_length` 文字以上であること (比較するのは長さのみ)、および保持ポリシー |
| `sqlite_hot` | 各 SQLite データベースを読み取り専用で開く: `quick_check` (既定) または `integrity_check` (`ops.doctor.sqlite_check` が deep)。`ops.doctor.sqlite_timeout_s` で打ち切り。停電後に壊れたファイルは失敗 |
| `backup_age` | 最後の正常なバックアップを `ops.doctor.backup_max_age_days` と比較 |
| `disk` | データボリュームの空き容量を `ops.doctor.min_free_mb` と比較 |
| `metrics` | Prometheus 出力がオンでモニターが動作中のとき、`/metrics` が応答する |
| `plugins` | `plugins.enabled` 時: 確認に通らなくなったプラグイン（鍵の失効、ファイル変更）と一時停止中のもの |

**終了コード (安定、cron 向け):** `0` すべて正常 (`--strict` なしなら警告があっても); `1` 少なくとも 1 つのチェックが失敗; `3` 警告のみで `--strict` (または `ops.doctor.strict_exit`); `4` doctor 自体を実行できなかった。これは doctor のコードで、`monitor_cli.py` の他のコマンドは自分のコードのままです。例: `0 * * * * python3 bin/monitor_cli.py doctor --strict --json > /var/lib/github-actions-monitor/doctor.json || true` とし、0 以外のコードで通知します。

## アプライアンスとして

**systemd** (コンテナなし): `deploy/github-actions-monitor.service` のコメントに従い、続いてバックアップ用ユニットとそのタイマーをインストールします。

```
install -m 644 deploy/github-actions-monitor-backup.service deploy/github-actions-monitor-backup.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now github-actions-monitor-backup.timer
systemctl list-timers github-actions-monitor-backup.timer
```

暗号化したバックアップにするには、`ops.backup.key_env` が指す変数を `/etc/github-actions-monitor/env` (モード 600) に入れます。タイマーは毎日 `backup create` を実行し、バックアップを作れなかったときの終了コードは 1 です。

**Docker:** `deploy/compose.yaml` は、データボリュームを失ってもバックアップが失われないよう、専用のボリューム (`/data/backups` の `monitor-backups`) に保存します。`docker compose exec monitor python bin/monitor_cli.py backup list` と `docker cp` でファイルを取り出し、停止したコンテナまたは `--to-dir` で復元します。TLS は `deploy/Caddyfile` の Caddy が更新します。

**アカウントを失わずに更新:** `backup create` → `backup verify FILE` → モニターを停止 → 製品フォルダを置き換え (`config/`、`data/`、`logs/`、`ai/` はあなたのもので保持されます) → `doctor` → 起動。問題が起きたら `backup restore FILE`。**きれいに削除:** ユニットを停止・無効化し、タイマーを削除してから製品フォルダを削除します。データを失ってよい場合のみ、`config/`、`data/` フォルダや Docker ボリュームも削除してください。

## 設定

すべて設定タブ (フォルダとファイル) と [SETTINGS_jpn.md](SETTINGS_jpn.md) にあります: `ops.backup.*` (enabled、dir、interval_hours、keep、include_config、compress_level、encrypt、key_env)、`ops.purge.*` (enabled、require_backup_hours)、`ops.doctor.*` (strict_exit、backup_max_age_days、min_free_mb、sqlite_check、sqlite_timeout_s、webhook_min_length)。すべてのスイッチはオフまたは保守的な値で始まり、セキュリティに関わるもの (定期バックアップ、設定の同梱、暗号化、削除) にはその印が付いています。

関連: [STORAGE_jpn.md](STORAGE_jpn.md) (バックエンドと保持期間)、[DEPLOYMENT_jpn.md](DEPLOYMENT_jpn.md) (サービス、コンテナ、TLS)、[CLI_jpn.md](CLI_jpn.md)。

## モニターは自分のメモリとスレッドを監視します

`selfwatch.interval_seconds`（60）ごとにモニターは自身の常駐メモリ、スレッド、プロセッサ使用量を読み取り、`/api/health` の `selfwatch`（`state`：`ok` または `high`）に表示します。メモリが `selfwatch.rss_warn_mb`（1024）を、スレッドが `selfwatch.threads_warn`（400）を超えると、握りつぶした失敗のカウンターに数値付きで一度だけ記録し（`high`）、解放できるものを解放し、通常に戻ったことも記録します。`selfwatch.enabled` でオフにできます。`selfwatch.rss_warn_mb` はコンテナーの上限より少し小さくしてください。CI は 1 プロセッサ・512 MB のコンテナーで 120 ワークフローのアカウントを使ってモニターを動かします（`tools/limits_check.py`）。
