# Roteiro

O que já foi publicado, o que vem a seguir e o que é apenas uma ideia, por essa ordem de certeza. São direções, não compromissos; uma issue ou um pull request é a melhor forma de fazer avançar uma.

## Onde está o monitor agora

Versão 2.0.2. A edição lite mostra o que corre e o que falhou. A edição completa acrescenta três sentinelas (CI, Collab e Security), uma lista de alertas, várias contas e uma equipa com funções, a pontuação de cada conta, a saúde de cada repositório e da equipa, relatórios agendados, um registo de ações, notificações (ntfy, Teams, correio eletrónico e Apprise), um assistente de IA opcional com predefinições de serviços compatíveis, o modo de serviço com Docker e uma página para todos os tamanhos de ecrã, do telemóvel ao 4K.

## Previsto, por esta ordem

Cada versão leva apenas conteúdo real: uma versão sem nada de real a acrescentar é saltada e nunca publicada vazia. Nada disto é dado como provado em serviços reais, salvo se o seu guia o disser.

### 2.0.2 a 2.0.9 - Depois do congelamento

O que só aparece com uso real prolongado: a migração desde a 1.8 e a 1.9, o crescimento dos eventos e da base de dados ao longo de meses, as sessões após uma atualização, os volumes do Docker, muitas contas com três sentinelas e o modo equipa em simultâneo, e o que a bateria de contrato encontrar. Nada da quarta fase (plugins, automação alargada, IA avançada) entra nestas versões; uma versão sem conteúdo real é saltada.

Os workflows do próprio monitor cumprem o que a sentinela de higiene pedirá aos outros: ações fixadas a um commit, as permissões mínimas e um limite de tempo em cada job.

## Feito da 1.8.2 à 2.1.2

### 2.1.2 - O monitor atualiza-se a partir de um menu, compara um período com o anterior e os painéis desdobrados chegam ao fundo

O menu Atualizações (edição Completa) mostra a versão instalada e as publicadas com as suas notas, aplica uma atualização com cópia prévia, verificação do zip face ao SHA256SUMS, migração da configuração e reinício, e volta atrás com um clique se a versão nova não arrancar; o atualizador autónomo continua como caminho de volta. A comparação põe um período junto ao anterior, com estados honestos quando um valor não se pode dizer, um relatório do que mudou, uma rota, um comando, uma secção do separador de gráficos e uma secção opcional do relatório agendado. Os ficheiros em que escrevem vários processos usam o bloqueio do sistema operativo, o painel desdobrado de um separador do Sentinela chega ao fundo da sua caixa, arrancar o monitor a partir do atualizador já não abre uma janela de consola por cada chamada a git e gh, e a imagem da arquitetura mostra no que o monitor se tornou.

### 2.1.1 - Dois sentinelas novos, um da cadeia de abastecimento e outro da entrega, e uma porta de release mais exigente

Dois sentinelas novos, desligados por predefinição e só na edição Complete, leem o que um repositório constrói e o que entrega sem escrever nada no GitHub: o da cadeia de abastecimento verifica nos ficheiros de workflow as ações não fixadas, os ramos móveis e as permissões demasiado largas ou em falta, e o da entrega compara releases, etiquetas, o changelog, os ficheiros de versão e as versões fixadas. O doctor mostra agora a vermelho um webhook de entrada sem segredo, a cobertura do webhook já não fica ativa quando o relógio é atrasado, e a porta de release compara o conteúdo de cada ficheiro do zip com o commit, aceita uma execução verde completa pela contagem que o unittest indicou e pode mostrar o andamento das suas suites.

### 2.1.0 - Ecrãs de parede com tema, logótipo e modo rotativo, uma cópia que se pode restaurar e um atualizador

