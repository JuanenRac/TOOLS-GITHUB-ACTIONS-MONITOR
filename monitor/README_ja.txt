Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE

GitHub Actions モニター + センチネル（バージョン 1.7.1）
========================================================
どれを起動する? (新しい利用者が2分で決められます)
  完全版  MONITOR_GITHUB_ACTIONS.*       センチネル付きのページ(ポート 8765): アラート、署名キュー、分析。複数のリポジトリがあるならここから。
  LITE版  MONITOR_LITE_GITHUB_ACTIONS.*  センチネルなしの同じページ(ポート 8766): 赤・停滞・実行中を表示。軽量で、完全版と同時に動かせます。
  バッチ  BATCH_GITHUB_ACTIONS.*         自分のビルドを署名して公開する場合のみ。
  ターミナル  python tui_textual.py (LITE版は --lite を付ける)   対話型ターミナルアプリ。tui.py --once は1画面だけ出力します。
  診断    python actions_monitor.py --doctor (スクリプト用は --json)   不足しているものと、直すための正確なコマンドを表示します。
  お試し  python actions_monitor.py --demo   架空のデータのページ: gh もログインも不要で、あなたのデータには触れません。

必要なもの: Python 3.11 以上と、ログイン済みの GitHub CLI（`gh`）（gh auth login）。それ以外は不要です。中核はパッケージを必要とせず、ターミナル表示(tui.py)だけが任意のパッケージ rich を使います。
初めて使うときの手順: QUICKSTART_ja.txt。

起動       Windows: MONITOR_GITHUB_ACTIONS.bat | Linux: ./MONITOR_GITHUB_ACTIONS.sh | macOS: MONITOR_GITHUB_ACTIONS.command をダブルクリック
           （http://127.0.0.1:<ポート> をブラウザーで開きます。ローカル専用）。どの OS でも次の実行も可能:  python3 actions_monitor.py  （Windows: py -3 actions_monitor.py）
バッチ     BATCH_GITHUB_ACTIONS.bat / .sh / .command（gha_dispatch_all.py: plan, dispatch, status, finalize, hygiene）。ビルドを手元で署名する人向けのオプションです。
絶対にしないこと   ネットワークモード(設定 > 詳細設定: プライベートアドレス、全リクエストのアクセストークン、ページ内の警告)をオンにしない限り、127.0.0.1 でのみ待ち受けます。システムの安全な保管庫に保存する任意のトークンをオンにしない限り、トークンは保存しません（`gh` に尋ねます）。単独では GitHub に何も書き込みません。GitHub に書き込むのはバッチコマンドの `dispatch --go`、`dispatch --real`、`finalize --execute` だけで（workflow の起動、未署名ドラフトの作成、公開）、あなたが実行したときに限ります。
           自動で署名したり公開したりすることは「ありません」。署名と公開はあなた自身が実行するコマンドで、モニターはそれをテキストとして表示するだけです。
           重要な判定に AI は使いません。オプションの AI による説明は、初期設定ではオフです。

言語       8 言語: en, es, de, fr, it, ja, zh, pt（ポルトガル語はポルトガル式）。起動時は英語です。システムの言語では決まりません。別の言語は、ページの「設定」タブ（歯車アイコン。ブラウザーが記憶します）、
           actions_monitor.json の "language"、環境変数 MONITOR_LANG、またはコマンドラインツールの --lang コード（最優先）で選びます。
           スクリプトが読む行（SKIP、DISPATCHED、READY、FAILED、Summary:、BUILD ONLY...）は常に英語です。
設定       actions_monitor.json（初回起動時に actions_monitor.example.json から作成されます）。主なキー: github_owner（空 = gh のアカウント）、
           language, ecosystems_file, targets_file, refresh_seconds, cold_refresh_seconds, max_workers, min_rate_remaining, sentinel.*
           ecosystems_file: 名前の接頭辞でリポジトリをまとめます（ecosystems.example.json を参照。"*" = すべてのリポジトリ）。targets_file: バッチツール用のビルド一覧
           （targets.example.json を参照）。profiles_file (profiles.example.json): バッチのプロファイル。これらのファイルで "_" で始まるキーはメタデータです。
