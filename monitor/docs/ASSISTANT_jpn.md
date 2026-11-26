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

## 人が承認する提案

AI が提案する操作（`ai.actions.enabled`）には AI 由来の印と、実行内容のハッシュ（SHA-256）が付き、再起動後も期限まで保持されます。自動で実行されることはありません。承認は人の判断です。利用者が2人以上なら2人が必要で（AI に尋ねた人は1人として数え、自分の提案は承認できません）、1人ならハッシュの先頭8文字を入力します。却下は1人でできます。`ai.assistant.can_propose`（オフ）を有効にするとチャットの回答も提案になります。通知タブに表示されます。

## 自由チャット

`ai.chat.enabled`（オフ）で通知タブにチャットが追加されます。AI は上の4つのツールで読むだけです。要求に応じてモニターが判断します。予算・マスキング・印は共通で、回答ごとに参照先を表示します。書き込むツールはありません。

## ローカルモデルによる類似通知

`ai.rag.enabled`（オフ）と `ai.rag.model` を設定すると、このコンピューター上のモデルの埋め込み（Ollama の API。ローカルアドレスのみ）で順位付けします。索引はベクトルとハッシュのみで本文は保存せず、`ai.rag.max_mb` までです。`ai_rag_index.json` を削除しても失われるものはありません。モデルがなければ単語比較を使います。疑似サーバーでのみ試験しました。

## リポジトリのレポート

`ui.copy_report.enabled` が有効なら、通知タブでリポジトリのレポート（Markdown）やトリアージの下書きをコピーできます。AI も GitHub への問い合わせも公開もありません。

ルート: `GET /api/assistant/extras`, `GET /api/assistant/repo-report?repo=`, `POST /api/assistant/chat`。MCP クライアント向けに要約はリソースとしても提供します: `resources/list`, `resources/read`, `monitor://briefs/index`, `monitor://briefs/<tab>`。
