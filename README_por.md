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
  <img src="https://img.shields.io/badge/Tests-4705_passing-brightgreen.svg" alt="4705 tests">
</p>

> Vigia os workflows de todos os seus repositórios e diz-lhe, numa página local, o que está a vermelho, o que está encravado e o que o espera.

O **GitHub Actions Monitor** é um pequeno programa que corre no seu próprio computador. Pergunta ao GitHub, com o seu próprio acesso `gh`, as últimas execuções de cada workflow dos seus repositórios, decide o que está mesmo a vermelho, avisa do que importa (segurança, higiene, versões prontas, quota) e mostra tudo numa página web que só o seu computador consegue abrir. Só precisa de Python e `gh`, nunca guarda um token e, por defeito, apenas lê.

## O que é

- **Um vigia das suas GitHub Actions**: com o seu próprio acesso `gh`, lê as últimas execuções de cada workflow de cada repositório seu e decide o que está a vermelho, o que está preso e o que o espera.
- **Três sentinelas que nunca escrevem no GitHub**: CI (execuções e workflows), Collab (issues e pull requests que precisam de uma pessoa) e Security (Dependabot, análise de código, análise de segredos, proteção de ramos) transformam o que leem em alertas de uma só lista.
- **Uma página, várias formas de a ver**: uma página local em `127.0.0.1` que se adapta de um telemóvel a um ecrã mural 4K (até três ecrãs ao mesmo tempo), um cliente de linha de comandos, uma vista no terminal, ficheiros e um ponto de acesso para os seus próprios painéis.
- **Duas edições**: o Lite é para uma pessoa e só mostra as execuções; o Complete acrescenta várias contas, uma equipa com funções, uma pontuação, a saúde de cada repositório, relatórios e um serviço para Docker.
- **Privado por conceção**: nada sai do seu computador, exceto as chamadas ao GitHub feitas com o seu acesso; a chave de uma IA opcional fica numa variável de ambiente; só se escreve no GitHub com os comandos por lotes que lança com um `--go` explícito.

## O que faz

