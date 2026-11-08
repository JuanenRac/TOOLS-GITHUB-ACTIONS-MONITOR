# Roteiro

Ideias que não couberam na versão atual, sem ordem prometida. São direções, não compromissos; uma issue ou um pull request é a melhor forma de fazer avançar uma.

## Feito na 1.6.5

Uma versão de integridade e segurança, sem grandes funcionalidades novas: um commit verde exige o workflow obrigatório do repositório, um fetch falhado pára o despacho, o catálogo não pode indicar uma ferramenta fora da pasta das ferramentas nem alterar `dry_run`/`ref`, e um lote sem verificação de commit registada deixa de ser oferecido para assinatura; o `act` fica dentro do espaço de trabalho e o Stop termina toda a árvore de processos e os contentores da execução; o modo de rede pode servir HTTPS, bloqueia tokens errados e só aceita IPv4; o webhook recusa repetições e inundações; o servidor MCP sobrevive a mensagens mal formadas; `max_per_hour` conta mensagens; as definições são guardadas sob bloqueio; o token guardado chega só ao `gh`; o `--doctor` avisa de combinações perigosas; o teste de instalação limpa é uma etapa própria do controlo de publicação.

## Feito na 1.6.4

Testes de isolamento da edição lite e da demonstração, nenhum pedido de rede quando a verificação de versão está desligada ou a instalação está isolada, um README que começa pela escolha do lançador, `--doctor --json`, uma barra persistente para o modo rede, a Ajuda e os seus documentos em oito idiomas, e as funções opcionais (modo rede, um token guardado pelo monitor, ações no GitHub, `act`, cópia local de artefactos, runners próprios, OpenTelemetry, FinOps por etiquetas de job); veja o registo de alterações e `ADVANCED.md`.

## A seguir

O que a 1.6.4 não alcançou, e porquê:

- **Decidido, não feito na 1.6.5** (a versão está limitada a integridade e segurança): o aviso ativo a uma IA externa (desligado por omissão, uma primeira confirmação por fornecedor, só os campos já filtrados da lista fechada, um limite de chamadas e de custo por hora, a chave pelo nome de uma variável de ambiente, e a IA nunca executa uma ação) com a sua variante de comando de saída (lista fechada, sem shell); capturas novas (`tools/make_screenshots.py --web` não produziu saída na máquina da publicação, por isso fazem-se à mão: arranque `--demo`, abra a página e guarde uma captura por separador); e os repositórios de vários proprietários numa só página.
- **Vários proprietários numa página**: o monitor identifica um repositório apenas pelo nome (execuções, sentinela, cache, exportações), pelo que dois proprietários com um repositório do mesmo nome se misturariam. As organizações são listadas e cada uma é vigiada pelo seu próprio monitor (`github_owner`). Fazê-lo numa página exige o proprietário em cada identificador.
- **O relatório de faturação com um login que o possa ler**: a resposta real de um login sem o âmbito `user` é «não encontrado» e o monitor volta à estimativa (verificado); os valores em si não foram comparados com uma conta de faturação.
- **Os preços dos runners grandes** em `quotas.json` vêm da memória da tabela pública de preços e estão marcados como não verificados; compare-os com a página de faturação do GitHub e edite o ficheiro.
- **`gh copilot`**: as suas opções verificam-se com `gh copilot -- --help`, que precisa da linha de comandos do Copilot; aqui não está instalada, por isso continuam por verificar.
- **Notificações, webhook, Enterprise Server e exemplos de serviço** contra serviços reais: `tools/manual_check_live.py` verifica-os à mão; precisam dos seus canais e máquinas, por isso não foram executados aqui.
- **A aplicação de terminal** edita as definições simples e mostra o estado da IA; a explicação de um workflow vermelho concreto e a edição de listas e mapas ficam na página.
- **Uma verificação de nova versão que descarregue ou instale**: nunca; o monitor apenas avisa.

## Mais adiante

- **Mais adaptadores de notificação**: ntfy, Microsoft Teams e e-mail através de um relé local.
- **Várias contas numa página**: hoje cada conta corre no seu próprio monitor.
- **Telemetria de hardware dos runners** através de um agente: hoje só se lê um endpoint opcional de node exporter.

## Ideias que precisam primeiro de uma decisão

- Um ecrã de início de sessão para a página, para que o modo rede não exija escrever uma vez o token de acesso. Hoje a resposta é o token de acesso e, para a Internet, um proxy inverso com autenticação (veja `monitor/docs/DEPLOYMENT.md`).
- Ler na página os registos de um passo falhado, com a mesma limpeza que o assistente de IA aplica.
