<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI.md) | [🇪🇸 Español](CLI_spa.md) | [🇫🇷 Français](CLI_fra.md) | [🇮🇹 Italiano](CLI_ita.md) | [🇩🇪 Deutsch](CLI_deu.md) | [🇨🇳 简体中文](CLI_zho.md) | [🇯🇵 日本語](CLI_jpn.md) | **🇵🇹 Português**

# A linha de comandos como cliente do monitor

`python bin/monitor_cli.py COMANDO` pergunta ao monitor em execução o que ele sabe (um `GET` em `127.0.0.1`, ou no endereço de `--url` / `MONITOR_URL`) e imprime-o. Não repete o trabalho da página junto do GitHub, nunca escreve no GitHub e não altera nenhuma definição. As ferramentas anteriores (`bin/read_report.py`, `--doctor`, `bin/gha_dispatch_all.py`) continuam a funcionar como antes.

## Comandos

| Comando | O que mostra | Lite |
|---|---|---|
| `status` | versão, edição, conta, repositórios, o que corre e o que falha, a quota | sim |
| `health` (ou `check`) | uma verificação rápida antes de ler algo pesado: o monitor está acessível, aceita este cliente, o acesso GitHub da conta responde? | sim |
| `doctor` | as verificações de `--doctor` para esta instalação (o monitor não tem de estar em execução) | sim |
| `backup` | a cópia de segurança completa da instalação (o monitor não tem de estar em execução): `backup create [FICHEIRO] [--account ID]`, `verify FICHEIRO [--deep]`, `restore FICHEIRO [--account ID] [--to-dir PASTA] [--force]`, `status`, `list`; `--encrypt` com `--key-env NOME` cifra-a (biblioteca opcional); veja [OPS_por.md](OPS_por.md) | não |
| `accounts` | as contas do supervisor (só com várias contas) | não |
| `alerts` | os alertas de todas as sentinelas numa lista: `--sentinel ci\|collab\|security\|supply\|delivery`, `--level info\|warning\|error`, `--muted show\|hide\|only`; `--since 90m|24h|7d|2w` lista os que estiveram abertos em algum momento desse tempo, também os fechados (do histórico que o monitor guarda enquanto funciona; um alerta conta como fechado após dez minutos de ausência) | não |
| `proposals` | as ações que a IA propôs (`ai.actions.enabled`): `proposals list`, `show ID`, `approve ID`, `reject ID`, `execute ID` (um id pode ser abreviado). `approve` e `reject` só registam a decisão; `execute` executa-a pela mesma porta da página e precisa de `ai.actions.execute`, e com `ai.actions.require_approval` de uma aprovação antes. Aprovar, rejeitar e executar só se faz neste computador Com um utilizador, `approve` precisa de `--code` e dos oito primeiros caracteres da impressão digital; com vários, aprove na página com a sua sessão (duas pessoas). | não |
| `score` | a pontuação da conta: número, letra, tendência, partes, cobertura e a decomposição por repositório; `--compare` compara-a com o histórico da janela | não |
| `compare` | este período face ao anterior: os números com a sua variação e sentido, quem piora ou melhora; `--window 7\|30d`, `--days all\|workdays\|weekend`, `--baseline previous\|year_ago`, `--format table\|json\|ndjson\|csv`; saída 4 se um número tem poucos dados, 5 com `--fail-on` se algum piora; `--format csv` com outro comando é um mau uso (saída 1) | não |
| `api` | a API de leitura para clientes: `api openapi` imprime o documento OpenAPI de cada rota congelada (redirecione-o para um ficheiro), `api me` diz quem o monitor julga que este cliente é (modo, utilizador, papel, o que a sessão pode fazer, versão do contrato); um monitor com `api.v1_enabled` fechado di-lo; `api contract-check` lança contra ele a suite de contrato para clientes (saída 4 se uma verificação falhar) | não |
| `team` | a saúde dos repositórios por ordem, primeiro os que precisam de uma pessoa; `--severity warn\|bad` fica com os piores e `--repo owner/name` dá o detalhe de um | não |
| `live` | o estado do recetor do webhook e os últimos eventos | não |
| `ai` | `ai models [--refresh]` lista os modelos do fornecedor de IA com os dados de cada um; `ai test --provider NOME --model NOME` experimenta um com um texto sintético (latência, tokens, custo estimado); `ai doctor` diz porque é que uma IA não responde, sem imprimir uma chave | não |
| `lessons` | o que as falhas desta CI ensinaram: `lessons list`, `lessons brief --repo NOME` (ler antes de um push), `lessons failures`, `lessons close` | não |
| `briefs` | os briefs dos separadores que as ferramentas de IA leem: `briefs index`, `briefs show SEPARADOR`, `briefs all` | sim |
| `docs` | os guias desta versão, lidos da instalação (sem monitor): `docs list` nomeia-os com o título, `docs show NOME` imprime um no idioma de `--lang` | não |
| `screens` | o menu Ecrãs da página: `screens list` (cada tipo de ecrã e se pode ser aberto) e `screens urls` (os endereços completos, prontos para um comando de quiosque) | não |
| `keyring` | as chaves públicas que podem assinar: `keyring list`, `add` (`--key-id`, `--public-key`, `--key-scope`, `--expires`), `revoke --key-id`, `verify --document FILE`; sem monitor, as chaves privadas são recusadas | não |
| `verify-release` | uma pasta de ficheiros de versão transferidos, verificada sem rede com SHA256SUMS e a assinatura: `verify-release --folder DIR`; saída 4 quando não são de confiança Também `--installed` (esta instalação contra a lista de materiais), `--attestations`, `--fetch` (precisa de `ops.verify_release.fetch`); `doctor --verify-release DIR` verifica a instalação; `keyring check-rotation --document FILE` verifica o anúncio de uma chave nova. | não |
| `toolbox` | as pequenas ferramentas do operador que funcionam neste computador, sem monitor em execução: `toolbox limits [N]` (a configuração face aos seus tetos), `toolbox workspaces` (os espaços de trabalho e o que está em uso), `toolbox ledger [--force]` (o registo de notificações já enviadas; `--force` esquece-o), `toolbox summary` (os eventos por tipo, repositório e dia) e `toolbox export-events FILE` (os eventos como jsonl, csv, parquet ou duckdb conforme o fim do nome; parquet e duckdb precisam do seu pacote, o ficheiro tem de ser novo) | não |
| `credential` | outro acesso ao GitHub para uma conta enquanto tudo corre: `credential replace\|reload [--account ID] [--new-token-file FICHEIRO\|-]`; nunca imprime um token | não |
| `install-skill` | copia uma skill do monitor (`internal` ou `external`) para a pasta onde uma ferramenta de IA lê as suas skills: `install-skill external --dest PASTA`; o monitor não tem de estar em execução | não |
| `gh-token` | imprime um token de instalação de uma hora da GitHub App para que as leituras de uma ferramenta gastem a quota da App (só com `github_app.share_reads` ligado); execute-o sem `--json` | não |
| `watch` | a mesma leitura vezes sem conta (`watch status\|alerts`, `--interval`, `--once`, `--exit-on-change`); veja [CLI_OPERATOR_por.md](CLI_OPERATOR_por.md) | não |
| `completions` | o script de completação para `bash`, `zsh`, `fish` ou `powershell`, escrito a partir do analisador real (só imprime) | não |
| `kiosk` | o endereço do monitor para uma TV ou uma parede (`ops`, `team`, `release`, `quiet`); veja [KIOSK_por.md](KIOSK_por.md) | não |
| `metrics` | os números como linhas `nome=valor` para o cron e o correio; com `--if-problem` não escreve nada quando tudo está bem; veja [CLI_OPERATOR.md](CLI_OPERATOR.md) | não |
| `posture` | Postura dos repositórios e da organização, só de leitura (`posture status|matrix|check --repo-name`); ver [POSTURE.md](POSTURE_por.md) | não |
| `traffic` | Histórico de transferências e tráfego guardado neste computador (`traffic status|export`); ver [TRAFFIC_por.md](TRAFFIC_por.md) | não |
| `external-ci` | Fontes de CI externas, só de leitura (`external-ci list|status|probe --source`); ver [EXTERNAL_CI.md](EXTERNAL_CI_por.md) | não |
| `plugin` | Plugins: `plugin list|validate|pack|verify|init|install|enable|disable|uninstall|audit`; ver [PLUGINS.md](PLUGINS_por.md) | não |

