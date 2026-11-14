<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](FIRST_STEPS.md) | [🇪🇸 Español](FIRST_STEPS_spa.md) | [🇫🇷 Français](FIRST_STEPS_fra.md) | [🇮🇹 Italiano](FIRST_STEPS_ita.md) | [🇩🇪 Deutsch](FIRST_STEPS_deu.md) | [🇨🇳 简体中文](FIRST_STEPS_zho.md) | [🇯🇵 日本語](FIRST_STEPS_jpn.md) | **🇵🇹 Português**

# Os seus primeiros cinco minutos

**1. Instale o que ele precisa.** Python 3.11 ou superior e o GitHub CLI (`gh`). Depois inicie sessão uma vez: `gh auth login`. O monitor nunca guarda um token: pede-o ao `gh` (a menos que ative o token opcional do monitor em Definições > Avançado).

**2. Verifique tudo com um comando.** `python bin/actions_monitor.py --doctor` diz, para cada problema, o comando exato que o corrige. Prefere espreitar primeiro? `python bin/actions_monitor.py --demo` abre a página com dados inventados: sem `gh`, sem sessão, sem rede.

**3. Arranque-o.** Duplo clique em `MONITOR_LITE_GITHUB_ACTIONS` para a edição simples (porta 8766) ou em `MONITOR_GITHUB_ACTIONS` para a completa com sentinela (porta 8765). A janela da consola indica a edição, no título e na primeira linha.

**4. Siga os três passos de boas-vindas.** Na primeira vez, a página explica o que faz, mostra o que encontrou na sua conta e indica as definições básicas. Por defeito não se esconde nada: os repositórios que nenhum grupo reclama aparecem como *Sem classificar*.

**5. Saiba onde está a ajuda.** O botão redondo **?** (ou a tecla `?`) abre a Ajuda; o botão **i** abre Acerca de, com a sua versão, os seus ficheiros e um botão que copia a informação para o suporte (sem segredos). Na consola: `--help-topics`, `--help-search PALAVRAS`, `--about`.

**Convém saber.** Se usa um plano com repositórios privados, escolha-o em Definições > Básico para ver as suas quotas ([Quotas e planos](QUOTAS_por.md)). A sentinela está explicada em [A sentinela](SENTINEL_por.md). A ferramenta só lê o GitHub; só escreve depois de confirmar.
