<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AUDIT_LOG.md) | [🇪🇸 Español](AUDIT_LOG_spa.md) | [🇫🇷 Français](AUDIT_LOG_fra.md) | [🇮🇹 Italiano](AUDIT_LOG_ita.md) | [🇩🇪 Deutsch](AUDIT_LOG_deu.md) | [🇨🇳 简体中文](AUDIT_LOG_zho.md) | [🇯🇵 日本語](AUDIT_LOG_jpn.md) | **🇵🇹 Português**

# O registo de ações

Só Complete, ligado por predefinição. Ao lado da auditoria dos acessos (inícios de sessão, bloqueios, recusas), o monitor mantém um registo de **ações**: quem mudou o quê, quando e em que conta. Uma alteração das definições, um silêncio ou a sua retirada, uma alteração de utilizadores, palavras-passe, preferências de notificação ou credenciais. É uma linha JSON por ação em `logs/audit_actions.jsonl`, que nunca é reescrito. Regista também o que é confirmado: uma ação no GitHub (reexecutar, cancelar, disparar, integrar), uma execução com `act`, guardar ou apagar o token guardado, uma mudança do modo de trabalho, um grupo acrescentado pela descoberta, uma lição acrescentada, um relatório escrito agora, o acesso da conta e as ações da IA. A linha diz o que foi confirmado e o resultado, nunca o corpo do pedido. Cada rota POST fica registada ou listada como isenta com o seu motivo, e um teste falha quando uma rota nova não é nem uma coisa nem outra.

## O que diz uma linha

`at`, `action` (uma palavra simples como `settings_change` ou `alert_mute`), `user`, `role`, `account`, `target` (um identificador curto: o nome de uma definição, um código de alerta), `result` (`ok`, `denied` ou `error`) e, se ajudar, `details`. **Nunca entra um valor nem um segredo**: uma alteração de definições escreve os nomes das definições, não o que valem; uma chave cujo nome parece um segredo (token, password, key, cookie, authorization, session...) é descartada; todo o texto é limpo como as notas para IAs e cortado a 200 carateres.

## A cadeia

Cada linha leva `prev` (o hash da linha anterior) e `hash` (o hash de si própria e de `prev`). Uma linha alterada, retirada ou metida depois quebra a cadeia, e `GET /api/audit-log` diz onde (`chain.broken_at`). Passado `audit_log.max_mb`, a parte antiga guarda-se como `audit_actions.jsonl.1` e a cadeia continua no ficheiro novo. A cadeia denuncia a manipulação; não pode impedir quem tem acesso ao ficheiro de o apagar todo, por isso guarde uma cópia onde importa. Com várias contas, cada conta guarda o seu próprio ficheiro na sua pasta (`accounts/<id>/audit_actions.jsonl`) e a API só responde com as linhas da conta consultada; as linhas escritas antes desta alteração ficam no antigo ficheiro partilhado. A verificação cobre também o ficheiro rodado e a ligação entre os dois (`segments`, e `segment` quando uma linha está quebrada); `complete: false` significa que a cadeia não começa no seu primeiro elo porque um ficheiro rodado foi substituído por uma rotação posterior ou apagado. Vários processos podem escrever o mesmo ficheiro: cada linha é encadeada à última linha que realmente lá está, sob um bloqueio. A cadeia não tem chave secreta: quem puder escrever o ficheiro pode cortar as suas linhas mais recentes ou reescrevê-lo com novos hashes; se tiver de servir de prova, guarde uma cópia noutro sítio. Com `audit_log.keep_generations` (5 por omissão, de 1 a 20) as partes antigas guardam-se como `.1`, `.2` e assim por diante: a mais recente é `.1`, o que for mais antigo do que esse número de ficheiros é apagado, e `GET /api/audit-log` verifica a cadeia através de todas.

## Quem o lê

Um administrador (e a pessoa no computador quando não há modo equipa). Um mantenedor só quando `audit_log.maintainers_can_read` está ligado; mais ninguém. `GET /api/audit-log` responde as últimas 200 linhas e o estado da cadeia. A edição Lite não tem nada disto. Um viewer é recusado à porta. Desligar o registo escreve a sua própria última linha (a alteração que o desligou). Uma linha que não pode ser escrita é contada: `write_failures` e `last_write_error_at` na resposta, e um aviso de degradação. As alterações falhadas da própria palavra-passe não são escritas aqui (a auditoria dos acessos guarda-as).

## Definições

Definições, separador Sentinela, bloco **Registo de ações**: `audit_log.enabled` (ligado), `audit_log.max_mb` (10) e `audit_log.maintainers_can_read` (desligado). `audit_log.keep_generations` (5) é o número de ficheiros rodados que se guardam. `audit_log.required` (desligado) recusa com um 503 as ações que têm de ficar registadas (as confirmações de ações no GitHub, o modo, os silêncios, as credenciais...) enquanto o registo não puder ser escrito; as definições continuam abertas para o poder corrigir.

Uma cópia feita agora (`POST /api/ops/backup`) e a purga a pedido (`POST /api/ops/purge`, também um ensaio) ficam registadas como `backup_run` e `purge_run`: a linha diz quem a pediu e o resultado, nunca o conteúdo da cópia.

## Pontos de controlo assinados, limpeza e exportação

Com `audit_checkpoints.enabled` a cadeia é assinada com uma chave da instalação, e o registo pode ser limpo e copiado para outro lado: ver [COMPLIANCE_por.md](COMPLIANCE_por.md). Com `retention.legal_hold` o registo não é rodado nem limpo.