- **Vermelho ou não, com uma só regra**: a última execução terminada de cada workflow no ramo predefinido. As execuções canceladas ou ignoradas nunca escondem uma falha anterior.
- **Sentinela**: alertas de segurança, higiene dos repositórios, pull requests antigas, versões prontas a publicar, compilações à espera de assinatura e um relatório em linguagem simples.
- **Sentinela Collab e uma lista de alertas**: issues e pull requests abertas que precisam de uma pessoa (esquecidas, críticas, revisões à espera, rascunhos antigos, conflitos), só de leitura e com um relógio próprio, e um separador Alertas com todas as sentinelas numa lista, filtro por origem e silêncios locais que acabam sozinhos.
- **Barra de estado, ecrã inteiro e tabelas ordenáveis**: o aviso mais importante (e uma janela com todos), a ligação, a quota, a última leitura, o modo, o endereço e o relógio ao pé da página; um botão de ecrã inteiro; Repositórios e Histórico ordenam-se por uma ou várias colunas, com as colunas à sua escolha.
- **A linha de comandos como cliente**: `bin/monitor_cli.py` (`status`, `health`, `alerts`, `accounts`, `live`, `doctor`, `score`) lê o que o monitor em execução diz, com `--json` e códigos de saída estáveis; nunca escreve no GitHub.
- **Duas skills para IAs**: guias curtos, em inglês, para a IA integrada no monitor (local ou de um fornecedor) e para as IA que falam com ele a partir de fora (linha de comandos, só HTTP ou ficheiros, MCP, stream), geradas a partir do código para que nada falte; instalam-se com `python bin/monitor_cli.py install-skill internal|external --dest PASTA` ou copiam-se do separador IA das Definições (`monitor/docs/SKILLS_por.md`).
- **Falhas e lições**: um livro local das falhas da sua CI, regras que classificam cada uma numa categoria, uma biblioteca de lições (`monitor/docs/LESSONS_por.md`) com a guarda que a teria evitado, a tendência de 24 horas e 7 dias, `ai/LESSONS.md`, `/api/ai/lessons` e um resumo antes do push para qualquer ferramenta de IA; só leitura, nada sai do computador.
- **Todos os tamanhos de ecrã e vários ecrãs**: a página ajusta-se a uma janela desde um telemóvel até 4K, na vertical ou rodada, e um monitor pode servir até três ecrãs (`/screen/1` a `/screen/3`), cada um com os seus separadores e a sua orientação (`monitor/docs/SCREENS_por.md`).
- **Uma pontuação por conta**: um número de 0 a 100, uma letra de A a E e uma tendência, feitos com a fiabilidade da CI, a sua velocidade, o tempo de recuperação e a rapidez com que se fecham os alertas de colaboração; diz «a calibrar» ou «dados insuficientes» em vez de um número que não consegue sustentar, mostra o que ainda não cobre, está no cabeçalho da página, tem um comando `score`, avisa quando desce e está nas métricas e no servidor MCP (`monitor/docs/SCORE.md`).
- **Um sentinela de segurança (só Complete, desligado por predefinição)**: lê, sem escrever nada no GitHub, os alertas abertos do Dependabot, da análise de código e da análise de segredos, se o ramo predefinido está protegido, a permissão predefinida dos fluxos e, se pedir, os proprietários do código; gera um alerta por repositório e sinal, conta os achados como quinta parte da pontuação e diz o que não conseguiu ler (`monitor/docs/SENTINEL_SECURITY_por.md`).
- **Um sentinela da cadeia de abastecimento (só Complete, desligado por predefinição)**: lê, sem escrever nada no GitHub, os ficheiros de fluxo de cada repositório pela API (sem clonar) e gera um alerta por repositório e sinal quando uma ação não está fixada a um commit ou segue um ramo móvel, um fluxo dá `write-all` ao token ou não declara permissões, ou `pull_request_target` obtém o código de um pull request; as deteções vêm do linter de fluxos, o valor de um segredo nunca é lido e um repositório que não conseguiu ler fica listado em vez de contado como limpo (`monitor/docs/SENTINEL_SUPPLY_por.md`).
- **A saúde de cada repositório e da equipa (só Complete)**: CI, alertas das três sentinelas, preparação das versões e atividade num estado (mau, aviso, bom ou não visto) com um número de risco; o separador Equipa põe primeiro os repositórios que precisam de uma pessoa, com filtros, um detalhe de cada um e ligações diretas para ecrãs de parede; os mesmos dados estão em `/api/team/health`, `/api/repos/<owner>/<repo>/health` e no comando `team` (`monitor/docs/HEALTH_por.md`).
- **Relatórios, registo de ações e Apprise (só Complete)**: um relatório da conta (pontuação, mudanças, repositórios que precisam de uma pessoa, alertas abertos) escrito em HTML e Markdown segundo um horário cron ou a pedido, desligado por predefinição (`monitor/docs/REPORT_SCHEDULE_por.md`); um registo de quem mudou o quê, com uma cadeia de hashes e sem valores nem segredos (`monitor/docs/AUDIT_LOG_por.md`); e um canal opcional do Apprise para as notificações, desligado por predefinição.
- **Como serviço**: a imagem oficial do Docker (sem root, só de leitura), um ficheiro Compose com proxy opcional, uma unidade systemd, uma verificação de saúde profunda e o comando que cria o primeiro administrador (`monitor/docs/DEPLOYMENT.md`).
- **Uma API congelada e um guia para cada uso**: desde a 2.0.0 a forma de cada endpoint de leitura e os códigos de erro estão fixados em `monitor/docs/schemas/api_contract.json`, uma ferramenta verifica qualquer monitor em execução contra esse contrato (`monitor/tools/check_api_contract.py`) e há um guia curto para a edição lite, para uma pessoa, para um serviço e para uma equipa (`monitor/docs/API_por.md`).
- **Várias contas, uma equipa e um lugar para os dados**: um processo por conta, utilizadores com papéis e as suas próprias contas, os ficheiros em `config/`, `data/`, `logs/` e `ai/`, um armazenamento SQLite opcional com retenção e cópia de segurança, e as portas como definições (`monitor/docs/ACCOUNTS.md`, `monitor/docs/STORAGE.md`, `monitor/docs/LAYOUT.md`).
- **Listas que se ordenam e se dobram**: «A acontecer agora» de sete maneiras e o separador de Alertas de nove, com um botão para dobrar ou desdobrar todos os repositórios; a escolha fica guardada por utilizador.
- **Notificações para cada utilizador**: no modo de equipa, cada utilizador escolhe num painel da página os canais (ntfy, Teams, correio), o nível mínimo e os resumos (`monitor/docs/NOTIFICATIONS_por.md`).
- **Página de definições**: altere caminhos, intervalos, quotas e interruptores no navegador; só uma lista fixa de chaves validadas, com cópia de segurança antes de cada gravação.
- **Gráficos e histórico**: minutos de cálculo, falhas e sucessos com barras animadas e um histórico diário (respeita o movimento reduzido).
- **Oito idiomas** (en, es, de, fr, it, ja, zh, pt) com o inglês como base; muda-se nas definições.
- **Saídas para painéis**: `ci_red.json`, um ponto de acesso Prometheus e uma fonte JSON para o Grafana, com um painel Grafana importável.
- **Ferramentas por lotes**: planeiam e lançam várias compilações de uma vez; nada é lançado sem `--go`.
- **Acerca de e Ajuda na página**: o botão **i** mostra a versão, a edição, as ligações, os ficheiros, o estado de saúde e um botão que copia a informação para o suporte; o botão **?** (ou a tecla `?`) abre toda a documentação, com pesquisa e no seu idioma, sem Internet. A consola tem `--about` e `--help-topics`, e uma aplicação interativa de terminal por separadores (`textual` opcional).
- **Aviso de versão nova**: um emblema discreto quando sai uma versão mais recente; só lê a página pública de versões uma vez por dia, nunca instala nada e pode ser desligado (sempre desligado numa instalação isolada).
- **Quotas para qualquer conta**: plano, minutos faturáveis (os repositórios públicos não custam), quota da API lida dos cabeçalhos do GitHub, concorrência e jobs perto do limite de 6 horas; os valores estão num ficheiro editável.

