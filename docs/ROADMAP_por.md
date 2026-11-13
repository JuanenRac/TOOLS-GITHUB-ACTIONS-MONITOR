# Roteiro

Ideias que não couberam na versão atual, sem ordem prometida. São direções, não compromissos; uma issue ou um pull request é a melhor forma de fazer avançar uma.

## Feito na 1.8.0

Uma nova organização das pastas (o pacote em `src/`, a página, os exemplos e as línguas em `assets/`); a barra inferior é uma só linha e diz apenas o que as caixas de cima não dizem; o resumo para as ferramentas de IA e o registo estão de acordo com um monitor em execução; uma leitura opcional dos repositórios sossegados por GraphQL (desativada por predefinição) com a sua contabilidade; o aviso ativo a uma IA externa (desativado por predefinição, uma primeira confirmação por fornecedor, só os campos redigidos de uma lista fechada, um limite de chamadas e de custo por hora, a chave pelo nome de uma variável, e a IA nunca executa uma ação); a aplicação de terminal edita listas e mapas; e o histórico de alterações está traduzido nas oito línguas até à 1.0.0.

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

- Um ecrã de início de sessão para a página, para que o modo rede não exija escrever uma vez o token de acesso. Hoje a resposta é o token de acesso e, para a Internet, um proxy inverso com autenticação (veja `monitor/docs/DEPLOYMENT.md`).
- Ler na página os registos de um passo falhado, com a mesma limpeza que o assistente de IA aplica.
