<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](TRAFFIC.md) | [🇪🇸 Español](TRAFFIC_spa.md) | [🇫🇷 Français](TRAFFIC_fra.md) | [🇮🇹 Italiano](TRAFFIC_ita.md) | [🇩🇪 Deutsch](TRAFFIC_deu.md) | [🇨🇳 简体中文](TRAFFIC_zho.md) | [🇯🇵 日本語](TRAFFIC_jpn.md) | **🇵🇹 Português**

# Transferências e tráfego

Um histórico, guardado neste computador, de quantas vezes se transferem os ficheiros das suas releases e das visitas e clonagens dos repositórios escolhidos. O GitHub só conserva 14 dias de visitas e clonagens e não dá histórico de transferências: o que não se guarda perde-se. Edição Complete; desligado por omissão.

## Ativação

Ligue `traffic.enabled` (Definições > Transferências e tráfego) e escreva os repositórios em `traffic.repos`, um por linha: um nome (da conta vigiada) ou dono/nome, no máximo 50. Com a lista vazia nada é lido. O painel aparece no separador Repositórios.

## O que se lê e quanto custa

Apenas pedidos GET, depois de um ciclo: cada repositório escolhido no máximo uma vez por dia (UTC), `traffic.repos_per_cycle` por ciclo. Um repositório custa de um a cinco pedidos da sua quota do GitHub (releases, até 300; visitas; clonagens). Se a quota acabar, para e tenta mais tarde. `traffic.views_clones` desliga as visitas e clonagens. As instalações sem rede não leem nada. Também espera enquanto não há ligação, durante a primeira leitura e quando não restam mais do dobro de `min_rate_remaining` pedidos.

## Permissões

As visitas e clonagens só são dadas a um token com acesso de escrita (push) ao repositório. Sem ele, o painel di-lo para esse repositório; não é um erro e as transferências continuam a ser guardadas.

## O que significam os valores

As transferências são anónimas, incluem robôs e espelhos e não contam os ficheiros comprimidos "Source code" que o GitHub acrescenta a uma release. As transferências novas comparam uma leitura com a anterior, apenas para os ficheiros que ainda existem. Um dia não lido é uma falha, nunca um zero.

## Exportação e privacidade

O painel exporta dois ficheiros CSV: uma linha por repositório e dia, e uma por ficheiro de release e dia em que a contagem mudou. `monitor_cli.py traffic export` imprime o primeiro. Os dias mais antigos que `traffic.keep_days` são apagados. O histórico fica na pasta de dados deste computador; nada é enviado.
