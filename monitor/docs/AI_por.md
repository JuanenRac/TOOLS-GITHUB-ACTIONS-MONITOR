<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AI.md) | [🇪🇸 Español](AI_spa.md) | [🇫🇷 Français](AI_fra.md) | [🇮🇹 Italiano](AI_ita.md) | [🇩🇪 Deutsch](AI_deu.md) | [🇨🇳 简体中文](AI_zho.md) | [🇯🇵 日本語](AI_jpn.md) | **🇵🇹 Português**

# O assistente de IA da sentinela

Opcional e **desligado por predefinição**. Um modelo de linguagem pode resumir o relatório diário, triar alertas, explicar um run falhado, redigir notas de versão e responder a uma pergunta sobre um repositório. Tudo o que escreve é mostrado como proposta por verificar.

## Fornecedores

- `ollama`: um modelo neste computador (só `127.0.0.1`; nada sai do computador).
- `openai-compatible`: qualquer serviço com um endpoint de chat ao estilo OpenAI. Serve também para o Gemini (o seu endpoint compatível com OpenAI) e para a própria OpenAI: defina `base_url`, `model` e o NOME da variável que guarda a chave.
- `anthropic`: a API Messages da Anthropic (`https://api.anthropic.com`, cabeçalhos `x-api-key` e `anthropic-version`). O modelo é você que o escolhe; nenhum vem incorporado.
- `copilot`: `gh copilot` com o seu próprio acesso ao GitHub (sem chave no monitor), só resposta de texto e sem ferramentas. Gasta pedidos premium do seu plano Copilot. Execute `gh copilot` uma vez à mão para instalar a CLI.
- A chave nunca é guardada: define-se o NOME de uma variável de ambiente. Os três fornecedores remotos ENVIAM dados dos seus repositórios a terceiros.


## O que pode ver

- Toda a entrada é limpa: carateres de controlo removidos, segredos ocultados por padrão, comprimento limitado, conteúdo entre delimitadores aleatórios e declarado não fiável. A resposta é cortada e as suas ligações neutralizadas.
- O mesmo limpador único (tokens, chaves, credenciais dentro de endereços, endereços de e-mail, endereços IP, a sua pasta pessoal) serve este assistente, o feed para IAs, os endpoints e o gancho. Funciona por padrões: reduz o risco, não é uma garantia. Uma chamada a um fornecedor nunca segue um redirecionamento (a chave iria para outro endereço) e não usa as variáveis de proxy do ambiente: um servidor deste computador é chamado diretamente e um remoto só passa pelo proxy com `network.use_proxy`.
- No separador Definições escolhe os tipos de evento que pode analisar (`build`, `codeql`, `report`), os repositórios que pode ver (vazio = os que o monitor vigia), o idioma das respostas, o limite diário de chamadas e os limites de tamanho. Um botão testa a ligação e a página mostra as chamadas de hoje.


## Propor e executar ações

- Nível 3 (`ai.actions.enabled`): um comando da resposta só é mantido se corresponder à LISTA FECHADA: `gh run rerun N --failed`, `gh run rerun N`, `gh issue close N` e `act -W FICHEIRO -j JOB` (este último só é mostrado). O comando mostrado é reconstruído a partir das peças verificadas, nunca copiado do modelo; o repositório e o número do run ou issue têm de ser já vigiados pelo monitor.
- Nível 4 (`ai.actions.execute`, interruptor próprio, desligado): cada proposta tem um botão de confirmar; uma janela mostra o comando inteiro e nada corre até aceitar. Corre com o seu próprio `gh`, sem shell, no máximo `ai.actions.max_per_hour` por hora, cada tentativa vai para o registo local mostrado pela página, e após duas falhas seguidas as ações ficam bloqueadas até as desbloquear.
- Fora da lista, de propósito: apagar ramos, fechar ou fundir pull requests, qualquer coisa sobre segredos ou definições.

## Modelos do fornecedor