ワークスペース  任意: リポジトリのローカルクローンを置いたフォルダー（MONITOR_ROOT、json の "workspace_root"、または .monitor-root ファイルのある親フォルダー）。
           ない場合、モニターは「縮小モード」で起動し、その旨を表示します。GitHub API から得られる情報だけを表示します（ローカルの署名キュー、監査レポート、CHANGELOG の読み取りなし）。
           ある場合は、リリース候補、署名キュー、バッチツールも使えます。署名記録は "signed_dir"、監査ファイルは "audit_dir" で指定します。
テスト     py -3 -I -m unittest discover -s tests （Linux/macOS: python3 -I -m unittest discover -s tests）。ネットワークは不要です。
困ったとき "API rate limit": gh の共有利用枠（1 時間 5000 回）を使い切りました。リセット（gh api rate_limit）を待ち、refresh_seconds を増やすか max_workers を減らしてください。
           gh が応答しないと、モニターは起動時に停止します。壊れたキャッシュは無視されます。キャッシュをやり直すには sentinel_cache.json を削除してください。
           パッケージを更新したらモニターを再起動してください（実行中のプロセスは古いコードのままです）。

ツール     read_report.py [--lang コード] [--json] [--export-status フォルダー] [--export-sign-queue ファイル]  実行中のモニターの内容を表示（ローカル、GitHub の利用枠は消費しません）
           gha_dispatch_all.py [--lang コード] plan|dispatch|status|finalize|hygiene    GitHub Actions のビルドをバッチ実行（この PC では何もコンパイルしません）
           release_notes.py REPO [--since タグ] [--out ファイル]    コミットからリリースノートの下書きを作成（提案のみで、何も公開しません）
           release_candidates.py    CHANGELOG の [Unreleased] に項目があり、最新リリースが古いプロジェクト（読み取り専用）
イベント   センチネルは「変化」（新しい赤、CI の回復、停滞ビルド、新しいアラートなど）ごとに JSON を 1 行、events_monitor.jsonl に書き込みます。各行には、言語に依存しない
           固定の `code`、`kind`, `level`, `repo`, `args`、そして設定した言語の `text` が含まれます。`tail -F` で追えます。
赤の CI    基準は 1 つだけ: 既定ブランチでの各 workflow の「最後に完了した run」。赤 = failure, timed_out, startup_failure, action_required。
           cancelled, skipped, neutral, stale は数えません。

1.5.1 の新機能（履歴: CHANGELOG.md）
  - 設定タブ：新しいグループ「センチネル用の外部 AI」（ai.provider none / ollama / openai-compatible、モデル、Ollama のアドレス（このコンピューターのみ）、https エンドポイント、キーを保持する環境変数の名前、1日あたりの呼び出し回数）。キー自体は保存されません。既定ではオフで、外部サービスにはリポジトリのデータが送られます。
  - migrate_state.py：1.5.0 より前に書かれたファイルを新しい名前に移します。`python migrate_state.py` はドライラン、`--apply` はコピー（古いファイルは残る）、`--move` は名前変更です。上書きはしません。docs/MIGRATING.md に8言語で1ページにまとめています。
  - 独自のカタログファイルがない初回起動：サンプルを使用していることをコンソールに表示し、`--init-catalog` で ecosystems.json、targets.json、profiles.json の編集可能なコピーを作成します。
  - Python 3.11 以上（Windows、Linux、macOS で 3.11 と 3.13 を検証）。

