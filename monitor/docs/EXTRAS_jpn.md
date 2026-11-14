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

`github_app.share_reads`:次のコマンドは、このコンピューター上であなたの GitHub App の1時間有効なインストールトークンを表示します。これにより、ツールやエージェントの `gh` があなたの利用枠ではなく App の利用枠で読み取ります(`GH_TOKEN`)。トークンは標準出力にのみ出力され、ファイルやログには書かれません。コマンドには `--read-only` が必要です。App を作るときは読み取り専用の権限だけを与えてください。`github_app.share_reads` がオフの間は拒否します。

```
python bin/monitor_cli.py gh-token --read-only
```

## まだ含まれていないもの

ワークフロー衛生パネル、キューレポート、リリース準備完了/ブロックのビュー、サプライチェーンパネルは、このバージョンには含まれていません。
