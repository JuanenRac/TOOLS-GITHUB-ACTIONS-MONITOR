Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE

MONITOR DO GITHUB ACTIONS + SENTINELA (versão 1.7.2)
====================================================
QUAL ARRANCAR? (um utilizador novo decide em dois minutos)
  COMPLETA  MONITOR_GITHUB_ACTIONS.*       a página com a sentinela (porta 8765): alertas, fila de assinatura, análise. Comece aqui se tem vários repositórios.
  LITE      MONITOR_LITE_GITHUB_ACTIONS.*  a mesma página sem sentinela (porta 8766): o que está a vermelho, preso ou a correr. Mais leve; convive com a completa.
  LOTES     BATCH_GITHUB_ACTIONS.*         só se assina e publica as suas próprias builds.
  TERMINAL  python tui_textual.py (acrescente --lite para a edição lite)   a aplicação interativa de terminal; tui.py --once imprime um ecrã.
  VERIFICAR python actions_monitor.py --doctor (--json para scripts)   diz o que falta e o comando exato que o resolve.
  EXPERIMENTAR python actions_monitor.py --demo   a página com dados inventados: sem gh, sem sessão, nada seu é tocado.

Requisitos: Python 3.11+ e o GitHub CLI (`gh`) com a sessão iniciada (gh auth login). Mais nada: o núcleo não precisa de pacotes (a vista de consola, tui.py, usa o pacote opcional rich).
Passos rápidos para a primeira utilização: QUICKSTART_pt.txt.

