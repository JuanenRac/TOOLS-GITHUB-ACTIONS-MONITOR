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

**6. Guardar ou imprimir um relatório.** Os dois botões no topo da página guardam o relatório do separador aberto (TXT, PDF e, se quiser, JSON, cada um pela janela **Guardar como** do navegador) ou imprimem-no como uma página limpa ([Saídas para outras ferramentas](OUTPUTS.md)).

**Convém saber.** Se usa um plano com repositórios privados, escolha-o em Definições > Básico para ver as suas quotas ([Quotas e planos](QUOTAS_por.md)). A sentinela está explicada em [A sentinela](SENTINEL_por.md). A ferramenta só lê o GitHub; só escreve depois de confirmar.

## Ler com conforto

- **Densidade** (`display.density`, ou `?density=dense` para uma janela): `dense` reduz os espaços e a letra de todos os separadores.
- **Menos movimento** (`display.reduce_motion`): `auto` segue a definição do seu sistema, `on` pára toda a animação e transição. O estado de um workflow escreve-se sempre com palavras e desenha-se também com uma forma, nunca só com cor.
- **Cores para daltonismo** (`display.palette`, ou `?palette=colorblind`): azul, vermelhão, amarelo e um azul mais claro, um conjunto para o modo escuro e outro para o claro. A porta de contraste (`python tools/check_contrast.py`) verifica todos os temas e simula as três formas de daltonismo.
- **Sem saltos enquanto lê** (`display.live_throttle_s`): enquanto o ponteiro ou o foco estão dentro do separador que lê, a atualização periódica espera; uma atualização que pede é aplicada de imediato.
- **Novidades** (`display.whats_new`): após uma atualização, um aviso oferece as entradas do histórico de alterações das versões que saltou; abra-o de novo a partir da paleta. `GET /api/whats-new?since=2.1.5` responde com as entradas (só leitura).
- **Glossário e limites**: abra-o a partir da paleta. `GET /api/glossary` responde com os números escritos com os seus parâmetros reais, os ataques que as regras procuram, os limites da análise e alguns sítios para saber mais. Com `report_export.limits` ligado, os relatórios guardados e impressos terminam com os limites.
- **O filtro do cabeçalho** cobre os separadores Agora, Alertas, Gráficos, os da Sentinela (Sentinela, CI, Colaboração, Segurança, Entrega, Cadeia de fornecimento), Repositórios e Histórico; os restantes (Tendência da Sentinela, Equipa, Frota, Relatórios, Lições, Atualizações e Definições) são sempre globais. Uma nota por baixo do filtro di-lo.
