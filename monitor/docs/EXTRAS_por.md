<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](EXTRAS.md) | [🇪🇸 Español](EXTRAS_spa.md) | [🇫🇷 Français](EXTRAS_fra.md) | [🇮🇹 Italiano](EXTRAS_ita.md) | [🇩🇪 Deutsch](EXTRAS_deu.md) | [🇨🇳 简体中文](EXTRAS_zho.md) | [🇯🇵 日本語](EXTRAS_jpn.md) | **🇵🇹 Português**

# Extras opcionais

Ambos estão **desligados por predefinição** e ligam-se nas Definições.

## O registo do passo falhado

`logs.failed_step.enabled`: um alerta de uma execução falhada recebe um botão **Passo falhado**. Um clique lê do GitHub as tarefas e o registo de falha dessa execução (duas chamadas da sua quota), mostra o passo que falhou e as suas últimas linhas relevantes (`logs.failed_step.lines`, `logs.failed_step.max_bytes`) e guarda a resposta em memória, por isso voltar a clicar não custa nada. O texto é limpo de tokens, chaves, endereços e pasta pessoal. Só se podem consultar repositórios que o monitor vigia, com `GET /api/run-log?repo=&run=`; no modo de equipa, só um administrador.

## Um token só de leitura da App do GitHub para as suas ferramentas

`github_app.share_reads`: o comando seguinte escreve, neste computador, um token de instalação da sua App do GitHub com a duração de uma hora, para que o `gh` das suas ferramentas e agentes leia com a quota da App e não com a sua (`GH_TOKEN`). O token vai só para a saída padrão, nunca para um ficheiro nem para um registo, e o comando precisa de `--read-only`; dê à App permissões só de leitura ao criá-la. Sem `github_app.share_reads` recusa.

```
python bin/monitor_cli.py gh-token --read-only
```

## Quatro relatórios opcionais

Os quatro estão **desligados por predefinição**. Aparecem num bloco "Relatórios opcionais" no fim do separador Alertas e em `GET /api/reports`. Os que leem o GitHub gastam no máximo `reports.max_calls_per_cycle` chamadas por ciclo, leem poucos repositórios de cada vez e guardam o que leem em memória durante um dia.

- `reports.workflow_hygiene.enabled`: lê os ficheiros de workflow dos repositórios e lista o que está mal escrito - actions não fixadas a um commit, permissões não limitadas, uma tarefa sem `timeout-minutes`, sem grupo `concurrency`, riscos de `pull_request_target` e injeção, segredos em claro (as regras do linter do painel A13, que lê clones locais, mais as duas novas).
- `reports.queue.enabled`: lê as tarefas de algumas execuções terminadas que esperaram e diz quanto esperou uma tarefa antes de começar para cada tipo de runner (Linux, Windows, macOS, maiores, auto-alojados).
- `reports.release_view.enabled`: nenhuma chamada; com o que a sentinela sabe diz que repositórios estão PRONTOS para uma versão (entradas no changelog ou uma compilação verde que ninguém publicou, nada vermelho, nenhuma assinatura à espera) e quais estão BLOQUEADOS, e porquê.
- `reports.supply_chain.enabled`: lê a última versão dos repositórios e diz, pelos nomes dos ficheiros, se traz uma lista de materiais de software (SBOM), somas de verificação e uma assinatura ou atestação. Os ficheiros nunca são descarregados.
