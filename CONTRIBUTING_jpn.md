# GitHub Actions Monitor への貢献

## 技術スタック
- **言語**: Python 3.11 以上。コアはパッケージ不要です(ターミナル表示 `bin/tui.py` は任意の Rich を使い、無い場合はそれが必要なテストをスキップします)。
- **インターフェース**: `127.0.0.1` で提供されるローカルのWebページ(`monitor/assets/static/actions_monitor.html`)とコマンドラインツール。
- **データ源**: 公式の GitHub コマンドラインクライアント `gh`(既定は読み取り専用の呼び出し)。

## ガイドライン
1. **まずテスト**: Pull Request の前に `python -m unittest discover -s monitor/tests` が通ること。オフライン実行で、テストは GitHub を呼びません。実サービスを手動で試すには `python tools/manual_check_live.py` を使います。
2. **8言語**: ユーザーが読むテキストはすべて `monitor/assets/locales/<lang>.json`(en、es、de、fr、it、ja、zh、pt=ヨーロッパポルトガル語)にあります。新しいキーは8ファイルすべてに追加し、テストが同じキーを持つことを確認します。
3. **秘密情報なし**: 既定ではモニターはトークンを保存しません(`gh` に尋ねます)。唯一の任意トークンはシステムの安全な保管庫(`secretstore.py`)にのみ置かれます。他の場所で認証情報を読み取る・出力する・記録する・書き込むコードを追加せず、実際の `actions_monitor.json` をコミットしないでください。
4. **既定で安全**: GitHub への書き込み、プログラムの実行、ネットワークポートの公開、外部へのデータ送信は、既定でオフ、設定 > 詳細設定に専用スイッチ、独自の確認があり、ネットワークモードがオンでない限り `127.0.0.1` で待ち受けます。そのような機能には、スイッチ・確認・トークンが無いと拒否すること、ログに何も漏れないことを示すテストが付きます。
5. **小さな一歩**: Pull Request 1件につき変更1つ、対応する行を `CHANGELOG.md` に。
6. **図**: `docs/architecture.json` か `docs/structure.json` を編集して `python tools/make_architecture.py` / `python tools/make_structure.py` を実行します。SVG を手で編集しないでください。
7. **8言語の変更履歴**: `monitor/CHANGELOG.md` の新しい項目には、それぞれ `monitor/docs/CHANGELOG_<spa|deu|fra|ita|jpn|zho|por>.md` に翻訳を付けます(同じバージョンと節。未翻訳の項目は翻訳された注記の下に英語の本文を残します)。翻訳にバージョンが欠けていると、`python tools/make_help_index.py --check` とリリースゲートが失敗します。
8. **バージョンごとにヘルプ全体を見直す**：リリースの前（そのリリースのプルリクエストの中で）、すべてのヘルプのトピック - リポジトリの README とその翻訳（概要、できること、プロジェクトの状況、テスト、リポジトリ構成、ドキュメント、セキュリティ）、`monitor/docs/` の各ガイド、クイックスタート、パッケージの README - を読み、古くなった数値、バージョン、コマンド、パス、画像、機能の一覧を 8 言語で直します。ヘルプのジェネレーターとテスト（`tools/make_glance.py`、`tools/make_help_index.py`、`tools/make_screenshots.py`、`monitor/tests/test_190_help_current.py`）が検出できるのは一部だけです。

## リリースごとのステータスダッシュボード更新

`.github/workflows/dashboard-dispatch.yml` は、`CI` ワークフローが `main` で成功した後(push イベントのみ)に実行されます。管理者が任意のリポジトリシークレット `ECOSYSTEM_DASHBOARD_DISPATCH_TOKEN` を定義すると、ダッシュボードリポジトリにバージョン表の更新を依頼します。シークレットが無ければ何もせず終了し、権限もなく、CIを変更・遅延させません。`electro-hobby-3d.project.json` のバージョンは各リリースで `tool_version.py` と等しくなければならず、テストが確認します。

- ヘルプのチェックリスト:新しい設定ごとの設定ヘルプ(`cfg.h.<キー>`)、変更したタブのヘルプ、`monitor/docs/` のガイド、8 言語、ヘルプのインデックス(`python tools/make_help_index.py`)、変更履歴。

## 手順を守る CI のチェック

- **ネットワークを遮断したテスト**：`sh tools/run_offline_tests.sh discover -s monitor/tests` は、ループバックだけを持つネットワーク名前空間でスイート全体を実行します。インターネットが必要なテストはここで失敗します。
- **依存関係の監査**：`python tools/audit_dependencies.py` は CI がインストールするパッケージに `pip-audit` を実行します。`.github/audit-suppressions.json` の抑制には `id`、`reason`、`expires`（最長 180 日先）が必要で、期限切れの抑制も、不要になった抑制（脆弱性がもう見つからない）も失敗になります。
- **外部ソースのスモークテスト**：週次のワークフロー `sources-smoke.yml` が `tools/smoke_sources.py` で本物のステータスページ、アドバイザリ、REST API の記述、最新リリースを読み、形式が変わると失敗します。
- **制限**：`tools/limits_check.py` は 1 プロセッサ・512 MB のコンテナーで 120 ワークフローのアカウントを使ってモニターを動かします。
- **リリースの順序**：GitHub のリリースを下書きとして作り、タグ `vX.Y.Z` をプッシュします。`release-image.yml` がイメージをビルドして公開し、両方のプラットフォームでタグ指定で応答したときだけ下書きを公開します。