ARRANQUE   Windows: MONITOR_GITHUB_ACTIONS.bat | Linux: ./MONITOR_GITHUB_ACTIONS.sh | macOS: duplo clique em MONITOR_GITHUB_ACTIONS.command
           (abre http://127.0.0.1:<porta>, apenas local). Em qualquer sistema também serve:  python3 actions_monitor.py  (Windows: py -3 actions_monitor.py)
LOTES      BATCH_GITHUB_ACTIONS.bat / .sh / .command  (gha_dispatch_all.py: plan, dispatch, status, finalize, hygiene). Opcional, para quem assina as suas builds localmente.
O QUE NUNCA FAZ   Só escuta em 127.0.0.1, a menos que ligue o modo rede (Definições > Avançado: um endereço privado, um token de acesso em cada pedido e um aviso na página). Não guarda nenhum token (pede-o ao `gh`), a menos que ligue o token opcional guardado no cofre seguro do sistema. Por si só não escreve nada no GitHub: apenas os comandos de lote `dispatch --go`, `dispatch --real` e `finalize --execute` escrevem no GitHub (lançam workflows, criam o rascunho por assinar, publicam), e só quando os executa.
           NÃO assina e NÃO publica nada por si só: assinar e publicar são comandos que executa VOCÊ; o monitor limita-se a mostrá-los como texto.
           Não há IA no caminho crítico; o explicador opcional com IA vem desligado.

IDIOMA     8 idiomas: en, es, de, fr, it, ja, zh, pt (português de Portugal). Arranca em INGLÊS: o idioma do sistema não decide. Escolha outro no separador DEFINIÇÕES da página
           (ícone da roda dentada; o navegador lembra-se), ou com "language" em actions_monitor.json, ou com a variável de ambiente MONITOR_LANG, ou com --lang CÓDIGO nas ferramentas de linha de comandos (prevalece sobre tudo).
           As linhas que os scripts leem (SKIP, DISPATCHED, READY, FAILED, Summary:, BUILD ONLY...) estão sempre em inglês.
CONFIG     actions_monitor.json (criado a partir de actions_monitor.example.json no primeiro arranque). Chaves úteis: github_owner (vazio = a conta do gh),
           language, ecosystems_file, targets_file, refresh_seconds, cold_refresh_seconds, max_workers, min_rate_remaining, sentinel.*
           ecosystems_file: agrupa repositórios por prefixo do nome (ver ecosystems.example.json; "*" = todos os repositórios). targets_file: catálogo de builds para as
           ferramentas de lote (ver targets.example.json). profiles_file (profiles.example.json): perfis de lote. As chaves que começam por "_" nestes ficheiros são metadados.
ESPAÇO DE TRABALHO  OPCIONAL: uma pasta com clones locais dos seus repositórios (MONITOR_ROOT, "workspace_root" no json, ou uma pasta superior com um ficheiro .monitor-root).
           Sem ele, o monitor arranca em MODO REDUZIDO e diz isso: só o que a API do GitHub fornece (sem fila de assinatura local, sem relatório de auditoria, sem leitura do CHANGELOG).
           Com ele, há também releases candidatas, fila de assinatura e as ferramentas de lote. Registos de assinatura: "signed_dir"; ficheiros de auditoria: "audit_dir".
TESTES     py -3 -I -m unittest discover -s tests   (Linux/macOS: python3 -I -m unittest discover -s tests). Não precisam de rede.
PROBLEMAS  "API rate limit": a quota partilhada do gh (5000/hora) esgotou-se; aguarde o reinício (gh api rate_limit) e aumente refresh_seconds / diminua max_workers.
           O monitor pára ao arrancar se o gh não responder. Um ficheiro de cache corrompido é ignorado; apague sentinel_cache.json para recomeçar a cache.
           Reinicie o monitor depois de atualizar o pacote (um processo em execução mantém o código antigo).

FERRAMENTAS  read_report.py [--lang CÓDIGO] [--json] [--export-status PASTA] [--export-sign-queue FICHEIRO]  imprime o que diz o monitor em execução (local, sem quota do GitHub)
           gha_dispatch_all.py [--lang CÓDIGO] plan|dispatch|status|finalize|hygiene    lote de builds do GitHub Actions (no seu PC não se compila nada)
           release_notes.py REPO [--since ETIQUETA] [--out FICHEIRO]    rascunho de notas de release a partir dos commits (uma proposta; não publica nada)
           release_candidates.py    projetos com entradas em CHANGELOG [Unreleased] e última release antiga (só leitura)
EVENTOS    A Sentinela escreve uma linha JSON por cada ALTERAÇÃO (novo vermelho, CI recuperada, build bloqueado, alertas novos...) em events_monitor.jsonl. Cada linha traz um
           `code` estável (nunca depende do idioma), `kind`, `level`, `repo`, `args` e `text` (no idioma configurado). `tail -F` acompanha-o.
CI VERMELHA Um único critério: o ÚLTIMO run terminado de cada workflow no ramo predefinido. Vermelho = failure, timed_out, startup_failure ou action_required.
           cancelled, skipped, neutral e stale não contam.

NOVIDADES 1.5.1 (histórico: CHANGELOG.md)
  - Separador DEFINIÇÕES: novo grupo «IA externa para a sentinela» (ai.provider none / ollama / openai-compatible, modelo, endereço do Ollama (só este computador), um endpoint https, o NOME da variável de ambiente que guarda a chave, chamadas por dia). A chave em si nunca é guardada. Desligada por defeito; um serviço externo recebe dados dos seus repositórios.
  - migrate_state.py: leva os ficheiros escritos antes da 1.5.0 para os nomes novos. `python migrate_state.py` é uma simulação; `--apply` copia (os antigos ficam), `--move` renomeia. Nada é substituído. Uma página em docs/MIGRATING.md, em 8 idiomas.
  - Primeiro arranque sem ficheiros de catálogo próprios: o monitor avisa que está a usar os de exemplo (consola), e `--init-catalog` cria cópias editáveis de ecosystems.json, targets.json e profiles.json.
  - Python 3.11 ou superior (testado com 3.11 e 3.13, em Windows, Linux e macOS).

NOVIDADES 1.5.0 (histórico: CHANGELOG.md)
  - Separador DEFINIÇÕES: altere na página os valores de actions_monitor.json (lista de chaves permitidas com tipo e intervalo, validadas, cópia em config_backups/ antes de cada gravação, nunca tokens nem segredos; docs/SETTINGS.md).
  - Botões com relevo que se iluminam e afundam, ícones SVG com nome e tooltip em 8 idiomas, o aspeto do painel de estado, barras e números com vida (tudo para com prefers-reduced-motion).
  - Saídas opcionais, desligadas por omissão, só em 127.0.0.1: /metrics (Prometheus), /api/outputs/grafana.json (Grafana JSON / Infinity), /api/outputs/dashboard.json (docs/OUTPUTS.md, painel de exemplo em docs/grafana/).
  - Pacote neutro: os seus ecossistemas, alvos e perfis ficam fora (ecosystems_file, targets_file, profiles_file; tools_dir para as ferramentas de assinatura locais); inglês por omissão; nomes de ficheiros e pastas em inglês.
  AO ATUALIZAR desde 1.4.x: estes nomes mudaram (os antigos continuam a ser lidos onde possa existir um ficheiro; só se escrevem os novos):
  leer_parte.py -> read_report.py          eventos.py -> events.py          parte_history.py -> report_history.py
  LOTE_GITHUB_ACTIONS.bat/.sh/.command -> BATCH_GITHUB_ACTIONS.bat/.sh/.command
  eventos_monitor.jsonl -> events_monitor.jsonl          eventos_estado.json -> events_state.json
  PARTE_CENTINELA_DIA_<day>.* -> SENTINEL_REPORT_DAY_<day>.*     PARTE_CENTINELA_<time>.txt -> SENTINEL_REPORT_<time>.txt     CANDIDATAS_RELEASE.txt -> RELEASE_CANDIDATES.txt
  <signed_dir>/lotes/lote_<time>.json -> <signed_dir>/batches/batch_<time>.json     parte_history_days -> report_history_days     monitor_y_centinela.zip -> github_actions_monitor.zip
  sentinel.audit_files: names of the A8 audit files (neutral defaults RECONCILIATION_TOTAL_*.txt, ROUNDS_MAP_2*.txt, ROUNDS_MAP_EXTRA_*.txt)
  ci_red.json and --export-status: unchanged (a contract).

NOVIDADES 1.4.2 (histórico: CHANGELOG.md)
  Quando o A2 pergunta pelo último run de um workflow escondido, um run em curso ou cancelado deixa de contar como visto (podia esconder um vermelho anterior): a Sentinela pede os
  últimos runs concluídos desse workflow e usa o primeiro com conclusão real (cancelled e skipped são ignorados). Se não houver nenhum no ramo predefinido, só esse workflow continua inconclusivo.

NOVIDADES 1.4.1 (histórico: CHANGELOG.md)
  O A2 já não dá um repositório inteiro por não conclusivo só porque a amostra de execuções está cheia: por cada workflow do clone que falta na amostra
  pergunta ao GitHub pela última execução desse workflow no ramo por defeito (só leitura, a mesma porta de quota do A10, limitado por
  sentinel.a2_resolve_max_calls_per_tick, respostas guardadas sentinel.a2_resolve_ttl_seconds). O vermelho conta como vermelho; um workflow sem execuções no ramo
  continua sem conclusão e o painel nomeia-o.

NOVIDADES 1.4.0 (histórico: CHANGELOG.md)
  Painel A11 "Prontidão": prontidão das versões por repositório (CI do ramo predefinido e o seu commit, versão acima da última publicada, compilação, assinatura,
  passo seguinte), saúde dos ecossistemas (pontuação só com contagens reais, retida quando poucos repositórios têm dados) e versões fixadas atrás do seu fornecedor
  (lidas dos ficheiros de versões dos clones locais, configurados em sentinel.readiness.pins.sources). Só leitura; nada é estimado.

NOVIDADES 1.3.0 (histórico: CHANGELOG.md)
  8 idiomas na página, na linha de comandos, nos eventos e nos relatórios; seletor de idioma; ecossistemas, alvos e conta do GitHub como dados (github_owner,
  ecosystems_file, targets_file); espaço de trabalho opcional com um modo reduzido honesto; autoria e GPL-3.0-or-later em cada ficheiro; LICENSE, NOTICE, AUTHORS;
  README e QUICKSTART em 8 idiomas.
LICENÇA    GPL-3.0-or-later (ver LICENSE e NOTICE). Copyright (C) 2026 JuanenRac (Electro Hobby 3D).

AJUDA, ACERCA DE E VERIFICAÇÕES (1.6.4)
---------------------------------------
A página tem um botão de Ajuda (? redondo) e um de Acerca de (i); na consola use --help-topics, --help-search, --about e --doctor; --demo mostra a página com dados inventados. A edição lite arranca com o seu próprio banner e título de janela (LITE, porta 8766, sem sentinela); a completa diz COMPLETE, porta 8765, sentinela ativa. O aviso de versão nova pode ser desligado (Definições > Básico).

NOVIDADES DA 1.7.2 (cabeçalho ordenado, controlos rápidos no canto, Acerca de no painel lateral; histórico: CHANGELOG.md)
  Os números do cabeçalho estão numa ordem que se lê e numa grelha que segue a largura; o botão de só quentes, a lista de velocidade e a saúde dos ecossistemas ficam em cima à direita.
  Definições, Ajuda e Acerca de estão só no painel lateral. O aviso de versão nova já não está no cabeçalho (Acerca de e a consola continuam a dizê-lo). Os testes não deixam nada junto do código.

NOVIDADES DA 1.7.1 (painel lateral, dezasseis temas, um contrato para as sentinelas; histórico: CHANGELOG.md)
  A página tem um painel lateral à esquerda com o logótipo, as secções em grupos e a ajuda; contrai-se para os seus ícones. Dezasseis temas além de auto, claro e escuro (Definições > Este navegador).
  A sentinela de CI está agora atrás de um contrato (BaseSentinel, SentinelRegistry), por isso podem juntar-se as seguintes; o que mostra e decide não muda. A edição lite não tem nada disto.

NOVIDADES DA 1.7.0 (várias contas; histórico: CHANGELOG.md)
  A edição completa pode vigiar várias contas do GitHub: uma pasta accounts/<id>/ por conta e um monitor por conta sob um supervisor, pelo que a falha de uma nunca toca noutra.
  --accounts, --account <id>, --migrate-accounts [--apply]; um seletor e a página Todas as contas; ?view= e ?chrome=0; a vista Ao vivo com o estado do webhook; um /api/webhook para todas.
  Guia: docs/ACCOUNTS.md. Sem uma pasta accounts/ nada muda. A edição lite tem uma conta e nada disto.

NOVIDADES DA 1.6.8 (proxy verificado a sério; histórico: CHANGELOG.md)
  O proxy HTTPS da 1.6.7 é verificado contra um proxy real na porta 443 (tools/manual_check_live.py proxy no repositório) e por testes que percorrem toda a cadeia. O histórico de
  alterações está traduzido até à 1.6.3 (Ajuda > Registo de alterações). Nenhuma definição muda.

NOVIDADES DA 1.6.7 (proxy HTTPS na porta predefinida; histórico: CHANGELOG.md)
  Nova definição listen.proxy_public_host (vazia por predefinição): o nome público de um proxy HTTPS na porta 443 que reencaminha Host e Origin sem porta é aceite tal como está, só com
  HTTPS, e só se altera a partir do próprio computador. O histórico de alterações está traduzido para a 1.6.7, a 1.6.6 e a 1.6.5 (Ajuda > Registo de alterações).

NOVIDADES DA 1.6.6 (correções do modo rede e do act; histórico: CHANGELOG.md)
  O modo rede com HTTPS funciona a partir da página (a origem segue o esquema da sessão); toda a definição marcada como segura só se altera a partir do próprio computador; POST /api/access abre
  a sessão sem o token no endereço; barra vermelha nas Definições se escuta em todas as interfaces; contador de falhas engolidas no --doctor e em Acerca de. act: o Stop liberta a execução e o
  canal fecha-se. O histórico de alterações está traduzido em oito idiomas (Ajuda > Registo de alterações).

NOVIDADES DA 1.6.5 (integridade e segurança; histórico: CHANGELOG.md)
  Lotes: CI verde significa que o workflow obrigatório passou (dispatch.required_ci), um git fetch falhado pára o despacho, o targets.json não pode indicar uma ferramenta fora da pasta das
  ferramentas nem alterar dry_run/ref, e o finalize só oferece execuções cujo lote registou a verificação do commit (finalize --accept-legacy para lotes antigos). O act fica dentro do espaço
  de trabalho e o Stop termina toda a árvore. Modo de rede: HTTPS opcional, bloqueio após tokens errados, só IPv4. Webhook: sem repetições. Notificações: max_per_hour conta mensagens.
  O --doctor avisa de combinações perigosas.
