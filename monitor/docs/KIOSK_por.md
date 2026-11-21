<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](KIOSK.md) | [🇪🇸 Español](KIOSK_spa.md) | [🇫🇷 Français](KIOSK_fra.md) | [🇮🇹 Italiano](KIOSK_ita.md) | [🇩🇪 Deutsch](KIOSK_deu.md) | [🇨🇳 简体中文](KIOSK_zho.md) | [🇯🇵 日本語](KIOSK_jpn.md) | **🇵🇹 Português**

# Quiosque: o monitor numa TV ou numa parede

O perfil de quiosque é a página do monitor para um ecrã em que ninguém toca: sem cabeçalho, sem separadores, com texto maior e, se quiser, um contraste alto e uma rotação por alguns separadores. Reutiliza o que a página já conhece (`?screen=`, `?tabs=`, `?rotate=`, `?chrome=0`; veja [SCREENS_por.md](SCREENS_por.md)) e acrescenta dois parâmetros. Não lê nada do GitHub e não escreve nada: apenas decide o aspeto da página.

Está **desligado por predefinição**. Com `kiosk.enabled` desligado, a página ignora `kiosk=1` no endereço, pelo que uma ligação copiada de outro sítio não muda nada.

## O endereço

`python bin/monitor_cli.py kiosk [PREDEFINIÇÃO] [--account ID]` imprime-o; não precisa de um monitor em execução. Por exemplo, `kiosk ops` imprime:

```
http://127.0.0.1:8765/?screen=1&tabs=now,al,charts&chrome=0&kiosk=1&scale=150
```

| Parâmetro | Significado |
|---|---|
| `kiosk=1` | liga o perfil (só quando `kiosk.enabled` está ligado) |
| `scale=%` | o tamanho do texto, de 100 a 400 (um valor fora do intervalo é trazido para ele) |
| `contrast=1` / `contrast=0` | contraste alto ligado ou desligado para esta janela (a definição `kiosk.high_contrast` é a predefinida) |
| `safe=PERCENTAGEM` | a margem de segurança desta janela, de 0 a 10 (a definição `kiosk.safe_margin_percent` é o valor por defeito) |
| `fit=1` / `fit=0` | a letra cresce com a janela nesta janela, ou não (a definição `kiosk.scale_with_window` é o valor por defeito) |
| `rotate=SECONDS` | percorrer os separadores de `tabs=` (o parâmetro que já existia; o comando só o acrescenta quando a rotação está ligada) |
| `chrome=0`, `screen=`, `tabs=`, `account=` | os que já existiam |

## Predefinições

| Predefinição | Separadores |
|---|---|
| `ops` | Agora, Alertas, Gráficos |
| `team` | Alertas, Saúde da equipa |
| `release` | Agora, Repositórios, Relatórios |
| `quiet` | só Alertas |

## Definições (Definições, Linha de comandos e Quiosque)

| Definição | Predefinição | Significado |
|---|---|---|
| `kiosk.enabled` | desligado | liga o perfil |
| `kiosk.font_scale_percent` | 150 | o tamanho do texto, de 100 a 400 |
| `kiosk.high_contrast` | desligado | fundo preto e linhas brancas |
| `kiosk.rotate_views` | desligado | uma predefinição com vários separadores muda de separador sozinha; desligado, o ecrã mostra o primeiro separador da predefinição |
| `kiosk.rotate_seconds` | 30 | quanto tempo fica cada separador (de 5 a 600) |
| `screens.version_check_seconds` | 300 | de quanto em quanto tempo a página consulta `/api/version` e se recarrega sozinha quando o monitor foi atualizado ou reiniciado (0 = nunca; o mínimo é 30) |
| `kiosk.safe_margin_percent` | 0 | a parte de cada borda, em percentagem, que a página deixa livre para uma televisão que corta a borda (overscan); de 0 a 10 |
| `kiosk.scale_with_window` | desligado | o tamanho da letra acima é o de uma janela de 1080 px no seu lado curto; ligado, cresce com a janela, pelo que uma televisão 4K se vê como uma Full HD |
| `screens.show_repo_names` | public | os nomes dos repositórios no quiosque, como nos ecrãs de parede: `public` mostra um repositório privado como `private-N` e omite os títulos, ramos e workflows das suas execuções, `none` chama `repo-N` a todos, `all` mostra tudo (aplica-se aos dados da página, `/api/data`) |

O tamanho aplica-se com o zoom da página, pelo que cada número e cada tabela crescem juntos. Um valor fora do seu intervalo não é um erro: é substituído pela predefinição.