O nome do modelo é texto livre, mas o monitor pode ler a lista de modelos do fornecedor e verificar o nome com ela. Os modelos e as versões mudam com frequência, por isso o monitor não traz nenhuma lista de modelos: os exemplos das predefinições podem estar desatualizados.

- **A lista.** Definições, separador *IA externa*, bloco *Modelos e dados por modelo*: *Carregar os modelos do fornecedor* lê a lista (`/models` de um servidor ao estilo OpenAI, a lista equivalente da API da Anthropic, `/api/tags` do Ollama) com um pedido só de leitura. A chave vai num cabeçalho, é lida da sua variável de ambiente e nunca é guardada. Procure na lista e escolha um modelo com *Usar este modelo*. A lista é guardada e limitada por `ai.catalog.ttl_minutes` e `ai.catalog.max_requests_per_day`. Com `ai.catalog.enabled` ligado (desligado por predefinição) o monitor também avisa quando o modelo configurado deixa de aparecer na lista (retirado ou renomeado); desligado, só você desencadeia a leitura.
- **Dados por modelo.** A janela de contexto, o preço de entrada e de saída por milhão de tokens e se aceita ferramentas só são preenchidos com o que o fornecedor devolve; o que não diz fica *desconhecido* (nunca se inventa um valor). Pode escrever os seus próprios valores; os seus prevalecem. Com `ai.catalog.fit_context` ligado (desligado por predefinição) o limite de entrada é ajustado à janela de contexto quando esta é conhecida.
- **Testar um modelo.** *Testar este modelo* ou `monitor_cli.py ai test --provider NOME --model NOME` pergunta ao modelo sobre uma falha SINTÉTICA (nunca dados dos seus repositórios) e mostra a latência, os tokens, o custo estimado e uma resposta de exemplo. Conta como uma chamada do limite diário e o resultado («testado», com a data local) fica na tabela.
- **Comandos.** `monitor_cli.py ai models [--refresh]` mostra os modelos e os dados; `ai doctor` explica porque é que uma IA não responde (variável da chave por definir, modelo desconhecido, quota, rede) e nunca imprime uma chave.
- **Rotas.** `GET /api/ai/models` (a lista guardada, a verificação e a tabela; só leitura) e, apenas a partir deste computador, `POST /api/ai/models/refresh`, `POST /api/ai/models/test`, `POST /api/ai/models/data` e `POST /api/ai/doctor`.

## IAs compatíveis

Serviços alojados e servidores locais cujo protocolo o monitor já fala (`openai-compatible`, `anthropic` ou `ollama`). A lista é uma tabela neutra, não uma recomendação: nenhuma está ativa por predefinição, a chave é lida SEMPRE de uma variável de ambiente cujo nome indica (nunca escrita numa definição, nem num registo, num relatório ou na API) e a predefinição só preenche o endereço, o nome dessa variável e um modelo de exemplo (editável; nada é descarregado e não se incluem pesos de modelos). Nas definições de IA escolha uma predefinição, prima o botão de preencher, reveja, guarde e prima «Testar ligação». A lista são dados (`ai_presets.json`) servidos só de leitura em `GET /api/ai/presets`.

