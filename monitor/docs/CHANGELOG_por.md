<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Registo de alterações

Versão da própria ferramenta (monitor + sentinela + ferramentas em lote), com o seu próprio semver. A fonte é o CHANGELOG.md em inglês; este ficheiro tem as mesmas versões e secções.

## [Unreleased]

### Alterado

- **`/api/health` diz mais e `?deep=1` pergunta mais**: além de `ok`, `version`, `loaded` e `offline`, a resposta traz o estado do ciclo de atualização (`cycle`), do acesso ao GitHub (`credential`) da conta e onde o monitor escuta (`listening`); o supervisor responde com as mesmas palavras. `/api/health?deep=1` é a verificação profunda: 503 quando o ciclo de atualização de uma conta está preso ou desapareceu e, no supervisor, também quando o seu ciclo parou, quando o ciclo de qualquer conta está preso ou quando nenhuma conta responde depois do arranque. Sem `deep`, nada falha que antes não falhasse.

- Os tipos de notificação `credential_blind` e `credential_back` são novos; `credential_blind` está na lista por defeito e na configuração de exemplo. O separador de alertas, `/api/alerts` e a linha de comandos conhecem o nível `critical` e a sentinela `system`, e um alerta crítico é listado em primeiro lugar.

- `--doctor` distingue também o acesso de cada conta pelo seu próprio ficheiro de credenciais, de modo que duas contas que receberam cada uma uma substituição não são apontadas como se partilhassem um token.

- Os prazos da porta de publicação são 3600 segundos por defeito (eram 900 e 1800, demasiado curtos para um computador carregado). `MONITOR_RELEASE_TEST_TIMEOUT` e `MONITOR_RELEASE_CLEAN_TIMEOUT` alteram-nos (de 60 a 86400 segundos), e o valor por defeito é lido quando a porta é executada, não quando o módulo é carregado.

### Adicionado

- **Imagem Docker oficial e modo de serviço**: `deploy/Dockerfile` é multietapa (a CLI do GitHub a partir do seu repositório apt assinado, o código compilado sem os testes e uma imagem final só com Python, `gh`, os certificados das CA e o código, só de leitura e pertencente ao root). Corre como o utilizador 10001, nunca como root, com dois volumes (`/config` e `/data`), `tini` como init e uma verificação de saúde que é a profunda. `python -m github_actions_monitor.service` prepara, a partir de variáveis de ambiente documentadas, tudo o que uma pessoa faz à mão antes do primeiro arranque: a configuração, a primeira conta (ou várias com `MONITOR_ACCOUNTS`), as chaves de `listen` e `auth` e um token de acesso que é criado uma vez, guardado com modo 600 e nunca impresso. `MONITOR_CONFIG` coloca o ficheiro de configuração fora do código.

- **Compose com proxy inverso, e systemd**: `deploy/compose.yaml` (código só de leitura, sem capacidades, o acesso como segredo do Docker) com um Caddy opcional à frente (`deploy/Caddyfile`; TLS automático para um nome público, a sua própria autoridade para um privado, ou nenhum), `deploy/.env.example` e, para uma instalação clássica, `deploy/github-actions-monitor.service` com o seu ficheiro env (reforçado, reinicia em caso de falha, verifica a saúde profunda após o arranque, volta a ler os ficheiros de credenciais com `systemctl reload`). O guia `DEPLOYMENT.md` nas oito línguas lista cada variável de ambiente, o primeiro arranque como serviço, a cópia de segurança, a atualização e a verificação da atestação da imagem.

- **Imagem para `linux/amd64` e `linux/arm64` no ghcr.io**: o fluxo `release-image.yml` constrói-a e publica-a quando uma versão é publicada (ou à mão), com as permissões mínimas de cada tarefa, cada ação fixada por commit, um limite de tempo em cada tarefa, etiquetas `X.Y.Z`, `X.Y` e `latest` e uma atestação da proveniência. Publicar é um passo à parte que só uma versão dá: o mesmo fluxo constrói sem publicar quando é lançado à mão com `push` desligado, e a CI constrói a imagem em cada alteração.

- **Uma verificação de saúde profunda**: `/api/health?deep=1` (ver acima), `python -m github_actions_monitor.cli.healthcheck` para um contentor ou um gestor de serviços (códigos de saída 0, 1, 2 e 3) e `monitor_cli.py health --deep` a partir de qualquer computador. Uma conta cujo acesso ao GitHub não serve é nomeada, mas não é uma falha: reiniciar não repara um acesso perdido.

- **Um acesso que o GitHub revoga ou deixa caducar deixa cega apenas essa conta**: após duas recusas seguidas que dizem que o próprio acesso não serve (401, `Bad credentials`, token caducado ou revogado, conta suspensa, nenhum acesso), a conta fica cega; as outras continuam. A página, `/api/accounts` (`state: blind`), a verificação de saúde e a linha de comandos dizem-no, abre-se uma vez um alerta crítico de sistema (`system.credential_blind`), os canais são avisados uma vez (`credential_blind`, e `credential_back` quando volta a funcionar) e a conta continua a tentar. A recusa de uma permissão (um 403 para um repositório) não torna uma conta cega. Um serviço que arranca com um acesso que já não serve fica ativo e cego em vez de desistir.

- **O acesso pode ser substituído sem reiniciar nada**: o endpoint `/api/accounts/<id>/credential` (uma sessão `admin` no modo de equipa; o computador do monitor, caso contrário), `monitor_cli.py credential replace --account ID --new-token-file FICHEIRO` (ou `-` para a entrada padrão; um token nunca é lido de uma opção) e SIGHUP onde o sistema o tenha (cada conta volta a ler os seus ficheiros de credenciais). O novo token é verificado no GitHub ANTES de ser guardado, pelo que um token que o GitHub recusa não altera nada; um bom é guardado apenas na pasta dessa conta (modo 600) e usado de imediato. `GH_TOKEN_FILE` indica um ficheiro para o acesso de todas as contas, lido no arranque e com SIGHUP. O token nunca aparece numa resposta, num registo, num alerta nem na auditoria.

- **O supervisor de várias contas escuta no modo de rede** como o monitor de uma conta: o token de acesso em cada pedido (cookie, cabeçalho ou `/api/access`), bloqueio após tokens errados, a verificação de `Host`, TLS opcional com o seu certificado, a segunda porta de quem está no computador (`listen.local_port`), e as chaves que decidem a exposição, o acesso ao GitHub e as ações no GitHub apenas a partir do computador do monitor (a conta trata um pedido vindo da rede como remoto).

- **A página e as ferramentas dizem onde o monitor escuta**: este computador, a rede ou atrás de um proxy (`listen.proxy_public_host`, `listen.secure_cookie`, `listen.trusted_proxy`), na barra inferior da página, em `/api/accounts`, `/api/health` e nas primeiras linhas de `monitor_cli.py status` e `monitor_cli.py accounts`.

- **A linha de comandos funciona contra um monitor de outro computador**: `--url` ou `MONITOR_URL`, `--ca-file` ou `MONITOR_CA_FILE` para confiar na autoridade de um certificado HTTPS próprio e, no modo de equipa, `--user` com `--password-file` (ou `MONITOR_USER`, `MONITOR_PASSWORD_FILE`) para iniciar sessão com uma sessão Bearer (`auth.allow_bearer`). `status` e `accounts` terminam com o código de saída 3 para uma conta cega.

- **Testes**: um teste do contentor na CI que constrói a imagem, a arranca só de leitura e sem root, revoga o acesso de uma de duas contas e verifica que só essa conta fica cega, que se abre o alerta crítico, que a verificação de saúde profunda continua verde, que um token recusado não altera nada, que um bom devolve a conta sem reiniciar e que o SIGHUP faz o mesmo; e um teste de regressão para cada comportamento de um acesso revogado (a contagem, as outras contas, o alerta, o aviso, a substituição, o ficheiro, o SIGHUP, os papéis, a auditoria e o token que nunca aparece).

### Corrigido

- O teste de uma conta que morre de imediato já não depende da velocidade do computador: a espera antes de voltar a arrancar uma conta é verificada com um relógio que o próprio teste dá, e um segundo teste verifica o calendário das esperas sem ler a hora real (o antigo falhava sob carga na porta de uma versão).

## [1.8.1]

### Corrigido

- A caixa «a carregar repositórios» ficava na página depois de ler o último repositório: a imagem terminada chega agora à página assim que a leitura acaba, sem esperar pela manutenção seguinte (o resumo para as ferramentas de IA, o centro de alertas), e uma lista longa de painéis do Sentinel já não pode fazer esse resumo repetir-se sem fim (esse ciclo mantinha no ecrã a última imagem parcial, 131 / 131).

- Recarregar a página (F5) já não demora minutos a obter os dados: o ciclo sem fim do resumo gastava todo o processador do monitor e a página desistia com um aborto; além disso, a resposta do ponto de acesso aos dados era escrita na ligação com o bloqueio global retido, pelo que uma ligação parada (um separador fechado) bloqueava todas as outras páginas e o ciclo de atualização. O bloqueio só é agora retido para tirar a imagem. Um teste de navegador verifica que a caixa aparece durante o carregamento e desaparece com o último repositório, e testes do servidor verificam que o resumo termina, que a imagem terminada é publicada antes da manutenção e que uma ligação parada não bloqueia um recarregamento.

## [1.8.0]

### Alterado

- **Nova estrutura de pastas, mesmo comportamento**: o código é agora um pacote importável em `src/github_actions_monitor/` (`app`, `accounts`, `sentinels`, `security`, `data_pipeline`, `integrations`, `cli`, `ui`, `i18n`, `util`); a página, os exemplos neutros com `quotas.json` e os oito catálogos de idioma estão em `assets/` (`static`, `examples`, `locales`); `make_release.py` está em `tools/`. Os lançadores ficam na pasta do produto e executam `python -m github_actions_monitor` (completo) ou `python -m github_actions_monitor.lite` (lite): mesmo endereço, mesma porta. Os dados de quem o utiliza (`actions_monitor.json`, caches, registos, `accounts/`, catálogos) continuam junto dos lançadores, nunca dentro de `src/`.

- Os comandos dos guias (`python read_report.py`, `python actions_monitor.py --doctor`, `python monitor_cli.py status` ...) continuam a funcionar: um pequeno ficheiro de entrada com o mesmo nome fica na pasta do produto, pelo que os hooks e os servidores MCP já registados por caminho também continuam a funcionar. O zip da versão mantém o nome da pasta e passa a incluir `src/`, `assets/` e `tools/`.

- **O roteiro diz o que a 1.8.0 leva e o que cada versão seguinte trará**: o que já está no ramo principal, o que está concluído à espera de integração, o que ainda se conclui e o plano da 1.8.2 à 2.0.0 pela ordem em que será feito, nas oito línguas.

### Adicionado

- `tools/migrate_layout.py` para uma pasta que era uma instalação plana: simulação por defeito; `--apply` copia a sua configuração para `layout_backup_<marca>/config/` e MOVE (nunca apaga nem substitui) os módulos, a página, os exemplos e `locales/` antigos para `layout_backup_<marca>/old_code/`. `--doctor` avisa enquanto existirem tais restos. `MIGRATING.md` descreve-o nos oito idiomas.

- **Camada de armazenamento** (`src/github_actions_monitor/storage/`): uma interface `Storage` (configuração, estado das sentinelas, feed de eventos, análises, pequenos documentos e registos globais de utilizadores, das suas contas e sessões) que cumpre em qualquer armazenamento a regra "uma escrita é atómica, um elemento danificado lê-se como vazio". O `FileStorage` é o primeiro e mantém a disposição de `accounts/<id>/` exatamente como antes (e a instalação plana junto dos lançadores): os mesmos ficheiros com os mesmos nomes, escritos através de um ficheiro temporário gravado no disco e renomeado. `create_storage` é o único sítio que escolhe o armazenamento; a edição lite recebe sempre ficheiros.

- Cópias de segurança de um armazenamento que qualquer armazenamento consegue restaurar: um `.zip` com um despejo e um manifesto (contas, tamanho, SHA-256); o restauro verifica primeiro a cópia e recusa escrever sobre um armazenamento que já tem contas, a menos que seja forçado.

- **Armazenamento SQLite** (opcional, desligado por omissão): os mesmos dados numa base de dados, um ficheiro por conta (`accounts/<id>/storage.sqlite3`), escrito apenas pelo processo dessa conta. Diário WAL e tempo de espera, cada escrita é uma transação curta, migrações de esquema com versão executadas na mesma transação que a subida da versão (uma interrompida deixa a base como estava; uma base de uma versão mais recente é recusada), um índice dos eventos de uma conta por hora, e um processo terminado a meio de uma escrita recupera no arranque seguinte. Passam para a base de dados: o feed de eventos, o que o feed anunciou, as análises, o estado das sentinelas, os silenciamentos e o aviso de atualização; a configuração continua a ser um ficheiro JSON, as caches e os registos continuam a ser ficheiros. A edição lite não tem esta opção.

- Uma base de dados partilhada por toda a instalação (várias contas e processos num ficheiro) fica preparada e testada: WAL, tempo de espera, dois processos a fazer o ciclo ao mesmo tempo e uma página que responde por HTTP sem esperar por quem escreve.

