<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](WEBHOOK.md) | [🇪🇸 Español](WEBHOOK_spa.md) | [🇫🇷 Français](WEBHOOK_fra.md) | [🇮🇹 Italiano](WEBHOOK_ita.md) | [🇩🇪 Deutsch](WEBHOOK_deu.md) | [🇨🇳 简体中文](WEBHOOK_zho.md) | [🇯🇵 日本語](WEBHOOK_jpn.md) | **🇵🇹 Português**

# Webhook de entrada

Opcional e **desligado por predefinição**. Permite que o GitHub avise o monitor de que algo mudou, para que o repositório seja atualizado no ciclo seguinte em vez de esperar pela próxima consulta.

## O que faz (só atualizar)

Um evento aceite apenas marca o repositório nele indicado para ser atualizado no ciclo seguinte. Nada é escrito no GitHub nem no disco, nenhum texto do evento é guardado ou mostrado, e só são aceites repositórios que o monitor já vigia. Eventos compreendidos: `workflow_run`, `workflow_job`, `push`, `release`, `check_run`, `check_suite` e `ping`; qualquer outro recebe `202` e é ignorado.

## Segurança

- O monitor continua a escutar apenas em `127.0.0.1`. O GitHub só lhe chega por um túnel que monte de propósito; a ferramenta nunca abre nenhum.
- Desligado até `webhook.enabled` estar ativo **e** o segredo partilhado (32 carateres ou mais) estar na variável de ambiente indicada por `webhook.secret_env` (`MONITOR_WEBHOOK_SECRET` por omissão; `MONITOR_WEBHOOK_SECRET_FILE` pode indicar um ficheiro cuja primeira linha é o segredo, como fazem os segredos de um contentor). O segredo nunca é escrito em `actions_monitor.json`, mostrado, registado nem herdado pelos programas que o monitor lança; o separador Definições só diz se está definido. A forma antiga (um `secret` no ficheiro) só é lida se `webhook.allow_config_secret` for verdadeiro, e a vista em direto avisa enquanto for usada.
- Todo o pedido tem de levar `X-Hub-Signature-256: sha256=<hmac>`, feito com esse segredo e comparado em tempo constante; qualquer outro recebe `401`, e nada do conteúdo é visto antes de a assinatura ser verificada.
- Um corpo com mais de 256 KB recebe `413`, antes de se calcular o que quer que seja.
- As listas são fechadas: só se atua sobre `workflow_run`, `workflow_job`, `check_run`, `push`, `release`, `check_suite` e `ping`, de um evento só se guardam campos curtos e validados (nunca uma mensagem de commit nem texto livre), e tudo o resto recebe `202` e é descartado.

## Como ativar

1. Crie um segredo de 32 ou mais carateres aleatórios, por exemplo `python -c "import secrets; print(secrets.token_hex(32))"`.
2. Entregue-o ao monitor pelo seu ambiente, nunca pelo ficheiro: `$env:MONITOR_WEBHOOK_SECRET = "<o segredo>"` no PowerShell antes de arrancar o monitor, `export MONITOR_WEBHOOK_SECRET=...` numa shell, `Environment=` ou `EnvironmentFile=` (um ficheiro que só você possa ler) num serviço, `-e` ou um ficheiro de segredo indicado por `MONITOR_WEBHOOK_SECRET_FILE` num contentor.
3. Ative o recetor (Definições > Webhook de entrada > Recetor ativo, ou `"webhook": {"enabled": true}` em `actions_monitor.json`) e reinicie o monitor.
4. Torne o endereço acessível: o GitHub não chega a `127.0.0.1`. Use um túnel que monte de propósito (um endereço HTTPS terminado em `/api/webhook`) ou, neste computador, `gh webhook forward` para `http://127.0.0.1:PORTA/api/webhook` (veja a documentação da CLI do GitHub para lhe dar o mesmo segredo sem o escrever na linha de comandos).
5. No GitHub abra o repositório (ou a organização) > Settings > Webhooks > Add webhook. **Payload URL**: o endereço do seu túnel terminado em `/api/webhook`. **Content type**: `application/json`. **Secret**: o mesmo segredo. **SSL verification**: ativa. **Events**: «Let me select individual events», depois Workflow runs e Workflow jobs, e opcionalmente Check runs, Pushes e Releases. **Active**: ativo. Um webhook de uma organização cobre todos os seus repositórios; o monitor ignora os que não vigia.
6. Verifique: no GitHub, Recent deliveries tem de mostrar `200` no primeiro `ping`; no monitor a vista em direto mostra o recetor ativo, os contadores e a cobertura.

## Eventos em tempo real

