<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SETTINGS.md) | [🇪🇸 Español](SETTINGS_spa.md) | [🇫🇷 Français](SETTINGS_fra.md) | [🇮🇹 Italiano](SETTINGS_ita.md) | [🇩🇪 Deutsch](SETTINGS_deu.md) | [🇨🇳 简体中文](SETTINGS_zho.md) | [🇯🇵 日本語](SETTINGS_jpn.md) | **🇵🇹 Português**

# O separador Definições

O separador Definições (a entrada Definições do painel lateral) altera, a partir da página, os valores de `actions_monitor.json`, para que ninguém tenha de editar o ficheiro à mão.
Está escrito nas oito línguas da página e segue o aspeto do resto.

<!-- settings:begin -->
## O que se pode alterar

Apenas as chaves da lista de `settings_api.py` (o esquema). Cada uma tem um tipo e um intervalo, e a página diz se uma alteração precisa de **reiniciar** o monitor (o ciclo lê a configuração uma vez) ou **aplica-se já**.

O separador divide-se em subseparadores, ordenados do comum ao avançado: Este navegador, Básico, Geral, Atualização e limites, Sentinela, Verificações de superfície (A10), Prontidão (A11), Pastas e ficheiros, Saídas e depois as integrações. Dentro de cada subseparador as definições estão em blocos com título; o primeiro campo de um bloco é o seu interruptor principal e, enquanto estiver desligado, o resto do bloco fica esbatido e não se pode editar. Cada campo mostra a unidade (s, min, h, dias, MB, chamadas), o intervalo, um distintivo (pede reinício / aplica-se já), outro para as opções de segurança que arrancam no estado conservador e uma linha de ajuda. A pesquisa filtra as definições de todos os subseparadores; cada subseparador conta as alterações por guardar; os botões Guardar e Descartar estão sempre visíveis; o navegador lembra o último subseparador. Os separadores seguem o padrão de teclado dos separadores (setas, Início, Fim).