Opções de todos os comandos: `--json` (a resposta como um documento JSON: `{"ok", "exit", "data"}`), `--account ID`, `--url URL`, `--lite` (porta 8766), `--timeout SEGUNDOS` (de 1 a 60), `--lang CÓDIGO`. No modo de rede ponha o token de acesso na variável de ambiente `MONITOR_ACCESS_TOKEN`, a que o próprio monitor lê (`MONITOR_TOKEN` é aceite como alias; `--token TOKEN` é o último recurso, porque uma opção aparece na lista de processos). A ordem: `MONITOR_ACCESS_TOKEN`, depois `MONITOR_TOKEN`, depois `--token`. Viaja no cabeçalho `X-Monitor-Access`, nunca no endereço nem no ecrã. Um `--url` com `http` sem cifra para outro computador imprime um aviso no stderr (o token e as respostas viajariam em claro): use `https` fora de uma rede que controle.

Todos os comandos aceitam também `--format text|table|plain|json|ndjson` (`--json` é `--format json`); veja [CLI_OPERATOR_por.md](CLI_OPERATOR_por.md).

A linha de comandos é um cliente da API de leitura para clientes: as rotas que o contrato congela (`docs/schemas/api_contract.json`) são pedidas primeiro em `/api/v1/` e, se o monitor responde 404 aí (a API está fechada, `api.v1_enabled`), pede-se a rota antiga e não se volta a tentar o prefixo. O documento é o mesmo pelos dois caminhos, por isso a saída de nenhum comando muda. `cli.prefer_v1` (ativado por predefinição) desativa-o, e a variável `MONITOR_CLI_PREFER_V1` (`0` ou `1`) prevalece. As rotas que o contrato não congela pedem-se sempre pelo caminho antigo.

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
| 6 | `watch --exit-on-change` viu uma alteração (só quando essa opção é dada); veja [CLI_OPERATOR_por.md](CLI_OPERATOR_por.md) |

