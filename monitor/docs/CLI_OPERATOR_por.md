<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI_OPERATOR.md) | [🇪🇸 Español](CLI_OPERATOR_spa.md) | [🇫🇷 Français](CLI_OPERATOR_fra.md) | [🇮🇹 Italiano](CLI_OPERATOR_ita.md) | [🇩🇪 Deutsch](CLI_OPERATOR_deu.md) | [🇨🇳 简体中文](CLI_OPERATOR_zho.md) | [🇯🇵 日本語](CLI_OPERATOR_jpn.md) | **🇵🇹 Português**

# A linha de comandos para o operador

O básico do `monitor_cli.py` está em [CLI_por.md](CLI_por.md). Esta página é para quem vive num terminal: como as respostas são escritas (`--format`), como vigiar (`watch`), como completar os comandos (`completions`), os códigos de saída e o endereço para uma TV (`kiosk`). Tudo o que aqui está lê a API do monitor deste computador (ou a de `--url`); nada escreve no GitHub e nada gasta a quota.

## Formatos: `--format`

| Formato | O que obtém |
|---|---|
| `text` | o que cada comando sempre escreveu. É o predefinido. |
| `table` | os registos em colunas que cabem na largura do terminal (os carateres japoneses e chineses contam como duas células). Não há cor, pelo que `NO_COLOR` é respeitado. |
| `plain` | um registo por linha, os campos separados por uma tabulação, sem cabeçalho: para `grep`, `cut` e `awk`. Uma tabulação ou uma quebra de linha dentro de um texto passa a um espaço. |
| `json` | o documento `{"ok", "exit", "data"}`. `--json` é o mesmo. |
| `ndjson` | um objeto JSON por linha, um por registo (um alerta, uma conta, um repositório, um evento). Um comando que responde uma só coisa (`status`, `health`) dá uma linha. |

`--format` prevalece sobre `--json`, e ambos prevalecem sobre a definição `cli.default_format` (por predefinição `text`). Os três formatos estruturados saem do mesmo documento que `--json`, pelo que nunca discordam. Uma lista vazia não imprime nada em `ndjson` nem em `plain`.

## `watch`: a mesma leitura vezes sem conta

```
python bin/monitor_cli.py watch status
python bin/monitor_cli.py watch alerts --interval 10 --format table
python bin/monitor_cli.py watch alerts --exit-on-change --format ndjson
```

`watch status|alerts` repete a leitura do comando. Lê a API do monitor, não o GitHub, pelo que um intervalo curto não gasta a quota. As opções:

- `--interval SEGUNDOS`: a pausa entre duas leituras. O mínimo é a definição `cli.watch.min_interval_seconds` (2 por predefinição): um intervalo menor é elevado até ela. Sem `--interval` a pausa é `cli.watch.default_interval_seconds` (5).
- `--once`: uma leitura e sair (o código de saída é o do comando).
- `--exit-on-change`: o ciclo termina com o código de saída **6** quando o que vigia já não é o que era na primeira leitura (o conjunto de alertas ou os números do estado). Um relógio que avança não é uma alteração. Sem a opção o código 6 nunca aparece.
- `--no-clear`: não limpar o ecrã entre duas leituras (o ecrã só é limpo num terminal e só em `text` e `table`).
- Um monitor que não se consegue ler é tentado de novo com uma pausa cada vez maior (o intervalo duplicado, no máximo um minuto) e o erro vai para o erro padrão. **Ctrl-C** termina o ciclo com o código 0.

## `watch branch`: o commit que acabou de enviar

```
git push && python bin/monitor_cli.py watch branch
python bin/monitor_cli.py watch branch --repo acme/widgets --branch main --wait 300
python bin/monitor_cli.py watch branch --single-pass --format json
```

`watch branch` pergunta ao git em que repositório (`origin`), ramo e commit está a pasta onde se encontra, e segue no monitor os workflows desse commit: espera que apareçam, mostra-os enquanto correm e termina sozinho. O código de saída é **0** quando todos os workflows passaram e **1** quando um falhou, foi cancelado ou não terminou a tempo (uma falha não se distingue de um tempo esgotado, para que `git push && monitor_cli.py watch branch` sirva num script). Lê as execuções que o monitor já tem, nunca o GitHub, por isso não gasta quota; o repositório tem de ser um dos que o monitor vigia. O endereço do remoto só é lido para tirar proprietário e nome e nunca é escrito (pode levar um token).

- `--repo PROPRIETÁRIO/NOME` e `--branch NOME` substituem o que diz o git. Com qualquer um deles (ou sem commit) segue-se a execução mais recente de cada workflow do ramo em vez das de um commit.
- `--single-pass` (ou `--once`): uma leitura e sair, com o código desse momento (1 enquanto as execuções não terminaram).
- `--wait SEGUNDOS`: quanto esperar pelo fim das execuções antes de desistir com 1 (10 a 86400). Sem ele, a espera é a definição `cli.watch.branch_timeout_seconds` (900).
- Um commit solto não tem ramo: indique `--branch`. Uma pasta sem um remoto chamado `origin` no GitHub precisa de `--repo`.

## `completions`: completar os comandos

```
python bin/monitor_cli.py completions bash > ~/.local/share/bash-completion/completions/monitor_cli.py
python bin/monitor_cli.py completions zsh  > "${fpath[1]}/_monitor_cli"
python bin/monitor_cli.py completions fish > ~/.config/fish/completions/monitor_cli.py.fish
python bin/monitor_cli.py completions powershell | Out-String | Invoke-Expression
```