| Separador | Blocos e definições |
|---|---|
| Este navegador | idioma da página, tema (auto / claro / escuro), vista densa do separador Agora. Ficam no navegador, não no ficheiro. |
| Básico | **Arranque**: `open_browser`<br>**Atualizações**: `updates.check`<br>**Escutar na rede**: `airgapped`<br>**Plano e quotas**: `account.plan`, `quota.default_runner`, `quota.warn_percent`, `quota.alert_percent`, `quota.billing_api`<br>**Segurança**: `session_guard`<br>**Descoberta**: `discovery.events`, `discovery.suggest_groups`, `discovery.auto_frequency`<br>**Ciclo de vida**: `discovery.hide` |
| Geral | **Identidade**: `github_owner`, `language`<br>**Âmbito**: `mode`, `repos`, `ecosystems`, `show_unclassified`, `exclude`<br>**Histórico**: `report_history_days` |
| Atualização e limites | **Repositórios quentes**: `refresh_seconds`, `hot_hours`, `runs_per_repo`, `stuck_minutes`<br>**Repositórios frios**: `cold_refresh_seconds`, `cold_runs_per_repo`<br>**Tarefas em segundo plano**: `issues_refresh_seconds`, `discover_refresh_seconds`, `discover_limit`, `max_workers`<br>**Quota da API**: `min_rate_remaining` |
| Leituras e cache | **Leituras condicionais**: `cache.etag.enabled`, `cache.etag.ttl_hours` |
| Sentinela | **Principal**: `sentinel.enabled`, `sentinel.refresh_seconds`, `sentinel.hot_hours`<br>**Avisos para IAs**: `sentinel.alerts_hot_seconds`, `sentinel.alerts_cold_seconds`, `sentinel.hygiene_seconds`<br>**Orçamento da API**: `sentinel.max_calls_per_tick`, `sentinel.budget_per_hour`, `sentinel.workers`, `sentinel.min_rate_remaining`<br>**Versões e assinaturas**: `sentinel.candidate_days`, `sentinel.candidate_min_entries`, `sentinel.skip_candidate_prefixes`, `sentinel.pending_sign_hours`, `sentinel.require_verified_signature`<br>**Consultas de vermelhos (A2)**: `sentinel.a2_full_sample_unknown`, `sentinel.a2_resolve_max_calls_per_tick`, `sentinel.a2_resolve_ttl_seconds`<br>**Pull requests**: `sentinel.stale_pr_days`<br>**Ficheiros obrigatórios**: `sentinel.required_files`<br>**Minutos de Actions**: `sentinel.minutes_budget_period`, `sentinel.minutes_budget`<br>**Ficheiros de auditoria**: `sentinel.audit_files.reconciliation`, `sentinel.audit_files.rounds`, `sentinel.audit_files.rounds_extra` |
| Verificações de superfície (A10) | **Principal**: `sentinel.surface.enabled`, `sentinel.surface.refresh_seconds`, `sentinel.surface.local_seconds`, `sentinel.surface.max_repos_per_tick`, `sentinel.surface.min_rate_factor`, `sentinel.surface.budget_share`<br>**Workflows desativados manualmente**: `sentinel.surface.checks.workflows_disabled.*` (`enabled`)<br>**Agendamentos sem execuções**: `sentinel.surface.checks.dead_schedule.*` (`enabled`, `days`)<br>**uses: não fixado por SHA**: `sentinel.surface.checks.unpinned_uses.*` (`enabled`)<br>**Permissões demasiado amplas (write-all)**: `sentinel.surface.checks.broad_permissions.*` (`enabled`)<br>**pull_request_target com checkout do PR**: `sentinel.surface.checks.pr_target.*` (`enabled`)<br>**Concurrency bloqueada (runs em fila do mesmo workflow)**: `sentinel.surface.checks.stuck_concurrency.*` (`enabled`, `minutes`)<br>**Falhas apenas num sistema da matriz**: `sentinel.surface.checks.matrix_os.*` (`enabled`, `max_per_tick`)<br>**Custo dos artifacts**: `sentinel.surface.checks.artifacts.*` (`enabled`, `max_mb`, `retention_days`)<br>**Checks obrigatórios vermelhos ou em falta**: `sentinel.surface.checks.required_checks.*` (`enabled`)<br>**Releases publicadas incompletas**: `sentinel.surface.checks.release_assets.*` (`enabled`, `recent_days`)<br>**Etiqueta de release vs versão do manifesto/CHANGELOG**: `sentinel.surface.checks.tag_vs_version.*` (`enabled`)<br>**GitHub Packages**: `sentinel.surface.checks.packages.*` (`enabled`)<br>**Rascunhos e pré-releases esquecidos**: `sentinel.surface.checks.drafts.*` (`enabled`, `days`)<br>**Alertas críticos/altos por idade (classificação de repositórios)**: `sentinel.surface.checks.security_aged.*` (`enabled`, `days`)<br>**Cobertura de segurança (CodeQL / Dependabot)**: `sentinel.surface.checks.coverage.*` (`enabled`)<br>**Secret scanning: abertos vs resolvidos**: `sentinel.surface.checks.secret_resolved.*` (`enabled`)<br>**Dependabot por prioridade**: `sentinel.surface.checks.dependabot_priority.*` (`enabled`)<br>**Issues que se podem fechar (apenas sugestão)**: `sentinel.surface.checks.issue_close.*` (`enabled`)<br>**Milestones vencidos por ecossistema**: `sentinel.surface.checks.milestones.*` (`enabled`)<br>**PRs humanos envelhecidos**: `sentinel.surface.checks.pr_human.*` (`enabled`, `days`)<br>**PRs que alteram workflows ou CODEOWNERS (prioridade)**: `sentinel.surface.checks.pr_workflow_touch.*` (`enabled`)<br>**Fila de integração: aprovados com CI verde**: `sentinel.surface.checks.merge_queue.*` (`enabled`)<br>**Maturidade do manifesto face à evidência**: `sentinel.surface.checks.maturity.*` (`enabled`)<br>**Paridade dos README em 8 idiomas quebrada**: `sentinel.surface.checks.parity.*` (`enabled`)<br>**Atestações de build**: `sentinel.surface.checks.attestation.*` (`enabled`, `max_per_tick`) |
| Preparação (A11) | **Principal**: `sentinel.readiness.enabled`, `sentinel.readiness.min_coverage`, `sentinel.readiness.warn_below`<br>**Pesos da saúde**: `sentinel.readiness.health.weights.red`, `sentinel.readiness.health.weights.stuck`, `sentinel.readiness.health.weights.secret`, `sentinel.readiness.health.weights.high_alert`, `sentinel.readiness.health.weights.alert`, `sentinel.readiness.health.weights.stale_pr`, `sentinel.readiness.health.weights.unsigned`, `sentinel.readiness.health.weights.hygiene`<br>**Versões fixadas**: `sentinel.readiness.pins.refresh_seconds`, `sentinel.readiness.pins.max_depth`, `sentinel.readiness.pins.sources` |
| Pastas e ficheiros | **Pastas locais**: `workspace_root`, `signed_dir`, `audit_dir`, `tools_dir`<br>**Ficheiros de dados**: `ecosystems_file`, `targets_file`, `profiles_file`<br>**ci_red.json**: `sentinel.ci_red_file`, `sentinel.ci_red_audit_copy` |
| Saídas para outras ferramentas | **Prometheus**: `outputs.prometheus.enabled`, `outputs.prometheus.per_repo`<br>**JSON do Grafana**: `outputs.json.enabled`<br>**Painel de estado**: `outputs.dashboard.enabled` |
| IA externa para a sentinela | **Serviço**: `ai.provider`, `ai.model`, `ai.ollama_url`, `ai.base_url`, `ai.api_key_env`, `ai.daily_limit`<br>**Limites**: `ai.max_input_chars`, `ai.max_output_chars`, `ai.timeout_seconds`<br>**Âmbito**: `ai.events`, `ai.allowed_repos`, `ai.answer_language`<br>**Ações**: `ai.actions.enabled`, `ai.actions.execute`, `ai.actions.allowed`, `ai.actions.max_per_hour`, `ai.actions.ttl_seconds`<br>**Avisos para IAs**: `ai_alerts.enabled`, `ai_alerts.folder`, `ai_alerts.brief_max_bytes`, `ai_alerts.hook.enabled`, `ai_alerts.hook.url`, `ai_alerts.hook.max_per_hour` |
| Webhook de entrada | **Webhook de entrada**: `webhook.enabled`, `webhook.signing_state`, `webhook.record_events`, `webhook.live_events_keep`, `webhook.replay_seconds`, `webhook.max_per_minute` |
| Notificações | **Principal**: `notify.enabled`, `notify.events`, `notify.max_per_hour`<br>**Telegram**: `notify.channels.telegram.enabled`, `notify.channels.telegram.token_env`, `notify.channels.telegram.chat_id`<br>**Discord**: `notify.channels.discord.enabled`, `notify.channels.discord.url_env`<br>**Slack**: `notify.channels.slack.enabled`, `notify.channels.slack.url_env`<br>**Matrix**: `notify.channels.matrix.enabled`, `notify.channels.matrix.homeserver`, `notify.channels.matrix.room`, `notify.channels.matrix.token_env`<br>**MQTT (este computador)**: `notify.channels.mqtt.enabled`, `notify.channels.mqtt.host`, `notify.channels.mqtt.port`, `notify.channels.mqtt.topic`<br>**HTTP (este computador)**: `notify.channels.http_local.enabled`, `notify.channels.http_local.url` |
| Análises | **Principal**: `analytics.enabled`, `analytics.keep_days`<br>**Amostras**: `analytics.min_samples`, `analytics.max_samples`, `analytics.jobs_per_cycle`, `analytics.steps`<br>**Sinais**: `analytics.slow_factor`, `analytics.flaky` |
| Linter de workflows | **Principal**: `lint.enabled`, `lint.refresh_seconds`, `lint.in_report`, `lint.ignore`<br>**uses: não fixado a um SHA de commit completo**: `lint.rules.unpinned_uses.enabled`, `lint.rules.unpinned_uses.severity`<br>**sem bloco permissions, ou write-all**: `lint.rules.permissions.enabled`, `lint.rules.permissions.severity`<br>**parece um segredo escrito no ficheiro**: `lint.rules.secrets_in_clear.enabled`, `lint.rules.secrets_in_clear.severity`<br>**texto de terceiros colado num script run:**: `lint.rules.injection.enabled`, `lint.rules.injection.severity`<br>**pull_request_target obtém o código do PR**: `lint.rules.pr_target.enabled`, `lint.rules.pr_target.severity` |
| Avançado (opcional) | **Escutar na rede**: `listen.network`, `listen.host`, `listen.token_env`, `listen.allowed_hosts`, `listen.tls_cert_file`, `listen.tls_key_file`, `listen.secure_cookie`, `listen.proxy_public_host`, `listen.max_failed_attempts`<br>**Token próprio do GitHub**: `github_token.enabled`, `github_token.store`<br>**Ações no GitHub**: `github_actions.enabled`, `github_actions.allowed`, `github_actions.merge_method`<br>**Executar um workflow aqui (act)**: `act.enabled`, `act.allowed`, `act.timeout_seconds`, `act.allow_symlinks`<br>**Compilações em lote**: `dispatch.required_ci`<br>**Cópia local dos artefactos**: `mirror.enabled`, `mirror.folder`, `mirror.max_mb`, `mirror.keep_days`, `mirror.max_per_cycle`<br>**Runners próprios**: `runners.enabled`, `runners.scope`<br>**Exportação OpenTelemetry**: `otlp.enabled`, `otlp.endpoint`, `otlp.interval_seconds`<br>**Organizações**: `organizations.discover`<br>**Custo dos minutos (FinOps)**: `finops.jobs_per_cycle` |
| Vista de consola | **Consola**: `tui.theme`, `tui.refresh_seconds` |

