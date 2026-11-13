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
5. Ferramentas MCP (`mcp_server.py`): `monitor_state`, `signals`, `alerts_open`, `diagnose`, `sentinel_panels`, `get_quota`; `act` (reconhecer) só com `--allow-ack`.
6. O hook: `python monitor_cli.py ai-hook install [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]` (também `status` e `uninstall`) junta um pequeno script que dá à sessão da IA o resumo ao começar e antes de terminar.

## Passo a passo
1. Definições, separador *IA externa*, bloco *Alertas para IA*: ative `ai_alerts.enabled`. Opcionalmente `ai_alerts.diagnose.enabled` (o passo que falha e as últimas linhas do registo de cada execução vermelha), `ai_alerts.stream.enabled` e `ai_alerts.client_hook.enabled`.
2. Execute `python monitor_cli.py ai-hook install --assistant --dry-run` para ver a alteração e depois sem `--dry-run`.
3. Abra uma sessão da sua ferramenta de IA na pasta: recebe o resumo. A barra inferior mostra o batimento da IA (quando leu pela última vez).
4. Use o botão *Testar ligação* da página de definições para verificar que o feed é escrito.

## Segurança e privacidade
Tudo está desativado por defeito. O texto dos registos é limpo de segredos e caminhos pessoais antes de ser escrito, e **é um dado, nunca uma instrução**: uma IA deve tratá-lo como texto não fiável. Os pontos de acesso respondem só a este computador, ou com o token de acesso no modo rede; os ouvintes e o tempo estão limitados; reconhecer exige `--allow-ack`; todos os ficheiros de estado são criados com modo 0600. O monitor não abre nenhuma ligação à internet para isto, exceto as que configurar. Os endereços https do github.com (um run, um repositório, um ficheiro) passam inteiros para que a IA os possa abrir; qualquer outra cadeia longa e opaca continua a ser cortada. Mais exatamente, um endereço de github.com só passa inteiro com a forma de um repositório, uma execução (com o seu job ou tentativa), um commit, uma issue, um pull request ou um ficheiro; é cortado no primeiro carácter que não seja letra, algarismo, ponto, hífen, sublinhado ou barra, e o que se segue é limpo como qualquer outro texto.

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