1.5.0 の新機能（履歴: CHANGELOG.md）
  - 「設定」タブ: actions_monitor.json の値をページから変更できます（型と範囲つきの許可キー一覧、検証あり、保存前に config_backups/ へコピー、トークンや秘密は扱いません。docs/SETTINGS.md）。
  - 光って沈むレリーフ付きボタン、名前とツールチップが 8 言語の SVG アイコン、状態ダッシュボードの見た目、動きのあるバーと数値（prefers-reduced-motion で停止）。
  - 任意の出力（既定はオフ、127.0.0.1 のみ）: /metrics（Prometheus）、/api/outputs/grafana.json（Grafana JSON / Infinity）、/api/outputs/dashboard.json（docs/OUTPUTS.md、docs/grafana/ にサンプル）。
  - 中立なパッケージ: エコシステム、ターゲット、プロファイルはパッケージの外に置きます（ecosystems_file、targets_file、profiles_file。ローカル署名ツールは tools_dir）。既定は英語、ファイルとフォルダー名も英語です。
  1.4.x からの更新: 次の名前が変わりました（古い名前はファイルが存在し得る場所では引き続き読み取られ、書き込まれるのは新しい名前だけです）:
  leer_parte.py -> read_report.py          eventos.py -> events.py          parte_history.py -> report_history.py
  LOTE_GITHUB_ACTIONS.bat/.sh/.command -> BATCH_GITHUB_ACTIONS.bat/.sh/.command
  eventos_monitor.jsonl -> events_monitor.jsonl          eventos_estado.json -> events_state.json
  PARTE_CENTINELA_DIA_<day>.* -> SENTINEL_REPORT_DAY_<day>.*     PARTE_CENTINELA_<time>.txt -> SENTINEL_REPORT_<time>.txt     CANDIDATAS_RELEASE.txt -> RELEASE_CANDIDATES.txt
  <signed_dir>/lotes/lote_<time>.json -> <signed_dir>/batches/batch_<time>.json     parte_history_days -> report_history_days     monitor_y_centinela.zip -> github_actions_monitor.zip
  sentinel.audit_files: names of the A8 audit files (neutral defaults RECONCILIATION_TOTAL_*.txt, ROUNDS_MAP_2*.txt, ROUNDS_MAP_EXTRA_*.txt)
  ci_red.json and --export-status: unchanged (a contract).

1.4.2 の新機能(履歴: CHANGELOG.md)
  A2 が隠れた workflow の最新の実行を問い合わせる際、実行中または取り消された run は「確認済み」とみなされなくなりました(以前の赤を隠す可能性があるため)。センチネルは
  その workflow の完了済み run を取得し、実際の結論を持つ最初のものを使います(cancelled と skipped は無視)。デフォルトブランチに無ければ、その workflow だけが判定不能のままです。

1.4.1 の新機能(履歴: CHANGELOG.md)
  A2 は、実行サンプルが上限に達しただけでリポジトリ全体を判定不能とはしなくなりました。サンプルに現れないクローンの各 workflow について、その workflow だけの
  デフォルトブランチ上の最新の実行を GitHub に問い合わせます(読み取り専用、A10 と同じクォータ制限、sentinel.a2_resolve_max_calls_per_tick で上限、回答は
  sentinel.a2_resolve_ttl_seconds 秒保持)。赤は赤として数え、ブランチに実行がない workflow は判定不能のままで、パネルがその名前を示します。

1.4.0 の新機能(履歴: CHANGELOG.md)
  A11「準備状況」パネル: リポジトリごとのリリース準備状況(デフォルトブランチのCIとそのコミット、直近のリリースを上回るバージョン、ビルド、署名、次の手順)、
  エコシステムの健全性(実際の件数だけから算出したスコア。データのあるリポジトリが少ない場合は表示しません)、提供元より古い固定バージョン
  (ローカルクローンの固定ファイルから読み取り、sentinel.readiness.pins.sources で設定)。読み取り専用で、推測は一切行いません。

1.3.0 の新機能（履歴: CHANGELOG.md）
  ページ、コマンドライン、イベント、レポートが 8 言語に対応。言語セレクター。エコシステム、ターゲット、GitHub アカウントをデータ化（github_owner, ecosystems_file,
  targets_file）。任意のワークスペースと、正直な縮小モード。すべてのファイルに著作権表示と GPL-3.0-or-later。LICENSE, NOTICE, AUTHORS。README と QUICKSTART を 8 言語で提供。
ライセンス GPL-3.0-or-later（LICENSE と NOTICE を参照）。Copyright (C) 2026 JuanenRac (Electro Hobby 3D)。

