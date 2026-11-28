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
- O segredo partilhado é a única barreira: o GitHub não pode enviar um token de acesso, por isso o recetor não o pede e só confia na assinatura. Com o recetor ligado e sem segredo, recusa toda a entrega com `401`, e o doctor di-lo a vermelho. Mantenha o endereço atrás de um túnel ou proxy que controle.
- Todo o pedido tem de levar `X-Hub-Signature-256: sha256=<hmac>`, feito com esse segredo e comparado em tempo constante; qualquer outro recebe `401`, e nada do conteúdo é visto antes de a assinatura ser verificada.
- Um corpo com mais de `webhook.max_body_kb` (1 MiB por omissão, até 25 MiB) recebe `413`, antes de se ler ou calcular o que quer que seja; as recusas são contadas em `stats.too_big`.
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
- Com `webhook.record_events` ligado (predefinição), um evento `workflow_run` assinado atualiza logo a lista de runs desse repositório, sem ler o GitHub: o repositório é lido de novo, mesmo assim, no ciclo seguinte (o evento é a notícia, a leitura é a prova); uma entrega mostra a alteração logo, mas não poupa uma leitura. Um evento `workflow_job` traz também o tempo em fila e o de cada passo para as análises.
- Só se guardam campos curtos validados (workflow, run, estado, conclusão, ramo, commit curto, ligação ao run, durações); nunca a mensagem do commit. Os nomes do workflow, do ramo e do trabalho são texto de terceiros com até 100 carateres: guardam-se e mostram-se como texto simples, e os nomes dos passos vão para as estatísticas. Os `webhook.live_events_keep` eventos mais recentes leem-se em `GET /api/live-events` (quem puder abrir a página: o token de acesso no modo de rede, uma sessão no modo de equipa).
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
| `413` | O corpo tem mais de `webhook.max_body_kb` (1 MiB por omissão). |
| `503` | A fila de eventos está cheia: o GitHub ou tu enviam de novo mais tarde (`Retry-After`); a entrega não fica guardada como duplicada. |
| `400` | Não há um id `X-GitHub-Delivery` válido, ou o conteúdo não é compreendido. |
| `202` | Aceite e ignorado: um repositório que não é vigiado, um evento fora da lista, um envio repetido ou um repositório acima do seu limite por minuto. |
| `429` | Um endereço enviou mais de 120 pedidos com assinatura correta num minuto, ou mais de `webhook.max_bad_per_minute` (120 por omissão) cuja assinatura não se verifica. |

## Repetições e inundações

Um pedido assinado válido que alguém capturou e volta a enviar é respondido mas não executado: cada entrega precisa do seu id `X-GitHub-Delivery`, os ids já aceites, e o próprio corpo assinado, são memorizados durante `webhook.replay_seconds` (uma hora por omissão, memória limitada), pelo que um pedido capturado e reenviado com outro id é a mesma entrega, e uma repetição recebe `202 {"duplicate": true}`. (Uma reentrega manual na página do GitHub repete o mesmo corpo, por isso é ignorada nessa janela.) Um repositório pode causar no máximo `webhook.max_per_minute` eventos aceites por minuto; os restantes são respondidos e ignorados. Se a carga indicar `full_name`, o seu proprietário tem de ser a conta vigiada (ou um de `webhook.allowed_owners`). Um endereço pode enviar 120 pedidos com assinatura correta por minuto e `webhook.max_bad_per_minute` com assinatura que não se verifica; contam-se em separado, em todos os modos, pelo que o lixo nunca gasta a quota das entregas reais (com `listen.trusted_proxy` o endereço é o que o proxy viu). Depois de um evento aceite, as leituras condicionais guardadas desse repositório são descartadas e é lido de novo no ciclo seguinte, pelo que um evento em direto é sempre reconciliado com o GitHub. A memória das entregas guarda-se num ficheiro privado da pasta de dados (`webhook.persist_deliveries`, ligado por omissão; limitada, e um ficheiro danificado é uma memória vazia), pelo que um reinício não volta a dar validade a uma entrega capturada. Com `webhook.reject_stale` ligado (ligado por omissão), um evento de workflow assinado cuja própria hora é mais antiga do que `webhook.replay_seconds` é respondido e ignorado. A quota de pedidos com assinatura correta de um endereço é `webhook.max_verified_per_minute` (120). `webhook.secret_env` nunca aceita uma variável do sistema ou do seu acesso ao GitHub (PATH, GH_TOKEN...) nem um segredo que pertença a outra definição, e um nome só pode ser escrito numa definição.

