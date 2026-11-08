<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CONSOLE_TOOLS.md) | [🇪🇸 Español](CONSOLE_TOOLS_spa.md) | [🇫🇷 Français](CONSOLE_TOOLS_fra.md) | [🇮🇹 Italiano](CONSOLE_TOOLS_ita.md) | [🇩🇪 Deutsch](CONSOLE_TOOLS_deu.md) | [🇨🇳 简体中文](CONSOLE_TOOLS_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](CONSOLE_TOOLS_por.md)

# コンソールツール:ワークフロー Lint とターミナル表示

任意のコマンドラインツールが 2 つあります。モニター本体はパッケージを必要とせず、ターミナル表示は必要なときだけ Rich を使います。

## ワークフロー Lint:`lint_workflows.py`

- `py -3 lint_workflows.py [パス ...] [--json] [--fail-on info|warn|bad]` は push の前に `.github/workflows/*.yml` を検査します。パスを省略すると現在のフォルダーを見ます。ファイルを開くだけです。
- ルール(設定タブ、サブタブ「ワークフロー Lint」で個別にオフにしたり重大度を変更できます):`unpinned_uses`(完全なコミット SHA で固定されていないアクション)、`permissions`(`permissions:` ブロックが無い、または `write-all`)、`secrets_in_clear`(トークンやキーのように見えるものがファイルに書かれている)、`injection`(第三者のテキストが `run:` スクリプトに埋め込まれている)、`pr_target`(プルリクエストのコードをチェックアウトする `pull_request_target`)。
- 指摘が `--fail-on`(既定 `bad`)に達すると終了コードは 1 になるため、push 前フックとして使えます。モニターがクローンを参照できる場合は、日次レポートにも 1 行追加します。


## ターミナル表示:`tui.py`

- `pip install rich` の後、`py -3 tui.py [--port 8765] [--refresh 5] [--once] [--theme dark|light]`。実行中のもの、赤のワークフロー、署名キュー、レポートのライブ表を、`127.0.0.1` で動いているモニターから読み取って描画します(GitHub の割り当ては使いません)。
- 読み取り専用で、再実行・クローズ・書き込みを行うキーはありません。Rich が無いときはインストール方法を表示してコード 3 で終了します。モニターとそのテストは Rich を必要としません。