O script é escrito a partir do analisador real da linha de comandos, pelo que oferece exatamente os comandos, palavras e opções que existem: uma opção nova não pode ficar esquecida e um teste compara ambos. O comando limita-se a **imprimir**; não edita nenhum ficheiro seu e não precisa de monitor. Ponha a saída onde a sua shell lê as completações, como acima.

## Códigos de saída

| Código | Significado |
|---|---|
| 0 | tudo bem (também Ctrl-C em `watch`) |
| 1 | uso incorreto do comando |
| 2 | o monitor não pode ser alcançado |
| 3 | o monitor ou o GitHub recusa a credencial |
| 4 | o monitor responde mas está degradado (sem ligação, quota esgotada, ainda sem dados) ou a resposta não se consegue ler |
| 5 | `alerts --fail-on NÍVEL` encontrou alertas desse nível ou pior |
| 6 | `watch --exit-on-change` viu uma alteração (só quando essa opção é dada) |

Os códigos 0 a 5 são os de [CLI_por.md](CLI_por.md); um teste mantém esta tabela e o código de acordo.

### Os códigos de saída de `status` para um operador

Por predefinição o `status` mantém os códigos da tabela acima, por isso nenhum script muda. Com `--status-codes operator` (ou a definição `cli.status_codes` em `operator`) o comando diz apenas três coisas: **0** saudável, **1** nada serve (o monitor não é alcançável ou recusa a credencial) e **2** a funcionar mas precisa de atenção. Precisa de atenção significa: o monitor não chega ao GitHub, ainda não há dados, a credencial está cega, a atualização está em pausa porque a quota está abaixo do mínimo, a resposta traz um erro, uma resposta que não é a de um monitor, ou **o código no disco é de outra versão que o processo em execução** (foi aplicada uma atualização e o monitor não foi reiniciado; o `/api/health` di-lo como `code_stale` e o `--doctor` tem a verificação `running`). Um erro de utilização continua a ser 1. Os motivos estão no campo `attention` de `--json`. As falhas de workflows vermelhos não contam: para essas use `alerts --fail-on`.

## Exemplos com `jq`

Estes exemplos usam apenas campos que fazem parte da forma estável das respostas, e um teste executa-os contra um monitor de mentira (quando o `jq` está instalado).

```
monitor_cli.py alerts --json | jq -r '.data.alerts[] | select(.level=="critical") | .repo'
monitor_cli.py alerts --format ndjson | jq -r '.code'
monitor_cli.py status --json | jq '.data.red_workflows'
monitor_cli.py team --json | jq -r '.data.ranking[] | .repo'
```

## `kiosk`: o endereço para uma TV ou uma parede

`monitor_cli.py kiosk [ops|team|release|quiet]` imprime o endereço do monitor para um ecrã em que ninguém toca. Veja [KIOSK_por.md](KIOSK_por.md).

## Definições

| Definição | Predefinição | Significado |
|---|---|---|
| `cli.default_format` | `text` | o formato quando não se dá `--format` nem `--json`: `text`, `table`, `plain`, `json` ou `ndjson` |
| `cli.watch.min_interval_seconds` | 2 | a pausa mais curta do `watch` (de 1 a 3600) |
| `cli.watch.default_interval_seconds` | 5 | a pausa do `watch` quando não se dá `--interval` (de 1 a 3600) |
| `cli.status_codes` | `classic` | os códigos de saída de `status`: `classic` (os da tabela) ou `operator` (0 saudável, 1 nada serve, 2 a funcionar mas precisa de atenção) |
| `cli.watch.branch_timeout_seconds` | 900 | quanto espera o `watch branch` pelo fim das execuções do commit (10 a 86400) |

## O que esta versão não faz

- O `completions` não tem `--install`: nunca escreve nos ficheiros de um utilizador.
- Não existe o comando `proposals`: o monitor ainda não tem rota de propostas sobre a qual atuar.

## Saída redirecionada, cor e largura

- Sem terminal (um redirecionamento, `tee`, um pipe, cron) o comando não escreve nenhuma sequência de escape, toma a largura de `COLUMNS` quando é um número e usa 80 caso contrário, e o texto vindo do GitHub (um título, um nome) é limpo das sequências de escape que possa trazer.
- `--color auto|always|never` (predefinido `auto`): `auto` escreve cor só num terminal e nunca quando `NO_COLOR` está definida (e não vazia) ou `TERM=dumb`; `always` escreve-a seja qual for o destino; `never` não escreve nenhuma. Só o cabeçalho de `--format table` é colorido (a negrito); `json` e `ndjson` nunca são tocados.
- Um leitor que fecha mais cedo (`monitor_cli.py alerts --format plain | head -1`) termina o comando em silêncio: sem traceback nem texto de erro.

## `metrics`: os números para o cron e para o correio

`monitor_cli.py metrics` escreve os números do monitor como uma linha `nome=valor` cada um, por ordem fixa e sem mais nada na saída padrão: `repos`, `active`, `queued`, `failures_24h`, `successes_24h`, `red_workflows`, `alerts`, `alerts_info`, `alerts_warning`, `alerts_error`, `alerts_critical`, `allowance_remaining`, `allowance_limit` e `offline`. Um número desconhecido é omitido, nunca escrito como 0. Lê o monitor, nunca o GitHub.

Com `--if-problem` não escreve nada e sai com 0 quando não há nenhum workflow vermelho nem alertas de `--fail-on` (error por predefinição) ou piores; caso contrário escreve os números e sai com 5. O cron envia por correio qualquer saída, por isso esta linha só envia correio no dia em que algo corre mal: `*/15 * * * * py -3 /opt/monitor/bin/monitor_cli.py metrics --if-problem`. Um monitor inalcançável nunca é silêncio: o erro vai para a saída de erros e o código é 2.