## O que poupa

Usar o monitor em vez de consultar o Actions à mão poupa tempo. É uma **estimativa, não uma medição**: cerca de **85-95 % do tempo gasto a vigiar a CI e a triar falhas** e, em consequência, cerca de **15-25 % da produtividade global de uma equipa** que trabalha com muitos repositórios. Pressupõe que, sem o monitor, alguém abre o separador Actions de cada repositório para ver o que está a vermelho e lê cada registo falhado para encontrar a causa, que há falhas todas as semanas e que vigiar e triar ocupa entre um sexto e um terço do tempo de trabalho (os dois números só concordam com este pressuposto). Com poucos repositórios, ou se hoje ninguém vigia à mão, a poupança é muito menor.

| Tarefa | Sem o monitor | Com o monitor | Poupança estimada |
| --- | --- | --- | --- |
| Vigiar cada fluxo de trabalho de cada repositório | Abrir vezes sem conta o separador Actions de cada repositório | Uma página e uma lista de alertas que se atualizam sozinhas | 85-95 % |
| Decidir o que está mesmo a vermelho | Comparar execuções a olho (as canceladas e ignoradas escondem falhas) | Uma regra: a última execução concluída de cada fluxo no ramo predefinido | 85-95 % |
| Encontrar a causa de uma execução falhada | Abrir a execução, a tarefa e o registo | O alerta já nomeia o fluxo e a falha, com as lições que lhe correspondem | 85-95 % |
| Saber a tempo de uma falha | Dar por ela mais tarde, ou quando alguém avisa | Alertas, notificações e um resumo para as ferramentas de IA | 85-95 % |
| Não repetir um erro conhecido, segurança, higiene e versões prontas | Depende da memória e de revisões manuais | Biblioteca de lições e sentinelas | Não quantificado |

Método, pressupostos e como medi-lo na sua própria utilização: [`monitor/docs/PRODUCTIVITY_por.md`](monitor/docs/PRODUCTIVITY_por.md).

## Num relance

| | |
|---|---|
| **Versão** | **2.1.3** · [todas as versões](https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases) |
| **Requisitos** | Python 3.11+ e a CLI do GitHub (`gh auth login`); mais nada (a vista de consola usa o pacote opcional `rich`) |
| **Abre** | uma página só em `127.0.0.1`, em oito idiomas |
| **Escreve no GitHub** | nunca sozinho: apenas os comandos por lotes que lançar com um `--go` explícito |
| **Exporta** | `ci_red.json`, métricas Prometheus e JSON para o Grafana (tudo desligado até o ativar) |

<!-- glance:begin -->

**Medido hoje** (v2.1.3)

| | |
|---|---|
| **Maturidade** | functional |
| **Testes** | 4705 métodos de teste (`python -m unittest discover -s monitor/tests`) |
| **Definições** | 729 definições, todas com ajuda |
| **Idiomas** | 8 (inglês, espanhol, alemão, francês, italiano, japonês, chinês e português) |
| **Testado no CI em** | ubuntu, windows, Python 3.11, 3.13 |

## Estado do projeto

Cada linha é uma parte deste repositório e a luz diz até onde chega hoje: o que os testes e o CI podem mostrar e o que correu de verdade, não o que está planeado.

