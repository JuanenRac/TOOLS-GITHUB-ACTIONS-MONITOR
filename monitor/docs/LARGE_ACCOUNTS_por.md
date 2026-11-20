<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LARGE_ACCOUNTS.md) | [🇪🇸 Español](LARGE_ACCOUNTS_spa.md) | [🇫🇷 Français](LARGE_ACCOUNTS_fra.md) | [🇮🇹 Italiano](LARGE_ACCOUNTS_ita.md) | [🇩🇪 Deutsch](LARGE_ACCOUNTS_deu.md) | [🇨🇳 简体中文](LARGE_ACCOUNTS_zho.md) | [🇯🇵 日本語](LARGE_ACCOUNTS_jpn.md) | **🇵🇹 Português**

# Contas grandes: centenas de repositórios

Uma conta com centenas de repositórios, muitos forks ou várias organizações gasta depressa a quota da API. Isto é uma receita, pela ordem que mais poupa; cada definição está no separador Definições.

1. **Comece por um perfil.** Definições > Básico > Perfil: *Organização de código aberto* fixa quase tudo o que se segue num clique (depois pode alterar cada definição).
2. **Vigie o que é mantido.** `discovery.fork_policy` = `auto` mantém só os forks com CI própria (o tipo de conta decide a janela, `discovery.fork_ci_days`); `discovery.fork_checks_per_pass` reparte as perguntas por várias listagens. `discovery.skip_archived` vem ativado. `exclude` e `ecosystems` restringem a lista por nome. Uma listagem da conta que chega vazia, ou com menos de `discovery.min_keep_pct` por cento da última boa, não é aceite: mantém-se a última boa listagem, volta a ler-se dentro de cinco minutos e o resumo para as ferramentas de IA tem o sinal repos.listing. `discovery.hide` aceita também `public` (e `private`, `fork`, `empty`); o separador Básico conta o que cada regra deixou de fora, por isso nada deixado de fora por um filtro é lido como limpo.
3. **Pergunte menos.** `cold_runs_per_repo` e `cold_refresh_seconds` fixam o custo dos repositórios calmos; `runs_per_repo` e `refresh_seconds` fazem o mesmo para os ativos. `network.etag` torna gratuitas as leituras repetidas quando nada mudou, e o modo Baixo (`modes.auto_low`) abranda tudo sozinho quando a quota escasseia.
4. **Dê um orçamento à Sentinela.** `sentinel.budget_per_hour`, `sentinel.max_calls_per_tick` e `sentinel.hygiene_seconds` (a higiene é um pedido por repositório de seis em seis horas por defeito; alongue-a) limitam o que gastam as verificações A3-A6.
5. **Junte uma segunda quota.** `github_app.share_reads` deixa uma GitHub App responder a parte das leituras com a sua própria quota.
6. **Não se afogue no ruído.** A verificação de higiene (`sentinel.hygiene.ruleset_mode` = `effective`, `sentinel.hygiene.skip`), as dos ficheiros das releases (`sentinel.surface.checks.release_assets.allow_empty`) e `sentinel.bots_apart` evitam que se acumulem verificações que não se aplicam aos seus repositórios.

O separador Quota mostra o que resta a cada fonte e quanto gasta o próprio monitor.

O acompanhamento dos originais dos forks (`upstream.enabled`) diz no seu painel quanto demora uma volta a todos os forks ao ritmo de `upstream.requests_per_hour` e `upstream.forks_per_request`; quando é mais do que `upstream.refresh_hours`, o acompanhamento nunca descansa (727 forks a 8 por pedido e 6 pedidos por hora demoram 15,2 horas). Os pedidos da última hora guardam-se ao reiniciar, pelo que um reinício não devolve a quota.

As chamadas de um tick do Sentinela (`sentinel.max_calls_per_tick`) são uma única contagem para todas as suas fases, e um repositório cujas leituras falham três vezes seguidas é deixado em paz 30 segundos, duplicando até 10 minutos, enquanto se leem os outros.

## Fila de leituras, limites e uma leitura para todos

- **Contrapressão** (`backpressure.enabled`, desligada por predefinição): as leituras de um ciclo passam por uma fila limitada (primeiro os repositórios com um workflow vermelho, depois os quentes, os nunca lidos e os lidos há mais tempo). `backpressure.max_reads_per_cycle` fixa um número (0 = nenhum); quando um ciclo dura mais de `backpressure.shed_percent` por cento da pausa entre ciclos, o número permitido reduz-se para metade (nunca abaixo de `backpressure.min_reads`) e volta a crescer um décimo após cada ciclo rápido. O que espera mantém a sua última imagem e vai primeiro no ciclo seguinte. `/metrics` mostra `ghamon_read_queue_*`.
- **Limites e o doctor**: `monitor_cli.py doctor` tem uma verificação `capacity` que compara a configuração com os seus tetos (chamadas por hora face à quota e a `sampling.api_budget_per_hour`, a memória das execuções guardadas face a `limits.memory_mb`, os repositórios face a `discover_limit`) e avisa a partir de `limits.warn_percent`. `/metrics` mostra os que estão vivos como `ghamon_limit_used_percent{limit=...}` (eventos guardados, fluxos, fila de leituras, séries dos histogramas).
- **Uma leitura para todos** (`refresh.share_by_workflow`, desligada por predefinição): quando o ciclo, uma página, um ecrã de parede ou um cliente da API pedem os jobs da mesma execução ao mesmo tempo, o primeiro lê do GitHub e os outros aproveitam a sua resposta, válida `refresh.share_seconds` segundos. `/metrics` conta as leituras poupadas (`ghamon_shared_reads_spared_total`).
