<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](STORAGE.md) | [🇪🇸 Español](STORAGE_spa.md) | [🇫🇷 Français](STORAGE_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](STORAGE_deu.md) | [🇨🇳 简体中文](STORAGE_zho.md) | [🇯🇵 日本語](STORAGE_jpn.md) | [🇵🇹 Português](STORAGE_por.md)

# Archiviazione e conservazione

Dove l'edizione completa conserva ciò che impara, come cambiarlo e cosa elimina da sola. L'edizione lite conserva sempre file semplici, non ha database né attività di conservazione e non mostra nulla di tutto questo.

## Cosa viene conservato

Per ogni account: la configurazione (`actions_monitor.json`), lo stato delle sentinelle, il feed degli eventi, ciò che il feed ha già annunciato, i campioni delle analisi, i silenziamenti e l'avviso di aggiornamento. Per l'intera installazione: gli utenti, gli account che possono vedere e le loro sessioni (le usa la modalità team). Le cache delle letture condizionali e i registri sono sempre file semplici.

## Le due archiviazioni

|  | `file` (predefinita) | `sqlite` |
|---|---|---|
| Dove | `accounts/<id>/` (accanto ai lanciatori se non c'è `accounts/`) | `accounts/<id>/storage.sqlite3`, un database per account |
| Scritture | un file temporaneo, scritto su disco e rinominato | una breve transazione, journal WAL |
| Sceglila per | una persona; file che puoi leggere e modificare | un servizio attivo per mesi; molti eventi |

Si sceglie nella configurazione dell'account (o del monitor): `"storage": {"backend": "sqlite"}`. La configurazione stessa resta sempre un file JSON, perché è lei a indicare l'archiviazione. Con SQLite il feed degli eventi è nel database, non in `events_monitor.jsonl`. Un database che non si può aprire blocca l'avvio: il monitor non scrive mai il proprio stato altrove alle tue spalle.

## Decisione: un'archiviazione per account (modello A)

*Contesto.* L'edizione completa avvia un processo per account. *Decisione.* Ogni processo ha la propria archiviazione: i propri file, o il proprio database `storage.sqlite3` dentro `accounts/<id>/`. Due processi non scrivono mai lo stesso file, quindi non c'è nulla da bloccare tra loro e un problema in un account non può danneggiarne un altro. *Costo.* Una domanda che attraversa più account richiede di leggere più database.

*Tenuto pronto: modello B, un database condiviso.* Metti lo stesso percorso nel blocco `storage` di ogni account (`"path": "/data/monitor.sqlite3"`). Funziona perché ogni tabella porta l'account, WAL permette alla pagina di leggere mentre le sentinelle scrivono, le transazioni sono brevi e si attende fino a 5 secondi se il database è occupato. È testato (due processi che eseguono il ciclo insieme; una pagina che risponde via HTTP mentre scrivono) ma non è il predefinito: è più fragile di A e conviene solo se ti serve SQL tra account.

## Cosa è garantito

- Una scrittura è atomica: chi legge vede il valore vecchio o quello nuovo. Un processo interrotto a metà (`kill -9`) lascia il valore vecchio; con SQLite il prossimo avvio si riprende da solo.
- Lo schema è versionato (`schema_version`). Ogni migrazione gira in un'unica transazione insieme all'aumento di versione: una interrotta lascia il database com'era e riparte al prossimo avvio. Un database scritto da una versione più recente viene rifiutato, mai retrocesso.
- Un elemento danneggiato o mancante si legge come vuoto: il monitor parte con ciò che c'è sul disco.

## Spostare i dati e copie di sicurezza

```
python tools/migrate_storage.py --from file --to sqlite              # simulazione: mostra cosa copierebbe
python tools/migrate_storage.py --from file --to sqlite --apply      # copia, poi confronta ogni elemento e ogni evento
python tools/backup_storage.py backup backup.zip --backend sqlite    # un .zip con manifesto e SHA-256
python tools/backup_storage.py verify backup.zip
python tools/backup_storage.py restore backup.zip --backend file     # in un'archiviazione vuota (--force su account esistenti)
```

La migrazione non modifica né cancella mai i tuoi file, riprende dopo un'interruzione (un account viene copiato per intero o per niente) e termina con un errore se i due lati differiscono; solo allora cambia l'archiviazione e riavvia. Una copia fatta da file si ripristina in SQLite e viceversa. `--db FILE` sceglie il database condiviso del modello B; `--flat` è l'installazione senza `accounts/`. `--doctor` controlla il database (presente, integrità, schema) senza modificarlo.

## Conservazione

Un monitor lasciato attivo per mesi crescerebbe senza limite, quindi un breve passaggio al termine di un aggiornamento (ogni `retention.interval_hours`, 24 per impostazione predefinita) elimina ciò che è vecchio:

| Impostazione | Predefinito | Significato |
|---|---|---|
| `retention.enabled` | attivo | l'interruttore |
| `retention.events_days` | 90 | gli eventi più vecchi vengono rimossi |
| `retention.analytics_days` | 180 | i giorni dello storico delle analisi più vecchi vengono rimossi |
| `retention.mode` | `archive` | `archive` scrive prima gli eventi vecchi in un `.gz` in `events/archive/` |
| `retention.events_max_kb` | 512 | limite di dimensione del file del feed con l'archiviazione su file (come sempre) |
| `retention.warn_events_mb` | 20 | `--doctor` avvisa oltre questa dimensione |

La pulizia tocca solo eventi e giorni di analisi più vecchi del loro limite; non tocca mai la configurazione, lo stato delle sentinelle, i silenziamenti né un evento senza ora. Ogni passaggio lascia una riga nel documento di audit (quando, quanti eventi rimossi e conservati, il file di archivio, quanti giorni di analisi, l'eventuale errore). `--doctor` avvisa della dimensione degli eventi e, per un monitor che funziona come servizio (modalità rete, senza browser, un container o `MONITOR_SERVICE=1`), quando la sua configurazione non ha un blocco `retention`. Fai una copia prima di accorciare i limiti.

Il predefinito `archive` conserva ciò che viene rimosso in file compressi che puoi rileggere; `delete` lo elimina definitivamente.
