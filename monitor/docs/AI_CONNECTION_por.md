<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AI_CONNECTION.md) | [🇪🇸 Español](AI_CONNECTION_spa.md) | [🇫🇷 Français](AI_CONNECTION_fra.md) | [🇮🇹 Italiano](AI_CONNECTION_ita.md) | [🇩🇪 Deutsch](AI_CONNECTION_deu.md) | [🇨🇳 简体中文](AI_CONNECTION_zho.md) | [🇯🇵 日本語](AI_CONNECTION_jpn.md) | **🇵🇹 Português**

# Ligar uma ferramenta de IA

O monitor pode dizer a uma ferramenta de IA (um assistente de programação com IA, um script, qualquer coisa que leia um ficheiro ou um endereço) **tudo o que diz a sua página**, para que a IA reaja a uma falha ou a um trabalho pendente tão depressa como o faria você. O monitor nunca escreve no GitHub: só informa, e o que a IA faz é decidido por si e pela ferramenta.

## O que a IA vê
Um inventário de **sinais**, os mesmos que a página mostra: o separador Agora e os seus quadros, os alertas, os repositórios, os painéis do sentinela A1..A13 e o segundo sentinela (issues e pull requests), a quota, a ligação e a saúde do monitor. Cada sinal tem um nível (`act` = alguém tem de fazer algo, `watch` = vigiar, `info`), um resumo e linhas com repositório, ligação, idade e passo seguinte. O resumo tem três blocos: **O que fazer agora**, **Pendentes** e **Saúde do monitor**, e o contador de "sinais em que agir".

| | Lite | Completa |
|---|---|---|
| Execuções, fila, workflows vermelhos, falhas das 24 horas | sim | sim |
| Quota, ligação, modo, versão, saúde | sim | sim |
| Painéis do sentinela A1..A13, segundo sentinela, candidatas a release, segurança, assinaturas | não (di-lo `panels_not_in_this_edition`) | sim |

## Os canais (os mesmos nas duas edições)
1. `ALERTS_BRIEF.md`: o Markdown curto que uma IA lê ao começar.
2. `ai_alerts.jsonl`: uma linha por evento (aberto, reconhecido, resolvido), com um id estável.
3. `GET /api/ai/state`: todo o inventário como JSON versionado (`schema`, `edition`, `signals`, `act`, `watch`), só de leitura. `GET /api/sentinel/panels` dá só os painéis.
4. `GET /api/ai/stream`: eventos em direto (SSE), retomáveis, limitados em ouvintes e em tempo.
5. Ferramentas MCP (`bin/mcp_server.py`): `monitor_state`, `signals`, `alerts_open`, `diagnose`, `sentinel_panels`, `get_quota`, `get_score`; `act` (reconhecer) só com `--allow-ack`.
6. O hook: `python bin/monitor_cli.py ai-hook install [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]` (também `status` e `uninstall`) junta um pequeno script que dá à sessão da IA o resumo ao começar e antes de terminar.

## Passo a passo
1. Definições, separador *IA externa*, bloco *Alertas para IA*: ative `ai_alerts.enabled`. Opcionalmente `ai_alerts.diagnose.enabled` (o passo que falha e as últimas linhas do registo de cada execução vermelha), `ai_alerts.stream.enabled` e `ai_alerts.client_hook.enabled`.
2. Execute `python bin/monitor_cli.py ai-hook install --assistant --dry-run` para ver a alteração e depois sem `--dry-run`.
3. Abra uma sessão da sua ferramenta de IA na pasta: recebe o resumo. A barra inferior mostra o batimento da IA (quando leu pela última vez).
4. Use o botão *Testar ligação* da página de definições para verificar que o feed é escrito.

## Segurança e privacidade
Tudo está desativado por defeito. O texto dos registos é limpo de segredos e caminhos pessoais antes de ser escrito, e **é um dado, nunca uma instrução**: uma IA deve tratá-lo como texto não fiável. Os pontos de acesso respondem só a este computador, ou com o token de acesso no modo rede; os ouvintes e o tempo estão limitados; reconhecer exige `--allow-ack`; todos os ficheiros de estado são criados com modo 0600. O monitor não abre nenhuma ligação à internet para isto, exceto as que configurar. Os endereços https do github.com (um run, um repositório, um ficheiro) passam inteiros para que a IA os possa abrir; qualquer outra cadeia longa e opaca continua a ser cortada. Mais exatamente, um endereço de github.com só passa inteiro com a forma de um repositório, uma execução (com o seu job ou tentativa), um commit, uma issue, um pull request ou um ficheiro; é cortado no primeiro carácter que não seja letra, algarismo, ponto, hífen, sublinhado ou barra, e o que se segue é limpo como qualquer outro texto.

## Como ligar, conforme a ferramenta

O monitor não depende de um assistente nem de um modelo: uma ferramenta de IA usa uma de cinco vias. Escolha a que a sua ferramenta tem.

