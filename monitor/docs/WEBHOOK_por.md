<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](WEBHOOK.md) | [🇪🇸 Español](WEBHOOK_spa.md) | [🇫🇷 Français](WEBHOOK_fra.md) | [🇮🇹 Italiano](WEBHOOK_ita.md) | [🇩🇪 Deutsch](WEBHOOK_deu.md) | [🇨🇳 简体中文](WEBHOOK_zho.md) | [🇯🇵 日本語](WEBHOOK_jpn.md) | **🇵🇹 Português**

# Webhook de entrada

Opcional e **desligado por predefinição**. Permite que o GitHub avise o monitor de que algo mudou, para que o repositório seja atualizado no ciclo seguinte em vez de esperar pela próxima consulta.

## O que faz (só atualizar)

Um evento aceite apenas marca o repositório nele indicado para ser atualizado no ciclo seguinte. Nada é escrito no GitHub nem no disco, nenhum texto do evento é guardado ou mostrado, e só são aceites repositórios que o monitor já vigia. Eventos compreendidos: `workflow_run`, `workflow_job`, `push`, `release`, `check_suite` e `ping`; qualquer outro recebe `202` e é ignorado.

## Segurança

- O monitor continua a escutar apenas em `127.0.0.1`. O GitHub só lhe chega por um túnel que você monte de propósito; a ferramenta nunca abre um.
- Desligado até `webhook.enabled` estar ativo **e** o segredo partilhado em `actions_monitor.json` ter pelo menos 32 carateres (caso contrário o ponto de acesso fica fechado).
- Todos os pedidos têm de trazer `X-Hub-Signature-256: sha256=<hmac>`, feito com esse segredo; o resto recebe `401`. O segredo nunca é mostrado: o separador Definições só diz se está definido.
- Um corpo com mais de 256 KB recebe `413`.

## Como ativar

Em `actions_monitor.json`: `"webhook": {"enabled": true, "secret": "<32 ou mais carateres aleatórios>"}`; o interruptor também está no separador Definições (subseparador Webhook de entrada), o segredo só no ficheiro. Reinicie o monitor. Nas definições do webhook do GitHub use o tipo `application/json`, o mesmo segredo e o URL do seu túnel terminado em `/api/webhook`.

## Eventos em tempo real

- Com `webhook.record_events` ligado (predefinição), um evento `workflow_run` assinado atualiza logo a lista de runs desse repositório, sem ler o GitHub: o repositório não gasta quota até à sua próxima leitura programada. Um evento `workflow_job` traz também o tempo em fila e o de cada passo para as análises.
- Só se guardam campos curtos validados (workflow, run, estado, conclusão, ramo, commit curto, ligação ao run, durações); nunca a mensagem do commit nem texto livre. Os `webhook.live_events_keep` eventos mais recentes leem-se em `GET /api/live-events` (só este computador).
- Um run que termina a vermelho envia também a notificação `workflow_failed` se as notificações estiverem ativas. Com `webhook.record_events` desligado o webhook volta ao modo de só atualizar descrito acima.
- O GitHub não consegue chegar a `127.0.0.1`: use `gh webhook forward` (ver a documentação da CLI do GitHub) ou um túnel que monte de propósito, a apontar para `http://127.0.0.1:PORTA/api/webhook`.