Todo erro traz um `help`: uma frase com o passo seguinte, que muitas vezes nomeia o guia a ler (`docs show FIRST_STEPS`). No formato de texto é a última linha, que começa por `ajuda:`; com `--json` é o campo `help` junto a `error`: `{"ok": false, "exit": 2, "error": "...", "help": "..."}`.

## Exemplos

```
python bin/monitor_cli.py health && python bin/monitor_cli.py alerts --fail-on error
python bin/monitor_cli.py alerts --sentinel collab --level warning --json
python bin/monitor_cli.py status --account org-acme
MONITOR_URL=http://192.168.0.20:8765 MONITOR_ACCESS_TOKEN=... python bin/monitor_cli.py health --json
```

O `health` distingue três coisas: o monitor não responde (2), o acesso ao GitHub falha (3), e a quota esgotou-se ou não se chega ao GitHub (4); um monitor que ainda não terminou a primeira leitura di-lo (4) em vez de mostrar números vazios.

## A edição lite

`python bin/monitor_cli.py status --lite`, `doctor --lite` e `health --lite` falam com a porta 8766. Os comandos que precisam de contas, sentinelas ou do recetor do webhook são recusados com o código de saída 1. A edição lite não tem contas nem API de alertas.

## `ai-hook`: dizer a uma ferramenta de IA o que o monitor vê

`python bin/monitor_cli.py ai-hook install|status|uninstall [--assistant|--cursor|--generic] [--scope project|user] [--project-dir DIR] [--dry-run] [--json]` não precisa de um monitor em execução. Acrescenta, mostra ou remove o script de ligação `bin/ai_hook.py` nas definições de ganchos de uma ferramenta de IA (ver o guia dos alertas para IA): o ficheiro de definições é fundido, guarda-se uma cópia e a resposta de `--json` é ASCII puro. `status` é a ação predefinida.

## O token de acesso na linha de comandos

No modo de rede o token é lido de `MONITOR_ACCESS_TOKEN`, depois de `MONITOR_TOKEN`, depois da primeira linha de `--token-file FICHEIRO` (mantenha esse ficheiro legível só por si: num sistema com modos de ficheiro o comando avisa se outros o puderem ler) e por fim de `--token`, que aparece na lista de processos e por isso imprime um aviso no stderr.

## As ferramentas de armazenamento

`python tools/migrate_storage.py` move o estado entre ficheiros e SQLite, e `python tools/backup_storage.py` faz, verifica e restaura cópias de qualquer um deles (ambas estão descritas em [STORAGE_por.md](STORAGE_por.md)). O `--doctor` tem duas verificações para elas: o armazenamento e a retenção.

## O despachante por lotes: as entradas de um workflow

`python bin/gha_dispatch_all.py plan --inputs` lista também, sob cada alvo, as entradas que o seu workflow pede quando é disparado à mão (nome, tipo, obrigatória ou opcional, valor por defeito, opções de uma escolha e descrição). São lidas do ficheiro do workflow em `origin/main` do clone com `git show`: nada é disparado, nada é enviado e o `gh` não é chamado. `--json` acrescenta uma lista `inputs` a cada linha; é `null` quando o ficheiro não está em `origin/main` ou usa uma forma que o leitor não conhece (o estilo de fluxo `inputs: {…}`), e `[]` quando o workflow não pede nenhuma entrada.

## Cópia de segurança e o doctor

`backup` e `doctor` trabalham sobre as pastas da instalação, por isso não precisam de um monitor em execução. `doctor` sai com `0` quando tudo está bem (também com avisos), `1` quando uma verificação falhou, `3` quando só há avisos e `--strict` (ou `ops.doctor.strict_exit`) está ativo, e `4` quando o próprio doctor não conseguiu executar-se; são os códigos do doctor, os outros comandos mantêm os códigos de saída acima. `backup` sai com `0` quando termina e `1` quando é recusado ou o pacote não passa a verificação. O guia [OPS_por.md](OPS_por.md) tem as verificações, o restauro e a cópia agendada. O doctor tem ainda `compare_window` (a comparação de dois períodos consegue olhar para trás duas janelas com o histórico que pede e guarda) e `etag` (a parte das leituras condicionais respondidas com 304 no monitor que corre aqui, e se as respostas do GitHub chegam sem ETag).

## Identidade de um repositório, vários proprietários

Linha de comandos: `identity status`, `identity plan`, `identity apply`.

```
python bin/monitor_cli.py identity plan
```

## Conformidade e registo de ações

`compliance report` diz que garantias oferece esta instalação; `audit verify|checkpoint|purge|export` trabalha sobre a cadeia do registo de ações. Ver [COMPLIANCE_por.md](COMPLIANCE_por.md).

## Comandos: actions, runner-hook

```
python bin/monitor_cli.py actions proposals
python bin/monitor_cli.py runner-hook started
```

[COLLABORATION_por.md](COLLABORATION_por.md)
