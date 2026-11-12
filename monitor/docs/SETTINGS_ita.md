<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SETTINGS.md) | [🇪🇸 Español](SETTINGS_spa.md) | [🇫🇷 Français](SETTINGS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](SETTINGS_deu.md) | [🇨🇳 简体中文](SETTINGS_zho.md) | [🇯🇵 日本語](SETTINGS_jpn.md) | [🇵🇹 Português](SETTINGS_por.md)

# La scheda Impostazioni

La scheda Impostazioni (la voce Impostazioni del pannello laterale) modifica dalla pagina i valori di `actions_monitor.json`, così nessuno deve modificare il file a mano.
È scritta negli otto lingue della pagina e segue l'aspetto del resto.

<!-- settings:begin -->
## Cosa si può modificare

Solo le chiavi dell'elenco di `settings_api.py` (lo schema). Ognuna ha un tipo e un intervallo, e la pagina dice se una modifica richiede il **riavvio** del monitor (il ciclo legge la configurazione una volta) o **si applica subito**.

La scheda è divisa in sotto-schede, dal comune all'avanzato: Questo browser, Di base, Generale, Aggiornamento e limiti, Sentinella, Controlli di superficie (A10), Prontezza (A11), Cartelle e file, Uscite, poi le integrazioni. In ogni sotto-scheda le impostazioni sono in blocchi con titolo; il primo campo di un blocco è il suo interruttore principale e, finché è spento, il resto del blocco è attenuato e non modificabile. Ogni campo mostra l'unità (s, min, h, giorni, MB, chiamate), l'intervallo, un badge (richiede riavvio / si applica subito), un badge per le opzioni di sicurezza che partono dal valore prudente e una riga di aiuto. La ricerca filtra le impostazioni di tutte le sotto-schede; ogni sotto-scheda conta le modifiche non salvate; i pulsanti Salva e Annulla restano visibili; il browser ricorda l'ultima sotto-scheda. Le schede seguono lo schema da tastiera (frecce, Home, Fine).

