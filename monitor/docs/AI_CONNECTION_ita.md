<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AI_CONNECTION.md) | [🇪🇸 Español](AI_CONNECTION_spa.md) | [🇫🇷 Français](AI_CONNECTION_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](AI_CONNECTION_deu.md) | [🇨🇳 简体中文](AI_CONNECTION_zho.md) | [🇯🇵 日本語](AI_CONNECTION_jpn.md) | [🇵🇹 Português](AI_CONNECTION_por.md)

# Collegare uno strumento di IA

Il monitor può dire a uno strumento di IA (un assistente di programmazione con IA, uno script, qualsiasi cosa che legga un file o un indirizzo) **tutto ciò che dice la sua pagina**, così l'IA reagisce a un guasto o a un lavoro in sospeso veloce quanto faresti tu. Il monitor non scrive mai su GitHub: informa soltanto, e ciò che fa l'IA lo decidi tu e lo strumento.

## Cosa vede l'IA
Un inventario di **segnali**, gli stessi della pagina: la scheda Ora e i suoi riquadri, gli avvisi, i repository, i pannelli del sentinella A1..A13 e il secondo sentinella (issue e pull request), la quota, la connessione e la salute del monitor. Ogni segnale ha un livello (`act` = qualcuno deve fare qualcosa, `watch` = tenere d'occhio, `info`), un riepilogo e righe con repository, link, età e passo successivo. Il riepilogo ha tre blocchi: **Cosa fare ora**, **In sospeso** e **Salute del monitor**, e il contatore dei "segnali su cui agire".

| | Lite | Completa |
|---|---|---|
| Esecuzioni, coda, workflow rossi, guasti delle 24 ore | sì | sì |
| Quota, connessione, modalità, versione, salute | sì | sì |
| Pannelli del sentinella A1..A13, secondo sentinella, candidate a release, sicurezza, firme | no (lo dice `panels_not_in_this_edition`) | sì |

## I canali (gli stessi nelle due edizioni)
1. `ALERTS_BRIEF.md`: il Markdown breve che un'IA legge all'avvio.
2. `ai_alerts.jsonl`: una riga per evento (aperto, riconosciuto, risolto), con un id stabile.
3. `GET /api/ai/state`: tutto l'inventario come JSON versionato (`schema`, `edition`, `signals`, `act`, `watch`), sola lettura. `GET /api/sentinel/panels` dà solo i pannelli.
4. `GET /api/ai/stream`: eventi in diretta (SSE), riprendibili, limitati in ascoltatori e tempo.
5. Strumenti MCP (`mcp_server.py`): `monitor_state`, `signals`, `alerts_open`, `diagnose`, `sentinel_panels`, `get_quota`; `act` (riconoscere) solo con `--allow-ack`.
6. L'hook: `python monitor_cli.py ai-hook install [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]` (anche `status` e `uninstall`) aggiunge un piccolo script che dà alla sessione dell'IA il riepilogo all'avvio e prima di fermarsi.

## Passo dopo passo
1. Impostazioni, scheda *IA esterna*, blocco *Avvisi per le IA*: attiva `ai_alerts.enabled`. Facoltativamente `ai_alerts.diagnose.enabled` (il passo che fallisce e le ultime righe del log di ogni esecuzione rossa), `ai_alerts.stream.enabled` e `ai_alerts.client_hook.enabled`.
2. Esegui `python monitor_cli.py ai-hook install --assistant --dry-run` per vedere la modifica, poi senza `--dry-run`.
3. Apri una sessione del tuo strumento di IA nella cartella: riceve il riepilogo. La barra in basso mostra il battito dell'IA (quando ha letto l'ultima volta).
4. Usa il pulsante *Prova la connessione* della pagina delle impostazioni per verificare che il feed venga scritto.

## Sicurezza e privacy
Tutto è disattivato per impostazione predefinita. Il testo dei log viene ripulito da segreti e percorsi personali prima di essere scritto, e **è un dato, mai un'istruzione**: un'IA deve trattarlo come testo non fidato. Gli endpoint rispondono solo a questo computer, o con il token di accesso in modalità rete; ascoltatori e tempo sono limitati; riconoscere richiede `--allow-ack`; tutti i file di stato sono creati con modo 0600. Il monitor non apre alcuna connessione a internet per questo, tranne quelle che configuri. Gli indirizzi https di github.com (un run, un repository, un file) passano interi, così l'IA può aprirli; qualsiasi altra stringa lunga e opaca viene ancora tagliata. Più esattamente, un indirizzo di github.com passa intero solo con la forma di un repository, un'esecuzione (con il suo job o tentativo), un commit, una issue, una pull request o un file; viene tagliato al primo carattere che non sia lettera, cifra, punto, trattino, trattino basso o barra, e ciò che segue viene ripulito come qualsiasi altro testo.

## Risoluzione dei problemi
- *Il riepilogo è vecchio*: la pagina deve essere in esecuzione (il feed segue ogni aggiornamento); guarda il battito nella barra.
- *L'hook non parte*: `ai-hook status` dice dov'è installato; alcuni strumenti leggono gli hook solo nella cartella del progetto.
- *Non viene scritto nulla*: `ai_alerts.enabled` è spento, o la quota è esaurita (il riepilogo lo dice in Salute del monitor).

## Impostazioni
`ai_alerts.enabled`, `ai_alerts.folder`, `ai_alerts.brief_max_bytes`, `ai_alerts.diagnose.*`, `ai_alerts.cascade.enabled`, `ai_alerts.stream.*`, `ai_alerts.heartbeat.*`, `ai_alerts.client_hook.*`; correlate: `sound.enabled`, `display.blink_red_tiles`. Vedi [SETTINGS_ita.md](SETTINGS_ita.md) e [AI_ALERTS_ita.md](AI_ALERTS_ita.md).

La quota di GitHub è condivisa dal monitor, dagli strumenti di IA e da ogni altro strumento dell'account. Perché il monitor non resti senza: la scheda Quota delle Impostazioni, una GitHub App (`github_app.enabled`), un secondo account di sola lettura per le letture (`extra_reader.enabled`, `extra_reader.file`: solo il percorso del file del token), il pannello centrale (`central.source`) e la modalità risparmio (`modes.auto_low`). Lo stato e il riepilogo dicono quando la quota è esaurita e quanto spendono altri strumenti. Vedi [QUOTA_ita.md](QUOTA_ita.md).