Os ecrãs de parede usam o tema do produto e podem mostrar o logótipo da organização; uma janela pode percorrer os três ecrãs e saltar para um vermelho novo; o resumo mostra o mapa da frota por grupos; uma atualização do Dependabot que falha é um alerta próprio; e cada tipo de evento tem também o seu som neste computador. A instalação pode ser copiada por inteiro, verificada e restaurada, com agendamento se quiser, o doctor verifica o funcionamento com códigos de saída que não mudam e pode lançar-se uma purga a pedido. O atualizador leva uma instalação para qualquer versão publicada, copia-a primeiro e volta atrás se algo falhar. A porta de publicação nomeia os testes que falham e aceita uma passagem verde já vista, as etiquetas de estado dos painéis de detalhe ficam numa só linha, as ligações da página verificam-se lendo o endereço e o guia do contentor explica como abrir a primeira sessão.

### 2.0.9 - Uma auditoria independente mais segura, menus com grupos, um som por tipo de evento e comandos de chat só de leitura

A auditoria independente endureceu o monitor: o token de acesso já não viaja no endereço por omissão, um silenciamento por padrão já não silencia o que não é um workflow, o limpador de texto apanha mais formas de um log real, um cabeçalho com um segredo nunca segue um redirecionamento, uma entrega do webhook é verificada e não pode ser repetida, e um fornecedor na internet ou num endereço privado precisa do seu próprio interruptor. O menu da esquerda tem grupos com título, cada tipo de evento tem o seu próprio som, comandos só de leitura respondem no Slack e no Discord (desligados por omissão), os ecrãs de parede seguem o idioma da página principal e a IA integrada tem um único orçamento que também conta o aviso ativo. O registo de ações pode ser condição das ações e guarda o número de ficheiros rotativos que escolher, um ciclo conta uma só vez para todas as etapas da sentinela, e um workflow para a auditoria da imagem do contentor, com as falhas que encontrou no contentor, faz parte da versão.

### 2.0.8 - Um segredo do webhook mais seguro, check runs e um guia para configurar o webhook (a versão que fecha a quarta fase)

O segredo partilhado do webhook de entrada só viaja no ambiente (ou num ficheiro que a definição nomeia), o webhook também recebe eventos de check run, a vista Em direto diz que parte do tempo os eventos cobrem, e um guia em oito idiomas (`docs/WEBHOOK.md`) configura o webhook no GitHub passo a passo. Os estudos de contas reais acrescentam três linhas: um workflow cujo ficheiro foi apagado não é um que se possa ativar, um fork que nunca foi enviado não está enviado recentemente, e o runner `codspeed` é reconhecido como runner de terceiros pago. Os documentos já não dizem que o macOS corre no CI. É a versão que fecha a quarta fase: uma versão de estabilização antes da auditoria.

### 2.0.7 - Uma API de leitura para clientes, o repositório original de cada fork e os workflows desativados à mão

Uma API de leitura em `/api/v1/` para clientes (`me`, `repos` e `openapi`, desativada por omissão, com um contrato congelado); um acompanhamento opcional do repositório original de cada fork (`upstream.enabled`, desativado por omissão, com um limite de pedidos por hora); e um workflow que o proprietário desativou à mão deixa de ser um vermelho e aparece à parte (`ci.disabled_apart`).

### 2.0.6 - Três ecrãs de parede, desenhados e desativados por omissão

Os três ecrãs de parede estão desenhados: Geral (pontuação, lâmpadas da frota, gráficos, mapa de calor, runners e a quota), Agora (execuções em curso, fila, aprovações, falhas recentes e uma linha em direto) e Sentinelas (um cartão por sentinela com um radar animado). A página desenha ela própria cada gráfico, uma falha nova pisca uma vez e acalma, nada se mexe para quem pediu menos movimento, tudo se desloca um pouco a cada minuto contra a retenção de imagem, a página pode escurecer à noite, uma janela pode rodar pelas três páginas e um teste do navegador verifica-as em 1080p, 4K e rodadas nos oito idiomas. Os ecrãs estão desativados por omissão (`screens.enabled`), e o README e o guia dos ecrãs já os mostram.

### 2.0.5 - Menos falsos vermelhos, repositórios adormecidos e perguntas visíveis em ecrã inteiro

