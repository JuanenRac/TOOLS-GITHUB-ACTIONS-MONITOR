<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AI.md) | [🇪🇸 Español](AI_spa.md) | [🇫🇷 Français](AI_fra.md) | [🇮🇹 Italiano](AI_ita.md) | [🇩🇪 Deutsch](AI_deu.md) | [🇨🇳 简体中文](AI_zho.md) | **🇯🇵 日本語** | [🇵🇹 Português](AI_por.md)

# センチネルの AI アシスタント

任意で**既定ではオフ**です。言語モデルが日次レポートの要約、アラートの仕分け、失敗した実行の説明、リリースノートの下書き、リポジトリに関する質問への回答を行えます。書かれた内容はすべて未検証の提案として表示されます。

## プロバイダー

- `ollama`:このコンピューター上のモデル(`127.0.0.1` のみ。何も外部に出ません)。
- `openai-compatible`:OpenAI 形式のチャットエンドポイントを持つ任意のサービス。Gemini(OpenAI 互換エンドポイント)や OpenAI 自体にも使えます。`base_url`、`model`、キーを保持する変数の名前を設定します。
- `anthropic`:Anthropic の Messages API(`https://api.anthropic.com`、ヘッダー `x-api-key` と `anthropic-version`)。モデルはあなたが選びます。組み込みのモデルはありません。
- `copilot`:自分の GitHub ログインで `gh copilot` を実行(モニターにキーは不要)。テキスト回答のみでツールは使いません。Copilot プランのプレミアムリクエストを消費します。CLI を導入するため、一度 `gh copilot` を手動で実行してください。
- キーは保存されません。環境変数の名前を設定します。3 つのリモートプロバイダーはリポジトリのデータを第三者に送信します。


## 参照できるもの

- すべての入力は整えられます:制御文字の除去、パターンによるシークレットの伏字化、長さの制限、ランダムな区切りで囲み信頼できないデータとして宣言。回答は切り詰められ、リンクは無効化されます。
- 設定タブで、分析できるイベントの種類(`build`、`codeql`、`report`)、参照できるリポジトリ(空ならモニターが監視するもの)、回答の言語、1 日の呼び出し上限、サイズ上限を選べます。ボタンで接続をテストでき、ページには本日の呼び出し数が表示されます。


## アクションの提案と実行

- レベル 3(`ai.actions.enabled`):回答中のコマンドは、限定リストに一致する場合のみ残ります:`gh run rerun N --failed`、`gh run rerun N`、`gh issue close N`、`act -W FILE -j JOB`(最後のものは表示のみ)。表示されるコマンドは検証済みの要素から組み立て直したもので、モデルのテキストのコピーではありません。リポジトリと実行/issue 番号はモニターが既に監視しているものに限ります。
- レベル 4(`ai.actions.execute`、独立したスイッチ、既定オフ):各提案に確認ボタンがあり、ダイアログにコマンド全文が表示され、承認するまで何も実行されません。自分の `gh` ログインでシェルなしに実行され、1 時間に最大 `ai.actions.max_per_hour` 件、各試行はページに表示されるローカルログに記録され、2 回連続で失敗するとロック解除するまでアクションはロックされます。
- 意図的にリストに無いもの:ブランチの削除、プルリクエストのクローズやマージ、シークレットや設定に関わるすべて。

## 互換性のあるAI

モニターがすでに通信方式に対応しているホスト型サービスとローカルサーバー(`openai-compatible`、`anthropic`、`ollama`)です。これは推奨ではなく中立の一覧です。初期状態ではどれも有効ではなく、キーは常に、名前を指定した環境変数から読み取られます(設定、ログ、レポート、APIには決して入力・出力されません)。プリセットは、アドレス、その変数名、例のモデルだけを入力します(編集可能。何もダウンロードされず、モデルの重みも同梱されません)。AI設定でプリセットを選び、入力ボタンを押し、確認して保存し、「接続テスト」を押してください。一覧はデータ(`ai_presets.json`)で、`GET /api/ai/presets` から読み取り専用で提供されます。

