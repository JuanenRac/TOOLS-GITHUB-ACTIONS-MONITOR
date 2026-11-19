<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](QUOTA.md) | [🇪🇸 Español](QUOTA_spa.md) | [🇫🇷 Français](QUOTA_fra.md) | [🇮🇹 Italiano](QUOTA_ita.md) | [🇩🇪 Deutsch](QUOTA_deu.md) | [🇨🇳 简体中文](QUOTA_zho.md) | [🇯🇵 日本語](QUOTA_jpn.md) | **🇵🇹 Português**

# Mais quota, menos gasto

O GitHub dá a cada conta uma **quota limitada de chamadas à API**, partilhada por todas as ferramentas que a usam. Este guia explica como funciona e todas as vias que o monitor tem para gastar menos.

## Como funciona a quota
- **REST**: 5000 chamadas por hora por utilizador (60 sem sessão). O **GraphQL** tem a sua, à parte. O `GITHUB_TOKEN` de um workflow no Actions também tem a sua. Uma **GitHub App** tem uma quota própria, separada da sua, que cresce com os repositórios em que está instalada (cerca de 10 000 por hora com 130 repositórios).
- O que conta e o que não conta: uma leitura condicional que responde `304 Not Modified` (ETag) não conta; pedir `rate_limit` é grátis; `git push`, `git fetch` e `git clone` não usam a API.

## As vias com que o monitor poupa
1. **Leituras condicionais** (ETag e `304`): `cache.etag.enabled` (ativado por defeito); a página mostra quantas leituras foram poupadas.
2. **Modo poupança**: só os repositórios quentes de 4 em 4 minutos, os restantes de 30 em 30; `modes.auto_low` (ativado) entra abaixo de 1000 chamadas e volta acima de 2500 ou na renovação; predefinições em `modes.low`. A barra diz que os números podem ser antigos, e quão antigos.
3. **Painel central como base**: `central.source` (`off`, `git`, `http`) lê `data/sentinel.json` do seu repositório de perfil, atualizado por um workflow com o seu próprio token; não gasta nada da sua quota. `central.max_age_minutes` (120): mais antigo do que isso está "atrasado" e não é considerado fiável.
4. **Um só aviso quando a quota se esgota**: as leituras param até à renovação, a página diz uma vez "quota esgotada até às HH:MM" (não um erro por repositório) e retoma sozinha.
5. **Uma GitHub App para as leituras** (`github_app.*`), abaixo.
6. **GraphQL para os repositórios sossegados (opcional, desativado por predefinição)**: `network.graphql_checks` lê os repositórios que não estão quentes em lotes (`network.graphql_batch`, 20 por predefinição) através do GraphQL, que tem uma quota própria; uma chamada substitui muitas chamadas REST. Só vê o último commit do ramo predefinido (um workflow que não correu nele não aparece) e não dá durações, tentativas nem outros ramos; por isso os repositórios quentes e qualquer um a que o GraphQL não responda continuam a ser lidos por REST no mesmo ciclo. A contabilidade (lotes, repositórios, pontos, repositórios que passaram para REST) está no resumo e no estado para as ferramentas de IA.

## Uma GitHub App, passo a passo
1. No GitHub, *Settings*, *Developer settings*, *GitHub Apps*, *New GitHub App*. Sem webhook. Permissões **só de leitura**: Actions, Checks, Code scanning alerts, Commit statuses, Contents, Dependabot alerts, Issues, Pull requests, Secret scanning alerts e Metadata.
2. *Generate a private key* e guarde o `.pem` **fora de qualquer repositório**, legível só por si.
3. *Install App* na sua conta, em todos os repositórios a vigiar.
4. No monitor: `github_app.enabled` ativado, `github_app.app_id` (o número da App) e `github_app.key_path` (só o CAMINHO da chave). `github_app.installation_id` pode ficar vazio.
5. Verifique com `GET /api/github-app/status` (só deste computador): mostra o nome, a instalação, as permissões concedidas e a quota da App, nunca a chave nem um token. O doctor verifica o `openssl`, o ficheiro da chave e as suas permissões.

