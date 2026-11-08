<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL.md) | [🇪🇸 Español](SENTINEL_spa.md) | [🇫🇷 Français](SENTINEL_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](SENTINEL_deu.md) | [🇨🇳 简体中文](SENTINEL_zho.md) | [🇯🇵 日本語](SENTINEL_jpn.md) | [🇵🇹 Português](SENTINEL_por.md)

# La sentinella e i suoi controlli A1-A13

La **sentinella** è la seconda metà dell'edizione completa. Il *monitor* mostra cosa gira e cosa fallisce adesso; la *sentinella* esamina l'intero account ogni pochi minuti e risponde a un'altra domanda: **cosa richiede una persona**. Legge GitHub (non vi scrive mai), conserva una breve cronologia su questo computer e trasforma ciò che trova in tredici controlli numerati, **da A1 ad A13**, con un semaforo ciascuno.

**L'edizione lite non la include.** `MONITOR_LITE_GITHUB_ACTIONS` (porta 8766) non ha sentinella: il modulo non viene nemmeno importato e i suoi endpoint rispondono 404. L'edizione completa (`MONITOR_GITHUB_ACTIONS`, porta 8765) la avvia da sola; si spegne con `sentinel.enabled` (Impostazioni > Sentinella). Le due edizioni usano la stessa regola di «rosso su main» (A2), quindi le cifre coincidono.

## Come parte e quanto costa

Parte con il monitor completo e gira nello stesso processo, in un thread proprio, con un proprio budget di chiamate a GitHub (`sentinel.budget_per_hour`, 600 per impostazione predefinita, e `sentinel.max_calls_per_tick`). Quando la quota di GitHub scende sotto `sentinel.min_rate_remaining` smette di chiedere e la pagina indica la pausa per quota. Nulla di ciò che fa scrive su GitHub.

## File che scrive (accanto al monitor, mai pubblicati)

| File | Contenuto |
|---|---|
| `ci_red.json` | schema 2: per repository i workflow in rosso e le ore che una release attende la firma. Contratto stabile per altri strumenti, vedi `CI_RED_SCHEMA_ita.md` e `CI_RED_BRIDGE_ita.md`. Dove: `sentinel.ci_red_file`. |
| `sentinel_history.json` | i totali giornalieri (avvisi, rossi, candidate) per le tendenze e per «nuovi da ieri». |
| `sentinel_cache.json` | le ultime risposte delle letture lente, perché un riavvio non richieda tutto da capo. |
| `events_monitor.jsonl`, `events_state.json` | il flusso di eventi (cosa è diventato rosso, cosa è stato risolto) con un `code` stabile per evento. |
| `SENTINEL_REPORT_*.txt` | il rapporto giornaliero, salvato nella cartella di audit se esiste. |

## Come leggerla

Ogni controllo ha uno di cinque livelli: **ok** (niente da fare), **info** (utile saperlo), **warn** (da guardare presto), **bad** (agisci ora) e **unknown** (non ancora verificabile: **unknown non è mai mostrato in verde**). Il rapporto in cima alla scheda li riassume in poche righe; il dettaglio si apre per controllo. Un repository filtrato nel monitor non viene controllato.

## I controlli

