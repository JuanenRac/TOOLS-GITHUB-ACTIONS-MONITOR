<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COLLAB.md) | [🇪🇸 Español](COLLAB_spa.md) | [🇫🇷 Français](COLLAB_fra.md) | [🇮🇹 Italiano](COLLAB_ita.md) | [🇩🇪 Deutsch](COLLAB_deu.md) | [🇨🇳 简体中文](COLLAB_zho.md) | [🇯🇵 日本語](COLLAB_jpn.md) | **🇵🇹 Português**

# A sentinela Collab: issues e pull requests

Uma segunda sentinela ao lado da de CI. Olha para as **issues e pull requests abertas** dos seus repositórios e diz-lhe o que precisa de uma pessoa: issues esquecidas, etiquetas críticas, revisões que ninguém faz, rascunhos sem fim, conflitos que ficam. Tem um relógio próprio, nunca altera o que a sentinela de CI decide e **nunca escreve no GitHub**. Pertence à edição completa; a edição lite não a carrega.

## Ativá-la

Vem desligada. Definições > Sentinela > Issues e pull requests, ou em `actions_monitor.json`:

```
"sentinels": {"collab": {"enabled": true, "refresh_seconds": 600, "max_repos_per_tick": 10, "repos": "all",
  "rules": {"issue_stale_days": 14, "issue_critical_labels": ["security", "critical"], "pr_review_pending_days": 3,
            "pr_draft_max_days": 30, "pr_conflict_days": 7, "watch_external_comments": false, "ignore_labels": ["monitor:ignore"]}}}
```

`repos` é `"all"`, uma lista de repositórios ou `{"ecosystems": [...]}`.

## As regras (códigos estáveis)

| Código | Nível | Quando |
|---|---|---|
| `collab.issue.stale` | aviso | uma issue aberta sem atividade há `issue_stale_days` |
| `collab.issue.critical` | erro | uma issue aberta com uma etiqueta de `issue_critical_labels`, qualquer que seja a idade |
| `collab.issue.external` | aviso | (só com `watch_external_comments`) uma issue de alguém fora da equipa a que ninguém respondeu passado um dia |
| `collab.pr.review_pending` | aviso | um pull request com revisão pedida à espera há `pr_review_pending_days` |
| `collab.pr.draft_old` | info | um pull request em rascunho aberto há `pr_draft_max_days` |
| `collab.pr.conflict` | aviso | um pull request com conflitos há `pr_conflict_days` |

Os bots ficam de fora. Os valores por omissão são lentos de propósito: um rascunho que espera meses é normal em muitas equipas.

## Quanto custa

Uma ronda lê no máximo `max_repos_per_tick` repositórios, com dois pedidos condicionais cada (um repositório que não mudou não gasta quota) e até seis detalhes de pull request por ronda. Pára enquanto a quota estiver abaixo de `min_rate_remaining`. O estado fica em `collab_state.json` (dentro da pasta da conta quando há várias), por isso um reinício não anuncia nada duas vezes.

## Menos ruído: ignorar e silenciar

- **Etiqueta de ignorar**: ponha no GitHub uma etiqueta de `ignore_labels` (`monitor:ignore` por omissão) na issue ou no pull request e a Collab não gera alerta para ele. O monitor nunca escreve etiquetas.
- **Silêncio no monitor**: no separador Alertas, cada alerta tem botões para silenciar esse alerta, a sua regra ou toda a sentinela durante `alerts.mute_hours` horas (24 por omissão, de 1 a 720). Caduca sozinho, pode repor-se quando quiser e o separador guarda um histórico curto do que foi silenciado e até quando. É uma nota deste monitor; nada muda no GitHub. No modo de rede um silêncio só pode ser feito (e levantado) a partir do computador onde o monitor corre (`this_computer`); um cliente da rede vê os silêncios e não os pode alterar. Continuará assim até uma edição posterior ter utilizadores próprios. O silêncio de um alerta também pode durar «até o item mudar» (`until_change` no pedido de `POST /api/alerts/mute`): termina logo que o `updated_at` da issue ou do pull request muda, ou no fim das horas, o que acontecer primeiro. No separador Alertas é o botão **Até haver alteração**, mostrado nos alertas que trazem o `updated_at` do seu elemento (os da sentinela Collab); o alerta silenciado indica então «silenciado até haver alteração».

## Onde se vê

- O separador **Alertas**: uma lista para todas as sentinelas, filtro por origem (CI, Collab) e por nível, e os silenciados a pedido.
- O separador Sentinela: a camada *Issues e pull requests*.
- `GET /api/alerts?sentinel=collab&level=&muted=show|hide|only` e `GET /api/sentinel/collab`; `GET /api/events?sentinel=collab&since=` para os eventos (`collab_new`, `collab_fixed`, que os canais de notificação também enviam se os escolher; ver NOTIFICATIONS).

## Limites

Só se leem as primeiras 100 issues abertas e os primeiros 100 pull requests abertos de cada repositório, os atualizados mais recentemente primeiro. A Collab não propõe nem executa nada; as ações sobre issues e pull requests são de uma edição posterior.
