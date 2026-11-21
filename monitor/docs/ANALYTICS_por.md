<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ANALYTICS.md) | [🇪🇸 Español](ANALYTICS_spa.md) | [🇫🇷 Français](ANALYTICS_fra.md) | [🇮🇹 Italiano](ANALYTICS_ita.md) | [🇩🇪 Deutsch](ANALYTICS_deu.md) | [🇨🇳 简体中文](ANALYTICS_zho.md) | [🇯🇵 日本語](ANALYTICS_jpn.md) | **🇵🇹 Português**

# Análises, leituras condicionais e ligação perdida

O que o monitor aprende com os runs que já lê, como poupa quota e como sobrevive a um corte de rede. Tudo é local; nada é enviado para lado nenhum.

## Durações, tempo em fila e passos

- `p50` e `p95` da duração dos runs bem-sucedidos de cada workflow; do tempo que um job esperou antes de começar (criado a iniciado); e de cada passo de um workflow. Um workflow mostra números quando tem `analytics.min_samples` amostras.
- Os tempos de jobs e passos precisam dos jobs de runs concluídos: até `analytics.jobs_per_cycle` runs por ciclo, cada um lido uma vez (0 não lê nenhum). O webhook de entrada fornece-os de graça.
- São exportados como `ghamon_workflow_duration_seconds`, `ghamon_job_queue_seconds` e `ghamon_step_duration_seconds` (etiqueta `quantile` 0.5 / 0.95; precisa de `per_repo`) e na fonte JSON do Grafana (`durations`, `queue`). `slower` lista os workflows cujo p50 é `analytics.slow_factor` vezes o habitual.


## Workflows instáveis (flaky)

Um workflow que FALHOU e depois PASSOU no mesmo commit (ou cujo run precisou de outra tentativa) é etiquetado como instável: `ghamon_workflow_flaky_rate`. É só uma etiqueta: o que conta como vermelho não muda.


## Leituras condicionais (ETag)

- Cada leitura das listas de runs envia `If-None-Match`; o GitHub responde `304 Not Modified` quando nada mudou e essa resposta não gasta quota. O cabeçalho mostra quantas leituras foram poupadas e `ghamon_etag_saved_total` conta-as. `cache.etag.enabled` e `cache.etag.ttl_hours` estão no separador Definições. Cada entrada pertence à credencial que a leu (uma impressão curta do token faz parte da chave, nunca o token), pelo que um `304` nunca devolve o corpo de outra identidade. Um estado que ainda se move lê-se sempre por inteiro: os trabalhos de uma execução, uma execução isolada, os conjuntos e verificações (`cache.etag.skip_stateful`) e qualquer lista de execuções cuja última resposta ainda tinha uma em fila ou em curso (`cache.etag.revalidate_active`). Uma recusa (404 ou 403 que não seja limite de pedidos) lembra-se durante `cache.negative_ttl_s` segundos. O `/metrics` conta ainda as respostas sem ETag, as leituras inteiras feitas de propósito e as recusas não repetidas, e o resumo para as ferramentas de IA tem o sinal quota.etag.
- O resumo para as ferramentas de IA nomeia schema.drift quando o GitHub enviou um estado ou uma conclusão que o monitor não conhece, ou uma execução sem número utilizável: o valor desconhecido mostra-se como chegou e nunca se conta como vermelho nem como verde.
- A cache é o ficheiro local `etag_cache.json` (nunca publicado); um ficheiro estragado é apenas uma cache vazia.


## Quando a ligação se perde

Se todas as leituras de um ciclo falham por um problema de ligação (não de login nem de quota), a página mantém a última imagem e mostra um aviso vermelho `sem ligação desde HH:MM`. Nada lança exceções; o monitor retoma sozinho e escreve um evento `offline` e outro `online`, uma vez cada (podem ser notificados). Entretanto `ghamon_offline` vale 1.

## Durante quanto tempo se guarda o histórico

Além de `keep_days` do bloco de análises, a passagem de retenção remove os dias do histórico mais antigos do que `retention.analytics_days` (180 por omissão); as próprias amostras são limitadas por `max_samples`. Veja [STORAGE_por.md](STORAGE_por.md).


## Tempo poupado (uma estimativa)

Desligado por predefinição (`productivity.enabled`). Ligado, a secção mostra, tarefa a tarefa, quantos minutos por semana o monitor poupa, com a fórmula de [PRODUCTIVITY_por.md](PRODUCTIVITY_por.md): vezes por semana x minutos de cada vez sem o monitor x poupança da tarefa.

- Quantificam-se duas tarefas. **Vigiar** (olhar à mão para os separadores do Actions e decidir o que está vermelho) toma as vezes por semana e os minutos das suas notas (`productivity.watch_times_per_week`, `productivity.watch_minutes_before`). **Diagnóstico** (achar a causa de uma execução falhada) conta as execuções falhadas que o monitor tem à vista em `productivity.window_days` e toma os minutos das suas notas (`productivity.triage_minutes_before`).
- O monitor não pode ver o que fazia antes de ser instalado. Uma tarefa sem essas notas diz **sem dados** e não se inventa nenhum número. O total também diz sem dados enquanto todas as tarefas não tiverem notas.
- Se anotou também os minutos com o monitor (`productivity.watch_minutes_after`, `productivity.triage_minutes_after`), a poupança é medida com as suas notas: 1 - depois / antes. Caso contrário é a percentagem de `productivity.saving_percent` (90 por predefinição) e a tabela diz **assumido (sem medir)**.
- Com `productivity.team_hours_per_week` a estimativa diz também que parte do tempo de trabalho são os minutos poupados.
- Corrigir uma falha leva o mesmo tempo com ou sem o monitor e nunca se conta. Só se contam as execuções falhadas que o monitor tem: uma lista de execuções muito longa pode ter mais falhas do que as mostradas.
- É local e só de leitura: nenhuma chamada ao GitHub, nada sai do computador. Está em `/api/analytics` (`time_saved`), no resumo do painel A12 e no brief do separador Resumo para as ferramentas de IA.
