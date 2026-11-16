<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_TEAM.md) | [🇪🇸 Español](COMPLETE_TEAM_spa.md) | [🇫🇷 Français](COMPLETE_TEAM_fra.md) | [🇮🇹 Italiano](COMPLETE_TEAM_ita.md) | [🇩🇪 Deutsch](COMPLETE_TEAM_deu.md) | [🇨🇳 简体中文](COMPLETE_TEAM_zho.md) | [🇯🇵 日本語](COMPLETE_TEAM_jpn.md) | **🇵🇹 Português**

# Edição completa para uma equipa

Várias pessoas leem o mesmo monitor, cada uma com o seu início de sessão e o seu papel. Está desligado por predefinição (`auth.enabled`) e a edição lite nunca o tem. A lista completa de opções está na secção Modo equipa de [ADVANCED_por.md](ADVANCED_por.md).

## Primeiros passos

- Com `auth.enabled` ativo, nada muda até existir o primeiro administrador: crie-o no computador que executa o monitor (a página `/login` ou `python -m github_actions_monitor.security.auth_cli create-admin`). No modo de rede o monitor não arranca sem um.
- Numa rede use HTTPS ou uma VPN: caso contrário o cookie de sessão e as palavras-passe seguiriam em claro.

## Papéis

- `viewer` lê; `maintainer` também altera o modo de trabalho e, só a partir do computador do monitor, silencia e reconhece alertas; `admin` também altera definições e utilizadores.
- Cada utilizador vê apenas as contas que lhe foram atribuídas (um administrador vê todas); outra conta responde 403 `account_scope`.

## Sessões e palavras-passe

- O navegador recebe o cookie `monitor_session` e um token CSRF; um script inicia sessão com `POST /api/auth/login` e, só se `auth.allow_bearer` estiver ativo, envia `Authorization: Bearer`.
- As palavras-passe são guardadas como hash com sal e exigem `auth.min_length` carateres; após `auth.max_failed_logins` falhas o utilizador fica bloqueado `auth.lockout_minutes` minutos.

## Quem fez o quê

- O registo de ações anota quem alterou o quê ([AUDIT_LOG_por.md](AUDIT_LOG_por.md)); um maintainer só o lê se `audit_log.maintainers_can_read` estiver ativo.
- A saúde da equipa e a pontuação por conta estão em [HEALTH_por.md](HEALTH_por.md) e [SCORE_por.md](SCORE_por.md); para um servidor que fica ligado, leia [COMPLETE_SERVICE_por.md](COMPLETE_SERVICE_por.md).
