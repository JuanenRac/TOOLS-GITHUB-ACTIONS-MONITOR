<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](API_V1.md) | [🇪🇸 Español](API_V1_spa.md) | [🇫🇷 Français](API_V1_fra.md) | [🇮🇹 Italiano](API_V1_ita.md) | [🇩🇪 Deutsch](API_V1_deu.md) | [🇨🇳 简体中文](API_V1_zho.md) | [🇯🇵 日本語](API_V1_jpn.md) | **🇵🇹 Português**

# A API de leitura v1, passo a passo

Um guia para quem escreve um cliente (um script, um ecrã de parede, uma app móvel, uma ferramenta de IA) contra a API de leitura do monitor. A referência de cada rota é o documento OpenAPI que o próprio monitor serve; as regras do contrato (o que está congelado e o que pode crescer) estão em [API_por.md](API_por.md). Eis o caminho a seguir, com comandos que um teste executa contra um monitor.

## 1. A API está aberta?

O prefixo `/api/v1/` responde sozinho quando o monitor corre como serviço (uma conta do modo equipa, a imagem Docker, a unidade systemd) e fica fechado, com 404, para uma pessoa num computador. Quem decide é a definição `api.v1_enabled` (`auto`, `on`, `off`). Um cliente começa por perguntar quem é: um `404` aí significa que a API está fechada, não que o cliente esteja errado.

## 2. Identificar-se

A partir do mesmo computador e sem modo de rede não é preciso token. No modo de rede cada pedido leva o token de acesso no cabeçalho `X-Monitor-Access`, lido aqui de um ficheiro para nunca aparecer numa linha de comandos guardada no histórico; com o modo equipa um script inicia sessão em `POST /api/auth/login`. Um token de leitura é tudo o que um cliente desta API precisa: sob o prefixo não se escreve.

## 3. Os comandos

Por esta ordem: quem és e a versão do contrato (`/api/v1/me`), a descrição de cada rota congelada (`/api/v1/openapi.json`), os repositórios por páginas (filtram `state`, `ecosystem` e `q`; `limit`; `fields` ou `profile=compact` para linhas mais curtas; `cursor` é o `next_cursor` da página anterior, até ser `null`), a resposta comprimida com gzip e duas rotas da API antiga que o prefixo serve também com a mesma resposta.

```
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/me
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/openapi.json -o openapi.json
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?state=bad&limit=20&profile=compact"
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?fields=repo,state,risk&limit=5"
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=50&cursor=THE_NEXT_CURSOR"
curl -s --compressed -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=100"
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/health
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/alerts
```

## 4. Erros

Um erro das rotas próprias é um objeto JSON com três chaves: `error` e `code` são estáveis e pensados para programas, `message` segue o idioma de `?lang=` e é pensado para pessoas. Os códigos são api.bad_cursor, api.bad_limit, api.unknown_field, api.bad_profile e api.server_error. Toda a resposta do prefixo, erros incluídos, leva o cabeçalho `X-API-Version: 1`. Cada erro leva também `help`, uma frase com o passo seguinte e o guia a ler, no mesmo idioma (o campo falta quando um código não o tem; um programa que o ignore não perde nada).

```
curl -s -i -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=0"
```

A resposta, depois dos cabeçalhos, é `{"error": "bad_request", "code": "api.bad_limit", "message": "..."}`.

## 5. O mesmo a partir da linha de comandos e de uma ferramenta de IA

Três portas dão os mesmos documentos, e um teste compara-as: o HTTP como acima, a linha de comandos (`python bin/monitor_cli.py api me`, `api openapi`, `api contract-check`; acrescente `--json` para a resposta como dados) e o servidor MCP (`python bin/mcp_server.py`, só de leitura: as ferramentas `api_me`, `api_openapi` e `api_contract_check`).

## 6. Verificar um servidor antes de confiar nele

`python tools/api_contract_suite.py --url URL --token-file token.txt` toma o documento que o servidor serve como descrição do que verificar e imprime uma linha por verificação e `API_CONTRACT=PASS` ou `API_CONTRACT=FAIL`. `python tools/check_api_contract.py --v1` executa a mesma suite e compara ainda as respostas com o contrato congelado. Execute um deles depois de cada atualização do monitor ou do seu cliente; a CI do monitor executa a suite contra uma demonstração em modo serviço.
