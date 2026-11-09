<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Registo de alterações

Versão da própria ferramenta (monitor + sentinela + ferramentas em lote), com o seu próprio semver. A fonte é o CHANGELOG.md em inglês; este ficheiro tem as mesmas versões e secções.

## [1.7.1]

Uma página nova e a mesma sentinela atrás de um contrato. A página tem um painel lateral à esquerda com o logótipo, as secções em grupos e dezasseis temas; a sentinela de CI é agora uma das sentinelas de um registo, e é isso que permite que cheguem as seguintes. O que o monitor mostra e decide não muda.

### Adicionado

- **Um painel lateral** (todas as edições): o logótipo da ferramenta (um SVG que se desenha com as cores do tema e fica parado quando o sistema pede menos movimento), o seletor de contas, as secções em três grupos que se recolhem (Vigiar, Dados, Sistema) e a ajuda. O painel contrai-se para os seus ícones e as duas escolhas ficam guardadas no navegador. A barra superior mostra o nome da secção e as ferramentas. As setas, também para cima e para baixo, passam de uma secção para outra. Num ecrã pequeno o painel passa para cima. `?chrome=0` esconde-o, como escondia a barra de separadores.
- **Dezasseis temas** além de auto, claro e escuro: os do Studio do sistema de alarme (Armor, Aqua, Midnight, Ember, Forest, Violet, Solar, Ice, Crimson, Mono, High contrast, Metallic, Professional, Videogame, Terminal e Blueprint), escolhidos numa lista em Definições > Este navegador ou com `?theme=`. Cada um define a página, o painel lateral, os painéis, as linhas, o texto, o acento, os cantos e as letras. O verde, o vermelho, o âmbar e o azul mantêm o seu significado em todos, aclarados ou escurecidos onde um tema o precisa para que cada número se leia a 4,5:1 ou mais, e o texto de um distintivo segue a sua cor.
- **`BaseSentinel`, `Alert` e `SentinelRegistry`** (`sentinel_base.py`, `sentinel_registry.py`; só a edição completa): o contrato de uma sentinela (`start`, `stop`, `tick`, `get_status`, `get_alerts`, `get_metrics`, `get_config_schema`, `refresh_seconds`), um alerta com um código estável que nunca depende da língua (`ci.red`, `ci.stuck`, `ci.pending_sign`) e a conta a que pertence, e um registo que dá a cada sentinela um relógio próprio. `sentinels.<nome>.enabled` em `actions_monitor.json` liga ou desliga uma; sem ele decide `sentinel.enabled`, como sempre, e onde os dois dizem algo ganha o bloco novo.
- **`SentinelCI`** (`sentinel_ci.py`): a sentinela de sempre atrás desse contrato. Contém o `Sentinel` antigo e não muda a forma como decide: a mesma regra de vermelho (a última execução terminada de cada workflow no ramo por omissão), os mesmos ficheiros, o mesmo ciclo, a mesma instantânea.
- Testes para cada alteração desta versão: o contrato, o registo e os seus interruptores, a sentinela de CI e os seus alertas em duas línguas, que a edição lite não carrega nada disto, o painel lateral e os dezasseis temas (que cada um define todas as variáveis e que o texto, o texto cinzento pequeno, o acento e as quatro cores de estado se leem a 4,5:1 na sua página e nos seus painéis).

### Alterado

- O tema escolhe-se numa lista em Definições > Este navegador (antes era um botão que percorria auto, claro e escuro); um tema guardado por uma versão anterior continua a ser entendido.
- A cor de um distintivo, de uma barra e de um aviso que era branca sobre vermelho, âmbar ou verde é agora a que se lê sobre essa cor no tema em uso.
- A sentinela arranca pelo registo; `SENTINEL["obj"]` continua a ser a sentinela de CI, por isso tudo o que lhe perguntava algo continua a funcionar. Os eventos, os ficheiros e os endpoints são os mesmos.

### Corrigido

- Um teste da 1.7.0 lia a saída de `tasklist` com a página de códigos errada e podia falhar num Windows com outra língua.
- **Uma recusa podia perder-se pelo caminho** (todas as edições): um POST que o monitor recusava antes de ler o seu corpo (token em falta, corpo demasiado grande) fechava a ligação com dados por ler, e o Windows, por vezes o Linux, respondia com um reinício: o cliente via uma ligação interrompida em vez do 403 que lhe era devido. Agora o monitor lê e descarta o que resta do corpo (até 1 MB, no máximo 2 segundos) depois de responder, por isso a resposta chega sempre. A recusa, o seu código e o seu texto são os mesmos. Um teste envia os cabeçalhos, espera e envia o corpo, e falha sem isto.

## [1.7.0]

Várias contas na edição completa, cada uma um monitor próprio, e uma página que as conhece. A edição lite não muda: uma conta, e nem sequer mostra as opções novas.

### Adicionado

- **Várias contas** (só a edição completa). Uma pasta `accounts/<id>/` por conta (uma pessoa ou uma organização) com o seu próprio `actions_monitor.json`, a sua própria cache, eventos, análise, estado da sentinela e registos; `accounts/global.json` é opcional (`default_account`, `enabled_accounts`) e `MONITOR_ACCOUNTS_DIR` muda a pasta de sítio. O id são letras minúsculas, dígitos, `_` e `-` (até 40), pelo que é sempre um nome de pasta seguro. Sem uma pasta `accounts/` nada muda: uma conta, com os seus ficheiros junto do código.
- **Um supervisor** (`accounts_supervisor.py`): com uma pasta `accounts/`, `python actions_monitor.py` arranca um processo pequeno na porta de sempre que executa um monitor por conta (`account_child.py`), cada um na sua própria porta de `127.0.0.1`. Uma falha, uma resposta lenta ou um limite de taxa de uma conta nunca toca noutra; uma conta em baixo é arrancada de novo com uma espera crescente (2, 5, 15, 30, 60 e depois 120 segundos) e o resumo diz que está em baixo entretanto. Não lê nada do GitHub e não escreve nada; ao pará-lo termina todos os processos que arrancou, também no Windows.
- **A API das contas**: `GET /api/accounts` (o resumo), `GET /api/accounts/<id>/status`, e qualquer outro pedido `/api/` vai para a conta indicada com `?account=<id>` ou o cabeçalho `X-Account-Id` (a conta predefinida sem nenhuma; uma conta desconhecida dá 404). As regras de acesso são as de um monitor isolado, e o token de uso único de uma alteração é pedido à mesma conta a que a alteração vai.
- **Um webhook para todas**: `POST /api/webhook` é um único endereço para a instalação; o supervisor lê apenas o proprietário em `repository.full_name` e passa o evento intacto à conta cujo `github_owner` é esse proprietário, que verifica a assinatura com o seu próprio segredo. Um proprietário que ninguém vigia recebe resposta e é ignorado.
- **`--accounts`, `--account <id>` e `--migrate-accounts [--apply]`**: listam as contas, executam só uma como um monitor normal e movem o esquema antigo para `accounts/default/`. A migração é um ensaio, salvo com `--apply`, nunca move nem apaga os originais, recusa uma segunda execução e não toca nos ficheiros da edição lite.
- **A página com várias contas**: um seletor de contas por baixo do cabeçalho e uma entrada **Todas as contas** com um cartão por conta (estado, repositórios, em curso, em falha). Cada janela guarda a sua própria conta e vista, lidas do endereço.
- **Vistas por endereço** (`?view=now|alerts|charts|repos|settings|live` e `?chrome=0`, um ecrã sem botões de cabeçalho, separadores nem filtros para uma parede ou um segundo monitor). A vista **Ao vivo** mostra os últimos eventos que o GitHub enviou, o estado do recetor de webhook (nunca o segredo) e um seletor do modo de trabalho. `GET /api/live-status` é a sua fonte.
- `tools/demo_accounts.py` para as imagens, o guia `ACCOUNTS.md` em oito idiomas e testes para cada alteração (a bateria passou de 866 para 914).

### Alterado

- Os ficheiros de estado de um monitor que é uma conta entre várias vivem na sua pasta através de `state_dir()`; um monitor isolado mantém-nos junto do código, como sempre.
- As imagens do README foram refeitas e o README em oito idiomas mostra as contas.

### Segurança

- O supervisor e as contas escutam só em `127.0.0.1`, salvo se o modo rede estiver ligado. O webhook não tem verificação de anfitrião nem token de acesso (um túnel muda o anfitrião) e a sua prova continua a ser o HMAC do GitHub; um cookie da sessão nunca é passado a uma conta.

### Corrigido

- A vista Ao vivo da 1.6.8 não tinha estado do recetor: com o webhook desligado ou com um segredo de menos de 32 carateres não dizia nada, e agora diz qual dos dois.

## [1.6.8]

O proxy HTTPS da 1.6.7 é agora verificado contra um proxy real, as imagens foram refeitas e o histórico de alterações está traduzido até à 1.6.3.

### Adicionado

