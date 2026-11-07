<p align="center">
  <img src="images/GITHUB_ACTIONS_MONITOR_BANNER.svg" alt="GitHub Actions Monitor" width="100%">
</p>

# GitHub Actions Monitor

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <b>🇯🇵 日本語</b> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL-3.0-or-later">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Dependencies-none-2EE6A6.svg" alt="No dependencies">
  <img src="https://img.shields.io/badge/Languages-8-FFB300.svg" alt="8 languages">
</p>

> 所有するすべてのリポジトリのワークフローを監視し、赤いもの・止まっているもの・対応待ちのものを、ローカルの1ページで教えます。

**GitHub Actions Monitor** は、あなた自身のコンピューターで動く小さなプログラムです。自分の `gh` ログインを使って GitHub に各ワークフローの最新の実行を問い合わせ、本当に赤いものを判定し、重要なこと（セキュリティ、衛生、公開準備の整ったバージョン、クォータ）を知らせ、自分のマシンからしか開けない Web ページにすべてを表示します。必要なのは Python と `gh` だけで、トークンは保存せず、既定では読み取りしか行いません。

## 概要

| | |
|---|---|
| **必要なもの** | Python 3.11 以上と GitHub CLI（`gh auth login`）。それ以外は不要 |
| **開く先** | `127.0.0.1` 上のページのみ、8言語対応 |
| **GitHub への書き込み** | 自動では行いません。明示的な `--go` を付けて実行したバッチコマンドのみ |
| **エクスポート** | `ci_red.json`、Prometheus メトリクス、Grafana 用 JSON（有効にするまですべてオフ） |

## スクリーンショット

<p align="center"><img src="docs/screenshots/monitor_now_dark.png" alt="Now" width="92%"></p>
<p align="center"><img src="docs/screenshots/monitor_sentinel_dark.png" alt="Sentinel" width="92%"></p>
<p align="center"><img src="docs/screenshots/monitor_charts_dark.png" alt="Charts" width="92%"></p>
<p align="center"><img src="docs/screenshots/monitor_settings_light.png" alt="Settings" width="92%"></p>

*デモデータです。画像内のリポジトリ名や名前は架空のものです。*

## できること

- **赤かどうかは1つのルールで判定**：既定ブランチ上の各ワークフローの最後に完了した実行。キャンセルやスキップされた実行が、以前の失敗を隠すことはありません。
- **センチネル**：セキュリティアラート、リポジトリの衛生、古いプルリクエスト、公開準備の整ったバージョン、署名待ちのビルド、平易な言葉のレポート。
- **設定ページ**：パス、間隔、クォータ、スイッチをブラウザーから変更できます。検証済みの固定キーのみで、保存前に必ずバックアップを取ります。
- **グラフと履歴**：計算時間、失敗、成功をアニメーションするバーと日次履歴で表示します（動きの軽減設定を尊重します）。
- **8言語**（en、es、de、fr、it、ja、zh、pt）。英語が基本で、設定で切り替えます。
- **ダッシュボード向け出力**：`ci_red.json`、Prometheus エンドポイント、Grafana 用 JSON ソースと、インポート可能な Grafana ダッシュボード。
- **バッチツール**：多数のビルドをまとめて計画・実行します。`--go` なしでは何も実行されません。

## アーキテクチャ

<p align="center"><img src="images/architecture.svg" alt="アーキテクチャ" width="100%"></p>

## クイックスタート

