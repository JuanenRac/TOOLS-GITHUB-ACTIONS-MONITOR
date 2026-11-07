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
| **Versão** | **1.5.1** · [todas as versões](https://github.com/JuanenRac/TOOLS-GITHUB-ACTIONS-MONITOR/releases) |
| **Requisitos** | Python 3.11+ e a CLI do GitHub (`gh auth login`); mais nada |
| **Abre** | uma página só em `127.0.0.1`, em oito idiomas |
| **Escreve no GitHub** | nunca sozinho: apenas os comandos por lotes que lançar com um `--go` explícito |
| **Exporta** | `ci_red.json`, métricas Prometheus e JSON para o Grafana (tudo desligado até o ativar) |

## Capturas de ecrã

<p align="center"><img src="docs/screenshots/monitor_now_dark.png" alt="Now" width="92%"></p>
<p align="center"><img src="docs/screenshots/monitor_sentinel_dark.png" alt="Sentinel" width="92%"></p>
<p align="center"><img src="docs/screenshots/monitor_charts_dark.png" alt="Charts" width="92%"></p>
<p align="center"><img src="docs/screenshots/monitor_settings_light.png" alt="Settings" width="92%"></p>

*Dados de demonstração: os repositórios e nomes das imagens são inventados.*

## O que faz

- **Vermelho ou não, com uma só regra**: a última execução terminada de cada workflow no ramo predefinido. As execuções canceladas ou ignoradas nunca escondem uma falha anterior.
- **Sentinela**: alertas de segurança, higiene dos repositórios, pull requests antigas, versões prontas a publicar, compilações à espera de assinatura e um relatório em linguagem simples.
- **Página de definições**: altere caminhos, intervalos, quotas e interruptores no navegador; só uma lista fixa de chaves validadas, com cópia de segurança antes de cada gravação.
- **Gráficos e histórico**: minutos de cálculo, falhas e sucessos com barras animadas e um histórico diário (respeita o movimento reduzido).
- **Oito idiomas** (en, es, de, fr, it, ja, zh, pt) com o inglês como base; muda-se nas definições.
- **Saídas para painéis**: `ci_red.json`, um ponto de acesso Prometheus e uma fonte JSON para o Grafana, com um painel Grafana importável.
- **Ferramentas por lotes**: planeiam e lançam várias compilações de uma vez; nada é lançado sem `--go`.

## Arquitetura

<p align="center"><img src="images/architecture.svg" alt="Arquitetura" width="100%"></p>

## Início rápido

1. Instale o Python 3.11 ou superior e a [CLI do GitHub](https://cli.github.com/), e execute `gh auth login`.
2. Transfira este repositório (ou o zip da última release) e abra a pasta `monitor`.
3. Arranque-o: no Windows `MONITOR_GITHUB_ACTIONS.bat`, no Linux `./MONITOR_GITHUB_ACTIONS.sh`, no macOS duplo clique em `MONITOR_GITHUB_ACTIONS.command`, ou `python actions_monitor.py` em qualquer sistema.
4. Abra o endereço que aparece (`http://127.0.0.1:<porta>`). No primeiro arranque cria `actions_monitor.json` a partir do exemplo.
5. Abra **Definições** para indicar a sua conta do GitHub, os ecossistemas (grupos de repositórios por prefixo do nome) e o resto.

> A atualizar de uma versão anterior à 1.5.0? [`monitor/docs/MIGRATING_por.md`](monitor/docs/MIGRATING_por.md)

## Definições

Tudo vive em `actions_monitor.json` (criado a partir de `actions_monitor.example.json`). O separador **Definições** edita-o em segurança; os tokens e segredos nunca são mostrados nem guardados. Os ecossistemas, os alvos de compilação e os perfis de lote são ficheiros à parte para os quais aponta (`ecosystems_file`, `targets_file`, `profiles_file`); vão incluídos modelos neutros `*.example.json`. Referência completa: [`monitor/docs/SETTINGS_por.md`](monitor/docs/SETTINGS_por.md).

## Saídas para o Grafana e painéis

Tudo desligado por defeito, só local (`127.0.0.1`) e sem token adicional. Ao ativar nas definições obtém `/metrics` (formato Prometheus), `/api/outputs/grafana.json` e `/api/outputs/dashboard.json`, e um painel Grafana importável em [`monitor/docs/grafana`](monitor/docs/grafana). Detalhes: [`monitor/docs/OUTPUTS_por.md`](monitor/docs/OUTPUTS_por.md). O formato de `ci_red.json`: [`monitor/docs/CI_RED_SCHEMA_por.md`](monitor/docs/CI_RED_SCHEMA_por.md).

## Segurança

- Só escuta em `127.0.0.1` e recusa pedidos cujo `Host` ou `Origin` não seja local. Nunca o ligue a `0.0.0.0`: não tem início de sessão.
- Não guarda nenhum token: usa o seu próprio `gh`.
- Não escreve nada no GitHub por si só. Apenas `dispatch --go`, `dispatch --real` e `finalize --execute` escrevem, e só quando os lança.
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
├── monitor/                          o programa
├── docs/                             arquitetura, capturas
├── tools/                            geradores de imagens
├── images/                           banner e imagens
├── .github/                          CI e formulários
├── CHANGELOG.md                      mudanças por versão
├── LICENSE NOTICE AUTHORS            licenças e autoria
├── CONTRIBUTING.md SECURITY.md       ajudar, comunicar
├── SUPPORT.md CODE_OF_CONDUCT.md     suporte e conduta
└── monitor/
    ├── actions_monitor.py            servidor local
    ├── actions_monitor.html          a página web
    ├── sentinel_local.py             alertas e relatório
    ├── surface.py readiness.py       verificações, preparação
    ├── settings_api.py outputs.py    definições, métricas
    ├── signstate.py sigverify.py     assinatura: estado e controlo
    ├── read_report.py                relatório no terminal
    ├── gha_dispatch_all.py           compilações por lotes
    ├── events.py report_history.py   eventos e histórico
    ├── ci_red.py export_status.py    ficheiros para outros
    ├── i18n.py locales/              oito idiomas
    ├── toolconfig.py workspace.py    definições e clones
    ├── tests/                        testes sem rede
    └── docs/                         definições, Grafana
```

## Documentação

- [`monitor/docs/SETTINGS_por.md`](monitor/docs/SETTINGS_por.md): todas as definições
- [`monitor/docs/OUTPUTS_por.md`](monitor/docs/OUTPUTS_por.md): métricas, Grafana e exportações
- [`monitor/docs/CI_RED_SCHEMA_por.md`](monitor/docs/CI_RED_SCHEMA_por.md): o formato de ci_red.json
- [`monitor/docs/CI_RED_BRIDGE_por.md`](monitor/docs/CI_RED_BRIDGE_por.md): levar o ci_red.json para um painel
- [`monitor/QUICKSTART_pt.txt`](monitor/QUICKSTART_pt.txt): primeiros passos, em oito idiomas

## Contribuir

Leia [CONTRIBUTING.md](CONTRIBUTING.md). Comunique erros e ideias com os formulários de incidências; os problemas de segurança como descrito em [SECURITY.md](SECURITY.md).

## Autoria

Escrito por **JuanenRac (Electro Hobby 3D)** · electrohobby3d@gmail.com

## Licença

O código é GPL-3.0-or-later; a documentação é CC BY-SA 4.0. Consulte [LICENSE](LICENSE) e [NOTICE](NOTICE).