- `python tools/manual_check_live.py proxy ANFITRIÃO [PORTA] [LIGAR]`: verifica, através do seu proxy HTTPS real na porta 443, que a página entra (a sessão abre-se com o token de acesso no corpo e o cookie volta `Secure` e `HttpOnly`) e que três pedidos continuam recusados (o outro esquema, outro nome de anfitrião, o nome com porta). Lê o token de acesso de `MONITOR_ACCESS_TOKEN`, nunca o imprime e, sem argumentos, diz o que pôr no nginx ou no Caddy.
- `tools/demo_monitor.py --network` mostra a página como se vê no modo rede (a barra vermelha persistente e, nas Definições, o aviso de todas as interfaces e o novo nome do proxy) para poder fotografá-la; a demo continua a escutar só em `127.0.0.1`. `tools/make_screenshots.py` tira com ele duas imagens novas: `web_network_now` e `web_network_settings`.
- Testes que percorrem toda a cadeia: um cliente sobre TLS real, um proxy inverso que termina o TLS e reencaminha `Host` e `Origin` sem porta, e o monitor real por trás. Verificam que uma alteração feita a partir da página chega às definições, que o mesmo pedido é recusado sem `listen.proxy_public_host`, que um esquema, um nome ou uma porta errados continuam recusados, que a sessão se abre e o cookie é `Secure`, e que a verificação à mão concorda com o proxy e nunca imprime o token (a bateria passou de 858 para 866).

### Alterado

- O histórico de alterações (Ajuda > Registo de alterações) está traduzido nos outros sete idiomas da 1.6.8 à 1.6.3 (a 1.6.7 e a 1.6.5 já estavam); as entradas anteriores à 1.6.3 mantêm o texto em inglês sob um aviso traduzido.
- As imagens do README foram refeitas, 76 no total, e o README em oito idiomas mostra o subseparador Avançado das Definições e as duas imagens do modo rede.
- `docs/MIGRATING.md` tem um bloco da 1.6.7 para a 1.6.8, e o roteiro em oito idiomas regista o que resta: as entradas antigas do histórico e as verificações que precisam dos seus próprios serviços.

### Corrigido

- O histórico da 1.6.7 dizia que só estavam traduzidas a 1.6.7 e a 1.6.5 e que o proxy só tinha sido verificado com a guarda; esta versão traduz o resto até à 1.6.3 e verifica o proxy de ponta a ponta, como acima.

## [1.6.7]

Um proxy HTTPS na porta 443 predefinida já funciona com o modo rede, e mais uma parte do histórico de alterações está traduzida.

### Adicionado

- `listen.proxy_public_host` (Definições > Avançado > Rede, vazio por predefinição): o nome de anfitrião público de um proxy HTTPS na porta 443 predefinida que reencaminha `Host` e `Origin` sem porta. Até agora a guarda comparava ambos com a porta do monitor, pelo que esse proxy era recusado; esse único nome é agora aceite tal como está. Só conta enquanto o modo rede está ligado e a sessão é HTTPS (TLS direto ou `listen.secure_cookie`), tem de ser um nome de anfitrião simples (uma porta, um caminho, um utilizador, um espaço ou um literal IPv6 deixam-no vazio), como toda a definição que o esquema marca como `secure` só se altera a partir do próprio computador, e a sua etiqueta e a sua ajuda existem em oito idiomas.
- Testes para cada alteração desta versão (a bateria passou de 843 para 858 e o ficheiro novo verifica a guarda, o valor, o esquema e os textos).

### Segurança

- A exceção da guarda é a mais estreita possível: só esse nome é aceite sem porta, nunca outro anfitrião sem porta, nunca com HTTP simples, e o `Origin` tem de levar o mesmo nome com o esquema `https` (outro esquema, uma porta, um caminho, um utilizador ou um anfitrião diferente continuam recusados). O nome do proxy nunca aparece no estado público da guarda.

### Alterado

- O histórico de alterações (Ajuda > Registo de alterações) está traduzido nos outros sete idiomas para a 1.6.7 e a 1.6.5 (a 1.6.6 já estava); as entradas mais antigas mantêm o texto em inglês sob um aviso traduzido e seguir-se-ão, da mais recente para a mais antiga.
- `docs/ADVANCED.md` (oito idiomas) explica o proxy na porta predefinida em vez de dizer que não é suportado, `docs/MIGRATING.md` tem um bloco da 1.6.6 para a 1.6.7, e o guia das definições e o índice da Ajuda foram regenerados.

## [1.6.6]

Correções do modo rede e do `act`, os pendentes da 1.6.5 e o histórico de alterações em oito idiomas.

### Adicionado

- Uma barra vermelha persistente no topo das Definições quando o modo rede escuta em todas as interfaces (`listen.host` = `0.0.0.0`), em oito idiomas. Até agora só o `--doctor` o dizia.
- `POST /api/access` com `{"token": "..."}`: abre a sessão do modo rede com o token de acesso no corpo, de modo que nunca fica numa barra de endereços, num histórico ou num registo. As mesmas verificações de qualquer pedido (anfitrião, origem, bloqueio após tokens errados, comparação em tempo constante); o cookie volta `HttpOnly`, `SameSite=Strict` e, em HTTPS, `Secure`. O endereço com `?access=` da 1.6.5 continua a funcionar.
- Um contador das falhas que o monitor engole de propósito (`degraded.py`): uma linha estruturada na consola por cada uma, uma contagem por origem em `degraded.json` junto do monitor, a nova verificação `degraded` do `--doctor` e uma linha «Falhas engolidas» no painel Acerca de. O comportamento não muda: continuam a nunca parar o monitor.
- O histórico de alterações (Ajuda > Registo de alterações) tem agora um ficheiro de tradução por idioma, `docs/CHANGELOG_<idioma>.md`, com as mesmas versões e secções da fonte em inglês; `tools/make_help_index.py --check` e um teste falham se faltar uma versão numa tradução. As entradas ainda por traduzir dizem-no, no idioma do leitor.
- Testes para cada alteração desta versão (a suite passou de 811 para 843).

### Corrigido

- **O modo rede com HTTPS era inutilizável a partir da página.** A guarda de mesma origem só aceitava uma origem `http://`, por isso com TLS direto ou um proxy HTTPS (`listen.secure_cookie`) o `Origin: https://...` do próprio navegador era recusado e toda a alteração (definições, confirmações) respondia 403. Agora a guarda constrói a origem permitida com o esquema da sessão (https ou http, nunca ambos), compara exatamente anfitrião e porta e recusa uma origem mal formada. Testado com um servidor TLS real e um certificado criado pelo teste.
- `act`: o Stop liberta agora a execução, de modo que o arranque seguinte já não responde `busy` para sempre quando o processo não termina; um worker que regressa tarde nunca toca numa execução mais recente; o canal de saída e o temporizador fecham-se em todos os casos (fim normal, limite de tempo, Stop, erro inesperado) e a suite já não emite `ResourceWarning`.
- `tools/make_screenshots.py` podia terminar sem dizer nada: o navegador corre sem canais capturados e com limite de tempo, avisa-se se falta o navegador ou se a demonstração não arranca, `MONITOR_BROWSER` indica um navegador à mão e o código de saída é 1 se alguma imagem não foi feita.

### Segurança

- No modo rede, toda a definição que o esquema marca como `secure` só pode ser alterada a partir do próprio computador, e não apenas as quatro famílias de antes (`listen.`, `github_token.`, `act.`, `github_actions.`): também o webhook, as ações da IA, as notificações, o OpenTelemetry, o espelho, os runners, as saídas e o resto. A lista é lida do esquema, por isso uma definição segura nova fica coberta sem que ninguém se lembre dela; um teste percorre-as todas.

### Alterado

- As imagens de Acerca de, Ajuda, Agora, Básico e Avançado no README e nos guias foram tiradas de novo.
- `docs/ADVANCED.md` (oito idiomas): HTTPS com o seu certificado ou atrás de um proxy, a regra da origem, a sessão aberta por POST e a barra de aviso.

## [1.6.5]

Uma versão de integridade e segurança: nenhuma funcionalidade nova grande. O que não se pode provar deixa de ser dado como seguro.

### Adicionado

- Definições novas, todas com um valor predefinido conservador: `dispatch.required_ci` (e, no ficheiro, `dispatch.required_ci_repos` e `dispatch.required_ci_profiles`), `act.allow_symlinks`, `listen.tls_cert_file`, `listen.tls_key_file`, `listen.secure_cookie`, `listen.max_failed_attempts`, `webhook.replay_seconds`, `webhook.max_per_minute`; o guia das definições é regenerado.
- `finalize --accept-legacy` para os lotes escritos por uma versão anterior, e as verificações `risks` e `backend` do `--doctor` (oito idiomas).
- Testes para cada alteração desta versão (a bateria passou de 729 para mais de 800).

### Segurança