Cada definição aparece num só sítio. Só de leitura: `webhook.signing_state` apenas diz se o segredo partilhado está definido; o segredo nunca é mostrado.

Que repositórios são vigiados: o catálogo de exemplo de ecossistemas termina com um grupo `rest` (prefixo `*`, «Everything else») que recolhe todo o repositório que nenhum outro grupo reclama, por isso por predefinição nada fica de fora. Se o seu próprio catálogo deixar repositórios de fora, um aviso da página diz quantos («o seu filtro de ecossistemas oculta N dos M repositórios da conta»).

IA externa: `ai.provider` pode ser `ollama` (este computador), `openai-compatible` (qualquer endpoint ao estilo OpenAI, que serve também para o Gemini através do seu endpoint compatível com OpenAI e para a OpenAI), `anthropic` (a API Messages; o modelo é você que o escolhe) ou `copilot` (`gh copilot` com o seu acesso; gasta pedidos premium). A chave nunca é guardada: só o NOME da variável de ambiente. Ver AI_por.md.

### Exemplo de fontes de versões fixadas

As versões fixadas só são lidas se houver uma fonte; com a lista vazia nada é lido e a página di-lo. O texto seguinte é um exemplo, comentado:

```jsonc
// Example, commented out: where the pinned versions of an ecosystem live. Copy the part you need into
// "sentinel" > "readiness" > "pins" > "sources" of actions_monitor.json (or paste it in the Settings tab) and remove the comments.
// [
//   {"ecosystem": "alpha", "kind": "pin_table", "provider": "ALPHA-COMMON", "file": "pins/consumers.json", "key": "consumers"},
//   {"ecosystem": "beta",  "kind": "lock_files", "provider": "BETA-CORE", "lock_name": "beta.lock.json", "version_key": "core"}
// ]
// pin_table: a JSON file of the provider that maps each repository to the version it pins (under "key").
// lock_files: every clone is searched (down to "max_depth" folder levels) for files called "lock_name"; the OLDEST version found in "version_key" counts.
```
<!-- settings:end -->

## O que nunca se pode alterar nem ver a partir da página

Tokens, segredos, chaves de assinatura, o segredo do webhook, o comando que a sentinela pode executar (`sentinel.notify_command`), a chave da API da IA (só se pode indicar o nome da sua variável de ambiente) e qualquer chave de outra ferramenta: **não estão no
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