Segurança: o monitor lê a chave em memória só para assinar um JWT de dez minutos no máximo (com a biblioteca padrão, sem precisar do `openssl`; o `openssl` é só o recurso) e nunca a copia, imprime nem regista. O token de instalação dura uma hora, fica em memória e é renovado cinco minutos antes. **Só as leituras** o usam; as escritas e ações mantêm o seu token. Se a App falhar ou lhe faltar uma permissão, a leitura repete-se com o seu token. A página mostra as duas quotas.

## Quando várias ferramentas partilham a mesma quota
Todas as ferramentas da conta gastam as mesmas 5000 chamadas por hora. Um bom padrão: um pequeno invólucro do `gh` com uma **cache partilhada** de uns minutos, uma **reserva** (recusa chamar quando restam menos de cerca de 1000, exceto para o urgente), o trabalho que precisa de dados frescos **logo a seguir à renovação**, e nunca `gh run watch` (consulta sem parar). Por exemplo, um invólucro que guarda a resposta de cada leitura num ficheiro temporário com o nome do comando e a volta a servir durante 120 segundos, e verifica `gh api rate_limit` antes de qualquer outra chamada.

## O que NÃO fazer
Não use várias contas nem vários tokens do mesmo utilizador para contornar o limite: é contra as regras do GitHub e pode levar ao bloqueio da conta. Use uma App, o painel central e o modo poupança.

## Definições
| Definição | Defeito |
|---|---|
| `cache.etag.enabled` | ativado |
| `modes.auto_low` / `modes.auto_low_enter` / `modes.auto_low_exit` | ativado / 1000 / 2500 |
| `modes.low.*` (`refresh_seconds`, `cold_refresh_seconds`, `runs_per_repo`, `hot_hours`) | 240 / 1800 / 10 / 2 |
| `min_rate_remaining` | 800 |
| `central.source` / `central.max_age_minutes` | off / 120 |
| `github_app.enabled` / `github_app.app_id` / `github_app.key_path` / `github_app.installation_id` | off / vazio / vazio / vazio |

## Resolução de problemas e FAQ
- *"quota esgotada até às HH:MM"*: espere; o monitor retoma sozinho. Outras ferramentas podem estar a gastá-la: veja as delas.
- *Os números são antigos*: o modo poupança está ativo (escolhido ou automático); a barra di-lo.
- *A App não funciona*: veja `/api/github-app/status` e o doctor: openssl, o caminho da chave, as permissões.
- *O `git fetch` custa quota?* Não. Ver também [QUOTAS_por.md](QUOTAS_por.md) (planos e minutos) e [MODES_por.md](MODES_por.md).

## O separador Quota e uma segunda conta
Tudo o que diz respeito à quota está num só sítio: *Definições*, separador *Quota*. Reúne os modos (`modes.auto_low`, `modes.auto_low_enter`, `modes.auto_low_exit` e os valores da poupança em `modes.low.*`), a poupança (`network.etag`, em conjunto com `cache.etag.enabled`), o painel central (`central.source`, `central.max_age_minutes`), a GitHub App (`github_app.*`) e uma **segunda conta para as leituras**. Os botões do separador mostram a quota de cada fonte (a sua sessão, a App, a segunda conta) com a hora de renovação, testam a App e a segunda conta, listam as permissões que faltam à App e aplicam os valores recomendados ou os predefinidos.

A segunda conta (`extra_reader.enabled`, `extra_reader.file`) é uma conta só de leitura cujo token de acesso fino está num ficheiro de texto fora de qualquer repositório, legível apenas por si; a definição guarda SÓ o caminho desse ficheiro. O monitor lê o token no momento de usar, guarda-o em memória e nunca o armazena, imprime nem regista. As leituras repartem-se entre a sua sessão, a App e a segunda conta conforme as chamadas que restam a cada uma (o valor da chamada gratuita `rate_limit`, menos as leituras feitas desde então); uma fonte recusada fica de fora cinco minutos e a leitura repete-se com a seguinte. As escritas e ações nunca a usam. É para uma conta sua (por exemplo uma segunda conta própria com acesso de leitura aos repositórios), não uma forma de contornar o limite com contas de outras pessoas. O ficheiro tem de estar dentro da pasta de contas do monitor (`accounts/`, ou a pasta indicada por `MONITOR_ACCOUNTS_DIR`) e nunca é lido através de uma ligação; `extra_reader.any_folder` (desligado por defeito) levanta a regra da pasta. O que depende de quem pergunta (a sua conta, as suas organizações, as notificações, uma pesquisa de `@me`, `gh auth`, `gh repo list` sem proprietário) é sempre respondido pelo seu próprio login, e só uma leitura simples `gh api ENDPOINT` (com, no máximo, as opções `--jq`, `--paginate`, `-H`, `-i` e `--cache`) é repartida pelas fontes: qualquer outra chamada vai para o seu login.

