<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ORGANIZATIONS.md) | [🇪🇸 Español](ORGANIZATIONS_spa.md) | [🇫🇷 Français](ORGANIZATIONS_fra.md) | [🇮🇹 Italiano](ORGANIZATIONS_ita.md) | [🇩🇪 Deutsch](ORGANIZATIONS_deu.md) | [🇨🇳 简体中文](ORGANIZATIONS_zho.md) | [🇯🇵 日本語](ORGANIZATIONS_jpn.md) | **🇵🇹 Português**

# Organizações e contas grandes

Como apontar o monitor a uma organização, ou a uma conta pessoal com centenas de repositórios, e o que fazer quando uma leitura volta vazia.

## 1. O token mais pequeno que funciona

O monitor só lê. Use o início de sessão do `gh` (`gh auth login`) ou um token em `GH_TOKEN`, e dê-lhe o mínimo de que precisa.

| Tipo de token | O que lhe dar |
|---|---|
| **Clássico** (token de acesso pessoal) | `repo` para repositórios privados (`public_repo` chega se tudo for público) e `read:org` para listar os repositórios e equipas de uma organização. Opcionais: `security_events` (alertas de code scanning, painel A3), `read:project` (os quadros de Projects, painel A9). Não precisa de `workflow` nem de qualquer âmbito de escrita. |
| **De granularidade fina** | Um só *proprietário do recurso*: crie um token por organização (ou por conta pessoal). Acesso aos repositórios: todos, ou os selecionados. Permissões só de leitura: Metadata, Actions, Contents, Pull requests, Issues, Administration (rulesets e regras de ramo), Code scanning alerts, Dependabot alerts, Secret scanning alerts. Uma organização pode exigir que um proprietário aprove primeiro o token. |
| **GitHub App** | Lê com a quota da App em vez da sua (ver `QUOTA.md`). |

Uma **conta pessoal** (`github_owner` é um utilizador) não precisa de mais do que o acima para os seus próprios repositórios. Os repositórios de uma organização a que pertence leem-se com um token cujo proprietário do recurso (granularidade fina) ou âmbitos (clássico) incluam essa organização.

## 2. Início de sessão único (SSO) e repositórios privados

Se a organização impõe o SSO SAML, um token clássico tem de estar autorizado para ela: no GitHub abra *Settings > Developer settings > Personal access tokens*, escolha o token e carregue em *Configure SSO > Authorize*. Um início de sessão feito com `gh auth login` fica autorizado no navegador quando aceita a organização. Até lá o GitHub responde `403` (*Resource protected by organization SAML enforcement*) ou, pior, responde `200` deixando de fora os repositórios privados (o cabeçalho `X-GitHub-SSO: partial-results`), o que parece uma organização com poucos repositórios.

Um token que não vê um repositório privado recebe `404`, exatamente como se não existisse. Assim, uma resposta vazia pode significar: SSO não autorizado, falta um âmbito ou permissão, um repositório privado que o acesso não vê, ou não haver Actions. A secção seguinte distingue-os.

## 3. O `--doctor` explica

`py -3 bin/actions_monitor.py --doctor` (também `bin/monitor_cli.py doctor`) faz três leituras pequenas e reporta duas linhas:

- **O acesso consegue ler a conta ou a organização** (`access`): `ok` com o utilizador e os seus âmbitos; ou `warn` com a causa no detalhe: `sso` (não autorizado, ou repositórios privados escondidos), `rate_limited`, `scope` (falta uma permissão), `not_found` (a conta não existe ou não é visível), `forbidden`; `fail` quando o GitHub recusa as credenciais. Um token de granularidade fina não tem âmbitos para listar e a linha di-lo.
- **As leituras por hora cabem na quota** (`estimate`): os repositórios da conta e as leituras por hora que as definições atuais exigiriam, face às 5000 por hora de um token pessoal. É uma estimativa sem chamadas: o sondeamento dos runs (um décimo dos repositórios quentes, a cada `refresh_seconds`; os restantes a cada `cold_refresh_seconds`), a Sentinela (no máximo `sentinel.budget_per_hour`) e, quando os ficheiros de workflow são lidos sem clones, a sua parte. `warn` acima de 60 %. Para a baixar: aumente `cold_refresh_seconds`, ative o modo Low, vigie menos repositórios (`repos`) ou leia com uma GitHub App.

As mesmas causas são escritas, com o repositório, em todo o lado onde o monitor não conseguiu ler ficheiros de workflow: o painel A13 da Sentinela lista-os como *não avaliáveis* com o motivo, nunca como um "sem dados" mudo.

## 4. Vigiar uma conta que não é sua (observador sem permissões)

Qualquer token pode ler os repositórios públicos de qualquer conta, por isso pode vigiar uma organização de código aberto com um token sem qualquer âmbito. O que um observador não obtém, e o monitor trata como *desconhecido* e nunca como *bem*: rulesets e proteção de ramos, alertas do Dependabot, code scanning e secret scanning, definições, e as listas de runs de repositórios com Actions desativadas. Os painéis que dependem disso (A3, partes de A6) ficam vazios ou marcados como não avaliáveis para esses repositórios. Nunca se escreve nada, por isso não é preciso nenhuma permissão de escrita.

## 5. Limites conhecidos

- A quota é de 5000 leituras por hora para um token pessoal; uma GitHub App instalada numa organização grande tem mais (ver `QUOTA.md`). A estimativa acima é a forma mais rápida de saber se cabe.
- O monitor lê uma amostra dos últimos runs de cada repositório. Um repositório que lança centenas de runs por hora é visto através dessa amostra, não run a run.
- O GitHub conserva os registos e artefactos de um run durante 90 dias por predefinição; o monitor não consegue ler o que o GitHub apagou.
- Um token de granularidade fina pertence a um só proprietário: vigiar duas organizações exige dois tokens (duas contas do monitor, ver `ACCOUNTS.md`).
- As organizações que exigem aprovação dos tokens, ou bloqueiam os clássicos, precisam que um proprietário atue primeiro; nenhuma definição do monitor consegue contornar isso.
