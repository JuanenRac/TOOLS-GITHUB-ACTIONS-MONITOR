# Roteiro

Ideias que não couberam na versão atual, sem ordem prometida. São direções, não compromissos; uma issue ou um pull request é a melhor forma de fazer avançar uma.

## Na 1.8.0 (a próxima versão)

Tudo o que se segue está escrito e testado; ou já está no ramo principal, ou aguarda num pull request. Nada se dá como demonstrado em serviços reais (ver «A seguir»).

### Já no ramo principal

- Uma nova organização das pastas (o pacote em `src/`, a página, os exemplos e as línguas em `assets/`), com uma ferramenta de migração que move uma instalação plana antiga sem apagar nada.
- Uma camada de armazenamento atrás de uma única interface, com o suporte de ficheiros que mantém a disposição de `accounts/<id>/`, escritas atómicas e cópias de segurança que qualquer suporte pode restaurar.
- Um suporte SQLite opcional (desativado por predefinição), uma base de dados por conta, migrações com versão, um tempo de espera configurável e ferramentas para mover o estado entre o suporte de ficheiros e o SQLite nos dois sentidos, primeiro com uma simulação.
- O histórico de alterações está traduzido nas oito línguas até à 1.0.0 e um teste mantém-no completo.
- Retenção e rotação do histórico (eventos e análises durante um número de dias, apagar ou arquivar, uma linha de auditoria por passagem, um aviso de tamanho no doctor; o estado das sentinelas e a configuração nunca são tocados).

### Concluído e à espera de integração

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

### Ainda a ser concluído

- Silêncios que recordam quem os definiu (exige o modo de equipa).

## Previsto, por esta ordem

Cada versão leva tudo o que é do seu troço do plano: nada fica pendurado de uma versão anterior e nada se adia para a seguinte. Depois da 1.8.3 e depois da 1.9.3 o produto passa por uma revisão independente e as suas conclusões fecham-se na versão de estabilização seguinte. Não há 1.8.1: utilizadores, funções e sessões chegam com a 1.8.0.

### 1.8.2 - Imagem Docker oficial e modo de serviço

Uma imagem em várias fases com utilizador sem privilégios, volumes para dados e configuração, variáveis de ambiente documentadas, um exemplo de compose com proxy inverso e TLS opcionais, uma unidade systemd para quem prefira a instalação clássica e uma verificação de saúde profunda que falha se o supervisor ou o ciclo de uma conta estiver bloqueado. Uma credencial que o GitHub revoga ou deixa caducar marca só essa conta como cega, lança um alerta de sistema crítico e pode ser substituída sem reiniciar o supervisor. Cópia de segurança, atualização e primeiro arranque como serviço ficam documentados; a página diz se escuta neste computador, na rede ou atrás de um proxy; a linha de comandos funciona contra um monitor remoto. A edição lite continua local. Além disso: um relatório do tempo que os jobs esperam na fila por cada runner.

### 1.8.3 - Notificações por utilizador

Preferências por utilizador (canal, sentinela, nível mínimo), um distribuidor que decide quem avisar segundo as preferências e as funções, canais como plug-ins simples e resumos dos alertas ainda não lidos. Além disso: um job ignorado pelos caminhos que vigia é mostrado à parte de um job vermelho.

### 1.8.4 - Estabilização

Sem grandes funcionalidades. Isolamento entre contas, a página, o armazenamento, início de sessão e funções, notificações, um GitHub que falha por vezes, o arranque após uma migração interrompida, a recuperação após um corte, um doctor mais amplo, os sítios que escrevem no GitHub, registos sem tokens, uma lista de verificação de segurança do modo de equipa e documentos que coincidem com o comportamento. A série só continua até à 1.8.9 se for preciso.

### 1.9.0 - Uma pontuação

Recolhedores de métricas por conta e por sentinela (taxa de sucesso, duração, tempo de recuperação, débito), um motor de pontuação com limiares que pode alterar, uma tendência face ao período anterior, instantâneos guardados no armazenamento, um widget de pontuação com minigráfico, alertas quando a pontuação desce e um verbo da linha de comandos que a imprime.

### 1.9.1 - Sentinela de segurança

A terceira sentinela: Dependabot, análise de código, análise de segredos, proteção de ramos, permissões dos workflows e proprietários do código, com regras por tipo de sinal, o mesmo filtro no separador Alertas e uma penalização na pontuação por alertas críticos abertos. Opcional, na mesma versão: higiene de workflows (ações não fixadas a um commit, jobs sem limite de tempo, workflows sem permissões ou sem concorrência, uso perigoso de pull_request_target), sobre o verificador de workflows que o projeto já tem.

### 1.9.2 - Saúde do repositório e da equipa

Uma vista de saúde de cada repositório (CI, issues e pull requests, segurança, preparação para uma versão, atividade) e uma da equipa com classificação, totais e filtros; páginas para ambas com ligações diretas para ecrãs de parede. Opcional, na mesma versão: um painel de benchmarks noturnos face a um orçamento (mediana face a uma referência por classe de máquina) e um painel de listas de materiais de software e atestações de cada versão.

### 1.9.3 - Relatórios programados e registo de auditoria

Modelos de relatório em HTML e Markdown (PDF opcional) com a pontuação, os alertas principais e as alterações, um agendador e um registo de auditoria só de acrescentar com quem fez o quê e quando, sem qualquer segredo lá dentro. Opcional, na mesma versão: uma vista «versão pronta / bloqueada» com o último commit verde de cada repositório.

### 1.9.4 - Estabilização da terceira fase

O mesmo tipo de fecho da 1.8.4 para a pontuação, a sentinela de segurança, as vistas de saúde, os relatórios e o registo de auditoria; o custo em chamadas à API com três sentinelas ativas; uma pontuação que se mantém coerente quando uma sentinela está desligada.

### 2.0.0 - Maturidade

Uma versão principal que limpa a dívida técnica e congela as interfaces públicas: sentinelas, armazenamento, alertas, o esquema de eventos e a API de leitura, com uma suite de testes de contrato que os clientes podem executar contra qualquer versão. Um guia para cada forma de usar o produto (lite, individual, serviço, equipa) e uma referência de definições, eventos, métricas e API. A partir da 2.0.1 há uma margem para o que só aparece com uso real prolongado.

Os workflows do próprio monitor cumprem o que a sentinela de higiene pedirá aos outros: ações fixadas a um commit, as permissões mínimas e um limite de tempo em cada job.

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

Uma barra ao pé da página com o aviso mais importante (e uma janela com todos), a ligação, a quota, a última leitura, o modo, o endereço e o relógio; um botão de ecrã inteiro; tabelas de Repositórios e Histórico que se ordenam por uma ou várias colunas com as colunas à sua escolha; `monitor_cli.py`, a linha de comandos como cliente do monitor em execução (`status`, `health`, `alerts`, `accounts`, `live`, `doctor`) com `--json` e códigos de saída estáveis, e o seu guia em oito idiomas; os registos de alterações verificados na ordem, o README do pacote sem histórico lá dentro e as imagens redesenhadas.

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

- **Mais adaptadores de notificação**: ntfy, Microsoft Teams e e-mail através de um relé local.
- **Várias contas numa página**: feito na 1.7.0, cada conta no seu próprio monitor sob um supervisor.
- **Telemetria de hardware dos runners** através de um agente: hoje só se lê um endpoint opcional de node exporter.

## Ideias que precisam primeiro de uma decisão

- Ler na página os registos de um passo falhado, com a mesma limpeza que o assistente de IA aplica.