Um vermelho conta agora pela origem do evento: os workflows que o GitHub cria para si (`dynamic/`) não são CI vermelha nem ficheiros, a procura de um workflow oculto segue a mesma regra de origem, as execuções em fila durante dias são reconhecidas como uma fila fantasma (7 dias por omissão) e um vermelho de que ninguém trata envelhece aos 30 dias e passa a inativo; os repositórios adormecidos e inativos são um estado próprio, nem verdes nem vermelhos; os forks só entram na higiene, no lint e na pontuação quando têm CI própria nos últimos 90 dias; a proteção do ramo por omissão é avaliada por omissão pelo que está em vigor, a partir de todas as fontes públicas; e as cinco confirmações da página usam um diálogo da página visível em ecrã inteiro.

### 2.0.4 - Um modelo para cada tarefa, menus independentes e uma ajuda que abre o tema certo

A IA do monitor pode usar um modelo para cada tipo de tarefa, uma cadeia de reservas quando o modelo principal falha e um orçamento para cada modelo, tudo desativado até ser escrito nas definições; Alertas, Relatórios e Lições são três entradas independentes do menu, cada uma com o seu painel, distintivo, tema de ajuda e endereço; o separador Histórico mantém um só contador em vez de acumular cópias a cada atualização; o botão «Ajuda deste separador» abre em todos os separadores o tema do separador aberto; e os testes do navegador são ignorados sem erro quando falta a pasta das ferramentas.

### 2.0.3 - Contas grandes, menos falsos vermelhos, lint sem clones e armazenamento mais seguro

Uma vista de frota, listas paginadas, um orçamento de pedidos e uma cobertura honesta da lista de execuções para contas com centenas de repositórios; um vermelho só conta quando o próprio repositório o causou, e as execuções à espera de aprovação, os workflows abandonados, os que só reagem a issues, a fila de merge e os ramos de manutenção têm cada um o seu lugar; o linter de workflows e as verificações de superfície funcionam pela API ou com um clone parcial sem clonar; os modelos do fornecedor de IA são lidos e verificados, e cada ligação da página passa pelo filtro de endereços; os bloqueios e o registo de ações são mais seguros no Windows e o livro de pontuação nunca é sobrescrito; ecrãs de parede para um monitor ou uma televisão, desativados por omissão; os testes do repositório deixam, por agora, de correr em macOS.

### 2.0.2 - Registos mais seguros, texto para IA mais limpo e uma pontuação mais justa

Tudo o que uma IA pode ler passa por um único limpador que conhece mais formas de segredo, o assistente integrado guarda a sua chave e já não segue redirecionamentos nem proxies, o registo de ações é uma cadeia num ficheiro por conta e um leitor não o pode ler, a imagem e os processos das contas já não levam segredos, a pontuação penaliza uma falha nunca corrigida e já não conta uma fonte ilegível como limpa, e uma longa lista de correções do armazenamento, das cópias de segurança, da migração, das vistas de terminal e do lançador.

### 2.0.1 - Empacotamento e uma chave em falta

O zip publicado passa a incluir o ficheiro das predefinições de IA e todos os outros ficheiros de dados do pacote, e a porta de lançamento falha se algum faltar no zip; a página de todas as contas já não mostra uma chave de estado por traduzir, e um teste verifica que cada chave usada pela página existe nos oito catálogos.

### 2.0.0 - Maturidade

A API de leitura e as interfaces públicas ficam congeladas: um ficheiro de contrato com as chaves e os tipos de cada endpoint de leitura e os códigos de erro, uma bateria de testes e uma ferramenta que o verificam contra qualquer monitor em execução, um teste que fixa os campos de um alerta e os métodos de uma sentinela e de um armazenamento, e um guia para cada uso (lite, uma pessoa, serviço, equipa) e para os clientes da API, em oito idiomas. As versões 1.9.6 a 1.9.9 não tinham nada de real a acrescentar após as revisões de fecho e foram saltadas.

### 1.9.5 - Fluxo de eventos em direto

