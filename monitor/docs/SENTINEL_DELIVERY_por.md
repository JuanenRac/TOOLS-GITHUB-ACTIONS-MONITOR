<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_DELIVERY.md) | [🇪🇸 Español](SENTINEL_DELIVERY_spa.md) | [🇫🇷 Français](SENTINEL_DELIVERY_fra.md) | [🇮🇹 Italiano](SENTINEL_DELIVERY_ita.md) | [🇩🇪 Deutsch](SENTINEL_DELIVERY_deu.md) | [🇨🇳 简体中文](SENTINEL_DELIVERY_zho.md) | [🇯🇵 日本語](SENTINEL_DELIVERY_jpn.md) | **🇵🇹 Português**

# O sentinela de entrega

O quinto sentinela, a par dos de CI, Collab, Segurança e Cadeia de abastecimento. Lê, sem escrever nada no GitHub, as últimas versões publicadas, as últimas etiquetas, o CHANGELOG e os ficheiros de versão que indicar de cada repositório (pela API, sem clonar) e avisa do que foi construído mas não entregue. Transforma isso em alertas do separador Alertas (origem Entrega). Está na edição Complete, desligado por predefinição (`sentinels.delivery.enabled`); o Lite não tem sentinelas.

## O que assinala

| Sinal | Alerta | Nível | Ativo por predefinição |
|---|---|---|---|
| O CHANGELOG tem entradas em `[Unreleased]` e a última versão publicada tem mais de `sentinels.delivery.unreleased_days` dias (14) | `release.unreleased_pending` | info | sim |
| Uma etiqueta de versão mais recente do que a última versão publicada e sem versão própria (um rascunho não conta como entregue) | `release.tag_without_release` | warning | sim |
| A última versão publicada tem a descrição vazia | `release.release_without_notes` | info | sim |
| Os ficheiros de versão de `version_files` e o primeiro título com versão do CHANGELOG não declaram todos a mesma versão (`1.2` e `1.2.0` são a mesma) | `release.version_mismatch` | warning | sim |
| Um repositório fixa uma versão mais antiga do que a última do repositório que fornece um contrato partilhado (as tabelas de fixação de `sentinel.readiness.pins.sources`, tipo `pin_table`) | `release.ecosystem_drift` | warning | sim |
| A última versão publicada não tem um ficheiro para algum dos padrões de `expected_assets` (por exemplo `*.zip`, `SHA256SUMS*`) | `release.assets_missing` | warning | sim |

Há um alerta por repositório e sinal, com os números e algumas etiquetas, padrões ou versões nos detalhes. Cada sinal pode ser desligado (`sentinels.delivery.signals.<sinal>.enabled`) e receber outro nível (`info`, `warning`, `error`, `critical`). Um repositório sem nenhuma versão publicada não é avaliado pelos sinais sobre versões: não as usa. As pré-versões e os rascunhos nunca são tomados como a última versão.

## Um dono para cada achado

O painel de preparação do separador Sentinela (A11) é uma linha por repositório obtida de clones locais; este sentinela produz alertas com identificador estável, silenciamentos, eventos e ciclo próprio, lidos pela API sem clonar. Os sinais sobre os workflows de um repositório pertencem ao sentinela de Cadeia de abastecimento e os das definições do GitHub à Segurança: nada é gerado duas vezes. O plugin opcional «Releases» do roteiro é substituído por este sentinela.

## O que não conseguiu verificar

Um repositório que não pode ser lido (sem acesso, SSO não autorizado, quota esgotada, uma ronda com menos chamadas do que as de que um repositório precisa) **não** é um alerta e **não** é um resultado limpo. Fica listado no estado em `unavailable`, com o motivo e quantos, e um nível `ok` aparece como `unknown` quando a maior parte do que foi visto não pôde ser lida. Se um repositório deixar de responder enquanto tem alertas, estes ficam uma semana (marcados `unread_since`) e nunca são anunciados como resolvidos. Um ficheiro que não existe (sem CHANGELOG nesse caminho, sem esse ficheiro de versão) simplesmente falta. As tabelas de fixação são lidas uma vez por ciclo; uma que não possa ser lida mantém os seus alertas e também fica listada.

## Custo

Uma ronda lê no máximo `sentinels.delivery.max_repos_per_tick` repositórios (10 por predefinição) e faz no máximo `sentinels.delivery.max_calls_per_tick` chamadas (60): uma para as versões e uma para as etiquetas, uma para o CHANGELOG (mais se indicar vários caminhos e os primeiros não existirem) e uma por cada ficheiro de versão. Um sinal desligado não é lido de todo. Os lidos há mais tempo vão primeiro e os que têm um alerta aberto um pouco antes; um ciclo a cada `sentinels.delivery.refresh_seconds` (uma hora por predefinição). Não há pedidos condicionais: o custo é limitado por estas definições, não por uma resposta 304. O sentinela fica em pausa enquanto a quota restante for inferior a `sentinels.delivery.min_rate_remaining`. O seu estado (`delivery_state.json`) guarda os alertas abertos, por isso um reinício não volta a anunciar nada, e o primeiro olhar a um repositório não escreve nenhum evento.

## Eventos, notificações e pontuação

Um achado novo escreve o evento `delivery_new` e um encerrado `delivery_fixed` (o evento diz `sentinel: delivery` e o código do alerta). Pertencem à família das versões, por isso só os responsáveis e os administradores os podem escolher, e a escolha do sentinela `ci` nas preferências de notificação de cada utilizador decide quem os recebe; não estão em nenhuma lista de eventos predefinida. As métricas trazem `delivery_alerts`, `delivery_unreleased_repos`, `delivery_unreleased_days_max`, `delivery_repos_checked`, `delivery_repos_unreadable` e `delivery_calls_last_hour`. A pontuação não as usa. A API responde a `GET /api/sentinel/delivery` e o separador Alertas e `monitor_cli.py alerts --sentinel delivery` filtram por ele.

## As definições

Na página Definições, subseparador Sentinela, bloco Entrega: `sentinels.delivery.enabled`, `sentinels.delivery.refresh_seconds`, `sentinels.delivery.max_repos_per_tick`, `sentinels.delivery.max_calls_per_tick`, `sentinels.delivery.min_rate_remaining`, `sentinels.delivery.repos`, `sentinels.delivery.unreleased_days`, `sentinels.delivery.unreleased_min_entries`, `sentinels.delivery.changelog_paths`, `sentinels.delivery.version_files`, `sentinels.delivery.expected_assets`, `sentinels.delivery.signals.unreleased_pending.enabled`, `sentinels.delivery.signals.unreleased_pending.level`, `sentinels.delivery.signals.tag_without_release.enabled`, `sentinels.delivery.signals.tag_without_release.level`, `sentinels.delivery.signals.release_without_notes.enabled`, `sentinels.delivery.signals.release_without_notes.level`, `sentinels.delivery.signals.version_mismatch.enabled`, `sentinels.delivery.signals.version_mismatch.level`, `sentinels.delivery.signals.ecosystem_drift.enabled`, `sentinels.delivery.signals.ecosystem_drift.level`, `sentinels.delivery.signals.assets_missing.enabled`, `sentinels.delivery.signals.assets_missing.level`.

## O que não faz

Não escreve no GitHub (nem etiqueta, versão, rótulo, pull request ou issue), não publica nem assina nada, não cria propostas a partir dos seus alertas e não lê o conteúdo de nenhum ficheiro além do CHANGELOG e dos ficheiros de versão que indicar.
