<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CONSOLE_TOOLS.md) | [🇪🇸 Español](CONSOLE_TOOLS_spa.md) | [🇫🇷 Français](CONSOLE_TOOLS_fra.md) | [🇮🇹 Italiano](CONSOLE_TOOLS_ita.md) | [🇩🇪 Deutsch](CONSOLE_TOOLS_deu.md) | [🇨🇳 简体中文](CONSOLE_TOOLS_zho.md) | [🇯🇵 日本語](CONSOLE_TOOLS_jpn.md) | **🇵🇹 Português**

# Ferramentas de consola: linter de workflows e vista de consola

Duas ferramentas de linha de comandos, opcionais. O monitor em si não precisa de nenhum pacote; a vista de consola usa o Rich quando a pede.

## O linter de workflows: `lint_workflows.py`

- `py -3 lint_workflows.py [CAMINHO ...] [--json] [--fail-on info|warn|bad]` verifica `.github/workflows/*.yml` antes do push. Sem caminho olha para a pasta atual. Só abre ficheiros.
- Regras (cada uma pode ser desligada e ter outra gravidade no separador Definições, subseparador Linter de workflows): `unpinned_uses` (uma ação não fixada a um SHA de commit completo), `permissions` (sem bloco `permissions:`, ou `write-all`), `secrets_in_clear` (o que parece um token ou chave escrito no ficheiro), `injection` (texto de terceiros colado num script `run:`) e `pr_target` (`pull_request_target` com obtenção do código do pull request).
- O código de saída é 1 quando uma deteção atinge `--fail-on` (predefinição `bad`), por isso serve de hook antes do push. Quando o monitor vê os seus clones, acrescenta também uma linha ao relatório diário.
- Um valor que parece um segredo é classificado sem nunca ser impresso nem guardado: um formato de token conhecido ou uma cadeia longa de alta entropia é grave (`bad`), um enchimento legível como `placeholder`, `dummy`, `changeme` ou `ci` é só informação, todo o resto é um aviso, e `${{ secrets.X }}`, `${X}` ou um valor vazio não é deteção. Para silenciar uma deteção escreva um comentário na sua linha ou na anterior: `# monitor-lint: ignore secrets_in_clear porque é um enchimento para docker compose config` (um nome de regra ou `all`); ou liste padrões `repositório:ficheiro:regra`, com `*`, na definição `lint.ignore`.


## A vista de consola: `tui.py`

- `pip install rich` e depois `py -3 tui.py [--port 8765] [--refresh 5] [--once] [--theme dark|light]`. Desenha uma grelha em direto com o que está a correr, os workflows vermelhos, a fila de assinatura e o relatório, lidos do monitor em execução em `127.0.0.1` (não gasta quota do GitHub).
- É só de leitura: nenhuma tecla volta a executar, fecha ou escreve nada. Sem o Rich diz como o instalar e sai com o código 3; o monitor e os seus testes nunca precisam do Rich.
- A aplicação interativa de terminal `tui_textual.py` (`pip install textual`; acrescente `--lite` para a edição lite) edita no separador Definições as definições simples dos grupos que lista, as **listas** (itens separados por vírgulas: `a, b, c`) e os **mapas de números** (`name=3, other=5`); o servidor volta a verificar cada valor, e as opções de segurança só se alteram na página.
