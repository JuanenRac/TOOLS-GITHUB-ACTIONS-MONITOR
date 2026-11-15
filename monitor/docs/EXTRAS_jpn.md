<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](EXTRAS.md) | [🇪🇸 Español](EXTRAS_spa.md) | [🇫🇷 Français](EXTRAS_fra.md) | [🇮🇹 Italiano](EXTRAS_ita.md) | [🇩🇪 Deutsch](EXTRAS_deu.md) | [🇨🇳 简体中文](EXTRAS_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](EXTRAS_por.md)

# オプションの追加機能

どちらも**既定ではオフ**で、設定でオンにします。

## 失敗したステップのログ

`logs.failed_step.enabled`:失敗した実行のアラートに **失敗したステップ** ボタンが付きます。押すと、その実行のジョブと失敗ログを GitHub から読み取り(利用枠を2回分使用)、失敗したステップと関連する末尾の行(`logs.failed_step.lines`、`logs.failed_step.max_bytes`)を表示し、結果をメモリに保持するので、もう一度押しても消費しません。テキストからトークン、キー、アドレス、ホームフォルダーは除去されます。問い合わせできるのはモニターが監視しているリポジトリだけで、`GET /api/run-log?repo=&run=` を使います。チームモードでは管理者のみ。

## ツール用の GitHub App 読み取り専用トークン

`github_app.share_reads`:次のコマンドは、このコンピューター上であなたの GitHub App の1時間有効なインストールトークンを表示します。これにより、ツールやエージェントの `gh` があなたの利用枠ではなく App の利用枠で読み取ります(`GH_TOKEN`)。トークンは標準出力にのみ出力され、ファイルやログには書かれません。コマンドには `--read-only` が必要です。App を作るときは読み取り専用の権限だけを与えてください。`github_app.share_reads` がオフの間は拒否します。 トークンはモニターが保持するものとは別に、読み取り権限のみで要求されます。応答に書き込み権限が含まれる場合、コマンドは出力を拒否します。

```
python bin/monitor_cli.py gh-token --read-only
```

## 4つのオプションレポート

4つとも**既定ではオフ**です。アラートタブの下部にある「オプションのレポート」ブロックと `GET /api/reports` に表示されます。GitHub を読むレポートは1サイクルに最大 `reports.max_calls_per_cycle` 回までの呼び出しを使い、毎回数個のリポジトリだけを読み、読み取った内容を1日メモリに保持します。

- `reports.workflow_hygiene.enabled`:各リポジトリのワークフローファイルを読み取り、問題のある書き方を一覧にします。コミットに固定されていないアクション、制限のない権限、`timeout-minutes` のないジョブ、`concurrency` グループなし、`pull_request_target` とインジェクションの危険、平文のシークレット(ローカルクローンを読む A13 パネルの linter のルールに、新しい2つを加えたもの)。
- `reports.queue.enabled`:待ち時間のあった完了済みの実行を数件選んでそのジョブを読み取り、ランナーの種類(Linux、Windows、macOS、大型、セルフホスト)ごとにジョブが開始までに待った時間を示します。
- `reports.release_view.enabled`:呼び出しは一切なし。センチネルが把握している情報から、リリースの準備が「完了」しているリポジトリ(チェンジログの項目、または誰も公開していない緑のビルドがあり、赤いものも署名待ちもない)と、「ブロック」されているリポジトリとその理由を示します。
- `reports.supply_chain.enabled`:各リポジトリの最新リリースを読み取り、ファイル名から、ソフトウェア部品表(SBOM)、チェックサム、署名または証明が含まれているかを示します。ファイルはダウンロードしません。
