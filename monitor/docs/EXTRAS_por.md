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

## Ainda não está

O painel de higiene de workflows, o relatório de fila, a vista de versão pronta ou bloqueada e o painel da cadeia de fornecimento não fazem parte desta versão.
