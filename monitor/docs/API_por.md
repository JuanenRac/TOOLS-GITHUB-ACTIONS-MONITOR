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
- `python tools/api_contract_suite.py` é a suite de contrato para clientes externos (só a biblioteca padrão, só lê): dê-lhe o endereço de um servidor (`--url`) e um token de leitura (`--token-file`) e toma o documento que o servidor serve como descrição do que verificar: a forma de cada rota sem parâmetros, o cabeçalho `X-API-Version`, o envelope de erro e os seus códigos estáveis, as páginas e os seus cursores, `fields` e `profile=compact`, gzip e que nada se pode escrever sob o prefixo. Imprime uma linha por verificação e `API_CONTRACT=PASS` ou `API_CONTRACT=FAIL` (`--json` para um documento); o código de saída é 0, 1 ou 2 (nada responde). `python bin/monitor_cli.py api contract-check` lança-a contra o monitor da linha de comandos.
- As duas rotas próprias respondem um erro como `{"error": "bad_request", "code": "api.bad_cursor", "message": "..."}`: `error` e `code` são estáveis, `message` segue o idioma de `?lang=`. Códigos: api.bad_cursor, api.bad_limit, api.unknown_field, api.bad_profile, api.server_error. Tudo é só de leitura: não há nenhuma escrita sob `/api/v1/`. A forma está congelada na secção `v1_endpoints` do contrato e verifica-se com `python tools/check_api_contract.py --v1` contra um monitor com `api.v1_enabled` ativado.

## Streams

- `GET /api/ai/stream` (os alertas) e `GET /api/live-events/stream` (os eventos do webhook, `live.sse.enabled`) são eventos enviados pelo servidor, só de leitura e desligados por predefinição; veja [AI_ALERTS_por.md](AI_ALERTS_por.md) e [WEBHOOK_por.md](WEBHOOK_por.md).
- `POST /api/chatops/slack` e `POST /api/chatops/discord` recebem os comandos só de leitura de um chat (desligados por defeito, `chatops.enabled`). Não usam o token de acesso: a prova é a assinatura da plataforma, e um pedido sem assinatura válida é recusado antes de se ler o que quer que seja. Ver [CHATOPS_por.md](CHATOPS_por.md).
