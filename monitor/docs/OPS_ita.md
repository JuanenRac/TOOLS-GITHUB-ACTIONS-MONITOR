<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](OPS.md) | [🇪🇸 Español](OPS_spa.md) | [🇫🇷 Français](OPS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](OPS_deu.md) | [🇨🇳 简体中文](OPS_zho.md) | [🇯🇵 日本語](OPS_jpn.md) | [🇵🇹 Português](OPS_por.md)

# Gestire l'installazione

Per un monitor che resta acceso per mesi (edizione Completa). Copre il backup completo, il ripristino, il backup pianificato, il doctor con codici di uscita su cui un cron può contare e come configurarlo come appliance (systemd o Docker). L'edizione Lite non ha nulla di tutto questo.

## Il pacchetto di backup

`python bin/monitor_cli.py backup create [FILE]` scrive UN `.zip` (formato 2) e lo verifica prima di metterlo a posto. Senza `FILE` va nella cartella `backups` della cartella dei dati (`ops.backup.dir`) con il nome `ghamon-backup-<ora UTC>.zip`. Non occorre fermare il monitor: i dati si leggono con le letture atomiche dell'archivio (file o SQLite), mai copiando un database mentre viene scritto.

| Membro | Cosa contiene |
|---|---|
| `dump.jsonl` | ogni account (le sue impostazioni, lo stato delle sentinelle, i piccoli documenti, gli eventi, le analisi, le istantanee del punteggio) e i record globali (utenti e account che possono vedere; mai le sessioni) |
| `files.json` | le impostazioni della pagina e gli elenchi dell'installazione (`targets.json`, `ecosystems.json`, `profiles.json`, i silenziamenti), ripuliti; anche gli archivi dei moduli opzionali, se esistono (`proposals.json`, `devices.json`) |
| `manifest.json` | il formato, la versione del prodotto, lo schema, i conteggi e la dimensione e lo SHA-256 di ogni membro |

**Cosa non viaggia mai:** token e chiavi di GitHub o di una App, password, il valore di qualunque variabile `*_env` (solo il suo nome), il segreto del webhook, le chiavi dei provider di IA, le sessioni e il contenuto dell'archivio dei segreti. Le impostazioni passano da una lista bianca (le stesse chiavi che la pagina delle Impostazioni può mostrare) e poi da una pulizia che scarta ogni chiave che sembra un segreto e ogni testo che sembra un token o una chiave privata. Con `ops.backup.include_config` spento, impostazioni ed elenchi restano del tutto fuori. Un ripristino non riporta alcuna credenziale: rimetti a posto l'accesso a GitHub (lo dice la sua lista di cose da fare).

Il backup è leggibile solo dal suo proprietario (modo 600) e il pacchetto non è cifrato se non lo chiedi: vedi sotto.

### Un pacchetto di un solo account

`backup create --account ID [FILE]` scrive il pacchetto di UN account: il suo dump (con le sue impostazioni, ripulite allo stesso modo) e nient'altro. Non contiene alcun utente né sessione, né le impostazioni o gli elenchi dell'installazione; il manifest dice `scope: account`. `backup verify` controlla che contenga solo quell'account, e `backup restore FILE` ripristina quell'account (non serve `--account`) senza toccare gli altri account, gli utenti o i file della destinazione; viene rifiutato solo quando quell'account esiste già lì e manca `--force`. È il modo per spostare o recuperare un solo account.

### Cifrare il backup (facoltativo)

`ops.backup.encrypt` (o `--encrypt` per un backup) cifra il pacchetto con AES-256-GCM usando una chiave presa dalla variabile d'ambiente indicata da `ops.backup.key_env` (`--key-env NOME`). La chiave non è mai un'impostazione, non viene mai scritta e non sta mai su una riga di comando. Serve la libreria facoltativa `cryptography` (`pip install cryptography`; il nucleo del monitor resta solo libreria standard). Senza la libreria, o senza una chiave di 12 caratteri o più, il backup viene **rifiutato** con un messaggio chiaro e non si scrive nulla: non si fa mai un backup in chiaro quando ne hai chiesto uno cifrato, né uno cifrato con qualcosa di più debole. Un file cifrato finisce in `.enc`; `verify` e `restore` lo aprono con la stessa variabile. Tieni la chiave separata dal file: senza di essa il backup non si apre.

