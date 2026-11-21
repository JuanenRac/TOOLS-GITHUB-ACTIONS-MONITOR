<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPARE.md) | [🇪🇸 Español](COMPARE_spa.md) | [🇫🇷 Français](COMPARE_fra.md) | [🇮🇹 Italiano](COMPARE_ita.md) | [🇩🇪 Deutsch](COMPARE_deu.md) | [🇨🇳 简体中文](COMPARE_zho.md) | [🇯🇵 日本語](COMPARE_jpn.md) | **🇵🇹 Português**

# Comparar períodos

Como correu esta semana em relação à passada? A comparação responde com o que o monitor já guarda (o registo das execuções e dos alertas concluídos e os registos horários da pontuação). Não lê nada do GitHub, não escreve nada, não precisa de IA e não inventa nada. Existe apenas na edição Completa e está **desativada** até ativar `compare.enabled`.

## Os dois períodos

- **Período**: os últimos 7 dias (ou 30, ou qualquer número até 90), ou um intervalo exato com `from` e `to`.
- **Referência**: `previous` (o período da mesma duração imediatamente antes, por predefinição), `year_ago` (as mesmas datas de há um ano) ou `custom` (`base_from` e `base_to`).
- **Dias**: `all`, `workdays` ou `weekend`. O filtro aplica-se a todos os números. O dia de um instante é o seu dia no fuso horário de `display.timezone`; os dias úteis são `compare.workdays` (de segunda = 1 a domingo = 7, de segunda a sexta por predefinição). Os feriados não são conhecidos: um feriado conta como o dia da semana em que calha.

Misturar dias úteis e fins de semana esconde coisas (uma falha que só acontece aos sábados pesa pouco numa semana de dados misturados), e é por isso que o filtro existe.

## Os números

| Número | Como se calcula | Melhor quando |
|---|---|---|
| `red_rate` | execuções falhadas / (bem-sucedidas + falhadas) iniciadas no período | é menor |
| `duration_p50` | mediana dos segundos das execuções bem-sucedidas | é menor |
| `resolution` | mediana do tempo entre a abertura e o fecho dos alertas do sentinela de colaboração fechados no período | é menor |
| `score_mean` | pontuação média dos registos horários que tinham número | é maior |
| `score_coverage` | parte média da pontuação que tinha dados | é maior |

Cada número viaja com `now`, `base`, `delta`, uma `direction` (`better`, `worse`, `same`) e o seu `state`. As execuções canceladas, ignoradas e por concluir não contam em nenhum sentido.

## Quando não há número

A comparação nunca mostra um número que não consiga sustentar: um número em falta é `null`, nunca 0 nem 100.

- `insufficient_data`: menos execuções concluídas do que `compare.min_runs_per_window`, menos alertas resolvidos do que `compare.min_resolved` ou menos registos do que `compare.min_snapshots` num dos dois períodos. A resposta diz qual e porquê (`missing`).
- `baseline_unavailable`: o período de referência não é fiável. O motivo é `history_too_short` (o monitor vigia há menos de `compare.min_days_of_history` dias), `before_history` (esse período é anterior aos dados guardados) ou `no_history`. Os números do período atual continuam a ser mostrados.
- `calibrating`: o monitor ainda não vigiou `score.calibrating_hours` horas. Não se compara nada.
- `off`: `compare.enabled` está desativado.

`data_quality` leva as execuções contadas em cada período e `truncated` quando o registo teve de descartar execuções antigas. `coverage` é a parte dos números que se conseguiu comparar.

## O que mudou

Além dos números: os repositórios que pioram ou melhoram (variação da sua proporção de execuções falhadas, só os que têm pelo menos `compare.min_repo_runs` execuções nos dois períodos), os workflows que começaram a falhar e os que deixaram de falhar, e o número de alertas abertos no período e ainda abertos no fim. Cada lista tem no máximo `compare.top_changes` linhas, ordenadas pela dimensão da variação e depois por nome. O registo não guarda o repositório dos alertas do sentinela de colaboração, por isso aparecem como contagens, nunca por nome.

