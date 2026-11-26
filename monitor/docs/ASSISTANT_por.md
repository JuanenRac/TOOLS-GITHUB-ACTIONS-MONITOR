<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# O assistente

Perguntas fixas à IA que já configurou, respondidas com os dados do monitor, só leitura. Desligado por predefinição.

## Ligá-lo

1. Configure um fornecedor de IA (`ai.provider`; ver [AI_CONNECTION_por.md](AI_CONNECTION_por.md)).
2. Nas Definições, IA, ative `ai.assistant.enabled`. O painel aparece no separador Alertas. Não existe na edição Lite.
3. Faça uma pergunta; a resposta mostra as suas fontes, quanto foi enviado e as chamadas do dia.

## As cinco perguntas

- `explain_alert`: porque há um alerta aberto (precisa do alerta).
- `summarize_week`: a situação da conta.
- `why_slow`: porque o CI de um repositório está lento ou preso (precisa do repositório).
- `explain_repo`: a situação de um repositório, as suas execuções e os seus alertas abertos.
- `prioritize`: os alertas abertos, o estado e a pontuação postos por ordem, com os seus ids.

Não há chat livre.

## O que lê

Quatro ferramentas, uma lista fechada que `ai.assistant.tools` pode reduzir: `status`, `alerts`, `runs` e `score`. No máximo `ai.assistant.max_tool_calls` leituras por pergunta e `ai.assistant.max_context` de texto enviado. Com `ai.similar.enabled` ativo, «explicar este alerta» também lista alertas parecidos, encontrados por comparação de palavras, sem modelo.

## O que nunca faz

Não escreve nada nem toca em nada no GitHub. O que um repositório escreveu (um título, o nome de um workflow) é cortado, limpo de segredos e das palavras que ocultou, e entregue como dado entre marcas, nunca como instrução. Cada pergunta gasta o único orçamento diário da IA (`ai.daily_limit`). Com `ai.airgapped` ativo só se usa um modelo deste computador ou da sua rede privada.

## Verificá-lo

`GET /api/assistant` diz o que é e os seus limites; `POST /api/assistant/ask` recebe `action` e, conforme preciso, `alert` ou `repo`. Ambas respondem 404 enquanto está desligado. A pergunta fica no registo de ações (nunca o seu texto); com `ai.prompt_log.enabled` os prompts limpos são guardados num registo local que pode ver e esvaziar nas Definições.

## Propostas que pessoas aprovam

Cada comando proposto por uma IA (`ai.actions.enabled`) fica marcado como vindo de uma IA, leva a impressão digital (SHA-256) do que seria executado e é guardado até expirar, mesmo após um reinício. Nunca corre sozinho. Aprová-lo é uma decisão de pessoas: com dois ou mais utilizadores são precisas duas pessoas (quem perguntou à IA conta como uma e não pode aprovar a sua); sozinho, escreve os oito primeiros caracteres da impressão digital. Uma pessoa basta para rejeitar. Com `ai.assistant.can_propose` (desligado) uma resposta da conversa também pode tornar-se proposta. Veem-se no separador Alertas.

## Conversa livre

`ai.chat.enabled` (desligado) acrescenta uma conversa no separador Alertas. A IA só pode ler, com as quatro ferramentas acima; pede-as e o monitor decide. Mesmo orçamento, mesma limpeza, mesmas marcas; cada resposta lista o que foi lido. Não há nenhuma ferramenta que escreva.

## Alertas parecidos com um modelo local

Com `ai.rag.enabled` (desligado) e `ai.rag.model`, «explicar este alerta» ordena pelos embeddings de um modelo que corre neste computador (API do Ollama; só endereço local). O índice guarda vetores e resumos criptográficos, nunca o texto, até `ai.rag.max_mb`; apagar `ai_rag_index.json` não perde nada. Sem modelo usa-se a comparação de palavras. Testado apenas com um servidor falso.

## Relatório de um repositório

Com `ui.copy_report.enabled` o separador Alertas copia o relatório de um repositório em Markdown, ou um rascunho de triagem, para colar à mão. Sem IA, sem pedidos ao GitHub, nada é publicado.

Rotas: `GET /api/assistant/extras`, `GET /api/assistant/repo-report?repo=`, `POST /api/assistant/chat`. Para clientes MCP os resumos também são recursos: `resources/list`, `resources/read`, `monitor://briefs/index`, `monitor://briefs/<tab>`.
