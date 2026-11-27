<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLIANCE.md) | [🇪🇸 Español](COMPLIANCE_spa.md) | [🇫🇷 Français](COMPLIANCE_fra.md) | [🇮🇹 Italiano](COMPLIANCE_ita.md) | [🇩🇪 Deutsch](COMPLIANCE_deu.md) | [🇨🇳 简体中文](COMPLIANCE_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](COMPLIANCE_por.md)

# コンプライアンス: 自分のインストールについて示せること

ここにあるものはすべて初期状態でオフで、完全版でのみ動作します。ただし二つの制限はモニターの全プロセスに適用されます。いずれも認証ではありません。

## 厳格な読み取り専用モード

`security.read_only_strict` (オフ)。オンにすると、エディションや他の設定にかかわらず GitHub には何も書き込みません。`gh` の読み取りコマンドだけを実行し (読み取りと分からないものは拒否)、`git push` と `act` は行わず、GitHub API への GET と HEAD 以外のリクエストも出しません。Python の監査フックで、起動されるすべてのプログラムを見てすべての部品の下層で強制します。変更はモニターのコンピューターからのみで、緩めるには再起動が必要です。有効かどうかは「このアプリについて」と `/api/about` (`restrictions`) で分かります。

## ネットワークポリシー

`security.egress_policy`: `default`、`github_only`、`none`。`security.egress_allow` でホスト (`名前`、`*.名前`、アドレス) または `program:名前` を追加します。`github_only` ではモニターのプロセスは `api.github.com`、`uploads.github.com`、`GH_HOST` のホスト (GitHub Enterprise)、許可した先だけに接続します。`none` ではこのコンピューターのみで、`gh` も起動しません。自分でネットワークを使うプログラム (ネットワーク系の `git`、`apprise`、`curl`、`docker`、シークレット保管ツール) は起動しません。拒否された接続は設定名を含むエラーになります。設定済みの宛先がポリシー外だと `python bin/monitor_cli.py doctor` が失敗し、`doctor --egress` は全宛先を一覧します。ファイアウォールではなく、他のプログラムの動作は制御しません。

## コンプライアンスレポート

`python bin/monitor_cli.py compliance report` (`--json` も可)、`GET /api/compliance/report` (管理者)、セキュリティタブ末尾の枠で表示します。各行は**確認済み** (モニターが実物を確認) か**設定値** (設定がそう述べている) かを示します。内容はバージョンとサポート、エディション、認証と ID プロバイダー、ネットワークモードと TLS、二つの制限と送信先、保持と訴訟ホールド、操作ログと連鎖、バックアップと暗号化、保存データの暗号化 (なし)、ストレージ、プラグイン、配置形態、プロファイルです。秘密、パス、名前は含みません。`GET /api/compliance/state` は制限、保持の表、エクスポート状態を返します。

## 保持と訴訟ホールド

イベント、分析、スコアは従来の設定 (`retention.events_days`、`retention.analytics_days`、`retention.mode`) を使います。その他のカテゴリは日数を指定しない限り無期限です: `retention.audit_days` (操作ログのローテーション済みファイル単位)、`retention.reports_days` (各アカウントの最新レポートは残る)、`retention.ai_log_days`、`retention.backups_days` (最新のコピーは残る)。削除のたびに操作ログに記録します。`retention.legal_hold` はすべての削除を止めます (イベント、分析、スコア、レポート、コピー、フィードとプロンプト記録の切り詰め、ログのローテーションと消去)。AI の提案は自然に失効し、ペアリングした端末は外すまで残ります。このバージョンは事後分析、インシデント、メモを保存しません。

## 操作ログの署名付きチェックポイント

`audit_checkpoints.enabled` (オフ) はインストール固有の鍵で連鎖に署名します (HMAC-SHA256)。鍵は `config/audit_checkpoint.key`、分離するなら `MONITOR_AUDIT_KEY_FILE` で指定したファイルです。最初の行と、その後は少なくとも 1 時間ごと・1000 行ごとにチェックポイントを作り、アンカーにも署名します。末尾の切り詰めの後に新しい行が書かれると、その事実が連鎖に記録されます。`python bin/monitor_cli.py audit verify` (`--audit-from N`)、`audit checkpoint`、`audit purge --older-than-days N` (`--dry-run`) があり、purge はローテーション済みファイルを丸ごと削除して連鎖の続きに署名します。鍵を読める者は署名できるので、ログを書ける者から離してください。

## 操作ログのエクスポート

`audit_export.enabled` (オフ) と `audit_export.target`: `file` (`path`、`max_mb` でローテーション)、`syslog` (`host`、`port` 6514、TLS 付き TCP の RFC 5424、`ca_file`)、`http` (`url`、JSON 行を POST、トークンは `token_env` の変数)。プライベートアドレスには `audit_export.allow_private_targets` が必要です。ログ自体が待ち行列で、宛先が受け取らなかった分はそこで待ちます。`spool_mb` を超えると doctor が `system.audit_export_lag` を報告し、送る前にローテーションで消えた行は損失として数えます。`python bin/monitor_cli.py audit export` で今すぐ一巡します。このコンピューター上の受信側でのみ試験し、実際の syslog や SIEM 製品では未確認です。

## サポートするバージョン

サポートするのは最新の公開バージョンだけで、長期サポートの系列はありません。新しい版を知っていると doctor (`compliance_support`) が警告します。

## 堅牢化の根拠

`[IMP]` はこのリポジトリのテストが対象の制御を実行していること、`[PAR]` は一部のみで、行に不足分を示します。一覧は `schemas/controls.json` で、表とテストの一致はテストが確認します。

| 制御 | 状態 | 内容 |
|---|---|---|
| `sqlite_contention` | [IMP] | 複数プロセスによる 1 つのデータベースへの書き込み |
| `storage_migrations` | [IMP] | ストレージの移行 |
| `retention_by_category` | [IMP] | カテゴリ別保持と訴訟ホールド |
| `incoming_webhook` | [IMP] | 受信 webhook: 署名・サイズ・時刻 |
| `metrics_labels` | [IMP] | /metrics のラベル |
| `timezone` | [IMP] | タイムゾーンと夏時間 |
| `read_only_strict` | [IMP] | 厳格な読み取り専用 |
| `egress_policy` | [IMP] | ネットワークポリシー |
| `audit_chain` | [IMP] | 操作ログの連鎖とチェックポイント |
| `service_and_volume` | [PAR] | systemd 上のサービスと大きな DB (ネットワークファイルシステムは未試験) |

## 既知の制限

- モニターのコンピューターそのものを操作する `viewer` アカウントはローカル扱いになり、完全なパスが見えます。
- 受信 webhook の時間枠チェックは `workflow_run` と `workflow_job` の配信だけです。
- `none` や `github_only` でも、モニターが起動した Python プロセスはモニターを import した場合にのみポリシーを適用します。自分で実行したプログラムは対象外です。
- 保存データの暗号化、長期サポート系列、フェデレーションはこのバージョンにはありません。