## Verificare, elencare e stato

- `backup verify FILE` rilegge il pacchetto e controlla ogni dimensione e ogni SHA-256 e i conteggi. Un byte cambiato, un membro mancante o uno che il manifest non elenca viene segnalato. `--deep` lo ripristina anche in una cartella temporanea e controlla il risultato.
- `backup list` mostra i backup della cartella; `backup status` mostra l'ultimo backup valido, la sua età, la pianificazione e l'ultimo errore.
- Un pacchetto del primo formato (fatto prima della 2.1.0) si verifica e si ripristina ancora.

## Ripristinare

`python bin/monitor_cli.py backup restore FILE`: ferma prima il monitor (il ripristino viene rifiutato finché uno risponde sulla sua porta). Verifica il pacchetto, poi scrive gli account e i file.

- Un archivio che contiene già account viene rifiutato salvo `--force` (gli account del pacchetto vengono allora scritti sopra; le impostazioni vengono **unite**: una chiave che il pacchetto non porta non viene mai rimossa).
- `--account ID` ripristina solo quell'account e lascia gli altri e i file globali come sono (rifiutato solo quando quell'account esiste e manca `--force`).
- `--to-dir CARTELLA` ripristina in una cartella vuota (backend a file) senza toccare l'installazione: il modo per guardare un backup o per traslocare su un'altra macchina.
- Scrive `ops/restore_report.json` nella cartella dei dati e stampa cosa resta da fare: rimettere l'accesso a GitHub, reimpostare le impostazioni che il pacchetto ha lasciato fuori, riavviare il monitor perché il supervisore avvii ogni account, eseguire il doctor.

## Il backup pianificato

Due modi, usane uno:

1. Dentro il monitor: `ops.backup.enabled` (spento per impostazione predefinita) fa un backup ogni `ops.backup.interval_hours` in un thread proprio, conserva i `ops.backup.keep` più recenti (si rimuovono solo file con il nome di un backup) e annota il risultato in `ops/backup_status.json`. Un errore (disco pieno, chiave mancante) viene annotato e mostrato nel pannello Informazioni e nel doctor; non ferma mai il monitor.
2. Con systemd: `deploy/github-actions-monitor-backup.service` e `deploy/github-actions-monitor-backup.timer` (vedi sotto).

Il pannello Informazioni ha una scheda **Operatività** con la modalità (servizio o locale), l'ultimo backup valido, la pianificazione, la conservazione in vigore e il pulsante **Fai il backup ora** (un amministratore, da questo computer). `GET /api/ops/status` dà gli stessi dati; `POST /api/ops/backup` fa un backup.

## Pulizia su richiesta

La pulizia di conservazione parte da sola ogni `retention.interval_hours`. Per eseguirla subito c'è un pulsante (e `POST /api/ops/purge`) che **non esiste** finché `ops.purge.enabled` non è acceso (spento per impostazione predefinita). Una richiesta è una prova (la politica in vigore e quanti eventi se ne andrebbero) salvo che dica `dry_run` false, e una pulizia reale viene rifiutata senza un backup valido più recente di `ops.purge.require_backup_hours` (24 per impostazione predefinita; 0 non lo richiede). Lascia la sua riga nell'audit della conservazione e nel registro delle azioni.

## Il doctor e i suoi codici di uscita

`python bin/monitor_cli.py doctor [--strict] [--json]` (o `python bin/actions_monitor.py --doctor`) controlla l'installazione, non cambia nulla e non stampa alcun segreto. L'edizione Completa aggiunge questi controlli dopo quelli abituali:

| Controllo | Cosa guarda |
|---|---|
| `volumes` | un file viene davvero scritto, letto e rimosso nelle cartelle dei dati, dei log e dei backup (un volume Docker montato come root o in sola lettura fallisce qui) |
| `supervisor` | un monitor in esecuzione: la salute approfondita del supervisore e di ogni ciclo di aggiornamento (non si avvia nulla) |
| `limits` | il segreto del webhook è definito e lungo almeno `ops.doctor.webhook_min_length` caratteri (si confronta solo la lunghezza) e la politica di conservazione |
| `sqlite_hot` | ogni database SQLite aperto in sola lettura: `quick_check` (predefinito) o `integrity_check` (`ops.doctor.sqlite_check` deep), fermato a `ops.doctor.sqlite_timeout_s`; un file corrotto dopo un'interruzione di corrente fallisce |
| `backup_age` | l'ultimo backup valido rispetto a `ops.doctor.backup_max_age_days` |
| `disk` | spazio libero del volume dei dati rispetto a `ops.doctor.min_free_mb` |
| `metrics` | `/metrics` risponde quando l'uscita Prometheus è accesa e un monitor è in esecuzione |

