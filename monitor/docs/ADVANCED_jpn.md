<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# 詳細機能(すべて既定でオフ)

このページの内容は、*設定 > 詳細設定*(または `actions_monitor.json`)でオンにするまで**オフ**です。モニターに誰が到達できるか、GitHub で何ができるかを決めるキーはセキュリティオプションとして印が付いています。必要なものだけオンにしてください。

## ネットワークで待ち受け

既定ではページは `127.0.0.1` でのみ応答します。`listen.network` をオン(再起動が必要)にすると `listen.host` でも待ち受けます。このPCのプライベートアドレス、または全インターフェースを表す `0.0.0.0` です。公開アドレスは拒否されます。

- **すべてのリクエストにアクセストークンが必要**です(Cookie、`X-Monitor-Access` ヘッダー、または `Authorization: Bearer`)。トークンは `listen.token_env` で指定した環境変数の値(16文字以上)で、無い場合は起動のたびにランダムなトークンが作られ、コンソールに一度だけ表示されます。そこに表示されたアドレスを一度開くと Cookie が設定され、きれいなアドレスに移動します。
- ページの使い捨てトークンは強制され、モードがオンの間は全タブに赤いバーが表示され、`listen.*`、`github_token.*`、`act.*`、`github_actions.*` のキーはこのPC自身からのみ変更できます。
- `listen.allowed_hosts` はページを開ける名前の一覧です(DNSリバインディング対策)。
- **リスク。** 通信は暗号化されないHTTPです。ネットワークを盗聴できる人はトークンとデータを読めます。信頼できるネットワークでのみ使うか、HTTPS のリバースプロキシを前に置いてください(`DEPLOYMENT.md` を参照)。インターネットには絶対に公開しないでください。LITE版はこのPCの外では待ち受けません。

## モニターが保持する GitHub トークン

既定は引き続き自分の `gh` ログインです。`github_token.enabled` をオンにすると、設定 > 詳細設定でトークンを貼り付けられます。トークンはシステムの安全な保管庫(Windows DPAPI、macOSキーチェーン、Linux Secret Service)に、無い場合のみ権限600のファイルに保存されます(ページに表示されます)。`actions_monitor.json`、ログ、バージョン情報パネル、サポート用テキストには決して書かれず、プロセスの環境経由でのみ `gh` に渡ります。**トークンを削除**ボタンですべての場所から消去します。

## GitHub への操作

`github_actions.enabled` をオンにすると、失敗した実行の再実行(`rerun_failed`、`rerun_run`、`rerun_job`)、実行のキャンセル(`cancel`)、Issue やプルリクエストのクローズ(`close_issue`、`close_pr`)、マージ(`merge_pr`、`github_actions.merge_method` を使用)ができます。使えるのは `github_actions.allowed` にある名前だけです(既定は `rerun_failed` と `cancel`)。**各操作は個別に確認されます**。ページは送信内容(メソッドとエンドポイント)を正確に表示し、そのプランを使い捨てトークンで確認するまで何も送りません。GitHub トークンには権限が必要です(実行には `workflow`、Issue とプルリクエストには `repo`。なければ GitHub の拒否が表示されます)。すべての試行は `github_actions_log.jsonl` に記録されます。AIアシスタントはこれらを開始できません。

## act でここでワークフローを実行

`act.enabled` をオンにし、`act.allowed` に `リポジトリ:ファイル.yml:イベント` の項目(3つとも完全一致)を入れると、正確なコマンドラインを確認した後、ボタンでローカルクローンに対して `act` を実行します。実際のシークレットは渡されません(シークレット・変数・環境・入力のファイルは空、トークンのない最小限の環境)。出力は逐次表示され、一度に1回だけ実行され、`act.timeout_seconds` の時間制限があり、停止もできます。

## アーティファクトのローカルコピー

`mirror.enabled` をオンにし、このPC上の `mirror.folder` を指定すると、完了した実行のアーティファクトがそこにコピーされます(1サイクルあたり `mirror.max_per_cycle`、フォルダー全体で `mirror.max_mb`、保持 `mirror.keep_days`)。各1回のみで、名前はフォルダー内で整形されます。

## セルフホストランナー

`runners.enabled` をオンにすると、設定 > 詳細設定に各ランナーが待機・使用中・オフラインで表示されます。ディスクと負荷は `runners.metrics`({名前: このPCまたはプライベートアドレスの node exporter のアドレス})に載せたランナーだけ表示されます。

## OpenTelemetry

`otlp.enabled` をオンにして `otlp.endpoint`(HTTPS、またはこのPC上のHTTP)を指定すると、完了した実行がトレースとして、ヘッダーの数値がメトリクスとして送られます(JSON の OTLP/HTTP)。各実行は1回だけです。送るのはリポジトリ、ワークフロー、ブランチ、イベント、結果、所要時間だけです。

## 組織とコスト

- `organizations.discover` は設定 > 基本にログインの組織を一覧表示します。1つを監視するには、`github_owner` をその組織にした2つ目のモニターを起動してください。
- `finops.jobs_per_cycle` を0より大きくすると、1サイクルあたりその数の完了した非公開実行のジョブのラベルを読み、仮定した1つのシステムではなく正しい倍率(Linux、Windows、macOS、`quotas.json` の大型ランナー)で分を計算します。請求レポート(`quota.billing_api`)をオンにすると、Codespaces と Packages の金額、使用中のストレージ、含まれる分を超えた分の料金も表示されます。

## 実サービスでの確認

`python tools/manual_check_live.py`(リポジトリ内)は、トークンのスコープ、請求レポート、組織、ランナー、`gh copilot` のフラグを読み取り、動作中のモニターにチャネル経由でテストメッセージを送らせます。シークレットは決して尋ねません。
