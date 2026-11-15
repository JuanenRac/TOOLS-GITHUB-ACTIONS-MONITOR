<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AUDIT_PACKAGE.md) | [🇪🇸 Español](AUDIT_PACKAGE_spa.md) | [🇫🇷 Français](AUDIT_PACKAGE_fra.md) | [🇮🇹 Italiano](AUDIT_PACKAGE_ita.md) | [🇩🇪 Deutsch](AUDIT_PACKAGE_deu.md) | [🇨🇳 简体中文](AUDIT_PACKAGE_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](AUDIT_PACKAGE_por.md)

# 監査担当者向けパッケージ

このツールのチームモード、ネットワーク公開、秘密情報の扱いを監査担当者が確認するために必要なもの：チェックリスト、過去のレビューの指摘とその修正および修正を維持するテスト、テストの実行方法、既知の残課題。

## チームモードのセキュリティチェックリスト

- チームモード（`auth.enabled`）は既定でオフです。HTTPS または信頼できるプロキシ（`listen.trusted_proxy`）の背後でのみ有効にしてください。
- チームモードが有効でネットワークが開いている場合、最初の管理者が存在するまでモニターは起動しません。
- それまでは、そのコンピューター自身だけが入れます（最初の管理者はそこで作成します）。
- スクリプト用トークン（`auth.allow_bearer`）は既定でオフです。セッションが書き込むには CSRF トークンが必要です。
- 各アカウントのプロセスは、起動時に渡される鍵を持つ監督プロセスにのみ応答します。
- 秘密情報はログにも API の応答にも書かれません。設定ファイルはロックの下で保存されます。
- モニターから出るすべての要求（通知、OpenTelemetry、ランナーのエクスポーター）は同じ規則に従います：プライベートアドレスなし、そこへのリダイレクトなし。

## 指摘・修正・テスト

| 指摘 | 修正 | テスト |
|---|---|---|
| チームモードでユーザーがいない間、すべてのルートがネットワークに開いていた | 最初の管理者ができるまでそのコンピューターだけが入れ、管理者なしではネットワークモードは起動しない | `test_184_audit_auth.py::FirstAdministratorWindow, test_185_bootstrap_start.py` |
| アカウントのプロセスがチームモードの検査を迂回していた | すべての要求で監督プロセスの鍵を要求する | `test_184_audit_auth.py::ChildAnswersOnlyToItsSupervisor` |
| タイムアウト後、ファイルロックなしで設定の保存が続行されていた | ロックが10秒間取られたままなら、メッセージ付きで保存を拒否する | `test_184_audit_hardening.py::ConfigurationLock` |
| センチネルのコマンドが引数付きのシェルになり得た | コマンドは、先頭がシェルではないプログラムの完全パスであるリストで、制御文字を含まない | `test_184_audit_hardening.py::NotifyCommand` |
| スクリプト用トークン（bearer）が既定でオンだった | 既定でオフ。本物の true だけがオンにする | `test_184_audit_hardening.py::ScriptTokens` |
| AI 向けフィードが全アカウントで共有され、更新・確認・通知上限が互いに追い越し得た | アカウントごとに1つのフィード。更新・確認・状態は同じロックを取り、上限は1回のロック付きの手順で確保する | `test_184_audit_feed.py (OneStepAtATime, CapOfTheNotices)` |
| AI ツールのフックの休止が1手順で確保されず、ランナーのエクスポーターがモニターをリダイレクトでき、戻らない GitHub 呼び出しが溜まった | 休止はロックで保持し、リダイレクトは検査して制限し、放棄された呼び出しは数えて上限を設ける（`watchdog_max_abandoned`） | `test_184_audit_robustness.py (HookCooldown, Exporter, AbandonedCalls)` |
| 末尾が改行の名前が、ID・リポジトリ・キーの検査を通過した | すべての検査がテキストの末尾で終わる（`\Z`） | `test_184_audit_anchors.py` |
| OpenTelemetry のエクスポートが送信要求の規則に従わず、プロキシが信頼境界だと示されておらず、ページのエスケープにテストがなかった | エクスポートは同じガードを通る（プライベートアドレスなし、リダイレクトなし）。境界はヘルプに記載し、API のすべてのテキストのエスケープをテストで維持する | `test_184_audit_network.py (Collector, ProxyIsAFrontierOfTrust, PageEscaping)` |
| 2つのモニターが同じポートで待ち受け可能で、Git for Windows の openssl が見つからず、意図的に握りつぶした失敗の出所が残らなかった | ポートは排他的に確保し、2つ目のモニターは起動を拒否する。openssl は Git for Windows の置き場所を探す。握りつぶした失敗ごとに種類と場所の行をログに書く | `test_185_startup.py (OnePerPort, WhereIsOpenssl), test_185_degraded.py` |
| 所要時間のない実行（GraphQL で取得）がセンチネルを毎サイクル失敗させた | 所要時間がない場合は 0 として数える | `test_186_unfinished_rows.py` |

## レビュー担当者向けのハーネスと再現テスト

`python tools/audit_harness.py --check` は、一時フォルダー内で GitHub なし（偽の `gh`）に、3 つのアカウント（`alpha`、`beta`、`default`）と 4 人のユーザー（`admin`、`alpha` だけの `maintainer`、`beta` だけの `viewer`、無効化された `inactive`）を持つスーパーバイザーを起動し、アカウントの分離を決めるルートを呼び出して応答ごとに 1 行（`ok` または `WRONG`）を出力します。すべて正しければ終了コード 0 で終わります。`--check` なしではアドレスとユーザーを表示して待機します。1.8.3 の独立レビューの再現は `tests/test_193_regressions.py` にあり、そのバージョンでは失敗し、現在は成功します。

## テストの実行

`monitor/` フォルダーで `python -m unittest discover -s tests` を実行します。テストにネットワークも GitHub トークンも不要です。Edge、Chrome、Chromium がある場合（または `MONITOR_BROWSER_TESTS=1`）にブラウザテストが実行されます。表のファイルは `monitor/tests/` にあります。

## 既知の制限

- 環境のプロキシ（`network.use_proxy`、既定はオフ）は名前を自分で解決します。名前の検査はその前に行われます。強い保証はネットワーク側（プライベートアドレスを拒否するファイアウォール）で得る必要があります。
- Windows では権限だけではファイルを非公開にできません。システムが対応する場合、秘密情報はユーザーの鍵で暗号化されます。
- テストは実際の GitHub、プロキシ、メールサーバーについては何も証明しません。ローカルの代役を使います。