## O programa openssl e um monitor por porta

O monitor procura `openssl` no PATH e, se não estiver lá, onde o Git for Windows o guarda (`Git\usr\bin`, `Git\mingw64\bin` em Program Files e nos Programas do utilizador) e nas pastas habituais do macOS e do Linux, de modo que um monitor iniciado a partir de um `.bat` ou de um serviço o encontra. `github_app.openssl_path` (caminho absoluto do programa) escolhe um à mão. `/api/github-app/status` mostra `openssl` e `openssl_path`, e o doctor diz qual assina quando não é o do PATH.

No Windows a porta do monitor é aberta em exclusivo (SO_EXCLUSIVEADDRUSE): dois processos já não podem escutar no 8765 ao mesmo tempo. E um monitor que arranca enquanto outro monitor já responde na sua porta di-lo e para, em vez de procurar outra porta.

## Repartição da quota: fonte preferida e reserva

Por predefinição cada leitura vai para a fonte (utilizador, GitHub App, segunda conta) com mais chamadas livres. O bloco `readpool` altera isso, no separador Quota das definições, com os valores prudentes de sempre (`auto`, reserva 0):

- `readpool.prefer.<tipo>` (`auto`, `user`, `app`, `extra`): a fonte que responde primeiro a um TIPO de leitura. Os tipos resultam da própria chamada: `runs` (execuções, workflows, verificações), `security` (code scanning, Dependabot, secret scanning), `issues` (issues e pull requests), `history` (versões, commits, etiquetas, conteúdo), `discovery` (organizações, pesquisa, listas de repositórios) e `other`. Se a fonte preferida falhar ou estiver abaixo da sua reserva, respondem as outras, o utilizador por último.
- `readpool.reserve.<fonte>` (0 a 4000): chamadas deixadas livres nessa fonte. Enquanto uma fonte tiver no máximo as chamadas da sua reserva, o monitor não lê com ela se outra puder. Use `readpool.reserve.user` para deixar chamadas ao `gh` das suas ferramentas e agentes.

As escritas e ações usam sempre o token do utilizador. A barra de quota e os modos de trabalho (rápido e turbo) contam a SOMA de todas as fontes: o mosaico mostra a soma e a sua dica o valor de cada fonte, e o separador Quota (Estado) acrescenta uma linha com o total junto à quota do utilizador, da App e da segunda conta.

## Ler menos: o webhook primeiro e as fontes gratuitas

As duas vias estão **desligadas por predefinição** e só afetam repositórios tranquilos (aqueles cujas últimas execuções terminaram e estão a verde). Um repositório em execução, a vermelho ou tocado por um evento é lido como sempre.

- `savings.webhook_first`: enquanto o webhook de entrada está vivo (entregou um evento nos últimos `savings.webhook_window_minutes` minutos), um repositório tranquilo não é lido no seu turno lento: o GitHub avisa quando algo acontece. Ainda assim é lido por inteiro a cada `savings.webhook_full_minutes` minutos. Sem um webhook vivo nada muda.
- `savings.webhook_live_per_repo`: faz de «vivo» assunto de cada repositório. Só um repositório sossegado cujos eventos PRÓPRIOS chegaram nos últimos `savings.webhook_window_minutes` minutos dispensa a leitura lenta; um cujo webhook nunca foi configurado, ou avariou, é lido como sempre enquanto os outros são poupados. Poupa menos leituras, e o painel do Webhook conta os repositórios que estão vivos por si. Desligado por omissão; funciona em conjunto com `savings.webhook_first`.
- `savings.feeds.enabled`: antes de ler com a API um repositório tranquilo, pergunta-se o último commit do seu ramo predefinido a uma fonte que não gasta quota - o feed Atom público dos commits, `git ls-remote`, ou qualquer um dos dois (`savings.feeds.method`: `atom`, `git`, `auto`). Se for o commit da última leitura completa, o repositório fica como está. A cada `savings.feeds.max_age_minutes` minutos é lido por inteiro de qualquer forma. Só repositórios públicos: com um privado, um erro ou uma resposta estranha, o repositório é lido com a API como sempre. Só saem do computador pedidos GET para github.com, nunca uma palavra-passe, e não se escreve nada. Não se usa se o monitor estiver isolado da rede (air-gapped).

