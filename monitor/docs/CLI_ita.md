<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI.md) | [🇪🇸 Español](CLI_spa.md) | [🇫🇷 Français](CLI_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](CLI_deu.md) | [🇨🇳 简体中文](CLI_zho.md) | [🇯🇵 日本語](CLI_jpn.md) | [🇵🇹 Português](CLI_por.md)

# La riga di comando come client del monitor

`python monitor_cli.py COMANDO` chiede al monitor in esecuzione ciò che sa (un `GET` su `127.0.0.1`, o sull'indirizzo di `--url` / `MONITOR_URL`) e lo stampa. Non ripete il lavoro della pagina verso GitHub, non scrive mai su GitHub e non cambia nessuna impostazione. Gli strumenti precedenti (`read_report.py`, `--doctor`, `gha_dispatch_all.py`) continuano a funzionare come prima.

## Comandi

| Comando | Cosa mostra | Lite |
|---|---|---|
| `status` | versione, edizione, account, repository, cosa gira e cosa fallisce, la quota | sì |
| `health` (o `check`) | un controllo rapido prima di leggere qualcosa di pesante: il monitor è raggiungibile, accetta questo client, l'accesso GitHub dell'account risponde? | sì |
| `doctor` | i controlli di `--doctor` per questa installazione (il monitor non deve essere in esecuzione) | sì |
| `accounts` | gli account del supervisore (solo con più account) | no |
| `alerts` | gli avvisi di tutte le sentinelle in un elenco: `--sentinel ci\|collab`, `--level info\|warning\|error`, `--muted show\|hide\|only` | no |
| `live` | lo stato del ricevitore del webhook e gli ultimi eventi | no |

Opzioni di tutti i comandi: `--json` (la risposta come un documento JSON: `{"ok", "exit", "data"}`), `--account ID`, `--url URL`, `--lite` (porta 8766), `--timeout SECONDI` (da 1 a 60), `--lang CODICE`. In modalità di rete metti il token di accesso nella variabile d'ambiente `MONITOR_ACCESS_TOKEN`, quella che legge il monitor stesso (`MONITOR_TOKEN` è accettata come alias; `--token TOKEN` è l'ultima risorsa, perché un'opzione compare nell'elenco dei processi). L'ordine: `MONITOR_ACCESS_TOKEN`, poi `MONITOR_TOKEN`, poi `--token`. Viaggia nell'intestazione `X-Monitor-Access`, mai nell'indirizzo e mai a schermo. Un `--url` in `http` non cifrato verso un altro computer stampa un avviso su stderr (il token e le risposte viaggerebbero in chiaro): usa `https` fuori da una rete che controlli.

Gli orari scritti per le persone (la riga `Last read`, i silenziamenti, il registro, i rapporti, le notifiche) usano il fuso di questo computer e lo nominano, con l'ora UTC accanto (`11:43:07 CET (10:43:07 UTC)`). Un altro fuso si sceglie con `display.timezone` (`local`, `utc` o un nome come `Europe/Madrid`; la variabile d'ambiente `MONITOR_TIMEZONE` prevale sul file). `--json` mantiene UTC e aggiunge `updated_local`.

## Codici di uscita (stabili)

| Codice | Significato |
|---|---|
| 0 | tutto a posto |
| 1 | uso errato del comando (anche `--lite` con un comando che richiede l'edizione completa) |
| 2 | il monitor non è raggiungibile |
| 3 | il monitor rifiuta questo client, oppure l'accesso GitHub dell'account è fallito o scaduto (un problema di credenziale, non una quota esaurita) |
| 4 | il monitor risponde ma è degradato: offline, quota esaurita, ancora senza dati, un endpoint che non ha, o una risposta che non è JSON |
| 5 | `alerts --fail-on LIVELLO` ha trovato un avviso aperto di quel livello o peggiore (uno silenziato non conta) |

## Esempi

```
python monitor_cli.py health && python monitor_cli.py alerts --fail-on error
python monitor_cli.py alerts --sentinel collab --level warning --json
python monitor_cli.py status --account org-acme
MONITOR_URL=http://192.168.0.20:8765 MONITOR_ACCESS_TOKEN=... python monitor_cli.py health --json
```

`health` distingue tre cose: il monitor non risponde (2), l'accesso a GitHub fallisce (3) e la quota è esaurita o GitHub non è raggiungibile (4); un monitor che non ha finito la prima lettura lo dice (4) invece di mostrare cifre vuote.

## L'edizione lite

`python monitor_cli.py status --lite`, `doctor --lite` e `health --lite` parlano con la porta 8766. I comandi che richiedono account, sentinelle o il ricevitore del webhook vengono rifiutati con il codice di uscita 1. L'edizione lite non ha account né API degli avvisi.

## `ai-hook`: dire a uno strumento di IA cosa vede il monitor

`python monitor_cli.py ai-hook install|status|uninstall [--assistant|--cursor|--generic] [--scope project|user] [--project-dir DIR] [--dry-run] [--json]` non richiede un monitor in esecuzione. Aggiunge, mostra o rimuove lo script di collegamento `ai_hook.py` nelle impostazioni degli hook di uno strumento di IA (vedi la guida agli avvisi per IA): il file di impostazioni viene unito, si conserva una copia e la risposta di `--json` è ASCII puro. `status` è l'azione predefinita.

## Il token di accesso nella riga di comando

In modalità di rete il token si legge da `MONITOR_ACCESS_TOKEN`, poi `MONITOR_TOKEN`, poi dalla prima riga di `--token-file FILE` (tieni quel file leggibile solo da te: su un sistema con modi di file il comando avvisa se altri possono leggerlo) e infine da `--token`, che compare nell'elenco dei processi e per questo stampa un avviso su stderr.
