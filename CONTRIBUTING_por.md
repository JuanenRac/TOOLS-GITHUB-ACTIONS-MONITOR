# Contribuir para o GitHub Actions Monitor

## Pilha tecnológica
- **Linguagem**: Python 3.11 ou superior; o núcleo não precisa de pacotes (a vista de terminal, `bin/tui.py`, usa o Rich, que é opcional; os testes ignoram o que dele depende se faltar).
- **Interface**: uma página web local (`monitor/assets/static/actions_monitor.html`) servida em `127.0.0.1`, mais ferramentas de linha de comandos.
- **Fonte de dados**: o cliente oficial de linha de comandos do GitHub, `gh` (chamadas só de leitura por defeito).

## Orientações
1. **Primeiro os testes**: `python -m unittest discover -s monitor/tests` tem de passar antes de um pull request. Offline: os testes nunca chamam o GitHub. Para experimentar os serviços reais à mão, use `python tools/manual_check_live.py`.
2. **Oito idiomas**: todo o texto que um utilizador lê vive em `monitor/assets/locales/<lang>.json` para en, es, de, fr, it, ja, zh e pt (português europeu). Uma chave nova vai para os oito ficheiros; os testes verificam que têm as mesmas chaves.
3. **Sem segredos**: por defeito o monitor não guarda nenhum token (pede-o ao `gh`); o único token opcional vive apenas no cofre seguro do sistema (`secretstore.py`). Não acrescente código que leia, imprima, registe ou escreva credenciais noutro lado e nunca submeta um `actions_monitor.json` real.
4. **Seguro por defeito**: tudo o que escreve no GitHub, executa um programa, abre uma porta de rede ou envia dados para fora está desligado por defeito, tem o seu próprio interruptor em Definições > Avançado, pede uma confirmação própria e escuta em `127.0.0.1` salvo se o modo rede estiver ligado. Uma função assim traz testes que provam que recusa sem o interruptor, sem a confirmação e sem o token, e que nada vaza para um registo.
5. **Passos pequenos**: uma alteração por pull request, com a linha correspondente em `CHANGELOG.md`.
6. **Imagens**: edite `docs/architecture.json` ou `docs/structure.json` e execute `python tools/make_architecture.py` / `python tools/make_structure.py`; nunca edite o SVG à mão.
7. **Registo de alterações em oito idiomas**: cada nova entrada de `monitor/CHANGELOG.md` recebe a sua tradução em `monitor/docs/CHANGELOG_<spa|deu|fra|ita|jpn|zho|por>.md` (mesmas versões e secções; uma entrada ainda por traduzir mantém o texto em inglês sob um aviso traduzido). `python tools/make_help_index.py --check` e a verificação de lançamento falham se faltar uma versão numa tradução.
8. **Cada versão revê a ajuda inteira**: antes de publicar (no seu pull request de versão) leia TODOS os temas da ajuda - o README do repositório e as suas traduções (Num relance, O que faz, Estado do projeto, Testes, Estrutura do repositório, Documentação, Segurança), cada guia de `monitor/docs/`, os inícios rápidos e os README do pacote - e corrija toda a cifra, versão, comando, caminho, imagem ou lista de funções que tenha ficado velha, nos oito idiomas. Os geradores e os testes da ajuda (`tools/make_glance.py`, `tools/make_help_index.py`, `tools/make_screenshots.py`, `monitor/tests/test_190_help_current.py`) apanham apenas uma parte.

## Atualizar um painel de estado após cada versão

`.github/workflows/dashboard-dispatch.yml` corre quando o workflow `CI` termina a verde em `main` (apenas eventos push). Se o responsável definir o segredo opcional do repositório `ECOSYSTEM_DASHBOARD_DISPATCH_TOKEN`, pede a um repositório de painel que atualize a sua tabela de versões; sem o segredo termina em silêncio, não tem permissões e nunca altera nem atrasa o CI. A versão em `electro-hobby-3d.project.json` tem de ser igual a `tool_version.py` em cada versão; um teste verifica-o.

- Lista de verificação da ajuda: a ajuda das Definições (`cfg.h.<chave>`) de cada nova definição, a ajuda do separador que mudou, os guias em `monitor/docs/`, os oito idiomas, o índice de ajuda (`python tools/make_help_index.py`) e o registo de alterações.

## Verificações do CI que protegem o processo

- **Testes sem rede**: `sh tools/run_offline_tests.sh discover -s monitor/tests` executa toda a suite num espaço de nomes de rede que só tem o loopback. Um teste que precise da internet falha aí.
- **Auditoria de dependências**: `python tools/audit_dependencies.py` executa `pip-audit` sobre os pacotes que o CI instala. Uma supressão em `.github/audit-suppressions.json` precisa de `id`, `reason` e `expires` (no máximo a 180 dias); uma expirada falha, e uma morta também (a vulnerabilidade já não é encontrada).
- **Teste de fumo das fontes externas**: o workflow `sources-smoke.yml` (semanal) executa `tools/smoke_sources.py` contra a página de estado real, os avisos de segurança, a descrição da API REST e a última versão, e falha quando uma mudou de formato.
- **Limites**: `tools/limits_check.py` executa o monitor com uma conta de 120 workflows num contentor de um processador e 512 MB.
- **Ordem da versão**: crie a release do GitHub como RASCUNHO e envie a etiqueta `vX.Y.Z`; `release-image.yml` constrói e publica a imagem e só publica o rascunho quando ela responde pela sua etiqueta nas duas plataformas. A ferramenta que a publica cria a release como RASCUNHO, envia `github_actions_monitor.zip`, `SHA256SUMS` e `monitor_updater.py`, verifica que estão todos e só então publica (as releases imutáveis não aceitam ficheiros depois); com a imagem primeiro, envia a etiqueta e `release-image.yml` publica o rascunho.

## Trabalhar com um assistente de IA

Uma alteração escrita com um assistente de IA segue as mesmas regras, e quem a envia responde por ela: leia cada linha, execute os testes e nunca cole no assistente um token, um registo com nomes privados ou o conteúdo de `actions_monitor.json`. As duas skills que acompanham o monitor (`monitor/skills/external/SKILL.md` para uma ferramenta que fala com um monitor em funcionamento, `monitor/skills/internal/SKILL.md` para a IA integrada) fazem parte do produto: uma definição, rota ou comando novos atualizam-nas (`python tools/make_skill_refs.py`). Para que serve o produto e o que nunca deve fazer está em `PRODUCT_por.md`.

## macOS: a marca de quarentena

Os ficheiros não estão assinados com um certificado da Apple. Um zip transferido com um navegador leva a marca de quarentena e o macOS pode recusar abrir os lançadores `.command`. Verifique primeiro a versão (ver `monitor/docs/UPDATE_por.md`) e depois retire a marca da pasta descompactada. O macOS não é testado de momento.

```sh
xattr -dr com.apple.quarantine /path/to/github_actions_monitor
```
