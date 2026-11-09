<p align="center">
  <img src="images/GITHUB_ACTIONS_MONITOR_BANNER.svg" alt="GitHub Actions Monitor" width="100%">
</p>

# GitHub Actions Monitor

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <b>🇵🇹 Português</b>
</p>

<p align="center">
  <a href="https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases/latest"><img src="https://img.shields.io/github/v/release/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR?label=version&color=2EE6A6" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/License-GPL%203.0--or--later-blue.svg" alt="GPL-3.0-or-later">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Dependencies-none-2EE6A6.svg" alt="No dependencies">
  <img src="https://img.shields.io/badge/Languages-8-FFB300.svg" alt="8 languages">
</p>

> Vigia os workflows de todos os seus repositórios e diz-lhe, numa página local, o que está a vermelho, o que está encravado e o que o espera.

O **GitHub Actions Monitor** é um pequeno programa que corre no seu próprio computador. Pergunta ao GitHub, com o seu próprio acesso `gh`, as últimas execuções de cada workflow dos seus repositórios, decide o que está mesmo a vermelho, avisa do que importa (segurança, higiene, versões prontas, quota) e mostra tudo numa página web que só o seu computador consegue abrir. Só precisa de Python e `gh`, nunca guarda um token e, por defeito, apenas lê.

## Num relance

| | |
|---|---|
| **Versão** | **1.6.8** · [todas as versões](https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases) |
| **Requisitos** | Python 3.11+ e a CLI do GitHub (`gh auth login`); mais nada (a vista de consola usa o pacote opcional `rich`) |
| **Abre** | uma página só em `127.0.0.1`, em oito idiomas |
| **Escreve no GitHub** | nunca sozinho: apenas os comandos por lotes que lançar com um `--go` explícito |
| **Exporta** | `ci_red.json`, métricas Prometheus e JSON para o Grafana (tudo desligado até o ativar) |

## Capturas de ecrã

### A página

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_now_light.png"><img src="docs/screenshots/web_now_dark.png" alt="Agora" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_light.png"><img src="docs/screenshots/web_sentinel_dark.png" alt="Sentinela" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_queue_light.png"><img src="docs/screenshots/web_sentinel_queue_dark.png" alt="Fila de assinatura (o mais urgente primeiro)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_analytics_light.png"><img src="docs/screenshots/web_sentinel_analytics_dark.png" alt="A12 · Análises: durações, tempo em fila, passos e workflows instáveis" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_charts_light.png"><img src="docs/screenshots/web_charts_dark.png" alt="Gráficos" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_repositories_light.png"><img src="docs/screenshots/web_repositories_dark.png" alt="Repositórios" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_history_light.png"><img src="docs/screenshots/web_history_dark.png" alt="Histórico" width="92%"></picture></p>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_about_light.png"><img src="docs/screenshots/web_about_dark.png" alt="Acerca de" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_help_light.png"><img src="docs/screenshots/web_help_dark.png" alt="Ajuda, com pesquisa e sem ligação" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_basic_light.png"><img src="docs/screenshots/web_settings_basic_dark.png" alt="Definições · Básico: plano, quotas e descoberta" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_network_now_light.png"><img src="docs/screenshots/web_network_now_dark.png" alt="O modo rede: a barra vermelha persistente" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_network_settings_light.png"><img src="docs/screenshots/web_network_settings_dark.png" alt="Definições · o modo rede com o seu aviso e o nome do proxy HTTPS" width="92%"></picture></p>

<details><summary><b>Definições, subseparador a subseparador</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_interface_light.png"><img src="docs/screenshots/web_settings_interface_dark.png" alt="Definições · Este navegador" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_general_light.png"><img src="docs/screenshots/web_settings_general_dark.png" alt="Definições · Geral" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_polling_light.png"><img src="docs/screenshots/web_settings_polling_dark.png" alt="Definições · Atualização e limites" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_cache_light.png"><img src="docs/screenshots/web_settings_cache_dark.png" alt="Definições · Leituras e cache" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_sentinel_light.png"><img src="docs/screenshots/web_settings_sentinel_dark.png" alt="Definições · Sentinela" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_surface_light.png"><img src="docs/screenshots/web_settings_surface_dark.png" alt="Definições · Verificações de superfície (A10)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_readiness_light.png"><img src="docs/screenshots/web_settings_readiness_dark.png" alt="Definições · Preparação (A11)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_paths_light.png"><img src="docs/screenshots/web_settings_paths_dark.png" alt="Definições · Pastas e ficheiros" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_outputs_light.png"><img src="docs/screenshots/web_settings_outputs_dark.png" alt="Definições · Saídas para outras ferramentas" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_ai_light.png"><img src="docs/screenshots/web_settings_ai_dark.png" alt="Definições · IA externa para a sentinela" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_webhook_light.png"><img src="docs/screenshots/web_settings_webhook_dark.png" alt="Definições · Webhook de entrada" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_notify_light.png"><img src="docs/screenshots/web_settings_notify_dark.png" alt="Definições · Notificações" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_analytics_light.png"><img src="docs/screenshots/web_settings_analytics_dark.png" alt="Definições · Análises" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_lint_light.png"><img src="docs/screenshots/web_settings_lint_dark.png" alt="Definições · Linter de workflows" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_console_light.png"><img src="docs/screenshots/web_settings_console_dark.png" alt="Definições · Vista de consola" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_advanced_light.png"><img src="docs/screenshots/web_settings_advanced_dark.png" alt="Definições · Avançado (opcional)" width="92%"></picture></p>