ヘルプ、バージョン情報、確認 (1.6.4)
------------------------------------
ページにはヘルプボタン（丸い ?）とバージョン情報ボタン（i）があります。コンソールでは --help-topics、--help-search、--about、--doctor を使い、--demo は架空のデータでページを表示します。lite 版は独自のバナーとウィンドウタイトル（LITE、ポート 8766、センチネルなし）で起動し、フル版は COMPLETE、ポート 8765、センチネル有効と表示します。新バージョンのお知らせはオフにできます（設定 > 基本）。

1.7.1 の新機能（サイドパネル、16 のテーマ、センチネルの契約。履歴: CHANGELOG.md）
  ページの左にロゴ、グループ分けしたセクション、ヘルプを備えたサイドパネルが付きました。アイコンだけに縮められます。自動、ライト、ダークに加えて 16 のテーマがあります（設定 > このブラウザ）。
  CI センチネルは契約（BaseSentinel、SentinelRegistry）の裏に置かれ、次のセンチネルを追加できます。表示と判断の内容は変わりません。lite 版にはどれもありません。

1.7.0 の新機能（複数アカウント。履歴: CHANGELOG.md）
  フル版は複数の GitHub アカウントを監視できます。アカウントごとに accounts/<id>/ フォルダーと、スーパーバイザーの下の 1 つのモニターがあり、1 つの障害が他に及ぶことはありません。
  --accounts、--account <id>、--migrate-accounts [--apply]。切り替えとすべてのアカウントのページ、?view= と ?chrome=0、Webhook の状態を表示するライブビュー、すべてに共通の 1 つの /api/webhook。
  ガイド: docs/ACCOUNTS.md。accounts/ フォルダーがなければ何も変わりません。lite 版はアカウントが 1 つで、これらはありません。

1.6.8 の新機能（プロキシの実機検証。履歴: CHANGELOG.md）
  1.6.7 の HTTPS プロキシを、ポート 443 の実際のプロキシ（リポジトリの tools/manual_check_live.py proxy）と、連鎖全体を通すテストで検証しました。変更履歴は 1.6.3 まで翻訳済みです
  （ヘルプ > 変更履歴）。変わる設定はありません。

1.6.7 の新機能（既定ポートの HTTPS プロキシ。履歴: CHANGELOG.md）
  新しい設定 listen.proxy_public_host（既定は空）: ポート 443 の HTTPS プロキシが Host と Origin をポートなしで転送する場合、その公開名はそのまま受け付けられます。HTTPS のときに限り、
  変更はそのコンピューター自身からのみ可能です。変更履歴は 1.6.7、1.6.6、1.6.5 について翻訳済みです（ヘルプ > 変更履歴）。

1.6.6 の新機能（ネットワークモードと act の修正。履歴: CHANGELOG.md）
  HTTPS のネットワークモードがページから動作（オリジンはセッションのスキームに従う）。secure とされた設定はそのコンピューター自身からのみ変更可能。POST /api/access でアドレスにトークンを
  含めずにセッションを開始。全インターフェースで待ち受けると設定に赤いバーを表示。握りつぶした失敗のカウンターを --doctor とバージョン情報に追加。act: Stop が実行を解放し、パイプを閉じる。
  変更履歴を8言語に翻訳（ヘルプ > 変更履歴）。

1.6.5 の新機能（整合性とセキュリティ。履歴: CHANGELOG.md）
  バッチ: CI が緑とは必須ワークフローが成功したこと（dispatch.required_ci）。git fetch の失敗は起動を止め、targets.json はツールフォルダー外のツールや dry_run/ref の変更を指定できず、
  finalize はコミット確認を記録したバッチの実行だけを提示します（古いバッチは finalize --accept-legacy）。act はワークスペース内に留まり、Stop はツリー全体を終了します。
  ネットワークモード: 任意の HTTPS、誤ったトークン後のロック、IPv4 のみ。Webhook: リプレイなし。通知: max_per_hour はメッセージ数。--doctor が危険な組み合わせを警告します。