| Scheda | Blocchi e impostazioni |
|---|---|
| Questo browser | lingua della pagina, tema (auto / chiaro / scuro), vista densa della scheda Adesso. Restano nel browser, non nel file. |
| Di base | **Avvio**: `open_browser`<br>**Aggiornamenti**: `updates.check`<br>**Ascolto in rete**: `airgapped`<br>**Piano e quote**: `account.plan`, `quota.default_runner`, `quota.warn_percent`, `quota.alert_percent`, `quota.billing_api`<br>**Sicurezza**: `session_guard`<br>**Rilevamento**: `discovery.events`, `discovery.suggest_groups`, `discovery.auto_frequency`<br>**Ciclo di vita**: `discovery.hide` |
| Generale | **Identità**: `github_owner`, `language`, `display.timezone`<br>**Ambito**: `mode`, `repos`, `ecosystems`, `show_unclassified`, `exclude`<br>**Cronologia**: `report_history_days` |
| Aggiornamento e limiti | **Repository attivi**: `refresh_seconds`, `hot_hours`, `runs_per_repo`, `stuck_minutes`<br>**Repository inattivi**: `cold_refresh_seconds`, `cold_runs_per_repo`<br>**Attività in background**: `issues_refresh_seconds`, `discover_refresh_seconds`, `discover_limit`, `max_workers`<br>**Quota API**: `min_rate_remaining` |
| Letture e cache | **Letture condizionali**: `cache.etag.enabled`, `cache.etag.ttl_hours` |
| Sentinella | **Principale**: `sentinel.enabled`, `sentinel.refresh_seconds`, `sentinel.hot_hours`<br>**Avvisi per le IA**: `sentinel.alerts_hot_seconds`, `sentinel.alerts_cold_seconds`, `sentinel.hygiene_seconds`<br>**Budget API**: `sentinel.max_calls_per_tick`, `sentinel.budget_per_hour`, `sentinel.workers`, `sentinel.min_rate_remaining`<br>**Release e firme**: `sentinel.candidate_days`, `sentinel.candidate_min_entries`, `sentinel.skip_candidate_prefixes`, `sentinel.pending_sign_hours`, `sentinel.require_verified_signature`<br>**Ricerche dei rossi (A2)**: `sentinel.a2_full_sample_unknown`, `sentinel.a2_resolve_max_calls_per_tick`, `sentinel.a2_resolve_ttl_seconds`<br>**Pull request**: `sentinel.stale_pr_days`<br>**File obbligatori**: `sentinel.required_files`<br>**Minuti di Actions**: `sentinel.minutes_budget_period`, `sentinel.minutes_budget`<br>**File di audit**: `sentinel.audit_files.reconciliation`, `sentinel.audit_files.rounds`, `sentinel.audit_files.rounds_extra`<br>**Issue e pull request**: `sentinels.collab.enabled`, `sentinels.collab.refresh_seconds`, `sentinels.collab.max_repos_per_tick`, `sentinels.collab.min_rate_remaining`, `sentinels.collab.repos`, `sentinels.collab.rules.issue_stale_days`, `sentinels.collab.rules.issue_critical_labels`, `sentinels.collab.rules.pr_review_pending_days`, `sentinels.collab.rules.pr_draft_max_days`, `sentinels.collab.rules.pr_conflict_days`, `sentinels.collab.rules.watch_external_comments`, `sentinels.collab.rules.ignore_labels`, `alerts.mute_hours` |
| Controlli di superficie (A10) | **Principale**: `sentinel.surface.enabled`, `sentinel.surface.refresh_seconds`, `sentinel.surface.local_seconds`, `sentinel.surface.max_repos_per_tick`, `sentinel.surface.min_rate_factor`, `sentinel.surface.budget_share`<br>**Workflow disattivati a mano**: `sentinel.surface.checks.workflows_disabled.*` (`enabled`)<br>**Schedule senza esecuzioni**: `sentinel.surface.checks.dead_schedule.*` (`enabled`, `days`)<br>**uses: non fissato tramite SHA**: `sentinel.surface.checks.unpinned_uses.*` (`enabled`)<br>**Permessi troppo ampi (write-all)**: `sentinel.surface.checks.broad_permissions.*` (`enabled`)<br>**pull_request_target con checkout della PR**: `sentinel.surface.checks.pr_target.*` (`enabled`)<br>**Concurrency bloccata (run in coda dello stesso workflow)**: `sentinel.surface.checks.stuck_concurrency.*` (`enabled`, `minutes`)<br>**Errori solo su un sistema della matrice**: `sentinel.surface.checks.matrix_os.*` (`enabled`, `max_per_tick`)<br>**Costo degli artifact**: `sentinel.surface.checks.artifacts.*` (`enabled`, `max_mb`, `retention_days`)<br>**Check obbligatori rossi o assenti**: `sentinel.surface.checks.required_checks.*` (`enabled`)<br>**Release pubblicate incomplete**: `sentinel.surface.checks.release_assets.*` (`enabled`, `recent_days`)<br>**Tag di release vs versione del manifest/CHANGELOG**: `sentinel.surface.checks.tag_vs_version.*` (`enabled`)<br>**GitHub Packages**: `sentinel.surface.checks.packages.*` (`enabled`)<br>**Bozze e pre-release dimenticate**: `sentinel.surface.checks.drafts.*` (`enabled`, `days`)<br>**Avvisi critici/alti per età (classifica dei repository)**: `sentinel.surface.checks.security_aged.*` (`enabled`, `days`)<br>**Copertura di sicurezza (CodeQL / Dependabot)**: `sentinel.surface.checks.coverage.*` (`enabled`)<br>**Secret scanning: aperti vs risolti**: `sentinel.surface.checks.secret_resolved.*` (`enabled`)<br>**Dependabot per priorità**: `sentinel.surface.checks.dependabot_priority.*` (`enabled`)<br>**Issue che si potrebbero chiudere (solo suggerimento)**: `sentinel.surface.checks.issue_close.*` (`enabled`)<br>**Milestone scaduti per ecosistema**: `sentinel.surface.checks.milestones.*` (`enabled`)<br>**PR umane datate**: `sentinel.surface.checks.pr_human.*` (`enabled`, `days`)<br>**PR che modificano workflow o CODEOWNERS (priorità)**: `sentinel.surface.checks.pr_workflow_touch.*` (`enabled`)<br>**Coda di merge: approvate con CI verde**: `sentinel.surface.checks.merge_queue.*` (`enabled`)<br>**Maturità del manifest rispetto alle prove**: `sentinel.surface.checks.maturity.*` (`enabled`)<br>**Parità dei README in 8 lingue interrotta**: `sentinel.surface.checks.parity.*` (`enabled`)<br>**Attestazioni di build**: `sentinel.surface.checks.attestation.*` (`enabled`, `max_per_tick`) |
| Preparazione (A11) | **Principale**: `sentinel.readiness.enabled`, `sentinel.readiness.min_coverage`, `sentinel.readiness.warn_below`<br>**Pesi della salute**: `sentinel.readiness.health.weights.red`, `sentinel.readiness.health.weights.stuck`, `sentinel.readiness.health.weights.secret`, `sentinel.readiness.health.weights.high_alert`, `sentinel.readiness.health.weights.alert`, `sentinel.readiness.health.weights.stale_pr`, `sentinel.readiness.health.weights.unsigned`, `sentinel.readiness.health.weights.hygiene`<br>**Versioni fissate**: `sentinel.readiness.pins.refresh_seconds`, `sentinel.readiness.pins.max_depth`, `sentinel.readiness.pins.sources` |
| Cartelle e file | **Cartelle locali**: `workspace_root`, `signed_dir`, `audit_dir`, `tools_dir`<br>**File di dati**: `ecosystems_file`, `targets_file`, `profiles_file`<br>**ci_red.json**: `sentinel.ci_red_file`, `sentinel.ci_red_audit_copy` |
| Uscite per altri strumenti | **Prometheus**: `outputs.prometheus.enabled`, `outputs.prometheus.per_repo`<br>**JSON di Grafana**: `outputs.json.enabled`<br>**Dashboard di stato**: `outputs.dashboard.enabled` |
| IA esterna per la sentinella | **Servizio**: `ai.provider`, `ai.model`, `ai.ollama_url`, `ai.base_url`, `ai.api_key_env`, `ai.daily_limit`<br>**Limiti**: `ai.max_input_chars`, `ai.max_output_chars`, `ai.timeout_seconds`<br>**Ambito**: `ai.events`, `ai.allowed_repos`, `ai.answer_language`<br>**Azioni**: `ai.actions.enabled`, `ai.actions.execute`, `ai.actions.allowed`, `ai.actions.max_per_hour`, `ai.actions.ttl_seconds`<br>**Avvisi per le IA**: `ai_alerts.enabled`, `ai_alerts.folder`, `ai_alerts.brief_max_bytes`, `ai_alerts.hook.enabled`, `ai_alerts.hook.url`, `ai_alerts.hook.max_per_hour`, `ai_alerts.diagnose.enabled`, `ai_alerts.diagnose.max_per_cycle`, `ai_alerts.diagnose.log_lines`, `ai_alerts.diagnose.max_bytes`, `ai_alerts.cascade.enabled`, `ai_alerts.stream.enabled`, `ai_alerts.stream.max_seconds`, `ai_alerts.stream.max_clients`, `ai_alerts.heartbeat.enabled`, `ai_alerts.heartbeat.window_minutes`, `ai_alerts.client_hook.enabled`, `ai_alerts.client_hook.block_on_stop`, `ai_alerts.client_hook.cooldown_minutes`, `ai_alerts.client_hook.stale_hours`, `ai_alerts.client_hook.max_lines`, `ai_alerts.client_hook.max_chars` |
| Webhook in ingresso | **Webhook in ingresso**: `webhook.enabled`, `webhook.signing_state`, `webhook.record_events`, `webhook.live_events_keep`, `webhook.replay_seconds`, `webhook.max_per_minute` |
| Notifiche | **Principale**: `notify.enabled`, `notify.allow_private_targets`, `network.use_proxy`, `notify.events`, `notify.max_per_hour`<br>**Telegram**: `notify.channels.telegram.enabled`, `notify.channels.telegram.token_env`, `notify.channels.telegram.chat_id`<br>**Discord**: `notify.channels.discord.enabled`, `notify.channels.discord.url_env`<br>**Slack**: `notify.channels.slack.enabled`, `notify.channels.slack.url_env`<br>**Matrix**: `notify.channels.matrix.enabled`, `notify.channels.matrix.homeserver`, `notify.channels.matrix.room`, `notify.channels.matrix.token_env`<br>**MQTT (questo computer)**: `notify.channels.mqtt.enabled`, `notify.channels.mqtt.host`, `notify.channels.mqtt.port`, `notify.channels.mqtt.topic`<br>**HTTP (questo computer)**: `notify.channels.http_local.enabled`, `notify.channels.http_local.url` |
| Analisi | **Principale**: `analytics.enabled`, `analytics.keep_days`<br>**Campioni**: `analytics.min_samples`, `analytics.max_samples`, `analytics.jobs_per_cycle`, `analytics.steps`<br>**Segnali**: `analytics.slow_factor`, `analytics.flaky` |
| Linter dei workflow | **Principale**: `lint.enabled`, `lint.refresh_seconds`, `lint.in_report`, `lint.ignore`<br>**uses: non fissato a un SHA di commit completo**: `lint.rules.unpinned_uses.enabled`, `lint.rules.unpinned_uses.severity`<br>**nessun blocco permissions, o write-all**: `lint.rules.permissions.enabled`, `lint.rules.permissions.severity`<br>**sembra un segreto scritto nel file**: `lint.rules.secrets_in_clear.enabled`, `lint.rules.secrets_in_clear.severity`<br>**testo di terzi incollato in uno script run:**: `lint.rules.injection.enabled`, `lint.rules.injection.severity`<br>**pull_request_target scarica il codice della PR**: `lint.rules.pr_target.enabled`, `lint.rules.pr_target.severity` |
| Avanzate (opzionali) | **Ascolto in rete**: `listen.network`, `listen.host`, `listen.token_env`, `listen.allowed_hosts`, `listen.tls_cert_file`, `listen.tls_key_file`, `listen.secure_cookie`, `listen.proxy_public_host`, `listen.max_failed_attempts`, `listen.query_access`<br>**Token GitHub proprio**: `github_token.enabled`, `github_token.store`<br>**Azioni su GitHub**: `github_actions.enabled`, `github_actions.allowed`, `github_actions.merge_method`<br>**Esegui un workflow qui (act)**: `act.enabled`, `act.allowed`, `act.timeout_seconds`, `act.allow_symlinks`<br>**Build a lotti**: `dispatch.required_ci`<br>**Copia locale degli artefatti**: `mirror.enabled`, `mirror.folder`, `mirror.max_mb`, `mirror.keep_days`, `mirror.max_per_cycle`<br>**Runner self-hosted**: `runners.enabled`, `runners.scope`<br>**Esportazione OpenTelemetry**: `otlp.enabled`, `otlp.endpoint`, `otlp.interval_seconds`<br>**Organizzazioni**: `organizations.discover`<br>**Costo dei minuti (FinOps)**: `finops.jobs_per_cycle` |
| Vista da console | **Console**: `tui.theme`, `tui.refresh_seconds` |

