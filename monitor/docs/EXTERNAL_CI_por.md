<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](EXTERNAL_CI.md) | [🇪🇸 Español](EXTERNAL_CI_spa.md) | [🇫🇷 Français](EXTERNAL_CI_fra.md) | [🇮🇹 Italiano](EXTERNAL_CI_ita.md) | [🇩🇪 Deutsch](EXTERNAL_CI_deu.md) | [🇨🇳 简体中文](EXTERNAL_CI_zho.md) | [🇯🇵 日本語](EXTERNAL_CI_jpn.md) | **🇵🇹 Português**

# Fontes de CI externas (só de leitura)

Um repositório espelhado no GitHub pode ser compilado noutro sítio. O monitor lê Buildbot, GitLab CI, Jenkins e Azure Pipelines e mostra as suas falhas como as do Actions. Apenas lê (GET); nunca inicia, cancela nem escreve nada lá. Edições Complete e Full; desligado por predefinição.

## Configuração

Ligue `external_ci.enabled` e escreva uma linha por fonte em `external_ci.sources` (Definições > CI externa). `repo` é o nome com que o resultado é mostrado.

```
buildbot;repo=my-mirror;url=https://buildbot.example.org;builders=linux+docs
gitlab;repo=my-mirror;url=https://gitlab.example.org;project=group/app;token_env=MY_GITLAB_VALUE
jenkins;repo=my-mirror;url=https://jenkins.example.org;job=folder/app;branch=main
azure;repo=my-mirror;url=https://dev.azure.com/my-org;project=my-project
```

## Vermelho, correto ou degradado

Decide a última build concluída de cada builder, pipeline ou job no seu ramo, como no Actions: pedidos de integração e estados cancelados, ignorados ou desconhecidos nunca decidem. Um serviço que não responde, responde outra coisa ou não tem um builder fica **degradado**, nunca vermelho; as falhas já vistas mantêm-se, marcadas como antigas. As falhas geram ci.external.red (nível `external_ci.alert.level`), contadas, notificadas e silenciadas como um vermelho do Actions; ci.external.degraded é informativo. Silenciá-las nunca silencia um alerta de segurança. Cada fonte é lida no máximo a cada `external_ci.refresh_seconds` (300 ou mais) e menos vezes após `external_ci.breaker.failures` falhas.

## Segurança

O endereço é verificado na ligação: este computador, redes privadas e metadados da nuvem são recusados salvo com `external_ci.allow_private_targets`. Não se seguem redirecionamentos nem ligações das respostas. As respostas são limitadas por `external_ci.max_bytes` e `external_ci.timeout_s`. Nenhuma credencial é escrita na configuração: `token_env` contém apenas o NOME de uma variável de ambiente (GitLab: token de leitura; Jenkins: `utilizador:token`; Azure: token pessoal com leitura de Build) e não é enviada sem TLS para um endereço público. Não consome a quota do GitHub. Em modo sem ligação (`airgapped`) nada é lido; `doctor --egress` lista os anfitriões. `token_env` não pode indicar uma variável do sistema ou do seu início de sessão no GitHub, um segredo do monitor nem uma variável indicada por outra definição.

## Registos de uma build falhada

Desligado por predefinição (`external_ci.logs.enabled`). Só é pedido o fim, limitado por `external_ci.logs.max_kb` e `external_ci.logs.tail_lines`, sem sequências de terminal nem caracteres de controlo, expurgado, mantido em memória durante `external_ci.logs.keep_hours`. É texto não fiável e nunca é dado a uma IA como instrução. A expurgação não reconhece todos os segredos.

## Teste, estado, linha de comandos

Em Definições > CI externa há **Testar ligação**: uma leitura sem guardar nada (`POST /api/external-ci/probe`). O separador de CI das sentinelas mostra cada fonte; `GET /api/external-ci/status` dá o mesmo e `GET /api/external-ci/log` um registo. Comandos: `external-ci list`, `external-ci status` (código 1 se houver vermelho ou degradado) e `external-ci probe --source "LINHA"`.

## Ainda não verificado

Os quatro adaptadores só foram testados com servidores simulados (`tools/extci_fake_servers.py`). Jenkins e Azure Pipelines têm a etiqueta **experimental** (`external_ci.experimental`) e precisam de `external_ci.jenkins.enabled` / `external_ci.azure.enabled`. Para outro adaptador: uma função `(reader, source, cfg) -> (runs, missing)` em `integrations/external_ci/extci_adapters.py` que leia apenas através de `reader`.

## Identidade de um repositório, vários proprietários

Dentro do monitor um repositório é (fonte, proprietário, nome), escrito `repo_key` (`github:proprietário/nome`, `gitlab@servidor:grupo/nome`); as rotas continuam a nomeá-lo pelo nome. Dois repositórios com o mesmo nome em dois sítios não partilham identificadores, execuções nem alertas: quando dois servidores do mesmo tipo espelham o mesmo nome, o servidor é acrescentado à etiqueta. O monitor regista a que proprietário pertencem os dados guardados. Se o proprietário mudar, os silenciamentos e o registo de alertas dos repositórios e o último estado do canal de eventos são postos de parte (conservados, não apagados), depois de copiar cada ficheiro para `identity_backup/`. Acontece depois de um ciclo; `identity plan` mostra-o sem alterar nada, `identity apply` fá-lo já e `identity status` mostra o registo. `sources.multi_owner` (desligado) permite registar contas de proprietários diferentes; as instalações que já têm vários continuam a funcionar e o doctor assinala-o. O `doctor` lê ainda cada fonte externa uma vez.

Linha de comandos: `identity status`, `identity plan`, `identity apply`.