**Codici di uscita (stabili, per cron):** `0` tutto bene (anche con avvisi, senza `--strict`); `1` almeno un controllo è fallito; `3` solo avvisi e `--strict` (o `ops.doctor.strict_exit`); `4` il doctor stesso non è riuscito a partire. Sono i codici del doctor; gli altri comandi di `monitor_cli.py` mantengono i loro. Esempio: `0 * * * * python3 bin/monitor_cli.py doctor --strict --json > /var/lib/github-actions-monitor/doctor.json || true` e avvisa per qualunque codice diverso da 0.

## Come appliance

**systemd** (senza contenitore): segui i commenti di `deploy/github-actions-monitor.service`, poi installa l'unità di backup e il suo timer:

```
install -m 644 deploy/github-actions-monitor-backup.service deploy/github-actions-monitor-backup.timer /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now github-actions-monitor-backup.timer
systemctl list-timers github-actions-monitor-backup.timer
```

Per un backup cifrato metti la variabile indicata da `ops.backup.key_env` in `/etc/github-actions-monitor/env` (modo 600). Il timer esegue `backup create` ogni giorno; il suo codice di uscita è 1 quando il backup non è stato possibile.

**Docker:** `deploy/compose.yaml` tiene i backup in un volume a parte (`monitor-backups` in `/data/backups`) così perdere il volume dei dati non li perde. Porta fuori un file con `docker compose exec monitor python bin/monitor_cli.py backup list` e `docker cp`, e ripristina in un contenitore fermo o con `--to-dir`. Il TLS lo rinnova il Caddy di `deploy/Caddyfile`.

**Aggiornare senza perdere gli account:** `backup create` → `backup verify FILE` → fermare il monitor → sostituire la cartella del prodotto (le cartelle `config/`, `data/`, `logs/` e `ai/` sono tue e restano) → `doctor` → avviare. Se qualcosa va storto, `backup restore FILE`. **Rimuoverlo in modo pulito:** ferma e disattiva le unità, rimuovi il timer, poi la cartella del prodotto e, solo se vuoi perdere i dati, le cartelle `config/`, `data/` o i volumi Docker.

## Impostazioni

Sono tutte nella scheda Impostazioni (Cartelle e file) e in [SETTINGS_ita.md](SETTINGS_ita.md): `ops.backup.*` (enabled, dir, interval_hours, keep, include_config, compress_level, encrypt, key_env), `ops.purge.*` (enabled, require_backup_hours) e `ops.doctor.*` (strict_exit, backup_max_age_days, min_free_mb, sqlite_check, sqlite_timeout_s, webhook_min_length). Ogni interruttore parte spento o prudente, e quelli di sicurezza (il backup pianificato, l'inclusione delle impostazioni, la cifratura, la pulizia) sono contrassegnati come tali.

Vedi anche [STORAGE_ita.md](STORAGE_ita.md) (i backend e la conservazione), [DEPLOYMENT_ita.md](DEPLOYMENT_ita.md) (servizio, contenitore, TLS) e [CLI_ita.md](CLI_ita.md).

## Il monitor sorveglia la propria memoria e i propri thread

Ogni `selfwatch.interval_seconds` (60) il monitor legge la propria memoria residente, i propri thread e l'uso del processore e li mostra in `/api/health` come `selfwatch` (`state`: `ok` o `high`). Quando la memoria supera `selfwatch.rss_warn_mb` (1024) o i thread `selfwatch.threads_warn` (400), lo annota una volta nel contatore degli errori inghiottiti (`selfwatch.high`, con le cifre), libera ciò che può e annota il ritorno alla normalità. Si disattiva con `selfwatch.enabled`. Imposta `selfwatch.rss_warn_mb` poco sotto il limite del tuo container. La CI esegue il monitor in un container con un processore e 512 MB con un account di 120 workflow (`tools/limits_check.py`).