🟢 Feito e verificado · 🟡 Funciona, com limites conhecidos · 🟠 Feito em parte ou ainda não verificado · 🔴 Por fazer ou a não funcionar

| Área | Estado | O que significa aqui |
|---|---|---|
| Monitor e página | 🟢 | Corre todos os dias numa conta real; os testes correm no CI em Ubuntu e Windows. |
| Sentinela (A1..A13) | 🟢 | Corre todos os dias numa conta real; os níveis e linhas são testados com fixtures. |
| Notificações | 🟡 | Testadas contra servidores simulados; nem todos os canais foram experimentados com o serviço real. |
| Ligação a uma ferramenta de IA e MCP | 🟡 | O feed, o estado, o fluxo, o hook e as ferramentas MCP são testados com um servidor real e um cliente simulado; nenhum utilizador independente os usou ainda. |
| Edição lite | 🟡 | Testada no CI e partilha os canais e definições da completa; pouco uso real até agora. |
| GitHub App, painel central e modo poupança | 🟠 | Novo: testado com servidores e ficheiros simulados; ainda não correu muito tempo com o serviço real. |
| Pontuação de cada conta | 🟡 | Testada com séries sintéticas, dados de teste e servidores simulados; ainda não foi observada durante semanas em contas reais. |
| Imagem Docker e modo de serviço | 🟡 | A imagem é construída e testada na CI (sem root, só de leitura, com um acesso revogado); ainda pouco tempo como serviço de longa duração. |
| Modo de equipa e várias contas | 🟡 | Testado com processos reais e utilizadores simulados; uma equipa real ainda não o usou durante muito tempo. |
| Armazenamento (ficheiros e SQLite) | 🟡 | Testado com os dois suportes e as migrações entre eles; uma base de dados com meses ainda não passou por uma atualização. |
| Linux e macOS | 🟠 | O Linux é testado só no CI; o macOS não é testado no CI por agora; o uso diário é no Windows. |

<!-- glance:end -->

## Arquitetura

<p align="center"><img src="images/architecture.svg" alt="Arquitetura" width="100%"></p>

## Comece aqui: que edição?

| Se quer... | Arranque | Porta |
|---|---|---|
| ver o que corre e o que falha, nada mais (**comece aqui**) | `MONITOR_LITE_GITHUB_ACTIONS` | 8766 |
| toda a conta vigiada por si: alertas, versões, assinatura, prontidão, análise | `MONITOR_GITHUB_ACTIONS` (com a [sentinela](monitor/docs/SENTINEL_por.md)) | 8765 |

A janela da consola indica qual está a correr, no título e na primeira linha. Ainda tem dúvidas? `python bin/actions_monitor.py --demo` abre a página com dados inventados e `--doctor` verifica a sua instalação. [Os seus primeiros cinco minutos](monitor/docs/FIRST_STEPS_por.md)

## Início rápido

