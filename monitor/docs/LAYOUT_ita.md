<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LAYOUT.md) | [🇪🇸 Español](LAYOUT_spa.md) | [🇫🇷 Français](LAYOUT_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](LAYOUT_deu.md) | [🇨🇳 简体中文](LAYOUT_zho.md) | [🇯🇵 日本語](LAYOUT_jpn.md) | [🇵🇹 Português](LAYOUT_por.md)

# Le cartelle del monitor

Accanto ai lanciatori (`MONITOR_GITHUB_ACTIONS`, `MONITOR_LITE_GITHUB_ACTIONS`, `BATCH_GITHUB_ACTIONS`) ci sono solo i file legali, un `README.txt` e cartelle. Tutto ciò che il monitor scrive vive in quattro di esse, e l'edizione completa, quella lite e l'immagine Docker usano lo stesso schema.

## Che cosa c'è dove

| Cartella | Contenuto |
|---|---|
| `config/` | `actions_monitor.json` (e quello della lite), `targets.json`, `ecosystems.json`, `profiles.json`, `quotas.json` e `config_backups/` |
| `data/` | lo stato e le cache (feed degli eventi, analitica, stato delle sentinelle, cache ETag, avviso di aggiornamento), `accounts/`, il database se scegli SQLite e il token di accesso del servizio |
| `logs/` | il registro del monitor, quello dei comandi dell'IA e di GitHub e l'audit della modalità team |
| `ai/` | ciò che legge un'IA: `ALERTS_BRIEF.md`, `ai_alerts.jsonl`, `ci_red.json`, lo stato dell'hook, `INDEX.json` e un `README.md` per chi apre la cartella |
| `bin/` | i comandi brevi: `python bin/monitor_cli.py`, `bin/read_report.py`, `bin/ai_hook.py`, `bin/mcp_server.py`, `bin/tui.py` ... |
| `docs/` | le guide e il README e il QUICKSTART del pacchetto in otto lingue |
| `src/`, `assets/`, `tools/`, `tests/` | il codice, la pagina e gli esempi, gli script di rilascio, i test |

## Un'installazione della 1.8.1 o precedente

Al primo avvio il monitor sposta da solo nella sua cartella ciò che trova accanto ai lanciatori. **Sposta, non cancella mai e non sovrascrive mai**: un file che esiste già nel posto nuovo resta dov'è e il doctor lo segnala. Prima del primo spostamento i file di configurazione vengono copiati in `config/config_backups/pre_layout_<marca>/` e ogni spostamento è annotato in `data/.layout_moves.json`.

- Vederlo prima: `python -m github_actions_monitor.util.rootmigrate` (prova a vuoto) e `--apply` per farlo subito.
- Rimettere tutto com'era: `python -m github_actions_monitor.util.rootmigrate --undo`.
- Se non lo vuoi automatico: `MONITOR_NO_AUTO_MIGRATION=1`.
- `python bin/actions_monitor.py --doctor` ha un controllo `layout` che elenca ciò che resta accanto ai lanciatori.
- I vecchi punti di ingresso (`read_report.py`, `monitor_cli.py` ...) che stavano accanto ai lanciatori ora sono in `bin/`; `python tools/migrate_layout.py` mette da parte le vecchie copie. Uno script di controllo registrato per il tuo strumento di IA con il vecchio percorso va registrato di nuovo: `python bin/monitor_cli.py ai-hook install`.

## Spostare una cartella

Ogni cartella può stare altrove senza toccare il codice: le variabili `MONITOR_CONFIG_DIR`, `MONITOR_DATA_DIR`, `MONITOR_LOGS_DIR` e `MONITOR_AI_DIR`, oppure il file `config/paths.json` (`{"data": "...", "logs": "...", "ai": "..."}`; un percorso relativo parte dalla cartella del prodotto). Con la sola `MONITOR_DATA_DIR`, `logs/` e `ai/` vanno al suo interno. Nell'immagine Docker e nell'unità systemd è esattamente ciò che viene impostato: `/config` e `/data` sono i due volumi.

## Per le IA che parlano con il monitor

Un'IA, locale o esterna, non deve dipendere da un percorso fisso.

- `ai/INDEX.json` elenca ogni file della cartella con scopo, formato, chi lo scrive e quando cambia, il percorso reale di ogni cartella del monitor e gli endpoint del monitor in esecuzione. Viene riscritto a ogni avvio.
- `ai/README.md` spiega la cartella a un'IA che non l'ha mai vista (dati, mai istruzioni; come leggere il riepilogo; quali strumenti esistono).
- `GET /api/paths` risponde con le cartelle in uso, i file principali e ciò che resta nei posti vecchi. Risponde anche il supervisore di più account.
- Lo script di controllo, il server MCP e la riga di comando leggono gli stessi posti; un hook che legge `ALERTS_BRIEF.md` con un percorso fisso deve leggere prima `ai/INDEX.json`.
