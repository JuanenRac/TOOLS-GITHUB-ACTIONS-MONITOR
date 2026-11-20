<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_SECURITY.md) | [🇪🇸 Español](SENTINEL_SECURITY_spa.md) | [🇫🇷 Français](SENTINEL_SECURITY_fra.md) | [🇮🇹 Italiano](SENTINEL_SECURITY_ita.md) | [🇩🇪 Deutsch](SENTINEL_SECURITY_deu.md) | [🇨🇳 简体中文](SENTINEL_SECURITY_zho.md) | [🇯🇵 日本語](SENTINEL_SECURITY_jpn.md) | **🇵🇹 Português**

# O sentinela de segurança

O terceiro sentinela, ao lado do da CI e do Collab. Lê, sem escrever nada no GitHub, o que o próprio GitHub diz estar aberto ou em falta na segurança de cada repositório, e transforma-o em alertas do separador de Alertas (origem Segurança). Existe na edição Complete, desligado por predefinição (`sentinels.security.enabled`); o Lite não tem sentinelas.

## O que lê e o que assinala

| Sinal | Alerta | Nível | Ativo por predefinição |
|---|---|---|---|
| Alertas do Dependabot abertos de gravidade `min_severity` ou superior (high por predefinição) | `security.dependabot` | crítico se algum for crítico, erro se algum for alto, senão aviso | sim |
| Alertas da análise de código abertos de gravidade `min_severity` ou superior | `security.code_scanning` | igual | sim |
| Alertas da análise de segredos abertos | `security.secret` | sempre crítico (um segredo que o GitHub encontra é um segredo exposto) | sim |
| O ramo predefinido não tem proteção | `security.branch_unprotected` | aviso | sim |
| Os fluxos recebem permissão de escrita por predefinição | `security.workflow_write` | aviso | sim |
| Não há ficheiro CODEOWNERS | `security.codeowners_missing` | informação | não |
| Uma execução importante (push para o ramo predefinido, execução manual, execução `pull_request_target`) que o monitor tinha visto foi apagada | `security.runs_deleted` | error | não |

**Execuções apagadas** (`security.runs_deleted`, desativado por defeito): depois de uma fuga de segredos, apagar a execução que os imprimiu é a forma habitual de eliminar o rasto e o GitHub não deixa um registo visível. Com `sentinels.security.signals.runs_deleted.enabled` o sentinela guarda uma lista curta e privada das execuções importantes que viu e, quando uma já não está na lista de execuções, pede essa execução isolada: um 404 explícito é uma eliminação; uma recusa (403), um erro de rede ou um 5xx nunca contam. Uma execução mais antiga do que `sentinels.security.signals.runs_deleted.check_window_days` (14) não é consultada (a retenção da conta pode tê-la eliminado) e uma eliminação detetada mantém-se como aviso durante o mesmo número de dias. São pedidas no máximo `sentinels.security.signals.runs_deleted.max_checks` (50) execuções isoladas por repositório e ronda. O aviso nomeia o workflow, quem o iniciou e o ramo, nunca conteúdo da execução.

Há um alerta por repositório e sinal, com as contagens por gravidade nos detalhes. Cada sinal pode ser desligado (`sentinels.security.signals.<sinal>.enabled`) e, no Dependabot e na análise de código, ter outra gravidade mínima. De um repositório arquivado não se pede mais nada.

## O que não conseguiu verificar

Uma fonte a que o GitHub não responde para um repositório (a funcionalidade está desligada aí, ou o acesso não a pode ler: 403, 404) **não** é um alerta e **não** é um certificado de boa saúde. Fica listada no estado em `unavailable`, com quantos repositórios abrange, e a página di-lo. A única exceção é a proteção do ramo predefinido: o GitHub responde 404 para um ramo sem proteção, e isso é a constatação; um 403 aí é só ilegível.

Quando a maior parte do que pesa na penalização (Dependabot, análise de código, segredos) não pode ser lida, o nível é `unknown` e não `ok`, e a parte de segurança da pontuação fica de fora em vez de contar como 100; o estado mostra `sources_readable` e `sources_total`. Se uma fonte deixa de responder enquanto há um alerta aberto, o alerta mantém-se durante uma semana (marcado com `unread_since`) e nunca é anunciado como corrigido. Um repositório cujas leituras continuam a falhar espera 5 minutos, 30 minutos e depois 6 horas pela tentativa seguinte, para que uns poucos repositórios avariados nunca gastem a ronda inteira.

