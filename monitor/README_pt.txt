Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE

MONITOR DO GITHUB ACTIONS + SENTINELA (versão 1.7.7)
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

HISTÓRICO DE ALTERAÇÕES
  Todas as versões, da mais recente à mais antiga, estão em CHANGELOG.md (em oito idiomas em docs/CHANGELOG_*.md, e na página: Ajuda > Registo de alterações).

AJUDA, ACERCA DE E VERIFICAÇÕES (1.6.4)
---------------------------------------
A página tem um botão de Ajuda (? redondo) e um de Acerca de (i); na consola use --help-topics, --help-search, --about e --doctor; --demo mostra a página com dados inventados. A edição lite arranca com o seu próprio banner e título de janela (LITE, porta 8766, sem sentinela); a completa diz COMPLETE, porta 8765, sentinela ativa. O aviso de versão nova pode ser desligado (Definições > Básico).