- `tools/migrate_storage.py` move o estado entre ficheiros e SQLite nos dois sentidos: simulação por omissão; `--apply` copia cada conta num só passo e depois compara cada elemento e cada evento; os seus ficheiros nunca são alterados nem apagados; uma execução interrompida deixa cada conta inteira ou como estava e o mesmo comando retoma. `tools/backup_storage.py` faz, verifica e restaura as cópias de qualquer um deles.

- **Retenção e rotação** (completa): `retention.events_days` (90) e `retention.analytics_days` (180) definem durante quanto tempo se guardam os eventos e os dias do histórico de análises; `retention.mode` é `archive` (predefinido; os eventos antigos são primeiro escritos num `.gz` em `events/archive/` da conta e depois retirados do feed) ou `delete`; `retention.enabled` é o interruptor e `retention.interval_hours` (24) diz de quanto em quanto tempo corre uma passagem curta no fim de uma atualização. Cada passagem deixa uma linha de auditoria (quando, eventos removidos e mantidos, ficheiro de arquivo, dias de análises, erro). A limpeza nunca toca na configuração, no estado das sentinelas, nos silenciamentos nem num evento sem hora. `retention.events_max_kb` (512, como antes) é o teto de tamanho do ficheiro do feed. As definições estão no separador Pastas e ficheiros; a edição lite não as tem.

- O `--doctor` tem duas verificações novas: o armazenamento (a base SQLite existe, passa a sua verificação de integridade e tem um esquema que esta versão entende; só leitura) e a retenção (o tamanho dos eventos de cada conta face a `retention.warn_events_mb` e um aviso para um monitor que corre como serviço sem bloco de retenção).

- **Modo equipa: utilizadores, funções e sessões** (`src/github_actions_monitor/security/auth.py`, `auth_http.py`, `auth_cli.py`; desativado por predefinição com `auth.enabled`, pelo que uma pessoa sozinha não nota nada): quando existe o primeiro administrador (criado em `/login` ou na consola, só a partir do computador que executa o monitor e uma única vez) cada pedido exige uma sessão. Funções `viewer` (lê), `maintainer` (também silencia, reconhece e altera o modo de trabalho) e `admin` (também definições, utilizadores e tudo o que possa chegar ao GitHub); uma rota que ninguém listou fica fechada a todos exceto a um admin. Cada utilizador tem as contas que pode ver: outra conta pedida com `?account=`, `X-Account-Id` ou uma exportação responde 403. As palavras-passe são guardadas como hash scrypt com sal; a sessão é um cookie HttpOnly, SameSite=Strict (Secure com HTTPS) com token CSRF em cada POST, ou um token Bearer para scripts e aplicações (`auth.allow_bearer`); um utilizador fica bloqueado após `auth.max_failed_logins` palavras-passe erradas, cada endereço tem limite de pedidos, uma nova palavra-passe, função ou estado termina as sessões do utilizador e fica sempre um administrador ativo. Os endpoints `/api/auth/login`, `/api/auth/users` e `/api/auth/audit` respondem os erros como `{"error", "code"}`; `auth_audit.jsonl` regista inícios de sessão, bloqueios, pedidos recusados e alterações de utilizadores sem qualquer segredo. A edição lite nunca tem início de sessão, o token de uso único da página continua a aplicar-se e `python -m github_actions_monitor.security.auth_cli` recupera uma palavra-passe de administrador perdida. Sete definições (`auth.*`) com a sua ajuda nos oito idiomas e uma secção de `docs/ADVANCED.md` nos oito idiomas; `tests/test_auth.py` cobre as regras, as funções de cada tipo de rota, o âmbito entre contas, o cookie, o CSRF, o Bearer, os bloqueios e a auditoria no servidor real.

- O supervisor de contas filtra por utilizador: `GET /api/accounts`, `/api/accounts/<id>/status`, a página de uma conta e todo o pedido com `?account=` ou `X-Account-Id` mostram e alcançam apenas as contas atribuídas ao utilizador (um admin vê todas), e o monitor de uma conta sabe quem age. Um silêncio do separador Alertas guarda agora quem o fez: `muted_by` em `GET /api/alerts` e no histórico de silêncios.

- **A página do modo equipa mostra quem iniciou sessão**: uma caixa no cabeçalho com o nome e a função (um texto, não só uma cor) que abre um menu para alterar a palavra-passe, ver e gerir os utilizadores e a auditoria (só administradores) e terminar sessão; da primeira vez, com o modo ativo e sem utilizadores, aponta para `/login`. Cada alteração enviada pela página leva o token CSRF, uma sessão terminada leva a pessoa a `/login` e um token errado é renovado e tentado uma vez. No modo individual e na edição lite a página não desenha nem pede nada de novo; `tests/test_auth_page.py` executa o invólucro de `fetch` em Node contra uma rede falsa.

### Segurança

- **O bloqueio por tokens errados volta a travar (modo de rede)**: um endereço que não é este computador e está bloqueado é recusado ANTES de o seu token ser avaliado, seja qual for a forma de o apresentar (cabeçalho, cookie, `?access=` e `POST /api/access`); até agora um endereço bloqueado podia continuar a adivinhar e o token certo entrava na mesma. Quem está neste computador nunca fica bloqueado fora do seu próprio monitor.

- **Um proxy inverso declarado faz com que o loopback deixe de significar «este computador»** (`listen.proxy_public_host`, `listen.secure_cookie` ou `listen.trusted_proxy`): um proxy que se esqueça dos cabeçalhos de reencaminhamento já não pode transformar qualquer cliente da internet no dono. Quem está no computador do monitor usa a nova segunda porta que só escuta em `127.0.0.1` (`listen.local_port`, 0 = desligado, requer reinício, o mesmo token de acesso). Com `listen.trusted_proxy`, os tokens errados de todos os clientes do proxy contam também em conjunto (o triplo do limite de um endereço), pelo que rodar `X-Forwarded-For` não anula o bloqueio.

- **O guia do proxy inverso** (`DEPLOYMENT.md`, oito idiomas) dá a receita completa: `Host` público, `X-Forwarded-For $proxy_add_x_forwarded_for`, `X-Forwarded-Proto`, o modo de rede e a declaração do proxy; já não diz que o monitor «não tem início de sessão» e avisa que `listen.trusted_proxy` pressupõe um proxy no mesmo computador.

- **`GET /api/settings` para um cliente da rede** devolve o valor apenas das definições que pode alterar; de qualquer outra definição (caminhos de chaves e tokens, pastas, nomes de variáveis) diz só se está definida.

- **Teste de cada rota «só este computador»**: uma tabela de rotas é percorrida contra um servidor real com um cliente fora do loopback (e o código-fonte é examinado para que uma rota nova não seja esquecida).

- **Um endereço do GitHub só passa o limpador com as formas de uma lista fechada** (um repositório, uma execução com o seu job ou tentativa, um commit, uma issue, um pull request, um ficheiro); é cortado no primeiro carácter que não seja letra, algarismo, ponto, hífen, sublinhado ou barra, e o que se segue é limpo como qualquer texto. Até agora, um segredo colado a uma ligação (uma consulta codificada, uma lista separada por vírgulas, dois pontos, um segmento opaco do caminho, um e-mail que começa no endereço) chegava inteiro à IA.

- **O hook do cliente de IA não entrega nenhum texto de registo**: só o repositório, o workflow, a conclusão e a ligação de cada alerta. A ordem de agir sem esperar que lha digam desapareceu; a última linha diz agora que um registo pode conter texto escrito por terceiros, que são dados não fiáveis e que as instruções que nele se encontrem nunca são seguidas. Nos oito idiomas.

### Corrigido

- **O fluxo de eventos para IA já não morre com uma linha de registo normal**: a linha do feed é limpa campo a campo e só depois escrita, em vez de limpar um JSON já escrito (uma causa que terminasse em `password: x`, `token=x` ou `DB_PASSWORD=x` estragava-o). Uma linha que não se consiga limpar é saltada e o fluxo continua; as respostas do servidor MCP são limpas da mesma forma. No limpador, o valor de um par `chave=valor` termina numa aspa, numa vírgula ou num ponto e vírgula, e um valor entre aspas é limpo por inteiro.

- **O que depende de quem pergunta é sempre respondido pelo seu próprio login**: `gh api user`, `user/orgs`, as notificações, uma pesquisa de `@me`, `gh auth` e `gh repo list` sem proprietário nunca vão para a GitHub App nem para a segunda conta, por muitas chamadas que lhes restem (com a segunda conta ativa, o monitor podia tomar como proprietário o titular dessa conta e listar as suas organizações).

- **Uma chamada a `gh` só é uma leitura se estiver numa lista branca**: `gh api ENDPOINT` com, no máximo, as opções `--jq`, `--paginate`, `-H` (das que uma leitura envia), `-i` e `--cache`. As formas coladas de uma escrita (`-XPOST`, `--method=DELETE`, `-fa=b`, `--field=a=b`, `--input=-`) e qualquer outra opção vão para o seu login em vez de serem repartidas pelas fontes.

- **O ficheiro do token da segunda conta** (`extra_reader.file`) tem de estar dentro da pasta de contas do monitor (`accounts/`, ou `MONITOR_ACCOUNTS_DIR`) e é aberto sem seguir uma ligação e só se for um ficheiro normal e pequeno; fora dessa pasta a definição fica vazia. O novo interruptor `extra_reader.any_folder` (desligado por defeito, só local) levanta a regra da pasta para um ficheiro que tenha de ficar noutro sítio.

- **Um painel central com data no futuro já não merece confiança**: a sua idade era reduzida a zero e contava como fresco para sempre; agora está atrasado, o resumo diz que a data não é fiável e tolera-se um relógio adiantado até cinco minutos.

- **O teste das portas das contas já não falha quando várias suites correm ao mesmo tempo**: o supervisor aceita que lhe indiquem por onde começar a procurar portas livres (o valor por defeito continua a ser 18800) e os testes pedem ao sistema um troço sem uso em vez de um fixo.

- **Uma página estragada põe o CI a vermelho**: um novo job (`page`, sem `continue-on-error`) abre a página do monitor de demonstração num navegador real (`tools/check_page.py`), percorre cada separador e cada subseparador das Definições, exige um mínimo de campos em cada um e falha perante qualquer erro da página, promessa não tratada ou console.error. Uma página estragada de propósito (uma segunda definição, uma atribuição ao nome de uma função, uma chamada a uma função que não existe) tem de o fazer falhar. O teste que procura funções definidas duas vezes passa a ver também uma declaração com recuo, uma com `async` e uma atribuição ao nome de uma função.

## [1.7.9]

### Corrigido

- Os links dos runs recebidos pelas ferramentas de IA (fluxo, resumo, estado, hook) eram cortados para "https://github.[blob]": o redator tomava o endereço por uma cadeia opaca. Os endereços https completos do github.com passam agora intactos; tokens, chaves, e-mails, IP e caminhos pessoais continuam limpos, também dentro de um link.

## [1.7.8]

### Adicionado

- **`listen.trusted_proxy`** (desativado por defeito, só local, nos oito idiomas): atrás de um proxy inverso próprio no mesmo computador, uma tentativa falhada é contada contra o último endereço de `X-Forwarded-For` em vez de contra o proxy, para que os tokens errados de uma pessoa não bloqueiem todos. Só muda essa contagem: um pedido que chega por um proxy continua a nunca ser tratado como este computador.

### Corrigido

- A página de Definições mostrava "O monitor local não responde" e nenhum separador: a caixa do separador Quota tinha o mesmo nome de uma função mais antiga do separador Básico e era substituída por ela. A caixa da Quota foi renomeada e um teste passa a falhar se uma função da página for definida duas vezes.

## [1.7.7]

### Adicionado