Um fluxo dos eventos em direto do webhook de entrada para clientes e ecrãs de parede que não podem sondar, desligado por predefinição, só de leitura, com um limite de ouvintes e um limite de tempo para cada um.

### 1.9.4 - Predefinições de IA

Uma tabela de doze serviços alojados e seis servidores locais que falam um protocolo que o monitor já conhece, um seletor nas definições de IA que preenche o endereço, o nome da variável da chave e um modelo de exemplo, servidores locais que funcionam sem chave e os endereços dos principais serviços lidos na sua documentação pública.

### 1.9.3 - Relatórios programados e registo de auditoria

Modelos de relatório em HTML e Markdown (PDF opcional) com a pontuação, os alertas principais e as alterações, um agendador e um registo de auditoria só de acrescentar com quem fez o quê e quando, sem qualquer segredo lá dentro. Opcional, na mesma versão: uma vista «versão pronta / bloqueada» com o último commit verde de cada repositório.

### 1.9.2 - Saúde do repositório e da equipa

Uma vista de saúde de cada repositório (CI, issues e pull requests, segurança, preparação para uma versão, atividade) e uma da equipa com classificação, totais e filtros; páginas para ambas com ligações diretas para ecrãs de parede. Opcional, na mesma versão: um painel de benchmarks noturnos face a um orçamento (mediana face a uma referência por classe de máquina) e um painel de listas de materiais de software e atestações de cada versão.

### 1.9.1 - Sentinela de segurança

A terceira sentinela: Dependabot, análise de código, análise de segredos, proteção de ramos, permissões dos workflows e proprietários do código, com regras por tipo de sinal, o mesmo filtro no separador Alertas e uma penalização na pontuação por alertas críticos abertos. Opcional, na mesma versão: higiene de workflows (ações não fixadas a um commit, jobs sem limite de tempo, workflows sem permissões ou sem concorrência, uso perigoso de pull_request_target), sobre o verificador de workflows que o projeto já tem.

### 1.9.0 - Uma pontuação

Recolhedores de métricas por conta e por sentinela (taxa de sucesso, duração, tempo de recuperação, débito), um motor de pontuação com limiares que pode alterar, uma tendência face ao período anterior, instantâneos guardados no armazenamento, um widget de pontuação com minigráfico, alertas quando a pontuação desce e um verbo da linha de comandos que a imprime.

### 1.8.4 - Estabilização

Sem grandes funcionalidades. Isolamento entre contas, a página, o armazenamento, início de sessão e funções, notificações, um GitHub que falha por vezes, o arranque após uma migração interrompida, a recuperação após um corte, um doctor mais amplo, os sítios que escrevem no GitHub, registos sem tokens, uma lista de verificação de segurança do modo de equipa e documentos que coincidem com o comportamento. A série só continua até à 1.8.9 se for preciso.

### 1.8.3 - Notificações por utilizador

Preferências por utilizador (canal, sentinela, nível mínimo), um distribuidor que decide quem avisar segundo as preferências e as funções, canais como plug-ins simples e resumos dos alertas ainda não lidos. Além disso: um relatório do tempo que os jobs esperam na fila por cada runner, e um job ignorado pelos caminhos que vigia é mostrado à parte de um job vermelho.

### 1.8.2 - Imagem Docker oficial e modo de serviço

Uma imagem em várias fases com utilizador sem privilégios, volumes para dados e configuração, variáveis de ambiente documentadas, um exemplo de compose com proxy inverso e TLS opcionais, uma unidade systemd para quem prefira a instalação clássica e uma verificação de saúde profunda que falha se o supervisor ou o ciclo de uma conta estiver bloqueado. Uma credencial que o GitHub revoga ou deixa caducar marca só essa conta como cega, lança um alerta de sistema crítico e pode ser substituída sem reiniciar o supervisor. Cópia de segurança, atualização e primeiro arranque como serviço ficam documentados; a página diz se escuta neste computador, na rede ou atrás de um proxy; a linha de comandos funciona contra um monitor remoto. A edição lite continua local.