- **Um commit verde precisa da CI obrigatória.** O `gha_dispatch_all.py` só dá um commit por verde quando os ficheiros de workflow obrigatórios tiveram êxito sobre ele (`ci.yml` por predefinição; `dispatch.required_ci`, `dispatch.required_ci_repos`, `dispatch.required_ci_profiles`), nada falhou, expirou nem aguarda uma aprovação (`action_required` bloqueia como uma falha), nada continua em curso e a lista de execuções está completa (lê até cinco páginas; uma lista mais longa não é verde).
- **Um `git fetch` falhado interrompe o despacho** desse repositório, os comandos git têm um limite de tempo e os ids de commit são validados; um `origin/main` antigo nunca é tomado como prova.
- **O catálogo não pode sair da sua pasta nem alterar o despacho.** `tool` tem de ser um nome de ficheiro simples que esteja na pasta das ferramentas (as ligações que saem dela também são recusadas); `extra` só pode conter entradas de workflow `-f chave=valor` (nunca `dry_run`, `ref`, `-R`, `--ref`); `finalize_flags` apenas opções longas; os argumentos de `gh workflow run` são construídos a partir das peças validadas e verificados de novo quando o lote dispara.
- **Os lotes antigos não são assinados às cegas.** O `finalize` só oferece para assinatura uma execução cujo lote registou que foi construído sobre o commit verificado. Um lote escrito por uma versão anterior fica `needs_review`; o `finalize --accept-legacy` volta a ler a execução do GitHub, só a aceita se o seu commit for o registado, avisa e pede a palavra LEGACY antes de cada assinatura.
- **O `act` fica dentro do espaço de trabalho.** O clone é resolvido e tem de ser uma pasta real do espaço de trabalho (uma ligação, um nome com `..` ou um `.github` que aponte para outro lado é recusado; `act.allow_symlinks` permite uma ligação para um clone). O limite de tempo e o Stop terminam toda a árvore de processos que a execução iniciou (um grupo de processos em Linux e macOS, `taskkill /T` sobre o seu próprio PID em Windows) e removem os contentores `act-` que essa execução criou.
- **Modo rede**: HTTPS servido diretamente com o seu próprio certificado e chave (`listen.tls_cert_file`, `listen.tls_key_file`; TLS 1.2 ou superior; o monitor não arranca em HTTP simples se não puderem ser usados) ou o cookie `Secure` atrás de um proxy HTTPS (`listen.secure_cookie`); o token de acesso sai logo da barra de endereços (redirecionamento, sem `Referer`); um endereço que envie demasiados tokens errados é recusado durante cinco minutos (`listen.max_failed_attempts`); o endereço da página é aquele em que o servidor escuta; só se aceitam endereços IPv4, tanto nas definições como na guarda; a consola avisa quando a ligação é HTTP simples.
- **Webhook**: cada entrega precisa do seu id `X-GitHub-Delivery` e uma repetida é ignorada durante `webhook.replay_seconds`; um repositório pode causar no máximo `webhook.max_per_minute` eventos aceites por minuto; o proprietário em `full_name` tem de ser a conta vigiada; um endereço é limitado a 120 pedidos por minuto no modo rede; um evento aceite descarta as leituras condicionais guardadas desse repositório e marca-o para o ciclo seguinte; um cabeçalho de assinatura com carateres invulgares é uma simples recusa.
- **Servidor MCP**: uma mensagem com forma errada (parâmetros, argumentos, id, método) recebe um erro só para essa mensagem, um defeito inesperado numa ferramenta é um erro interno que não termina o servidor, e uma linha com mais de 64 KB é recusada.
- **O token do GitHub guardado é entregue só ao `gh`.** Já não é posto no ambiente do monitor, pelo que o `act`, o seu comando de notificação e qualquer outro processo filho não o podem herdar.
- **Um GET nunca escreve.** A cópia do relatório diário na pasta de auditoria é um POST com o token de uso único (`/api/sentinel/parte/save`); o `?save=1` no GET desapareceu.
- O `--doctor` nomeia as combinações perigosas (modo rede em todas as interfaces, ações da IA que executam com o modo rede ligado, `act` com o modo rede ligado, o token num ficheiro simples) e mostra onde o token é guardado, nunca o token.

### Corrigido

- O `max_per_hour` das notificações passa a limitar mensagens (uma unidade por canal, reservada de uma vez sob um único bloqueio) e não eventos; um canal que não consegue enviar não reserva nada.
- Duas gravações simultâneas das definições já não perdem uma delas (um bloqueio no processo e um ficheiro de bloqueio).
- A exportação da fila de assinatura diz porque não escreveu (uma unidade ou caminho de rede recusado, uma pasta em vez de um ficheiro, o erro do sistema) em vez de uma simples recusa.
- A espera do limite secundário e a nova tentativa após um tempo esgotado levam uma variação aleatória.
- O teste que descomprime o zip numa pasta limpa deixou de fazer parte da bateria ordinária: o `make_release.py` executa a bateria uma vez com um limite de tempo, depois a instalação limpa como etapa própria, e mostra stdout e stderr quando alguma falha.

### Alterado

- Os guias de notificações, webhook, funcionalidades avançadas, saídas, alertas de IA e migração dizem tudo isto em oito idiomas; `docs/MIGRATING.md` tem um bloco da 1.6.4 para a 1.6.5.

## [1.6.4]

### Adicionado

- **Alertas para IA**: o monitor escreve um feed local só de leitura (`ai_alerts.jsonl`, uma linha por evento, e `ALERTS_BRIEF.md`, reescrito a cada ciclo, 2 KB por predefinição) com um alerta por workflow vermelho: id estável, gravidade, causa provável distinguida como real ou transitória com regras editáveis, ação sugerida e um estado (aberto, reconhecido, resolvido sozinho quando o workflow volta a verde). Tudo passa por um limpador de tokens, chaves, endereços de e-mail, endereços IP e pastas pessoais. `GET /api/ai/brief` e `GET /api/ai/alerts`, um servidor MCP opcional só de leitura (`mcp_server.py`: `get_alerts`, `get_red_repos`, `get_run_failure`, `get_quota` e `ack_alert` com `--allow-ack`), uma notificação quando aparece um alerta REAL novo, um gancho opcional para um endereço deste computador (desligado) e um `ai_hint` opcional em `ci_red.json`. Novo guia `AI_ALERTS.md` em oito idiomas.
- **Funcionalidades opcionais, todas desligadas por predefinição, cada uma com o seu interruptor em Definições > Avançado** e testes que provam que recusam sem o interruptor, a confirmação ou o token: o modo rede (um endereço privado, um token de acesso para cada pedido, nomes de anfitrião aceites, uma barra vermelha persistente, chaves de exposição que só se alteram a partir do próprio computador); um token do GitHub guardado pelo monitor no cofre seguro do sistema (DPAPI do Windows, Keychain do macOS, Secret Service do Linux, ou então um ficheiro com permissões 600) e nunca numa definição, num registo nem numa resposta, com um botão de eliminação; ações no GitHub (executar de novo, cancelar, fechar, fundir), cada uma confirmada à parte depois de mostrar exatamente o que será enviado; executar aqui um workflow com `act` a partir de uma lista fechada, sem segredos reais; uma cópia local de artefactos; runners próprios (inativos, ocupados, offline, disco e carga opcionais); exportação OpenTelemetry (traços e métricas, OTLP/HTTP JSON); as organizações do login; FinOps por etiquetas de job (Linux, Windows, macOS e runners maiores), o preço dos minutos acima dos incluídos, Codespaces, Packages e armazenamento do relatório de faturação. Novo guia `ADVANCED.md` em oito idiomas e `tools/manual_check_live.py` para experimentar à mão os serviços reais.
- `--doctor --json`; o doctor também comunica portas ocupadas, a margem que resta, se tem o seu próprio ficheiro de alvos, o token de uso único e a exposição. O README do pacote começa pela escolha do lançador (completo, lite, em lote, terminal, doctor, demo).
- A aplicação de terminal edita as definições simples (não as de segurança) e tem um separador de IA; um aviso persistente para as definições que precisam de reinício sobrevive a um recarregamento; o cabeçalho mostra quando o A10 da sentinela está em pausa por quota e quanto do orçamento de minutos foi usado; o servidor também se lembra da boas-vindas.
- O `redrule.py` ignora as execuções dinâmicas das atualizações de dependências como o painel faz, e os casos partilhados da regra são agora um fixture de testes.

### Alterado

- **A Ajuda está completa em oito idiomas**: os documentos do roteiro, de contribuição, de segurança e de suporte estão traduzidos, as etiquetas fixas do histórico de alterações estão traduzidas e as suas entradas são marcadas como só em inglês, com um aviso traduzido; o `tools/make_help_index.py --check` e um teste falham quando a um tópico falta um idioma. Uma pesquisa mostra no máximo 30 resultados e um documento enorme já não prende o fio do servidor.
- O mosaico vermelho conta workflows nas duas edições e diz em quantos repositórios. A edição lite herda o ritmo de atualização da completa no seu primeiro arranque.
- Uma falha passageira (um soluço de TLS, um 5xx) é repetida com uma espera exponencial e só é mostrada como erro depois de três ciclos seguidos; a última imagem mantém-se.
- A vista de terminal da edição lite já não pede a sentinela; a edição lite nunca carrega o módulo da sentinela (a guarda local passou para `localguard.py`).
- O `--demo` redireciona para a sua pasta temporária todo o ficheiro que poderia escrever (registos, caches, feed de eventos, histórico, boas-vindas).

