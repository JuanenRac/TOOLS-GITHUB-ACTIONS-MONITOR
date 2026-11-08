<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](NOTIFICATIONS.md) | [🇪🇸 Español](NOTIFICATIONS_spa.md) | [🇫🇷 Français](NOTIFICATIONS_fra.md) | [🇮🇹 Italiano](NOTIFICATIONS_ita.md) | [🇩🇪 Deutsch](NOTIFICATIONS_deu.md) | [🇨🇳 简体中文](NOTIFICATIONS_zho.md) | [🇯🇵 日本語](NOTIFICATIONS_jpn.md) | **🇵🇹 Português**

# Notificações

Opcionais e **desligadas por predefinição**. Os eventos do feed (um vermelho novo, um build preso, um build à espera da assinatura, uma ligação perdida, um run falhado avisado pelo webhook) podem ser enviados para um chat ou para um dispositivo. Uma notificação é apenas uma mensagem com uma ligação: nunca volta a executar, cancela ou escreve nada no GitHub.

## Canais

- `telegram` (um bot), `discord` e `slack` (webhook de canal), `matrix` (uma sala), `mqtt` (um broker neste computador, para luzes e sinalizadores) e `http_local` (um POST para um endereço deste computador).
- Cada canal tem o seu interruptor no separador Definições (subseparador Notificações) e um botão para enviar um teste.


## Segurança

- Os tokens e os URL de webhook nunca são guardados na configuração: define-se o NOME de uma variável de ambiente e o valor só é lido no momento do envio, sem ser mostrado nem registado.
- `discord` só aceita `discord.com` e `slack` só `hooks.slack.com`; `mqtt` e `http_local` só aceitam `127.0.0.1`, `localhost` ou `[::1]`.
- No máximo `notify.max_per_hour` mensagens saem do computador; um envio que falha é contado e ignorado, nunca para o monitor.


## O contrato dos adaptadores

- Para chegar a um serviço que não está na lista, execute um pequeno recetor neste computador e aponte `http_local` para ele. Recebe um POST com `Content-Type: application/json` e este corpo: `{"kind": "red_new", "repo": "demo-repo", "text": "...", "url": "https://.../actions/runs/1"}`.
- `kind` é um de `red_new`, `red_fixed`, `stuck_new`, `pending_sign`, `release_due`, `rate_low`, `offline`, `online`, `alerts_up`, `workflow_failed`. Os campos só se acrescentam. Responda com qualquer 2xx; o resto conta como falha.
- `mqtt` publica o mesmo JSON como carga de uma mensagem QoS 0 em `notify.channels.mqtt.topic`.

## O limite por hora conta mensagens

`notify.max_per_hour` limita as MENSAGENS que saem do computador, não os eventos: um evento enviado para três canais gasta três unidades, uma por canal. Se a quota não chega para todos os canais, os primeiros da lista recebem a mensagem e os restantes são descartados (a página conta-os como «limitados»). Um canal que não consegue enviar (sem segredo, endereço errado) não gasta nada. A contagem é feita sob um único bloqueio, por isso vários fios nunca ultrapassam o limite.