## Feito na 1.8.0

Tudo o que se segue foi entregue na série 1.8 e está testado; nada se dá por demonstrado com serviços reais.

- Uma nova organização das pastas (o pacote em `src/`, a página, os exemplos e as línguas em `assets/`), com uma ferramenta de migração que move uma instalação plana antiga sem apagar nada.
- Uma camada de armazenamento atrás de uma única interface, com o suporte de ficheiros que mantém a disposição de `accounts/<id>/`, escritas atómicas e cópias de segurança que qualquer suporte pode restaurar.
- Um suporte SQLite opcional (desativado por predefinição), uma base de dados por conta, migrações com versão, um tempo de espera configurável e ferramentas para mover o estado entre o suporte de ficheiros e o SQLite nos dois sentidos, primeiro com uma simulação.
- O histórico de alterações está traduzido nas oito línguas até à 1.0.0 e um teste mantém-no completo.
- Retenção e rotação do histórico (eventos e análises durante um número de dias, apagar ou arquivar, uma linha de auditoria por passagem, um aviso de tamanho no doctor; o estado das sentinelas e a configuração nunca são tocados).
- Modo de rede: o travão de bloqueio volta a atuar antes de olhar para o token, um proxy inverso declarado nunca é tomado por este computador, as leituras remotas das definições limitam-se ao que um cliente remoto pode alterar e o guia de implementação traz a receita completa.
- O canal para a IA é limpo campo a campo, só passam endereços do GitHub de formas fechadas e o gancho não entrega texto de registos, apenas o repositório, o workflow, o resultado e a ligação.
- As leituras de identidade são sempre do utilizador, uma leitura é julgada por uma lista branca e o ficheiro de token da segunda conta fica dentro da pasta das contas.
- Um teste de fumo da página num navegador real põe a CI a vermelho quando um separador se estraga ou uma função é definida duas vezes.
- Uma barra inferior de uma só linha que diz apenas o que as caixas de cima não dizem, um resumo para as ferramentas de IA e um registo de acordo com o monitor em execução, uma página que avisa quando está dessincronizada do monitor e um som que se desbloqueia com um clique e sobrevive a um recarregamento.
- Uma leitura opcional dos repositórios sossegados por GraphQL (desativada por predefinição) com a sua contabilidade.
- O aviso ativo a uma IA externa (desativado por predefinição, uma primeira confirmação por fornecedor, só os campos redigidos de uma lista fechada, um limite de chamadas e de custo por hora, a chave pelo nome de uma variável, e a IA nunca executa uma ação).
- A aplicação de terminal edita listas e mapas.
- Modo de equipa (desativado por predefinição): utilizadores, funções (admin, maintainer, viewer) e sessões guardados no armazenamento, uma página de início de sessão, um token Bearer para clientes que não são um navegador, erros JSON estáveis e a recuperação de um administrador a partir da consola deste computador. O modo individual continua sem início de sessão e a edição lite nunca o tem.
- Uma página mais viva: ícones animados, luzes de estado cujo movimento segue o estado, respostas a passar o rato, foco e clique; tudo se desliga com movimento reduzido e é leve na edição lite.

## Feito na 1.7.9

### Corrigido

## Feito na 1.7.8

### Adicionado

## Feito na 1.7.7

### Adicionado

## Feito na 1.7.6

A ligação entre o monitor e uma ferramenta de IA: o feed coincide sempre com a página, cada alerta diz porque está vermelho, um fluxo e três ferramentas MCP empurram as novidades, um comando instala o script de ligação, a barra mostra se há uma IA ligada e todos os ficheiros de estado são privados do seu dono.

## Feito na 1.7.5

A linha de comandos lê o token de acesso com o seu próprio nome, o modo de rede é mais seguro por predefinição (o endereço do computador fica escondido da rede, o endereço antigo ?access= pode ser desativado, os destinos de notificação da rede local são recusados, aviso sobre HTTP simples), as horas para as pessoas usam o seu fuso horário, um alerta pode ser silenciado até o elemento mudar, e foram corrigidas as contagens e verificações que davam respostas erradas.

