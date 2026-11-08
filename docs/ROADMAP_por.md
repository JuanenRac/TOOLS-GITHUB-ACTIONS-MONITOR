# Roteiro

Ideias que não couberam na versão atual, sem ordem prometida. São direções, não compromissos; uma issue ou um pull request é a melhor forma de fazer avançar uma.

## Feito na 1.6.4

Testes de isolamento da edição lite e da demonstração, nenhum pedido de rede quando a verificação de versão está desligada ou a instalação está isolada, um README que começa pela escolha do lançador, `--doctor --json`, uma barra persistente para o modo rede, a Ajuda e os seus documentos em oito idiomas, e as funções opcionais (modo rede, um token guardado pelo monitor, ações no GitHub, `act`, cópia local de artefactos, runners próprios, OpenTelemetry, FinOps por etiquetas de job); veja o registo de alterações e `ADVANCED.md`.

## A seguir

O que a 1.6.4 não alcançou, e porquê:

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
