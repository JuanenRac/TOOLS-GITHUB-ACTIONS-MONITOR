<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCORE.md) | [🇪🇸 Español](SCORE_spa.md) | [🇫🇷 Français](SCORE_fra.md) | [🇮🇹 Italiano](SCORE_ita.md) | [🇩🇪 Deutsch](SCORE_deu.md) | [🇨🇳 简体中文](SCORE_zho.md) | [🇯🇵 日本語](SCORE_jpn.md) | **🇵🇹 Português**

# A pontuação de uma conta

Um número de 0 a 100, uma letra de A a E e uma tendência, para cada conta, feitos apenas com o que o monitor já sabe (as execuções concluídas e os alertas do sentinela de colaboração). Existe na edição Complete; o Lite não tem pontuação.

## De que é feita

Uma soma ponderada de cinco partes, cada uma de 0 a 100. Uma parte vale 100 no seu limite **bom**, 0 no seu limite **mau** e é linear entre os dois. Os pesos e os limites são definições.

| Parte | Peso | O que mede | Bom | Mau |
|---|---|---|---|---|
| Fiabilidade | 30 | proporção das execuções concluídas que correm bem (as canceladas e as ignoradas não contam) | 98 % | 50 % |
| Velocidade | 15 | percentil 95 da duração das execuções bem-sucedidas | 10 min | 60 min |
| Recuperação | 15 | tempo mediano desde a primeira falha de um fluxo até ao seu sucesso seguinte; um fluxo que continua a vermelho conta o tempo que está a vermelho até agora | 30 min | 24 h |
| Colaboração | 15 | tempo mediano em que um alerta do sentinela de colaboração fica aberto até desaparecer | 2 dias | 14 dias |
| Segurança | 25 | os pontos que as constatações abertas do sentinela de segurança tiram a 100 (só enquanto esse sentinela estiver ativo) | 0 pontos | 100 pontos |

A letra é A a partir de 90, B a partir de 80, C a partir de 70, D a partir de 55 e E abaixo disso. A tendência compara a pontuação com a janela imediatamente anterior: sobe, desce ou estável (uma variação inferior a `score.trend_flat` pontos é estável).

## Quando não há número

A pontuação nunca mostra um número que não consiga sustentar. A resposta traz sempre o seu `state`, a sua `coverage` e a sua `data_quality`:

- **calibrating** (a calibrar): a conta está vigiada há menos de `score.calibrating_hours` (24 por predefinição). Sem número nem letra.
- **insufficient_data** (dados insuficientes): menos de `score.min_runs` execuções concluídas na janela (20 por predefinição), ou as partes com dados pesam menos de `score.min_coverage` do total (metade por predefinição). Sem número.
- **scored** (pontuada): um número, uma letra e uma tendência. Uma parte sem dados fica de fora e as outras são reescaladas; isso baixa a `coverage` (por exemplo 0,85 quando o sentinela de colaboração está desligado). Nunca conta como 0 nem como 100.

A segurança é uma parte como as outras, mas só tem dados enquanto o sentinela de segurança estiver ativo e tiver olhado para repositórios suficientes. Sem ele, a resposta diz `complete: false` e lista `security` em `missing_parts`, e as outras partes são reescaladas, para que o número nunca seja lido como «está tudo bem». O GitHub não dá histórico das constatações, pelo que a parte de segurança é a mesma na janela e na anterior: a tendência mostra o que a CI e a colaboração fizeram. Os pesos são 30, 15, 15, 15 e 25 por predefinição. Uma janela com execuções e nenhuma falha não tem nada a recuperar: a sua parte de recuperação é completa, como um facto e não como uma lacuna.

Um fluxo que continua a vermelho no fim da janela não é esquecido: a parte de recuperação conta o tempo que está a vermelho até agora, um limite inferior que cresce enquanto o vermelho dura, por isso uma falha que ninguém corrige baixa mais o número a cada hora. Uma falha corrigida conta o seu tempo real. Uma nova execução de uma execução conta como mais uma execução do fluxo, de modo que se veem a primeira tentativa falhada e a segunda a verde. Se atualizar a partir de uma versão anterior, os números de uma conta com um fluxo a vermelho podem ser mais baixos do que antes. Quando nenhuma parte tem dados, a resposta é `insufficient_data` com o motivo `no_data`. O livro guarda no máximo 20000 execuções: quando teve de descartar execuções que pertencem à janela atual, `data_quality.truncated` é verdadeiro e `truncated` consta entre os motivos, para que uma taxa de sucesso que vê só parte da janela não seja tomada por completa. Em `GET /api/score/global`, uma conta cujo instantâneo está caducado fica fora da média e é contada em `accounts_stale`, e `/metrics` não exporta `ghamon_score` para um instantâneo caducado.

Também uma falha que atravessa o limite da janela não é esquecida: a parte de recuperação conta o troço do vermelho que cai dentro da janela (a janela anterior contou o seu próprio troço, nenhum dia é contado duas vezes), e o registo guarda a última falha de um fluxo que ninguém corrigiu enquanto a regra do vermelho ainda a mostrar (`ci.red_age_days`). Do mesmo modo, um alerta da sentinela de colaboração que continua aberto no fim da janela conta com o tempo que está aberto até agora, um limite inferior: deixar alertas por resolver baixa a parte de colaboração em vez de a deixar sem dados. Se atualizar a partir de uma versão anterior, os valores podem ser mais baixos do que antes.

