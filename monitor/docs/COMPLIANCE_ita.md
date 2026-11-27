<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLIANCE.md) | [🇪🇸 Español](COMPLIANCE_spa.md) | [🇫🇷 Français](COMPLIANCE_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](COMPLIANCE_deu.md) | [🇨🇳 简体中文](COMPLIANCE_zho.md) | [🇯🇵 日本語](COMPLIANCE_jpn.md) | [🇵🇹 Português](COMPLIANCE_por.md)

# Conformità: cosa puoi dimostrare della tua installazione

Tutto è spento di fabbrica e vale solo nell'edizione completa, salvo le due restrizioni, che valgono per ogni processo del monitor. Nulla di questo è una certificazione.

## Modalità di sola lettura rigorosa

`security.read_only_strict` (spento). Acceso, non viene scritto nulla su GitHub qualunque cosa dicano edizione o altre impostazioni: partono solo comandi di lettura di `gh` (ciò che non è noto come lettura viene rifiutato), niente `git push`, niente `act` e nessuna richiesta all'API di GitHub diversa da GET o HEAD. È applicato sotto tutte le parti, con un hook di audit di Python che vede ogni programma avviato. Si cambia solo dal computer del monitor e allentarlo richiede un riavvio. La finestra Informazioni e `/api/about` (`restrictions`) dicono se è in vigore.

## Criterio di rete

`security.egress_policy`: `default`, `github_only` o `none`; `security.egress_allow` aggiunge host (`nome`, `*.nome`, un indirizzo) o `program:NOME`. Con `github_only` i processi del monitor raggiungono solo `api.github.com`, `uploads.github.com`, l'host di `GH_HOST` (GitHub Enterprise) e ciò che consenti; con `none` solo questo computer, e `gh` non viene avviato. I programmi che aprono la rete da soli (`git` per i comandi di rete, `apprise`, `curl`, `docker`, gli strumenti dei depositi di segreti) non vengono avviati. Una connessione rifiutata fallisce con un errore che nomina l'impostazione. `python bin/monitor_cli.py doctor` fallisce quando una destinazione configurata è fuori dal criterio, e `doctor --egress` le elenca tutte. Non è un firewall: non governa ciò che fanno gli altri programmi del computer.

## Il rapporto di conformità

`python bin/monitor_cli.py compliance report` (con `--json`), `GET /api/compliance/report` (amministratori) e un riquadro in fondo alla scheda Sicurezza. Ogni riga dice se è **verificata** (il monitor ha controllato) o solo **dichiarata** (lo dice la configurazione): versione e supporto, edizione, autenticazione e provider di identità, modalità di rete e TLS, le due restrizioni e le destinazioni, conservazione e blocco legale, registro delle azioni e la sua catena, copie e loro cifratura, cifratura a riposo (nessuna), archiviazione, plugin, installazione e profilo. Nessun segreto, percorso o nome. `GET /api/compliance/state` fornisce restrizioni, tabella di conservazione e stato dell'esportazione.

## Conservazione e blocco legale

Eventi, analisi e punteggi mantengono le loro impostazioni (`retention.events_days`, `retention.analytics_days`, `retention.mode`). Le altre categorie si conservano per sempre salvo indicare dei giorni: `retention.audit_days` (file ruotati interi del registro delle azioni), `retention.reports_days` (resta il rapporto più recente di ogni account), `retention.ai_log_days`, `retention.backups_days` (resta la copia più recente). Ogni eliminazione lascia una riga nel registro delle azioni. `retention.legal_hold` ferma ogni rimozione: eventi, analisi, punteggi, rapporti, copie, il taglio del feed e del registro dei prompt, la rotazione e la pulizia del registro. Le proposte dell'IA scadono da sole; i dispositivi abbinati restano finché non li togli; questa versione non conserva postmortem, incidenti o note.

## Punti di controllo firmati del registro delle azioni

`audit_checkpoints.enabled` (spento) firma la catena (HMAC-SHA256) con una chiave dell'installazione: `config/audit_checkpoint.key`, o il file indicato in `MONITOR_AUDIT_KEY_FILE` per tenerla separata. Un punto di controllo alla prima riga e poi almeno ogni ora e ogni 1000 righe; anche l'ancora è firmata, e un taglio della fine seguito da una nuova riga resta scritto nella catena. `python bin/monitor_cli.py audit verify` (`--audit-from N`), `audit checkpoint` e `audit purge --older-than-days N` (`--dry-run`), che elimina interi file ruotati e firma il punto da cui continua la catena. Chi può leggere la chiave può firmare: tienila lontana da chi può scrivere il registro.

## Esportazione del registro delle azioni

`audit_export.enabled` (spento) con `audit_export.target` = `file` (`path`, ruotato a `max_mb`), `syslog` (`host`, `port` 6514, RFC 5424 su TCP con TLS, `ca_file`) o `http` (`url`, POST di righe JSON, token dalla variabile indicata in `token_env`). Gli indirizzi privati richiedono `audit_export.allow_private_targets`. Il registro è la coda: ciò che la destinazione non ha preso attende lì; oltre `spool_mb` il doctor segnala `system.audit_export_lag`, e le righe ruotate prima dell'invio contano come perse. `python bin/monitor_cli.py audit export` fa subito un passaggio. Provato con ricevitori di questo computer, non con un vero prodotto syslog o SIEM.

## Versioni supportate

È supportata solo l'ultima versione pubblicata: non c'è un ramo a lungo termine. Il doctor (`compliance_support`) avvisa quando ne conosce una più recente.

## Prove dell'irrobustimento

`[IMP]` = un test di questo repository esercita il controllo; `[PAR]` = solo una parte, e la riga dice cosa manca. L'elenco è `schemas/controls.json` e un test verifica che questa tabella e i test citati coincidano.

| Controllo | Stato | Nome |
|---|---|---|
| `sqlite_contention` | [IMP] | Più processi che scrivono un database |
| `storage_migrations` | [IMP] | Migrazioni dell'archivio |
| `retention_by_category` | [IMP] | Conservazione per categoria e blocco legale |
| `incoming_webhook` | [IMP] | Webhook in ingresso: firma, dimensione, tempo |
| `metrics_labels` | [IMP] | Etichette di /metrics |
| `timezone` | [IMP] | Fusi orari e cambio dell'ora |
| `read_only_strict` | [IMP] | Sola lettura rigorosa |
| `egress_policy` | [IMP] | Criterio di rete |
| `audit_chain` | [IMP] | Catena e punti di controllo del registro |
| `service_and_volume` | [PAR] | Servizio systemd, database grande (file system di rete non provati) |

## Limiti noti

- Un account `viewer` seduto al computer stesso del monitor è trattato come locale e vede i percorsi completi.
- Il webhook in ingresso controlla la finestra di tempo solo per le consegne `workflow_run` e `workflow_job`.
- Con `none` o `github_only`, un processo Python avviato dal monitor applica il criterio solo se importa il monitor; un programma lanciato da te ne è fuori.
- In questa versione non esistono cifratura a riposo, un ramo a lungo termine e federazione.