</details>

<details><summary><b>Ferramentas de consola</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_read_report_light.png"><img src="docs/screenshots/console_read_report_dark.png" alt="read_report.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_migrate_state_light.png"><img src="docs/screenshots/console_migrate_state_dark.png" alt="migrate_state.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_plan_light.png"><img src="docs/screenshots/console_plan_dark.png" alt="gha_dispatch_all.py plan" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_lint_light.png"><img src="docs/screenshots/console_lint_dark.png" alt="lint_workflows.py" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/console_tui_light.png"><img src="docs/screenshots/console_tui_dark.png" alt="tui.py" width="92%"></picture></p>

</details>

<details><summary><b>A edição lite</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_now_light.png"><img src="docs/screenshots/web_lite_now_dark.png" alt="lite · Agora" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_charts_light.png"><img src="docs/screenshots/web_lite_charts_dark.png" alt="lite · Gráficos" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_history_light.png"><img src="docs/screenshots/web_lite_history_dark.png" alt="lite · Histórico" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_lite_settings_light.png"><img src="docs/screenshots/web_lite_settings_dark.png" alt="lite · Definições" width="92%"></picture></p>

</details>

Cada imagem segue o tema claro ou escuro da sua página do GitHub.

*Dados de demonstração: os repositórios e nomes das imagens são inventados.*

## O que faz

- **Vermelho ou não, com uma só regra**: a última execução terminada de cada workflow no ramo predefinido. As execuções canceladas ou ignoradas nunca escondem uma falha anterior.
- **Sentinela**: alertas de segurança, higiene dos repositórios, pull requests antigas, versões prontas a publicar, compilações à espera de assinatura e um relatório em linguagem simples.
- **Página de definições**: altere caminhos, intervalos, quotas e interruptores no navegador; só uma lista fixa de chaves validadas, com cópia de segurança antes de cada gravação.
- **Gráficos e histórico**: minutos de cálculo, falhas e sucessos com barras animadas e um histórico diário (respeita o movimento reduzido).
- **Oito idiomas** (en, es, de, fr, it, ja, zh, pt) com o inglês como base; muda-se nas definições.
- **Saídas para painéis**: `ci_red.json`, um ponto de acesso Prometheus e uma fonte JSON para o Grafana, com um painel Grafana importável.
- **Ferramentas por lotes**: planeiam e lançam várias compilações de uma vez; nada é lançado sem `--go`.
- **Acerca de e Ajuda na página**: o botão **i** mostra a versão, a edição, as ligações, os ficheiros, o estado de saúde e um botão que copia a informação para o suporte; o botão **?** (ou a tecla `?`) abre toda a documentação, com pesquisa e no seu idioma, sem Internet. A consola tem `--about` e `--help-topics`, e uma aplicação interativa de terminal por separadores (`textual` opcional).
- **Aviso de versão nova**: um emblema discreto quando sai uma versão mais recente; só lê a página pública de versões uma vez por dia, nunca instala nada e pode ser desligado (sempre desligado numa instalação isolada).
- **Quotas para qualquer conta**: plano, minutos faturáveis (os repositórios públicos não custam), quota da API lida dos cabeçalhos do GitHub, concorrência e jobs perto do limite de 6 horas; os valores estão num ficheiro editável.

## Arquitetura

<p align="center"><img src="images/architecture.svg" alt="Arquitetura" width="100%"></p>

## Comece aqui: que edição?

| Se quer... | Arranque | Porta |
|---|---|---|
| ver o que corre e o que falha, nada mais (**comece aqui**) | `MONITOR_LITE_GITHUB_ACTIONS` | 8766 |
| toda a conta vigiada por si: alertas, versões, assinatura, prontidão, análise | `MONITOR_GITHUB_ACTIONS` (com a [sentinela](monitor/docs/SENTINEL_por.md)) | 8765 |