1. Python 3.11 以上と [GitHub CLI](https://cli.github.com/) をインストールし、`gh auth login` を実行します。
2. このリポジトリ（または最新リリースの zip）をダウンロードし、`monitor` フォルダーを開きます。
3. 起動：Windows は `MONITOR_GITHUB_ACTIONS.bat`、Linux は `./MONITOR_GITHUB_ACTIONS.sh`、macOS は `MONITOR_GITHUB_ACTIONS.command` をダブルクリック、どの環境でも `python actions_monitor.py` で起動できます。
4. 表示されたアドレス（`http://127.0.0.1:<ポート>`）を開きます。初回起動時に、サンプルから `actions_monitor.json` を作成します。
5. **設定** を開き、GitHub アカウント、エコシステム（名前の接頭辞によるリポジトリのグループ）などを設定します。

## 設定

すべては `actions_monitor.json`（`actions_monitor.example.json` から作成）にあります。**設定** タブで安全に編集でき、トークンや秘密情報は表示も保存もされません。エコシステム、ビルド対象、バッチプロファイルは別ファイルで、`ecosystems_file`、`targets_file`、`profiles_file` で指定します。中立な `*.example.json` テンプレートが付属します。詳細は [`monitor/docs/SETTINGS_jpn.md`](monitor/docs/SETTINGS_jpn.md) を参照してください。

## Grafana とダッシュボード向け出力

すべて既定でオフ、ローカル（`127.0.0.1`）限定で、追加のトークンは不要です。設定で有効にすると `/metrics`（Prometheus 形式）、`/api/outputs/grafana.json`、`/api/outputs/dashboard.json` が使え、インポート可能な Grafana ダッシュボードが [`monitor/docs/grafana`](monitor/docs/grafana) にあります。詳細：[`monitor/docs/OUTPUTS_jpn.md`](monitor/docs/OUTPUTS_jpn.md)。`ci_red.json` の形式：[`monitor/docs/CI_RED_SCHEMA_jpn.md`](monitor/docs/CI_RED_SCHEMA_jpn.md)。

## セキュリティ

- `127.0.0.1` でのみ待ち受け、`Host` または `Origin` がローカルでないリクエストは拒否します。ログインがないため、`0.0.0.0` には決して割り当てないでください。
- トークンは保存せず、あなた自身の `gh` を使います。
- 自動では GitHub に何も書き込みません。書き込むのは `dispatch --go`、`dispatch --real`、`finalize --execute` だけで、あなたが実行したときのみです。
- 設定ページは、バックアップを保存してから、検証済みの固定キーだけを書き込みます。

## テスト

ネットワークも追加パッケージも不要です：

```
python -m unittest discover -s monitor/tests
```

## リポジトリ構造

<p align="center"><img src="images/repository-structure.svg" alt="リポジトリ構造" width="100%"></p>

```
TOOLS-GITHUB-ACTIONS-MONITOR/
├── monitor/                          プログラム本体
├── docs/                             構成図、スクリーンショット
├── tools/                            図のジェネレーター
├── images/                           バナーと図
├── .github/                          CI と Issue フォーム
├── CHANGELOG.md                      バージョン別の変更
├── LICENSE NOTICE AUTHORS            ライセンスと作者
├── CONTRIBUTING.md SECURITY.md       参加方法、報告
├── SUPPORT.md CODE_OF_CONDUCT.md     サポートと行動規範
└── monitor/
    ├── actions_monitor.py            ローカルサーバー
    ├── actions_monitor.html          Web ページ
    ├── sentinel_local.py             アラートとレポート
    ├── surface.py readiness.py       検査とリリース準備
    ├── settings_api.py outputs.py    設定とメトリクス
    ├── signstate.py sigverify.py     署名の状態と検証
    ├── read_report.py                ターミナルでレポート
    ├── gha_dispatch_all.py           バッチビルド
    ├── events.py report_history.py   イベントと履歴
    ├── ci_red.py export_status.py    他ツール向けファイル
    ├── i18n.py locales/              8言語
    ├── toolconfig.py workspace.py    設定とクローン
    ├── tests/                        オフラインテスト
    └── docs/                         設定と Grafana
```

## ドキュメント

- [`monitor/docs/SETTINGS_jpn.md`](monitor/docs/SETTINGS_jpn.md): すべての設定
- [`monitor/docs/OUTPUTS_jpn.md`](monitor/docs/OUTPUTS_jpn.md): メトリクス、Grafana、エクスポート
- [`monitor/docs/CI_RED_SCHEMA_jpn.md`](monitor/docs/CI_RED_SCHEMA_jpn.md): ci_red.json の形式
- [`monitor/docs/CI_RED_BRIDGE_jpn.md`](monitor/docs/CI_RED_BRIDGE_jpn.md): ci_red.json をダッシュボードへ渡す
- [`monitor/QUICKSTART_ja.txt`](monitor/QUICKSTART_ja.txt): 最初の手順（8言語）

## コントリビュート

[CONTRIBUTING.md](CONTRIBUTING.md) をお読みください。バグやアイデアは Issue フォームで、セキュリティ上の問題は [SECURITY.md](SECURITY.md) に従って報告してください。

## 作者

作者：**JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## ライセンス

コードは GPL-3.0-or-later、ドキュメントは CC BY-SA 4.0 です。[LICENSE](LICENSE) と [NOTICE](NOTICE) を参照してください。
