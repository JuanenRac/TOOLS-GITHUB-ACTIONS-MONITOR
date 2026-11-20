<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_SUPPLY.md) | [🇪🇸 Español](SENTINEL_SUPPLY_spa.md) | [🇫🇷 Français](SENTINEL_SUPPLY_fra.md) | [🇮🇹 Italiano](SENTINEL_SUPPLY_ita.md) | [🇩🇪 Deutsch](SENTINEL_SUPPLY_deu.md) | [🇨🇳 简体中文](SENTINEL_SUPPLY_zho.md) | [🇯🇵 日本語](SENTINEL_SUPPLY_jpn.md) | **🇵🇹 Português**

# O sentinela da cadeia de abastecimento

O quarto sentinela, ao lado dos de CI, Collab e Segurança. Lê, sem escrever nada no GitHub, os ficheiros de fluxo de cada repositório (`.github/workflows`, pela API, sem clonar) e assinala o que permite que uma etiqueta movida ou um estranho atue com o token e o código do repositório. Transforma isso em alertas do separador Alertas (origem Cadeia de abastecimento). Está na edição Completa, desligado por predefinição (`sentinels.supply.enabled`); o Lite não tem sentinelas.

Tem a sua própria entrada no grupo Sentinela do menu, **Sentinela da cadeia de fornecimento** (endereço `#sentinel-supply`), visível enquanto o sentinela está ligado: um painel com os achados abertos de cada repositório, o estado do seu ciclo e o que não foi possível ler; o distintivo da entrada conta os erros.

## O que assinala

| Sinal | Alerta | Nível | Ativo por predefinição |
|---|---|---|---|
| Um `uses:` de uma ação ou fluxo reutilizável não fixado a um SHA de commit completo (o dono pode mover a etiqueta) | `actions.supply.unpinned` | warning | sim |
| Um `uses:` que segue um ramo que se move sozinho (`@main`, `@master`...): pior do que uma etiqueta | `actions.supply.mutable_ref` | warning | sim |
| Um fluxo com `permissions: write-all` | `actions.supply.permissions_wide` | warning | sim |
| Um fluxo sem bloco `permissions:` (o token recebe a permissão predefinida, mais ampla) | `actions.supply.permissions_missing` | warning | sim |
| `pull_request_target` junto com a obtenção do código do pull request | `actions.supply.pr_target_checkout` | error | sim |

Há um alerta por repositório e sinal, com o número de deteções, os ficheiros onde estão e alguns exemplos (o nome de uma ação) nos detalhes. Cada sinal pode ser desligado (`sentinels.supply.signals.<sinal>.enabled`) e receber outro nível (`info`, `warning`, `error`, `critical`). Um `uses:` de um fluxo do mesmo repositório não é de terceiros e fica de fora.

## Uma única fonte de verdade

Não tem regras próprias: as deteções vêm do linter de fluxos (`bin/lint_workflows.py`, o mesmo do separador Sentinela e da linha de comandos); aqui só estão ativas `unpinned_uses`, `permissions` e `pr_target`, e as outras regras ficam desligadas. Em concreto, a regra que procura segredos escritos num ficheiro está desligada, por isso **o valor de um segredo nunca é lido, guardado nem mostrado**. As definições `lint.own_owners` e `lint.unpinned_own` continuam a decidir como se trata uma ação da própria conta, e um comentário `# monitor-lint: ignore REGRA` num fluxo silencia a deteção ali mesmo.

## Um dono para cada deteção

`security.workflow_write` (sentinela de Segurança) é a permissão predefinida do repositório, uma definição do GitHub; os sinais daqui tratam do conteúdo de cada ficheiro de fluxo, por isso um repositório nunca levanta a mesma deteção pelos dois. O painel do lint do separador Sentinela continua a ser um painel; os alertas do separador Alertas sobre estes sinais vêm só daqui.

## O que não conseguiu verificar

Um repositório cujos fluxos não se conseguem ler (sem acesso, SSO não autorizado, quota gasta, uma pasta com demasiados ficheiros) **não** é um alerta e **não** é um atestado de saúde. Fica listado no estado em `unavailable`, com o motivo e quantos repositórios, e um nível `ok` aparece como `unknown` quando a maior parte do que foi visto não se pôde ler. Se um repositório deixar de responder enquanto tem alertas, estes ficam uma semana (marcados `unread_since`) e nunca são anunciados como resolvidos. Um repositório sem pasta `.github/workflows` é lido e simplesmente não tem nada a assinalar. Um repositório cujas leituras continuam a falhar espera 5 minutos, 30 minutos e depois 6 horas antes da tentativa seguinte.

## Custo

