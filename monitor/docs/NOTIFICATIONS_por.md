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
- `kind` é um de `red_new`, `red_fixed`, `stuck_new`, `pending_sign`, `release_due`, `rate_low`, `offline`, `online`, `alerts_up`, `workflow_failed`, `ai_alert`, `collab_new`, `collab_fixed`, `credential_blind`, `credential_back`, `score_dropped`, `security_new`, `security_fixed`, `delivery_new`, `delivery_fixed`, `alerts_digest`, `silence_review`. Os campos só se acrescentam. Responda com qualquer 2xx; o resto conta como falha.
- `mqtt` publica o mesmo JSON como carga de uma mensagem QoS 0 em `notify.channels.mqtt.topic`.

## Apprise (opcional, desligado por predefinição)

O canal `apprise` entrega a mensagem ao comando `apprise` (instale-o você, por exemplo `pip install apprise`) para chegar a qualquer um dos serviços que ele conhece. Os endereços contêm os segredos desses serviços, por isso estão numa variável de ambiente cujo NOME é `notify.channels.apprise.urls_env` (separados por espaços ou vírgulas, no máximo dez); são escritos num ficheiro temporário privado durante o instante da chamada, nunca nos argumentos do comando, e o comando recebe um ambiente sem as chaves do monitor. **O Apprise abre as suas próprias ligações: a proteção do monitor contra endereços privados não se aplica**, por isso o que alcança depende dos endereços que lhe der; é por isso que o canal tem o seu próprio interruptor, desligado por predefinição, e está marcado como definição de segurança. Se o comando faltar, o canal diz `not_installed`; uma falha conta-se como qualquer outra e nunca pára o monitor.

## O limite por hora conta mensagens

`notify.max_per_hour` limita as MENSAGENS que saem do computador, não os eventos: um evento enviado para três canais gasta três unidades, uma por canal. Se a quota não chega para todos os canais, os primeiros da lista recebem a mensagem e os restantes são descartados (a página conta-os como «limitados»). Um canal que não consegue enviar (sem segredo, endereço errado) não gasta nada. A contagem é feita sob um único bloqueio, por isso vários fios nunca ultrapassam o limite.

## Notificações por utilizador (modo de equipa)

Desativado por predefinição (`notify.users.enabled`). Com o modo de equipa ativo, cada utilizador escolhe em `GET/POST /api/auth/me/notify` os canais (`ntfy`, `teams`, `email`), as sentinelas (`ci`, `collab`), o nível mínimo (`info`, `warn`, `bad`), se quer os eventos do sistema e se as mensagens chegam logo ou reunidas num resumo (`hourly`, `daily`). A função decide o que um utilizador pode saber: um leitor, os eventos de CI das contas que pode ver; um mantenedor, além disso o que espera por uma pessoa (uma compilação à espera de assinatura, uma versão por publicar); um administrador, além disso os eventos do sistema. Um evento de uma conta nunca chega a quem não pode ver essa conta. `notify.users.max_per_hour` limita as mensagens que um utilizador recebe.

- `ntfy`: o tópico de cada utilizador no servidor `notify.channels.ntfy.server` (https, ou um deste computador); um token de acesso é opcional.
- `teams`: o endereço do webhook de entrada de um canal do Teams (apenas servidores da Microsoft).
- `email`: o endereço do utilizador, enviado por um relé deste computador que não pede início de sessão (`notify.channels.email`).

O endereço do webhook do Teams e o token do ntfy são guardados cifrados pelo sistema (DPAPI, Porta-chaves, Secret Service ou um ficheiro privado) e nunca voltam numa resposta, num registo nem na configuração; ao apagar um utilizador são apagados. `MONITOR_SECRET_BACKEND=file` força o ficheiro privado. Cada canal está desligado até o administrador o ativar. O resumo reúne os alertas que o utilizador não viu (até `notify.digest.max_items`); `POST /api/auth/me/notify/seen` marca-os como vistos e não são enviados; `POST /api/auth/me/notify/test` envia uma mensagem de teste aos canais do utilizador. Um administrador lê as preferências de todos (nunca um segredo) em `GET /api/auth/notify`.

### O painel de cada utilizador

No modo de equipa, o menu do utilizador com sessão iniciada (o nome no topo) tem a entrada **Notificações**. O painel mostra e guarda as mesmas preferências que `GET/POST /api/auth/me/notify`: se quer notificações, os canais (ntfy com o seu tópico e um token opcional, Teams com o endereço web do canal, correio com um endereço), as sentinelas (CI, colaboração), o nível mínimo, os eventos do sistema (só para um administrador) e se cada alerta chega de imediato ou num resumo por hora ou por dia. Um segredo já guardado é mostrado como guardado e nunca volta à página; só é enviado se escrever um novo, e uma caixa vazia mantém-no. **Enviar um teste** manda uma mensagem aos seus canais e **Vi os meus alertas** marca os pendentes como vistos. Se o administrador não ativou `notify.users.enabled`, o painel di-lo: pode guardar as suas escolhas, ainda não é enviado nada.

## Muitos avisos, ou sempre os mesmos

Quatro definições opcionais do bloco `alerts` (todas desligadas ou vazias por defeito) decidem o que chega aos canais acima. As listas, o separador Alertas e o registo de eventos continuam a mostrar tudo.

- **Silenciamentos permanentes** (`alerts.silences`): uma entrada por linha, `repositório:workflow:ramo;motivo;data de revisão`. Tudo exceto o repositório é opcional e `*` corresponde a qualquer texto. Os avisos que correspondem são mostrados como silenciados, ninguém é notificado e na data de revisão é anunciado um lembrete; o silenciamento continua até o remover.
- **Serviços e crons curtos** (`alerts.service`): um workflow que só corre agendado ou à mão e falha de vez em quando só é anunciado depois de `failures` falhas seguidas, ou quando `rate_percent` dos seus últimos runs falhou; anunciado uma vez e levantado uma vez em vez de avisar em ciclo. `workflows` junta mais workflows a esta classe.
- **Agrupar por commit** (`alerts.group`): quando `min` ou mais workflows de um repositório ficam a vermelho no mesmo commit, uma notificação lista-os.
- **Resumo quando há muitos** (`alerts.digest`): depois de `threshold` notificações na última hora, as restantes são retidas e comunicadas num resumo a cada `minutes` minutos. Os eventos retidos ficam no registo de eventos.
