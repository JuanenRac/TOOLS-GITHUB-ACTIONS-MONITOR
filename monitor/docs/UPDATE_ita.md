<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Aggiornare il monitor (l'updater)

[English](UPDATE.md) · [Español](UPDATE_spa.md) · [Français](UPDATE_fra.md) · **Italiano** · [Deutsch](UPDATE_deu.md) · [简体中文](UPDATE_zho.md) · [日本語](UPDATE_jpn.md) · [Português](UPDATE_por.md)

L'updater porta un'installazione da qualsiasi versione pubblicata a qualsiasi altra (in su o in giù), migra la tua configurazione e lascia una via di ritorno. È UN solo file, `monitor_updater.py`, che richiede solo Python e funziona con qualunque versione installata; è anche dentro il prodotto (`tools/monitor_updater.py`) e come comando `monitor_cli.py update`. Non si aggiorna mai da solo: solo quando lo chiedi, e non cancella nulla (ciò che viene sostituito va nella cartella delle copie).

## Tre modi per aprirlo

- `py -3 monitor_updater.py` apre una pagina nel browser. È servita su 127.0.0.1 solo mentre l'updater gira, con un token monouso nell'indirizzo; nient'altro può usarla.
- `py -3 monitor_updater.py --tk` apre lo stesso in una finestra (serve Tkinter).
- `py -3 monitor_updater.py --console` è un menu di testo per server, SSH e container.
- `py -3 bin/monitor_cli.py update` è lo stesso file avviato dal prodotto; `update plan`, `update apply` e gli altri comandi sotto accettano le opzioni della tabella.

## Il menu Aggiornamenti dentro il monitor

L'edizione Completa ha lo stesso aggiornatore dentro la sua pagina: **Sistema > Aggiornamenti**. Mostra la versione installata e quella trovata dal controllo (impostazione `updates.check`; non si chiede nulla a GitHub finché è spento o il monitor è offline), le note di ogni release e, con il pulsante «Cerca versioni», l'elenco di quelle pubblicate. Nulla viene scaricato o applicato se non premi un pulsante. Applicare richiede un amministratore sul computer dove gira il monitor (le rotte `/api/updates/*` rispondono 403 dalla rete) e una conferma che dice cosa succederà: lo SHA-256 dello zip confrontato con SHA256SUMS, la copia fatta prima (con la sua cartella), la migrazione della configurazione e il riavvio. L'aggiornamento gira in un processo a parte: il monitor si ferma da solo, l'aggiornamento viene applicato, il monitor riparte con la nuova versione e la pagina si riconnette; se la nuova versione non parte, quella precedente viene rimessa e avviata. «Torna alla versione precedente» fa lo stesso al contrario. I passi, la cronologia e il risultato si vedono nella pagina e vengono annotati nel registro delle azioni. Non è offerto nell'edizione Lite, in un container né sotto un gestore di servizi (riavviano il processo da soli: usa la riga di comando), e gira un solo aggiornamento alla volta. Configurazione, dati, chiavi e log non vengono sostituiti. Il file autonomo resta la via di ritorno quando il monitor non parte.

Sotto un gestore di servizi la pagina non applica gli aggiornamenti per impostazione predefinita. Se il monitor gira come servizio UTENTE di systemd (`systemctl --user`), puoi attivare `updates.systemd_helper` (spento di default): la pagina offre allora l'aggiornamento e il processo che lo applica ferma quel servizio, applica l'aggiornamento e riavvia il servizio, sempre con `systemctl --user` e mai con `sudo`. Un servizio di sistema (che richiede l'amministratore) non viene toccato e resta «usa la riga di comando». Lo stesso funziona dalla riga di comando con `--systemd-unit UNITÀ` (`apply` e `rollback`); se il servizio non si può fermare non parte nulla, e se la nuova versione non si avvia viene rimessa la precedente e il servizio riavviato.

**Fiducia.** Il controllo confronta lo zip con SHA256SUMS ed entrambi provengono dalla stessa release di GitHub: rileva un download danneggiato o incompleto, non una release sostituita all'origine. La fiducia nella release poggia su GitHub e sul tuo account lì.

## Cosa fa, passo per passo Le rotte che lo sostengono sono `/api/updates/status`, `/api/updates/progress`, `/api/updates/history`, `/api/updates/log` (le ultime righe del registro del processo, valori dopo token o secret nascosti), `/api/updates/copies` (sola lettura) e `/api/updates/check`, `/api/updates/plan`, `/api/updates/apply`, `/api/updates/rollback`, `/api/updates/discard` (amministratore, solo da questo computer). L'avanzamento viaggia anche come eventi inviati dal server su `/api/updates/stream` (la pagina lo usa mentre un aggiornamento è in corso e torna a chiedere ogni secondo e mezzo se il browser o la connessione non lo consentono).

1. Rileva l'installazione: cartella, versione, edizione (Completa o Lite), configurazione, dati, porte, se il monitor è in esecuzione, container o servizio.
2. Elenca tutte le versioni pubblicate su GitHub (senza token) con data e note, e segna quella installata e l'ultima. Senza connessione, dagli uno zip con `--zip`.
3. Scegli la versione di destinazione. Una inferiore è un downgrade: richiede `--allow-downgrade`.
4. Mostra il PIANO come prova a secco: la catena di passi tra le due versioni (letta dal registro delle migrazioni), cosa cambia nella TUA configurazione, i cambi di comportamento che noterai e ogni incoerenza trovata.
5. Lo applica: copia preventiva, SHA-256 verificato con SHA256SUMS, zip estratto in una cartella nuova e ispezionato (percorsi con `..`, link, dimensione), prodotto copiato, le tue righe nei launcher rimesse a posto, configurazione migrata, struttura delle cartelle migrata e, se vuoi, monitor avviato e `/api/health` verificato.
6. Se qualcosa fallisce torna da solo allo stato precedente e scrive un rapporto. Ogni aggiornamento entra nella cronologia (`update_history.jsonl`) e l'ultimo si può annullare con il comando `rollback`.

## Comandi

Senza comando si apre la pagina. I comandi rispondono una volta (aggiungi `--json` per un documento):

| Comando | Significato |
|---|---|
| `status` | cosa è installato e cosa trovano i controlli |
| `releases` | tutte le versioni pubblicate |
| `plan` | la prova a secco per una destinazione |
| `apply` | eseguirlo (`--dry-run` mostra solo il piano) |
| `migrate` | migrare solo un file di configurazione, vedi sotto |
| `rollback` | tornare alla versione precedente all'ultimo aggiornamento |
| `history` | gli aggiornamenti fatti su questa installazione |
| `copies` | le copie della cartella delle copie: nome, stato, versioni, dimensione e quale serve al ritorno indietro |
| `discard` | `discard --name COPIA` elimina UNA copia dopo la conferma (`--yes` salta la domanda); la copia del ritorno indietro solo con `--force`; quella di un aggiornamento in corso, mai |
| `log` | le ultime righe (`--lines N`, al massimo 2000) del registro del processo dell'ultimo aggiornamento, con i valori dopo token, secret o password nascosti |

## Opzioni

| Opzione | Significato |
|---|---|
| `--dir` | l'installazione (predefinito: dove si trova il file, risalendo) |
| `--to` | versione di destinazione (predefinito: l'ultima) |
| `--from` | migrate: la versione da cui viene il file |
| `--config` | migrate: un file di configurazione |
| `--zip` | usare questo zip invece di GitHub |
| `--sha256` | SHA-256 atteso dello zip |
| `--dry-run` | mostrare solo il piano |
| `--apply` | migrate: scrivere il risultato |
| `--yes` | non chiedere conferma |
| `--json` | la risposta come un documento JSON |
| `--keep-old-defaults` | scrive il vecchio valore predefinito di ogni impostazione mai definita, così il comportamento non cambia |
| `--adopt-new-defaults` | sposta al nuovo valore anche le impostazioni che hanno ancora il vecchio |
| `--start` | avviare poi il monitor e verificarlo |
| `--handover` | il monitor che ha avviato questo processo si ferma da solo: aspettarlo, applicare, riavviarlo (se l'avvio fallisce, torna la versione precedente) |
| `--status-file` | scrive l'avanzamento in questo file JSON (lo legge il menu Aggiornamenti) |
| `--edition` | complete o lite, se non si può dedurre |
| `--allow-downgrade` | consentire una versione inferiore |
| `--allow-container` | lavorare comunque in un container (l'immagine non viene sostituita) |
| `--no-gh` | non usare il programma `gh`, solo l'API pubblica |
| `--backups` | cartella delle copie (predefinito: update_backups nell'installazione) |
| `--restore-data` | yes, no o auto: cosa fa il ritorno con i dati |
| `--port` | porta della pagina |
| `--no-browser` | non aprire il browser |
| `--tk` | la finestra |
| `--console` | il menu di testo |
| `--lang` | lingua: en es de fr it ja zh pt |

## La tua configurazione e i valori predefiniti che cambiano

- Il registro delle migrazioni (file JSON versionati in ogni release, `assets/migrations/`) dice per ogni versione cosa è cambiato: impostazioni rinominate, rimosse o nuove, nuovi valori predefiniti, file spostati, cambi di comportamento. L'updater applica la catena delle versioni che salti.
- Per impostazione predefinita conserva ciò che hai fissato esplicitamente e adotta un nuovo valore predefinito solo dove non avevi definito nulla. Un cambio di comportamento (per esempio una funzione ora spenta di default) è indicato nel rapporto; `--keep-old-defaults` fissa il vecchio comportamento, `--adopt-new-defaults` porta tutto al nuovo.
- `migrate` lavora su un file singolo: `monitor_updater.py migrate --from 2.0.1 --to 2.0.8 --config mio.json` mostra il risultato e `--apply` lo scrive (dopo una copia). I segreti sono mascherati in ogni rapporto.

## Controlli prima di applicare

- Bloccanti: il monitor è in esecuzione, lo SHA-256 non corrisponde, lo zip non è sicuro, spazio su disco insufficiente, dati di uno schema più recente della destinazione, un container, un altro aggiornamento in sospeso.
- Avvisi: impostazioni che non esistono più o hanno cambiato tipo o intervallo, valori fuori intervallo, chiavi duplicate, una porta occupata da un altro programma, un launcher che hai modificato, un passo che ne richiede un altro prima. Ogni avviso ha un'azione suggerita.

## Sicurezza e via di ritorno

- Ascolta solo su 127.0.0.1 con un token effimero, rifiuta richieste da altri siti, non esegue nulla dello zip, non usa shell e scrive solo dentro l'installazione e la cartella delle copie.
- Prima di cambiare qualcosa copia il pacchetto, la configurazione e i dati; se un passo fallisce la copia viene ripristinata e viene scritto un rapporto. Se fallisce anche il ritorno, la copia resta intatta e il rapporto spiega come ripristinarla a mano.
- Offline: `--zip FILE` con `--sha256` (o un SHA256SUMS accanto). Docker: si aggiorna il volume, l'immagine non viene sostituita dall'interno (`--allow-container` per forzare).
- La pagina mostra le copie e un pulsante **Scarta la copia** per ognuna (chiede prima, e due volte per la copia del ritorno indietro), e un pulsante per leggere tutto il registro del processo dell'ultimo aggiornamento. Scartare elimina solo quella copia, mai l'installazione né i dati, e viene annotato nella cronologia.
- L'aggiornatore indipendente, che funziona senza il monitor, offre lo stesso: la sua pagina nel browser (pulsanti **Copie** e **Registro del processo**, e **Scarta la copia** su ogni copia, con le stesse domande), il suo menu di testo (voci da 7 a 9) e la sua finestra (Tkinter).

## Codici di uscita

| Codice | Significato |
|---|---|
| 0 | fatto, o niente da fare |
| 2 | uso errato |
| 3 | bloccato da un controllo, nulla è cambiato |
| 4 | download, SHA-256 o zip falliti, nulla è cambiato |
| 5 | fallito e stato precedente ripristinato |
| 6 | fallito e fallito anche il ritorno: ripristina la copia a mano |
| 7 | nessuna connessione a GitHub e nessuno zip |
| 8 | non confermato |

## L'avviso nomina il comando del tuo modo di installare

L'avviso di una versione più recente (console, Informazioni, `/api/about`) dice ora il comando esatto del modo in cui è stato installato questo monitor, nel campo `command` accanto a `channel`: il prodotto decompresso (`py -3 monitor/bin/monitor_cli.py update`), un gestore di servizi (`... update apply --systemd-unit <unità>`), un container (`docker pull ghcr.io/juanenrac/tools-github-actions-monitor:<versione>`), pipx, uv o un'estensione del comando `gh`. L'avviso non esegue nulla.
## Protezioni dell'assistente di servizio

Con `updates.systemd_helper` (o `--systemd-unit`) l'aggiornatore controlla ora il servizio prima di toccarlo: un'unità la cui directory di lavoro e il cui comando non puntano a QUESTA cartella appartiene a un'altra installazione e non viene né fermata né avviata; un'unità non viene avviata finché qualcos'altro (un monitor in primo piano) risponde sulla sua porta; un riavvio non è dato per fatto finché il processo è ancora quello vecchio (l'unità deve mostrare un nuovo PID); e `update status --systemd-unit UNITÀ` elenca solo gli errori del servizio dall'ultimo avvio. Sono domande di sola lettura a `systemctl --user show` e `journalctl --user`; una domanda senza risposta non blocca nulla.
