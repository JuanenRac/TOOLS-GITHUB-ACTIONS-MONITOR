<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LITE.md) | [🇪🇸 Español](LITE_spa.md) | [🇫🇷 Français](LITE_fra.md) | [🇮🇹 Italiano](LITE_ita.md) | [🇩🇪 Deutsch](LITE_deu.md) | [🇨🇳 简体中文](LITE_zho.md) | [🇯🇵 日本語](LITE_jpn.md) | **🇵🇹 Português**

# A edição lite

Um segundo produto, mais simples, no mesmo pacote: a página do que está a correr e do que falha, sem a sentinela. Para quem só quer vigiar os seus runs.

|  | Completa | Lite |
|---|---|---|
| Arranque | `MONITOR_GITHUB_ACTIONS` (`.bat` / `.sh` / `.command`) | `MONITOR_LITE_GITHUB_ACTIONS` (os mesmos três) |
| Porta | 8765 | 8766 |
| Separadores | Agora, Sentinela, Gráficos, Repositórios, Histórico, Definições | Agora, Gráficos, Repositórios, Histórico, umas Definições curtas |
| Cabeçalho | todos os mosaicos, prontidão, assinatura | em curso, em fila, falhas e êxitos de 24 h, minutos de cálculo, issues, vermelhos em main, repositórios, quota, ligação |
| Sentinela (alertas, versões, fila de assinatura, prontidão, linter) | sim | não: nem sequer é importada |
| Análises, notificações, webhook, IA, saídas Prometheus / Grafana | sim, desligadas até as ligar | não: esses caminhos respondem 404 |
| Configuração | `actions_monitor.json` | `actions_monitor_lite.json` (criado no primeiro arranque; a sentinela está desligada nele) |
| Ficheiros de estado | `etag_cache.json`, `analytics_history.json`... | os mesmos nomes com o sufixo `_lite` |

Como a arrancar: `MONITOR_LITE_GITHUB_ACTIONS.bat` no Windows, `./MONITOR_LITE_GITHUB_ACTIONS.sh` no Linux, duplo clique em `MONITOR_LITE_GITHUB_ACTIONS.command` no macOS, ou `python actions_monitor.py --lite` (também `MONITOR_MODE=lite`). Escuta em `127.0.0.1:8766`, por isso a completa pode correr ao mesmo tempo.

As Definições curtas têm a conta (`github_owner`), os repositórios e ecossistemas a vigiar (`repos`, `ecosystems`, `exclude`), o tempo de atualização (`refresh_seconds`), o idioma e o tema. «Vermelhos em main» conta os workflows cujo último run concluído falhou. Para ter depois a sentinela e o resto, arranque a completa: não há nada a migrar.
