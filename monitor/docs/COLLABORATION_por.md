<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COLLABORATION.md) | [🇪🇸 Español](COLLABORATION_spa.md) | [🇫🇷 Français](COLLABORATION_fra.md) | [🇮🇹 Italiano](COLLABORATION_ita.md) | [🇩🇪 Deutsch](COLLABORATION_deu.md) | [🇨🇳 简体中文](COLLABORATION_zho.md) | [🇯🇵 日本語](COLLABORATION_jpn.md) | **🇵🇹 Português**

# Vistas de colaboração e ações opcionais

Vistas do que está à espera de alguém e algumas ações no GitHub que ficam desligadas até as permitir. Edições Complete e Full.

## Ativar

Ative `teamwork.enabled` (Definições > Colaboração). As vistas de execuções vêm do que o monitor já lê; pull requests, alertas e workflows leem-se de poucos repositórios por ciclo (`teamwork.repos_per_cycle`, `teamwork.refresh_hours`). A caixa fica no fim do separador Colaboração da área Sentinela.

## As vistas

À espera de uma pessoa (aprovação de ambiente, workflow de um fork, ação necessária), à parte da espera por um executor. A execução mais recente de cada via (workflow e ramo); um vermelho pode ser posto de parte `teamwork.dismiss_days` dias, só essa execução, e reposto. Pull requests abertos: prontos a integrar, atrasados, a precisar de ação ou desconhecido, atualizações de bots reconhecidas por autor, ramo ou etiqueta; `teamwork.hide_workflows` oculta workflows. Repositórios com alertas críticos ou altos com a idade do mais antigo, e os repositórios NÃO lidos, pelo nome. Com `teamwork.dismissed_alerts`, quem descartou alertas; um descarte fora de `teamwork.dismiss_allowed` gera um alerta.

## Escrever no GitHub

Nada é escrito a menos que `github_actions.enabled` esteja ativo, a ação esteja em `github_actions.allowed` e confirme o plano, que mostra exatamente o que é enviado. Ações novas: `update_branch`, `approve_fork`, `approve_deployment`, `force_cancel`, `enable_workflow`, `dispatch`. As vistas apenas PROPÕEM: atualizações de bots com verificações falhadas, ramos atrasados, execuções demasiado tempo em fila ou a correr (`teamwork.queued_hours`, `teamwork.stuck_hours`), as que correspondem a `teamwork.cancel_policy`, workflows desativados por inatividade (`teamwork.inactive_workflows`). O formulário de um workflow manual lê e verifica as entradas. Com `teamwork.forks_help`, dados sobre o autor de uma execução de fork; sem veredito. Uma implementação é aprovada um ambiente de cada vez, nomeado na confirmação; se uma execução esperar por vários, a página pergunta qual.

## A única ação automática

`teamwork.auto_rerun` (desligado) repete uma vez os trabalhos falhados de uma execução que não arrancou ou expirou, com as mesmas verificações. Nunca uma segunda vez; se voltar a falhar é gerado um alerta.

## Manter vivo um agendamento

O GitHub desliga os workflows agendados de um repositório público ao fim de 60 dias sem atividade. Com `teamwork.keep_alive_days` (0 = desligado; por exemplo 45), um repositório público sem nenhum push durante esse tempo e com workflows executados por agendamento aparece nas propostas como `enable_workflow`, com os dias que faltam. É uma proposta como as outras: nada é enviado até a confirmar. O GitHub não documenta que ativar um workflow já ativo reinicie a contagem, e isto não foi experimentado num repositório real: o caminho seguro é um novo commit.

## Hooks de executores próprios

Com `teamwork.runner_hooks`, um hook de um executor deste computador regista o início e o fim:

```
# ACTIONS_RUNNER_HOOK_JOB_STARTED
python /path/to/monitor/bin/monitor_cli.py runner-hook started
```

Para o fim use ACTIONS_RUNNER_HOOK_JOB_COMPLETED com `completed`. Um executor noutro computador não está coberto.

## API e linha de comandos

`GET /api/actions/state`, `GET /api/actions/dispatch-form`, `GET /api/actions/environments`, `GET /api/actions/fork-facts`, `POST /api/actions/plan`, `POST /api/actions/dismiss`.

```
python bin/monitor_cli.py actions status
python bin/monitor_cli.py actions proposals
python bin/monitor_cli.py runner-hook started
python bin/monitor_cli.py runner-hook completed
```

## Por verificar

Leituras e escritas só foram testadas com respostas inventadas; nenhuma das ações novas foi executada num repositório real.

## Todas as definições

`teamwork.enabled` `teamwork.repos_per_cycle` `teamwork.refresh_hours` `teamwork.dismiss_days` `teamwork.hide_workflows` `teamwork.bot_authors` `teamwork.bot_branches` `teamwork.bot_labels` `teamwork.dismissed_alerts` `teamwork.dismiss_allowed` `teamwork.auto_rerun` `teamwork.cancel_policy` `teamwork.queued_hours` `teamwork.stuck_hours` `teamwork.forks_help` `teamwork.inactive_workflows` `teamwork.keep_alive_days` `teamwork.runner_hooks`