- **Uma verificação de que nenhum texto sai da sua caixa** (`tools/check_overflow.py` e um teste que é ignorado sem navegador): a página é aberta num navegador sem janela nos oito idiomas, larga e estreita, percorre cada separador e janela, e falha se algum texto for mais largo do que uma caixa com borda ou fundo ou sair da janela.
- **`display.blink_red_tiles`** (ativado por defeito, no separador Definições, nos oito idiomas): os quadros de cima e os elementos da barra inferior que ficam vermelhos piscam suavemente até a causa ser resolvida; com movimento reduzido no sistema, mostram em vez disso uma borda vermelha fixa e mais grossa.
- **Uma verificação do doctor para o fuso horário**: um fuso que nem o sistema nem a tabela interna conhecem é assinalado, e as horas passam a ser mostradas em UTC (antes caíam no fuso do computador sem avisar).
- **O separador Histórico diz "n de N"** quando a lista é mais curta do que o que o cabeçalho contou (o monitor guarda as 600 execuções mais recentes; os dados trazem `runs_total`).
- **Os painéis do separador Sentinela como dados**: `GET /api/sentinel/panels` (só de leitura), a ferramenta MCP `sentinel_panels` e uma secção "Sentinel panels" no resumo dão, para A1..A13 e o segundo sentinela, o nível, uma linha e as linhas em que agir com repositório e ligação; as linhas de um painel em "agir" ou "vigiar" tornam-se também alertas do feed (classes `real` e `watch`), pelo que o fluxo em direto, o hook, `alerts_open` e o contador de alertas reais as incluem.
- **Um "bing bing" quando algo novo falha** (as definições `sound`, nos oito idiomas): a página reproduz dois toques curtos (Web Audio) só por um NOVO vermelho ou uma ligação perdida, nunca numa atualização nem pelo que já existia, com pausa mínima, volume e um chip "Som" na barra inferior que desbloqueia o áudio do navegador, o silencia e fica memorizado; um botão "Testar som" em Este navegador; e `sound.server_beep` (desativado por defeito, só local) para quando a página está fechada (sinal do Windows, `afplay` do macOS, `canberra-gtk-play` do Linux ou o sino do terminal, sem shell e sem rede).
- **Tudo o que o monitor diz, como sinais para uma ferramenta de IA**: um inventário único (`signals.py`) com nível (agir / vigiar / info), resumo e linhas com repositório, ligação, idade e passo seguinte para o separador Agora e os seus quadros, os alertas, os repositórios, os painéis do sentinela A1..A13 e o segundo sentinela, a quota, a ligação e a saúde do monitor; `GET /api/ai/state` (versionado, só de leitura), um resumo com "O que fazer agora", "Pendentes" e "Saúde do monitor" e o contador de sinais em que agir, e as ferramentas MCP `monitor_state`, `signals`, `diagnose` e `act`. Um teste percorre a página e falha se um quadro ou separador não estiver no inventário nem marcado como decorativo.
- **A ligação a uma ferramenta de IA é a mesma na edição lite e na completa**: os mesmos canais (resumo, feed, `/api/ai/state`, fluxo em direto, ferramentas MCP, `ai-hook`), o mesmo código e as mesmas definições em ambas; o estado diz `edition` e lista os painéis que não existem em lite, para que um painel ausente não seja tomado por dados em falta.
- **Um modo poupança (poupança extrema da quota)**: ao lado de Normal, Rápido e Turbo, `low` lê só os repositórios quentes de 4 em 4 minutos e os restantes de 30 em 30, com listas de execuções curtas, e diz na barra e no resumo que os seus números podem ser antigos e quão antigos; `modes.auto_low` (ativado por defeito) entra sozinho abaixo de 1000 chamadas e volta acima de 2500 ou quando a quota se renova (dois números diferentes, sem oscilar); os valores estão em `modes.low` do ficheiro.
- **O painel central como base que não gasta quota** (`central.source`: desativado por defeito, `git` ou `http`; `central.max_age_minutes`, nos oito idiomas): o monitor lê `data/sentinel.json` do repositório de perfil (atualizado de meia em meia hora por um workflow com o seu próprio token) com um simples git fetch ou o ficheiro em bruto, mostra "fonte: painel central, há N min" no estado e no resumo, ignora um ficheiro atrasado (mais de duas horas) e di-lo, e no modo poupança só consulta a API em direto os repositórios que o painel diz estarem vermelhos, os que têm uma execução em curso e o que o painel não traz.
- **Uma GitHub App opcional para as leituras** (`github_app.enabled`, desativado por defeito, com `app_id`, `key_path` e um `installation_id` opcional, nos oito idiomas): as leituras do monitor usam o token de instalação de uma App, cuja quota é separada da do utilizador e maior quantos mais repositórios cobre; o JWT (dez minutos no máximo) é assinado pelo `openssl` a partir do caminho da chave, que o monitor nunca lê, copia, imprime nem regista; o token dura uma hora, fica em memória e é renovado cinco minutos antes; as escritas e ações mantêm o token do utilizador; se a App falhar ou lhe faltar uma permissão, a leitura repete-se com o token do utilizador; `GET /api/github-app/status` (só deste computador) mostra o nome, a instalação, as permissões concedidas e a quota da App, nunca a chave nem o token; os dados trazem a quota do utilizador junto da da App, e o doctor verifica o openssl, o ficheiro da chave e as suas permissões.
- **Dois guias novos, nos oito idiomas**: `docs/AI_CONNECTION.md` (ligar uma ferramenta de IA: o que vê, os cinco canais, passo a passo, segurança, resolução de problemas, o que mostra cada edição) e `docs/QUOTA.md` ("Mais quota, menos gasto": como funciona a quota, todas as vias com que o monitor a poupa, uma GitHub App passo a passo, partilhar a quota entre ferramentas, o que não fazer); ambos estão ligados a partir do README e do índice de ajuda, e um teste verifica que cada definição citada existe.
- **A ajuda é verificada a cada alteração**: uma definição sem etiqueta e ajuda nos oito idiomas, um separador sem tópico de ajuda ou uma linha do registo de alterações que nomeia uma definição ou um endpoint ausente da ajuda e dos guias fazem agora falhar os testes; há uma lista de verificação da ajuda no CONTRIBUTING e no modelo de pull request.
- **Um separador Quota nas Definições** (nos oito idiomas, também na edição lite): os modos e os valores da poupança (`modes.*`), a poupança (`network.etag`, um alias que funciona em conjunto com `cache.etag.enabled`), o painel central, a GitHub App e uma segunda conta para as leituras num só sítio, com botões que mostram a quota de cada fonte com a hora de renovação, testam a App e a segunda conta, listam as permissões que faltam à App e aplicam os valores recomendados ou os predefinidos.
- **Uma segunda conta só de leitura para as leituras** (`extra_reader.enabled`, `extra_reader.file`): a definição guarda só o CAMINHO de um ficheiro com um token de acesso fino, que o monitor lê no momento de usar, guarda em memória e nunca armazena, imprime nem regista; as leituras repartem-se entre a sua sessão, a App e a segunda conta conforme as chamadas que restam a cada uma, uma fonte recusada fica de fora cinco minutos e a leitura repete-se com a seguinte, e as escritas e ações nunca a usam.
- **Contabilidade das leituras**: o estado, o resumo e os dados dizem quantas chamadas condicionais foram feitas e quantas responderam 304 (sem gastar quota) e a quota de cada fonte.
- **Quem gasta a quota**: o monitor compara, dentro de cada janela horária, o que gastou toda a conta com as suas próprias chamadas e diz no separador Quota, no estado e no resumo quanto gastam outras ferramentas, com um aviso quando gastam a maior parte (o GitHub não diz qual).
- **O fluxo em direto leva também os outros sinais**: a quota esgotada, a ligação que cai, os dados que ficam velhos, um painel central atrasado e os avisos de saúde passam a ser eventos do feed (e do fluxo e do hook) quando aparecem, mudam ou se resolvem, não só os workflows vermelhos e os painéis do separador Sentinela.
- **O despacho por lotes guarda a tentativa da execução que encontrou** (`run_attempt` no registo do lote, do campo `attempt` de `gh run list`; vazio se o `gh` não o der), e os guias da ligação a uma ferramenta de IA e da quota descrevem a segunda conta só de leitura.

### Alterado

- **A barra inferior foi redesenhada**: cada elemento é uma pastilha com a sua borda, a ligação e a quota tomam a cor do seu estado, o relógio é uma caixa com dígitos grandes, a negrito e tabulares, a data por cima e o fuso em letra pequena, e a barra mantém a sua ordem em janelas estreitas.
- **Cada caixa deixa o texto quebrar em vez de sair** (quadros, pastilhas, etiquetas, células, títulos, botões das janelas): a hora da última leitura traz o fuso à parte em letra pequena, as linhas de alertas passam a duas colunas em janelas estreitas e as grelhas de quadros podem encolher abaixo do seu conteúdo.
- **Os quadros de uma linha têm a mesma altura**, seja o que for que o seu texto pequeno precise.

### Corrigido

- **Um só número para as falhas abertas**: o quadro "vermelhos em main", a lista de alertas, a barra inferior e o resumo contam o mesmo, um workflow cuja última execução no ramo principal falhou (uma falha num ramo de trabalho já não aparece como alerta aberto), e a barra nunca diz "sem avisos" enquanto houver alertas abertos.
- **O arranque do monitor nomeia a versão uma só vez**: desaparece a linha "GitHub Actions v..." que repetia o cabeçalho; o autor e a licença ficam numa linha.
- **Ficheiros de estado danificados** (estado de colaboração, cache e histórico do sentinela com outra forma) são ignorados entrada a entrada em vez de chegarem ao código que os lê.
- **Uma quota do GitHub esgotada é UM aviso, não um erro por repositório**: as leituras dos repositórios param até à renovação (e retomam sozinhas), a lista de Alertas diz "Quota do GitHub esgotada até às HH:MM ... (N repositórios por atualizar)", a barra inferior também, nada fica vermelho e nada chega ao feed, ao som nem ao resumo como falha; os textos de erro do `gh` são cortados numa linha (sem parágrafo legal nem id do pedido) e muitos repositórios com o mesmo tipo de erro são agrupados numa linha.
- **O Acerca de (e qualquer página) já não espera pela rede**: a verificação de uma nova versão do monitor era lida dentro do pedido de /api/about quando a sua resposta tinha mais de um dia, pelo que um `gh` sem sessão ou uma rede lenta faziam a janela Acerca de demorar de 10 a 25 segundos; agora a resposta da cache é devolvida de imediato e a leitura é feita por um fio em segundo plano, um de cada vez.

## [1.7.6]

A ligação entre o monitor e uma ferramenta de IA: o feed coincide sempre com a página, cada alerta diz porque está vermelho, um fluxo e três ferramentas MCP empurram as novidades, um comando instala o script de ligação, a barra mostra se há uma IA ligada e todos os ficheiros de estado são privados do seu dono.

### Adicionado

- **O resumo e o feed seguem cada atualização do separador Alertas** (e cada leitura do feed e cada ciclo): antes iam um ciclo atrás, de modo que uma IA podia ler 10 alertas enquanto a página mostrava 6. O `ALERTS_BRIEF.md` leva agora `Updated:` no seu fuso horário e uma linha para máquinas `updated_epoch:`, e `GET /api/ai/brief?fmt=json` acrescenta `updated`, `updated_local` e `age_seconds`. Um ciclo que ainda não carregou os dados nunca resolve alertas.
- **`ai_alerts.diagnose`** (desligado por predefinição, no separador Definições, em oito idiomas): cada alerta de uma execução vermelha nova leva `diagnosis`, o primeiro passo que falha e cerca de dez linhas relevantes do registo, lidas com chamadas só de leitura, limpas de segredos e limitadas em tamanho e em execuções por ciclo; um erro de infraestrutura no registo torna o alerta transitório.
- **`ai_alerts.cascade`**: os alertas vermelhos porque outro repositório está vermelho (nomeado no registo ou na regra `ai_alerts.cascade.map`) são listados sob ele no resumo e levam `origin`.
- **`GET /api/ai/stream`** (`ai_alerts.stream`, desligado por predefinição): eventos do servidor, só leitura, com o token de acesso no modo de rede, limitado em ouvintes e em tempo, retomável com `Last-Event-ID`; a edição lite não o tem.
- **Ferramentas MCP `alerts_open`, `alert_diagnose` e `alert_ack`** (a última só com `--allow-ack`) e um aviso à IA quando se liga, nas `instructions` e com uma notificação, que diz quantos alertas reais estão abertos.
- **`monitor_cli.py ai-hook install|status|uninstall [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]`** e o script de ligação `ai_hook.py` (só biblioteca padrão): junta o resumo à sessão de IA e, só com `ai_alerts.client_hook.block_on_stop` (desligado por predefinição), pede à IA que veja os alertas reais abertos antes de terminar um turno. As definições da ferramenta são fundidas, nunca substituídas, guarda-se uma cópia do ficheiro, um ficheiro que não seja JSON válido é recusado sem lhe tocar e tudo o que se escreve é ASCII puro. Os valores estão em `ai_alerts.client_hook` (separador Definições, oito idiomas).
- **Um batimento da IA** (`ai_alerts.heartbeat`): o fluxo, o servidor MCP, o script de ligação e os endpoints anotam a sua última leitura num pequeno ficheiro local, e a barra inferior mostra se há uma IA ligada e há quanto tempo leu.
- **`monitor_cli.py --token-file FICHEIRO`** e um aviso no stderr quando se usa `--token` (aparece na lista de processos) ou quando o ficheiro do token pode ser lido por outros utilizadores.
- Testes para cada alteração, numa pasta temporária e sem rede, incluindo o modo de cada ficheiro de estado com um `umask` permissivo.

### Alterado

- **Todos os ficheiros de estado do monitor são criados com o modo 0600** (as pastas criadas, com 0700) através de um único auxiliar, `private_io.py`: silenciamentos, eventos, o feed, o resumo, caches, as definições e os ficheiros escritos pelo instalador do script de ligação. No Windows o programa não consegue impor os modos (as pastas herdam as permissões da pasta-mãe).
- **Ao arrancar o modo de rede** com `listen.query_access` ainda ligado, passam a imprimir-se os primeiros passos (desligá-lo; usar HTTPS ou uma VPN), e a ajuda de `listen.network` e o guia avançado dizem o mesmo em oito idiomas.
- **O feed de alertas para IA está desligado por predefinição** (`ai_alerts.enabled`, estava ligado): uma instalação nova não escreve nenhum feed até o ligar. Uma instalação que já tem um feed na sua pasta mantém-no ligado, e a consola di-lo uma vez ao arrancar, pelo que ninguém que o usasse de propósito fica desligado.


