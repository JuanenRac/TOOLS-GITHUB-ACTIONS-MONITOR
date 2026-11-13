<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](QUOTAS.md) | [🇪🇸 Español](QUOTAS_spa.md) | [🇫🇷 Français](QUOTAS_fra.md) | [🇮🇹 Italiano](QUOTAS_ita.md) | [🇩🇪 Deutsch](QUOTAS_deu.md) | [🇨🇳 简体中文](QUOTAS_zho.md) | [🇯🇵 日本語](QUOTAS_jpn.md) | **🇵🇹 Português**

# Quotas e planos

O monitor é usado por todos os tipos de conta, por isso nunca assume nenhum. Os valores abaixo estão em `monitor/assets/examples/quotas.json` (uma cópia chamada `quotas.json` junto dos lançadores tem prioridade) (edite-o para acompanhar as mudanças do GitHub sem uma versão nova do monitor) e foram confrontados com a documentação pública do GitHub; mudam com o tempo, por isso use-os como ponto de partida e consulte as páginas indicadas no ficheiro. Escolha o seu plano em **Definições > Básico** (`account.plan`); enquanto for *desconhecido* não se mostra nenhum valor de quota.

## A quota da API

| Como inicia sessão | Chamadas por hora |
|---|---|
| Sem sessão | 60 por hora e por endereço |
| A sua sessão (`gh auth login`) ou um token pessoal | 5.000 |
| O token de um workflow (dentro do Actions) | 1.000 por repositório (15.000 no Enterprise Cloud) |
| Uma aplicação no Enterprise Cloud | 15.000 |
| Uma GitHub App noutros casos | 5.000, cresce com a instalação até 12.500 |

A página mostra o limite real lido dos cabeçalhos do GitHub (`X-RateLimit-*`), nunca um 5.000 assumido: é também isso que faz funcionar o GitHub Enterprise Server (`GH_HOST`). Sem sessão (60 por hora) aconselha `gh auth login`. Existe ainda um limite *secundário* (no máximo 100 pedidos em simultâneo e rajadas): quando o GitHub responde com ele, o monitor espera pelo menos um minuto, depois duplica a espera até cinco minutos e nunca insiste em bloco.

## Minutos do Actions

| Plano | Incluído por mês (em dinheiro) | Em minutos Linux | Armazenamento de artefactos |
|---|---|---|---|
| Free | 12 $ | 2.000 | 500 MB |
| Pro | 18 $ | 3.000 | 1 GB |
| Team | 18 $ | 3.000 | 2 GB |
| Enterprise Cloud | 300 $ | 50.000 | 50 GB |

**Os repositórios públicos não gastam minutos em nenhum plano** (os runners próprios também não); os runners maiores são sempre faturados. Um minuto multiplica-se pela tarifa do seu sistema: o Windows vale cerca de 1,67 minutos de Linux e o macOS cerca de 10,3 (tarifas por minuto em `quotas.json`: 0,006 $ Linux, 0,010 $ Windows, 0,062 $ macOS). O que o monitor mostra em **Definições > Básico > Plano e quotas** é uma **estimativa**: a duração dos runs das últimas 24 horas, arredondada ao minuto, só de repositórios privados, com o sistema que assume em `quota.default_runner`, e o ritmo de um dia multiplicado pelos dias do mês. Os valores reais só vêm do interruptor opcional `quota.billing_api` (desligado por defeito, só de leitura, precisa de uma sessão com permissão para ver a faturação; com um 403 ou 404 a estimativa mantém-se e di-lo). Envia-se um aviso pelas notificações uma vez por mês a `quota.warn_percent` (75 %) e a `quota.alert_percent` (90 %) dos minutos incluídos.

## Concorrência e limites

| Plano | Jobs em simultâneo | dos quais macOS |
|---|---|---|
| Free | 20 | 5 |
| Pro | 40 | 5 |
| Team | 60 | 5 |
| Enterprise | 500 | 50 |

O painel compara os jobs em curso e em fila com o limite do seu plano e avisa aos 90 % ou quando há jobs à espera com o limite cheio. Um job pode durar no máximo 6 horas num runner do GitHub (o painel lista os que passam de 80 %), um run de workflow dura no máximo 35 dias e uma matriz tem até 256 jobs.

## O que não está coberto

Não se acompanham os preços por minuto extra, os runners maiores, o armazenamento em uso, o Codespaces nem o Packages; a tabela de planos é um ponto de partida e os limites do macOS mudam. Nada disto foi ainda experimentado com um relatório de faturação real: a leitura de `usageItems` segue a descrição pública e degrada em silêncio.