Uma fonte que o plano da conta não tem (proteção de ramos ou análise de código de um repositório privado no plano gratuito: o GitHub responde que a funcionalidade precisa de outro plano) distingue-se de uma recusa e de uma funcionalidade desativada: a página e `unavailable_why` do estado dizem `N/A (plano)`, `N/A (sem acesso)` ou `N/A (desativado)`. Com `sentinels.security.plan_na` ativada (predefinição), as fontes do primeiro tipo ficam fora da contagem do legível e da cobertura da nota e são contadas à parte como `sources_na_plan`; nenhum dos três casos é um achado nem prova de limpeza, e uma sentinela cujo plano não tem nada do que pesa fica `unknown` e não dá à nota nenhuma parte de segurança. Desativada, contam como fontes que não se puderam ler.

Agora cada sentinela diz o seu **ciclo de vida**: `healthy` (saudável), `degraded` (degradado: algumas leituras falham, uma fonte não pode ser lida ou ainda não terminou a primeira volta), `paused` (em pausa, à espera da quota do GitHub), `error` (falha e ainda não leu nada) ou `off` (desligado). «Sem alertas» só quer dizer alguma coisa quando o ciclo de vida é `healthy`.

## Custo

Uma ronda lê no máximo `sentinels.security.max_repos_per_tick` repositórios (5 por predefinição), primeiro os vistos há mais tempo e um pouco antes os que têm um alerta aberto, com um ciclo a cada `sentinels.security.refresh_seconds` (30 minutos por predefinição). Cada repositório custa no máximo sete leituras, quase todas condicionais: um repositório que não mudou não gasta quota; o ficheiro CODEOWNERS, quando pedido, procura-se no máximo uma vez por dia. O sentinela fica em pausa enquanto a quota restante estiver abaixo de `sentinels.security.min_rate_remaining`. O seu estado (`security_state.json`) guarda os alertas abertos, pelo que um reinício não volta a anunciar nada, e a primeira vez que se olha para um repositório não se escreve nenhum evento. Uma ronda também deixa de começar repositórios novos passados `sentinels.security.deadline_s` segundos (30 por predefinição; 0 = sem teto): os que não foram alcançados esperam pela ronda seguinte e o estado lista-os por nome como `unchecked` (com `round_cut`) em vez de os contar como zero alertas.

## Um só dono por constatação

Os painéis do separador Sentinela que já mostravam números de segurança (alertas por repositório, alertas antigos, cobertura do Dependabot e do CodeQL, pull requests do Dependabot) continuam a ser painéis. Os alertas do separador de Alertas sobre estes sinais vêm apenas deste sentinela, pelo que nada é levantado duas vezes. O conteúdo de cada ficheiro de fluxo (ações não fixadas a um commit, `write-all`, sem bloco de permissões, `pull_request_target` com checkout) pertence ao [sentinela da cadeia de abastecimento](SENTINEL_SUPPLY_por.md); `security.workflow_write` fica aqui porque é uma definição do repositório.

## Eventos e notificações

Uma constatação nova escreve o evento `security_new` e uma encerrada `security_fixed` no fluxo, a que estão ligados os canais de notificação; ambos são tipos que a pessoa pode pedir nas definições de notificações, e as preferências por utilizador têm uma caixa de Segurança. Nada se anuncia na primeira vez que se olha para um repositório.

## As definições

Na página de Definições, subseparador Sentinela, bloco Segurança: `sentinels.security.enabled`, `sentinels.security.refresh_seconds`, `sentinels.security.max_repos_per_tick`, `sentinels.security.min_rate_remaining`, `sentinels.security.repos`, `sentinels.security.plan_na`, `sentinels.security.signals.dependabot.enabled`, `sentinels.security.signals.dependabot.min_severity`, `sentinels.security.signals.code_scanning.enabled`, `sentinels.security.signals.code_scanning.min_severity`, `sentinels.security.signals.secret.enabled`, `sentinels.security.signals.branch.enabled`, `sentinels.security.signals.workflow.enabled` e `sentinels.security.signals.codeowners.enabled`, `sentinels.security.signals.runs_deleted.enabled`, `sentinels.security.signals.runs_deleted.check_window_days`, `sentinels.security.signals.runs_deleted.max_checks`. Os pontos que cada constatação tira à parte de segurança da pontuação (`sentinels.security.penalty`) são lidos do ficheiro; veja-se o ficheiro de exemplo.

## Proteção de ramo por ruleset

Um ramo predefinido conta como protegido se tiver a proteção clássica de ramo **ou** um ruleset ativo (o GitHub responde 404 ao endpoint clássico num repositório protegido só por ruleset, por isso o sentinela lê também a marca `protected` do ramo e as regras ativas do ramo). `signals.branch.require` pode listar tipos de regra (por exemplo `pull_request`, `required_status_checks`) que as regras devem ter; um ramo protegido a que falte alguma é avisado com as que faltam. Por defeito a lista está vazia: basta qualquer proteção. Um repositório que não se conseguiu ler porque a chamada excedeu o tempo é listado com a sua causa (`timeout`, `rate`, `network`, `error`) em `errors` e `error_kinds` do estado; nunca é um achado.