### Segurança

- Com `updates.check` desligado ou `airgapped` ligado, o monitor não faz nenhum pedido de rede para o aviso de atualização (testado).
- Verificado contra a API real do GitHub: os scopes do token são lidos corretamente, a lista de organizações e o relatório de faturação degradam em silêncio (um login sem o scope `user` recebe «não encontrado» e o monitor mantém a estimativa).

## [1.6.3]

### Adicionado

- **Painel Acerca de** (o botão **i** do cabeçalho, nas duas edições): versão, edição, autor, licença, Python e sistema, ligações (repositório, releases, histórico de alterações, documentação, issues), os ficheiros que usa (só leitura), a saúde do servidor, os créditos das bibliotecas e um botão que copia a informação para o suporte (sem segredos nem tokens, com a pasta pessoal mostrada como `~`). `GET /api/about`, e `--about` na consola.
- **Painel de Ajuda** (o botão **?**, a tecla `?`, e um «?» na barra de separadores que abre a página do separador em que está): toda a documentação (README, início rápido, cada guia, roteiro, histórico de alterações, contribuição, segurança) como um índice onde se pode pesquisar, no idioma da página e em inglês onde um documento não está traduzido, servido pelo servidor local sem Internet. É construído a partir dos documentos reais pelo `tools/make_help_index.py` (`--check` na CI), pelo que nenhum texto é escrito duas vezes; o markdown é apresentado de forma segura (tudo escapado, nenhuma imagem carregada, só ligações `http(s)` e ligações a outros documentos). Na consola: `--help-topics [TÓPICO]` e `--help-search PALAVRAS`.
- **Aviso de uma versão mais recente**: um emblema discreto no cabeçalho, uma linha em Acerca de, na consola e no `--doctor` quando é publicada uma release mais recente. Um único pedido de leitura por dia à página pública de releases, com o mesmo cliente que tudo o resto (leitura condicional), nunca descarrega nem instala nada, não envia nada sobre si, ignora as pré-versões, compara as versões como números (1.6.10 é mais recente do que 1.6.9), cala-se offline e desliga-se com `updates.check` ou numa instalação isolada (`airgapped`).
- **Definições > Básico**, o primeiro separador: abrir o navegador ao arrancar, o aviso de atualização, o interruptor de instalação isolada, o token de uso único, as opções de descoberta, as regras de ciclo de vida, e o plano e as quotas. Por baixo, o que o monitor encontrou na conta (proprietário, repositórios encontrados, vigiados, deixados de fora), as novidades e os grupos sugeridos.
- **`--doctor`**: Python, `gh`, o login, a margem disponível, a rede, a permissão de escrita da pasta, uma porta livre, e os opcionais Docker, Rich e Textual; cada falha vem com o comando exato que a corrige, em oito idiomas.
- **`--demo`**: a página com dados inventados, sem `gh`, sem login e sem rede; nada seu é lido nem escrito.
- **Uma boas-vindas de três passos** na primeira vez que a página é aberta (o que faz, o que encontrou na sua conta, para onde ir a seguir).
- **Descoberta automática**: eventos para um repositório novo, desaparecido, arquivado ou desarquivado (consola, Definições > Básico e, na edição completa, as notificações); um grupo sugerido quando três ou mais repositórios por classificar partilham um prefixo, acrescentado só depois da sua confirmação e com uma cópia do ficheiro; regras de ciclo de vida para deixar de fora forks e repositórios vazios e privados; uma frequência de atualização automática opcional que segue a atividade real dentro do orçamento de chamadas.
- **Um token de uso único** (`session_guard`, ligado por predefinição) que a página pede mesmo antes de guardar uma definição ou confirmar uma ação, e uma **barra de reinício** em cada separador enquanto uma definição guardada aguarda um reinício.
- **Níveis do linter de workflows** (informação, aviso, erro) como filtros na página, e `Scripts` na aplicação de terminal.
- **Quotas e planos para qualquer tipo de conta**: o seu plano em Definições > Básico; os números (minutos incluídos como dinheiro, tarifas por sistema, concorrência, limites de um job e de uma execução, margens da API) vivem em `quotas.json`, que pode editar sem uma versão nova; minutos faturáveis à parte dos minutos de relógio (os repositórios públicos não custam nada, os privados usam o multiplicador do Windows ou do macOS), uma projeção mensal marcada como estimativa, um aviso uma vez por mês aos 75 % e aos 90 % dos minutos incluídos através das notificações, jobs em execução e em fila face ao limite do plano, jobs perto do limite de 6 horas e o tipo de token lido dos próprios cabeçalhos do GitHub (com o conselho de iniciar sessão quando só restam 60 chamadas por hora). O uso real vem só do relatório de faturação opcional e só de leitura (`quota.billing_api`, desligado por predefinição, silencioso perante um 403 ou 404). `GET /api/quota`.
- **Modos de trabalho: normal, rápido e turbo** (`modes.py`, guia `MODES`): um seletor com um ícone de medidor no cabeçalho e `--mode` / `--mode-minutes` na consola, nas duas edições. As predefinições vivem no bloco `modes` da configuração; antes de começar, a página mostra as chamadas por hora no pior caso, o que as leituras condicionais costumam poupar e quanto duraria a margem restante; volta ao normal sozinho quando o tempo acaba ou quando a margem desce abaixo de `min_rate_remaining`, com um aviso; sem login (60 chamadas por hora) o rápido e o turbo são recusados com o motivo; precisa do token de uso único, vive em memória e o banner da consola nomeia-o. `GET` e `POST /api/mode`.
- **Depois de um limite de taxa secundário**, o monitor espera pelo menos um minuto e depois duplica a espera até cinco minutos em vez de tentar de novo logo.
- **A aplicação de terminal interativa** `tui_textual.py` (opcional, `pip install textual`): separadores Resumo, Repositórios, Builds, Desempenho, Scripts e Definições (os interruptores básicos), um filtro, os níveis do linter, atualizar, abrir no navegador, Acerca de e Ajuda; `--lite` mostra os separadores da edição lite. A vista simples com Rich (`tui.py`, `--once`) mantém-se e também tem `--about` e `--help-topics`.
- **A edição vê-se logo**: um banner de arranque (`GitHub Actions Monitor LITE 1.6.3 · porta 8766 · actions_monitor_lite.json · sem sentinela · http://127.0.0.1:8766/`, ou COMPLETE · porta 8765 · sentinela ativa), o título da janela da consola e do terminal, a etiqueta `[LITE]` / `[COMPLETE]` nas linhas de estado, no `--doctor` e nas vistas de terminal, e o mesmo título nos lançadores.
- Guias novos em oito idiomas: **A sentinela e as suas verificações A1-A13** (o que é, como arranca, os ficheiros que escreve, como lê-la, a regra exata, a definição e a ação de cada verificação e as vinte e cinco verificações do A10; um teste mantém o guia e o código de acordo), **Quotas e planos** e **Os seus primeiros cinco minutos** (`FIRST_STEPS`); o guia de migração tem um bloco da 1.5.x para a 1.6.x e o README tem um seletor entre as duas edições.
- Testes para tudo isto (as versões semânticas, o aviso offline, desligado e em instalação isolada, o markdown seguro, o índice, o token de uso único, a descoberta, o `--doctor`, as quotas para repositórios públicos e privados, Windows e macOS, sem token, Enterprise e um 403 do relatório de faturação, o banner e os lançadores).

### Alterado

- A página de Definições começa pelo separador **Básico**; o guia `SETTINGS` é gerado com ele.
- O monitor lista os repositórios da conta com o seu tipo (arquivado, fork, privado, vazio); um `gh` mais antigo sem esses campos volta à lista simples.

### Segurança

- Nada de novo escreve no GitHub. O aviso de atualização, o relatório de faturação e a descoberta são só de leitura e podem ser desligados; nenhum envia dados sobre si. Os painéis Ajuda e Acerca de são servidos deste computador e o texto de suporte não leva nenhum segredo.
- Escrever uma definição, confirmar uma ação do assistente de IA e acrescentar um grupo sugerido precisam do token de uso único da página.

## [1.6.2]

> Esta versão está, por enquanto, apenas em inglês; a tradução chegará numa versão posterior.

### Adicionado

- **A catch-all group** `rest` ("Everything else", prefix `*`) at the end of the example catalogue of ecosystems, so a new installation leaves no repository out.
- **An automatic group "Unclassified"** for the repositories that no group claims (setting `show_unclassified`, on by default; an explicit choice of ecosystems is respected).
- **A warning when the filter hides repositories**: a banner (complete and lite) says "your ecosystem filter hides N of the M repositories of the account" and names them.
- **The lite edition starts with what you already set up**: on its first start `actions_monitor_lite.json` copies from `actions_monitor.json` (when it exists) the account, the repositories and ecosystems to watch, the catalogue files, the exclusions, the language and the reading depth, and says so on the console. Without such a file its template watches all the ecosystems.
- **`tui.py --lite`** (or `MONITOR_MODE=lite`) reads the lite edition on port 8766.
- **`redrule.py`**, the single small rule of "red on main", used by the sentinel and by the lite edition (which marks the figure as approximate because it guesses the default branch).
- **`ghamon_etag_invalid_total`**, the count of damaged cache entries, in `/metrics`.
- Tests: header-data parity between the complete and the lite edition, the catch-all group, the hidden-repository count, the lite start, the webhook hot mark, the damaged cache entry, and that importing the monitor or the sentinel never loads Rich.
- Guides `LITE` and `SETTINGS` (eight languages) updated.