## Feito na 1.7.4

Uma barra ao pé da página com o aviso mais importante (e uma janela com todos), a ligação, a quota, a última leitura, o modo, o endereço e o relógio; um botão de ecrã inteiro; tabelas de Repositórios e Histórico que se ordenam por uma ou várias colunas com as colunas à sua escolha; `bin/monitor_cli.py`, a linha de comandos como cliente do monitor em execução (`status`, `health`, `alerts`, `accounts`, `live`, `doctor`) com `--json` e códigos de saída estáveis, e o seu guia em oito idiomas; os registos de alterações verificados na ordem, o README do pacote sem histórico lá dentro e as imagens redesenhadas.

## Feito na 1.7.3

Uma segunda sentinela para issues e pull requests (Collab, desligada por omissão, só de leitura, com relógio próprio), um separador Alertas com os alertas de todas as sentinelas e filtro por origem e nível, silêncios locais que acabam sozinhos (um alerta, uma regra ou uma sentinela; `alerts.mute_hours`), a etiqueta que faz ignorar um elemento, `GET /api/alerts` e `GET /api/events`, uma lista de verificação da vista em direto, um guia da sentinela Collab em oito idiomas e as imagens redesenhadas.

## Feito na 1.7.2

O cabeçalho com os seus números numa ordem que se lê e numa grelha que segue a largura; os controlos rápidos (só quentes, velocidade, saúde dos ecossistemas) fixos em cima à direita; Definições, Ajuda e Acerca de só no painel lateral; o aviso de versão nova fora do cabeçalho; e os testes que já não deixam ficheiros junto do código.

## Feito na 1.7.1

Uma página com painel lateral (o logótipo, o seletor de contas, as secções em grupos que se recolhem, a ajuda) e dezasseis temas além de auto, claro e escuro, os do Studio do sistema de alarme; e a sentinela de CI atrás de um contrato (`BaseSentinel`, `Alert`, `SentinelRegistry`, `SentinelCI`), para poder juntar as sentinelas seguintes sem que o monitor saiba o que faz cada uma. O que se mostra e se decide não muda.

## Feito na 1.7.0

Várias contas na edição completa, cada uma um monitor próprio sob um supervisor (`accounts/<id>/`, `--accounts`, `--account`, `--migrate-accounts`), a API das contas, um webhook para todas, a página com um seletor e os cartões de todas as contas, as vistas por endereço (`?view=` e `?chrome=0`) e a vista Ao vivo com o estado do recetor de webhook. A edição lite não muda.

## Feito na 1.6.8

O proxy HTTPS da 1.6.7 é verificado contra um proxy real na porta 443 (`tools/manual_check_live.py proxy`, e testes que percorrem um cliente sobre TLS, um proxy inverso e o monitor), as imagens foram refeitas com duas novas do modo rede, e o histórico de alterações está traduzido nos outros sete idiomas até à 1.6.3.

## Feito na 1.6.7

Um proxy HTTPS na porta 443 predefinida já funciona com o modo rede (`listen.proxy_public_host`, vazio por predefinição: o único nome público do proxy é aceite sem porta, só com HTTPS, e só se altera a partir do próprio computador), e o histórico de alterações está traduzido nos outros sete idiomas para a 1.6.7, a 1.6.6 e a 1.6.5.

## Feito na 1.6.6

Correções depois da 1.6.5: o modo rede funciona agora com HTTPS a partir da página (a guarda de origem segue o esquema da sessão), toda a definição que o esquema marca como segura só se altera a partir do próprio computador, o `act` liberta a sua execução depois do Stop e fecha o seu canal, uma barra vermelha nas Definições quando o modo rede escuta em todas as interfaces, a sessão pode abrir-se por POST em vez do endereço, um contador de falhas engolidas no `--doctor` e em Acerca de, o `tools/make_screenshots.py` diz o que faz e as imagens foram tiradas de novo, e o histórico de alterações está traduzido em oito idiomas.