| Controllo | Cosa controlla e la regola esatta | Dove si configura | Livello e cosa fare |
|---|---|---|---|
| **A1** | **Build.** Un run in corso o in coda oltre il limite è *bloccato*. Si elencano anche le issue aperte con l'etichetta `build-failed` o `build-stuck`. I run dell'evento `dynamic` (interni di Dependabot) sono ignorati. | `stuck_minutes` | **bad** se qualcosa è bloccato o c'è un'issue aperta. Apri il run, annullalo o rilancialo; chiudi l'issue a correzione avvenuta. |
| **A2** | **CI rossa.** Per ogni file di workflow, l'ULTIMO run COMPLETATO sul branch PREDEFINITO: è rosso se è fallito (`failure`, `timed_out`, `startup_failure`, `action_required`). I run `cancelled`, `skipped`, `neutral` o `stale`, quelli in corso e quelli di altri branch non dicono nulla e non nascondono mai un rosso precedente. *Serie* = rossi consecutivi. Quando la lista di run di un repository è lunga quanto il campione richiesto, un workflow può restare oltre: la sentinella chiede a GitHub l'ultimo run di ciascuno di quei workflow. | `runs_per_repo`, `cold_runs_per_repo`, `sentinel.a2_full_sample_unknown`, `sentinel.a2_resolve_max_calls_per_tick`, `sentinel.a2_resolve_ttl_seconds` | **bad** se un workflow è rosso; **unknown** (mai verde) se un repository non ha dati di run o un workflow non è stato risolto. Correggi il workflow o rilancialo; l'edizione lite mostra la stessa cifra, segnata come approssimata perché indovina il branch predefinito. |
| **A3** | **Avvisi di sicurezza.** Avvisi aperti di CodeQL, Dependabot e secret scanning per repository, con la gravità, e quanti sono nuovi dall'ultimo giorno della cronologia. | `sentinel.alerts_hot_seconds`, `sentinel.alerts_cold_seconds` | **bad** per qualsiasi avviso di segreti o critico/alto; **warn** per gli altri; **unknown** durante il caricamento. Ruota prima un segreto trapelato; poi aggiorna o scarta il resto. |
| **A4** | **Pull request di Dependabot.** PR aperte di Dependabot con la loro età, un salto di versione *maggiore* e un conflitto di merge; le PR di altre persone sono solo contate. | `sentinel.stale_pr_days` (7) | **warn** se una è un salto maggiore o in conflitto; **info** se ci sono solo PR. Unisci le verdi; riallinea o chiudi quelle in conflitto. |
| **A5** | **Release.** (a) *Candidata*: almeno `candidate_min_entries` voci sotto `[Unreleased]` del CHANGELOG e l'ultima release più vecchia di `candidate_days` (o nessuna). (b) Una *build verde* di un workflow di release più recente dell'ultima release. (c) *In attesa di firma*: una build verde più vecchia di `pending_sign_hours` non firmata né pubblicata; una firma conta solo se si verifica con la chiave pubblica dell'ecosistema. | `sentinel.candidate_days` (2), `sentinel.candidate_min_entries` (1), `sentinel.skip_candidate_prefixes`, `sentinel.pending_sign_hours` (24), `sentinel.require_verified_signature` | **warn** con una candidata o una firma in sospeso; **info** con build verdi non ancora pubblicate. Taglia la release o firma la build. |
| **A6** | **Igiene.** Per repository: il ruleset `protect-main` è ACTIVE, esiste l'etichetta `dependencies`, esistono i file richiesti (per impostazione predefinita README, LICENSE, CHANGELOG, SECURITY), il pinning per SHA è obbligatorio, `allowed_actions` è `selected` e nessun workflow pianificato è stato disattivato da GitHub. | `sentinel.required_files`, `sentinel.hygiene_seconds` | **warn** se un repository ha un problema; **info** finché alcuni non sono controllati. Ogni problema indica il rimedio. |
| **A7** | **Uso.** Minuti di Actions delle ultime 24 ore e 7 giorni per repository ed ecosistema, la quota API rimasta e il *budget* per ecosistema: **ok** sotto l'80 %, **warn** dall'80 %, **over** dal 100 % del tetto. | `sentinel.min_rate_remaining` (800), `sentinel.minutes_budget`, `sentinel.minutes_budget_period` (7d) | **warn** se la quota è sotto il limite o un budget raggiunge l'80 %. Rallenta l'aggiornamento o riduci i workflow lunghi. |
| **A8** | **Round.** Legge i file di audit e di round della cartella di audit (i modelli di `sentinel.audit_files`) e ne mostra lo stato. Vuoto se non c'è la cartella di audit. | `sentinel.audit_files.*`, `audit_dir` | Solo **info**. Niente da fare. |
| **A9** | **Roadmap.** Se le board di GitHub Projects degli ecosistemi sono *vive*: riconciliate negli ultimi 8 giorni e non più vecchie delle loro definizioni. Richiede lo scope `read:project` di `gh`; senza, la scheda funziona con le definizioni e dice cosa manca. | (fixed: 8 days) | **warn** se una board è scaduta o mai riconciliata; **unknown** se non configurata. |
| **A10** | **Superficie di Actions e release.** Venticinque controlli di sola lettura sui cloni e poche chiamate a freddo, elencati nella tabella sotto. Ognuno ha un interruttore e, quando serve, una soglia. | `sentinel.surface.*` | Per controllo, vedi sotto. In pausa quando la quota è bassa (il rapporto lo dice). |
| **A11** | **Prontezza delle release, salute dell'ecosistema e pin.** Prontezza per repository (voci, CI, versione, build, firma, passo successivo); un punteggio di salute 0-100 per ecosistema che sottrae penalità ponderate per rossi, blocchi, segreti, avvisi alti, avvisi, PR vecchie, build non firmate e igiene; e i pin delle dipendenze in ritardo. Un punteggio compare solo se `min_coverage` dei repository ha dati. | `sentinel.readiness.*` (`warn_below` 70, `min_coverage` 0.5) | **warn** quando un punteggio è sotto `warn_below`; **info** con repository in ritardo; **unknown** con pochi dati. |
| **A12** | **Analitica.** p50 / p95 della durata di ogni workflow, del tempo in coda dei suoi job e di ogni passo; workflow più lenti del solito (`analytics.slow_factor`); workflow *flaky* (falliti e poi passati sullo stesso commit). Solo un'etichetta: non cambia mai ciò che conta come rosso. | `analytics.*` | Nessun semaforo proprio. Guarda prima i lenti e i flaky. |
| **A13** | **Linter dei workflow.** Regole statiche sui cloni locali: `unpinned_uses`, `permissions`, `secrets_in_clear`, `injection`, `pr_target`. Ogni rilievo ha un livello (info / avviso / errore); un commento `# monitor-lint: ignore REGOLA motivo` o `lint.ignore` ne silenzia uno. | `lint.*` | Colore del rilievo peggiore. Correggi prima gli errori; la pagina filtra per livello. |