### Segurança

- **As notificações enviadas ignoram as variáveis de proxy do ambiente** (`http_proxy`, `https_proxy`): um proxy fazia a verificação julgar o endereço do proxy e não o do destino, e um proxy que respondesse com um redirecionamento podia enviar o pedido para a rede local (incluindo o endereço de metadados de uma cloud). A nova definição `network.use_proxy` (desligada por predefinição, no separador Definições, em oito idiomas) volta a usá-las e, então, o destino e o alvo de cada redirecionamento são verificados antes de o proxy receber o que quer que seja. Testado com um proxy que redireciona para o endereço de metadados.
- **`/api/ai/actions/confirm`, `/api/ai/actions/unlock`, `/api/ai/test` e `/api/notify/test` são só para este computador** no modo de rede (403 `local_only`), como os outros endpoints que atuam.
- **Um plano do `act` fica preso ao seu workflow**: o plano guarda o caminho resolvido e o SHA-256 do ficheiro, e ambos são verificados de novo mesmo antes de o `act` arrancar; um workflow editado, substituído ou removido depois da confirmação não corre (`workflow_changed`, com texto em oito idiomas).
- **O porta-chaves do macOS já não recebe o token numa linha de comandos**: o `security -i` lê o comando da entrada padrão, pelo que o token não aparece na lista de processos.
- **Tudo o que o `gh` imprime é limpo antes de ser guardado**: o registo das ações para IA e o detalhe de uma ação recusada passam pelo limpador, que agora cobre também os tokens antigos de 40 hexadecimais e o token guardado pelo monitor.
- **A lista de endereços recusados é limitada** (`localguard`): o bloqueio seguinte elimina todos os bloqueios terminados, não só o do endereço que pergunta, e nunca guarda mais de 2000 entradas.
- **Um silenciamento que não se conseguiu guardar não é dado como guardado**: `POST /api/alerts/mute` e `unmute` respondem `ok: false` quando o ficheiro não pôde ser escrito.
- **A linha de comandos nunca mostra um traceback perante uma resposta de forma errada**: uma lista, `null` ou um número em vez de um objeto, ou um campo do tipo errado, termina com o código de saída 4 e uma mensagem.
- **Um cliente da rede só pode escrever uma lista curta de definições** (o idioma, o fuso horário e o ritmo da página): cada canal de notificações, cada caminho, cada nome de variável de ambiente e os ficheiros em que o fluxo de assinatura e envio confia alteram-se a partir do computador do monitor. Uma definição acrescentada depois é só local até ser incluída de propósito.
- **Atrás de um proxy inverso na mesma máquina**, um pedido com cabeçalho de reencaminhamento (`Forwarded`, `X-Forwarded-*`, `X-Real-IP`) ou com o nome público do proxy nunca é «este computador», e o token de acesso é julgado antes do bloqueio por endereço, pelo que uma enxurrada de tokens errados não deixa o dono de fora.
- **As chamadas a este computador nunca passam por um proxy do ambiente** (`netguard.local_open`, usado pela linha de comandos, pelo servidor MCP, pelas vistas de terminal e pelos ganchos), e a linha de comandos não segue redirecionamentos, pelo que o token de acesso não é reenviado para outro endereço.
- **Cada resposta proíbe ser colocada numa moldura** (`X-Frame-Options: DENY`, `frame-ancestors 'none'`, `nosniff`), a página verifica o `Host` como a API, e toda a resposta autenticada pelo endereço obsoleto `?access=` leva o cabeçalho `Deprecation`.
- **Envio e assinatura**: as execuções que existem antes de um envio são anotadas e só uma nova pode ser tomada como nossa (sem relógios); dois candidatos novos exigem revisão; a entrada `ref` é o commit verificado; um workflow obrigatório compara-se com o seu FICHEIRO, nunca com um nome visível; o nome de um lote vai em UTC.
- **O limpador do feed para IA cobre mais formatos**: nomes que terminam em `PASSWORD`, `PWD`, `SECRET` ou `TOKEN`, credenciais dentro de um endereço, webhooks do Slack e do Discord, tokens de bot do Telegram, tokens `glpat-`, `npm_` e `pypi-`, chaves privadas, cadeias hexadecimais longas e o token de acesso deste monitor. O `get_run_failure` do servidor MCP só lê repositórios que o monitor vigia (ou `ai.allowed_repos`).
- **Os ficheiros editados à mão** (silenciamentos, estado das atualizações) perdem só as entradas más, e um estado das atualizações mau já não pára o arranque.
- **Fusos horários**: O Cairo segue o horário de verão desde 2023 na tabela interna, e um nome de fuso que o sistema não conhece é recusado no separador Definições. A edição completa dá o número de workflows a vermelho no cabeçalho como a lite, e `monitor_cli.py status` sem dados termina com o código 4 como `health`.

## [1.7.5]

A linha de comandos lê o token de acesso com o seu próprio nome, o modo de rede é mais seguro por predefinição (o endereço do computador fica escondido da rede, o endereço antigo ?access= pode ser desativado, os destinos de notificação da rede local são recusados, aviso sobre HTTP simples), as horas para as pessoas usam o seu fuso horário, um alerta pode ser silenciado até o elemento mudar, e foram corrigidas as contagens e verificações que davam respostas erradas.

### Adicionado

- **`monitor_cli.py --token TOKEN`**, e o token de acesso da linha de comandos tem agora o nome que o próprio monitor lê: `MONITOR_ACCESS_TOKEN`, depois o seu alias `MONITOR_TOKEN`, depois `--token` (uma opção aparece na lista de processos, por isso é o último recurso). A mensagem de um cliente recusado nomeia a variável. Testado contra um monitor falso que exige o cabeçalho.
- **Um aviso no stderr** quando o `monitor_cli.py` aponta para `http` sem cifra noutro computador (o token e as respostas viajariam em claro); a resposta e o `--json` não são tocados.
- **`listen.query_access`** (ativo por defeito, no separador Definições, em oito idiomas): desative-o e o endereço obsoleto `?access=` é recusado, pelo que a sessão só se abre com `POST /api/access` (o token no corpo) ou o cabeçalho. O endereço que funciona responde com um cabeçalho `Deprecation` e a consola diz que é obsoleto.
- **Um silêncio «até o item mudar»**: `POST /api/alerts/mute` aceita `until_change` para um alerta; o silêncio guarda o `updated_at` que tinha a issue ou o pull request e termina logo que muda (um comentário novo, um push), ou no fim das horas, o que acontecer primeiro. Os alertas do Collab passam a levar `details.updated`.
- **Uma verificação do doctor para um token partilhado por várias contas** (`credential`): compara só uma impressão digital curta dos tokens com que as contas leriam o GitHub (o token guardado pelo monitor, ou `GH_TOKEN` / `GITHUB_TOKEN` do ambiente) e lista as contas que partilham um; o token nunca é mostrado.
- Testes para cada alteração, incluindo um teste de higiene do webhook: uma carga com um segredo, um e-mail, uma mensagem de commit e um token não chega nem à lista em direto, nem ao feed, nem a uma notificação, e a lista em direto passa a ser filtrada por uma lista de campos permitidos.

- **`notify.allow_private_targets`** (desligado por predefinição, no separador Definições, nas oito línguas): é recusado um destino de notificação que seja, ou resolva para, um endereço de loopback, privado (10.x, 172.16-31.x, 192.168.x, fc00::/7), de ligação local (169.254.x, com o endereço de metadados da nuvem, fe80::/10), partilhado (100.64.0.0/10) ou reservado. O nome é resolvido uma vez e o socket abre-se para o endereço verificado (um nome que mude a resposta não passa), e cada redirecionamento segue a mesma regra. Os canais `mqtt` e `http_local` continuam apenas locais por definição. Testado com um servidor e um resolvedor falsos.
- **Um aviso sobre HTTP simples no modo de rede**: a ajuda do interruptor `listen.network` diz agora, nas oito línguas, que sem HTTPS o token e os dados circulam sem cifra; a consola já avisa ao arrancar em rede sem certificado.
- **Horas para as pessoas no seu próprio fuso horário**: a linha `Last read` e os silêncios do `monitor_cli.py`, o registo `actions_monitor_log.txt`, os relatórios da sentinela, o resumo para IAs e as notificações mostravam UTC (`...Z`) sem o dizer, uma ou duas horas diferente do relógio da parede. Agora lêem-se como `11:43:07 CET (10:43:07 UTC)`: o fuso do computador, o seu nome e a hora UTC ao lado. O horário de verão é seguido (testado em torno das duas mudanças do ano e para Madrid, UTC, Tóquio e Nova Iorque).
- **`display.timezone`** (`local` por omissão, no separador Definições e nos oito idiomas): `utc` ou um nome IANA como `Europe/Madrid` mostra os textos e os relógios da página nesse fuso; a variável de ambiente `MONITOR_TIMEZONE` prevalece sobre o ficheiro. Sem base de dados de fusos no sistema (Windows sem `tzdata`) usa-se uma tabela incorporada dos fusos habituais.
- **Os campos para máquinas mantêm UTC e ganham um campo irmão legível**: `generated_local` em `ci_red.json` e na exportação local da fila, `updated_local` em `monitor_cli.py status --json` e nos dados da página, e uma linha `Updated:` em `ALERTS_BRIEF.md`. Os relógios da página e a barra inferior mostram o fuso (`CET`, `JST`...).
- **Um botão «Até haver alteração» no separador Alertas**: silencia um alerta de um issue ou pull request até o seu `updated_at` mudar (novo comentário, push), ou no máximo pelas horas habituais; o alerta silenciado indica «silenciado até haver alteração». Textos nos oito idiomas e um teste de regressão.

### Alterado

- **A API chama à edição `complete`** (dizia `full`) em `/api/about`, `/api/statusbar`, `--doctor --json` e na linha de comandos; `full` fica reservado ao que a sentinela pode executar. A página e a linha de comandos continuam a entender as duas palavras.
- **Os silêncios só se fazem a partir do computador do monitor** (também no modo de rede, até às edições com utilizadores): o guia do Collab di-lo nos oito idiomas e um teste mantém a rota atrás dessa regra.
- **Os workflows deste repositório usam ações fixadas a um commit completo**, com a versão num comentário, e um teste mantém isso.

### Corrigido

- **Issues que se poderiam fechar** (verificação de superfície): uma execução verde de outro workflow deixa de propor o fecho de uma issue; a issue tem de nomear o workflow (pelo nome ou pelo ficheiro, «Firmware build failed» para `firmware-build.yml`) e esse mesmo workflow tem de ter uma execução verde posterior no ramo por defeito. Uma issue que não nomeia nenhum workflow não propõe nada.
- **Tag face ao manifesto** (verificação de superfície): quando o tag da última release vai à frente do manifesto lido do clone, o manifesto do ramo por defeito no GitHub é lido uma vez para essa release (o clone pode estar atrasado depois de uma release) e o aviso desaparece se já tinha essa versão; os tags que não são versões (`meshes-1`) são ignorados.
- **Passo seguinte de um candidato a release**: um repositório cuja release precisa de uma compilação assinada diz agora «compilar no Actions e assinar», à parte de «subir a versão», «assinar» e «publicar»; os repositórios de ecossistemas tratados noutro sítio ficam fora dos candidatos (testado).
- **As execuções em curso e em fila contam-se uma só vez**: os mosaicos «em curso» e «em fila», a lista «A acontecer agora», a barra de estado (novo elemento «N em curso · M em fila», também em `/api/statusbar` como `runs`) e `monitor_cli status` dão os mesmos números para os mesmos dados, nas duas edições. Quando os filtros da página (ecossistema, estado, pesquisa, uma lista vinda de um mosaico) escondem execuções, os mosaicos mostram «3 de 13» e a lista começa por «A mostrar 3 de 14 (filtros ativos)», pelo que um filtro guardado no navegador já não parece uma incoerência. A lista de execuções ativas também descarta uma execução lida duas vezes. Textos nos oito idiomas e testes para as duas edições.

### Segurança

- **`/api/statusbar` já não entrega o endereço do computador na rede local (`lan_address`) a um cliente da rede** no modo de rede; a barra desenha-se sem ele.
- O endereço obsoleto `?access=` só é atendido num `GET`.

## [1.7.4]

Uma barra ao pé da página para os avisos e os dados do monitor, um botão de ecrã inteiro, tabelas que se ordenam por uma ou várias colunas com as colunas à sua escolha e a linha de comandos como cliente do monitor em execução.

### Adicionado

