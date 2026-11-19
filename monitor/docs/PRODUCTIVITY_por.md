<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](PRODUCTIVITY.md) | [🇪🇸 Español](PRODUCTIVITY_spa.md) | [🇫🇷 Français](PRODUCTIVITY_fra.md) | [🇮🇹 Italiano](PRODUCTIVITY_ita.md) | [🇩🇪 Deutsch](PRODUCTIVITY_deu.md) | [🇨🇳 简体中文](PRODUCTIVITY_zho.md) | [🇯🇵 日本語](PRODUCTIVITY_jpn.md) | **🇵🇹 Português**

# O que o monitor poupa: uma estimativa e como a medir

Este guia explica os números do README. São uma estimativa feita com um modelo simples, não uma medição feita nos seus repositórios. Meça os seus antes de confiar neles.

## Os números

- Cerca de 85-95 % do tempo gasto a vigiar a CI e a triar falhas.
- Cerca de 15-25 % da produtividade global de uma equipa, em consequência do primeiro número.

## Como a estimativa é construída

Tempo poupado numa semana = a soma, sobre as tarefas, de (vezes por semana x minutos de cada vez sem o monitor) x a poupança dessa tarefa. As tarefas são: vigiar cada fluxo de trabalho, decidir o que está mesmo a vermelho, encontrar a causa de uma execução falhada e saber a tempo de uma falha. A estimativa pressupõe que:

1. Há muitos repositórios com vários fluxos de trabalho cada um, pelo que olhar para eles à mão obriga a abrir muitas páginas vezes sem conta.
2. Sem o monitor, alguém verifica à mão os separadores Actions e lê cada registo falhado para encontrar a causa. Com ele, a página e os alertas já dizem que fluxo está a vermelho e porquê.
3. Há falhas todas as semanas. Uma equipa sem falhas não tem nada para triar.
4. A poupança abrange apenas a vigilância e a triagem. Corrigir uma falha demora o mesmo com ou sem o monitor e não conta.

Os dois números só concordam se vigiar e triar ocuparem entre 16 e 29 % do tempo de trabalho da equipa (0,15 / 0,95 a 0,25 / 0,85). Se na sua equipa ocuparem menos, o ganho global é menor.

## Quando poupa menos

- Poucos repositórios ou um único fluxo de trabalho: há pouco para vigiar.
- Hoje ninguém vigia a CI à mão, ou já tem alertas que nomeiam a causa.
- Os alertas não são lidos. Lê-los também demora, e a poupança desaparece se forem ignorados ou silenciados sem motivo.

## Como medi-lo na sua própria utilização

1. Antes: durante uma semana normal, anote cada vez que olha para a CI à mão (minutos) e cada execução falhada que tria (minutos até saber a causa).
2. Depois: repita as mesmas notas durante uma semana com o monitor aberto. A pontuação (tempo de recuperação) e o livro de falhas (tendência a 24 horas e 7 dias) mostram se as falhas se fecham mais depressa.
3. Para cada grupo, a poupança é 1 - depois / antes. Compare-a com 85-95 %.
4. Para o ganho global, divida as horas poupadas pelo total de horas trabalhadas nessa semana. Compare-o com 15-25 %.

### Exemplo com números inventados

Alguém gasta 20 minutos por dia a olhar para os separadores Actions (100 minutos numa semana de cinco dias) e tria 4 execuções falhadas por semana a 30 minutos cada (120 minutos): 220 minutos ao todo. Com 85-95 % de poupança, ficam livres entre 187 e 209 minutos. Estes números são inventados para mostrar o cálculo; use os seus.
