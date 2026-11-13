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
- **HTTPS.** Com o seu próprio certificado e chave (`listen.tls_cert_file`, `listen.tls_key_file`) o monitor serve HTTPS por si; atrás de um proxy que o faz por si, defina `listen.secure_cookie`. Nos dois casos o navegador envia `Origin: https://anfitrião:porta` a cada alteração, e a guarda aceita exatamente o esquema da sessão (o outro esquema, outro anfitrião, outra porta ou uma origem mal formada são recusados). O endereço usado pelo navegador tem de levar a porta do monitor, exceto atrás de um proxy HTTPS na porta 443 predefinida que reencaminha `Host` e `Origin` sem porta: indique o seu nome público em `listen.proxy_public_host` (apenas um nome de anfitrião, vazio por predefinição). Só conta com HTTPS, só esse nome é aceite sem porta e só se altera a partir do próprio computador.
- **Abrir a sessão por POST.** Em vez do endereço com `?access=` pode enviar `POST /api/access` com o JSON `{"token": "..."}`: o token fica fora da barra de endereços, do histórico e dos registos, e o cookie volta na resposta. O endereço com `?access=` é obsoleto: continua a funcionar por defeito (nada do que já está configurado deixa de funcionar) e só num `GET`, mas o token fica no histórico, nos registos e no `Referer`, e o monitor responde com um cabeçalho `Deprecation`. Desative `listen.query_access` para o recusar e abrir a sessão só com `POST /api/access` ou o cabeçalho `X-Monitor-Access`. Uma barra vermelha no topo das Definições avisa quando `listen.host` é `0.0.0.0`. Toda a definição que o esquema marca como segura (não só `listen.*`, `github_token.*`, `act.*` e `github_actions.*`: também o webhook, as ações da IA, as notificações, o OpenTelemetry, o espelho, os runners e as saídas) só se altera a partir do próprio computador.
- **Primeiros passos ao escutar na rede.** Desligue primeiro `listen.query_access` (assim o token nunca viaja num endereço, num histórico ou num registo; abra a sessão com `POST /api/access` ou com o cabeçalho) e ponha à frente HTTPS (um certificado em `listen.tls_cert_file` ou um proxy HTTPS) ou uma VPN. A consola repete isto ao arrancar o modo de rede enquanto o endereço antigo ainda for aceite.

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

## Notas de segurança (leia antes de ligar o que quer que seja)

- **Modo de rede**: use-o apenas numa rede de confiança. O token de acesso não substitui a cifragem; em HTTP simples o token e os dados viajam em claro. Ponha à frente um proxy HTTPS (e ative `listen.secure_cookie`) ou dê ao monitor o seu próprio certificado e chave (`listen.tls_cert_file`, `listen.tls_key_file`): então serve HTTPS por si (TLS 1.2 ou superior) e não arranca se não puder usar os ficheiros. Prefira UM endereço privado deste computador a todas as interfaces. Só são aceites endereços IPv4. Depois da primeira visita a barra de endereços fica limpa do token e o cookie é HttpOnly, SameSite=Strict (e Secure com HTTPS). Um endereço que envie `listen.max_failed_attempts` tokens errados num minuto é recusado durante cinco minutos. `/metrics` e `dashboard.json` listam os seus repositórios: no modo de rede também exigem o token.
- **Ações no GitHub**: **desligadas por omissão, uma confirmação por ação, lista fechada** (reexecutar uma execução ou job, cancelar, fechar uma issue ou pull request, integrar um pull request se o incluir). Apagar ramos ou repositórios, segredos e definições **não** existem. A IA pode propor uma lista menor (`rerun_failed`, `rerun_run`, `close_issue`) e nunca integra.
- **act**: desligado por omissão, cada execução confirmada, lista fechada `repositório:ficheiro:evento`, sem segredos reais. O clone tem de ser uma pasta real dentro do espaço de trabalho: uma pasta que seja ligação para outro sítio é recusada, salvo se `act.allow_symlinks` estiver ligado. O limite de tempo e o Stop terminam toda a árvore de processos que a execução lançou e removem os contentores `act-` que criou.
- **O seu próprio token** fica no armazenamento do sistema, se existir; o ficheiro simples (permissões 600) é o armazenamento mais fraco. Vai só para o `gh`, nunca para o `act` nem para os seus comandos. O `--doctor` mostra o armazenamento, nunca o token.
- **Combinações a evitar** (o `--doctor` nomeia-as): modo de rede em todas as interfaces; ações da IA que executam com o modo de rede ligado; `act` com o modo de rede ligado; o token num ficheiro simples.
- O servidor MCP fala apenas por entrada e saída padrão; nunca o ponha atrás de uma porta de rede.

`listen.trusted_proxy` (desativado por defeito): só se um proxy inverso SEU no mesmo computador for a única entrada. As tentativas falhadas são então contadas contra o último endereço de `X-Forwarded-For` (o que o seu proxy acrescenta) e não contra o proxy; um pedido que chega por um proxy continua a nunca ser tratado como este computador. Se mais alguém puder chegar diretamente ao monitor, deixe-o desligado.

## O ciclo de atualização: batimento e vigilante

`/api/data` devolve também `loop`: a fase do ciclo de atualização (`collect`, `maintain`, `publish`, `log`, `extras`, `idle`), há quanto tempo o ciclo está a correr, o último ciclo bom, o último erro e a fase em que ocorreu, os reinícios e qualquer problema ao escrever o registo ou o resumo para a IA. A barra inferior da página mostra-o a vermelho quando um ciclo demora demasiado e como aviso quando não se consegue escrever um ficheiro. Um vigilante reinicia numa thread nova o ciclo que exceda `watchdog_minutes` (por defeito 10, 0 desliga-o), depois de escrever em `actions_monitor_log.txt` o rasto de todas as threads.