- **Uma barra de estado ao pé da página** (todas as edições) no lugar da linha de autoria. À esquerda, o aviso mais importante (vermelho antes de amarelo) com o número dos outros e um botão que abre uma janela com todos, o mais recente primeiro, com filtro por nível; sem avisos di-lo. À direita, a ligação (uma luz: GitHub em linha, sem ligação ou quota baixa), a quota e quando renova, a última leitura, o modo de trabalho, quantas sentinelas estão ativas, os repositórios vigiados, a conta, versão e edição, o endereço do monitor e a data e hora locais. Segue a largura da janela: os dados secundários dobram-se em ecrãs estreitos. `GET /api/statusbar` dá-lhe os factos que os dados do GitHub não trazem (sem chamada ao GitHub, sem segredos).
- **Um botão de ecrã inteiro** no canto superior direito (a API Fullscreen; um segundo toque sai), com ícone e texto nos oito idiomas.
- **Tabelas ordenáveis**: Repositórios e Histórico ordenam-se com um clique num cabeçalho (crescente, decrescente, sem ordem), por várias colunas ao mesmo tempo com Shift+clique (cada critério mostra o número e o sentido), com os valores vazios sempre no fim, e a ordem é recordada. Um seletor de colunas junta mais colunas: número da execução, autor, commit curto, tentativa, espera na fila, ficheiro e ecossistema no Histórico; ecossistema, número da execução, autor, commit, tentativa, espera na fila, execuções em 24 h, ramo predefinido, visibilidade, último push e pull requests abertos nos Repositórios. O monitor passa a enviar o número da execução e a espera na fila de cada execução e um pequeno bloco de dados por repositório (tirado do que já leu; nada de novo do GitHub).
- **`monitor_cli.py`**, a linha de comandos como cliente do monitor em execução (`status`, `health` ou `check`, `doctor`, `accounts`, `alerts`, `live`): lê `GET /api/...` neste computador ou em `--url` / `MONITOR_URL`, imprime texto ou um documento JSON com `--json`, aceita `--account`, `--sentinel`, `--level`, `--muted`, `--timeout` e `--lang`, e usa códigos de saída estáveis (0 bem, 1 uso incorreto, 2 monitor inacessível, 3 credencial recusada, 4 degradado, 5 alertas encontrados com `--fail-on`). O `health` distingue um monitor que não responde de um acesso ao GitHub que falhou e de uma quota esgotada. A edição lite responde a `status`, `doctor` e `health`. Nunca escreve no GitHub; o token de acesso do modo de rede vai em `MONITOR_TOKEN`. As ferramentas anteriores continuam a funcionar. Guia em oito idiomas (`CLI.md`).
- Testes de cada alteração, incluindo a lógica de ordenação executada a sério com Node onde está instalado, os comandos contra um monitor falso, cada código de saída e um teste de que cada registo de alterações, em cada idioma, lista as suas versões da mais recente à mais antiga, com as mesmas versões da fonte.

### Alterado

- **Os avisos vermelhos e amarelos já não estão no topo da página**: os mesmos avisos aparecem na barra do pé (o mais importante) e na sua janela (todos).
- **O README do pacote** (`README_<idioma>.txt`) deixa de levar um histórico de versões: remete para o registo de alterações.
- As imagens do README, da arquitetura e da estrutura são redesenhadas para esta versão, com uma imagem das novas tabelas e da barra.

### Removido

- **A linha de autoria ao pé da página**: o autor e a licença estão em Acerca de.

## [1.7.3]

Uma segunda sentinela para issues e pull requests, um separador com os alertas de todas as sentinelas e silêncios que acabam sozinhos. A Collab só lê; nada disto escreve no GitHub.

### Adicionado

- **A sentinela Collab** (`sentinel_collab.py`, só edição completa, desligada por omissão): as issues e pull requests abertas dos seus repositórios, com um relógio próprio (`sentinels.collab.refresh_seconds`) que nunca altera a sentinela de CI. Seis regras com códigos estáveis: `collab.issue.stale`, `collab.issue.critical`, `collab.issue.external`, `collab.pr.review_pending`, `collab.pr.draft_old` e `collab.pr.conflict`. Lê com pedidos condicionais (um repositório sem alterações não gasta quota), no máximo `max_repos_per_tick` repositórios por ronda, pára abaixo de `min_rate_remaining`, guarda o estado em `collab_state.json` (dentro da pasta de cada conta) e só anuncia as mudanças. Os bots ficam de fora. A sua camada *Issues e pull requests* está no separador Sentinela e `GET /api/sentinel/collab` serve-a.
- **Dois eventos novos**, `collab_new` e `collab_fixed`, para o registo e para todos os canais de notificação (estão na lista de eventos dos canais e no esquema de eventos).
- **O separador Alertas** (edição completa): uma lista com os alertas de todas as sentinelas, cada um com a sua origem (CI ou Collab) e nível, filtro por origem e por nível, ligação ao GitHub e um ponto vermelho no separador com os erros abertos. `?view=alerts&sentinel=collab` abre-o já filtrado.
- **Silêncios com fim** (`alert_center.py`): a partir do separador Alertas pode silenciar-se um alerta, uma regra (o seu código) ou uma sentinela inteira durante `alerts.mute_hours` horas (24 por omissão, de 1 a 720). Um silêncio caduca sozinho, pode repor-se de imediato e um histórico curto diz o que foi silenciado, desde quando e até quando. É uma nota do monitor, guardada por conta em `alert_mutes.json`; no GitHub nada muda.
- **`ignore_labels`** nas regras da Collab (`monitor:ignore` por omissão): uma issue ou pull request que uma pessoa etiquetou assim no GitHub não gera alerta. O monitor nunca escreve etiquetas.
- **`GET /api/alerts`** (`?sentinel=`, `?level=`, `?muted=show|hide|only`) e **`GET /api/events`** (`?sentinel=`, `?since=`), ambos só de leitura e por conta; `POST /api/alerts/mute` e `/api/alerts/unmute` (só deste computador, token de uso único, como qualquer outra alteração).
- **Uma lista de verificação na vista em direto** (segredo de 32 carateres ou mais, reencaminhamento ou túnel para `/api/webhook`, o evento de teste do GitHub, vigiar a quota) e os mesmos passos no guia do webhook.
- **Um guia da sentinela Collab** nos oito idiomas (`COLLAB.md`), encontrado pela Ajuda.
- Testes de cada alteração: as regras e os seus códigos estáveis, o custo (leituras condicionais, o limite por ronda, a pausa), que só lê, os silêncios (âmbitos, fim, limites, histórico, um ficheiro danificado), a etiqueta de ignorar, os endpoints, que a lite não tem nada disto, os ficheiros de estado de cada conta e da demonstração e os textos nos oito idiomas.

### Alterado

- A página de definições tem doze definições da Collab num bloco do separador Sentinela, e `alerts.mute_hours` ao lado.
- Os ficheiros `alert_mutes.json`, `collab_state.json`, `ai_alerts_state.json` e `ALERTS_BRIEF.md` nunca são enviados para o git nem viajam num pacote.

## [1.7.2]

Um cabeçalho que se lê por ordem e se ajusta à janela, os controlos rápidos fixos no canto superior direito, Acerca de no painel lateral e o fim do aviso de versão nova. Os testes deixam de deixar ficheiros junto do código, que é o que tinha substituído as definições de uma pessoa pelo modelo neutro.

### Alterado

- **Os números do cabeçalho, por ordem e numa grelha** (todas as edições): a primeira linha vai agora do que está a acontecer ao que pede atenção (em curso, em fila, falhas, sucessos, minutos de cálculo, incidências abertas, workflows a vermelho em main, por assinar) e a segunda guarda a maquinaria (repositórios, quentes, modo, leituras poupadas, quota, ligação, atualizado). Cada linha é uma grelha de oito colunas, quatro ou duas conforme a largura do seu próprio bloco, de modo que as duas linhas enchem sempre as suas filas com qualquer largura de janela, a partir de um ecrã de 1080p (um mosaico nunca impõe uma largura própria). O mosaico comprido da quota ocupa duas colunas.
- **Os controlos rápidos ficam no canto superior direito**: o botão de só quentes, a lista de velocidade (normal, rápido, turbo) e as etiquetas de saúde dos ecossistemas (e os avisos de orçamento e de pausa) estão fixos aí, numa coluna própria, e quebram dentro dela sem mexer nos números. Abaixo de 1100 pontos de largura o canto passa para cima dos números. A página de todas as contas esconde-o, como esconde os números.
- **Definições, Ajuda e Acerca de estão só no painel lateral**: os botões da roda dentada, do ponto de interrogação e da informação saem do cabeçalho. Definições já era uma secção do painel; Ajuda deste separador fica ao fundo e **Acerca de** junta-se ao lado. O guia das Definições di-lo nos oito idiomas.

### Removido

- **O aviso de versão nova no cabeçalho** (o distintivo laranja) com o seu código e o seu estilo. O painel Acerca de continua a dizer se há uma versão mais recente, e a consola também; a definição `updates.check` e a cache de 24 horas são as mesmas.

### Corrigido

- **O modelo neutro podia substituir as definições de uma pessoa.** Três grupos de testes (o isolamento do lite, o token de uma só utilização e a parte lite das contas) arrancavam um monitor cujo primeiro arranque escreve `actions_monitor.json` ou `update_check.json` junto do código, e nada os removia; ao copiar a pasta `monitor/` sobre uma instalação, as definições da pessoa (o seu catálogo próprio de ecossistemas) ficavam substituídas pelo modelo, e todos os repositórios caíam no grupo «Everything else» (um canto que dizia «Everything else 54»). Cada um desses testes remove agora o que criou, e um teste demonstra-o. O pacote nunca levou as definições nem o catálogo de ninguém, e continua sem os levar.

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

### Adicionado

- **Um grupo de recurso** `rest` («Todo o resto», prefixo `*`) no fim do catálogo de exemplo de ecossistemas, para que uma instalação nova não deixe nenhum repositório de fora.
- **Um grupo automático «Sem classificação»** para os repositórios que nenhum grupo reclama (definição `show_unclassified`, ativa por omissão; uma escolha explícita de ecossistemas é respeitada).
- **Um aviso quando o filtro esconde repositórios**: um banner (completa e lite) diz «o seu filtro de ecossistemas esconde N dos M repositórios da conta» e nomeia-os.
- **A edição lite arranca com o que já configurou**: no primeiro arranque, `actions_monitor_lite.json` copia de `actions_monitor.json` (se existir) a conta, os repositórios e ecossistemas a vigiar, os ficheiros de catálogo, as exclusões, o idioma e a profundidade de leitura, e di-lo na consola. Sem esse ficheiro, o seu modelo vigia todos os ecossistemas.
- **`tui.py --lite`** (ou `MONITOR_MODE=lite`) lê a edição lite na porta 8766.
- **`redrule.py`**, a regra única e pequena do «vermelho em main», usada pela sentinela e pela edição lite (que marca o número como aproximado porque adivinha o ramo predefinido).
- **`ghamon_etag_invalid_total`**, a contagem de entradas de cache danificadas, em `/metrics`.
- Testes: paridade dos dados do cabeçalho entre a edição completa e a lite, o grupo de recurso, a contagem de repositórios escondidos, o arranque lite, a marca quente do webhook, a entrada de cache danificada, e que importar o monitor ou a sentinela nunca carrega o Rich.
- Guias `LITE` e `SETTINGS` (oito idiomas) atualizados.

### Alterado

- **As duas edições mostram os mesmos números do cabeçalho**: execuções, falhas, sucessos, minutos de cálculo, em curso e em fila são contados uma só vez, pelo servidor, sobre as mesmas 24 horas e com cada execução contada uma vez; a edição lite lê com a mesma profundidade que a completa. A edição lite esconde o cartão «não assinados».
- **Um evento do webhook marca o repositório como quente**, para que o ciclo seguinte o leia outra vez, diga o que disser o evento.
- O cartão da quota do GitHub é desenhado desde o primeiro momento, enquanto os repositórios ainda carregam.

### Corrigido

- Uma instalação nova com o catálogo de exemplo via quase nenhum repositório; a edição lite detetava um repositório em 129 porque o seu modelo filtrava por ecossistema.
- **Uma entrada de cache danificada é apenas uma falha de cache**: é deitada fora e o endpoint é lido de novo por inteiro.
- «Vermelho em main» e os minutos de cálculo diferiam entre as duas edições.

### Segurança

- A edição lite nunca herda da completa a sentinela, a IA, o webhook, as saídas nem as notificações, nem qualquer segredo; não escreve nem `ci_red.json` nem uma fila de assinatura.

## [1.6.1]

### Adicionado

- **A edição lite**, um segundo produto mais simples no mesmo pacote: `MONITOR_LITE_GITHUB_ACTIONS.bat` / `.sh` / `.command` ou `--lite` / `MONITOR_MODE=lite`. O que corre e o que falhou, falhas e sucessos das 24 horas, vermelho em main, o histórico e os gráficos básicos; uma página de Definições curta (conta, repositórios e ecossistemas, atualização, idioma, tema); o seu próprio ficheiro `actions_monitor_lite.json`, os seus próprios ficheiros de estado com o sufixo `_lite` e a porta 8766, para que as duas possam correr lado a lado.
- **Comando `act` no painel do repositório**: para cada workflow do repositório, `act -W .github/workflows/FICHEIRO -j JOB` pronto a copiar. O monitor nunca o executa (executá-lo existe apenas como ação confirmada do assistente de IA).
- **Um exemplo de contentor** (`deploy/Dockerfile`) que a CI constrói.
- Guia `LITE` em oito idiomas, uma tabela Lite contra Completa em cada README e capturas novas de ambas as edições em claro e escuro.
- O roteiro lista o que não coube: espelho local de artefactos, FinOps dos minutos, estado dos runners próprios e uma exportação OTLP, e as notas da vista de terminal (porque usa o Rich).