Un'impostazione compare in un solo posto. Sola lettura: `webhook.signing_state` dice solo se il segreto condiviso è definito; il segreto non viene mai mostrato.

Quali repository si osservano: il catalogo di esempio degli ecosistemi termina con un gruppo `rest` (prefisso `*`, «Everything else») che prende ogni repository che nessun altro gruppo rivendica, quindi per impostazione predefinita nulla resta fuori. Se il tuo catalogo ne lascia fuori, un avviso della pagina dice quanti («il tuo filtro degli ecosistemi nasconde N dei M repository dell'account»).

IA esterna: `ai.provider` può essere `ollama` (questo computer), `openai-compatible` (qualsiasi endpoint in stile OpenAI, che serve anche per Gemini tramite il suo endpoint compatibile OpenAI e per OpenAI), `anthropic` (l'API Messages; il modello lo scegli tu) o `copilot` (`gh copilot` con il tuo accesso; consuma richieste premium). La chiave non viene mai salvata: solo il NOME della variabile d'ambiente. Vedi AI_ita.md.

### Esempio di fonti delle versioni fissate

Le versioni fissate si leggono solo se è indicata una fonte; con l'elenco vuoto non si legge nulla e la pagina lo dice. Il testo seguente è un esempio, commentato:

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

## Che cosa non si può mai modificare né vedere dalla pagina

Token, segreti, chiavi di firma, il segreto del webhook, il comando che la sentinella può eseguire (`sentinel.notify_command`), la chiave API dell'IA (si può impostare solo il nome della sua variabile d'ambiente) e qualsiasi chiave di un altro strumento: **non sono nello
schema**, quindi la pagina non li mostra né li scrive, e una richiesta che ne nomini uno viene rifiutata. Tutte le altre chiavi del file restano esattamente come erano.

## Come funziona un salvataggio

1. Vengono inviati solo i valori modificati, come `POST /api/settings` con `Content-Type: application/json` e un corpo di al massimo 16 KB.
2. Ogni valore viene verificato rispetto al proprio tipo e intervallo; un solo valore non valido fa rifiutare l'intera richiesta e non viene scritto nulla. I percorsi devono essere testo senza caratteri di controllo, mai un
   percorso di rete (UNC) e mai sull'unità `D:`.
3. Il file precedente viene copiato in `config_backups/actions_monitor-<time>.json` (si conservano le ultime dieci copie).
4. Il nuovo file viene scritto in un file temporaneo e spostato sopra il vecchio (in modo atomico), così un arresto anomalo non lascia mai un file a metà. Un file che non è JSON valido non viene mai sovrascritto dalla pagina.
5. La pagina indica quali valori salvati richiedono il riavvio e mantiene un avviso finché non riavvii.

## Chi può farne richiesta

Solo la pagina della stessa macchina: il server è in ascolto su `127.0.0.1` e rifiuta le richieste il cui `Host` o `Origin` non sia il suo stesso indirizzo (gli stessi controlli di ogni altro endpoint).
Un modulo proveniente da un altro sito non può raggiungerlo, perché la richiesta deve essere JSON.

## Prima della 1.5.0

La lingua degli strumenti era decisa dalla lingua del sistema; ora partono in inglese e la lingua è un'impostazione (qui `language`, `MONITOR_LANG` oppure `--lang`).
`parte_history_days` ora è `report_history_days` (il vecchio nome viene ancora letto).
