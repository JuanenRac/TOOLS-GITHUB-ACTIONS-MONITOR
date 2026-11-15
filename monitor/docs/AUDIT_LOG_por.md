<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AUDIT_LOG.md) | [🇪🇸 Español](AUDIT_LOG_spa.md) | [🇫🇷 Français](AUDIT_LOG_fra.md) | [🇮🇹 Italiano](AUDIT_LOG_ita.md) | [🇩🇪 Deutsch](AUDIT_LOG_deu.md) | [🇨🇳 简体中文](AUDIT_LOG_zho.md) | [🇯🇵 日本語](AUDIT_LOG_jpn.md) | **🇵🇹 Português**

# O registo de ações

Só Complete, ligado por predefinição. Ao lado da auditoria dos acessos (inícios de sessão, bloqueios, recusas), o monitor mantém um registo de **ações**: quem mudou o quê, quando e em que conta. Uma alteração das definições, um silêncio ou a sua retirada, uma alteração de utilizadores, palavras-passe, preferências de notificação ou credenciais. É uma linha JSON por ação em `logs/audit_actions.jsonl`, que nunca é reescrito.

## O que diz uma linha

`at`, `action` (uma palavra simples como `settings_change` ou `alert_mute`), `user`, `role`, `account`, `target` (um identificador curto: o nome de uma definição, um código de alerta), `result` (`ok`, `denied` ou `error`) e, se ajudar, `details`. **Nunca entra um valor nem um segredo**: uma alteração de definições escreve os nomes das definições, não o que valem; uma chave cujo nome parece um segredo (token, password, key, cookie, authorization, session...) é descartada; todo o texto é limpo como as notas para IAs e cortado a 200 carateres.

## A cadeia

Cada linha leva `prev` (o hash da linha anterior) e `hash` (o hash de si própria e de `prev`). Uma linha alterada, retirada ou metida depois quebra a cadeia, e `GET /api/audit-log` diz onde (`chain.broken_at`). Passado `audit_log.max_mb`, a parte antiga guarda-se como `audit_actions.jsonl.1` e a cadeia continua no ficheiro novo. A cadeia denuncia a manipulação; não pode impedir quem tem acesso ao ficheiro de o apagar todo, por isso guarde uma cópia onde importa.

## Quem o lê

Um administrador (e a pessoa no computador quando não há modo equipa). Um mantenedor só quando `audit_log.maintainers_can_read` está ligado; mais ninguém. `GET /api/audit-log` responde as últimas 200 linhas e o estado da cadeia. A edição Lite não tem nada disto.

## Definições

Definições, separador Sentinela, bloco **Registo de ações**: `audit_log.enabled` (ligado), `audit_log.max_mb` (10) e `audit_log.maintainers_can_read` (desligado).
