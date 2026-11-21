<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](API.md) | [🇪🇸 Español](API_spa.md) | [🇫🇷 Français](API_fra.md) | [🇮🇹 Italiano](API_ita.md) | [🇩🇪 Deutsch](API_deu.md) | [🇨🇳 简体中文](API_zho.md) | [🇯🇵 日本語](API_jpn.md) | **🇵🇹 Português**

# A API para clientes

Aquilo em que um script, um ecrã de parede ou um cliente móvel pode confiar. Desde a 2.0.0 os endpoints de leitura estão congelados: uma chave do contrato mantém o seu nome e o seu tipo, podem aparecer chaves novas e nada é retirado ou alterado sem uma nova versão maior.

## Pedir

- No modo normal a API responde em `127.0.0.1` sem início de sessão. No modo de rede cada pedido leva o token de acesso no cabeçalho `X-Monitor-Access` (ou o cookie de sessão, ou `POST /api/access` uma vez). Com o modo equipa um script inicia sessão em `POST /api/auth/login`.
- Uma palavra da consulta que um endpoint não conhece é ignorada. As respostas são JSON em UTF-8, exceto o resumo em Markdown e os streams.

## Erros

- Um erro é JSON `{"error": "palavra"}`, por vezes com um `code`. `401 access` significa que o token falta ou está errado, `403 forbidden` que o pedido não vem de onde é permitido (também um `Host` alheio), `404` que o caminho não existe nesta edição (a lite responde 404 ao que só a completa tem), `429` que o endereço está bloqueado ou os ouvintes estão cheios.
- Uma escrita recusada nunca altera nada. As escritas não fazem parte do contrato.

## O contrato

- `docs/schemas/api_contract.json` lista cada endpoint de leitura com as suas chaves e tipos em cada edição e os códigos de erro. As rotas que se podem ler mas não estão congeladas (fluxos, texto, exportações de outras ferramentas) estão listadas em `unfrozen` no mesmo ficheiro, cada uma com o seu motivo; `/api/data`, que dá as execuções, os repositórios e a quota, está congelada. As suas chaves chegam aos elementos das listas: uma lista escrita `[{...}]` no ficheiro descreve os seus elementos (os três primeiros são verificados), pelo que as execuções, os repositórios e a quota de `/api/data`, os alertas de `/api/alerts` e `/api/auth/me` não podem mudar sem que a verificação falhe.
- `python tools/check_api_contract.py` verifica um monitor em execução contra ele (`--lite`, `--url`, `--token-file`) e imprime `CONTRACT=PASS` ou `CONTRACT=FAIL`; execute-o após cada atualização do monitor ou do seu cliente.

## API de leitura v1 (automática por predefinição)

