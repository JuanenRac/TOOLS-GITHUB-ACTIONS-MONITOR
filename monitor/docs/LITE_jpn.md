<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LITE.md) | [🇪🇸 Español](LITE_spa.md) | [🇫🇷 Français](LITE_fra.md) | [🇮🇹 Italiano](LITE_ita.md) | [🇩🇪 Deutsch](LITE_deu.md) | [🇨🇳 简体中文](LITE_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](LITE_por.md)

# lite 版

同じパッケージに入った、もう 1 つのシンプルな製品です。実行中のものと失敗したものを見せるページで、センチネルはありません。自分の実行を眺めたいだけの人向けです。

|  | 完全版 | lite 版 |
|---|---|---|
| 起動 | `MONITOR_GITHUB_ACTIONS`(`.bat` / `.sh` / `.command`) | `MONITOR_LITE_GITHUB_ACTIONS`(同じ 3 種類) |
| ポート | 8765 | 8766 |
| タブ | 今、センチネル、グラフ、リポジトリ、履歴、設定 | 今、グラフ、リポジトリ、履歴、短い設定 |
| ヘッダー | すべてのタイル、準備状況、署名 | 実行中、待機、24 時間の失敗と成功、計算分数、issue、main の赤、リポジトリ、割り当て、接続 |
| センチネル(アラート、リリース、署名キュー、準備状況、Lint) | あり | なし(インポートもされません) |
| 分析、通知、Webhook、AI、Prometheus / Grafana 出力 | あり(オンにするまでオフ) | なし(これらのパスは 404 を返します) |
| 設定 | `actions_monitor.json` | `actions_monitor_lite.json`(初回起動時に作成。センチネルはオフ) |
| 状態ファイル | `etag_cache.json`、`analytics_history.json` など | 同じ名前に接尾辞 `_lite` |

起動方法:Windows は `MONITOR_LITE_GITHUB_ACTIONS.bat`、Linux は `./MONITOR_LITE_GITHUB_ACTIONS.sh`、macOS は `MONITOR_LITE_GITHUB_ACTIONS.command` をダブルクリック、または `python actions_monitor.py --lite`(`MONITOR_MODE=lite` でも可)。`127.0.0.1:8766` で待ち受けるので、完全版と同時に動かせます。

短い設定には、アカウント(`github_owner`)、監視するリポジトリとエコシステム(`repos`、`ecosystems`、`exclude`)、更新間隔(`refresh_seconds`)、言語、テーマがあります。「main の赤」は、直近に完了した実行が失敗したワークフローの数です。後からセンチネルなどが必要になったら完全版を起動するだけで、移行は不要です。 初回起動時、`actions_monitor_lite.json` は `actions_monitor.json`(存在する場合)からアカウント、監視するリポジトリとエコシステム、カタログファイル、言語をコピーし、コンソールにそう表示します。センチネル、AI、Webhook、出力、通知は決してコピーしません。そのファイルが無ければすべてのエコシステムを監視します(`"ecosystems": "all"`)。テーマはブラウザーがポートごとに別々に記憶します。 lite 版は `ci_red.json` も署名キューも書き込まず、専用の状態ファイルを使います。両方の版に `sentinel.ci_red_file` を設定する場合は、同じファイルを指さないでください。
