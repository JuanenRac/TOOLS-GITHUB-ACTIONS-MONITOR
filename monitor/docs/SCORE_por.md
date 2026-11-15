<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCORE.md) | [🇪🇸 Español](SCORE_spa.md) | [🇫🇷 Français](SCORE_fra.md) | [🇮🇹 Italiano](SCORE_ita.md) | [🇩🇪 Deutsch](SCORE_deu.md) | [🇨🇳 简体中文](SCORE_zho.md) | [🇯🇵 日本語](SCORE_jpn.md) | **🇵🇹 Português**

# A pontuação de uma conta

Um número de 0 a 100, uma letra de A a E e uma tendência, para cada conta, feitos apenas com o que o monitor já sabe (as execuções concluídas e os alertas do sentinela de colaboração). Existe na edição Complete; o Lite não tem pontuação.

## De que é feita

Uma soma ponderada de quatro partes, cada uma de 0 a 100. Uma parte vale 100 no seu limite **bom**, 0 no seu limite **mau** e é linear entre os dois. Os pesos e os limites são definições.

| Parte | Peso | O que mede | Bom | Mau |
|---|---|---|---|---|
| Fiabilidade | 40 | proporção das execuções concluídas que correm bem (as canceladas e as ignoradas não contam) | 98 % | 50 % |
| Velocidade | 20 | percentil 95 da duração das execuções bem-sucedidas | 10 min | 60 min |
| Recuperação | 20 | tempo mediano desde a primeira falha de um fluxo até ao seu sucesso seguinte | 30 min | 24 h |
| Colaboração | 20 | tempo mediano em que um alerta do sentinela de colaboração fica aberto até desaparecer | 2 dias | 14 dias |

A letra é A a partir de 90, B a partir de 80, C a partir de 70, D a partir de 55 e E abaixo disso. A tendência compara a pontuação com a janela imediatamente anterior: sobe, desce ou estável (uma variação inferior a `score.trend_flat` pontos é estável).

## Quando não há número

A pontuação nunca mostra um número que não consiga sustentar. A resposta traz sempre o seu `state`, a sua `coverage` e a sua `data_quality`:

- **calibrating** (a calibrar): a conta está vigiada há menos de `score.calibrating_hours` (24 por predefinição). Sem número nem letra.
- **insufficient_data** (dados insuficientes): menos de `score.min_runs` execuções concluídas na janela (20 por predefinição), ou as partes com dados pesam menos de `score.min_coverage` do total (metade por predefinição). Sem número.
- **scored** (pontuada): um número, uma letra e uma tendência. Uma parte sem dados fica de fora e as outras são reescaladas; isso baixa a `coverage` (por exemplo 0,8 quando o sentinela de colaboração está desligado). Nunca conta como 0 nem como 100.

A segurança ainda não é uma parte. Até lá, cada resposta diz `complete: false` e lista `security` em `missing_parts`, para que um 85 nunca seja lido como «está tudo bem».

## A janela

A janela é o número de dias de execuções que a pontuação observa: `score.window_days`, 7 por predefinição, escolhido pelo utilizador para cada conta. A janela imediatamente anterior, com a mesma duração, dá a tendência. O monitor guarda um pequeno registo das execuções concluídas que viu, pelo que a janela pode ser mais longa do que a lista das últimas execuções que a página mostra. Guarda-se um instantâneo por hora, conservado tanto tempo quanto o histórico das análises (`retention.analytics_days`).

## Por repositório e por conta

Cada conta tem a sua própria pontuação. O detalhe decompõe-na por repositório (só as partes de CI, as piores primeiro). Não há um número único para toda a instalação.

## Na página

Uma ficha no cabeçalho, junto às fichas de preparação, mostra a pontuação: o número, a letra, uma seta com a variação face à janela anterior e uma pequena linha dos últimos dias. A cor segue a letra (A e B verde, C âmbar, D e E vermelho). Enquanto não há número, é neutra e diz porquê (a calibrar, dados insuficientes). Uma estrela depois da letra significa que uma parte ainda não conta (hoje, a segurança): um número alto não quer então dizer que esteja tudo bem. Ao passar o rato mostra a cobertura, as partes com os seus pesos e o repositório mais fraco. A ficha não aparece no Lite nem com a pontuação desligada (`score.enabled`).

## A API

`GET /api/score` responde com o último instantâneo da conta: `state`, `score`, `letter`, `trend`, `parts`, `coverage`, `data_quality`, `complete`, `missing_parts`, `repos`, `age_seconds` e `stale` (verdadeiro quando o instantâneo tem mais de três horas). `GET /api/score/history` responde com os pontos ao longo do tempo, do mais antigo ao mais recente (`?hours=` para trás a partir de agora, no máximo 90 dias, e `?limit=`, no máximo 2000). Um número em falta é `null`, nunca 0. No modo equipa, quem pode ver a conta pode ler a sua pontuação; os pesos e os limites são definições que só um administrador altera.

## As definições

Na página de Definições, subseparador Sentinela, blocos Pontuação da conta, Pesos da pontuação e Letras da pontuação: `score.enabled`, `score.window_days`, `score.calibrating_hours`, `score.min_runs`, `score.min_coverage`, `score.trend_flat`, `score.weights.reliability`, `score.weights.speed`, `score.weights.recovery`, `score.weights.collaboration`, de `score.grades.A` a `score.grades.D`, `score.alert.enabled`, `score.alert.drop_points` e `score.alert.notify_external` (desligado por predefinição). Os limites bom e mau de cada parte são lidos do ficheiro, em `score.limits` (veja-se o ficheiro de exemplo); não se editam na página.
