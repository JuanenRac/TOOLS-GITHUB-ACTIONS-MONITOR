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

Segurança: o monitor nunca lê, copia, imprime nem regista a chave; passa o seu caminho ao `openssl`, que assina um JWT de dez minutos no máximo. O token de instalação dura uma hora, fica em memória e é renovado cinco minutos antes. **Só as leituras** o usam; as escritas e ações mantêm o seu token. Se a App falhar ou lhe faltar uma permissão, a leitura repete-se com o seu token. A página mostra as duas quotas.

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
