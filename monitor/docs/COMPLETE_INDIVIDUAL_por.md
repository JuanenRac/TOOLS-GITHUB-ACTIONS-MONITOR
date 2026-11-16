<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_INDIVIDUAL.md) | [🇪🇸 Español](COMPLETE_INDIVIDUAL_spa.md) | [🇫🇷 Français](COMPLETE_INDIVIDUAL_fra.md) | [🇮🇹 Italiano](COMPLETE_INDIVIDUAL_ita.md) | [🇩🇪 Deutsch](COMPLETE_INDIVIDUAL_deu.md) | [🇨🇳 简体中文](COMPLETE_INDIVIDUAL_zho.md) | [🇯🇵 日本語](COMPLETE_INDIVIDUAL_jpn.md) | **🇵🇹 Português**

# Edição completa para uma pessoa

A edição completa no seu próprio computador é a forma habitual de usar o monitor: uma pessoa, uma conta do GitHub, sem início de sessão e uma página que só abre em `127.0.0.1`. A edição simples para quem só quer ver as suas execuções é [LITE_por.md](LITE_por.md).

## Começar

- Inicie sessão no GitHub uma vez com `gh auth login` e arranque `MONITOR_GITHUB_ACTIONS` (`.bat`, `.sh` ou `.command`). A página abre na porta 8765 (`ports.complete`).
- Escolha nas Definições os repositórios e ecossistemas a vigiar. Os primeiros cinco minutos estão em [FIRST_STEPS_por.md](FIRST_STEPS_por.md).

## O que obtém

- Três sentinelas (CI ativa; Collab e Security desligadas até as ligar) e uma lista de alertas que pode silenciar a partir do seu computador.
- A pontuação da conta, a saúde de cada repositório, relatórios agendados (desligados por predefinição) e um registo das ações realizadas (ativo por predefinição, `audit_log.enabled`).
- Os modos de trabalho normal, rápido e turbo ([MODES_por.md](MODES_por.md)) e o modo Baixo quando a quota escasseia ([QUOTA_por.md](QUOTA_por.md)).

## Mantê-lo neste computador

- Com `auth.enabled` desligado (a predefinição) não há utilizadores nem nada a recordar: ative o modo equipa apenas quando mais de uma pessoa usar o monitor ([COMPLETE_TEAM_por.md](COMPLETE_TEAM_por.md)).
- `listen.network` está desligado por predefinição: a página e a API só respondem a `127.0.0.1`. Para o deixar sempre a funcionar, leia [COMPLETE_SERVICE_por.md](COMPLETE_SERVICE_por.md).

## No dia a dia

- `python bin/monitor_cli.py status`, `doctor` e `health` consultam o monitor em execução ([CLI_por.md](CLI_por.md)). Para atualizar, leia [MIGRATING_por.md](MIGRATING_por.md).
- Os seus próprios scripts podem ler a API: [API_por.md](API_por.md) indica o que se promete que não muda.
