<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Funções avançadas (todas desligadas por defeito)

Tudo nesta página está **desligado até o ligar** em *Definições > Avançado* (ou em `actions_monitor.json`), e as chaves que decidem quem pode chegar ao monitor ou o que ele pode fazer no GitHub estão marcadas como opções de segurança. Ligue apenas o que precisa.

## Escutar na rede

Por defeito a página responde apenas em `127.0.0.1`. Com `listen.network` ligado (requer reinício) também escuta em `listen.host`: um endereço privado deste computador, ou `0.0.0.0` para todas as interfaces. Um endereço público é recusado.

- **Cada pedido precisa do token de acesso** (cookie, cabeçalho `X-Monitor-Access` ou `Authorization: Bearer`). O token é o valor da variável de ambiente indicada em `listen.token_env` (16 caracteres ou mais); sem ela, é criado um token aleatório em cada arranque e mostrado uma vez na consola. Abra uma vez o endereço impresso aí: define o cookie e passa para o endereço limpo.
- O token de uso único da página fica forçado, a página mostra uma barra vermelha em todos os separadores enquanto o modo estiver ligado, e as chaves de `listen.*`, `github_token.*`, `act.*` e `github_actions.*` só podem ser alteradas a partir do próprio computador.
- `listen.allowed_hosts` lista os nomes com que a página pode ser aberta (proteção contra DNS rebinding).
- **Riscos.** O tráfego é HTTP em claro: quem puder ler a sua rede pode ler o token e os dados. Use-o apenas numa rede de confiança, ou ponha à frente um proxy inverso com HTTPS (veja `DEPLOYMENT.md`). Nunca o exponha à Internet. A edição lite nunca escuta para além deste computador.

## Um token do GitHub guardado pelo monitor

O predefinido continua a ser o seu próprio início de sessão do `gh`. Com `github_token.enabled` ligado pode colar um token em Definições > Avançado: fica guardado no cofre seguro do sistema (DPAPI do Windows, Porta-chaves do macOS, Secret Service do Linux) e, só quando este falta, num ficheiro com permissões 600 (a página di-lo). Nunca é escrito em `actions_monitor.json`, num registo, no painel Acerca de nem no texto para suporte, e chega ao `gh` apenas pelo ambiente do processo. O botão **Apagar o token** remove-o de todos os sítios.

## Ações no GitHub

Com `github_actions.enabled` ligado, o monitor pode reexecutar uma execução falhada (`rerun_failed`, `rerun_run`, `rerun_job`), cancelar uma execução (`cancel`), fechar uma issue ou um pull request (`close_issue`, `close_pr`) e fundir um (`merge_pr`, com `github_actions.merge_method`). Só se podem usar os nomes em `github_actions.allowed` (por defeito `rerun_failed` e `cancel`). **Cada ação é confirmada à parte**: a página mostra exatamente o que será enviado (método e endpoint) e não envia nada até confirmar esse plano com o token de uso único. O token do GitHub precisa da permissão (`workflow` para execuções, `repo` para issues e pull requests; caso contrário mostra-se a recusa do próprio GitHub). Cada tentativa é escrita em `github_actions_log.jsonl`. O assistente de IA não tem forma de iniciar nenhuma.

## Executar um workflow aqui com act

Com `act.enabled` ligado e entradas `repositório:ficheiro.yml:evento` em `act.allowed` (as três exatas), um botão executa o `act` no clone local depois de confirmar a linha de comandos exata. Não são fornecidos segredos reais (ficheiros de segredos, variáveis, ambiente e entradas vazios, e um ambiente mínimo sem token), a saída aparece à medida que chega, uma execução de cada vez, com o limite de tempo `act.timeout_seconds`, e pode pará-la.

## Cópia local de artefactos

Com `mirror.enabled` ligado e uma `mirror.folder` neste computador, os artefactos das execuções terminadas são copiados para lá (`mirror.max_per_cycle` por ciclo, `mirror.max_mb` para a pasta, `mirror.keep_days` de retenção), uma vez cada, com nomes limpos dentro da pasta.

## Runners próprios

Com `runners.enabled` ligado, Definições > Avançado mostra cada runner como livre, ocupado ou offline. O disco e a carga só aparecem para os runners listados em `runners.metrics` ({nome: endereço de um node exporter neste computador ou um endereço privado}).

## OpenTelemetry

Com `otlp.enabled` ligado e um `otlp.endpoint` (HTTPS, ou HTTP neste computador), as execuções terminadas saem como traces e os valores do cabeçalho como métricas (OTLP/HTTP com JSON), cada execução uma vez. Só se enviam repositório, workflow, ramo, evento, conclusão e duração.

## Organizações e custos

- `organizations.discover` lista as organizações do login em Definições > Básico. Para vigiar uma, arranque um segundo monitor com `github_owner` definido para ela.
- `finops.jobs_per_cycle` acima de 0 lê as etiquetas dos jobs de outras tantas execuções privadas terminadas por ciclo, para que os minutos usem o multiplicador certo (Linux, Windows, macOS e os runners grandes de `quotas.json`) em vez de um sistema presumido. Com o relatório de faturação ligado (`quota.billing_api`) mostram-se também os dólares de Codespaces e Packages, o armazenamento em uso e o preço dos minutos acima dos incluídos.

## Verificar contra os serviços reais

`python tools/manual_check_live.py` (no repositório) lê os âmbitos do seu token, o relatório de faturação, as organizações, os runners e as opções do `gh copilot`, e pede a um monitor em execução que envie uma mensagem de teste pelos seus canais. Nunca pede um segredo.
