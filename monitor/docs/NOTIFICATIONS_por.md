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
- É recusado um destino que seja, ou resolva para, um endereço de loopback, privado (10.x, 172.16-31.x, 192.168.x, fc00::/7), de ligação local (169.254.x com o endereço de metadados da nuvem, fe80::/10), partilhado (100.64.0.0/10) ou reservado, enquanto `notify.allow_private_targets` estiver desligado (predefinição). O nome é resolvido uma vez, a ligação vai para o endereço verificado e cada redirecionamento segue a mesma regra. Assim, um servidor Matrix mal indicado não chega ao router nem ao serviço de metadados de uma máquina na nuvem.
- No máximo `notify.max_per_hour` mensagens saem do computador; um envio que falha é contado e ignorado, nunca para o monitor.


## O contrato dos adaptadores

- Para chegar a um serviço que não está na lista, execute um pequeno recetor neste computador e aponte `http_local` para ele. Recebe um POST com `Content-Type: application/json` e este corpo: `{"kind": "red_new", "repo": "demo-repo", "text": "...", "url": "https://.../actions/runs/1"}`.
- `kind` é um de `red_new`, `red_fixed`, `stuck_new`, `pending_sign`, `release_due`, `rate_low`, `offline`, `online`, `alerts_up`, `workflow_failed`, `collab_new`, `collab_fixed`, `credential_blind`, `credential_back`. Os campos só se acrescentam. Responda com qualquer 2xx; o resto conta como falha.
- `mqtt` publica o mesmo JSON como carga de uma mensagem QoS 0 em `notify.channels.mqtt.topic`.

## O limite por hora conta mensagens

`notify.max_per_hour` limita as MENSAGENS que saem do computador, não os eventos: um evento enviado para três canais gasta três unidades, uma por canal. Se a quota não chega para todos os canais, os primeiros da lista recebem a mensagem e os restantes são descartados (a página conta-os como «limitados»). Um canal que não consegue enviar (sem segredo, endereço errado) não gasta nada. A contagem é feita sob um único bloqueio, por isso vários fios nunca ultrapassam o limite.

## Notificações por utilizador (modo de equipa)

Desativado por predefinição (`notify.users.enabled`). Com o modo de equipa ativo, cada utilizador escolhe em `GET/POST /api/auth/me/notify` os canais (`ntfy`, `teams`, `email`), as sentinelas (`ci`, `collab`), o nível mínimo (`info`, `warn`, `bad`), se quer os eventos do sistema e se as mensagens chegam logo ou reunidas num resumo (`hourly`, `daily`). A função decide o que um utilizador pode saber: um leitor, os eventos de CI das contas que pode ver; um mantenedor, além disso o que espera por uma pessoa (uma compilação à espera de assinatura, uma versão por publicar); um administrador, além disso os eventos do sistema. Um evento de uma conta nunca chega a quem não pode ver essa conta. `notify.users.max_per_hour` limita as mensagens que um utilizador recebe.

- `ntfy`: o tópico de cada utilizador no servidor `notify.channels.ntfy.server` (https, ou um deste computador); um token de acesso é opcional.
- `teams`: o endereço do webhook de entrada de um canal do Teams (apenas servidores da Microsoft).
- `email`: o endereço do utilizador, enviado por um relé deste computador que não pede início de sessão (`notify.channels.email`).

O endereço do webhook do Teams e o token do ntfy são guardados cifrados pelo sistema (DPAPI, Porta-chaves, Secret Service ou um ficheiro privado) e nunca voltam numa resposta, num registo nem na configuração; ao apagar um utilizador são apagados. `MONITOR_SECRET_BACKEND=file` força o ficheiro privado. Cada canal está desligado até o administrador o ativar. O resumo reúne os alertas que o utilizador não viu (até `notify.digest.max_items`); `POST /api/auth/me/notify/seen` marca-os como vistos e não são enviados; `POST /api/auth/me/notify/test` envia uma mensagem de teste aos canais do utilizador. Um administrador lê as preferências de todos (nunca um segredo) em `GET /api/auth/notify`.
