<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SETTINGS.md) | [🇪🇸 Español](SETTINGS_spa.md) | [🇫🇷 Français](SETTINGS_fra.md) | [🇮🇹 Italiano](SETTINGS_ita.md) | [🇩🇪 Deutsch](SETTINGS_deu.md) | [🇨🇳 简体中文](SETTINGS_zho.md) | [🇯🇵 日本語](SETTINGS_jpn.md) | **🇵🇹 Português**

# O separador Definições

O separador Definições (o ícone da roda dentada no cabeçalho ou na barra de separadores) altera, a partir da página, os valores de `actions_monitor.json`, para que ninguém tenha de editar o ficheiro à mão.
Está escrito nas oito línguas da página e segue o aspeto do resto.

## O que se pode alterar

Apenas as chaves da lista de `settings_api.py` (o esquema). Cada uma tem um tipo e um intervalo, e a página indica se uma alteração exige **reiniciar** o monitor (o ciclo lê
a sua configuração uma única vez) ou **se aplica de imediato**.

| Grupo | Chaves |
|---|---|
| Este navegador | idioma da página, tema (auto / claro / escuro), vista compacta do separador Agora. Ficam guardados no navegador, não no ficheiro. |
| Geral | `language` (idioma predefinido das ferramentas), `github_owner`, `mode` (`full` / `lite`), `ecosystems`, `exclude`, `report_history_days` |
| Atualização e limites | `refresh_seconds`, `cold_refresh_seconds`, `issues_refresh_seconds`, `discover_refresh_seconds`, `stuck_minutes`, `runs_per_repo`, `cold_runs_per_repo`, `hot_hours`, `max_workers`, `min_rate_remaining` |
| Sentinela | `sentinel.enabled`, os ciclos, o orçamento da API, os limiares dos candidatos, das pull requests obsoletas e das assinaturas pendentes, `sentinel.require_verified_signature`, as consultas de A2 |
| Verificações de superfície (A10) | `sentinel.surface.enabled`, os respetivos ciclos, os repositórios por ciclo, o fator de margem e a parte do orçamento |
| Prontidão (A11) | `sentinel.readiness.enabled`, `min_coverage`, `warn_below` |
| Pastas e ficheiros | `workspace_root`, `signed_dir`, `audit_dir`, `ecosystems_file`, `targets_file`, `profiles_file`, `tools_dir`, `sentinel.ci_red_file`, `sentinel.ci_red_audit_copy` |
| Saídas para outras ferramentas | `outputs.prometheus.enabled`, `outputs.prometheus.per_repo`, `outputs.json.enabled`, `outputs.dashboard.enabled` (ver OUTPUTS_por.md) |

## O que nunca se pode alterar nem ver a partir da página

Tokens, segredos, chaves de assinatura, o segredo do webhook, o comando que a sentinela pode executar (`sentinel.notify_command`), as definições de IA e qualquer chave de outra ferramenta: **não estão no
esquema**, pelo que a página nem as mostra nem as escreve, e um pedido que nomeie alguma é recusado. Todas as outras chaves do ficheiro mantêm-se exatamente como estavam.

## Como funciona uma gravação

1. Só são enviados os valores que mudaram, como `POST /api/settings` com `Content-Type: application/json` e um corpo de, no máximo, 16 KB.
2. Cada valor é verificado quanto ao tipo e ao intervalo; um único valor inválido faz recusar todo o pedido e nada é escrito. Os caminhos têm de ser texto sem carateres de controlo, nunca um
   caminho de rede (UNC) e nunca na unidade `D:`.
3. O ficheiro anterior é copiado para `config_backups/actions_monitor-<time>.json` (guardam-se as últimas dez cópias).
4. O novo ficheiro é escrito num ficheiro temporário e movido para cima do antigo (de forma atómica), pelo que uma falha nunca deixa um ficheiro a meio. Um ficheiro que não seja JSON válido nunca é substituído a partir da página.
5. A página indica quais os valores guardados que exigem reinício e mantém um aviso até reiniciar.

## Quem pode fazer o pedido

Apenas a página da mesma máquina: o servidor escuta em `127.0.0.1` e recusa qualquer pedido cujo `Host` ou `Origin` não seja o seu próprio endereço (as mesmas verificações de todos os outros pontos de acesso).
Um formulário de outro site não o consegue alcançar, porque o pedido tem de ser JSON.

## Antes da 1.5.0

O idioma das ferramentas era decidido pelo idioma do sistema; agora arrancam em inglês e o idioma é uma definição (aqui, `language`, `MONITOR_LANG` ou `--lang`).
`parte_history_days` passou a `report_history_days` (o nome antigo continua a ser lido).