### Alterado

- **Both editions show the same header figures**: runs, failures, successes, compute minutes, running and queued are counted once, by the server, over the same 24 hours with each run counted once; the lite edition reads as deep as the complete one. The lite edition hides the "unsigned" tile.
- **A webhook event marks the repository as hot**, so the next cycle reads it again whatever the event said.
- The GitHub allowance tile is painted from the first moment, while the repositories are still loading.

### Corrigido

- A new installation with the example catalogue saw almost no repository; the lite edition detected one repository out of 129 because its template filtered by ecosystem.
- **A damaged cache entry is only a miss**: it is thrown away and the endpoint is read again in full.
- "Red on main" and the compute minutes differed between the two editions.

### Segurança

- The lite edition never inherits the sentinel, the AI, the webhook, the outputs or the notifications, nor any secret, from the complete one; it writes neither `ci_red.json` nor a signing queue.

## [1.6.1]

> Esta versão está, por enquanto, apenas em inglês; a tradução chegará numa versão posterior.

### Adicionado

- **The lite edition**, a second and simpler product in the same package: `MONITOR_LITE_GITHUB_ACTIONS.bat` / `.sh` / `.command` or `--lite` / `MONITOR_MODE=lite`. What is running and what failed, failures and successes of 24 hours, red on main, the history and the basic charts; a short Settings page (account, repositories and ecosystems, refresh, language, theme); its own file `actions_monitor_lite.json`, its own state files with the suffix `_lite` and port 8766, so both can run side by side.
- **`act` command in the repository panel**: for each workflow of the repository, `act -W .github/workflows/FILE -j JOB` ready to copy. The monitor never runs it (running it exists only as a confirmed action of the AI assistant).
- **A container example** (`deploy/Dockerfile`) that the CI builds.
- Guide `LITE` in eight languages, a Lite-versus-Complete table in every README and new screenshots of both editions in light and dark.
- The roadmap lists what did not fit: local mirror of artifacts, FinOps of the minutes, self-hosted runner status and an OTLP export, and the notes of the terminal view (why it uses Rich).

### Segurança

- The lite edition has no sentinel: it is not imported and its endpoints answer 404.

## [1.6.0]

> Esta versão está, por enquanto, apenas em inglês; a tradução chegará numa versão posterior.

### Adicionado