A janela da consola indica qual está a correr, no título e na primeira linha. Ainda tem dúvidas? `python actions_monitor.py --demo` abre a página com dados inventados e `--doctor` verifica a sua instalação. [Os seus primeiros cinco minutos](monitor/docs/FIRST_STEPS_por.md)

## Início rápido

1. Instale o Python 3.11 ou superior e a [CLI do GitHub](https://cli.github.com/), e execute `gh auth login`.
2. Transfira este repositório (ou o zip da última release) e abra a pasta `monitor`.
3. Arranque-o: no Windows `MONITOR_GITHUB_ACTIONS.bat`, no Linux `./MONITOR_GITHUB_ACTIONS.sh`, no macOS duplo clique em `MONITOR_GITHUB_ACTIONS.command`, ou `python actions_monitor.py` em qualquer sistema.
4. Abra o endereço que aparece (`http://127.0.0.1:<porta>`). No primeiro arranque cria `actions_monitor.json` a partir do exemplo.
5. Abra **Definições** para indicar a sua conta do GitHub, os ecossistemas (grupos de repositórios por prefixo do nome) e o resto.

> A atualizar de uma versão anterior à 1.5.0? [`monitor/docs/MIGRATING_por.md`](monitor/docs/MIGRATING_por.md)

## A edição lite

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

[`monitor/docs/LITE_por.md`](monitor/docs/LITE_por.md)

## Definições

Tudo vive em `actions_monitor.json` (criado a partir de `actions_monitor.example.json`). O separador **Definições** edita-o em segurança; os tokens e segredos nunca são mostrados nem guardados. Os ecossistemas, os alvos de compilação e os perfis de lote são ficheiros à parte para os quais aponta (`ecosystems_file`, `targets_file`, `profiles_file`); vão incluídos modelos neutros `*.example.json`. Referência completa: [`monitor/docs/SETTINGS_por.md`](monitor/docs/SETTINGS_por.md).

## Saídas para o Grafana e painéis

Tudo desligado por defeito, só local (`127.0.0.1`) e sem token adicional. Ao ativar nas definições obtém `/metrics` (formato Prometheus), `/api/outputs/grafana.json` e `/api/outputs/dashboard.json`, e um painel Grafana importável em [`monitor/docs/grafana`](monitor/docs/grafana). Detalhes: [`monitor/docs/OUTPUTS_por.md`](monitor/docs/OUTPUTS_por.md). O formato de `ci_red.json`: [`monitor/docs/CI_RED_SCHEMA_por.md`](monitor/docs/CI_RED_SCHEMA_por.md).

## Segurança

- Só escuta em `127.0.0.1` e recusa pedidos cujo `Host` ou `Origin` não seja local. Nunca o ligue a `0.0.0.0`: não tem início de sessão.
- Não guarda nenhum token: usa o seu próprio `gh` (a menos que ative o token opcional do monitor em Definições > Avançado).
- Não escreve nada no GitHub por si só. Apenas `dispatch --go`, `dispatch --real` e `finalize --execute` escrevem, e só quando os lança.
- **Análises**: p50 / p95 da duração, do tempo em fila e de cada passo de cada workflow, workflows instáveis (falharam e depois passaram no mesmo commit) e workflows que ficaram mais lentos; exportadas para o Prometheus e o Grafana.
- **Poupa quota e sobrevive a um corte**: leituras condicionais (um 304 não custa nada) e um modo de última imagem com aviso de sem ligação que retoma sozinho.
- **Webhook de entrada e notificações**: eventos assinados atualizam um repositório em tempo real; mensagens opcionais para Telegram, Discord, Slack, Matrix, MQTT ou um endereço local (nunca uma escrita no GitHub).
- **Linter de workflows e vista de consola**: `lint_workflows.py` verifica `.github/workflows` antes do push; `tui.py` (opcional, com `rich`) mostra uma grelha em direto na consola.
- **Assistente de IA (desligado por predefinição)**: resumos, triagem e explicações com Ollama, um serviço compatível com OpenAI, Anthropic ou `gh copilot`; só comandos de uma lista fechada, executados apenas depois de confirmar cada um.
- A página de definições escreve uma lista fixa de chaves validadas, depois de guardar uma cópia de segurança.

## Testes

Não precisam de rede nem de pacotes adicionais:

```
python -m unittest discover -s monitor/tests
```

## Estrutura do repositório

<p align="center"><img src="images/repository-structure.svg" alt="Estrutura do repositório" width="100%"></p>

```
TOOLS-GITHUB-ACTIONS-MONITOR/
├── monitor/                             o programa
├── docs/                                arquitetura, capturas, roteiro
├── tools/                               imagens, guias e demo
├── deploy/                              exemplo de contentor
├── images/                              banner e imagens
├── .github/                             CI e formulários
├── CHANGELOG.md                         mudanças por versão
├── LICENSE NOTICE AUTHORS               licenças e autoria
├── CONTRIBUTING.md SECURITY.md          ajudar, comunicar
├── SUPPORT.md CODE_OF_CONDUCT.md        suporte e conduta
└── monitor/
    ├── actions_monitor.py               servidor local
    ├── actions_monitor.html             a página web
    ├── MONITOR_LITE_GITHUB_ACTIONS.*    a edição lite
    ├── sentinel_local.py                alertas e relatório
    ├── surface.py readiness.py          verificações, preparação
    ├── settings_api.py outputs.py       definições, métricas
    ├── signstate.py sigverify.py        assinatura: estado e controlo
    ├── read_report.py                   relatório no terminal
    ├── gha_dispatch_all.py              compilações por lotes
    ├── events.py report_history.py      eventos e histórico
    ├── ci_red.py export_status.py       ficheiros para outros
    ├── etagcache.py resilience.py       leituras condicionais
    ├── analytics.py lint_workflows.py   durações, flaky, linter
    ├── notifiers.py ai_actions.py       notificações, lista fechada IA
    ├── tui.py migrate_state.py          vista de consola, migração
    ├── about.py  helpdocs.py            painéis Acerca de e Ajuda
    ├── quota.py  quotas.json            plano, minutos e quotas
    ├── modes.py  updatecheck.py         modos de trabalho, aviso de versão
    ├── doctor.py  demo_mode.py          --doctor e --demo
    ├── discovery.py  banner.py          descoberta, banner da edição
    ├── tui_textual.py                   terminal interativo
    ├── i18n.py locales/                 oito idiomas
    ├── toolconfig.py workspace.py       definições e clones
    ├── tests/                           testes sem rede
    └── docs/                            guias, esquemas, Grafana
```

## Documentação

- [`monitor/docs/SETTINGS_por.md`](monitor/docs/SETTINGS_por.md): todas as definições
- [`monitor/docs/OUTPUTS_por.md`](monitor/docs/OUTPUTS_por.md): métricas, Grafana e exportações
- [`monitor/docs/CI_RED_SCHEMA_por.md`](monitor/docs/CI_RED_SCHEMA_por.md): o formato de ci_red.json
- [`monitor/docs/CI_RED_BRIDGE_por.md`](monitor/docs/CI_RED_BRIDGE_por.md): levar o ci_red.json para um painel
- [`monitor/docs/WEBHOOK_por.md`](monitor/docs/WEBHOOK_por.md): o webhook de entrada
- [`monitor/docs/LITE_por.md`](monitor/docs/LITE_por.md): A edição lite
- [`monitor/docs/NOTIFICATIONS_por.md`](monitor/docs/NOTIFICATIONS_por.md): notificações e o contrato dos adaptadores
- [`monitor/docs/AI_por.md`](monitor/docs/AI_por.md): o assistente de IA: fornecedores, segurança e ações
- [`monitor/docs/ANALYTICS_por.md`](monitor/docs/ANALYTICS_por.md): análises, leituras condicionais e ligação perdida
- [`monitor/docs/CONSOLE_TOOLS_por.md`](monitor/docs/CONSOLE_TOOLS_por.md): o linter de workflows e a vista de consola
- [`monitor/docs/DEPLOYMENT_por.md`](monitor/docs/DEPLOYMENT_por.md): executá-lo como serviço, atrás de um proxy, permissões
- [`monitor/QUICKSTART_pt.txt`](monitor/QUICKSTART_pt.txt): primeiros passos, em oito idiomas
- [`monitor/docs/FIRST_STEPS_por.md`](monitor/docs/FIRST_STEPS_por.md): os seus primeiros cinco minutos
- [`monitor/docs/SENTINEL_por.md`](monitor/docs/SENTINEL_por.md): a sentinela e as suas verificações A1-A13
- [`monitor/docs/QUOTAS_por.md`](monitor/docs/QUOTAS_por.md): quotas e planos do GitHub
- [`monitor/docs/MODES_por.md`](monitor/docs/MODES_por.md): modos de trabalho: normal, rápido e turbo

## Contribuir

Leia [CONTRIBUTING.md](CONTRIBUTING.md). Comunique erros e ideias com os formulários de incidências; os problemas de segurança como descrito em [SECURITY.md](SECURITY.md).

## Autoria

Escrito por **JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## Licença

O código é GPL-3.0-or-later; a documentação é CC BY-SA 4.0. Consulte [LICENSE](LICENSE) e [NOTICE](NOTICE).
