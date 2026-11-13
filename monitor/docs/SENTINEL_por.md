<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL.md) | [🇪🇸 Español](SENTINEL_spa.md) | [🇫🇷 Français](SENTINEL_fra.md) | [🇮🇹 Italiano](SENTINEL_ita.md) | [🇩🇪 Deutsch](SENTINEL_deu.md) | [🇨🇳 简体中文](SENTINEL_zho.md) | [🇯🇵 日本語](SENTINEL_jpn.md) | **🇵🇹 Português**

# A sentinela e as suas verificações A1-A13

A **sentinela** é a segunda metade da edição completa. O *monitor* mostra o que está a correr e o que falha neste momento; a *sentinela* examina toda a conta de poucos em poucos minutos e responde a outra pergunta: **o que precisa de uma pessoa**. Lê o GitHub (nunca escreve nele), guarda um histórico curto neste computador e transforma o que encontra em treze verificações numeradas, **de A1 a A13**, com um semáforo cada uma.

**A edição lite não a inclui.** `MONITOR_LITE_GITHUB_ACTIONS` (porta 8766) não tem sentinela: o módulo nem sequer é importado e os seus endpoints respondem 404. A edição completa (`MONITOR_GITHUB_ACTIONS`, porta 8765) arranca-a sozinha; desliga-se com `sentinel.enabled` (Definições > Sentinela). As duas edições usam a mesma regra de «vermelho no main» (A2), por isso os números coincidem.

## Como arranca e quanto custa

Arranca com o monitor completo e corre no mesmo processo, num fio próprio, com o seu orçamento de chamadas ao GitHub (`sentinel.budget_per_hour`, 600 por defeito, e `sentinel.max_calls_per_tick`). Quando a quota do GitHub desce abaixo de `sentinel.min_rate_remaining` deixa de perguntar e a página indica a pausa por quota. Nada do que faz escreve no GitHub.

## Ficheiros que escreve (junto ao monitor, nunca publicados)

| Ficheiro | O que contém |
|---|---|
| `ci_red.json` | esquema 2: por repositório, os workflows a vermelho e as horas que uma versão espera pela assinatura. Contrato estável para outras ferramentas, ver `CI_RED_SCHEMA_por.md` e `CI_RED_BRIDGE_por.md`. Onde: `sentinel.ci_red_file`. |
| `sentinel_history.json` | os totais diários (alertas, vermelhos, candidatas) para as tendências e para «novos desde ontem». |
| `sentinel_cache.json` | as últimas respostas das leituras lentas, para que um reinício não volte a perguntar tudo. |
| `events_monitor.jsonl`, `events_state.json` | o fluxo de eventos (o que ficou vermelho, o que foi corrigido) com um `code` estável por evento. |
| `SENTINEL_REPORT_*.txt` | o relatório diário, guardado na pasta de auditoria se existir. |

## Como ler

Cada verificação tem um de cinco níveis: **ok** (nada a fazer), **info** (convém saber), **warn** (veja em breve), **bad** (aja já) e **unknown** (ainda não foi possível verificar: **unknown nunca é mostrado a verde**). O relatório no topo do separador resume tudo em poucas linhas; o detalhe abre por verificação. Um repositório que filtrou no monitor não é verificado.

Cada luz tem uma forma além de uma cor (um visto para ok, um ponto de exclamação para warn, uma cruz para bad, um *i* para info e um ponto de interrogação para unknown), por isso o nível nunca depende só da cor. Passe o rato por cima de uma luz, ou chegue a ela com o teclado, para ler o seu nível por palavras e como estava antes de mudar. As luzes respiram a um ritmo que segue o seu nível, a que muda faz uma transição breve e, se o sistema pedir movimento reduzido, não se mexe nada.

## As verificações

