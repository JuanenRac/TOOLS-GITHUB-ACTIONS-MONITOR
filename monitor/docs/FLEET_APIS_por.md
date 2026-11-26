<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](FLEET_APIS.md) | [🇪🇸 Español](FLEET_APIS_spa.md) | [🇫🇷 Français](FLEET_APIS_fra.md) | [🇮🇹 Italiano](FLEET_APIS_ita.md) | [🇩🇪 Deutsch](FLEET_APIS_deu.md) | [🇨🇳 简体中文](FLEET_APIS_zho.md) | [🇯🇵 日本語](FLEET_APIS_jpn.md) | **🇵🇹 Português**

# Frota por papel e grupo, APIs de leitura e sítio de demonstração

## Papéis e grupos

No fim do separador Frota: o pior estado de cada grupo (ecossistema) com ligação ao seu ecrã `/g/<chave>`, e uma coluna por papel de workflow (`fleet.roles`). O que não foi lido é `desconhecido`, nunca bom.

## Desativar

`fleet.disabled` aceita nomes, padrões ou `group:<chave>`; o monitor deixa de os ler no ciclo seguinte, sem reiniciar. Edições Complete e Full.

## APIs de leitura

`GET /api/fleet/columns` `GET /api/fleet/group?slug=` `GET /api/cctray.xml` `GET /api/cctray.json` `GET /api/security/secrets` `GET /api/security/code-scanning`. Todas só de leitura, com os mesmos controlos de acesso; também em `/api/v1/` com a API versionada ativa. `fleet.cctray` serve a fonte CCTray; `fleet.security_api` serve contagens de alertas de segredos e de código por repositório (nunca um segredo), nomeando o que não se pôde ler. Ambas desligadas de fábrica.

## Impressão dos relatórios

Relatórios e briefs da IA trazem `report_digest`: SHA-256 dos factos, da versão do monitor, da versão das regras e do veredito. Mesma impressão, mesmo conteúdo. Não é uma assinatura.

## Sítio de demonstração

Uma cópia estática da demonstração (dados inventados, sem início de sessão, sem ações, sem pedidos para outro lado) e uma verificação de workflows no navegador com Pyodide (nada é enviado):

```
python tools/make_public_demo.py demo-site
```

O workflow *Demo site* guarda-a como artefacto. Publicá-la é uma decisão à parte do dono do repositório; nada a publica sozinho. A verificação no navegador não foi experimentada num sítio publicado.

## Todas as definições

`fleet.disabled` `fleet.roles` `fleet.cctray` `fleet.security_api`