- **Conditional reads (ETag)**: every read of the run lists sends `If-None-Match`; a `304 Not Modified` answer costs no quota. The header and `ghamon_etag_saved_total` count the reads saved; `cache.etag.*` in the Settings tab.
- **Resilience to network cuts**: when every read of a cycle fails with a connection problem the page keeps the last picture with an offline banner and resumes by itself; `offline` and `online` events (they can be notified) and `ghamon_offline`.
- **Analytics** (section A12 of the Sentinel tab, `/api/analytics`, `/metrics`, the Grafana JSON source): p50 / p95 of the duration of each workflow, of the queue time of its jobs and of each step; workflows that got slower than usual; **flaky** workflows (failed, then passed on the same commit, or needed another attempt), only a label that never changes what counts as red.
- **Incoming webhook in real time**: a signed `workflow_run` event updates the run list of its repository without reading GitHub, `workflow_job` events bring queue and step times; only short validated fields are kept (`/api/live-events`).
- **Workflow linter**: `lint_workflows.py` (actions not pinned by SHA, missing or broad permissions, secrets in clear text, injection, `pull_request_target` with the PR's code), rules switchable with their own severity, a line in the daily report and the section A13. A comment `# monitor-lint: ignore RULE reason` or the setting `lint.ignore` silences a finding.
- **Notifications** (off by default): Telegram, Discord, Slack, Matrix, MQTT and a local HTTP address, a limit per hour, a test button and a documented adapter contract (`monitor/docs/schemas/notification_event.schema.json`).
- **AI assistant**: new providers `anthropic` (Messages API, the model is yours to choose) and `copilot` (`gh copilot` with your own login, text only, no tools); new tasks (daily report, release notes, a question about a repository); settings for the kinds of event, the repositories, the language and the limits, a test button and the use of the day. A closed list of actions (`gh run rerun`, `gh issue close`, `act`), only PROPOSED by default.
- **The figures of the header are tiles** with an icon, a big figure and a small label, coloured by state, with a tooltip, a click that leads to the tab, counting figures and a skeleton that shows the last known values at once; the second line (repositories, hot, mode, reads saved, GitHub allowance with a bar and a live countdown, connection, last update and the loading progress) is made of tiles too.
- **Terminal view**: `tui.py` draws a live grid in the console (read-only, optional, needs the package `rich`; the monitor and its tests need no package).
- **For servers and bigger accounts**: `GET /api/health`, `GH_HOST` for GitHub Enterprise Server (every link of the page follows it), `discover_limit`, minimum permissions per feature, and a guide to run it as a service (systemd, launchd, a scheduled task, a container) and behind a reverse proxy.
- Published JSON schemas of `ci_red.json`, of the public export and of the notification event (`monitor/docs/schemas`), and a public roadmap (`docs/ROADMAP.md`).
- New guides in eight languages: notifications, the AI assistant, analytics, console tools and deployment; the webhook guide covers the real-time events. All screenshots were redone (light and dark, console tools included) with `tools/make_screenshots.py` and invented data.

### Alterado

- **Settings**: new sub-tabs for reads and cache, notifications, analytics, the linter and the terminal view; the AI and webhook sub-tabs have all their options.

### Corrigido

- **The linter no longer cries wolf on placeholders**: a value that looks like a secret is classified (a known token format or a long high-entropy string is serious, a readable filler such as `placeholder` or `changeme` is only information, anything else a warning; references and empty values are no finding) and its value is never printed or stored.
- **A browser that closes or reloads its tab while the page is loading no longer prints a traceback** (`ConnectionAbortedError`, `ConnectionResetError`, `BrokenPipeError`): they are counted in `ghamon_client_disconnects_total`; a real error is still shown.

### Segurança

- The incoming webhook stays off by default, on `127.0.0.1`, with a mandatory HMAC.
- Notification secrets live only in environment variables; hosts are fixed; notifications never write to GitHub.
- AI actions: running one needs its own switch and a confirmation of the full command each time, only on targets the monitor already watches, with a limit per hour, a local log and a lock after two failures in a row.

## [1.5.2]

> Esta versão está, por enquanto, apenas em inglês; a tradução chegará numa versão posterior.

### Adicionado

- **The Settings tab is organised in sub-tabs**, ordered from the common to the advanced (This browser, General, Refresh and limits, Sentinel, Surface checks A10, Readiness A11, Folders and files, Outputs, External AI, Incoming webhook). Inside a sub-tab the settings sit in titled blocks whose first field is the main switch (the rest of the block dims while it is off). Every field shows its unit and range, a badge (needs a restart / applies now), a badge for the safety options that start in their conservative state, and one line of help. A search box filters all the sub-tabs, each sub-tab counts its unsaved changes, Save and Discard stay visible, the arrow keys, Home and End move between the tabs and the last sub-tab used is remembered by the browser.
- **Every setting of the configuration file is in the page now**: the A10 checks (a switch per check and its limits), the weights of the ecosystem health score, the sources of the pinned versions, the Actions-minutes ceilings, the required files, the audit file patterns, the hot period of the sentinel, the unknown-sample rule of A2, the candidate prefixes, the list of repositories and the switch of the incoming webhook.
- **Signing queue by trust**: each row says `verified`, `unknown` or `failed`; the Sentinel tab has a Signature filter with the count of each kind; `read_report.py --sign-trust` filters the console list and the export, and the exported rows carry `trust`.
- **Readiness chips in the header**: one coloured chip per ecosystem with its health score.
- **A minimal Grafana board** (`red_by_ecosystem.json`) and a test that checks every metric of both boards against what `/metrics` serves.
- New guide `WEBHOOK` (refresh-only mode) and a commented example of the pin sources, in eight languages.
- `tools/make_settings_doc.py` writes the settings table of the guides from the schema and the texts of the page, and the CI checks it.

### Alterado

- **The daily report groups the issue-closing suggestions** in one line per repository (the monitor still closes nothing).
- **The contract of the profile dashboard** is documented and checked by a test (`/api/outputs/dashboard.json` is exactly the document of `ci_red.json`; the public export never carries the signing side).

### Segurança

- The shared secret of the webhook is never shown in the page: it only says whether it is defined.

## [1.5.1]

> Esta versão está, por enquanto, apenas em inglês; a tradução chegará numa versão posterior.

### Adicionado

- **The settings page can set the external AI of the sentinel** (group "External AI for the sentinel"): `ai.provider` (`none` / `ollama` / `openai-compatible`), `ai.model`, `ai.ollama_url` (only this computer), `ai.base_url` (https only), `ai.api_key_env` and `ai.daily_limit`. Off by default; an outside service receives data of your repositories.
- **`migrate_state.py`**: brings the files written before 1.5.0 to the new names (events, report history, release candidates, batch records, the `report_history_days` setting). A dry run by default; `--apply` copies and keeps the old files, `--move` renames them; nothing that exists is overwritten. One-page guide in `docs/MIGRATING.md`, in eight languages.
- **`--init-catalog`** creates editable `ecosystems.json`, `targets.json` and `profiles.json` from the examples.
- A test makes sure no document sends the reader to a command that was renamed in 1.5.0 (only the tables of old and new names and the migration guides may name them).
- The version in every README.

### Alterado

- **First start without catalogue files of your own**: the console says the example files are in use.
- Python 3.11 or newer is the documented minimum (tested on 3.11 and 3.13 on Windows, Linux and macOS).

### Segurança

- Only the NAME of the environment variable that holds the AI key can be set: the key itself is never shown or saved.

## [1.5.0]

> Esta versão está, por enquanto, apenas em inglês; a tradução chegará numa versão posterior.

**Update notice (read this first).** Several files and settings have English names now. Nothing is lost: the old names are still READ where a file written by an earlier version may exist, and the new names are the only ones written.

| Before 1.5.0 | From 1.5.0 |
|---|---|
| `leer_parte.py` | `read_report.py` |
| `eventos.py` | `events.py` |
| `parte_history.py` | `report_history.py` |
| `LOTE_GITHUB_ACTIONS.bat` / `.sh` / `.command` | `BATCH_GITHUB_ACTIONS.bat` / `.sh` / `.command` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` (copy or rename them to keep the history of events) |
| `PARTE_CENTINELA_DIA_<day>.txt/.json` (report history) | `SENTINEL_REPORT_DAY_<day>.txt/.json` (the old ones are still read) |
| `PARTE_CENTINELA_<time>.txt` (saved report) | `SENTINEL_REPORT_<time>.txt` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_<time>.json` | `<signed_dir>/batches/batch_<time>.json` (the old records are still read) |
| `parte_history_days` (setting) | `report_history_days` (the old name is still read) |
| `monitor_y_centinela.zip` and folder | `github_actions_monitor.zip` and folder; `LEEME_CORREO.txt` is `README_MAIL.txt` |
| A8 looked for `RECONCILIACION_TOTAL_AUDITORIAS_*.txt`, `MAPA_DE_RONDAS_*` | the names are `sentinel.audit_files` (neutral defaults `RECONCILIATION_TOTAL_*.txt`, `ROUNDS_MAP_2*.txt`, `ROUNDS_MAP_EXTRA_*.txt`); set your own there |
| `ci_red.json`, its schema and the `--export-status` files | unchanged (they are a contract) |

- **English by default.** The language of the system no longer decides: the tools start in English until you choose another one in the Settings tab, with `language` in `actions_monitor.json`, `MONITOR_LANG` or `--lang`.
- **A clean, neutral package.** `ecosystems.json`, `targets.json` and `profiles.json` are no longer part of the package: only the `*.example.json` files travel, and a missing default file falls back to its example. Your own files live anywhere and are named by `ecosystems_file`, `targets_file` and the new `profiles_file`; the folder of your local signing tools is the new `tools_dir`. The tests use their own fixtures (`tests/fixtures`).
- **Settings tab.** A new tab changes the values of `actions_monitor.json` from the page: a whitelist of keys with their type and range, one request refused as a whole when a value is invalid, a copy of the previous file in `config_backups/` before every save (the last ten are kept), an atomic write, only on 127.0.0.1 with the same Host and Origin checks as every other endpoint, JSON only. Tokens, secrets, signature keys and the command of the sentinel are not in the list: they are never shown and never written, and every other key of the file is kept as it was. Each setting says whether it needs a restart. The language selector, the theme and the dense view moved there.
- **Buttons and icons.** Buttons have relief, light up on hover and sink when pressed; the icon buttons are inline SVG with an accessible name and a tooltip in the 8 languages. Colours, type, cards, bars and the ring follow the status dashboard of the profile repository.
- **Life in the charts.** Bars grow in, what is red or running has a discreet pulse, the figures of the header count up, hovering a bar highlights it and gives its text as a tooltip, widths change smoothly; all of it stops with `prefers-reduced-motion`.
- **Outputs for other tools (off by default, 127.0.0.1 only, no new token).** `/metrics` in the Prometheus format (red workflows per ecosystem and repository, red streaks and hours, builds waiting for a signature, A10 paused, allowance left, incomplete snapshot...), `/api/outputs/grafana.json` for the Grafana JSON / Infinity source and `/api/outputs/dashboard.json` (the `ci_red.json` document) for the status dashboard. An importable Grafana dashboard is in `docs/grafana/` and the details in `docs/OUTPUTS.md`.
- **Report:** a line (code `tag_vs_manifest`) when a release tag is ahead of the version of the manifest; the unsigned figure is ordered by the longest wait and says how long it is; the repository panel suggests the `gh issue close` command (never run) for a failure issue whose workflow is green again; the `hil` batch profile is documented in `profiles.example.json`; tests for `finalize` and for `monitor_link`.
- **Docs:** `docs/SETTINGS.md`, `docs/OUTPUTS.md`, README and QUICKSTART in the 8 languages updated, screenshots made with invented repositories.

## [1.4.5]

> Esta versão está, por enquanto, apenas em inglês; a tradução chegará numa versão posterior.

- **The report says when the snapshot is incomplete:** a line with the stable code `incomplete` (still loading, no local workspace, errors while reading) right after the headline, so nobody acts on a half-read list of red repositories or signing queue.
- **Signing summary:** one line with how many releases wait to be signed (verified / not checked / failed the check) and how many builds are build-only on purpose, so "not signed on purpose" is not confused with "signature missing" (code `sign_summary`).
- **A10 paused for the quota is said in the report** (code `a10_paused`) with the allowance left and needed, and the three knobs that control it.
- Texts in the 8 languages; tests for the three lines.

## [1.4.4]

> Esta versão está, por enquanto, apenas em inglês; a tradução chegará numa versão posterior.

- **Author and licence are always visible:** the web panel has a footer with the author and the licence, `read_report.py --version` and the new `gha_dispatch_all.py --version` print them under the version, and the monitor prints the same line when it starts. The text is in the 8 languages (`ui.about`); the author and the licence come from `tool_version.py`.
- **Bridge to the dashboard written down:** `docs/CI_RED_BRIDGE.md` says what `ci_red.json` contains (schema 2, `complete`), how to export it and what a reader must check; the monitor still never pushes or commits.
- Tests for the author line in the 8 languages, the footer, both `--version` flags and the start-up line.

## [1.4.3]

> Esta versão está, por enquanto, apenas em inglês; a tradução chegará numa versão posterior.

- **A workflow that only runs on pull requests no longer makes A2 inconclusive:** `pull_request` and `pull_request_target` join the events whose runs never sit on the default branch (like `workflow_dispatch`, `release` and `workflow_call`), so a workflow such as a contract integration check that only runs on pull requests is not asked for a last run on main. A workflow that also has `push` or `schedule` still counts. Tests for both cases.

## [1.4.2]

> Esta versão está, por enquanto, apenas em inglês; a tradução chegará numa versão posterior.

- **A2 no longer counts a run in progress or a cancelled one as seen:** when it resolves a hidden workflow, the Sentinel now asks for the last completed runs of that workflow on the default branch (`gh run list -w <file> --branch <default> --status completed -L 10`, read only) and uses the first one with a real conclusion. A cancelled or skipped run (and anything without a conclusion) is ignored, so it can no longer hide an earlier red; a workflow with no completed run with a conclusion on the branch stays inconclusive on its own. Same quota gate, call limit and cache as before.

## [1.4.1]

> Esta versão está, por enquanto, apenas em inglês; a tradução chegará numa versão posterior.

- **A2 resolves a hidden workflow instead of giving up on the whole repository:** when a repository has a full run sample and a workflow of its clone (one that can run on the default branch) is missing from it, the Sentinel asks GitHub for the last run of THAT workflow on the default branch (`gh run list -w <file> --branch <default> -L 1`, read only). A red answer counts as red in A2; a green one removes the workflow from the inconclusive list; a workflow with no run on the branch stays inconclusive on its own and the panel names it (`repo/file.yml (no run on the default branch)`) instead of only the repository. Without quota (same gate as A10: `min_rate_remaining` x `surface.min_rate_factor`, plus the hourly budget) the workflow stays inconclusive and the panel says why. New options `sentinel.a2_resolve_max_calls_per_tick` (4; 0 = never ask) and `sentinel.a2_resolve_ttl_seconds` (3600, how long an answer is kept; it is also saved in the cache file). The snapshot carries `a2.inconclusive_workflows` (labels) and `a2.inconclusive_details`; `a2.inconclusive` is still the list of repositories. 5 new texts in the 8 languages and a reworded `ui.a2_inconclusive`.

## [1.4.0]

> Esta versão está, por enquanto, apenas em inglês; a tradução chegará numa versão posterior.

- **New layer A11 "Readiness" (read only, real data only):** a panel of the Sentinel tab, a traffic light in its header and two lines of the report. It is switched with `sentinel.readiness.enabled` and described in `readiness.py`.
  - **Release readiness:** one row per repository with at least `candidate_min_entries` entries in `[Unreleased]` (external ecosystems excluded): CI of the default branch (the single rule of A2) with the commit it ran on, whether the version the clone declares (`*.project.json`, else `pyproject.toml`, else the first CHANGELOG heading) is already above the last release, whether a build exists after that release, whether it is signed (the states of A5), and the next step (`fix the red CI`, `wait for run data`, `bump the version`, `build in Actions`, `sign`, `publish`, `cut and publish`). A green CI over a full run sample that may hide an older workflow says so.
  - **Ecosystem health:** per ecosystem, 100 minus weighted counts of red CI, stuck builds, secrets, serious alerts, other alerts, Dependabot PRs older than `stale_pr_days`, builds waiting for signing and repositories with hygiene problems (`sentinel.readiness.health.weights`); the parts that lower the score are listed. No score is shown (`?`) when fewer than `min_coverage` (0.5) of the repositories of the ecosystem have run data and alerts. The report warns when a score is under `warn_below` (70).
  - **Dependency pins:** repositories that pin an older version than the one of the repository that provides the contract or library. Where the pins live is data (`sentinel.readiness.pins.sources`): a JSON table of pins in the provider (`pin_table`) or lock files in the consumers (`lock_files`, the oldest one found counts). Plain file reads of the local clones, cached `pins.refresh_seconds`; an ecosystem without a configured source is listed as having none, and nothing is guessed. The shipped example has no source.
  - 60 new texts in the 8 languages; `tests/test_readiness.py` (rules, weights, coverage, pins on a temporary tree, the page and the 8 catalogues).
- **`docs/CI_RED_SCHEMA.md`:** says explicitly that the PC publishes neither `ci_red.json` nor `pending_sign` to any repository or dashboard (the signing side is local by decision); a public consumer recomputes the rule from the public runs or uses `read_report.py --export-status`.
- **Quota tuning from the log (`actions_monitor_log.txt`, 3 days, 889 samples):** the shared allowance was under the floor (`min_rate_remaining` 1500) in 11% of the samples since 5 November and under 3000 in 45%; the hourly burn was 3000-5000 calls in most hours and reached the limit in some. In the maintainer's `actions_monitor.json`: `refresh_seconds` 120 -> 180 (the real cycle was a median of 139 s) and `sentinel.surface.min_rate_factor` 2.0 -> 1.5 (the cold calls of A10 are about 260 a day, so they can run above 2250; with 3000 they waited almost half of the time). `max_repos_per_tick` (6) and the daily cold cycle stay: they cost less than 1% of the allowance. The shipped example keeps its neutral defaults.

## [1.3.3]

> Esta versão está, por enquanto, apenas em inglês; a tradução chegará numa versão posterior.

- **A2 ignores workflows that never run on the default branch:** when deciding whether a full run sample hides a workflow, the files of the clone whose `on:` has no `push`, `pull_request` or `schedule` for the branch (only `workflow_dispatch`, `release`, tag-only `push` without `branches`, or `workflow_call`) are no longer expected in the sample. `on:` is read with the standard library only (string, list, map, and the YAML `true` key); if it cannot be parsed the workflow counts as before. The workflow scan carries the new field `main_triggered` (`true`/`false`/`null`).

## [1.3.2]

> Esta versão está, por enquanto, apenas em inglês; a tradução chegará numa versão posterior.

- **A2 shows `unknown` instead of green when its sample is full and inconclusive:** a repository whose list of runs is as long as the sample asked for (`runs_per_repo` / `cold_runs_per_repo` of the monitor, which the check did not see before) and whose clone has a workflow file with no run in that sample (or that has no clone) is listed as inconclusive, and A2 is `unknown` unless something is red. New option `sentinel.a2_full_sample_unknown` (default `true`; `false` = only informative as before). The page lists the repositories.
- **`profiles.example.json`:** a neutral batch-profiles template that matches `targets.example.json` and `ecosystems.example.json`. A test (and the release gate) validates it against those catalogues, not the maintainer's, and checks that every profile selects at least one target.
- **Clean-install check in `make_release`:** before anything is left in the output folder the zip is extracted into a new, empty temporary directory and, from there with `python -I`, every member must be present, every module must compile, `read_report.py --version` must run and the whole suite must pass; any gap fails the release.
- **Wording:** README and QUICKSTART in the 8 languages now say that the package writes nothing to GitHub on its own and that only `dispatch --go`, `dispatch --real` and `finalize --execute` (which you run) do.
- **A10 quota:** the share of the sentinel's per-tick call budget that A10 may use is now `sentinel.surface.budget_share` (default `0.5`, as before but configurable); the page shows "A10 paused for quota" with the allowance left and the one needed (`min_rate_remaining` x `min_rate_factor`) while the cold calls wait.

## [1.3.1]

> Esta versão está, por enquanto, apenas em inglês; a tradução chegará numa versão posterior.

- **A run built on another commit is never offered for signing:** when `dispatch` could only find a recent run of another commit (`sha_matched` false), `finalize` now lists it as not ready with the reason and gives no signing command; an old batch without the field behaves as before. Tests with two concurrent runs of different commits.
- **`/api/data` goes through the same Host/Origin guard as the other routes** of the local server (DNS rebinding).

## [1.3.0]

> Esta versão está, por enquanto, apenas em inglês; a tradução chegará numa versão posterior.

Made to be shared: eight languages, authorship and licence in every file, no private data, and nothing tied to one GitHub account.

- **8 languages** (en, es, de, fr, it, ja, zh, pt = European Portuguese) for the page, the command line tools, the launchers, the events, the reports and the error
  messages. `i18n.py` + `locales/<lang>.json` (one flat catalogue per language, standard library only, `t("key", name=value)` with a fallback to English). The language
  is `language` in `actions_monitor.json` (default: the system language, English if unsupported), a selector in the header of the page (remembered by the browser),
  `MONITOR_LANG` / `JUANENRAC_LANG`, or `--lang CODE` in every tool (it wins over the rest). Technical names, commands, paths and the markers that scripts read
  (`SKIP`, `DISPATCHED`, `READY`, `FAILED`, `Summary:`, `BUILD ONLY`, `WOULD DISPATCH`...) are never translated. Events in `events_monitor.jsonl` now carry a stable
  `code` (and `args`) next to the text, so nobody has to parse a language.
- A test checks that the 8 catalogues have exactly the same keys, none empty, the same `{placeholders}`, that every key used by the code and the page exists, and that no
  visible string in the code bypasses `t()`.
- README and QUICKSTART in the 8 languages (`README_<lang>.txt`, `QUICKSTART_<lang>.txt`); `README.txt` is now a short language chooser with the quick start.
- **Authorship and licence**: every source file carries "Copyright (C) 2026 JuanenRac (Electro Hobby 3D)" and "GPL-3.0-or-later - see LICENSE"; JSON data files carry
  `_author` / `_license`; `LICENSE` (GPL-3.0 text), `NOTICE` and `AUTHORS` travel in the zip. `make_release.py` refuses to build when a file lacks them, when private data
  would travel, when the locales differ, or when a launcher loses its executable bit.
- **Shareable**: `github_owner` in the configuration (default: the account of `gh`) replaces the constant that was spread over three modules; the ecosystem prefixes and the
  signing tools are data (`ecosystems.json`, neutral `ecosystems.example.json`; `"*"` = every repository; `"external": true` = only reported) and so are the targets (`targets.json`
  is the maintainer's real catalogue, `targets.example.json` the neutral one; `targets_file` / `ecosystems_file` choose them; keys that start with `_` are metadata).
  The example configuration is neutral. Nothing of this adds a call to the hot cycle.
- **The workspace is optional**: without local clones the monitor starts in a reduced mode (only what the GitHub API gives: no local signing queue, no audit report, no
  CHANGELOG scan) and says so on the page, in the report and at start, instead of stopping. `MONITOR_ROOT` / `MONITOR_AUDIT_DIR` / `MONITOR_SIGNED_DIR` and `signed_dir`
  were added next to the old names. The roadmap layer (A9) is optional too.
- Launchers: menus and messages come from `launcher_msg.py` (your language); comments in English; header on every file.
- Fix: `workspace_root()` no longer ends the monitor when the sentinel starts without a workspace.

## [1.2.0]

> Esta versão está, por enquanto, apenas em inglês; a tradução chegará numa versão posterior.

What was missing and what else can be done on GitHub, all of it read only and local.

**Part A - what was missing**
- `ci_red.json` schema 2 is now a documented contract: `docs/CI_RED_SCHEMA.md` (shape, the one rule of "red", what is for the owner only). Nothing is
  published from the PC. Optional, explicit exports (never a commit or a push): `read_report.py --export-status DIR` writes ONLY the red list
  (`ci_status_public.json/.md`); `read_report.py --export-sign-queue FILE` (.json/.csv) writes the global signing queue with the local commands.
- Attestation: the signing queue shows whether the build has an attestation (existence by digest of the signed files, one lookup per entry, no signature
  check; switch `sentinel.surface.checks.attestation`). A missing one is a line in the report.
- More verified formats: HYDRA `hydra-sign` (`FILE.sig` = base64 Ed25519 over the bytes of the file, the pinned release key, read in blocks) is checked
  definitively; URTC `.imgsig` has its strict format checked (152 hex digits + LF; malformed = not valid) and stays "unknown" when well formed (the signed
  message also needs the build header, which the signed folder does not carry); ARMOR APKs are signed inside the APK by apksigner and stay "unknown".
- `HYDRA-UMC-OS` is labelled on purpose in `targets.json` (`"build_only": true` + `reason`): `plan` lists it under BUILD ONLY and it is no longer an orphan.
  The signing tools were not touched (its workflow takes other inputs and a different signature scheme).
- Fix: `ci_red.target_path` refused every Windows path written with backslashes (`C:\...`); only forward slashes were accepted.

**Part B - the A10 layer "Actions & releases surface"** (`surface.py`, new section of the tab, a switch and a threshold per check under `sentinel.surface`)
- Actions: workflows disabled by hand, schedules with no run in N days (only when the sample of runs covers the window), `uses:` not pinned by SHA
  (reusable workflows flagged apart), `permissions: write-all`, `pull_request_target` with a checkout of the PR, stuck concurrency queues, failures on only one
  OS of a matrix, artifact cost and retention, required status checks that are red or missing (GraphQL), `dispatch --profile release|nightly|hil` with a canary
  (the first target alone, the rest only if it is green) and a quota gate (`--min-rate`, fails closed). Profiles live in `profiles.json`.
- Releases: expected assets per kind of target (alert when a release was published incomplete), tag vs manifest vs CHANGELOG, GitHub Packages, forgotten drafts
  and pre-releases, `release_notes.py` (a DRAFT of notes from the commits since the last tag; it publishes nothing).
- Security: critical/high alerts by age with a ranking of repositories, coverage (a stack without CodeQL/Dependabot), secret scanning open vs resolved,
  Dependabot by priority (runtime major first, CI-only last).
- Issues and PRs: suggestion of `gh issue close` for build issues whose CI is green again (an event with the text; nothing is ever closed), overdue milestones,
  old human PRs, PRs that touch workflows or CODEOWNERS, the merge queue (approved with green checks). Stale board cards: PENDING (needs per-item reads and a threshold).
- Manifest vs evidence (maturity), 8-language README parity failures, Actions minutes per ecosystem in the header, the report and A7.
- `finalize --execute` now tells the running monitor (127.0.0.1) to refresh just the signed repositories and rewrite `ci_red.json` at once (`monitor_link.py`).
- Optional signed webhook receiver (`webhook.enabled`, off by default, 127.0.0.1 only, HMAC with a shared secret from the config, never a GitHub token).
- Cost: nothing in the hot cycle. Cold, spread over ticks and inside the hourly budget: 2 REST calls per repository per day, one GraphQL query per 15
  repositories per day, 3 for Packages, plus the jobs of red runs and the attestation lookups of the signing queue, and only while the allowance is above
  twice `min_rate_remaining`. The hot GraphQL pass asks for 3 more fields per node (alert dates, review decision, checks state): no extra call.
- The gate also compares `sentinel.surface` of the example file with the defaults and validates `profiles.json`.

## [1.1.1]

> Esta versão está, por enquanto, apenas em inglês; a tradução chegará numa versão posterior.

- **Cross-platform:** the monitor and the batch tools work on Windows, macOS and Linux. Launchers `MONITOR_GITHUB_ACTIONS.sh`/`.command` and `BATCH_GITHUB_ACTIONS.sh`/`.command` (the zip keeps the executable permission and make_release rejects Windows line endings in them).
- New `platform_compat.py`: the command that starts a child tool (`py -3` on Windows, the current interpreter elsewhere), the text of the commands that `finalize` shows (cmd/PowerShell or POSIX quoting), UTF-8 console and a notice with the way to install `gh` on each system.
- New tests of the cross-platform part (Windows and POSIX simulated from any system).

## [1.1.0]

> Esta versão está, por enquanto, apenas em inglês; a tradução chegará numa versão posterior.

Signature trust, a stable bridge to the dashboard, orphans and conventions in the batch tools, and a more useful page.

- Signature trust: `sigverify.py` (standard library, read only, no network) checks the signed folder `_firmados/<REPO>/release-<version>/` against the PUBLIC
  key each ecosystem pins (URTC `release_sign.py`, ARMOR helper `PACKAGE_PUBLIC_KEY`, HYDRA updater `RELEASES_PUBLIC_KEY`, or `sentinel.signature_pubkeys`).
  Every state now carries `signature_kind` (none | dev | release) and `signature_verified` (true | false | "unknown"); only a release signature that verifies
  (`trusted`) lowers the pending-signature alert, besides "published". A signature that does not verify keeps the alert and says so in the report.
  `sentinel.require_verified_signature` (default true; false = the 1.0.0 rule). Formats this module cannot check (.sig2, .hdr2, .imgsig, APK, hydra-sign) are
  "unknown", never "false". The build attestation still needs the network and stays with the signing tools.
- `ci_red.json` schema 2: per repository a `pending_sign` list (workflow, hours, state, signature_kind, signature_verified, last_build_at, url) next to the red
  workflows, plus `schema`, `pending_sign_repos` and the threshold; the format is documented in `ci_red.py` and is only ever extended.
- One definition of "last run on main" (`signstate.completed_runs`) shared by the red check, the green-without-release check and the target states.
- `ci_red.target_path` refuses D: paths, WSL/Git Bash forms of D: and drive/UNC paths that the running system cannot use; the tests simulate both systems
  and the whole suite now passes on Linux.
- `gha_dispatch_all.py plan` always ends with the section "Signature orphans" (green CI + known `*-build.yml` + no target); coverage is by repository AND workflow.
- Convention for targets (ecosystem prefix -> default signing tool, workflow in the known list); `targets.json` only holds the overrides and always wins.
  `hygiene --write-candidates` writes the proposed entries to `targets.candidates.json` (never applied by itself, never packaged).
- Page: clickable header counters "red on main" and "unsigned" (filter the repositories; the second one also focuses the signing queue), the signing queue
  with its commands and a copy button, repository panel with build / signed / published, signature kind and verification, and the suggested command;
  a header badge when a minutes budget reaches 80 % (red when exceeded); "yesterday vs today" also compares budget warnings and the lines of the report.

Not done: reading the build attestation / SBOM (network); `HYDRA-UMC-OS` has a build workflow but its signing tool does not support it yet (listed as an orphan).

## [1.0.0]

> Esta versão está, por enquanto, apenas em inglês; a tradução chegará numa versão posterior.

First numbered version. What the package does:

- Monitor of GitHub Actions for the four ecosystems (local web page, run cache, stuck builds, build-failed/build-stuck issues).
- Sentinel layer A (read only, no AI needed): A1 stuck builds, A2 red CI (one criterion: last completed run of each workflow on the default
  branch), A3 CodeQL/Dependabot/secret alerts, A4 Dependabot pull requests, A5 releases (candidates, green builds without a release,
  pending signature), A6 hygiene, A7 consumption (minutes and API allowance), A8 audits and rounds, A9 roadmap boards.
- Explicit state of each build target: built_on_gha -> signed_local (none | dev | release) -> published, with `last_build_at`,
  `last_signed_at`, `signature_kind` and the real hours waiting; local batch and signed-folder records lower the pending-signature
  alert without waiting for GitHub.
- Signing queue of the day (`a5.sign_queue`): most urgent first, with the exact finalize command of each target.
- Budget of Actions minutes per ecosystem (`sentinel.minutes_budget`, empty by default): warning at 80 % in the report and as an event.
- Event feed (`events_monitor.jsonl`) and `ci_red.json` (repository -> red workflows + hours pending signature), written atomically.
- Batch tools: `gha_dispatch_all.py plan|dispatch|status|finalize|hygiene` with `--only` or `--ecosystem`, `plan --json`,
  `finalize --json`, one retry of a failed dispatch at the end of the batch, targets as data in `targets.json`.
- `read_report.py`: the report as plain text from the running monitor, without spending API quota.
- `make_release.py`: quality gate (unit tests, clean zip, complete example configuration, version/changelog agreement) and SHA256SUMS.

Not done in this version: verifying release signatures against the public key and the build attestation from the sentinel
(different signature formats per ecosystem; the attestation needs the network; the signing tools verify both before publishing).
