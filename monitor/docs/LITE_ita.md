<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](LITE.md) | [🇪🇸 Español](LITE_spa.md) | [🇫🇷 Français](LITE_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](LITE_deu.md) | [🇨🇳 简体中文](LITE_zho.md) | [🇯🇵 日本語](LITE_jpn.md) | [🇵🇹 Português](LITE_por.md)

# L'edizione lite

Un secondo prodotto, più semplice, nello stesso pacchetto: la pagina di ciò che è in corso e di ciò che fallisce, senza la sentinella. Per chi vuole solo osservare i propri run.

|  | Completa | Lite |
|---|---|---|
| Avvio | `MONITOR_GITHUB_ACTIONS` (`.bat` / `.sh` / `.command`) | `MONITOR_LITE_GITHUB_ACTIONS` (gli stessi tre) |
| Porta | 8765 | 8766 |
| Schede | Adesso, Sentinella, Grafici, Repository, Cronologia, Impostazioni | Adesso, Grafici, Repository, Cronologia, Impostazioni brevi |
| Intestazione | tutte le tessere, prontezza, firma | in corso, in coda, fallimenti e successi di 24 h, minuti di calcolo, issue, rossi su main, repository, quota, connessione |
| Sentinella (avvisi, release, coda di firma, prontezza, linter) | sì | no: non viene nemmeno importata |
| Analisi, notifiche, webhook, IA, uscite Prometheus / Grafana | sì, spente finché non le attivi | no: quei percorsi rispondono 404 |
| Configurazione | `actions_monitor.json` | `actions_monitor_lite.json` (creato al primo avvio; la sentinella vi è spenta) |
| File di stato | `etag_cache.json`, `analytics_history.json`... | gli stessi nomi con il suffisso `_lite` |

Come avviarla: `MONITOR_LITE_GITHUB_ACTIONS.bat` su Windows, `./MONITOR_LITE_GITHUB_ACTIONS.sh` su Linux, doppio clic su `MONITOR_LITE_GITHUB_ACTIONS.command` su macOS, oppure `python bin/actions_monitor.py --lite` (anche `MONITOR_MODE=lite`). Ascolta su `127.0.0.1:8766`, quindi la completa può girare nello stesso tempo.

Le Impostazioni brevi hanno l'account (`github_owner`), i repository e gli ecosistemi da osservare (`repos`, `ecosystems`, `exclude`), il tempo di aggiornamento (`refresh_seconds`), la lingua e il tema. «Rossi su main» conta i workflow il cui ultimo run terminato è fallito. Per avere poi la sentinella e il resto, avvia la completa: non c'è nulla da migrare. Al primo avvio, `actions_monitor_lite.json` copia da `actions_monitor.json` (se esiste) l'account, i repository e gli ecosistemi da osservare, i file di catalogo e la lingua, e lo dice sulla console; non copia mai la sentinella, l'IA, il webhook, le uscite né le notifiche. Senza quel file osserva tutti gli ecosistemi (`"ecosystems": "all"`). Il browser ricorda il tema separatamente per ogni porta. L'edizione lite non scrive `ci_red.json` né coda di firma e tiene i propri file di stato; se mai dai a entrambe le edizioni un `sentinel.ci_red_file`, non puntarle allo stesso file.

## La riga di comando

`python bin/monitor_cli.py status --lite`, `doctor --lite` e `health --lite` interrogano il monitor lite sulla porta 8766 (vedi [CLI_ita.md](CLI_ita.md)); i comandi che richiedono account o sentinelle vengono rifiutati. Anche la pagina ha la barra di stato a piè di pagina e le tabelle ordinabili.

## Archiviazione

L'edizione lite conserva solo file semplici: nessun database, nessuna attività di conservazione e nessuna delle opzioni di [STORAGE_ita.md](STORAGE_ita.md).
