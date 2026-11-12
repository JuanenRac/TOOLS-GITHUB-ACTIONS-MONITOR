<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI.md) | [🇪🇸 Español](CLI_spa.md) | [🇫🇷 Français](CLI_fra.md) | [🇮🇹 Italiano](CLI_ita.md) | [🇩🇪 Deutsch](CLI_deu.md) | [🇨🇳 简体中文](CLI_zho.md) | [🇯🇵 日本語](CLI_jpn.md) | **🇵🇹 Português**

# A linha de comandos como cliente do monitor

`python monitor_cli.py COMANDO` pergunta ao monitor em execução o que ele sabe (um `GET` em `127.0.0.1`, ou no endereço de `--url` / `MONITOR_URL`) e imprime-o. Não repete o trabalho da página junto do GitHub, nunca escreve no GitHub e não altera nenhuma definição. As ferramentas anteriores (`read_report.py`, `--doctor`, `gha_dispatch_all.py`) continuam a funcionar como antes.

## Comandos

| Comando | O que mostra | Lite |
|---|---|---|
| `status` | versão, edição, conta, repositórios, o que corre e o que falha, a quota | sim |
| `health` (ou `check`) | uma verificação rápida antes de ler algo pesado: o monitor está acessível, aceita este cliente, o acesso GitHub da conta responde? | sim |
| `doctor` | as verificações de `--doctor` para esta instalação (o monitor não tem de estar em execução) | sim |
| `accounts` | as contas do supervisor (só com várias contas) | não |
| `alerts` | os alertas de todas as sentinelas numa lista: `--sentinel ci\|collab`, `--level info\|warning\|error`, `--muted show\|hide\|only` | não |
| `live` | o estado do recetor do webhook e os últimos eventos | não |

Opções de todos os comandos: `--json` (a resposta como um documento JSON: `{"ok", "exit", "data"}`), `--account ID`, `--url URL`, `--lite` (porta 8766), `--timeout SEGUNDOS` (de 1 a 60), `--lang CÓDIGO`. No modo de rede ponha o token de acesso na variável de ambiente `MONITOR_ACCESS_TOKEN`, a que o próprio monitor lê (`MONITOR_TOKEN` é aceite como alias; `--token TOKEN` é o último recurso, porque uma opção aparece na lista de processos). A ordem: `MONITOR_ACCESS_TOKEN`, depois `MONITOR_TOKEN`, depois `--token`. Viaja no cabeçalho `X-Monitor-Access`, nunca no endereço nem no ecrã. Um `--url` com `http` sem cifra para outro computador imprime um aviso no stderr (o token e as respostas viajariam em claro): use `https` fora de uma rede que controle.

As horas escritas para as pessoas (a linha `Last read`, os silêncios, o registo, os relatórios, as notificações) usam o fuso deste computador e nomeiam-no, com a hora UTC ao lado (`11:43:07 CET (10:43:07 UTC)`). Escolha outro fuso com `display.timezone` (`local`, `utc` ou um nome como `Europe/Madrid`; a variável de ambiente `MONITOR_TIMEZONE` prevalece sobre o ficheiro). `--json` mantém UTC e acrescenta `updated_local`.

## Códigos de saída (estáveis)

| Código | Significado |
|---|---|
| 0 | tudo bem |
| 1 | uso incorreto do comando (também `--lite` com um comando que precisa da edição completa) |
| 2 | o monitor não está acessível |
| 3 | o monitor recusa este cliente, ou o acesso GitHub da conta falhou ou caducou (um problema de credencial, não uma quota esgotada) |
| 4 | o monitor responde mas está degradado: sem ligação, quota esgotada, ainda sem dados, um endpoint que não tem, ou uma resposta que não é JSON |
| 5 | `alerts --fail-on NÍVEL` encontrou um alerta aberto desse nível ou pior (um silenciado não conta) |

## Exemplos

```
python monitor_cli.py health && python monitor_cli.py alerts --fail-on error
python monitor_cli.py alerts --sentinel collab --level warning --json
python monitor_cli.py status --account org-acme
MONITOR_URL=http://192.168.0.20:8765 MONITOR_ACCESS_TOKEN=... python monitor_cli.py health --json
```

O `health` distingue três coisas: o monitor não responde (2), o acesso ao GitHub falha (3), e a quota esgotou-se ou não se chega ao GitHub (4); um monitor que ainda não terminou a primeira leitura di-lo (4) em vez de mostrar números vazios.

## A edição lite

`python monitor_cli.py status --lite`, `doctor --lite` e `health --lite` falam com a porta 8766. Os comandos que precisam de contas, sentinelas ou do recetor do webhook são recusados com o código de saída 1. A edição lite não tem contas nem API de alertas.