1. Instale o Python 3.11 ou superior e a [CLI do GitHub](https://cli.github.com/), e execute `gh auth login`.
2. Transfira este repositório (ou o zip da última release) e abra a pasta `monitor`.
3. Arranque-o: no Windows `MONITOR_GITHUB_ACTIONS.bat`, no Linux `./MONITOR_GITHUB_ACTIONS.sh`, no macOS duplo clique em `MONITOR_GITHUB_ACTIONS.command`, ou `python bin/actions_monitor.py` em qualquer sistema.
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

## Capturas de ecrã

### A página

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_now_light.png"><img src="docs/screenshots/web_now_dark.png" alt="Agora" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_menu_groups_light.png"><img src="docs/screenshots/web_menu_groups_dark.png" alt="O menu em grupos: Vigiar, Sentinelas, Equipa, Relatórios e aprendizagem" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_ci_light.png"><img src="docs/screenshots/web_sentinel_ci_dark.png" alt="Sentinela: CI" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_collab_light.png"><img src="docs/screenshots/web_sentinel_collab_dark.png" alt="Sentinela: colaboração" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_delivery_light.png"><img src="docs/screenshots/web_sentinel_delivery_dark.png" alt="Sentinela de entrega: o que está construído mas ainda não foi entregue" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_supply_light.png"><img src="docs/screenshots/web_sentinel_supply_dark.png" alt="Sentinela da cadeia de fornecimento: ações não fixadas e permissões amplas" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_trend_light.png"><img src="docs/screenshots/web_sentinel_trend_dark.png" alt="Tendência diária: uma linha para cada valor" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_fleet_light.png"><img src="docs/screenshots/web_fleet_dark.png" alt="Frota: todos os repositórios num relance" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_reports_light.png"><img src="docs/screenshots/web_reports_dark.png" alt="Relatórios" width="92%"></picture></p>
<p align="center"><img src="docs/screenshots/web_theme_midnight.png" alt="A página inteira noutro tema (Midnight)" width="92%"></p>
<p align="center"><img src="docs/screenshots/web_screen_overview_1080p.png" alt="Ecrã de parede: visão geral" width="92%"></p>
<p align="center"><img src="docs/screenshots/web_screen_now_1080p.png" alt="Ecrã de parede: neste momento" width="92%"></p>
<p align="center"><img src="docs/screenshots/web_screen_sentinels_1080p.png" alt="Ecrã de parede: sentinelas" width="92%"></p>
<p align="center"><img src="docs/screenshots/web_screen_rotate.png" alt="Ecrã de parede que roda sozinho pelos três ecrãs" width="92%"></p>
<p align="center"><img src="docs/screenshots/web_screen_overview_midnight.png" alt="Ecrã de parede com o logótipo da organização e o seu próprio tema" width="92%"></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_alerts_light.png"><img src="docs/screenshots/web_alerts_dark.png" alt="Alertas: todas as sentinelas numa lista, com silêncios locais" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_light.png"><img src="docs/screenshots/web_sentinel_dark.png" alt="Sentinela" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_queue_light.png"><img src="docs/screenshots/web_sentinel_queue_dark.png" alt="Fila de assinatura (o mais urgente primeiro)" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_sentinel_analytics_light.png"><img src="docs/screenshots/web_sentinel_analytics_dark.png" alt="A12 · Análises: durações, tempo em fila, passos e workflows instáveis" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_charts_light.png"><img src="docs/screenshots/web_charts_dark.png" alt="Gráficos" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_compare_light.png"><img src="docs/screenshots/web_compare_dark.png" alt="Comparar períodos: este período face ao anterior" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_repositories_light.png"><img src="docs/screenshots/web_repositories_dark.png" alt="Repositórios" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_team_light.png"><img src="docs/screenshots/web_team_dark.png" alt="Equipa: a saúde dos repositórios, por ordem" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_history_light.png"><img src="docs/screenshots/web_history_dark.png" alt="Histórico" width="92%"></picture></p>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_about_light.png"><img src="docs/screenshots/web_about_dark.png" alt="Acerca de" width="92%"></picture></p>
<p align="center"><img src="docs/screenshots/web_updater.png" alt="O atualizador: todas as versões publicadas, para passar a qualquer uma delas" width="92%"></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_updates_light.png"><img src="docs/screenshots/web_updates_dark.png" alt="Menu Sistema, Atualizações: versão instalada e disponível" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_help_light.png"><img src="docs/screenshots/web_help_dark.png" alt="Ajuda, com pesquisa e sem ligação" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_basic_light.png"><img src="docs/screenshots/web_settings_basic_dark.png" alt="Definições · Básico: plano, quotas e descoberta" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_network_now_light.png"><img src="docs/screenshots/web_network_now_dark.png" alt="O modo rede: a barra vermelha persistente" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_network_notices_light.png"><img src="docs/screenshots/web_network_notices_dark.png" alt="A barra do pé: o aviso mais importante e a janela com todos" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_network_settings_light.png"><img src="docs/screenshots/web_network_settings_dark.png" alt="Definições · o modo rede com o seu aviso e o nome do proxy HTTPS" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_accounts_all_light.png"><img src="docs/screenshots/web_accounts_all_dark.png" alt="Todas as contas: um cartão por conta" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_accounts_one_light.png"><img src="docs/screenshots/web_accounts_one_dark.png" alt="A página de uma conta, com o seletor" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_accounts_live_light.png"><img src="docs/screenshots/web_accounts_live_dark.png" alt="Vista Ao vivo: o recetor de webhook e o modo de trabalho" width="92%"></picture></p>

<details><summary><b>Definições, subseparador a subseparador</b></summary>

<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_interface_light.png"><img src="docs/screenshots/web_settings_interface_dark.png" alt="Definições · Este navegador" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_general_light.png"><img src="docs/screenshots/web_settings_general_dark.png" alt="Definições · Geral" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_polling_light.png"><img src="docs/screenshots/web_settings_polling_dark.png" alt="Definições · Atualização e limites" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_cache_light.png"><img src="docs/screenshots/web_settings_cache_dark.png" alt="Definições · Leituras e cache" width="92%"></picture></p>
<p align="center"><picture><source media="(prefers-color-scheme: light)" srcset="docs/screenshots/web_settings_quota_light.png"><img src="docs/screenshots/web_settings_quota_dark.png" alt="Definições · Quota" width="92%"></picture></p>
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

## Definições

Tudo vive em `actions_monitor.json` (criado a partir de `monitor/assets/examples/actions_monitor.example.json`). O separador **Definições** edita-o em segurança; os tokens e segredos nunca são mostrados nem guardados. Os ecossistemas, os alvos de compilação e os perfis de lote são ficheiros à parte para os quais aponta (`ecosystems_file`, `targets_file`, `profiles_file`); vão incluídos modelos neutros `*.example.json`. Referência completa: [`monitor/docs/SETTINGS_por.md`](monitor/docs/SETTINGS_por.md).

## Saídas para o Grafana e painéis

Tudo desligado por defeito, só local (`127.0.0.1`) e sem token adicional. Ao ativar nas definições obtém `/metrics` (formato Prometheus), `/api/outputs/grafana.json` e `/api/outputs/dashboard.json`, e um painel Grafana importável em [`monitor/docs/grafana`](monitor/docs/grafana). Detalhes: [`monitor/docs/OUTPUTS_por.md`](monitor/docs/OUTPUTS_por.md). O formato de `ci_red.json`: [`monitor/docs/CI_RED_SCHEMA_por.md`](monitor/docs/CI_RED_SCHEMA_por.md).

## Segurança

- Só escuta em `127.0.0.1` e recusa pedidos cujo `Host` ou `Origin` não seja local. Nunca o ligue a `0.0.0.0`: não tem início de sessão.
- Não guarda nenhum token: usa o seu próprio `gh` (a menos que ative o token opcional do monitor em Definições > Avançado).
- Não escreve nada no GitHub por si só. Apenas `dispatch --go`, `dispatch --real` e `finalize --execute` escrevem, e só quando os lança.
- O modo de rede e o modo de equipa estão desligados por predefinição; ligados, o acesso, os papéis, os bloqueios e o registo de auditoria protegem a página, e cada pedido é avaliado para uma só conta (`monitor/docs/DEPLOYMENT.md`, `monitor/docs/ACCOUNTS.md`).
- **Análises**: p50 / p95 da duração, do tempo em fila e de cada passo de cada workflow, workflows instáveis (falharam e depois passaram no mesmo commit) e workflows que ficaram mais lentos; exportadas para o Prometheus e o Grafana.
- **Poupa quota e sobrevive a um corte**: leituras condicionais (um 304 não custa nada) e um modo de última imagem com aviso de sem ligação que retoma sozinho.
- **Webhook de entrada e notificações**: eventos assinados atualizam um repositório em tempo real; mensagens opcionais para Telegram, Discord, Slack, Matrix, MQTT ou um endereço local (nunca uma escrita no GitHub).
- **Linter de workflows e vista de consola**: `bin/lint_workflows.py` verifica `.github/workflows` antes do push; `bin/tui.py` (opcional, com `rich`) mostra uma grelha em direto na consola.
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
├── monitor/                            o programa
├── docs/                               arquitetura, capturas, roteiro
├── tools/                              imagens, guias e demo
├── deploy/                             imagem, compose, systemd
├── images/                             banner e imagens
├── .github/                            CI e formulários
├── CHANGELOG.md                        mudanças por versão
├── LICENSE NOTICE AUTHORS              licenças e autoria
├── CONTRIBUTING.md SECURITY.md         ajudar, comunicar
├── SUPPORT.md CODE_OF_CONDUCT.md       suporte e conduta
└── monitor/
    ├── MONITOR_GITHUB_ACTIONS.*        os lançadores (duplo clique)
    ├── MONITOR_LITE_GITHUB_ACTIONS.*   a edição lite
    ├── BATCH_GITHUB_ACTIONS.*          o menu das compilações por lotes
    ├── src/                            o pacote importável
    ├── assets/                         exemplos, a página, idiomas
    ├── bin/                            os comandos curtos (read_report, monitor_cli ...)
    ├── tests/                          testes sem rede
    ├── docs/                           guias, inícios rápidos, esquemas, Grafana
    ├── skills/                         as duas skills para IAs
    └── tools/                          scripts de versão e migração
```

## Documentação

- [`monitor/docs/SETTINGS_por.md`](monitor/docs/SETTINGS_por.md): todas as definições
- [`monitor/docs/OUTPUTS_por.md`](monitor/docs/OUTPUTS_por.md): métricas, Grafana e exportações
- [`monitor/docs/CI_RED_SCHEMA_por.md`](monitor/docs/CI_RED_SCHEMA_por.md): o formato de ci_red.json
- [`monitor/docs/CI_RED_BRIDGE_por.md`](monitor/docs/CI_RED_BRIDGE_por.md): levar o ci_red.json para um painel
- [`monitor/docs/WEBHOOK_por.md`](monitor/docs/WEBHOOK_por.md): o webhook de entrada
- [`monitor/docs/CHATOPS_por.md`](monitor/docs/CHATOPS_por.md): comandos de chat só de leitura para Slack e Discord
- [`monitor/docs/SOUNDS_por.md`](monitor/docs/SOUNDS_por.md): um som para cada tipo de evento
- [`monitor/docs/UPDATE_por.md`](monitor/docs/UPDATE_por.md): o atualizador: passar a outra versão e migrar a configuração
- [`monitor/docs/OPS_por.md`](monitor/docs/OPS_por.md): Operar a instalação: cópia de segurança completa, restauro, cópia agendada, purga a pedido, o doctor e os seus códigos de saída, appliance com systemd e Docker
- [`monitor/docs/LITE_por.md`](monitor/docs/LITE_por.md): A edição lite
- [`monitor/docs/COMPLETE_INDIVIDUAL_por.md`](monitor/docs/COMPLETE_INDIVIDUAL_por.md): Edição completa para uma pessoa
- [`monitor/docs/COMPLETE_SERVICE_por.md`](monitor/docs/COMPLETE_SERVICE_por.md): Edição completa como serviço
- [`monitor/docs/COMPLETE_TEAM_por.md`](monitor/docs/COMPLETE_TEAM_por.md): Edição completa para uma equipa
- [`monitor/docs/API_por.md`](monitor/docs/API_por.md): A API para clientes
- [`monitor/docs/API_V1_por.md`](monitor/docs/API_V1_por.md): A API de leitura v1, passo a passo
- [`monitor/docs/ASSISTANT_por.md`](monitor/docs/ASSISTANT_por.md): O assistente: perguntas fixas só de leitura à sua IA
- [`monitor/docs/NOTIFICATIONS_por.md`](monitor/docs/NOTIFICATIONS_por.md): notificações e o contrato dos adaptadores
- [`monitor/docs/AI_por.md`](monitor/docs/AI_por.md): o assistente de IA: fornecedores, segurança e ações
- [`monitor/docs/ANALYTICS_por.md`](monitor/docs/ANALYTICS_por.md): análises, leituras condicionais e ligação perdida
- [`monitor/docs/CONSOLE_TOOLS_por.md`](monitor/docs/CONSOLE_TOOLS_por.md): o linter de workflows e a vista de consola
- [`monitor/docs/DEPLOYMENT_por.md`](monitor/docs/DEPLOYMENT_por.md): executá-lo como serviço (a imagem oficial, Compose, systemd), atrás de um proxy, quando o GitHub revoga o acesso, permissões
- [`monitor/docs/LAYOUT_por.md`](monitor/docs/LAYOUT_por.md): as pastas do monitor, a mudança desde a 1.8.1 e o mapa para as IA
- [`monitor/docs/QUICKSTART_pt.txt`](monitor/docs/QUICKSTART_pt.txt): primeiros passos, em oito idiomas
- [`monitor/docs/FIRST_STEPS_por.md`](monitor/docs/FIRST_STEPS_por.md): os seus primeiros cinco minutos
- [`monitor/docs/SENTINEL_por.md`](monitor/docs/SENTINEL_por.md): a sentinela e as suas verificações A1-A13
- [`monitor/docs/COLLAB_por.md`](monitor/docs/COLLAB_por.md): a sentinela Collab, o separador Alertas e os silêncios
- [`monitor/docs/SENTINEL_SECURITY_por.md`](monitor/docs/SENTINEL_SECURITY_por.md): O sentinela de segurança: Dependabot, análise de código, segredos, proteção de ramos, permissões dos fluxos e CODEOWNERS, e o que não conseguiu verificar
- [`monitor/docs/SENTINEL_SUPPLY_por.md`](monitor/docs/SENTINEL_SUPPLY_por.md): O sentinela da cadeia de abastecimento: ações não fixadas, ramos móveis, permissões de fluxo amplas ou em falta e pull_request_target com checkout, e o que não conseguiu ler
- [`monitor/docs/SENTINEL_DELIVERY_por.md`](monitor/docs/SENTINEL_DELIVERY_por.md): O sentinela de entrega: entradas por publicar, etiquetas sem versão, versões sem notas nem ficheiros, versões que não coincidem e fixações atrás de um contrato partilhado, e o que não conseguiu ler
- [`monitor/docs/AUDIT_LOG_por.md`](monitor/docs/AUDIT_LOG_por.md): O registo de ações: quem mudou o quê, a cadeia de hashes, quem o lê e as definições
- [`monitor/docs/HEALTH_por.md`](monitor/docs/HEALTH_por.md): A saúde de um repositório e da equipa: de que é feita, o separador Equipa, as ligações diretas e a API
- [`monitor/docs/REPORT_SCHEDULE_por.md`](monitor/docs/REPORT_SCHEDULE_por.md): Relatórios agendados: a pontuação, o que mudou, os repositórios que precisam de uma pessoa e os alertas abertos em HTML e Markdown, o horário e os ficheiros
- [`monitor/docs/CLI_por.md`](monitor/docs/CLI_por.md): a linha de comandos como cliente do monitor
- [`monitor/docs/ACCOUNTS_por.md`](monitor/docs/ACCOUNTS_por.md): várias contas, um processo cada
- [`monitor/docs/QUOTAS_por.md`](monitor/docs/QUOTAS_por.md): quotas e planos do GitHub
- [`monitor/docs/MODES_por.md`](monitor/docs/MODES_por.md): modos de trabalho: normal, rápido e turbo
- [`monitor/docs/AI_CONNECTION_por.md`](monitor/docs/AI_CONNECTION_por.md): Ligar uma ferramenta de IA: tudo o que o monitor diz, como sinais, no resumo, no endpoint, nas ferramentas MCP e no hook
- [`monitor/docs/AI_SETUP_PROMPT_por.md`](monitor/docs/AI_SETUP_PROMPT_por.md): Configurar o monitor com uma IA: um prompt para colar no teu assistente de IA que o instala, pergunta o que queres e escreve a configuração
- [`monitor/docs/QUOTA_por.md`](monitor/docs/QUOTA_por.md): Mais quota, menos gasto: modo poupança, o painel central, uma GitHub App e como partilhar a quota
- [`monitor/docs/EXTRAS_por.md`](monitor/docs/EXTRAS_por.md): Extras opcionais: o registo do passo falhado e um token só de leitura da GitHub App
- [`monitor/docs/SCORE_por.md`](monitor/docs/SCORE_por.md): A pontuação de uma conta: partes, estados, API, a ficha do cabeçalho, o alerta e as definições
- [`monitor/docs/COMPARE_por.md`](monitor/docs/COMPARE_por.md): Comparar períodos: este período face ao anterior, os números, o filtro de calendário, os estados sem número, a API, o comando e as definições
- [`monitor/docs/STORAGE_por.md`](monitor/docs/STORAGE_por.md): Armazenamento e retenção: ficheiros ou SQLite, cópia de segurança, migração e o que se guarda
- [`monitor/docs/ADVANCED_por.md`](monitor/docs/ADVANCED_por.md): Funções avançadas (todas desligadas por defeito)
- [`monitor/docs/AI_ALERTS_por.md`](monitor/docs/AI_ALERTS_por.md): Avisos para IAs: o feed, o resumo, o hook e o stream
- [`monitor/docs/AUDIT_PACKAGE_por.md`](monitor/docs/AUDIT_PACKAGE_por.md): Pacote para o auditor
- [`monitor/docs/LARGE_ACCOUNTS_por.md`](monitor/docs/LARGE_ACCOUNTS_por.md): Contas grandes: centenas de repositórios
- [`monitor/docs/ORGANIZATIONS_por.md`](monitor/docs/ORGANIZATIONS_por.md): Organizações e contas grandes
- [`monitor/docs/PRODUCTIVITY_por.md`](monitor/docs/PRODUCTIVITY_por.md): o que o monitor poupa: uma estimativa, os seus pressupostos e como a medir

## Contribuir

Leia [CONTRIBUTING.md](CONTRIBUTING.md). Comunique erros e ideias com os formulários de incidências; os problemas de segurança como descrito em [SECURITY.md](SECURITY.md).

## Autoria

Escrito por **JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## Licença

O código é GPL-3.0-or-later; a documentação é CC BY-SA 4.0. Consulte [LICENSE](LICENSE) e [NOTICE](NOTICE).
