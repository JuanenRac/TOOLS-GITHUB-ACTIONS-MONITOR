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

- `docs/schemas/api_contract.json` lista cada endpoint de leitura com as suas chaves e tipos em cada edição e os códigos de erro.
- `python tools/check_api_contract.py` verifica um monitor em execução contra ele (`--lite`, `--url`, `--token-file`) e imprime `CONTRACT=PASS` ou `CONTRACT=FAIL`; execute-o após cada atualização do monitor ou do seu cliente.

## Streams

- `GET /api/ai/stream` (os alertas) e `GET /api/live-events/stream` (os eventos do webhook, `live.sse.enabled`) são eventos enviados pelo servidor, só de leitura e desligados por predefinição; veja [AI_ALERTS_por.md](AI_ALERTS_por.md) e [WEBHOOK_por.md](WEBHOOK_por.md).