### Segurança

- A edição lite não tem sentinela: não é importada e os seus endpoints respondem 404.

## [1.6.0]

### Adicionado

- **Leituras condicionais (ETag)**: cada leitura das listas de execuções envia `If-None-Match`; uma resposta `304 Not Modified` não gasta quota. O cabeçalho e `ghamon_etag_saved_total` contam as leituras poupadas; `cache.etag.*` no separador Definições.
- **Resistência a cortes de rede**: quando todas as leituras de um ciclo falham por um problema de ligação, a página mantém a última imagem com um banner de sem ligação e retoma sozinha; eventos `offline` e `online` (podem ser notificados) e `ghamon_offline`.
- **Análise** (secção A12 do separador Sentinela, `/api/analytics`, `/metrics`, a fonte JSON do Grafana): p50 / p95 da duração de cada workflow, do tempo em fila dos seus jobs e de cada passo; workflows que ficaram mais lentos do que o habitual; workflows **instáveis** (falharam e depois passaram com o mesmo commit, ou precisaram de outra tentativa), apenas uma etiqueta que nunca muda o que conta como vermelho.
- **Webhook de entrada em tempo real**: um evento `workflow_run` assinado atualiza a lista de execuções do seu repositório sem ler o GitHub, os eventos `workflow_job` trazem tempos de fila e de passos; só se guardam campos curtos validados (`/api/live-events`).
- **Linter de workflows**: `lint_workflows.py` (ações não fixadas por SHA, permissões em falta ou largas, segredos em claro, injeção, `pull_request_target` com o código da PR), regras ativáveis com a sua própria gravidade, uma linha no relatório diário e a secção A13. Um comentário `# monitor-lint: ignore REGRA motivo` ou a definição `lint.ignore` silencia um achado.
- **Notificações** (desligadas por omissão): Telegram, Discord, Slack, Matrix, MQTT e um endereço HTTP local, um limite por hora, um botão de teste e um contrato de adaptadores documentado (`monitor/docs/schemas/notification_event.schema.json`).
- **Assistente de IA**: novos fornecedores `anthropic` (API Messages, o modelo é à sua escolha) e `copilot` (`gh copilot` com o seu próprio acesso, só texto, sem ferramentas); tarefas novas (relatório diário, notas de versão, uma pergunta sobre um repositório); definições para os tipos de evento, os repositórios, o idioma e os limites, um botão de teste e o uso do dia. Uma lista fechada de ações (`gh run rerun`, `gh issue close`, `act`), só PROPOSTAS por omissão.
- **Os números do cabeçalho são cartões** com um ícone, um número grande e uma etiqueta pequena, coloridos conforme o estado, com dica, um clique que leva ao separador, números que contam e um esqueleto que mostra logo os últimos valores conhecidos; a segunda linha (repositórios, quentes, modo, leituras poupadas, quota do GitHub com uma barra e contagem decrescente em direto, ligação, última atualização e progresso do carregamento) também é feita de cartões.
- **Vista de terminal**: `tui.py` desenha uma grelha em direto na consola (só leitura, opcional, precisa do pacote `rich`; o monitor e os seus testes não precisam de nenhum pacote).
- **Para servidores e contas grandes**: `GET /api/health`, `GH_HOST` para o GitHub Enterprise Server (todas as ligações da página o seguem), `discover_limit`, permissões mínimas por funcionalidade e um guia para o executar como serviço (systemd, launchd, uma tarefa agendada, um contentor) e atrás de um proxy inverso.
- Esquemas JSON publicados de `ci_red.json`, da exportação pública e do evento de notificação (`monitor/docs/schemas`), e um roteiro público (`docs/ROADMAP.md`).
- Guias novos em oito idiomas: notificações, o assistente de IA, análise, ferramentas de consola e implementação; o guia do webhook cobre os eventos em tempo real. Todas as capturas foram refeitas (claro e escuro, ferramentas de consola incluídas) com `tools/make_screenshots.py` e dados inventados.

### Alterado

- **Definições**: novos subseparadores para leituras e cache, notificações, análise, o linter e a vista de terminal; os subseparadores de IA e webhook têm todas as suas opções.

### Corrigido

- **O linter já não dá falsos alarmes com marcadores de posição**: um valor que parece um segredo é classificado (um formato de token conhecido ou uma cadeia longa de alta entropia é grave, um preenchimento legível como `placeholder` ou `changeme` é só informação, tudo o resto um aviso; as referências e os valores vazios não são achado) e o seu valor nunca é impresso nem guardado.
- **Um navegador que fecha ou recarrega o seu separador enquanto a página carrega já não imprime um traceback** (`ConnectionAbortedError`, `ConnectionResetError`, `BrokenPipeError`): são contados em `ghamon_client_disconnects_total`; um erro real continua a ser mostrado.

### Segurança

- O webhook de entrada continua desligado por omissão, em `127.0.0.1`, com HMAC obrigatório.
- Os segredos das notificações vivem só em variáveis de ambiente; os anfitriões são fixos; as notificações nunca escrevem no GitHub.
- Ações da IA: executar uma precisa do seu próprio interruptor e de uma confirmação do comando completo de cada vez, só sobre alvos que o monitor já vigia, com um limite por hora, um registo local e um bloqueio após duas falhas seguidas.

## [1.5.2]

### Adicionado

- **O separador Definições está organizado em subseparadores**, ordenados do comum ao avançado (Este navegador, Geral, Atualização e limites, Sentinela, Verificações de superfície A10, Prontidão A11, Pastas e ficheiros, Saídas, IA externa, Webhook de entrada). Dentro de um subseparador, as definições estão em blocos com título cujo primeiro campo é o interruptor principal (o resto do bloco esbate-se enquanto está desligado). Cada campo mostra a sua unidade e intervalo, um emblema (precisa de reinício / aplica-se já), um emblema para as opções de segurança que arrancam no estado conservador e uma linha de ajuda. Uma caixa de pesquisa filtra todos os subseparadores, cada subseparador conta as suas alterações por guardar, Guardar e Descartar ficam visíveis, as setas, Início e Fim movem-se entre os separadores e o navegador recorda o último subseparador usado.
- **Todas as definições do ficheiro de configuração estão agora na página**: as verificações A10 (um interruptor por verificação e os seus limites), os pesos da pontuação de saúde do ecossistema, as fontes das versões fixadas, os tetos de minutos do Actions, os ficheiros obrigatórios, os padrões dos ficheiros de auditoria, o período quente da sentinela, a regra da amostra desconhecida de A2, os prefixos de candidatos, a lista de repositórios e o interruptor do webhook de entrada.
- **Fila de assinatura por confiança**: cada linha diz `verified`, `unknown` ou `failed`; o separador Sentinela tem um filtro de Assinatura com a contagem de cada tipo; `read_report.py --sign-trust` filtra a lista da consola e a exportação, e as linhas exportadas levam `trust`.
- **Emblemas de prontidão no cabeçalho**: um emblema colorido por ecossistema com a sua pontuação de saúde.
- **Um painel Grafana mínimo** (`red_by_ecosystem.json`) e um teste que verifica cada métrica de ambos os painéis contra o que `/metrics` serve.
- Guia novo `WEBHOOK` (modo só atualizar) e um exemplo comentado das fontes de fixação, em oito idiomas.
- `tools/make_settings_doc.py` escreve a tabela de definições dos guias a partir do esquema e dos textos da página, e a CI verifica-a.

### Alterado

- **O relatório diário agrupa as sugestões de fecho de issues** numa linha por repositório (o monitor continua a não fechar nada).
- **O contrato do painel do perfil** está documentado e verificado por um teste (`/api/outputs/dashboard.json` é exatamente o documento de `ci_red.json`; a exportação pública nunca leva o lado da assinatura).

### Segurança

- O segredo partilhado do webhook nunca é mostrado na página: só diz se está definido.

## [1.5.1]

### Adicionado

- **A página de definições pode configurar a IA externa da sentinela** (grupo «IA externa para a sentinela»): `ai.provider` (`none` / `ollama` / `openai-compatible`), `ai.model`, `ai.ollama_url` (só este computador), `ai.base_url` (só https), `ai.api_key_env` e `ai.daily_limit`. Desligada por omissão; um serviço externo recebe dados dos seus repositórios.
- **`migrate_state.py`**: leva para os nomes novos os ficheiros escritos antes da 1.5.0 (eventos, histórico de relatórios, candidatos a versão, registos de lotes, a definição `report_history_days`). Por omissão é um ensaio; `--apply` copia e mantém os antigos, `--move` renomeia-os; nada do que existe é sobrescrito. Guia de uma página em `docs/MIGRATING.md`, em oito idiomas.
- **`--init-catalog`** cria `ecosystems.json`, `targets.json` e `profiles.json` editáveis a partir dos exemplos.
- Um teste garante que nenhum documento manda o leitor para um comando que foi renomeado na 1.5.0 (só as tabelas de nomes antigos e novos e os guias de migração os podem nomear).
- A versão em cada README.

### Alterado

- **Primeiro arranque sem ficheiros de catálogo próprios**: a consola diz que se usam os ficheiros de exemplo.
- O Python 3.11 ou posterior é o mínimo documentado (testado em 3.11 e 3.13 no Windows, Linux e macOS).

### Segurança

- Só se pode indicar o NOME da variável de ambiente que guarda a chave da IA: a chave em si nunca é mostrada nem guardada.

## [1.5.0]

**Aviso de atualização (leia primeiro).** Vários ficheiros e definições têm agora nomes em inglês. Nada se perde: os nomes antigos continuam a ser LIDOS onde possa existir um ficheiro escrito por uma versão anterior, e os nomes novos são os únicos escritos.

| Antes da 1.5.0 | Desde a 1.5.0 |
|---|---|
| `leer_parte.py` | `read_report.py` |
| `eventos.py` | `events.py` |
| `parte_history.py` | `report_history.py` |
| `LOTE_GITHUB_ACTIONS.bat` / `.sh` / `.command` | `BATCH_GITHUB_ACTIONS.bat` / `.sh` / `.command` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` (copie-os ou renomeie-os para guardar o histórico de eventos) |
| `PARTE_CENTINELA_DIA_<day>.txt/.json` (histórico de relatórios) | `SENTINEL_REPORT_DAY_<day>.txt/.json` (os antigos continuam a ser lidos) |
| `PARTE_CENTINELA_<time>.txt` (relatório guardado) | `SENTINEL_REPORT_<time>.txt` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_<time>.json` | `<signed_dir>/batches/batch_<time>.json` (os registos antigos continuam a ser lidos) |
| `parte_history_days` (definição) | `report_history_days` (o nome antigo continua a ser lido) |
| `monitor_y_centinela.zip` e pasta | `github_actions_monitor.zip` e pasta; `LEEME_CORREO.txt` passa a `README_MAIL.txt` |
| A8 procurava `RECONCILIACION_TOTAL_AUDITORIAS_*.txt`, `MAPA_DE_RONDAS_*` | os nomes são `sentinel.audit_files` (valores neutros por omissão `RECONCILIATION_TOTAL_*.txt`, `ROUNDS_MAP_2*.txt`, `ROUNDS_MAP_EXTRA_*.txt`); ponha aí os seus |
| `ci_red.json`, o seu esquema e os ficheiros de `--export-status` | sem alterações (são um contrato) |

- **Inglês por omissão.** O idioma do sistema deixa de decidir: as ferramentas arrancam em inglês até escolher outro no separador Definições, com `language` em `actions_monitor.json`, `MONITOR_LANG` ou `--lang`.
- **Um pacote limpo e neutro.** `ecosystems.json`, `targets.json` e `profiles.json` deixam de fazer parte do pacote: só viajam os ficheiros `*.example.json`, e um ficheiro por omissão em falta recorre ao seu exemplo. Os seus próprios ficheiros ficam onde quiser e são indicados por `ecosystems_file`, `targets_file` e o novo `profiles_file`; a pasta das suas ferramentas de assinatura locais é o novo `tools_dir`. Os testes usam os seus próprios dados (`tests/fixtures`).
- **Separador Definições.** Um separador novo altera os valores de `actions_monitor.json` a partir da página: uma lista branca de chaves com tipo e intervalo, um pedido recusado por inteiro quando um valor é inválido, uma cópia do ficheiro anterior em `config_backups/` antes de cada gravação (guardam-se as dez últimas), uma escrita atómica, só em 127.0.0.1 com as mesmas verificações de Host e Origin de qualquer outro endpoint, só JSON. Os tokens, segredos, chaves de assinatura e o comando da sentinela não estão na lista: nunca são mostrados nem escritos, e as outras chaves do ficheiro mantêm-se como estavam. Cada definição diz se precisa de reinício. O seletor de idioma, o tema e a vista densa mudaram para lá.
- **Botões e ícones.** Os botões têm relevo, acendem-se ao passar o rato e afundam-se ao premir; os botões de ícone são SVG em linha com nome acessível e dica nos 8 idiomas. As cores, a tipografia, os cartões, as barras e o anel seguem o painel de estado do repositório do perfil.
- **Vida nos gráficos.** As barras crescem ao aparecer, o que está a vermelho ou em curso tem uma pulsação discreta, os números do cabeçalho contam para cima, passar sobre uma barra destaca-a e dá o seu texto como dica, as larguras mudam suavemente; tudo pára com `prefers-reduced-motion`.
- **Saídas para outras ferramentas (desligadas por omissão, só 127.0.0.1, sem token novo).** `/metrics` em formato Prometheus (workflows a vermelho por ecossistema e repositório, séries e horas a vermelho, compilações à espera de assinatura, A10 em pausa, quota restante, instantâneo incompleto...), `/api/outputs/grafana.json` para a fonte JSON / Infinity do Grafana e `/api/outputs/dashboard.json` (o documento `ci_red.json`) para o painel de estado. Um painel Grafana importável está em `docs/grafana/` e os detalhes em `docs/OUTPUTS.md`.
- **Relatório:** uma linha (código `tag_vs_manifest`) quando uma etiqueta de versão está à frente da versão do manifesto; o número de não assinados é ordenado pela espera mais longa e diz quanto é; o painel do repositório sugere o comando `gh issue close` (nunca executado) para uma issue de falha cujo workflow voltou a verde; o perfil de lote `hil` está documentado em `profiles.example.json`; testes de `finalize` e de `monitor_link`.
- **Documentos:** `docs/SETTINGS.md`, `docs/OUTPUTS.md`, README e QUICKSTART nos 8 idiomas atualizados, capturas feitas com repositórios inventados.

