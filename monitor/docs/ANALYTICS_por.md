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

- Cada leitura das listas de runs envia `If-None-Match`; o GitHub responde `304 Not Modified` quando nada mudou e essa resposta não gasta quota. O cabeçalho mostra quantas leituras foram poupadas e `ghamon_etag_saved_total` conta-as. `cache.etag.enabled` e `cache.etag.ttl_hours` estão no separador Definições.
- A cache é o ficheiro local `etag_cache.json` (nunca publicado); um ficheiro estragado é apenas uma cache vazia.


## Quando a ligação se perde

Se todas as leituras de um ciclo falham por um problema de ligação (não de login nem de quota), a página mantém a última imagem e mostra um aviso vermelho `sem ligação desde HH:MM`. Nada lança exceções; o monitor retoma sozinho e escreve um evento `offline` e outro `online`, uma vez cada (podem ser notificados). Entretanto `ghamon_offline` vale 1.

## Durante quanto tempo se guarda o histórico

Além de `keep_days` do bloco de análises, a passagem de retenção remove os dias do histórico mais antigos do que `retention.analytics_days` (180 por omissão); as próprias amostras são limitadas por `max_samples`. Veja [STORAGE_por.md](STORAGE_por.md).
