<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LESSONS.md) | [🇪🇸 Español](LESSONS_spa.md) | [🇫🇷 Français](LESSONS_fra.md) | [🇮🇹 Italiano](LESSONS_ita.md) | [🇩🇪 Deutsch](LESSONS_deu.md) | [🇨🇳 简体中文](LESSONS_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](LESSONS_por.md)

# 失敗とレッスン

モニターは、CI の失敗を記録するブックとレッスンのライブラリを持てます。人でも、あなたの AI ツールでも、モニターの AI でも、同じ間違いを繰り返さないためです。**ローカルで読み取り専用**です。コンピューターの外には何も出ず、GitHub には何も書き込みません。AI 向けフィードのアラートに従うため、`ai_alerts.enabled` が必要です。

## ブック

フィードが開いた失敗は、`data/failures.jsonl`(スキーマ 1)の1行になります:`schema`, `ts`, `repo`, `workflow`, `job`, `step`, `event`, `branch`, `actor_kind`, `category`, `root_cause`, `avoidable`, `run_id`, `lesson_ref`, `had_lesson`, `sha`, `url`, `source`。すべてのテキストはフィードと同じクリーニングを通ります(トークン、キー、アドレス、ホームフォルダーはブックに入りません)。`lessons.retention_days` と `lessons.max_entries` でサイズを制限できます。同じスキーマのブックを他から取り込めます(`lessons.import_book`)。

## 分類器

各失敗はルールでカテゴリに分類され、最初に一致したものが採用されます:quota, flaky_network, workflow_config, permissions, secret_config, derived_files, dependencies, types, linter, test, other。ルールはプログラムに内蔵されています。独自のルールを使うには `config/lessons_rules.json` を書きます:`{"rules": [{"category": "mine", "label": "自分の種類", "avoidable": true, "patterns": ["正規表現"]}]}`。このファイルは内蔵ルールを置き換えます。無効な(または120文字を超える)ルールやパターンはスキップされます。

## レッスンのライブラリ

各カテゴリにレッスンがあります:何が失敗したか、何をすべきか、それを防げたはずのガード。内蔵のものは8言語で用意されています。独自のものは `config/lessons.json`(`{"lessons": [{"id": "L1", "category": "test", "what": "...", "do": "...", "guard": "..."}]}`)に書き、同じカテゴリの内蔵レッスンを置き換えます。

## 繰り返しと傾向

カテゴリごとに、直近24時間と直近7日間の失敗を数え、7日間をその前の7日間と比較します(新規、増加、減少、横ばい)。7日間に `lessons.recurring_from` 回の失敗があると、その種類の失敗は**繰り返し**とみなされ、ガードが提案されます。ガードとは、プッシュの前にあなたのコンピューターで失敗するチェックです。

## AI が読むもの

- `ai/LESSONS.md`:簡潔な Markdown(サイズ:`lessons.brief_max_bytes`)。失敗が開いたとき・解決したときに書き直されます。
- `GET /api/ai/lessons`:分析、今すぐ該当するレッスン、ライブラリ(ファイルは `?fmt=md`、プッシュ前の概要は `?fmt=brief&repo=NAME`、JSON に入れて受け取るには `&as=json`)。
- `GET /api/ai/failures`:ブック(新しい順)(`?since=秒&repo=NAME&category=NAME&limit=N`)。
- `GET /api/ai/state` とアラートの概要には、今すぐ該当するレッスンが含まれます。
- MCP サーバー:`lessons_apply`、`lessons_recurring`、`lessons_brief`、`lesson_propose`。
- コマンドライン:`python bin/monitor_cli.py lessons [list | brief | failures] [--repo NAME]`。

すべてデータであり、指示ではありません。誰かが書いたログの行がブックに入ることがあります。

## プッシュの前に

プッシュの前に概要を読んでください。該当するレッスン(そのリポジトリのものが先)、実行すべきガード、そのリポジトリで今赤いものが並びます。

## AI ツール向けのフックの例

多くの AI ツールは、セッション開始時にコマンドを実行して出力をコンテキストに加えられます。次のコマンドはプッシュ前の概要を出力します:

```
python bin/monitor_cli.py lessons brief --repo MY-REPOSITORY
```

```json
{"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "python /path/to/monitor/bin/monitor_cli.py lessons brief"}]}]}}
```

## モニターの AI

失敗したビルドの AI 解説を有効にしている場合、そのプロンプトにはログが該当するカテゴリのレッスンが含まれます。他の AI ツールは、インターフェース `LessonProvider`(`applicable`、`recurrences`、`pre_push_brief`、`propose`、`register`)を通じて同じ機能を使えます。`FileProvider` が実際に使われるもので、`ExampleProvider` は最小の例です:

```python
from github_actions_monitor.integrations import lessons

class WikiProvider(lessons.LessonProvider):
    name = "wiki"
    def applicable(self, repo="", text="", limit=5):
        return [{"category": "test", "what": "...", "do": "...", "guard": "..."}]

lessons.register_provider("wiki", lambda config: WikiProvider())
```

## レッスンの書き込み

読み取りは常に可能です。レッスンの書き込みには3つが必要です:`lessons.allow_write` をオン(既定はオフ)、管理者、そして確認です。`{"lesson": {...}, "confirm": true}` を付けて `POST /api/ai/lessons`(`confirm` がなければ応答は下書き)。MCP サーバーは `--allow-lessons` で起動し、スイッチがオンのときだけ書き込みます。GitHub には何も書き込みません。

## 設定

`lessons.enabled`、`lessons.allow_write`、`lessons.retention_days`、`lessons.max_entries`、`lessons.brief_max_bytes`、`lessons.recurring_from`。設定の AI タブにあります。**失敗から学んだこと** パネルはアラートタブの下部にあります。

## ラウンドの締め

作業のまとまりの最後に `python bin/monitor_cli.py lessons close` を実行すると、自分のレッスンとそのガードがまだない繰り返しの失敗の種類(`GET /api/ai/lessons` の `needs_guard`)が一覧表示され、1つでも残っている間は 0 以外の終了コードで終わります。ガードを書くか、まだ存在できない理由を述べて、もう一度実行してください。