## [1.4.5]

- **O relatório diz quando o instantâneo está incompleto:** uma linha com o código estável `incomplete` (ainda a carregar, sem espaço de trabalho local, erros ao ler) logo a seguir ao título, para que ninguém aja sobre uma lista lida a meio de repositórios a vermelho ou da fila de assinatura.
- **Resumo de assinatura:** uma linha com quantas versões esperam para ser assinadas (verificadas / por verificar / com a verificação falhada) e quantas compilações são só de compilação de propósito, para não confundir «não assinado de propósito» com «falta a assinatura» (código `sign_summary`).
- **A10 em pausa por causa da quota é dito no relatório** (código `a10_paused`) com a quota restante e a necessária, e os três comandos que a controlam.
- Textos nos 8 idiomas; testes das três linhas.

## [1.4.4]

- **O autor e a licença estão sempre visíveis:** o painel web tem um rodapé com o autor e a licença, `read_report.py --version` e o novo `gha_dispatch_all.py --version` imprimem-nos sob a versão, e o monitor imprime a mesma linha ao arrancar. O texto está nos 8 idiomas (`ui.about`); o autor e a licença vêm de `tool_version.py`.
- **A ponte para o painel, por escrito:** `docs/CI_RED_BRIDGE.md` diz o que contém `ci_red.json` (esquema 2, `complete`), como exportá-lo e o que um leitor deve verificar; o monitor continua a não enviar nem confirmar nada.
- Testes da linha do autor nos 8 idiomas, do rodapé, de ambos os indicadores `--version` e da linha de arranque.

## [1.4.3]

- **Um workflow que só corre em pull requests já não torna o A2 inconclusivo:** `pull_request` e `pull_request_target` juntam-se aos eventos cujas execuções nunca estão no ramo predefinido (como `workflow_dispatch`, `release` e `workflow_call`), pelo que a um workflow como uma verificação de integração de contrato que só corre em pull requests não se pede uma última execução em main. Um workflow que também tem `push` ou `schedule` continua a contar. Testes dos dois casos.

## [1.4.2]

- **O A2 já não conta como vista uma execução em curso ou cancelada:** ao resolver um workflow escondido, a sentinela pede agora as últimas execuções concluídas desse workflow no ramo predefinido (`gh run list -w <ficheiro> --branch <predefinido> --status completed -L 10`, só leitura) e usa a primeira com uma conclusão real. Uma execução cancelada ou ignorada (e qualquer uma sem conclusão) é ignorada, pelo que já não pode esconder um vermelho anterior; um workflow sem execução concluída com conclusão no ramo continua inconclusivo por si só. Mesma porta de quota, mesmo limite de chamadas e mesma cache de antes.

## [1.4.1]

- **O A2 resolve um workflow escondido em vez de desistir de todo o repositório:** quando um repositório tem uma amostra completa de execuções e lhe falta um workflow do seu clone (um que pode correr no ramo predefinido), a sentinela pergunta ao GitHub pela última execução DESSE workflow no ramo predefinido (`gh run list -w <ficheiro> --branch <predefinido> -L 1`, só leitura). Uma resposta a vermelho conta como vermelho no A2; uma a verde tira o workflow da lista de inconclusivos; um workflow sem execução no ramo continua inconclusivo por si só e o painel nomeia-o (`repo/ficheiro.yml (sem execução no ramo predefinido)`) em vez de nomear só o repositório. Sem quota (a mesma porta do A10: `min_rate_remaining` x `surface.min_rate_factor`, mais o orçamento por hora) o workflow continua inconclusivo e o painel diz porquê. Opções novas `sentinel.a2_resolve_max_calls_per_tick` (4; 0 = nunca perguntar) e `sentinel.a2_resolve_ttl_seconds` (3600, quanto tempo se guarda uma resposta; também fica no ficheiro de cache). O instantâneo leva `a2.inconclusive_workflows` (etiquetas) e `a2.inconclusive_details`; `a2.inconclusive` continua a ser a lista de repositórios. 5 textos novos nos 8 idiomas e um `ui.a2_inconclusive` reformulado.

## [1.4.0]

- **Camada nova A11 «Prontidão» (só leitura, só dados reais):** um painel do separador Sentinela, um semáforo no seu cabeçalho e duas linhas do relatório. Liga-se com `sentinel.readiness.enabled` e descreve-se em `readiness.py`.
  - **Prontidão da versão:** uma linha por repositório com pelo menos `candidate_min_entries` entradas em `[Unreleased]` (sem os ecossistemas externos): a CI do ramo predefinido (a regra única do A2) com o commit em que correu, se a versão que o clone declara (`*.project.json`, senão `pyproject.toml`, senão o primeiro cabeçalho do CHANGELOG) já está acima da última versão publicada, se existe uma compilação posterior a essa versão, se está assinada (os estados do A5) e o passo seguinte (`corrigir a CI a vermelho`, `esperar por dados de execução`, `subir a versão`, `compilar no Actions`, `assinar`, `publicar`, `cortar e publicar`). Uma CI a verde sobre uma amostra de execuções completa que pode esconder um workflow mais antigo di-lo.
  - **Saúde do ecossistema:** por ecossistema, 100 menos as contagens ponderadas de CI a vermelho, compilações presas, segredos, alertas graves, outros alertas, PRs do Dependabot mais antigas que `stale_pr_days`, compilações à espera de assinatura e repositórios com problemas de higiene (`sentinel.readiness.health.weights`); listam-se as partes que baixam a pontuação. Não se mostra pontuação (`?`) quando menos de `min_coverage` (0,5) dos repositórios do ecossistema têm dados de execução e alertas. O relatório avisa quando uma pontuação está abaixo de `warn_below` (70).
  - **Fixações de dependências:** repositórios que fixam uma versão mais antiga do que a do repositório que fornece o contrato ou a biblioteca. Onde vivem as fixações é um dado (`sentinel.readiness.pins.sources`): uma tabela JSON de fixações no fornecedor (`pin_table`) ou ficheiros de bloqueio nos consumidores (`lock_files`, conta o mais antigo encontrado). Leituras simples de ficheiros dos clones locais, em cache `pins.refresh_seconds`; um ecossistema sem fonte configurada é listado como sem nenhuma, e nada se adivinha. O exemplo incluído não tem fonte.
  - 60 textos novos nos 8 idiomas; `tests/test_readiness.py` (regras, pesos, cobertura, fixações numa árvore temporária, a página e os 8 catálogos).
- **`docs/CI_RED_SCHEMA.md`:** diz expressamente que o PC não publica nem `ci_red.json` nem `pending_sign` em nenhum repositório ou painel (o lado da assinatura é local por decisão); um consumidor público recalcula a regra a partir das execuções públicas ou usa `read_report.py --export-status`.
- **Ajuste da quota a partir do registo (`actions_monitor_log.txt`, 3 dias, 889 amostras):** a quota partilhada esteve abaixo do mínimo (`min_rate_remaining` 1500) em 11 % das amostras desde 5 de novembro e abaixo de 3000 em 45 %; o gasto por hora foi de 3000-5000 chamadas na maioria das horas e chegou ao limite em algumas. No `actions_monitor.json` do mantenedor: `refresh_seconds` 120 -> 180 (o ciclo real tinha uma mediana de 139 s) e `sentinel.surface.min_rate_factor` 2,0 -> 1,5 (as chamadas a frio do A10 são cerca de 260 por dia, pelo que podem correr acima de 2250; com 3000 esperavam quase metade do tempo). `max_repos_per_tick` (6) e o ciclo diário a frio mantêm-se: custam menos de 1 % da quota. O exemplo incluído mantém os seus valores neutros.

## [1.3.3]

- **O A2 ignora os workflows que nunca correm no ramo predefinido:** ao decidir se uma amostra completa de execuções esconde um workflow, os ficheiros do clone cujo `on:` não tem `push`, `pull_request` nem `schedule` para o ramo (só `workflow_dispatch`, `release`, `push` só de etiquetas sem `branches`, ou `workflow_call`) deixam de ser esperados na amostra. O `on:` é lido só com a biblioteca padrão (cadeia, lista, mapa e a chave YAML `true`); se não puder ser interpretado, o workflow conta como antes. A análise dos workflows leva o campo novo `main_triggered` (`true`/`false`/`null`).

## [1.3.2]

- **O A2 mostra `unknown` em vez de verde quando a sua amostra está cheia e é inconclusiva:** um repositório cuja lista de execuções é tão longa como a amostra pedida (`runs_per_repo` / `cold_runs_per_repo` do monitor, que a verificação antes não via) e cujo clone tem um ficheiro de workflow sem execução nessa amostra (ou não tem clone) é listado como inconclusivo, e o A2 é `unknown` a não ser que algo esteja a vermelho. Opção nova `sentinel.a2_full_sample_unknown` (por omissão `true`; `false` = só informativa como antes). A página lista os repositórios.
- **`profiles.example.json`:** um modelo neutro de perfis de lote que corresponde a `targets.example.json` e `ecosystems.example.json`. Um teste (e a porta da versão) valida-o contra esses catálogos, não os do mantenedor, e verifica que cada perfil seleciona pelo menos um destino.
- **Verificação de instalação limpa em `make_release`:** antes de deixar o que quer que seja na pasta de saída, o zip é extraído para um diretório temporário novo e vazio e, a partir daí com `python -I`, cada membro tem de estar presente, cada módulo compilar, `read_report.py --version` funcionar e toda a suite passar; qualquer falha faz falhar a versão.
- **Redação:** README e QUICKSTART nos 8 idiomas dizem agora que o pacote não escreve nada no GitHub por si só e que apenas `dispatch --go`, `dispatch --real` e `finalize --execute` (que você executa) o fazem.
- **Quota do A10:** a parte do orçamento de chamadas por ciclo da sentinela que o A10 pode usar é agora `sentinel.surface.budget_share` (por omissão `0.5`, como antes mas configurável); a página mostra «A10 em pausa por causa da quota» com a quota restante e a necessária (`min_rate_remaining` x `min_rate_factor`) enquanto as chamadas a frio esperam.

## [1.3.1]

- **Uma execução construída sobre outro commit nunca é oferecida para assinar:** quando o `dispatch` só encontrou uma execução recente de outro commit (`sha_matched` falso), o `finalize` lista-a agora como não pronta com o motivo e não dá nenhum comando de assinatura; um lote antigo sem o campo comporta-se como antes. Testes com duas execuções concorrentes de commits diferentes.
- **`/api/data` passa pela mesma guarda de Host/Origin que as outras rotas** do servidor local (DNS rebinding).

## [1.3.0]

Feita para ser partilhada: oito idiomas, autoria e licença em cada ficheiro, nenhum dado privado e nada preso a uma conta do GitHub.