## Até onde chega para trás

A comparação lê o registo da pontuação. Enquanto `compare.enabled` estiver ativo, o registo conserva dois períodos de `compare.default_window_days` (pelo menos 15 dias) em vez das duas janelas da pontuação; nunca é mais antigo do que o monitor, pelo que uma instalação nova só pode comparar 30 dias com 30 dias quando tiver 60 dias de histórico.

## A API

`GET /api/compare?window=7&days=workdays&baseline=previous` (também `from`, `to`, `base_from`, `base_to`). Responde `state`, `windows`, `metrics`, `changes`, `alerts`, `coverage` e `data_quality`. `format=ndjson` ou `format=csv` dão uma linha por número. Um pedido sem sentido é um 400 com um `code` estável: `bad_range` (from depois de to, mais de 90 dias, no futuro), `bad_window`, `bad_days`, `bad_baseline` ou `bad_format`. Um leitor pode lê-la; serve a conta do processo, nunca outra. Com a API de leitura v1 ativada é também servida sob o prefixo `/api/v1/`. Não existe na edição Lite.

## A linha de comandos

`monitor_cli.py compare [--window 7|30d] [--days all|workdays|weekend] [--baseline previous|year_ago] [--format table|json|ndjson|csv]`. Códigos de saída: 0 tudo foi comparado; 4 um número tem poucos dados, não há referência ou a comparação está desativada; 5 com `--fail-on` quando um número piora. `score --compare` continua a comparar a pontuação com o histórico da sua janela.

## Na página

O separador Gráficos mostra a secção «Comparar períodos» quando a comparação está ativa: um seletor de período, dias e referência, uma linha por número com a sua variação, os alertas e as listas de alterações.

## Respostas frescas, obsoletas e lentas

A comparação e os relatórios opcionais são consultas pesadas, por isso a sua resposta guarda-se em memória e cada pedido encontra-a num de três estados. **Fresca** (mais nova do que `cache.heavy_fresh_s`, 5 segundos): serve-se tal como está, sem a calcular outra vez. **Obsoleta** (mais velha do que isso e mais nova do que `cache.stale_serve_h` horas, 1 hora): serve-se de imediato e marca-se com `X-Monitor-Freshness: stale` / `X-Monitor-Age: N` enquanto um cálculo a renova em segundo plano; uma resposta fresca não leva esse cabeçalho. **Caducada** (mais velha ou nunca feita): calcula-se agora, e uma cópia tão velha nunca se serve. Um cálculo tem um teto, `analytics.query_timeout_s` (120 segundos): passado esse tempo a resposta é `504` com o código `query_timeout` em vez de esperar para sempre; um cálculo não se pode matar, por isso termina sozinho, a sua resposta guarda-se para o pedido seguinte e entretanto não se começa um segundo cálculo da mesma consulta. Nada disto chama o GitHub.

## As definições

Definições, separador Sentinela, bloco Comparação de períodos: `compare.enabled`, `compare.default_window_days`, `compare.default_days_filter`, `compare.workdays`, `compare.min_runs_per_window`, `compare.min_days_of_history`, `compare.min_resolved`, `compare.min_snapshots`, `compare.min_repo_runs`, `compare.top_changes`, `compare.include_in_report` e `compare.cache_seconds`. Uma resposta é guardada `compare.cache_seconds` segundos e depois calculada de novo.

## Janelas longas numa conta grande

Com `compare.progressive` ligado (desligado por predefinição) uma comparação sobre uma janela mais longa do que `compare.progressive_days` (7 por predefinição) é respondida já com os seus últimos dias e a resposta di-lo (`partial`: os dias pedidos, os dias mostrados e que o resto está a ser calculado); a janela inteira é terminada em segundo plano e o pedido seguinte, ou a próxima atualização da página, recebe-a. Um pedido com `from` e `to` nunca é dividido.