O relógio usado é sempre o deste computador, nunca o da entrega. `webhook.clock_skew_s` (300 segundos por predefinição, de 0 a 3600) é o desvio que dois relógios podem ter: um evento que parece assim tão antigo em relação à janela não é dado por caducado por isso (`webhook.reject_stale`), e um evento marcado quando o relógio deste computador ia adiantado e depois foi atrasado conta na mesma como chegado, de modo que um repositório não aparece como morto por causa de um relógio; envelhece a partir do momento em que é notado. Uma marca adiantada mais de um dia não é acreditada. `webhook.reject_stale` está ligado por omissão: um evento de run ou de job cuja própria hora é mais antiga do que `webhook.replay_seconds` mais essa diferença recebe `202` e não é executado, e uma entrega é memorizada exatamente esse tempo mais a diferença (a memória é limitada pelo tempo, com uma rede de segurança de 20000 entradas); uma entrega capturada não pode, por isso, ser aceite outra vez depois de a memória a ter deixado sair. A ligação de um run (`html_url`) só é mantida se apontar para github.com ou para o anfitrião de `GH_HOST`. Limite conhecido: só os eventos `workflow_run` e `workflow_job` trazem uma hora que é verificada; uma entrega capturada de outro evento (`push`, `release`, `check_run`, `check_suite`) pode voltar a ser aceite depois de a memória a ter largado, o que custa mais uma leitura desse repositório.

## Ordem, fila e entregas perdidas

- **Ordem.** O GitHub não promete a ordem das entregas. Uma execução ou um job só avança (em fila, em curso, concluído): um evento que diz menos do que já se sabe sobre a mesma execução (conta também o que o último ciclo leu) não altera nada e é contado em `stats.out_of_order` de `GET /api/live-status`. Uma nova tentativa de uma execução recomeça.
- **Fila.** Um evento aceite espera numa fila de, no máximo, `webhook.queue_max` eventos (500 por omissão, de 1 a 10000) e um trabalhador aplica-o, por isso o GitHub recebe resposta depressa. Com a fila cheia, o recetor responde `503` com `Retry-After` e esquece a entrega, de modo que a que o GitHub reenvia é aceite: um evento nunca é descartado em silêncio. A profundidade é `queue` em `GET /api/live-status` e as recusas são `stats.queue_full`.
- **Entregas perdidas.** Uma execução que um evento deixou aberta (em fila ou em curso) e que não recebe evento final em `webhook.stale_after_h` horas (6 por omissão, de 1 a 168) fica marcada como `stale` na lista de execuções e o seu repositório é lido de novo no ciclo seguinte (`stats.stale`; `open_runs` conta as execuções mantidas abertas).
- **Pronto.** `GET /readyz` (só neste computador) responde `200` quando o monitor pode aceitar trabalho e `503` quando não pode, com a verificação que falha: `loaded` (há uma primeira leitura), `cycle` (o ciclo de atualização nem está preso nem parou), `store` (a pasta de dados aceita escrita) e `queue` (a fila tem espaço). `GET /api/health` só diz que o processo está vivo.

## Sem webhook: os eventos da conta (desativado por omissão)

Com `events_feed.enabled` ativo, o monitor lê os eventos da conta (`GET /orgs/OWNER/events`, ou `/users/OWNER/events`; `events_feed.owner_kind` diz qual, e `auto` tenta primeiro a organização) a cada `events_feed.interval_seconds` (60 por omissão; vale `X-Poll-Interval` se for maior) com um ETag. Uma leitura que não encontra nada de novo responde `304` e não gasta quota; quando algo mudou (um push, um pull request, uma etiqueta ou uma release) só se volta a ler, no ciclo seguinte, o repositório indicado no evento, no máximo `events_feed.max_per_tick` por turno. A primeira leitura só aprende onde está a lista. Não precisa de webhook nem de túnel e pode funcionar ao lado de um. Os contadores são `feed` em `GET /api/live-status`.

## Sem endereço público: o WebSocket do GitHub (desativado por omissão)

O GitHub não consegue chegar a um monitor em casa, atrás de um router. Com `webhook.transport` em `websocket`, a CLI do GitHub faz o contrário: `gh webhook forward` cria um webhook temporário, mantém uma ligação aberta a partir deste computador e entrega cada envio ao recetor do monitor, por isso nada fica exposto e não é preciso túnel.

