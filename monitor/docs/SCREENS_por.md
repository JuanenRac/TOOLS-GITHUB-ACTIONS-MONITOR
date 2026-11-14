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
