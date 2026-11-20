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

Um pedido a um caminho cujo interruptor está desligado recebe `404`. A forma anterior de entregar o mesmo documento a um painel, `ci_red.json` e `bin/read_report.py --export-status`, não muda: é um contrato.

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
| `ghamon_score`, `ghamon_score_coverage`, `ghamon_score_scored` | | a pontuação da conta (0 a 100, só enquanto tem número), a proporção dos seus pesos com dados e 1 quando tem número (só Complete; veja-se SCORE.md) |
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

## O painel mínimo do Grafana

`docs/grafana/red_by_ecosystem.json` é um painel com um único gráfico: workflows vermelhos por ecossistema (consulta `ghamon_ecosystem_red_workflows`, legenda `{{ecosystem}}`). Importe-o e escolha a sua fonte Prometheus. Um teste deste repositório verifica que a métrica e a etiqueta usadas são mesmo servidas por `/metrics`.

## A fila de assinatura por confiança

Cada linha da fila tem um `trust`: `verified` (assinatura verificada com a chave pública), `unknown` (o formato não se pode verificar aqui: nunca se adivinha) ou `failed` (verificada e não corresponde). O separador Sentinela tem um filtro Assinatura com o número de cada tipo e marca as linhas (margem verde, cinzenta ou vermelha). Na consola: `py -3 bin/read_report.py --export-sign-queue FILE --sign-trust failed`.

## No modo de rede

`/metrics` e `dashboard.json` listam os seus repositórios e o seu estado: não são páginas públicas. Com o modo de rede ligado exigem o token de acesso como qualquer outro endpoint; desligue `outputs.prometheus.enabled` / `outputs.dashboard.enabled` se não quiser que esse inventário seja acessível de todo.

## Guardar e imprimir o relatório de um separador

A barra no topo da página (em todos os separadores) faz UM relatório do separador aberto e desenha-o de quatro maneiras com os mesmos dados, pelo que os formatos nunca diferem:

- **Guardar o relatório** abre uma janela com três caixas: **TXT** (marcada), **PDF** (marcada) e **JSON** (desmarcada: os dados do relatório, para outras ferramentas). Depois de aceitar, abre-se a janela **Guardar como** do navegador uma vez por formato, com o nome sugerido `monitor-<separador>-<data>.<extensão>` e o tipo de ficheiro certo (o navegador pede um clique por janela, por isso o botão passa ao formato seguinte). Um navegador sem essa janela transfere o ficheiro e a página diz onde ele ficou.
- **PDF**: o monitor escreve o PDF ele próprio, sem bibliotecas e com o tipo de letra padrão Helvetica, em inglês, espanhol, alemão, francês, italiano e português (`GET /api/report/tab.pdf`, só a partir deste computador; cada utilização deixa uma linha no registo de ações). O japonês e o chinês precisam de tipos de letra que um PDF escrito assim não tem; para eles, ou quando escolhe «O navegador» na janela, o PDF sai da janela de impressão do navegador: escolha aí **Guardar como PDF**. A página di-lo; nunca escreve um PDF com carateres estragados.
- **Imprimir** mostra o mesmo relatório sem menus nem barras (título com o nome do separador, data e hora, versão do monitor, números principais, alertas e as tabelas do separador) e abre a janela de impressão.
- O relatório é servido por `GET /api/report/tab?tab=now&lang=pt` (`&fmt=json`, `&fmt=txt` ou `&fmt=options`), igual nas duas edições.

Definições (Definições > Saídas para outras ferramentas > «Guardar e imprimir o relatório de um separador»): `report_export.txt`, `report_export.pdf` e `report_export.json` (que caixas começam marcadas: TXT e PDF sim, JSON não), `report_export.name` (nome sugerido, por omissão `monitor-{tab}-{date}`), `report_export.paper` (`a4` ou `letter`, por omissão `a4`) e `report_export.pdf_path` (`auto`, `own` ou `browser`, por omissão `auto`).

## Para onde o monitor chama, e eventos para um SIEM

- **Tabela de destinos de rede**: `monitor_cli.py doctor --egress` (também com `--json`) lista cada anfitrião que a configuração ATUAL pode chamar, para que serve, a definição que o torna destino e o que falha se for bloqueado: `api.github.com`, `github.com` e `objects.githubusercontent.com` (atualizações), `raw.githubusercontent.com` (`lint.anonymous_public`), ntfy, Telegram, os webhooks de conversa, o fornecedor de IA escolhido, o coletor OTLP e os destinos SIEM. Com `airgapped` nada está em uso. Um teste mantém a tabela igual aos anfitriões que o código nomeia.
- **SIEM** (desligado): `siem.sinks` no ficheiro lista os destinos, cada um com `enabled: true` para ser usado: `elasticsearch` (bulk), `splunk_hec`, `loki`, `sentinel` (Log Analytics, assinado com a chave partilhada), `bigquery` (`insertAll`) ou `http` (linhas JSON). O token ou a chave é lido da variável de ambiente indicada por `token_env`, nunca do ficheiro. Cada destino filtra com `from_minutes` (5), `levels` e `repos_filter`; os eventos têm uma lista fechada de campos (sem token nem texto de log); um recetor num endereço privado é recusado salvo `allow_private`; se um recetor está em baixo os eventos esperam numa fila de `siem.queue_max` (500) e os mais antigos são descartados primeiro. No modo sem ligação nada é enviado.