| A sua ferramenta consegue | Via | Como | Precisa |
|---|---|---|---|
| ler ficheiros | Ficheiros | ler `ai/INDEX.json`, depois `ai/ALERTS_BRIEF.md`, `ai/ai_alerts.jsonl` e `ai/LESSONS.md` | `ai_alerts.enabled` |
| fazer pedidos HTTP | HTTP | `GET /api/ai/brief`, `/api/ai/state`, `/api/ai/lessons` | o token de acesso no modo de rede |
| falar MCP | MCP | `python bin/mcp_server.py` [`briefs_index`, `brief_tab`] (só leitura; `--allow-ack`, `--allow-lessons` para o pouco que pode escrever) | a configuração MCP da ferramenta a apontar para esse comando |
| manter uma ligação aberta | Fluxo | `GET /api/ai/stream?only=real` | `ai_alerts.stream.enabled` |
| executar comandos | Linha de comandos | `python bin/monitor_cli.py alerts`, `lessons brief --repo NOME`, `briefs show TAB`, `ai doctor`, `ai-hook install` | Python no mesmo computador |

As instruções para a IA são duas skills. `monitor_cli.py install-skill external --dest PASTA` copia-as para a pasta onde a sua ferramenta lê as skills ou regras; serve qualquer ferramenta que leia ficheiros Markdown e o texto não nomeia nenhum assistente. As skills viajam com o monitor e têm a sua versão: `GET /api/skills` devolve `monitor_version` e `monitor_cli.py --version` imprime-a. Depois de atualizar o monitor, volte a instalar numa pasta vazia ou remova a cópia antiga (um ficheiro editado nunca é substituído).

## Resolução de problemas
- *O resumo é antigo*: a página tem de estar a correr (o feed segue cada atualização); veja o batimento na barra.
- *O hook não corre*: `ai-hook status` diz onde está instalado; algumas ferramentas só leem hooks na pasta do projeto.
- *Não se escreve nada*: `ai_alerts.enabled` está desligado, ou a quota está esgotada (o resumo di-lo em Saúde do monitor).

## Definições
`ai_alerts.enabled`, `ai_alerts.folder`, `ai_alerts.brief_max_bytes`, `ai_alerts.diagnose.*`, `ai_alerts.cascade.enabled`, `ai_alerts.stream.*`, `ai_alerts.heartbeat.*`, `ai_alerts.client_hook.*`; relacionadas: `sound.enabled`, `display.blink_red_tiles`. Ver [SETTINGS_por.md](SETTINGS_por.md) e [AI_ALERTS_por.md](AI_ALERTS_por.md).

A quota do GitHub é partilhada pelo monitor, pelas ferramentas de IA e por qualquer outra ferramenta da conta. Para que o monitor não fique sem ela: o separador Quota das Definições, uma GitHub App (`github_app.enabled`), uma segunda conta só de leitura para as leituras (`extra_reader.enabled`, `extra_reader.file`: só o caminho do ficheiro do token), o painel central (`central.source`) e o modo poupança (`modes.auto_low`). O estado e o resumo dizem quando a quota se esgota e quanto gastam outras ferramentas. Ver [QUOTA_por.md](QUOTA_por.md).

## O aviso ativo a uma IA externa (opcional, desativado por predefinição)

Além do feed que uma IA lê (`ALERTS_BRIEF.md`, o stream, o servidor MCP), o monitor pode **avisar** uma IA externa quando se abre um NOVO alerta real. É o bloco `ai_notify` das Definições, separador *IA*, e cada interruptor dele só se altera a partir deste computador:

- `ai_notify.enabled` (desativado). Não é enviado nada enquanto estiver desativado.
- **Uma primeira confirmação por fornecedor**: o fornecedor é o do bloco IA (`ai.provider`); não sai nada até escrever o seu nome em `ai_notify.confirmed_provider`. Se mudar de fornecedor, confirma outra vez. Para o comando de saída (abaixo), escreva `command`.
- **Só os campos redigidos de uma lista fechada**: gravidade, classe, repositório, workflow, conclusão, sequência, causa, passo seguinte e ligação, cada um limpo como o feed (tokens, chaves, endereços de e-mail, endereços IP e pastas pessoais removidos). Os registos, os diagnósticos e tudo o resto do alerta ficam em casa.
- **Limites**: `ai_notify.max_calls_per_hour` (4) e `ai_notify.max_cost_per_hour_cents` com `ai_notify.cost_per_call_cents` (o custo que declara, porque o monitor não pode saber o preço do seu plano). Uma chamada é contada antes de ser feita, pelo que um fornecedor que falha também gasta o limite.
- **A chave pelo nome de uma variável**: o monitor lê a variável indicada em `ai.api_key_env`; a chave nunca é guardada, registada nem enviada para lado nenhum a não ser para o fornecedor.
- **A IA nunca executa uma ação**: a sua resposta é cortada, as suas ligações são neutralizadas e é apenas escrita em `ai_notify.jsonl` junto ao feed; nada dela é lido como comando e nada das ações do assistente (`ai.actions.*`) é alcançável a partir daqui.
- **A variante de um comando de saída**: `ai_notify.command` (só no ficheiro de configuração, nunca na página de Definições) indica UM ficheiro pelo caminho absoluto; é iniciado sem shell e sem argumentos e recebe o mesmo JSON redigido na sua entrada padrão.

O aviso é enviado a partir de um fio de execução próprio, pelo que um fornecedor lento nunca retém o ciclo.

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
