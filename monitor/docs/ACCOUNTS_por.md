<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ACCOUNTS.md) | [🇪🇸 Español](ACCOUNTS_spa.md) | [🇫🇷 Français](ACCOUNTS_fra.md) | [🇮🇹 Italiano](ACCOUNTS_ita.md) | [🇩🇪 Deutsch](ACCOUNTS_deu.md) | [🇨🇳 简体中文](ACCOUNTS_zho.md) | [🇯🇵 日本語](ACCOUNTS_jpn.md) | **🇵🇹 Português**

# Várias contas

A edição completa pode vigiar várias contas do GitHub (uma pessoa ou uma organização) ao mesmo tempo. Cada conta é um monitor próprio: um processo à parte, com a sua pasta, a sua porta em `127.0.0.1`, a sua configuração e a sua própria leitura da quota do GitHub. Uma falha, uma resposta lenta ou um limite de taxa de uma conta nunca toca nas outras. A edição lite tem uma conta e nada disto: nem sequer mostra as opções abaixo.

## Quando não há nada a fazer

Sem uma pasta `accounts/`, o monitor funciona exatamente como antes: uma conta, com os seus ficheiros junto do código. Só continua a ler se quiser mais do que uma.

## A pasta das contas

```
accounts/
  global.json              opcional: {"default_account": "personal", "enabled_accounts": "all"}
  personal/
    actions_monitor.json   a configuração desta conta (o seu github_owner, repos, sentinela...)
  org-acme/
    actions_monitor.json
```

O id de uma conta são letras minúsculas, dígitos, `_` e `-` (até 40 carateres), porque é o nome de uma pasta; tudo o resto é recusado. `enabled_accounts` é `"all"` ou uma lista; `default_account` é a que se abre quando não se pede nenhuma. `MONITOR_ACCOUNTS_DIR` muda a pasta de sítio. Cada conta guarda a sua cache, eventos, análise, estado da sentinela e registos dentro da sua pasta, pelo que duas contas nunca partilham um ficheiro.

## Passar de uma conta para várias

```
python actions_monitor.py --migrate-accounts          # mostra o que seria copiado, não escreve nada
python actions_monitor.py --migrate-accounts --apply  # copia-o para accounts/default/
python actions_monitor.py --accounts                  # lista as contas
```

Os originais nunca são movidos nem apagados: apaga-os você depois de verificar. Uma segunda execução recusa-se, para que dois estados nunca se misturem. Para acrescentar uma conta, crie `accounts/<id>/actions_monitor.json` com o seu `github_owner` (copie o modelo `actions_monitor.example.json`).

## Executar

`python actions_monitor.py` com uma pasta `accounts/` arranca o supervisor, um processo pequeno na porta de sempre (8765) que arranca um monitor por conta e dá à página e às ferramentas um único endereço. Não lê nada do GitHub e não escreve nada. Se uma conta morrer, arranca-a de novo com uma espera crescente (2, 5, 15, 30, 60 e depois 120 segundos) e o resumo diz que está em baixo entretanto. `python actions_monitor.py --account personal` executa só essa conta, como um monitor normal.

## A página

A página é a que conhece, com um seletor de contas no topo do painel lateral e uma entrada **Todas as contas** que mostra um cartão por conta (estado, repositórios, em curso, em falha) e abre qualquer uma. Cada janela guarda a sua própria conta e vista: lêem-se do endereço, nunca de uma definição única que outra janela pisaria.

| Endereço | O que mostra |
|---|---|
| `/?account=org-acme` | a página dessa conta |
| `/?account=all` | os cartões de todas as contas |
| `/?view=now` `alerts` `charts` `repos` `settings` `live` | um painel |
| `/?chrome=0` | sem botões de cabeçalho, separadores nem filtros: um ecrã para uma parede ou um segundo monitor |

Para vários ecrãs, abra uma janela por vista, por exemplo `?view=now&chrome=0`, `?view=alerts&chrome=0` e `?view=live&chrome=0`. Um só monitor serve-as todas, pelo que não gasta a quota duas vezes. A vista **Ao vivo** mostra os últimos eventos que o GitHub enviou, o estado do recetor de webhook (ligado ou desligado, quantas entregas foram aceites, ignoradas, repetidas ou recusadas, nunca o segredo) e um seletor do modo de trabalho.

## A API

`GET /api/accounts` é o resumo, `GET /api/accounts/<id>/status` uma conta, e qualquer outro pedido sob `/api/` vai para a conta indicada com `?account=<id>` ou o cabeçalho `X-Account-Id` (a conta predefinida se nenhuma for dada). Uma conta desconhecida dá 404. As regras de acesso são as de um monitor isolado: a mesma verificação de anfitrião e origem, e o mesmo token de acesso no modo rede. O token de uso único de uma alteração deve ser pedido à mesma conta a que a alteração é enviada.

## Um webhook para todas

`POST /api/webhook` é um único endereço para toda a instalação. O supervisor lê apenas o proprietário do repositório na carga (`repository.full_name`) e passa o evento, intacto, à conta cujo `github_owner` é esse proprietário; a conta verifica a assinatura com o seu próprio segredo. Um proprietário que ninguém vigia recebe resposta e é ignorado. Para escolher você a conta, acrescente `?account=<id>`.

## Limites e honestidade

- Várias contas são vários processos: cada um lê o GitHub por si, pelo que a quota é partilhada pelo login que usa. Veja-a nos cartões e baixe `refresh_seconds` ou `max_workers` por conta, se for preciso.
- As verificações que precisam de um navegador real, contas reais do GitHub e um túnel de webhook real ficam consigo; os testes usam substitutos do monitor de uma conta e nunca chamam o GitHub.
- Uma versão posterior trará as contas para um só processo; a disposição das pastas e a API acima mantêm-se.
