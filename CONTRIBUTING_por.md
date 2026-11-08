# Contribuir para o GitHub Actions Monitor

## Pilha tecnológica
- **Linguagem**: Python 3.11 ou superior; o núcleo não precisa de pacotes (a vista de terminal, `tui.py`, usa o Rich, que é opcional; os testes ignoram o que dele depende se faltar).
- **Interface**: uma página web local (`monitor/actions_monitor.html`) servida em `127.0.0.1`, mais ferramentas de linha de comandos.
- **Fonte de dados**: o cliente oficial de linha de comandos do GitHub, `gh` (chamadas só de leitura por defeito).

## Orientações
1. **Primeiro os testes**: `python -m unittest discover -s monitor/tests` tem de passar antes de um pull request. Offline: os testes nunca chamam o GitHub. Para experimentar os serviços reais à mão, use `python tools/manual_check_live.py`.
2. **Oito idiomas**: todo o texto que um utilizador lê vive em `monitor/locales/<lang>.json` para en, es, de, fr, it, ja, zh e pt (português europeu). Uma chave nova vai para os oito ficheiros; os testes verificam que têm as mesmas chaves.
3. **Sem segredos**: por defeito o monitor não guarda nenhum token (pede-o ao `gh`); o único token opcional vive apenas no cofre seguro do sistema (`secretstore.py`). Não acrescente código que leia, imprima, registe ou escreva credenciais noutro lado e nunca submeta um `actions_monitor.json` real.
4. **Seguro por defeito**: tudo o que escreve no GitHub, executa um programa, abre uma porta de rede ou envia dados para fora está desligado por defeito, tem o seu próprio interruptor em Definições > Avançado, pede uma confirmação própria e escuta em `127.0.0.1` salvo se o modo rede estiver ligado. Uma função assim traz testes que provam que recusa sem o interruptor, sem a confirmação e sem o token, e que nada vaza para um registo.
5. **Passos pequenos**: uma alteração por pull request, com a linha correspondente em `CHANGELOG.md`.
6. **Imagens**: edite `docs/architecture.json` ou `docs/structure.json` e execute `python tools/make_architecture.py` / `python tools/make_structure.py`; nunca edite o SVG à mão.

## Atualizar um painel de estado após cada versão

`.github/workflows/dashboard-dispatch.yml` corre quando o workflow `CI` termina a verde em `main` (apenas eventos push). Se o responsável definir o segredo opcional do repositório `ECOSYSTEM_DASHBOARD_DISPATCH_TOKEN`, pede a um repositório de painel que atualize a sua tabela de versões; sem o segredo termina em silêncio, não tem permissões e nunca altera nem atrasa o CI. A versão em `electro-hobby-3d.project.json` tem de ser igual a `tool_version.py` em cada versão; um teste verifica-o.