Uma ronda lê, no máximo, `sentinels.supply.max_repos_per_tick` repositórios (10 por predefinição) e faz, no máximo, `sentinels.supply.max_calls_per_tick` chamadas (60): uma para listar os fluxos de um repositório e mais uma por cada ficheiro novo ou alterado, porque um ficheiro cujo SHA não mudou não volta a ser lido. Vão primeiro os lidos há mais tempo e um pouco antes os que têm um alerta aberto; um ciclo a cada `sentinels.supply.refresh_seconds` (uma hora por predefinição). O sentinela fica em pausa enquanto a quota restante estiver abaixo de `sentinels.supply.min_rate_remaining`. O seu estado (`supply_state.json`) guarda os alertas abertos, por isso um reinício não anuncia nada de novo, e a primeira vista a um repositório não escreve nenhum evento. `sentinels.supply.max_files_per_repo` limita os ficheiros lidos num repositório; um repositório acima do limite é lido em parte e contado como parcial. Uma ronda também deixa de começar repositórios novos passados `sentinels.supply.deadline_s` segundos (30 por predefinição; 0 = sem teto): os que não foram alcançados esperam pela ronda seguinte e o estado lista-os por nome como `unchecked` (com `round_cut`) em vez de os contar como zero alertas.

Com `sentinels.supply.incremental` (desativado por defeito) um repositório cujos ficheiros de workflow (os seus SHA de blob) e regras são os mesmos da última passagem boa não é analisado de novo e os seus avisos ficam exatamente como estão: não olhar nunca fecha um aviso, e a alteração de uma regra, da lista de ignorados ou da versão do programa faz com que todos os repositórios sejam analisados de novo. O estado indica quantos repositórios ficaram sem alterações (`unchanged`). É uma escolha para repositórios que conhece, não um valor herdado.

## Ignorar uma deteção

`sentinels.supply.ignore` aceita padrões `repositório:ficheiro:regra` (com `*` para qualquer) que nomeiam a regra do linter, por exemplo `meurepo:release.yml:unpinned_uses`; `unpinned_uses` é a regra por trás de `unpinned` e `mutable_ref`, e `permissions` a dos dois sinais de permissões. Os padrões de `lint.ignore` não se aplicam aqui.

`sentinels.supply.ignore_uses` aceita nomes `proprietário/repositório` (com `*` para qualquer, por exemplo `other-org/*`) de ações ou fluxos reutilizáveis de outra organização privada que o acesso não consegue ver e cuja referência o monitor não consegue avaliar: as suas referências não fixadas ou móveis ficam fora dos achados e são contadas à parte como `uses_left_out` no estado, pelo que nem são avisadas por suposição nem escondidas.

## Eventos, notificações e pontuação

Uma deteção nova escreve o evento `security_new` e uma fechada `security_fixed` (o evento indica `sentinel: supply` e o código do alerta), pelo que a caixa Segurança das preferências de notificação de cada utilizador e os canais decidem quem fica a saber. Não se anuncia nada na primeira vez que se olha para um repositório. As métricas incluem `supply_alerts`, `supply_findings`, `supply_penalty` (informativa: `sentinels.supply.penalty.per_finding`, 2, e `cap_per_repo`, 10, são lidos do ficheiro), `supply_repos_checked`, `supply_repos_unreadable` e `supply_calls_last_hour`. A pontuação não usa a penalização. A API responde a `GET /api/sentinel/supply`, e o separador Alertas e `monitor_cli.py alerts --sentinel supply` filtram por ele.

## As definições

Na página Definições, subseparador Sentinela, bloco Cadeia de abastecimento: `sentinels.supply.enabled`, `sentinels.supply.incremental`, `sentinels.supply.refresh_seconds`, `sentinels.supply.max_repos_per_tick`, `sentinels.supply.max_calls_per_tick`, `sentinels.supply.max_files_per_repo`, `sentinels.supply.min_rate_remaining`, `sentinels.supply.repos`, `sentinels.supply.ignore`, `sentinels.supply.ignore_uses`, `sentinels.supply.signals.unpinned.enabled`, `sentinels.supply.signals.unpinned.level`, `sentinels.supply.signals.mutable_ref.enabled`, `sentinels.supply.signals.mutable_ref.level`, `sentinels.supply.signals.permissions_wide.enabled`, `sentinels.supply.signals.permissions_wide.level`, `sentinels.supply.signals.permissions_missing.enabled`, `sentinels.supply.signals.permissions_missing.level`, `sentinels.supply.signals.pr_target_checkout.enabled`, `sentinels.supply.signals.pr_target_checkout.level`.

## O que não faz

Não escreve no GitHub (nem pull requests, nem etiquetas, nem issues), não propõe o SHA a que fixar uma ação e não lê o valor de nenhum segredo.