| Verificação | O que verifica e a regra exata | Onde se configura | Nível e o que fazer |
|---|---|---|---|
| **A1** | **Builds.** Um run em curso ou em fila há mais do que o limite está *preso*. Listam-se também os problemas abertos com a etiqueta `build-failed` ou `build-stuck`. Ignoram-se os runs do evento `dynamic` (internos do Dependabot). | `stuck_minutes` | **bad** se algo estiver preso ou houver um problema aberto. Abra o run, cancele-o ou volte a lançá-lo; feche o problema depois de corrigir. |
| **A2** | **CI a vermelho.** Para cada ficheiro de workflow, o ÚLTIMO run CONCLUÍDO no ramo POR DEFEITO: está a vermelho se falhou (`failure`, `timed_out`, `startup_failure`, `action_required`). Os runs `cancelled`, `skipped`, `neutral` ou `stale`, os que estão em curso e os de outros ramos não dizem nada e nunca escondem um vermelho anterior. *Sequência* = vermelhos consecutivos. Quando a lista de runs de um repositório é tão longa como a amostra pedida, um workflow pode ficar para lá dela: a sentinela pergunta ao GitHub o último run de cada um desses workflows. | `runs_per_repo`, `cold_runs_per_repo`, `sentinel.a2_full_sample_unknown`, `sentinel.a2_resolve_max_calls_per_tick`, `sentinel.a2_resolve_ttl_seconds` | **bad** se algum workflow estiver a vermelho; **unknown** (nunca verde) se um repositório não tiver dados de runs ou um workflow não puder ser resolvido. Corrija o workflow ou volte a lançá-lo; a edição lite mostra o mesmo número, marcado como aproximado porque adivinha o ramo por defeito. |
| **A3** | **Alertas de segurança.** Alertas abertos de CodeQL, Dependabot e secret scanning por repositório, com a gravidade, e quantos são novos desde o último dia do histórico. | `sentinel.alerts_hot_seconds`, `sentinel.alerts_cold_seconds` | **bad** com qualquer alerta de segredos ou crítico/alto; **warn** com os restantes; **unknown** durante o carregamento. Rode primeiro um segredo divulgado; depois atualize ou descarte o resto. |
| **A4** | **Pull requests do Dependabot.** PRs abertos do Dependabot com a idade, um salto de versão *maior* e um conflito de fusão; os PRs de outras pessoas só são contados. | `sentinel.stale_pr_days` (7) | **warn** se algum for um salto maior ou tiver conflito; **info** se só houver PRs. Fundir os verdes; reorganizar ou fechar os que colidem. |
| **A5** | **Versões.** (a) *Candidata*: pelo menos `candidate_min_entries` entradas em `[Unreleased]` do CHANGELOG e a última versão mais antiga do que `candidate_days` (ou nenhuma). (b) Uma *build verde* de um workflow de versão mais recente do que a última versão. (c) *À espera de assinatura*: uma build verde com mais de `pending_sign_hours` sem assinar nem publicar; uma assinatura só conta se verificar com a chave pública do ecossistema. | `sentinel.candidate_days` (2), `sentinel.candidate_min_entries` (1), `sentinel.skip_candidate_prefixes`, `sentinel.pending_sign_hours` (24), `sentinel.require_verified_signature` | **warn** com uma candidata ou uma assinatura pendente; **info** com builds verdes ainda não publicadas. Corte a versão ou assine a build. |
| **A6** | **Higiene.** Por repositório: o ruleset `protect-main` está ACTIVE, existe a etiqueta `dependencies`, existem os ficheiros exigidos (por defeito README, LICENSE, CHANGELOG, SECURITY), exige-se fixar por SHA, `allowed_actions` é `selected` e nenhum workflow agendado foi desativado pelo GitHub. | `sentinel.required_files`, `sentinel.hygiene_seconds` | **warn** se algum repositório tiver um problema; **info** enquanto alguns não estiverem verificados. Cada problema indica a correção. |
| **A7** | **Utilização.** Minutos de Actions das últimas 24 horas e 7 dias por repositório e ecossistema, a quota de API que resta e o *orçamento* por ecossistema: **ok** abaixo de 80 %, **warn** a partir de 80 %, **over** a partir de 100 % do teto. | `sentinel.min_rate_remaining` (800), `sentinel.minutes_budget`, `sentinel.minutes_budget_period` (7d) | **warn** se a quota estiver abaixo do limite ou um orçamento chegar a 80 %. Espace a atualização ou reduza os workflows longos. |
| **A8** | **Rondas.** Lê os ficheiros de auditoria e de rondas da pasta de auditoria (os padrões de `sentinel.audit_files`) e mostra o seu estado. Vazio se não houver pasta de auditoria. | `sentinel.audit_files.*`, `audit_dir` | Apenas **info**. Nada a fazer. |
| **A9** | **Roadmaps.** Se os quadros do GitHub Projects dos ecossistemas estão *vivos*: reconciliados nos últimos 8 dias e não mais antigos do que as suas definições. Precisa do âmbito `read:project` do `gh`; sem ele o separador funciona com as definições e diz o que falta. | (fixed: 8 days) | **warn** se um quadro estiver desatualizado ou nunca reconciliado; **unknown** se não estiver configurado. |
| **A10** | **Superfície de Actions e versões.** Vinte e cinco verificações só de leitura sobre os clones e algumas chamadas a frio, listadas na tabela abaixo. Cada uma tem interruptor e, quando faz sentido, um limiar. | `sentinel.surface.*` | Por verificação, ver abaixo. Em pausa quando a quota é baixa (o relatório di-lo). |
| **A11** | **Preparação de versões, saúde do ecossistema e pins.** Preparação por repositório (entradas, CI, versão, build, assinatura, passo seguinte); uma nota de saúde 0-100 por ecossistema que subtrai penalizações ponderadas por vermelhos, bloqueios, segredos, alertas altos, alertas, PRs antigos, builds por assinar e higiene; e os pins de dependências em atraso. A nota só aparece quando `min_coverage` dos repositórios tem dados. | `sentinel.readiness.*` (`warn_below` 70, `min_coverage` 0.5) | **warn** quando uma nota fica abaixo de `warn_below`; **info** com repositórios em atraso; **unknown** com poucos dados. |
| **A12** | **Análise.** p50 / p95 da duração de cada workflow, do tempo em fila dos seus jobs e de cada passo; workflows mais lentos do que o habitual (`analytics.slow_factor`); workflows *instáveis* (falharam e depois passaram no mesmo commit). É só uma etiqueta: nunca muda o que conta como vermelho. | `analytics.*` | Sem semáforo próprio. Veja primeiro os lentos e os instáveis. |
| **A13** | **Linter de workflows.** Regras estáticas sobre os clones locais: `unpinned_uses`, `permissions`, `secrets_in_clear`, `injection`, `pr_target`. Cada achado tem um nível (info / aviso / erro); um comentário `# monitor-lint: ignore REGRA motivo` ou `lint.ignore` silencia um. | `lint.*` | Cor do pior achado. Corrija primeiro os erros; a página filtra por nível. |

