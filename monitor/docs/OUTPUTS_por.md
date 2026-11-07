<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](OUTPUTS.md) | [🇪🇸 Español](OUTPUTS_spa.md) | [🇫🇷 Français](OUTPUTS_fra.md) | [🇮🇹 Italiano](OUTPUTS_ita.md) | [🇩🇪 Deutsch](OUTPUTS_deu.md) | [🇨🇳 简体中文](OUTPUTS_zho.md) | [🇯🇵 日本語](OUTPUTS_jpn.md) | **🇵🇹 Português**

# Saídas para outras ferramentas

Três saídas opcionais, **todas desativadas por predefinição**, que se ativam no separador Definições (grupo «Saídas para outras ferramentas») ou em `actions_monitor.json`:

```json
"outputs": {"prometheus": {"enabled": false, "per_repo": true}, "json": {"enabled": false}, "dashboard": {"enabled": false}}
```

São servidas pelo mesmo servidor web, apenas em `127.0.0.1`, com as mesmas verificações de `Host` / `Origin` que o resto, e **não precisam de token**. Leem o estado que o monitor já tem, pelo que um
scrape ou a atualização de um painel não gasta quota da API do GitHub. Ativá-las ou desativá-las aplica-se de imediato (sem reiniciar).

| Caminho | Formato | Interruptor |
|---|---|---|
| `/metrics` | Texto do Prometheus, versão 0.0.4 | `outputs.prometheus.enabled` (`per_repo` acrescenta as séries por repositório) |
| `/api/outputs/grafana.json` | Tabelas JSON para a fonte de dados «Infinity» / JSON do Grafana | `outputs.json.enabled` |
| `/api/outputs/dashboard.json` | o documento de `ci_red.json` (esquema 2, ver CI_RED_SCHEMA_por.md) para um painel de estado | `outputs.dashboard.enabled` |

Um pedido a um caminho cujo interruptor está desligado recebe `404`. A forma anterior de entregar o mesmo documento a um painel, `ci_red.json` e `read_report.py --export-status`, não muda: é um contrato.

## Métricas do Prometheus

Todos os nomes começam por `ghamon_`. Apenas medidores (gauges). Um valor desconhecido é **omitido**, nunca escrito como 0.

| Métrica | Etiquetas | Significado |
|---|---|---|
| `ghamon_info` | `version` | sempre 1 |
| `ghamon_snapshot_complete` | | 1 quando o instantâneo da sentinela está completo, 0 enquanto carrega ou está reduzido |
| `ghamon_red_workflows`, `ghamon_red_repos` | | workflows (repositórios) cuja última execução concluída no ramo predefinido está a vermelho |
| `ghamon_ecosystem_red_workflows` | `ecosystem` | o mesmo por ecossistema |
| `ghamon_repo_red_workflows` | `repo`, `ecosystem` | por repositório (requer `per_repo`) |
| `ghamon_workflow_red_streak` | `repo`, `workflow`, `ecosystem` | execuções vermelhas consecutivas (requer `per_repo`) |
| `ghamon_workflow_red_hours` | `repo`, `workflow`, `ecosystem` | horas desde que ficou vermelho (requer `per_repo`) |
| `ghamon_pending_sign`, `ghamon_pending_sign_repos`, `ghamon_pending_sign_hours_max` | | compilações à espera da assinatura ou publicação locais, acima do limiar |
| `ghamon_repo_pending_sign_hours` | `repo`, `ecosystem` | a espera mais longa de um repositório (requer `per_repo`) |
| `ghamon_surface_paused`, `ghamon_surface_paused_remaining`, `ghamon_surface_paused_needed` | | 1 enquanto as verificações de superfície (A10) esperam por quota do GitHub, com a quota restante e a necessária |
| `ghamon_api_rate_remaining`, `ghamon_api_rate_limit` | | a quota da API do GitHub |
| `ghamon_sentinel_calls_last_hour`, `ghamon_sentinel_budget_per_hour` | | as chamadas à API da sentinela face ao seu orçamento |
| `ghamon_repos_watched`, `ghamon_runs_active`, `ghamon_runs_stuck`, `ghamon_runs_failing`, `ghamon_issues_open`, `ghamon_quota_paused` | | os números em tempo real do separador Agora |

Um trabalho de scrape:

```yaml
scrape_configs:
  - job_name: github-actions-monitor
    scrape_interval: 30s
    static_configs:
      - targets: ["127.0.0.1:8765"]
```

## Grafana

`docs/grafana/monitor_dashboard.json` é um painel importável (Grafana 10 ou posterior): painéis de estatística para os workflows a vermelho, as compilações à espera de assinatura, a quota restante, o
estado de A10, se o instantâneo está completo e as execuções bloqueadas; um gráfico de barras dos workflows a vermelho por ecossistema; um gráfico da maior sequência vermelha e da espera de assinatura; e duas tabelas lidas
de `/api/outputs/grafana.json` com a fonte de dados Infinity (`root_selector` `red` e `pending_sign`). Ao importar, o Grafana pede as fontes de dados Prometheus e Infinity; altere
a porta no URL das duas tabelas se o monitor não usar a 8765. O Grafana tem de correr na mesma máquina (as saídas só respondem em 127.0.0.1).

## Ideias retiradas de projetos semelhantes

Ler o que outras ferramentas fazem para o GitHub Actions deu algumas ideias; não se usa nada do seu código nem dos seus textos. De um exportador de métricas do Prometheus: o estado de uma execução como número mais etiquetas, a
escolha das etiquetas a exportar e uma porta e um intervalo configuráveis. De um painel de TV alimentado por webhooks: um estado por repositório com filtros, mostrado em grande. De um observador de terminal: todos os
workflows de um repositório de uma só vez até terminarem. De um painel de webhooks com regras de alerta: filtros por repositório, ramo e workflow antes de alertar. Aqui as mesmas ideias surgem como
`per_repo` (escolher as séries), a fonte JSON com uma linha por workflow a vermelho, o separador Agora em tempo real e o ficheiro de eventos com filtros na página.