## Feito na 1.6.5

Uma versão de integridade e segurança, sem grandes funcionalidades novas: um commit verde exige o workflow obrigatório do repositório, um fetch falhado pára o despacho, o catálogo não pode indicar uma ferramenta fora da pasta das ferramentas nem alterar `dry_run`/`ref`, e um lote sem verificação de commit registada deixa de ser oferecido para assinatura; o `act` fica dentro do espaço de trabalho e o Stop termina toda a árvore de processos e os contentores da execução; o modo de rede pode servir HTTPS, bloqueia tokens errados e só aceita IPv4; o webhook recusa repetições e inundações; o servidor MCP sobrevive a mensagens mal formadas; `max_per_hour` conta mensagens; as definições são guardadas sob bloqueio; o token guardado chega só ao `gh`; o `--doctor` avisa de combinações perigosas; o teste de instalação limpa é uma etapa própria do controlo de publicação.

## Feito na 1.6.4

Testes de isolamento da edição lite e da demonstração, nenhum pedido de rede quando a verificação de versão está desligada ou a instalação está isolada, um README que começa pela escolha do lançador, `--doctor --json`, uma barra persistente para o modo rede, a Ajuda e os seus documentos em oito idiomas, e as funções opcionais (modo rede, um token guardado pelo monitor, ações no GitHub, `act`, cópia local de artefactos, runners próprios, OpenTelemetry, FinOps por etiquetas de job); veja o registo de alterações e `ADVANCED.md`.

## A seguir

O que a 1.6.4 não alcançou, e porquê:

- **Vários proprietários num processo e numa página**: desde a 1.7.0 cada conta é um monitor próprio e a página mostra-as lado a lado, mas dentro de um monitor um repositório continua a ser identificado só pelo nome, pelo que dois proprietários no mesmo monitor se misturariam. Trazê-los para um só processo exige o proprietário em cada identificador (as leituras, os identificadores de alerta, as listas das definições, as sentinelas e a página); não foi possível demonstrá-lo sem repositórios de dois proprietários reais, por isso as contas da 1.7.0 continuam a ser a forma de os manter separados.
- **O relatório de faturação com um login que o possa ler**: a resposta real de um login sem o âmbito `user` é «não encontrado» e o monitor volta à estimativa (verificado); os valores em si não foram comparados com uma conta de faturação.
- **Os preços dos runners grandes** em `quotas.json` vêm da memória da tabela pública de preços e estão marcados como não verificados; compare-os com a página de faturação do GitHub e edite o ficheiro.
- **`gh copilot`**: as suas opções verificam-se com `gh copilot -- --help`, que precisa da linha de comandos do Copilot; aqui não está instalada, por isso continuam por verificar.
- **Notificações, webhook, Enterprise Server e exemplos de serviço** contra serviços reais: `tools/manual_check_live.py` verifica-os à mão; precisam dos seus canais e máquinas, por isso não foram executados aqui.
- **A aplicação de terminal** edita as definições simples, as listas e os mapas de números e mostra o estado da IA; a explicação de um workflow vermelho concreto fica na página.
- **Só o proprietário o pode demonstrar numa instalação real**: várias contas com a sentinela Collab em repositórios reais, uma GitHub App e uma segunda conta só de leitura com chaves reais, e o proxy HTTPS com um certificado real. Verificam-se à mão (`tools/manual_check_live.py`) e não se dão por feitos.
- **Uma verificação de nova versão que descarregue ou instale**: nunca; o monitor apenas avisa.

## Mais adiante

- **Telemetria de hardware dos runners** através de um agente: hoje só se lê um ponto de acesso opcional do node exporter.
- **Uma quarta fase** (plugins, automatização mais ampla, IA avançada) só depois de várias semanas de 2.0.x estável e de uma decisão explícita.

## Ideias que precisam primeiro de uma decisão

- Uma versão em PDF dos relatórios agendados (hoje HTML e Markdown).
- Uma vista das versões prontas ou bloqueadas, uma por repositório, no separador Equipa.
