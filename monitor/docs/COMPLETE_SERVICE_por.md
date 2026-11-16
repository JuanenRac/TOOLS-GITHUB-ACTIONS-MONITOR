<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_SERVICE.md) | [🇪🇸 Español](COMPLETE_SERVICE_spa.md) | [🇫🇷 Français](COMPLETE_SERVICE_fra.md) | [🇮🇹 Italiano](COMPLETE_SERVICE_ita.md) | [🇩🇪 Deutsch](COMPLETE_SERVICE_deu.md) | [🇨🇳 简体中文](COMPLETE_SERVICE_zho.md) | [🇯🇵 日本語](COMPLETE_SERVICE_jpn.md) | **🇵🇹 Português**

# Edição completa como serviço

Para um monitor que funciona sempre num servidor ou num contentor e que outras pessoas ou outros programas leem. É um resumo das escolhas; os pormenores, os comandos e a tabela de variáveis estão em [DEPLOYMENT_por.md](DEPLOYMENT_por.md).

## Como escuta

- De três maneiras: só este computador (predefinição, sem início de sessão), a rede (`listen.network` ativo, `listen.host` e o token de acesso em cada pedido) ou atrás de um proxy (`listen.proxy_public_host`, `listen.secure_cookie` ou `listen.trusted_proxy`).
- Coloque HTTPS (um certificado ou um proxy) ou uma VPN à frente do modo de rede: com HTTP simples o token e as palavras-passe seguem em claro.

## Como executá-lo

- A imagem oficial, o Docker Compose com um proxy opcional ou uma instalação clássica com systemd; todos arrancam `python -m github_actions_monitor.service` sem navegador.
- As portas são 8765 para a edição completa e 8766 para a lite (`ports.complete`, `ports.lite`).

## Vigiá-lo

- `GET /api/health` não chama o GitHub; `GET /api/health?deep=1` responde 503 quando um ciclo de atualização está preso, e `python -m github_actions_monitor.cli.healthcheck` faz essa chamada para um contentor ou um gestor de serviços.
- Quando o GitHub revoga o acesso, substitua a credencial pela linha de comandos, pelo endpoint de administração ou com `SIGHUP`; reiniciar não repara um acesso perdido.

## Durante meses

- Escolha ficheiros ou SQLite e a retenção em [STORAGE_por.md](STORAGE_por.md), faça uma cópia de segurança antes de cada atualização e leia [MIGRATING_por.md](MIGRATING_por.md).
- Com pessoas que iniciam sessão, o modo equipa está descrito em [COMPLETE_TEAM_por.md](COMPLETE_TEAM_por.md); o contrato em que os programas podem confiar está em [API_por.md](API_por.md).
