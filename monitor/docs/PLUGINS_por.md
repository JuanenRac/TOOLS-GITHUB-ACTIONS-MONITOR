<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](PLUGINS.md) | [🇪🇸 Español](PLUGINS_spa.md) | [🇫🇷 Français](PLUGINS_fra.md) | [🇮🇹 Italiano](PLUGINS_ita.md) | [🇩🇪 Deutsch](PLUGINS_deu.md) | [🇨🇳 简体中文](PLUGINS_zho.md) | [🇯🇵 日本語](PLUGINS_jpn.md) | **🇵🇹 Português**

# Plugins e cofres de segredos

Os plugins acrescentam verificações ao monitor sem o alterar. Tudo está desligado por predefinição. A edição Lite não tem plugins.

## Ligar

Ligue `plugins.enabled` e depois o plugin que quiser. Definições > Extensões mostra cada um com as permissões, a chave, o estado e o que fica isolado. O que encontram são alertas da origem `plugin`, com o nome do plugin à frente.

## Plugins oficiais

Vêm dentro da versão assinada e correm dentro do monitor, num fio próprio.

- **discussions** (`plugins.official.discussions.enabled`): discussões sem comentários há mais de `plugins.official.discussions.days` dias. Issues e PR são do Collab.
- **packages** (`plugins.official.packages.enabled`): pacotes container ou npm com mais versões do que `plugins.official.packages.max_versions`. Precisa de `read:packages`. As releases são do sentinela de entrega.

## Plugins de terceiros

Ligue `plugins.third_party.enabled`. Um pacote é um zip com `plugin.json` e uma assinatura separada `NOME.zip.ed25519.sig` feita pelo autor. Só é instalado se assinado por uma chave do **seu** porta-chaves com o âmbito `plugins`, e só depois de repetir a impressão digital dessa chave. Chega desligado. A assinatura é verificada antes de cada execução; uma chave revogada ou um ficheiro alterado pausam o plugin.

**Assinado não quer dizer seguro.** Um manifesto não é uma sandbox.

```
python bin/monitor_cli.py plugin init --path my-plugin
python bin/monitor_cli.py plugin validate --path my-plugin
python bin/monitor_cli.py plugin pack --path my-plugin --out my-plugin.zip
python bin/monitor_cli.py keyring add --key-id author --public-key HEX --key-scope plugins
python bin/monitor_cli.py plugin verify --path my-plugin.zip
python bin/monitor_cli.py plugin install --path my-plugin.zip
python bin/monitor_cli.py plugin install --path my-plugin.zip --fingerprint HEX
python bin/monitor_cli.py plugin enable --name my-plugin
python bin/monitor_cli.py plugin list
python bin/monitor_cli.py plugin audit
python bin/monitor_cli.py plugin uninstall --name my-plugin
```

## O que fica isolado

| Sistema | Processo separado, ambiente vazio, sem token | Sem rede | Memória e processos filhos |
|---|---|---|---|
| Linux | sim | sim se o sistema permitir espaços de nomes de utilizador; senão **sem isolamento de rede** | limites de memória e CPU |
| Windows | sim | **não**: **sem isolamento de rede** | Job Object: limite de memória, sem processos filhos |
| macOS | sim | **não**: **sem isolamento de rede** | limite de CPU; memória não garantida |

Em nenhum sistema os seus ficheiros ficam escondidos de um plugin destes: corre com o seu utilizador. `plugins.worker.platforms_ok` vazio: os de terceiros nunca correm. As leituras do GitHub são pedidas ao monitor, que só permite as `get_paths` do manifesto em repositórios vigiados. `plugins.worker.timeout_s`, `max_output_kb` e `memory_mb` limitam cada execução.

## Saída não fiável e saúde

Os títulos são limpos e cortados (`plugins.alert_title_max`), só ficam ligações para github.com e um plugin de terceiros não pode levantar um alerta crítico. O texto de um plugin é um dado, nunca uma instrução para uma IA. Após `plugins.breaker.failures` falhas seguidas fica em pausa até o retomar; em pausa ou degradado não significa «está tudo bem». A verificação `plugins` do doctor e `plugin audit` indicam pacotes revogados ou alterados.

## Para autores

O contrato é a versão 1 (`api_compat`). `run(ctx)` devolve `{"alerts": [{id, code, level, repo, url, title}]}`; `ctx` oferece `owner`, `now`, `options`, `repos()`, `get(path)`, `discussions()`, cada um com a sua permissão (`repos.list`, `gh.get`, `graphql.discussions`). `init` escreve um modelo com o teste. O monitor nunca assina.

```json
{"name": "example-labels", "version": "1.0.0", "api_compat": "1", "author": "...", "description": "...", "trust": "third_party",
 "entry": "plugin.py", "permissions": ["repos.list", "gh.get"], "get_paths": ["repos/{owner}/{repo}/labels"], "refresh_seconds": 3600}
```

## Rotas e pacotes pip

Rotas (administrador; alterações só a partir deste computador): `/api/plugins/catalog`, `/api/plugins/inspect`, `/api/plugins/install`, `/api/plugins/enable`, `/api/plugins/uninstall`. Com `plugins.entry_points` o monitor lista pacotes instalados com pip que declarem o grupo `gha_monitor.plugins` e tragam um `*.plugin.zip`; o código nunca é importado, instala-se o zip como os outros.

## Ler o token do GitHub a partir de outro programa

`secrets.backend` lê o token em vez de o guardar no monitor (`github_token.enabled` tem de estar ligado). Só leitura. `vault` (HTTP, `secrets.vault.addr`, `path`, `field`, token do Vault na variável indicada por `token_env`; https, ou http só para este computador), `sops` (`secrets.sops.file`, `field`; só num computador de confiança), `bitwarden` (`bws`, `secrets.bitwarden.item`), `aws`, `azure`, `gcp` (as suas ferramentas, `secrets.cloud.ref`). Com `secrets.reload_on_rotate` é relido a cada `secrets.reload_seconds`. Testado com servidores falsos e um Vault em modo de desenvolvimento; nenhuma conta real na nuvem.