| 名前 | 種類 | プロバイダー | アドレス | キーの変数 | モデルの例 | プライバシー | 状態 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenAI | ホスト型 | `openai-compatible` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini`, `gpt-4.1-mini` | インターネット経由で送信 | プロトコル互換で、このツールでは未検証 |
| Anthropic | ホスト型 | `anthropic` | `既定のアドレス` | `ANTHROPIC_API_KEY` | `claude-sonnet-5-5` | インターネット経由で送信 | プロトコル互換で、このツールでは未検証 |
| Google Gemini | ホスト型 | `openai-compatible` | `https://generativelanguage.googleapis.com/v1beta/openai` | `GEMINI_API_KEY` | `gemini-2.5-flash` | インターネット経由で送信 | 公式ドキュメントで確認したアドレス。プロトコル互換で、このツールでは未検証 |
| xAI Grok | ホスト型 | `openai-compatible` | `https://api.x.ai/v1` | `XAI_API_KEY` | `grok-4` | インターネット経由で送信 | プロトコル互換で、このツールでは未検証 |
| Mistral | ホスト型 | `openai-compatible` | `https://api.mistral.ai/v1` | `MISTRAL_API_KEY` | `mistral-small-latest` | インターネット経由で送信 | プロトコル互換で、このツールでは未検証 |
| DeepSeek | ホスト型 | `openai-compatible` | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` | `deepseek-chat` | インターネット経由で送信 | プロトコル互換で、このツールでは未検証 |
| Groq | ホスト型 | `openai-compatible` | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | インターネット経由で送信 | プロトコル互換で、このツールでは未検証 |
| OpenRouter | ホスト型 | `openai-compatible` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `meta-llama/llama-3.3-70b-instruct` | インターネット経由で送信 | プロトコル互換で、このツールでは未検証 |
| Together AI | ホスト型 | `openai-compatible` | `https://api.together.ai/v1` | `TOGETHER_API_KEY` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | インターネット経由で送信 | 公式ドキュメントで確認したアドレス。プロトコル互換で、このツールでは未検証 |
| Fireworks AI | ホスト型 | `openai-compatible` | `https://api.fireworks.ai/inference/v1` | `FIREWORKS_API_KEY` | `accounts/fireworks/models/llama-v3p1-8b-instruct` | インターネット経由で送信 | 公式ドキュメントで確認したアドレス。プロトコル互換で、このツールでは未検証 |
| Perplexity | ホスト型 | `openai-compatible` | `https://api.perplexity.ai` | `PERPLEXITY_API_KEY` | `sonar` | インターネット経由で送信 | 公式ドキュメントで確認したアドレス。プロトコル互換で、このツールでは未検証 |
| Cohere | ホスト型 | `openai-compatible` | `https://api.cohere.ai/compatibility/v1` | `COHERE_API_KEY` | `command-a-03-2025` | インターネット経由で送信 | 公式ドキュメントで確認したアドレス。プロトコル互換で、このツールでは未検証 |
| Ollama | ローカル | `ollama` | `http://127.0.0.1:11434` | なし(ローカルサーバー) | `llama3.2`, `mistral`, `qwen2.5`, `deepseek-r1` | このコンピューターから出ない | プロトコル互換で、このツールでは未検証 |
| LM Studio | ローカル | `openai-compatible` | `http://127.0.0.1:1234/v1` | なし(ローカルサーバー) | `llama-3.2-3b-instruct`, `qwen2.5-7b-instruct`, `gemma-3-4b-it`, `phi-4` | このコンピューターから出ない | プロトコル互換で、このツールでは未検証 |
| llama.cpp server | ローカル | `openai-compatible` | `http://127.0.0.1:8080/v1` | なし(ローカルサーバー) | `llama-3.2-3b-instruct`, `mistral-7b-instruct`, `qwen2.5-7b-instruct` | このコンピューターから出ない | プロトコル互換で、このツールでは未検証 |
| vLLM | ローカル | `openai-compatible` | `http://127.0.0.1:8000/v1` | なし(ローカルサーバー) | `meta-llama/Llama-3.2-3B-Instruct`, `Qwen/Qwen2.5-7B-Instruct`, `mistralai/Mistral-7B-Instruct-v0.3` | このコンピューターから出ない | プロトコル互換で、このツールでは未検証 |
| LocalAI | ローカル | `openai-compatible` | `http://127.0.0.1:8081/v1` | なし(ローカルサーバー) | `llama-3.2-3b-instruct`, `mixtral-8x7b-instruct`, `phi-4` | このコンピューターから出ない | プロトコル互換で、このツールでは未検証 |
| Jan | ローカル | `openai-compatible` | `http://127.0.0.1:1337/v1` | なし(ローカルサーバー) | `llama3.2-3b-instruct`, `qwen2.5-7b-instruct`, `gemma-3-4b-it` | このコンピューターから出ない | プロトコル互換で、このツールでは未検証 |
