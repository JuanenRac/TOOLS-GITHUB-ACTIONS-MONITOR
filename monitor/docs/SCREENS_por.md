<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCREENS.md) | [🇪🇸 Español](SCREENS_spa.md) | [🇫🇷 Français](SCREENS_fra.md) | [🇮🇹 Italiano](SCREENS_ita.md) | [🇩🇪 Deutsch](SCREENS_deu.md) | [🇨🇳 简体中文](SCREENS_zho.md) | [🇯🇵 日本語](SCREENS_jpn.md) | **🇵🇹 Português**

# Ecrãs, tamanhos e orientação

A página adapta-se ao tamanho da janela, do telemóvel ao 4K, na vertical ou na horizontal, e um mesmo monitor pode servir vários ecrãs, cada um com os separadores que escolher. Nada é consultado duas vezes: todos os ecrãs leem o mesmo estado.

## Endereços

- `/` - a página inteira.
- `/screen/1`, `/screen/2`, `/screen/3` - os separadores definidos para esse ecrã (`ui.screen1_tabs` ...). Abra cada um numa janela do seu próprio monitor ou televisão.
- `?orient=portrait` ou `?orient=landscape` força a disposição de uma janela; `?tabs=now,charts` e `?rotate=30` definem os separadores e os segundos entre eles numa janela.

## Definições

| Definição | O que faz |
|---|---|
| `ui.orientation` | auto segue a janela; portrait empilha os painéis numa coluna; landscape mantém a disposição lado a lado. |
| `ui.rotate_seconds` | 0 = desligado. Segundos entre os separadores de um ecrã que tem mais de um. |
| `ui.screen1_tabs` | Separadores de /screen/1, separados por vírgulas: now, al, sent, charts, repos, hist, cfg. Vazio = todos. |
| `ui.screen1_orientation` | auto, portrait ou landscape só para /screen/1. |
| `ui.screen2_tabs` | Separadores de /screen/2. |
| `ui.screen2_orientation` | Orientação de /screen/2. |
| `ui.screen3_tabs` | Separadores de /screen/3. |
| `ui.screen3_orientation` | Orientação de /screen/3. |
| `ui.now_sort` | Ordem de A acontecer agora para quem não escolheu: ecosystem, severity, age, newest, repo, event ou state. |
| `ui.alerts_sort` | Ordem do separador Alertas para quem não escolheu: server, severity, streak, class, age, newest, repo, origin ou state. |

## Ordem das listas

A secção **A acontecer agora** do primeiro separador está ordenada por ecossistema, com um título para cada um. A lista por cima da secção altera-a: ecossistema, gravidade (primeiro as bloqueadas, depois as que têm uma tarefa com falha, depois as em curso e por fim as em fila), antiguidade (a que leva mais tempo, primeiro), mais recente primeiro, repositório, disparador (push, pull_request, schedule...) e estado (em curso antes de em fila). A escolha fica guardada para cada pessoa: no modo de equipa é o servidor que a guarda com o utilizador (`GET` e `POST /api/auth/me/view`, por isso acompanha-o noutro navegador); caso contrário, é este navegador. Enquanto ninguém escolhe, a ordem é `ui.now_sort` do ficheiro de configuração (ecossistema se faltar ou estiver errado). Os botões **Expandir tudo** e **Recolher tudo** junto à lista expandem ou recolhem de uma vez todos os repositórios da secção, com qualquer ordem; a escolha é lembrada por pessoa no mesmo sítio e sobrevive a uma atualização (um repositório que abra ou feche à mão depois mantém a sua escolha).

A lista do separador **Alertas** mantém a ordem que o monitor envia até alguém escolher outra com a lista por cima: gravidade (crítico, erro, aviso, info), a maior sequência de falhas seguidas primeiro, classe (um alerta de erro ou crítico é real e vai antes dos que há que vigiar), os mais antigos primeiro, os mais recentes primeiro, repositório, origem (a sentinela que o levantou) e estado (abertos antes de silenciados). Fica guardada do mesmo modo e, enquanto ninguém escolhe, vale `ui.alerts_sort` do ficheiro de configuração (`server` se faltar ou estiver errado).

## Tamanhos testados

Um teste de navegador abre a página em cada um destes tamanhos, percorre todos os separadores e falha se houver deslocação lateral ou texto que saia da sua caixa. As janelas de 2400 px ou mais recebem um tipo de letra maior (as de 3200 px, ainda maior) em vez de uma disposição esticada; uma janela mais alta do que larga empilha os painéis.

| Tamanho | Tipo |
|---|---|
| 1920x1080 | Full HD |
| 2560x1080 | 21:9 |
| 3440x1440 | 21:9 |
| 5120x1440 | 32:9 |
| 3840x2160 | 4K |
| 1080x1920 | Full HD |
| 2160x3840 | 4K |
| 768x1024 | tablet |
| 390x844 | phone |

## Receita para um posto com dois ou três ecrãs

1. No computador que executa o monitor, ponha `ui.screen1_tabs` em `now,al`, `ui.screen2_tabs` em `charts,repos` e, para um monitor rodado, `ui.screen2_orientation` em `portrait`.
2. Abra `http://este-computador:8765/screen/1` numa janela do primeiro monitor e `/screen/2` no segundo; F11 para ecrã inteiro. A partir de outro computador, use o modo de rede com o seu token de acesso.
3. Para um ecrã de parede em que ninguém toca, dê-lhe vários separadores e ponha `ui.rotate_seconds` em 20-30.

## Imagens

O separador Agora em quatro tamanhos, com dados inventados (4K, um monitor 21:9, um monitor rodado, um telemóvel):

![4K 3840x2160](../../docs/screenshots/web_size_4k_light.png)

![ultrawide 3440x1440](../../docs/screenshots/web_size_ultrawide_light.png)

![rodado 1080x1920](../../docs/screenshots/web_size_portrait_light.png)

![telemóvel 390x844](../../docs/screenshots/web_size_phone_light.png)
