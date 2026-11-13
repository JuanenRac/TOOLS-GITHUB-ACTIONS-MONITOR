Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE

GitHub Actions モニター + センチネル（バージョン 1.7.7）
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

変更履歴
  すべてのバージョンが新しい順に CHANGELOG.md にあります（8 言語版は docs/CHANGELOG_*.md、ページでは ヘルプ > 変更履歴）。

ヘルプ、バージョン情報、確認 (1.6.4)
------------------------------------
ページにはヘルプボタン（丸い ?）とバージョン情報ボタン（i）があります。コンソールでは --help-topics、--help-search、--about、--doctor を使い、--demo は架空のデータでページを表示します。lite 版は独自のバナーとウィンドウタイトル（LITE、ポート 8766、センチネルなし）で起動し、フル版は COMPLETE、ポート 8765、センチネル有効と表示します。新バージョンのお知らせはオフにできます（設定 > 基本）。
