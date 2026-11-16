<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](REPORT_SCHEDULE.md) | [🇪🇸 Español](REPORT_SCHEDULE_spa.md) | [🇫🇷 Français](REPORT_SCHEDULE_fra.md) | [🇮🇹 Italiano](REPORT_SCHEDULE_ita.md) | [🇩🇪 Deutsch](REPORT_SCHEDULE_deu.md) | [🇨🇳 简体中文](REPORT_SCHEDULE_zho.md) | [🇯🇵 日本語](REPORT_SCHEDULE_jpn.md) | **🇵🇹 Português**

# Relatórios agendados

Só Complete, desligado por predefinição. O monitor pode escrever um relatório da conta segundo um horário ou quando o pede: a pontuação, o que mudou desde o último relatório, os repositórios que precisam de uma pessoa e os alertas abertos, como página HTML e como Markdown. É feito com o que o monitor já tem, não pede nada ao GitHub e não envia nada para lado nenhum: os ficheiros ficam na pasta `data/reports/`.

## Como ligar

Definições, separador Sentinela, bloco **Relatórios agendados**:

| Definição | Predefinição | O que faz |
|---|---|---|
| `report_schedule.enabled` | desligado | escreve um relatório segundo o horário |
| `report_schedule.cron` | `0 8 * * 1` | cinco campos (minuto, hora, dia do mês, mês, dia da semana) na hora local deste computador; números, listas, intervalos e passos, sem nomes; `0 8 * * 1` é toda a segunda-feira às 8:00 |
| `report_schedule.formats` | ambos | `html`, `markdown` ou `both` |
| `report_schedule.keep` | 12 | quantas séries se guardam; as mais antigas são removidas |
| `report_schedule.top` | 10 | quantos repositórios e alertas mostra cada lista, os piores primeiro |

O primeiro relatório espera pelo primeiro minuto agendado depois de ligar. Escreve-se um relatório por minuto agendado, mesmo que o monitor tenha estado desligado dias (então escreve um, não uma pilha). Um relatório que falha fica registado na saúde do monitor e o minuto agendado seguinte tenta outra vez. Um agendamento que indica um dia do mês continua em dívida após uma paragem de até um mês (se indicar um mês, até um ano), e a hora que se repete quando o relógio recua no outono não é comunicada duas vezes. Um relatório é todos os seus formatos ou nada: se o segundo formato não puder ser escrito, o primeiro ficheiro é removido.

## O que leva um relatório

A pontuação da conta (com a letra e a tendência; enquanto calibra ou tem poucos dados di-lo e não mostra número), o que mudou desde o último relatório (a diferença em pontos, os alertas novos e os que desapareceram), os repositórios da vista de saúde que precisam de uma pessoa primeiro e os alertas abertos, os piores primeiro. Um alerta silenciado não está aberto. Todo o texto que vem dos dados é escapado: a página não tem scripts nem endereços externos.

## PDF

Não há um PDF próprio: abra a página HTML e imprima-a para PDF a partir do navegador. A página tem um estilo de impressão para A4.

## Onde os ver e pedir

- O separador **Equipa** tem uma secção Relatórios: a lista, uma ligação para cada ficheiro e o botão **Escrever um relatório agora** (um administrador, a partir deste computador).
- `GET /api/report-files` lista-os, `GET /api/report-files/file?name=...` abre um (só um ficheiro que o serviço escreveu para esta conta) e `POST /api/report-files/run` escreve um agora.
- No modo equipa, quem pode ver a conta pode ler os seus relatórios; escrever um agora é para um administrador neste computador. A edição Lite não tem nada disto.