- Com `webhook.record_events` ligado (predefinição), um evento `workflow_run` assinado atualiza logo a lista de runs desse repositório, sem ler antes o GitHub: o run mantém o tipo de evento que já tinha, por isso a sua cor não muda, e o repositório é lido de novo no ciclo seguinte para o confirmar (uma leitura por evento aceite). Um evento `workflow_job` traz também o tempo em fila e o de cada passo para as análises.
- Só se guardam campos curtos validados (workflow, run, estado, conclusão, ramo, commit curto, ligação ao run, durações); nunca a mensagem do commit nem o autor. Guardam-se também os nomes curtos do workflow, do ramo, do trabalho e dos passos, numa linha e limpos como qualquer texto que sai do monitor. Os `webhook.live_events_keep` eventos mais recentes leem-se em `GET /api/live-events` (no modo rede, com o token de acesso).
- Opcional, desligado por predefinição: com `live.sse.enabled` ligado, `GET /api/live-events/stream` envia esses mesmos eventos à medida que são aceites, como eventos do servidor (`hello`, depois um quadro `live` por evento, com um `id` sequencial para retomar com `Last-Event-ID` ou `?since=`, um comentário de keep-alive e um `bye` final). Só leitura; no modo de rede pede o token de acesso como qualquer outro pedido; no máximo `live.sse.max_clients` ouvintes, cada um durante `live.sse.max_seconds`. A edição Lite não o tem.
- Um run que termina a vermelho envia também a notificação `workflow_failed` se as notificações estiverem ativas. Com `webhook.record_events` desligado o webhook volta ao modo de só atualizar descrito acima.
- O GitHub não consegue chegar a `127.0.0.1`: use `gh webhook forward` (ver a documentação da CLI do GitHub) ou um túnel que monte de propósito, a apontar para `http://127.0.0.1:PORTA/api/webhook`.

## Cobertura no tempo

A vista em direto diz quanto do tempo os eventos cobrem o estado: **coberto por eventos** (o último evento é mais recente do que `savings.webhook_window_minutes`, 60 minutos por omissão), **sem eventos há ...** (mais antigo: um repositório calmo ou um túnel perdido) ou **à espera do primeiro evento**. A sondagem é sempre o recurso: um envio que nunca chegou (o monitor estava desligado, o túnel caiu) é apanhado pela leitura seguinte do repositório, pelo que os eventos reduzem as leituras mas nunca as substituem. Os mesmos números estão em `GET /api/live-status`, em `coverage` e `secret_source` (`env`, `config` ou `none`; nunca o segredo).

## Se não funcionar

| Resposta | Significado |
|---|---|
| `404` | O recetor está desligado, ou o segredo falta ou tem menos de 32 carateres na variável de ambiente. |
| `401` | A assinatura não coincide: o mesmo segredo dos dois lados e o tipo de conteúdo `application/json`. |
| `413` | O corpo tem mais de 256 KB. |
| `400` | Não há um id `X-GitHub-Delivery` válido, ou o conteúdo não é compreendido. |
| `202` | Aceite e ignorado: um repositório que não é vigiado, um evento fora da lista, um envio repetido ou um repositório acima do seu limite por minuto. |
| `429` | Um endereço enviou mais de 120 pedidos num minuto (modo de rede). |

## Repetições e inundações

Um pedido assinado válido que alguém capturou e volta a enviar é respondido mas não executado: cada entrega precisa do seu id `X-GitHub-Delivery`, os ids já aceites são memorizados durante `webhook.replay_seconds` (uma hora por omissão, memória limitada) e uma repetição recebe `202 {"duplicate": true}`. (Uma reentrega manual na página do GitHub reutiliza o id, por isso é ignorada nessa janela.) Um repositório pode causar no máximo `webhook.max_per_minute` eventos aceites por minuto; os restantes são respondidos e ignorados. Se a carga indicar `full_name`, o seu proprietário tem de ser a conta vigiada (ou um de `webhook.allowed_owners`). No modo de rede, um endereço pode enviar 120 pedidos por minuto. Depois de um evento aceite, as leituras condicionais guardadas desse repositório são descartadas e é lido de novo no ciclo seguinte, pelo que um evento em direto é sempre reconciliado com o GitHub.

## Lista de verificação da vista em direto

1. Coloque um segredo com pelo menos 32 carateres na variável de ambiente indicada por `webhook.secret_env` e ative o webhook.
2. Reencaminhe a porta (`gh webhook forward`) ou abra um túnel e use o seu endereço terminado em `/api/webhook` no GitHub.
3. Envie o evento de teste do GitHub (Recent deliveries > Redeliver) e procure-o em `?view=live`.
4. Vigie a quota no cabeçalho: com webhooks basta um ciclo mais lento.
