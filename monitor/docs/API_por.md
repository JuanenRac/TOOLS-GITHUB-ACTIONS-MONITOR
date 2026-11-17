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

## API de leitura v1 (desativada por predefinição)

- Ative `api.v1_enabled` (Definições, Avançado, API de leitura v1). Cada rota de leitura é então servida também em `/api/v1/` (por exemplo `/api/v1/alerts`): a mesma resposta e os mesmos papéis, mais o cabeçalho `X-API-Version: 1`. Enquanto está desativada, na edição lite e para qualquer outro número de versão, o prefixo responde 404.
- `/api/v1/me`: quem pergunta: `mode` (`individual` ou `team`), `authenticated`, `user`, e o `role` e as `accounts` da sessão de equipa (null sem ela), os `limits` das listas e a versão.
- `/api/v1/repos`: os repositórios que o monitor vigia, uma linha cada um (`repo`, `ecosystem`, `state`, `risk`, `runs_24h`, `failures_24h`, `red_workflows`, `stuck_runs`, `alerts`, `last_run_at`). Filtros `state`, `ecosystem` e `q`; `limit` (por predefinição `api.default_limit`, no máximo `api.max_limit`); `cursor` (o `next_cursor` da página anterior, assinado e válido durante `api.cursor_ttl_seconds`); `fields=a,b` ou `profile=compact` para linhas mais curtas. A resposta é comprimida com gzip quando o cliente o aceita.
- `/api/v1/openapi.json`: uma descrição OpenAPI 3 leve dessas duas rotas.
- As duas rotas próprias respondem um erro como `{"error": "bad_request", "code": "api.bad_cursor", "message": "..."}`: `error` e `code` são estáveis, `message` segue o idioma de `?lang=`. Códigos: api.bad_cursor, api.bad_limit, api.unknown_field, api.bad_profile, api.server_error. Tudo é só de leitura: não há nenhuma escrita sob `/api/v1/`. A forma está congelada na secção `v1_endpoints` do contrato e verifica-se com `python tools/check_api_contract.py --v1` contra um monitor com `api.v1_enabled` ativado.

## Streams

- `GET /api/ai/stream` (os alertas) e `GET /api/live-events/stream` (os eventos do webhook, `live.sse.enabled`) são eventos enviados pelo servidor, só de leitura e desligados por predefinição; veja [AI_ALERTS_por.md](AI_ALERTS_por.md) e [WEBHOOK_por.md](WEBHOOK_por.md).
- `POST /api/chatops/slack` e `POST /api/chatops/discord` recebem os comandos só de leitura de um chat (desligados por defeito, `chatops.enabled`). Não usam o token de acesso: a prova é a assinatura da plataforma, e um pedido sem assinatura válida é recusado antes de se ler o que quer que seja. Ver [CHATOPS_por.md](CHATOPS_por.md).