Um repositório não está saudável só porque não tem nada para mostrar. Cada repositório vigiado está *ativo* (uma execução própria mais recente do que `ci.inactive_days` dias), *dormente* (nunca executou nada próprio) ou *inativo* (a sua execução mais recente é mais antiga): os repositórios dormentes e inativos não são verdes nem vermelhos e são contados à parte (`activity` do instantâneo, os números `dormant` e `inactive_repos`, a dica da ficha), pelo que uma conta com centenas de forks não mostra uma pontuação feita de nada. Um repositório que o monitor não conseguiu ler está *desconhecido*, nunca dormente. `ci.dormant_repos` desativa a contagem.

## A janela

A janela é o número de dias de execuções que a pontuação observa: `score.window_days`, 7 por predefinição, escolhido pelo utilizador para cada conta. A janela imediatamente anterior, com a mesma duração, dá a tendência. O monitor guarda um pequeno registo das execuções concluídas que viu, pelo que a janela pode ser mais longa do que a lista das últimas execuções que a página mostra. Guarda-se um instantâneo por hora, conservado tanto tempo quanto o histórico das análises (`retention.analytics_days`).

## Por repositório e por conta

Cada conta tem a sua própria pontuação. O detalhe decompõe-na por repositório (só as partes de CI, as piores primeiro). Não há um número único para toda a instalação. Apenas a título informativo, `GET /api/score/global` do supervisor dá a média das contas pontuadas que quem pergunta pode ver, ponderada pelos seus repositórios com número e sempre com quantas contas entram; uma conta sem número é listada e deixada de fora.

## Na página

Uma ficha no cabeçalho, junto às fichas de preparação, mostra a pontuação: o número, a letra, uma seta com a variação face à janela anterior e uma pequena linha dos últimos dias. A cor segue a letra (A e B verde, C âmbar, D e E vermelho). Enquanto não há número, é neutra e diz porquê (a calibrar, dados insuficientes). Uma estrela depois da letra significa que uma parte ainda não conta (hoje, a segurança): um número alto não quer então dizer que esteja tudo bem. Ao passar o rato mostra a cobertura, as partes com os seus pesos e o repositório mais fraco. A ficha não aparece no Lite nem com a pontuação desligada (`score.enabled`). Durante a calibração, a ficha diz quanto falta de `score.calibrating_hours` (`data_quality.calibrating_hours`), com uma barra e o dia e a hora em que o número vai aparecer; com dados insuficientes diz que condição falha (execuções ou cobertura), e o texto ao passar o rato diz também porque é que uma parte não conta (uma sentinela desligada, que não terminou a primeira varredura ou que leu poucos repositórios).

## Para outras ferramentas

As métricas (`/metrics`, com a saída Prometheus ativa) trazem três séries sem etiquetas: `ghamon_score_scored` (1 quando a conta tem número), `ghamon_score_coverage` (a proporção dos pesos com dados, de 0 a 1) e `ghamon_score` (o número, só enquanto existe: nunca é exportado como 0 quando não existe). O servidor MCP tem uma ferramenta só de leitura `get_score` com a resposta da API. `--demo` mostra uma pontuação inventada e não escreve nada. O painel Grafana de exemplo (`docs/grafana/monitor_dashboard.json`) tem um painel da pontuação e outro da pontuação ao longo do tempo.

## A API

`GET /api/score` responde com o último instantâneo da conta: `state`, `score`, `letter`, `trend`, `parts`, `coverage`, `data_quality`, `complete`, `missing_parts`, `repos`, `age_seconds` e `stale` (verdadeiro quando o instantâneo tem mais de três horas). `GET /api/score/history` responde com os pontos ao longo do tempo, do mais antigo ao mais recente (`?hours=` para trás a partir de agora, no máximo 90 dias, e `?limit=`, no máximo 2000). Um número em falta é `null`, nunca 0. No modo equipa, quem pode ver a conta pode ler a sua pontuação; os pesos e os limites são definições que só um administrador altera.

## O alerta por descida

Quando a pontuação desce `score.alert.drop_points` pontos (10 por predefinição) ou mais face à janela anterior, ou passa a uma letra inferior, o separador de Alertas mostra o alerta `score.dropped` (um aviso; crítico se a letra for E), com a pontuação antiga e a nova. Mantém-se enquanto o instantâneo mostrar a descida e desaparece quando a pontuação recupera, e pode ser silenciado como qualquer outro alerta. Está ativo para o painel por predefinição. Sai pelos canais de notificação externos (evento `score_dropped`) só se `score.alert.notify_external` estiver ativo, o que não acontece por predefinição, e só no momento em que aparece. `score.alert.enabled` desliga o alerta.

## As definições

Na página de Definições, subseparador Sentinela, blocos Pontuação da conta, Pesos da pontuação e Letras da pontuação: `score.enabled`, `score.window_days`, `score.calibrating_hours`, `score.min_runs`, `score.min_coverage`, `score.trend_flat`, `score.weights.reliability`, `score.weights.speed`, `score.weights.recovery`, `score.weights.collaboration`, `score.weights.security`, de `score.grades.A` a `score.grades.D`, `score.alert.enabled`, `score.alert.drop_points` e `score.alert.notify_external` (desligado por predefinição). Os limites bom e mau de cada parte são lidos do ficheiro, em `score.limits` (veja-se o ficheiro de exemplo); não se editam na página.

## Face ao período anterior

A comparação de períodos (`GET /api/compare`, `monitor_cli.py compare`) coloca a pontuação média, a proporção de execuções falhadas, as durações e o tempo de resolução de alertas de um período face ao anterior, com o mesmo registo e os mesmos registos horários da pontuação. Está desativada por predefinição (`compare.enabled`) e diz `insufficient_data` ou `baseline_unavailable` em vez de inventar um número. Ver [COMPARE_por.md](COMPARE_por.md).