- `webhook.ws_targets` lista o que reencaminhar: `dono/repo` para um repositório ou `dono` para uma organização inteira (uma conta pessoal precisa de uma entrada por repositório, no máximo `webhook.ws_max_targets`). Vazio por omissão: mudar só o transporte não arranca nada. O recetor tem de estar ativo (`webhook.enabled` e o segredo partilhado) e o monitor reiniciado.
- **Escreve no GitHub** (os hooks temporários) e precisa de um token que possa gerir webhooks (`admin:repo_hook`, `admin:org_hook`). Com um token que não pode, o estado do destino diz `forbidden` e só se tenta de novo a cada poucos minutos.
- Os envios são assinados com um segredo criado em cada arranque, guardado em memória e passado ao `gh` na sua linha de comandos, por isso outro processo do mesmo utilizador neste computador poderia lê-lo; só permite a esse utilizador enviar eventos a um recetor que está neste computador. O segredo partilhado nunca sai do ambiente. O GitHub não assina cada trama do WebSocket em separado: a ligação é autenticada pelo token.
- Um reencaminhador que termina é arrancado de novo com uma espera cada vez maior (de 5 segundos a 5 minutos). Um hook aceita um só subscritor: não executes `gh webhook forward` à mão para o mesmo destino. Os envios deste transporte não aparecem como reenviáveis na página do hook no GitHub, por isso a recuperação abaixo só funciona com o transporte `http`.
- `webhook.ws_cleanup` (desativado) apaga no arranque os hooks que apontam para o reencaminhador do GitHub nos destinos indicados, o que limpa o que uma falha deixou; apaga hooks, por isso ativa-o só se souberes que nenhuma outra sessão os usa.
- O estado de cada reencaminhador é `forwarders` em `GET /api/live-status`.

## Entregas que nunca chegaram (desativado por omissão)

Um monitor em casa nem sempre está ligado: o computador desliga-se de noite, o túnel cai. O GitHub guarda os envios recentes de um webhook, diz quais falharam e permite reenviar um que falhou. Com `webhook.redeliver.enabled` ativo, o monitor verifica os webhooks que indicares em `webhook.redeliver.hooks` (`repo:DONO/REPO#ID` ou `org:DONO#ID`, onde ID é o número no fim do endereço do webhook no GitHub) um minuto depois do arranque e depois a cada `webhook.redeliver.interval_minutes` (60 por omissão), e pede ao GitHub que reenvie os envios a que nenhuma tentativa respondeu com um 2xx.

- **Escreve no GitHub** (o pedido de reenvio) e precisa de um token que possa gerir o webhook. Desativado por omissão; as entregas de uma GitHub App não estão cobertas.
- No máximo `webhook.redeliver.max_per_run` (20) envios por verificação, nenhum mais antigo que `webhook.redeliver.max_age_hours` (24; o GitHub guarda-os três dias), primeiro os nunca pedidos. Um envio é pedido de novo com uma espera crescente (5, 10, 20, 40, 80, 160 e 300 segundos) e abandonado (`dead`) à oitava vez. O que foi pedido fica num ficheiro privado da pasta de dados (o id do envio e a contagem, nunca uma carga), por isso um reinício não volta a pedir logo.
- Um envio que chega de novo é respondido pelo recetor como duplicado, por isso pedir duas vezes não faz mal.
- `POST /api/webhook/redeliver` (administradores, só neste computador, com o token de uso único) verifica já, seja qual for o horário, e deixa uma linha no registo de ações. Os contadores são `redelivery` em `GET /api/live-status`.

## Lista de verificação da vista em direto

1. Coloque um segredo com pelo menos 32 carateres na variável de ambiente indicada por `webhook.secret_env` e ative o webhook.
2. Reencaminhe a porta (`gh webhook forward`) ou abra um túnel e use o seu endereço terminado em `/api/webhook` no GitHub.
3. Execute um workflow (ou faça push para um repositório vigiado) e procure o evento em `?view=live`. O `ping` do GitHub só prova a assinatura: recebe `200` e não aparece na lista, e um reenvio a partir do GitHub é ignorado como repetição.
4. Vigie a quota no cabeçalho: com webhooks basta um ciclo mais lento.