| Nome | Tipo | Fornecedor | Endereço | Variável da chave | Modelos de exemplo | Privacidade | Estado |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OpenAI | alojado | `openai-compatible` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini`, `gpt-4.1-mini` | enviado pela internet | endereço lido na documentação pública; compatível por protocolo, não testado com esta ferramenta |
| Anthropic | alojado | `anthropic` | `endereço predefinido` | `ANTHROPIC_API_KEY` | — | enviado pela internet | compatível por protocolo, não testado com esta ferramenta |
| Google Gemini | alojado | `openai-compatible` | `https://generativelanguage.googleapis.com/v1beta/openai` | `GEMINI_API_KEY` | `gemini-2.5-flash` | enviado pela internet | endereço lido na documentação pública; compatível por protocolo, não testado com esta ferramenta |
| xAI Grok | alojado | `openai-compatible` | `https://api.x.ai/v1` | `XAI_API_KEY` | `grok-4.7` | enviado pela internet | endereço lido na documentação pública; compatível por protocolo, não testado com esta ferramenta |
| Mistral | alojado | `openai-compatible` | `https://api.mistral.ai/v1` | `MISTRAL_API_KEY` | `mistral-small-latest` | enviado pela internet | endereço lido na documentação pública; compatível por protocolo, não testado com esta ferramenta |
| DeepSeek | alojado | `openai-compatible` | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` | `deepseek-flash` | enviado pela internet | endereço lido na documentação pública; compatível por protocolo, não testado com esta ferramenta |
| Groq | alojado | `openai-compatible` | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` | enviado pela internet | endereço lido na documentação pública; compatível por protocolo, não testado com esta ferramenta |
| OpenRouter | alojado | `openai-compatible` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `meta-llama/llama-3.3-70b-instruct` | enviado pela internet | endereço lido na documentação pública; compatível por protocolo, não testado com esta ferramenta |
| Together AI | alojado | `openai-compatible` | `https://api.together.ai/v1` | `TOGETHER_API_KEY` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` | enviado pela internet | endereço lido na documentação pública; compatível por protocolo, não testado com esta ferramenta |
| Fireworks AI | alojado | `openai-compatible` | `https://api.fireworks.ai/inference/v1` | `FIREWORKS_API_KEY` | `accounts/fireworks/models/llama-v3p1-8b-instruct` | enviado pela internet | endereço lido na documentação pública; compatível por protocolo, não testado com esta ferramenta |
| Perplexity | alojado | `openai-compatible` | `https://api.perplexity.ai` | `PERPLEXITY_API_KEY` | `sonar` | enviado pela internet | endereço lido na documentação pública; compatível por protocolo, não testado com esta ferramenta |
| Cohere | alojado | `openai-compatible` | `https://api.cohere.ai/compatibility/v1` | `COHERE_API_KEY` | `command-a-03-2025` | enviado pela internet | endereço lido na documentação pública; compatível por protocolo, não testado com esta ferramenta |
| Ollama | local | `ollama` | `http://127.0.0.1:11434` | nenhuma (servidor local) | `llama3.2`, `mistral`, `qwen2.5`, `deepseek-r1` | fica neste computador | compatível por protocolo, não testado com esta ferramenta |
| LM Studio | local | `openai-compatible` | `http://127.0.0.1:1234/v1` | nenhuma (servidor local) | `llama-3.2-3b-instruct`, `qwen2.5-7b-instruct`, `gemma-3-4b-it`, `phi-4` | fica neste computador | compatível por protocolo, não testado com esta ferramenta |
| llama.cpp server | local | `openai-compatible` | `http://127.0.0.1:8080/v1` | nenhuma (servidor local) | `llama-3.2-3b-instruct`, `mistral-7b-instruct`, `qwen2.5-7b-instruct` | fica neste computador | compatível por protocolo, não testado com esta ferramenta |
| vLLM | local | `openai-compatible` | `http://127.0.0.1:8000/v1` | nenhuma (servidor local) | `meta-llama/Llama-3.2-3B-Instruct`, `Qwen/Qwen2.5-7B-Instruct`, `mistralai/Mistral-7B-Instruct-v0.3` | fica neste computador | compatível por protocolo, não testado com esta ferramenta |
| LocalAI | local | `openai-compatible` | `http://127.0.0.1:8081/v1` | nenhuma (servidor local) | `llama-3.2-3b-instruct`, `mixtral-8x7b-instruct`, `phi-4` | fica neste computador | compatível por protocolo, não testado com esta ferramenta |
| Jan | local | `openai-compatible` | `http://127.0.0.1:1337/v1` | nenhuma (servidor local) | `llama3.2-3b-instruct`, `qwen2.5-7b-instruct`, `gemma-3-4b-it` | fica neste computador | compatível por protocolo, não testado com esta ferramenta |