O que custa: uma execução que começa sem um push (uma programação, uma repetição) num repositório tranquilo vê-se na leitura completa seguinte, não de imediato. O separador Quota (Estado) mostra as leituras que cada via poupou desde que o monitor arrancou (cerca de uma chamada da API cada): leituras condicionais, GraphQL, webhook primeiro, feed Atom, git e painel central.

## Contas grandes: o que cobre a lista de execuções, e um orçamento

Um repositório que lança centenas de execuções por hora enche em minutos uma lista de 20-100 execuções, pelo que uma falha mais antiga ou um workflow que corre pouco simplesmente não está nela. O monitor di-lo em vez de parecer verde:

- **Cobertura**: a tabela de repositórios mostra até onde recua cada lista. Uma lista cheia que recua menos de `sampling.min_coverage_minutes` é marcada como *cobertura baixa*; uma lista mais curta do que o pedido é *completa* (tem todo o histórico); um total de 2500 ou 40 000 é onde o GitHub deixa de contar, por isso mostra-se como *pelo menos*. O bloco `sampling` de `GET /api/data` traz os mesmos números.
- **Segunda vista**: com `sampling.default_branch_probe` ativada, uma lista cheia pede também os push para o ramo predefinido (sem pull requests), mais um pedido por leitura, para que as execuções que decidem o vermelho em main não sejam empurradas para fora por pull requests e agendamentos.
- **A2 de uma vez**: a um repositório com `sentinel.a2_resolve_batch_min` ou mais workflows por consultar pedem-se uma só vez as execuções concluídas mais recentes do ramo predefinido (no máximo `sentinel.a2_resolve_batch_pages` páginas de 100) e resolvem-se juntos; o que essa lista não mostra pergunta-se um a um. Com 100 ou mais workflows demora poucos ciclos em vez de quatro workflows por ciclo.
- **Orçamento**: `sampling.api_budget_per_hour` (0 = nenhum) limita os pedidos de listas de execuções numa hora. Ao ultrapassá-lo, lêem-se primeiro os repositórios com um workflow vermelho, reserva-se sempre uma décima parte do orçamento para eles e os restantes esperam; a página diz quantos. A estimativa de pedidos por hora para o número de repositórios e os intervalos mostra-se a partir de 3500 (o GitHub permite 5000 por hora) ou sempre que haja orçamento.

As predefinições não mudam nada numa conta com poucos repositórios: a segunda vista e o orçamento estão desativados, e a marca de cobertura baixa só aparece quando uma lista cheia recua menos de meia hora.

## Quando a App está ligada e não é usada

Se `github_app.enabled` está ligado mas a App não consegue dar um token, as leituras continuam com o seu token e a quota é a menor, a do utilizador. Nunca é em silêncio: o doctor fica âmbar com a causa, uma falha é anotada uma vez na lista de falhas engolidas e o separador Quota mostra uma linha `GitHub App` com a causa e o limite em uso. As causas: a chave não se consegue ler ou não é uma chave RSA sem frase-passe (`key_unreadable`), a chave não conseguiu assinar (`sign_failed`), a App não está instalada na conta (`app_not_installed`), o GitHub recusou o token (`token_refused`) e a App está ligada sem o seu número ou o ficheiro da chave (`not_configured`). A mesma nota está em `GET /api/quota` como `app` e em `GET /api/github-app/status` como `signer` e `code`.
