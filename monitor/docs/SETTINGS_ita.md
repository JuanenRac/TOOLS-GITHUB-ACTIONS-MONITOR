<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SETTINGS.md) | [🇪🇸 Español](SETTINGS_spa.md) | [🇫🇷 Français](SETTINGS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](SETTINGS_deu.md) | [🇨🇳 简体中文](SETTINGS_zho.md) | [🇯🇵 日本語](SETTINGS_jpn.md) | [🇵🇹 Português](SETTINGS_por.md)

# La scheda Impostazioni

La scheda Impostazioni (l'icona a forma di ingranaggio nell'intestazione o nella barra delle schede) modifica dalla pagina i valori di `actions_monitor.json`, così nessuno deve modificare il file a mano.
È scritta negli otto lingue della pagina e segue l'aspetto del resto.

## Che cosa si può modificare

Solo le chiavi dell'elenco in `settings_api.py` (lo schema). Ognuna ha un tipo e un intervallo, e la pagina indica se una modifica richiede il **riavvio** del monitor (il ciclo legge
la propria configurazione una sola volta) oppure **si applica subito**.

| Gruppo | Chiavi |
|---|---|
| Questo browser | lingua della pagina, tema (auto / chiaro / scuro), vista compatta della scheda Adesso. Sono conservati nel browser, non nel file. |
| Generale | `language` (lingua predefinita degli strumenti), `github_owner`, `mode` (`full` / `lite`), `ecosystems`, `exclude`, `report_history_days` |
| Aggiornamento e limiti | `refresh_seconds`, `cold_refresh_seconds`, `issues_refresh_seconds`, `discover_refresh_seconds`, `stuck_minutes`, `runs_per_repo`, `cold_runs_per_repo`, `hot_hours`, `max_workers`, `min_rate_remaining` |
| Sentinella | `sentinel.enabled`, i cicli, il budget delle API, le soglie dei candidati, delle pull request obsolete e delle firme in sospeso, `sentinel.require_verified_signature`, le consultazioni di A2 |
| Controlli di superficie (A10) | `sentinel.surface.enabled`, i relativi cicli, i repository per ciclo, il fattore di margine e la quota del budget |
| Prontezza (A11) | `sentinel.readiness.enabled`, `min_coverage`, `warn_below` |
| Cartelle e file | `workspace_root`, `signed_dir`, `audit_dir`, `ecosystems_file`, `targets_file`, `profiles_file`, `tools_dir`, `sentinel.ci_red_file`, `sentinel.ci_red_audit_copy` |
| Uscite per altri strumenti | `outputs.prometheus.enabled`, `outputs.prometheus.per_repo`, `outputs.json.enabled`, `outputs.dashboard.enabled` (vedi OUTPUTS_ita.md) |
| IA esterna per la sentinella | `ai.provider` (`none` / `openai-compatible` / `ollama`), `ai.model`, `ai.ollama_url` (solo questo computer), `ai.base_url` (https), `ai.api_key_env` (il NOME della variabile d'ambiente che contiene la chiave) e `ai.daily_limit`. La chiave stessa non viene mai salvata. Spenta per impostazione predefinita; un servizio esterno riceve dati dei tuoi repository. |

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