- Defina `api.v1_enabled` (Definições, Avançado, API de leitura v1): `auto` (predefinição) responde quando o monitor corre como serviço (uma conta do modo equipa, a imagem Docker, a unidade systemd) e fica fechada para uma pessoa num só computador; `on` sempre; `off` nunca (os antigos true e false equivalem a on e off). Quando responde, cada rota de leitura é servida também em `/api/v1/` (por exemplo `/api/v1/alerts`): a mesma resposta e os mesmos papéis, mais o cabeçalho `X-API-Version: 1`. Enquanto está fechada, na edição lite e para qualquer outro número de versão, o prefixo responde 404.
- `/api/v1/me`: quem pergunta: `mode` (`individual` ou `team`), `authenticated`, `user`, e o `role` e as `accounts` da sessão de equipa (null sem ela), o que a sessão pode fazer (`capabilities`: `read`, `write`, `admin` e `v1_write`, sempre falso porque o prefixo é só de leitura), os `limits` das listas, a versão do monitor e a versão do contrato (`contract`, `1.0`: cresce com cada chave acrescentada e nunca perde uma).
- `/api/v1/repos`: os repositórios que o monitor vigia, uma linha cada um (`repo`, `ecosystem`, `state`, `risk`, `runs_24h`, `failures_24h`, `red_workflows`, `stuck_runs`, `alerts`, `last_run_at`). Filtros `state`, `ecosystem` e `q`; `limit` (por predefinição `api.default_limit`, no máximo `api.max_limit`); `cursor` (o `next_cursor` da página anterior, assinado e válido durante `api.cursor_ttl_seconds`); `fields=a,b` ou `profile=compact` para linhas mais curtas. A resposta é comprimida com gzip quando o cliente o aceita.
- `/api/v1/openapi.json`: a descrição OpenAPI 3 de toda a API de leitura congelada, construída a partir do contrato (`docs/schemas/api_contract.json`) e nunca escrita à mão: cada rota congelada com as chaves e os tipos que promete, `x-lite` (o que responde a edição lite) e `x-local-only`. As rotas que o contrato não congela são experimentais: respondem 404 em `/api/v1/` e não estão no documento, a menos que `api.experimental_routes` esteja ativado (então são listadas com `x-experimental`). As rotas antigas em `/api/` nunca mudam. Descarregue-o com `python bin/monitor_cli.py api openapi`.
- Um guia passo a passo para quem escreve um cliente, com os comandos por ordem e os erros: [API_V1_por.md](API_V1_por.md).
- `python tools/api_contract_suite.py` é a suite de contrato para clientes externos (só a biblioteca padrão, só lê): dê-lhe o endereço de um servidor (`--url`) e um token de leitura (`--token-file`) e toma o documento que o servidor serve como descrição do que verificar: a forma de cada rota sem parâmetros, o cabeçalho `X-API-Version`, o envelope de erro e os seus códigos estáveis, as páginas e os seus cursores, `fields` e `profile=compact`, gzip e que nada se pode escrever sob o prefixo. Imprime uma linha por verificação e `API_CONTRACT=PASS` ou `API_CONTRACT=FAIL` (`--json` para um documento); o código de saída é 0, 1 ou 2 (nada responde). `python bin/monitor_cli.py api contract-check` lança-a contra o monitor da linha de comandos.
- As mesmas três coisas são ferramentas do servidor MCP (`python bin/mcp_server.py`, só de leitura, sem qualquer opção): `api_me` (quem o monitor julga que o cliente é), `api_openapi` (o documento, ou uma rota com `path`) e `api_contract_check` (a suite de contrato, resposta `{ok, checks, failed, rows}`). O HTTP, a linha de comandos (`api me`, `api openapi`, `api contract-check`) e o MCP dão o mesmo documento; um teste compara-os. Enquanto o prefixo está fechado, as ferramentas dizem-no numa linha.
- As duas rotas próprias respondem um erro como `{"error": "bad_request", "code": "api.bad_cursor", "message": "..."}`: `error` e `code` são estáveis, `message` segue o idioma de `?lang=`. Códigos: api.bad_cursor, api.bad_limit, api.unknown_field, api.bad_profile, api.server_error. Tudo é só de leitura: não há nenhuma escrita sob `/api/v1/`. A forma está congelada na secção `v1_endpoints` do contrato e verifica-se com `python tools/check_api_contract.py --v1` contra um monitor com `api.v1_enabled` ativado.

### Exemplos com curl

O token é o token de acesso do modo de rede (ou use uma sessão do modo equipa); sem modo de rede não é preciso token a partir do mesmo computador. Um cliente segue `next_cursor` até ser `null` e lê primeiro `/api/v1/me` para saber a versão do contrato e o que a sessão pode fazer.

```
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/me
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?state=bad&limit=20&profile=compact"
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/openapi.json -o openapi.json
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=50&cursor=THE_NEXT_CURSOR"
```

## Streams

- `GET /api/ai/stream` (os alertas) e `GET /api/live-events/stream` (os eventos do webhook, `live.sse.enabled`) são eventos enviados pelo servidor, só de leitura e desligados por predefinição; veja [AI_ALERTS_por.md](AI_ALERTS_por.md) e [WEBHOOK_por.md](WEBHOOK_por.md).
- `POST /api/chatops/slack` e `POST /api/chatops/discord` recebem os comandos só de leitura de um chat (desligados por defeito, `chatops.enabled`). Não usam o token de acesso: a prova é a assinatura da plataforma, e um pedido sem assinatura válida é recusado antes de se ler o que quer que seja. Ver [CHATOPS_por.md](CHATOPS_por.md).

## Outras rotas da página

Estas rotas servem a página e as ferramentas deste computador. Não fazem parte do contrato congelado e podem mudar entre versões. POST altera algo; "este computador" significa que só o computador que executa o monitor a pode usar.

