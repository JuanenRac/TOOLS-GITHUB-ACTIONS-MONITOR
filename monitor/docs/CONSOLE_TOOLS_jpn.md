<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CONSOLE_TOOLS.md) | [🇪🇸 Español](CONSOLE_TOOLS_spa.md) | [🇫🇷 Français](CONSOLE_TOOLS_fra.md) | [🇮🇹 Italiano](CONSOLE_TOOLS_ita.md) | [🇩🇪 Deutsch](CONSOLE_TOOLS_deu.md) | [🇨🇳 简体中文](CONSOLE_TOOLS_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](CONSOLE_TOOLS_por.md)

# コンソールツール:ワークフロー Lint とターミナル表示

任意のコマンドラインツールが 2 つあります。モニター本体はパッケージを必要とせず、ターミナル表示は必要なときだけ Rich を使います。

## ワークフロー Lint:`bin/lint_workflows.py`

- `py -3 bin/lint_workflows.py [パス ...] [--json] [--fail-on info|warn|bad]` は push の前に `.github/workflows/*.yml` を検査します。パスを省略すると現在のフォルダーを見ます。ファイルを開くだけです。`--remote OWNER/REPO`(複数指定可)を付けると、クローンなしで `gh` 経由で GitHub からリポジトリのワークフローファイルを読み、読めない場合は理由(SSO 未承認、アクセス権なし)を表示します。
- `--remote OWNER/REPO --anon` は、`lint.anonymous_public` がオンのとき(既定はオフ)、公開リポジトリ(たとえば第三者のもの)を認証情報なしで読みます。ワークフローフォルダの一覧は匿名リクエストで、各ファイルは `raw.githubusercontent.com` から取得され、トークンの割り当てを消費しません。変更のないファイルは再読込されず、256 KiB を超えるファイルはスキップされ、非公開または存在しないリポジトリは「見つかりません」(「問題なし」ではない)と表示され、エアギャップのモニターは読み取りません。秘密を含むヘッダーは送信されません。
- ルール(設定タブ、サブタブ「ワークフロー Lint」で個別にオフにしたり重大度を変更できます):`unpinned_uses`(完全なコミット SHA で固定されていないアクション)、`permissions`(`permissions:` ブロックが無い、または `write-all`)、`secrets_in_clear`(トークンやキーのように見えるものがファイルに書かれている)、`injection`(第三者のテキストが `run:` スクリプトに埋め込まれている)、`pr_target`(プルリクエストのコードをチェックアウトする `pull_request_target`)。
- 任意ルール（有効にするまでオフ）: `no_timeout`（`timeout-minutes` のないジョブ）、`secrets_inherit`（再利用可能ワークフローの呼び出しでの `secrets: inherit`）、`own_action_main`（`@main` を追う自分のアカウントのアクション）、`permissions_top`（ジョブに独自の `permissions:` があるのにファイル先頭にない）。`unpinned_uses` はそのアクションが自分のものか第三者のものかを示し（`lint.own_owners`）、`lint.unpinned_own` で自分のものの重要度を下げたり非表示にできます。
- 情報用の規則 `archived_action`(オンにするまで無効。GitHub が必要):ファイルが使う GitHub のアクションや再利用可能ワークフローのうち、リポジトリが**アーカイブ済み**のものを、`lint.maintenance.inactive` をオンにするとさらに `lint.maintenance.inactive_years` 年(既定は 2)プッシュのないものも一覧にします。GitHub への問い合わせはアクションごとに 1 回です(コマンドラインでは `--check-actions` と `--inactive-years N`。モニターは自分の割り当てで読み、1 回のスキャンで最大 `lint.maintenance.max_calls_per_tick` 件、各回答を `lint.maintenance.refresh_seconds` 秒保持します)。知らせるだけで、常に情報レベルであり、`--fail-on` を失敗させることも終了コードを変えることもありません。GitHub に接続できないときはアクションを判定せず、それらについての通知も出さず、読み取れなかった件数を出力に示します。
- 指摘が `--fail-on`(既定 `bad`)に達すると終了コードは 1 になるため、push 前フックとして使えます。モニターがクローンを参照できる場合は、日次レポートにも 1 行追加します。`--remote` を使うとき、リポジトリを読めなかった場合(存在しない、トークンから見えない、SSO 未承認、ネットワークなし)や名前が `OWNER/REPO` でない場合は終了コードが 2 になります。読めなかったリポジトリが問題なしとして扱われることはありません。 指定したフォルダやファイルが存在しない場合や、読めないワークフローファイルがある場合も同様で、エラー出力にその名前が示され、他のファイルは引き続き確認され、終了コードは 2 になります。
- シークレットらしく見える値は、出力も保存もされずに分類されます。既知のトークン形式や高エントロピーの長い文字列は重大(`bad`)、`placeholder`、`dummy`、`changeme`、`ci` のように読めるダミーは情報のみ、それ以外は警告で、`${{ secrets.X }}`、`${X}`、空の値は指摘になりません。指摘を黙らせるには、その行または直前の行にコメントを書きます:`# monitor-lint: ignore secrets_in_clear docker compose config 用のダミーのため`(ルール名または `all`)。または設定 `lint.ignore` に `リポジトリ:ファイル:ルール`(`*` 可)のパターンを並べます。


## ターミナル表示:`bin/tui.py`

- `pip install rich` の後、`py -3 bin/tui.py [--port 8765] [--refresh 5] [--once] [--theme dark|light]`。実行中のもの、赤のワークフロー、署名キュー、レポートのライブ表を、`127.0.0.1` で動いているモニターから読み取って描画します(GitHub の割り当ては使いません)。
- 読み取り専用で、再実行・クローズ・書き込みを行うキーはありません。Rich が無いときはインストール方法を表示してコード 3 で終了します。モニターとそのテストは Rich を必要としません。
- 対話型ターミナルアプリ `bin/tui_textual.py`(`pip install textual`。lite 版には `--lite` を付けます)は、設定タブで、一覧表示されるグループの単純な設定、**リスト**(項目をカンマで区切って入力:`a, b, c`)、数値の**マップ**(`name=3, other=5`)を編集できます。サーバーが各値を再度検証し、セキュリティのオプションはページでのみ変更できます。

## ルール `container_input_name`：コンテナーアクションのハイフン付き入力

オプション（`lint.rules.container_input_name.enabled`、既定はオフ、重大度 `warn`）。コンテナーで動くアクション（`action.yml` の `runs.using: docker`）を持つリポジトリで、ハイフン付き入力の落とし穴を探します。GitHub は `fail-on-findings` をプログラムに `INPUT_FAIL-ON-FINDINGS`（ハイフンのまま）として渡すため、`INPUT_FAIL_ON_FINDINGS` を読むスクリプトは値を受け取れず、警告だけのモードが静かに機能しなくなります。検出結果にはスクリプト、行、入力名が示されます。シェルはハイフンで名前を切るため、シェル形式の `$INPUT_FAIL-ON-FINDINGS` も指摘します。値は `printenv` または使用言語の環境変数から読んでください。