## As verificações de A10

Todas são sugestões só de leitura para uma pessoa; o monitor nunca fecha um problema, funde um pull request nem publica uma versão. Desliga-se uma com `sentinel.surface.checks.<nome>.enabled`.

| Verificação | O que procura | Por defeito |
|---|---|---|
| `workflows_disabled` | Workflows desativados manualmente | on |
| `dead_schedule` | Agendamentos sem execuções | on · days=14 |
| `unpinned_uses` | uses: não fixado por SHA | on |
| `broad_permissions` | Permissões demasiado amplas (write-all) | on |
| `pr_target` | pull_request_target com checkout do PR | on |
| `stuck_concurrency` | Concurrency bloqueada (runs em fila do mesmo workflow) | on · minutes=60 |
| `matrix_os` | Falhas apenas num sistema da matriz | on · max_per_tick=4 |
| `artifacts` | Custo dos artifacts | on · max_mb=500, retention_days=30 |
| `required_checks` | Checks obrigatórios vermelhos ou em falta | on |
| `release_assets` | Releases publicadas incompletas | on · recent_days=30, required |
| `tag_vs_version` | Etiqueta de release vs versão do manifesto/CHANGELOG | on |
| `packages` | GitHub Packages | on |
| `drafts` | Rascunhos e pré-releases esquecidos | on · days=14 |
| `security_aged` | Alertas críticos/altos por idade (classificação de repositórios) | on · days=30 |
| `coverage` | Cobertura de segurança (CodeQL / Dependabot) | on |
| `secret_resolved` | Secret scanning: abertos vs resolvidos | on |
| `dependabot_priority` | Dependabot por prioridade | on |
| `issue_close` | Issues que se podem fechar (apenas sugestão) | on |
| `milestones` | Milestones vencidos por ecossistema | on |
| `pr_human` | PRs humanos envelhecidos | on · days=7 |
| `pr_workflow_touch` | PRs que alteram workflows ou CODEOWNERS (prioridade) | on |
| `merge_queue` | Fila de integração: aprovados com CI verde | on |
| `maturity` | Maturidade do manifesto face à evidência | on |
| `parity` | Paridade dos README em 8 idiomas quebrada | on |
| `attestation` | Atestações de build | on · max_per_tick=3 |

## Onde se configura tudo

Cada limiar acima é uma definição dos separadores **Sentinela**, **Verificações de superfície (A10)**, **Prontidão (A11)**, **Pastas e ficheiros**, **Análise** e **Linter de workflows** da página de Definições, e uma chave de `actions_monitor.json`. A lista completa com os intervalos está em `SETTINGS_por.md`. O painel de Ajuda e `--help-topics sentinel` mostram esta página sem ligação.

## A segunda sentinela e a lista de alertas

Além desta sentinela (CI), a edição completa tem a **sentinela Collab**, que vigia issues e pull requests abertas com um relógio próprio e nunca escreve no GitHub: [COLLAB_por.md](COLLAB_por.md). O separador **Alertas** reúne os alertas de ambas numa lista, com filtro por origem e nível e silêncios locais que acabam sozinhos (`alerts.mute_hours`); `GET /api/alerts` serve a mesma lista.