| Rota | O que faz |
| --- | --- |
| `/api/about` | O painel Acerca de: versões, ligações, ficheiros, saúde, créditos e o aviso de uma atualização; sem segredos. |
| `/api/act/plan` | POST, este computador. Prepara o que faria uma execução local com `act`; ainda não corre nada. |
| `/api/act/confirm` | POST, este computador. Executa um workflow neste computador com `act` depois do plano; a execução fica registada. |
| `/api/act/status` | O estado da execução local em curso. |
| `/api/act/stop` | POST, este computador. Para a execução local. |
| `/api/advanced` | O estado das funções que se ativam por escolha: a rede, o armazém do token do GitHub, as ações no GitHub, a execução local e o modo de demonstração; nunca um token. |
| `/api/ai/actions` | O estado das ações da IA (bloqueadas ou não), o seu registo, as propostas à espera (`proposals`) e o estado da IA. |
| `/api/ai/actions/confirm` | POST, este computador. Executa uma ação proposta pela IA, depois de a confirmar; fica registada. |
| `/api/ai/actions/review` | POST, este computador. Aprova ou rejeita uma proposta da IA (`id`, `decision`); fica registado. Nada é executado. |
| `/api/ai/actions/unlock` | POST, este computador. Desbloqueia as ações da IA durante um tempo limitado; fica registado. |
| `/api/ai/budget` | As chamadas e o custo estimado de hoje de cada modelo de IA, os limites e as últimas falhas; não consulta nenhum fornecedor. |
| `/api/ai/test` | POST, este computador. Testa a ligação da IA configurada; não altera nada. |
| `/api/alerts/unmute` | POST. Retira o silêncio de um alerta; fica registado. |
| `/api/analytics` | O resumo da análise das execuções: durações, fila, passos, testes instáveis e execuções mais lentas, e a estimativa do tempo poupado quando está ligada. |
| `/api/discovery` | O que a descoberta encontrou: o quadro com a conta e os repositórios mostrados e ocultos, os últimos eventos, os grupos sugeridos, as suas definições, os forks e as organizações. |
| `/api/discovery/group` | POST. Junta um grupo sugerido ao ficheiro de ecossistemas, guardando uma cópia do ficheiro. |
| `/api/gh-action/plan` | POST, este computador. Prepara o que seria enviado ao GitHub (uma repetição, um cancelamento, um dispatch ou um merge); ainda não se envia nada. |
| `/api/gh-action/confirm` | POST, este computador. Envia ao GitHub o que dizia o plano, depois de o confirmar; fica registado. Se o GitHub recusar, a resposta traz `reason`: forbidden, not_found, method, conflict ou invalid. |
| `/api/github-token` | Só este computador. O estado do armazém do token do GitHub (o sistema e se há um guardado); nunca o seu valor. |
| `/api/help/search` | Procura uma palavra nos temas de ajuda e devolve os que coincidem. |
| `/api/help/topic` | O texto de um tema de ajuda (`id=`) no idioma da página. |
| `/api/help/topics` | A lista dos temas de ajuda com os seus títulos. |
| `/api/hot-only` | POST, este computador. O interruptor "só o quente" da página; não altera nenhum estado guardado. |
| `/api/mirror` | O estado do espelho dos repositórios (desligado por predefinição). |
| `/api/mode` | GET: o modo de trabalho, a estimativa de cada modo e o tempo que resta. POST, este computador: muda o modo. |
| `/api/notify/test` | POST. Envia uma mensagem de teste a um canal de notificação; não altera nada. |
| `/api/quota-pool/status` | Só este computador. A quota de cada fonte de leituras e o que falta à GitHub App; nunca uma chave nem um token. |
| `/api/refresh-repos` | POST, este computador. Atualiza só os repositórios indicados e reescreve o ficheiro dos vermelhos (usado por `finalize --execute`). |
| `/api/screens/logo` | GET: o logótipo da organização como imagem. POST: guarda um novo (no máximo 1 MB, verificado pelo seu tipo real). |
| `/api/screens/logo/remove` | POST. Remove o logótipo da organização; fica registado. |
| `/api/sentinel/ai` | POST. Pede à IA que explique um alerta ou uma compilação; o pedido é pequeno e a pergunta é limpa de segredos antes. Não existe enquanto a IA estiver desligada. |
| `/api/sentinel/historial` | Ontem contra hoje: os vermelhos e as assinaturas pendentes que aparecem ou desaparecem. |
| `/api/sentinel/parte/save` | POST. Guarda uma cópia do relatório diário na pasta de auditoria; um GET nunca escreve. |
| `/api/sentinel/security` | O que o GitHub diz estar aberto ou em falta na segurança (a sentinela de Segurança; desligada por predefinição; só leitura). |
| `/api/session-token` | Um token de uso único para a próxima alteração de uma definição; a página pede-o mesmo antes de escrever. |
| `/api/statusbar` | O que mostra a barra no fundo da página: edição, endereço, conta e sentinelas; sem segredos e sem chamadas ao GitHub. |
| `/api/welcome` | GET: se o guia do primeiro arranque está concluído. POST, este computador: marca-o como concluído ou não. |