- **8 idiomas** (en, es, de, fr, it, ja, zh, pt = português de Portugal) para a página, as ferramentas de linha de comandos, os lançadores, os eventos, os relatórios e as mensagens de erro. `i18n.py` + `locales/<idioma>.json` (um catálogo plano por idioma, só biblioteca padrão, `t("chave", nome=valor)` com recurso ao inglês). O idioma é `language` em `actions_monitor.json` (por omissão: o idioma do sistema, inglês se não for suportado), um seletor no cabeçalho da página (o navegador recorda-o), `MONITOR_LANG` / `JUANENRAC_LANG`, ou `--lang CÓDIGO` em cada ferramenta (prevalece sobre o resto). Os nomes técnicos, comandos, caminhos e os marcadores que os scripts leem (`SKIP`, `DISPATCHED`, `READY`, `FAILED`, `Summary:`, `BUILD ONLY`, `WOULD DISPATCH`...) nunca se traduzem. Os eventos de `events_monitor.jsonl` levam agora um `code` estável (e `args`) junto ao texto, para que ninguém tenha de analisar um idioma.
- Um teste verifica que os 8 catálogos têm exatamente as mesmas chaves, nenhuma vazia, os mesmos `{marcadores}`, que cada chave usada pelo código e pela página existe e que nenhum texto visível do código contorna `t()`.
- README e QUICKSTART nos 8 idiomas (`README_<idioma>.txt`, `QUICKSTART_<idioma>.txt`); `README.txt` é agora um seletor de idioma curto com o arranque rápido.
- **Autoria e licença**: cada ficheiro de código leva «Copyright (C) 2026 JuanenRac (Electro Hobby 3D)» e «GPL-3.0-or-later - see LICENSE»; os ficheiros de dados JSON levam `_author` / `_license`; `LICENSE` (texto da GPL-3.0), `NOTICE` e `AUTHORS` viajam no zip. O `make_release.py` recusa-se a construir quando a um ficheiro faltam, quando viajariam dados privados, quando os locales diferem ou quando um lançador perde o bit de execução.
- **Partilhável**: `github_owner` na configuração (por omissão: a conta do `gh`) substitui a constante que estava espalhada por três módulos; os prefixos de ecossistema e as ferramentas de assinatura são dados (`ecosystems.json`, neutro `ecosystems.example.json`; `"*"` = todos os repositórios; `"external": true` = só se reporta) e os destinos também (`targets.json` é o catálogo real do mantenedor, `targets.example.json` o neutro; `targets_file` / `ecosystems_file` escolhem-nos; as chaves que começam por `_` são metadados). A configuração de exemplo é neutra. Nada disto acrescenta uma chamada ao ciclo quente.
- **O espaço de trabalho é opcional**: sem clones locais o monitor arranca em modo reduzido (só o que dá a API do GitHub: sem fila de assinatura local, sem relatório de auditorias, sem análise do CHANGELOG) e di-lo na página, no relatório e ao arrancar, em vez de parar. `MONITOR_ROOT` / `MONITOR_AUDIT_DIR` / `MONITOR_SIGNED_DIR` e `signed_dir` foram acrescentados ao lado dos nomes antigos. A camada do roteiro (A9) também é opcional.
- Lançadores: os menus e mensagens vêm de `launcher_msg.py` (o seu idioma); comentários em inglês; cabeçalho em cada ficheiro.
- Correção: `workspace_root()` já não termina o monitor quando a sentinela arranca sem espaço de trabalho.

## [1.2.0]

O que faltava e o que mais se pode fazer no GitHub, tudo só de leitura e local.

**Parte A - o que faltava**
- O esquema 2 de `ci_red.json` é agora um contrato documentado: `docs/CI_RED_SCHEMA.md` (forma, a regra única do «vermelho», o que é só do proprietário). Não se publica nada a partir do PC. Exportações opcionais e explícitas (nunca um commit nem um push): `read_report.py --export-status DIR` escreve SÓ a lista a vermelho (`ci_status_public.json/.md`); `read_report.py --export-sign-queue FILE` (.json/.csv) escreve a fila de assinatura global com os comandos locais.
- Atestação: a fila de assinatura mostra se a compilação tem uma atestação (existência por resumo dos ficheiros assinados, uma consulta por entrada, sem verificação de assinatura; interruptor `sentinel.surface.checks.attestation`). Uma em falta é uma linha do relatório.
- Mais formatos verificados: HYDRA `hydra-sign` (`FICHEIRO.sig` = Ed25519 em base64 sobre os bytes do ficheiro, a chave de versão fixada, lido por blocos) é verificado de forma definitiva; URTC `.imgsig` tem o formato estrito verificado (152 dígitos hexadecimais + LF; mal formado = inválido) e fica «unknown» quando está bem formado (a mensagem assinada também precisa do cabeçalho da compilação, que a pasta de assinados não leva); os APK do ARMOR são assinados dentro do APK pelo apksigner e ficam «unknown».
- `HYDRA-UMC-OS` é etiquetado de propósito em `targets.json` (`"build_only": true` + `reason`): `plan` lista-o em BUILD ONLY e já não é órfão. As ferramentas de assinatura não foram tocadas (o seu workflow recebe outras entradas e um esquema de assinatura diferente).
- Correção: `ci_red.target_path` recusava todos os caminhos do Windows escritos com barras invertidas (`C:\...`); só se aceitavam barras normais.

**Parte B - a camada A10 «superfície de Actions e versões»** (`surface.py`, secção nova do separador, um interruptor e um limiar por verificação em `sentinel.surface`)
- Actions: workflows desativados à mão, agendamentos sem execução há N dias (só quando a amostra de execuções cobre a janela), `uses:` não fixados por SHA (os workflows reutilizáveis assinalados à parte), `permissions: write-all`, `pull_request_target` com checkout da PR, filas de concorrência presas, falhas num só SO de uma matriz, custo e retenção de artefactos, verificações de estado obrigatórias a vermelho ou em falta (GraphQL), `dispatch --profile release|nightly|hil` com um canário (só o primeiro destino, os restantes só se estiver a verde) e uma porta de quota (`--min-rate`, falha fechada). Os perfis vivem em `profiles.json`.
- Versões: ativos esperados por tipo de destino (alerta quando uma versão foi publicada incompleta), etiqueta contra manifesto contra CHANGELOG, GitHub Packages, rascunhos e pré-versões esquecidos, `release_notes.py` (um RASCUNHO de notas a partir dos commits desde a última etiqueta; não publica nada).
- Segurança: alertas críticos/altos por antiguidade com um ranking de repositórios, cobertura (uma pilha sem CodeQL/Dependabot), análise de segredos abertos contra resolvidos, Dependabot por prioridade (primeiro as maiores de runtime, no fim as só de CI).
- Issues e PRs: sugestão de `gh issue close` para issues de compilação cuja CI voltou a verde (um evento com o texto; nunca se fecha nada), marcos em atraso, PRs humanas antigas, PRs que tocam workflows ou CODEOWNERS, a fila de fusão (aprovadas com verificações a verde). Cartões de quadro obsoletos: PENDENTE (precisa de leituras por elemento e de um limiar).
- Manifesto contra evidência (maturidade), falhas de paridade do README em 8 idiomas, minutos do Actions por ecossistema no cabeçalho, no relatório e no A7.
- `finalize --execute` diz agora ao monitor em execução (127.0.0.1) para atualizar só os repositórios assinados e reescrever `ci_red.json` de imediato (`monitor_link.py`).
- Recetor opcional de webhook assinado (`webhook.enabled`, desligado por omissão, só 127.0.0.1, HMAC com um segredo partilhado da configuração, nunca um token do GitHub).
- Custo: nada no ciclo quente. A frio, repartido por ciclos e dentro do orçamento por hora: 2 chamadas REST por repositório e dia, uma consulta GraphQL por cada 15 repositórios e dia, 3 para o Packages, mais os jobs das execuções a vermelho e as consultas de atestação da fila de assinatura, e só enquanto a quota estiver acima do dobro de `min_rate_remaining`. A passagem GraphQL quente pede mais 3 campos por nó (datas de alertas, decisão de revisão, estado das verificações): sem chamadas extra.
- A porta também compara `sentinel.surface` do ficheiro de exemplo com os valores por omissão e valida `profiles.json`.

## [1.1.1]

- **Multiplataforma:** o monitor e as ferramentas de lotes funcionam em Windows, macOS e Linux. Lançadores `MONITOR_GITHUB_ACTIONS.sh`/`.command` e `BATCH_GITHUB_ACTIONS.sh`/`.command` (o zip conserva a permissão de execução e o make_release rejeita os fins de linha do Windows neles).
- Novo `platform_compat.py`: o comando que arranca uma ferramenta filha (`py -3` no Windows, o interpretador atual nos outros), o texto dos comandos que o `finalize` mostra (aspas de cmd/PowerShell ou POSIX), consola UTF-8 e um aviso com a forma de instalar o `gh` em cada sistema.
- Testes novos da parte multiplataforma (Windows e POSIX simulados a partir de qualquer sistema).

## [1.1.0]

Confiança nas assinaturas, uma ponte estável para o painel, órfãos e convenções nas ferramentas de lotes, e uma página mais útil.

- Confiança na assinatura: `sigverify.py` (biblioteca padrão, só leitura, sem rede) verifica a pasta de assinados `_firmados/<REPO>/release-<versão>/` contra a chave PÚBLICA que cada ecossistema fixa (URTC `release_sign.py`, o auxiliar do ARMOR `PACKAGE_PUBLIC_KEY`, o atualizador do HYDRA `RELEASES_PUBLIC_KEY`, ou `sentinel.signature_pubkeys`). Cada estado leva agora `signature_kind` (none | dev | release) e `signature_verified` (true | false | "unknown"); só uma assinatura de versão que se verifica (`trusted`) baixa o alerta de assinatura pendente, além de «publicado». Uma assinatura que não se verifica mantém o alerta e di-lo no relatório. `sentinel.require_verified_signature` (por omissão true; false = a regra da 1.0.0). Os formatos que este módulo não pode verificar (.sig2, .hdr2, .imgsig, APK, hydra-sign) são «unknown», nunca «false». A atestação da compilação continua a precisar da rede e fica com as ferramentas de assinatura.
- Esquema 2 de `ci_red.json`: por repositório uma lista `pending_sign` (workflow, horas, estado, signature_kind, signature_verified, last_build_at, url) junto aos workflows a vermelho, mais `schema`, `pending_sign_repos` e o limiar; o formato está documentado em `ci_red.py` e só é alargado.
- Uma definição de «última execução em main» (`signstate.completed_runs`) partilhada pela verificação do vermelho, pela do verde sem versão e pelos estados dos destinos.
- `ci_red.target_path` recusa caminhos de D:, as formas WSL/Git Bash de D: e caminhos de unidade/UNC que o sistema em execução não pode usar; os testes simulam ambos os sistemas e toda a suite passa agora em Linux.
- `gha_dispatch_all.py plan` termina sempre com a secção «Órfãos de assinatura» (CI a verde + `*-build.yml` conhecido + sem destino); a cobertura é por repositório E workflow.
- Convenção para os destinos (prefixo do ecossistema -> ferramenta de assinatura por omissão, workflow na lista conhecida); `targets.json` só tem as exceções e ganha sempre. `hygiene --write-candidates` escreve as entradas propostas em `targets.candidates.json` (nunca aplicadas sozinhas, nunca empacotadas).
- Página: contadores de cabeçalho clicáveis «vermelho em main» e «não assinados» (filtram os repositórios; o segundo também foca a fila de assinatura), a fila de assinatura com os seus comandos e um botão de copiar, painel do repositório com compilado / assinado / publicado, tipo de assinatura e verificação, e o comando sugerido; um emblema no cabeçalho quando um orçamento de minutos chega aos 80 % (vermelho ao ser excedido); «ontem contra hoje» também compara os avisos de orçamento e as linhas do relatório.

Não feito: ler a atestação da compilação / SBOM (rede); `HYDRA-UMC-OS` tem um workflow de compilação mas a sua ferramenta de assinatura ainda não o suporta (listado como órfão).

## [1.0.0]

Primeira versão numerada. O que o pacote faz:

- Monitor do GitHub Actions para os quatro ecossistemas (página web local, cache de execuções, compilações presas, issues de build-failed/build-stuck).
- Camada A da sentinela (só leitura, sem IA): A1 compilações presas, A2 CI a vermelho (um único critério: a última execução concluída de cada workflow no ramo predefinido), A3 alertas de CodeQL/Dependabot/segredos, A4 pull requests do Dependabot, A5 versões (candidatas, compilações a verde sem versão, assinatura pendente), A6 higiene, A7 consumo (minutos e quota da API), A8 auditorias e rondas, A9 quadros do roteiro.
- Estado explícito de cada destino de compilação: built_on_gha -> signed_local (none | dev | release) -> published, com `last_build_at`, `last_signed_at`, `signature_kind` e as horas reais de espera; os registos locais de lotes e da pasta de assinados baixam o alerta de assinatura pendente sem esperar pelo GitHub.
- Fila de assinatura do dia (`a5.sign_queue`): o mais urgente primeiro, com o comando finalize exato de cada destino.
- Orçamento de minutos do Actions por ecossistema (`sentinel.minutes_budget`, vazio por omissão): aviso aos 80 % no relatório e como evento.
- Fluxo de eventos (`events_monitor.jsonl`) e `ci_red.json` (repositório -> workflows a vermelho + horas à espera de assinatura), escritos de forma atómica.
- Ferramentas de lotes: `gha_dispatch_all.py plan|dispatch|status|finalize|hygiene` com `--only` ou `--ecosystem`, `plan --json`, `finalize --json`, uma nova tentativa de um dispatch falhado no fim do lote, destinos como dados em `targets.json`.
- `read_report.py`: o relatório em texto simples a partir do monitor em execução, sem gastar quota da API.
- `make_release.py`: porta de qualidade (testes unitários, zip limpo, configuração de exemplo completa, acordo versão/changelog) e SHA256SUMS.

Não feito nesta versão: verificar as assinaturas das versões contra a chave pública e a atestação da compilação a partir da sentinela (formatos de assinatura diferentes por ecossistema; a atestação precisa da rede; as ferramentas de assinatura verificam ambas antes de publicar).