## I controlli di A10

Sono tutti suggerimenti di sola lettura per una persona; il monitor non chiude mai un'issue, non unisce una pull request né pubblica una release. Se ne spegne uno con `sentinel.surface.checks.<nome>.enabled`.

| Controllo | Cosa cerca | Predefinito |
|---|---|---|
| `workflows_disabled` | Workflow disattivati a mano | on |
| `dead_schedule` | Schedule senza esecuzioni | on · days=14 |
| `unpinned_uses` | uses: non fissato tramite SHA | on |
| `broad_permissions` | Permessi troppo ampi (write-all) | on |
| `pr_target` | pull_request_target con checkout della PR | on |
| `stuck_concurrency` | Concurrency bloccata (run in coda dello stesso workflow) | on · minutes=60 |
| `matrix_os` | Errori solo su un sistema della matrice | on · max_per_tick=4 |
| `artifacts` | Costo degli artifact | on · max_mb=500, retention_days=30 |
| `required_checks` | Check obbligatori rossi o assenti | on |
| `release_assets` | Release pubblicate incomplete | on · recent_days=30, required |
| `tag_vs_version` | Tag di release vs versione del manifest/CHANGELOG | on |
| `packages` | GitHub Packages | on |
| `drafts` | Bozze e pre-release dimenticate | on · days=14 |
| `security_aged` | Avvisi critici/alti per età (classifica dei repository) | on · days=30 |
| `coverage` | Copertura di sicurezza (CodeQL / Dependabot) | on |
| `secret_resolved` | Secret scanning: aperti vs risolti | on |
| `dependabot_priority` | Dependabot per priorità | on |
| `issue_close` | Issue che si potrebbero chiudere (solo suggerimento) | on |
| `milestones` | Milestone scaduti per ecosistema | on |
| `pr_human` | PR umane datate | on · days=7 |
| `pr_workflow_touch` | PR che modificano workflow o CODEOWNERS (priorità) | on |
| `merge_queue` | Coda di merge: approvate con CI verde | on |
| `maturity` | Maturità del manifest rispetto alle prove | on |
| `parity` | Parità dei README in 8 lingue interrotta | on |
| `attestation` | Attestazioni di build | on · max_per_tick=3 |

## Dove si configura tutto

Ogni soglia qui sopra è un'impostazione delle schede **Sentinella**, **Controlli di superficie (A10)**, **Prontezza (A11)**, **Cartelle e file**, **Analitica** e **Linter dei workflow** della pagina Impostazioni, e una chiave di `actions_monitor.json`. L'elenco completo con gli intervalli è in `SETTINGS_ita.md`. Il pannello Guida e `--help-topics sentinel` mostrano questa pagina offline.
