<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CI_RED_BRIDGE.md) | [🇪🇸 Español](CI_RED_BRIDGE_spa.md) | [🇫🇷 Français](CI_RED_BRIDGE_fra.md) | [🇮🇹 Italiano](CI_RED_BRIDGE_ita.md) | [🇩🇪 Deutsch](CI_RED_BRIDGE_deu.md) | [🇨🇳 简体中文](CI_RED_BRIDGE_zho.md) | [🇯🇵 日本語](CI_RED_BRIDGE_jpn.md) | **🇵🇹 Português**

# Do monitor ao painel: `ci_red.json`

O que o monitor escreve, como exportá-lo e o que precisa quem lê o ficheiro. O monitor apenas lê o GitHub e escreve ficheiros locais: nunca faz push, nunca faz commit e nunca fecha nada por iniciativa própria.

## O que o monitor escreve

`ci_red.json` ao lado de `actions_monitor.py`, atualizado após cada passagem da sentinela (esquema 2):

| Campo | Significado |
|---|---|
| `schema` | `2`. Os campos só são acrescentados, nunca renomeados. |
| `generated` | Hora UTC da passagem. |
| `tool_version` | Versão da ferramenta que escreveu o ficheiro. |
| `complete` | `true` quando todos os repositórios vigiados foram lidos nessa passagem. `false` durante o carregamento, quando a quota da API ficou curta ou quando faltam clones: não aja sobre a lista de repositórios a vermelho nem sobre a fila de assinatura até ser `true`. |
| `red_repos` / `pending_sign_repos` | Contagens. |
| `repos.<NAME>.ecosystem` | `armor`, `urtc`, `hydra`, `eh3d` ou `other`. |
| `repos.<NAME>.red[]` | Uma entrada por workflow cuja última execução concluída no ramo predefinido falhou: `workflow`, `conclusion`, `since`, `streak`, `url`. |
| `repos.<NAME>.pending_sign[]` e `pending_sign_hours` | Versões compiladas e ainda por assinar, e a idade da mais antiga. |

## Como exportá-lo

```
py -3 read_report.py --export-status DIR          # ci_status_public.json + .md, apenas o que pode ser publicado
py -3 read_report.py --export-sign-queue FILE     # a fila de assinatura
```

Ambos leem o monitor em execução em `127.0.0.1` (sem quota do GitHub). Recusam-se a escrever enquanto o instantâneo está a carregar e explicam porquê; nesse caso o código de saída não é zero.

## O que precisa quem lê (o gerador do painel)

1. Ler `schema`; aceitar qualquer valor `>= 2` e ignorar os campos desconhecidos.
2. Ler `complete`; quando for `false`, manter a última exportação completa em vez de a substituir.
3. Mostrar `generated` junto dos números para que um ficheiro desatualizado se note.
4. Usar `repos.<NAME>.red[].url` como ligação; nunca o reconstruir.

## O que o monitor não faz

Não publica o ficheiro, não faz push para o repositório do perfil e não toca em nenhum workflow. Levar a exportação até ao painel é um passo do proprietário (ou de um workflow do repositório do perfil que leia o ficheiro exportado).

## O painel do perfil (contrato do consumidor)

O painel de estado de um repositório de perfil pode ler o mesmo documento de duas maneiras: do monitor em execução (`GET /api/outputs/dashboard.json`, desligado até ativar `outputs.dashboard.enabled`, apenas este computador) ou do ficheiro escrito por `py -3 read_report.py --export-status DIR` (só os workflows vermelhos, nunca o lado da assinatura). Aquilo com que o painel pode contar, verificado por um teste deste repositório:

1. `schema` é `2` e os campos só se acrescentam.
2. O documento servido é exatamente o de `ci_red.json`.
3. `complete: false` significa: mantenha a sua última imagem completa.
4. A exportação pública tem as chaves `schema`, `generated`, `tool_version`, `complete`, `red_repos` e `red`, e nada do estado de assinatura.

O monitor nunca envia o ficheiro para o repositório do perfil; levá-lo para lá é um passo do seu dono.
