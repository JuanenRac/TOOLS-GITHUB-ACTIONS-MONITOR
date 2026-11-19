<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# アシスタント

設定済みの AI への定型の質問に、モニターのデータだけで答えます。読み取り専用で、既定ではオフです。

## 有効にする

1. AI プロバイダーを設定します(`ai.provider`。[AI_CONNECTION_jpn.md](AI_CONNECTION_jpn.md) を参照)。
2. 設定の AI で `ai.assistant.enabled` をオンにします。パネルはアラートのタブに現れます。Lite エディションにはありません。
3. 質問すると、回答にその根拠、送信量、当日の呼び出し回数が表示されます。

## 5 つの質問

- `explain_alert`: あるアラートが開いている理由(アラートが必要)。
- `summarize_week`: アカウントの状況。
- `why_slow`: あるリポジトリの CI が遅い、または止まっている理由(リポジトリが必要)。
- `explain_repo`: あるリポジトリの状況、その実行と未解決のアラート。
- `prioritize`: 未解決のアラート、ステータス、スコアを ID 付きで順位づけ。

自由なチャットはありません。

## 何を読むか

ツールは 4 つで、`ai.assistant.tools` で絞れる閉じた一覧です: `status`、`alerts`、`runs`、`score`。1 回の質問で読むのは最大 `ai.assistant.max_tool_calls` 回、送るテキストは `ai.assistant.max_context` までです。`ai.similar.enabled` がオンなら、「このアラートを説明」は単語の比較で見つけた似たアラートも一覧します(モデルは使いません)。

## 決してしないこと

何も書き込まず、GitHub にも触れません。リポジトリが書いた内容(タイトルやワークフロー名)は短く切り、秘密情報と非表示にした語を取り除き、目印の間のデータとして渡します。指示としては扱いません。質問のたびに AI の 1 日分の予算(`ai.daily_limit`)を消費します。`ai.airgapped` がオンなら、このコンピューターまたは私的ネットワーク上のモデルだけを使います。

## 確かめる

`GET /api/assistant` は内容と上限を返し、`POST /api/assistant/ask` は `action` と、必要に応じて `alert` か `repo` を受け取ります。オフの間はどちらも 404 を返します。質問は操作の記録に残ります(本文は残りません)。`ai.prompt_log.enabled` がオンなら、整えたプロンプトがローカルの記録に保存され、設定で確認・消去できます。
