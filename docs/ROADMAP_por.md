# Roteiro

Ideias que não couberam na versão atual, sem ordem prometida. São direções, não compromissos; uma issue ou um pull request é a melhor forma de fazer avançar uma.

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

- **Decidido, não feito na 1.6.6**: o aviso ativo a uma IA externa (desligado por omissão, uma primeira confirmação por fornecedor, só os campos já filtrados da lista fechada, um limite de chamadas e de custo por hora, a chave pelo nome de uma variável de ambiente, e a IA nunca executa uma ação) com a sua variante de comando de saída (lista fechada, sem shell); e os repositórios de vários proprietários numa página (o monitor identifica um repositório só pelo nome, por isso precisa do proprietário em cada identificador; é a base de várias contas). Cada um é uma funcionalidade própria com o seu desenho e os seus testes, por isso a 1.6.6 fechou primeiro as correções.
- **As entradas antigas do histórico de alterações nos outros sete idiomas**: a Ajuda mostra o histórico em cada idioma, e da 1.6.8 à 1.6.3 estão traduzidas; a 1.6.2 e as anteriores mantêm o texto em inglês sob um aviso traduzido e serão traduzidas versão a versão, da mais recente para a mais antiga.
- **Vários proprietários num processo e numa página**: desde a 1.7.0 cada conta é um monitor próprio e a página mostra-as lado a lado, mas dentro de um monitor um repositório identifica-se ainda só pelo nome, pelo que dois proprietários no mesmo monitor se misturariam. As contas da 1.7.0 são a forma de os manter separados; trazê-las para um só processo, com o proprietário em cada identificador, é o que falta.
- **O relatório de faturação com um login que o possa ler**: a resposta real de um login sem o âmbito `user` é «não encontrado» e o monitor volta à estimativa (verificado); os valores em si não foram comparados com uma conta de faturação.
- **Os preços dos runners grandes** em `quotas.json` vêm da memória da tabela pública de preços e estão marcados como não verificados; compare-os com a página de faturação do GitHub e edite o ficheiro.
- **`gh copilot`**: as suas opções verificam-se com `gh copilot -- --help`, que precisa da linha de comandos do Copilot; aqui não está instalada, por isso continuam por verificar.
- **Notificações, webhook, Enterprise Server e exemplos de serviço** contra serviços reais: `tools/manual_check_live.py` verifica-os à mão; precisam dos seus canais e máquinas, por isso não foram executados aqui.
- **A aplicação de terminal** edita as definições simples e mostra o estado da IA; a explicação de um workflow vermelho concreto e a edição de listas e mapas ficam na página.
- **Uma verificação de nova versão que descarregue ou instale**: nunca; o monitor apenas avisa.

## Mais adiante

- **Mais adaptadores de notificação**: ntfy, Microsoft Teams e e-mail através de um relé local.
- **Várias contas numa página**: feito na 1.7.0, cada conta no seu próprio monitor sob um supervisor.
- **Telemetria de hardware dos runners** através de um agente: hoje só se lê um endpoint opcional de node exporter.

## Ideias que precisam primeiro de uma decisão

- Um ecrã de início de sessão para a página, para que o modo rede não exija escrever uma vez o token de acesso. Hoje a resposta é o token de acesso e, para a Internet, um proxy inverso com autenticação (veja `monitor/docs/DEPLOYMENT.md`).
- Ler na página os registos de um passo falhado, com a mesma limpeza que o assistente de IA aplica.
