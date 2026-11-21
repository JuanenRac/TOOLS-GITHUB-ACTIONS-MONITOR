<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPARE.md) | [🇪🇸 Español](COMPARE_spa.md) | [🇫🇷 Français](COMPARE_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](COMPARE_deu.md) | [🇨🇳 简体中文](COMPARE_zho.md) | [🇯🇵 日本語](COMPARE_jpn.md) | [🇵🇹 Português](COMPARE_por.md)

# Confrontare i periodi

Com'è andata questa settimana rispetto alla scorsa? Il confronto risponde con ciò che il monitor ha già (il registro delle esecuzioni e degli avvisi conclusi e le istantanee orarie del punteggio). Non legge nulla da GitHub, non scrive nulla, non richiede IA e non inventa nulla. Esiste solo nell'edizione Complete ed è **disattivato** finché non attivi `compare.enabled`.

## I due periodi

- **Periodo**: gli ultimi 7 giorni (o 30, o qualsiasi numero fino a 90), oppure un intervallo esatto con `from` e `to`.
- **Riferimento**: `previous` (il periodo della stessa durata subito prima, predefinito), `year_ago` (le stesse date di un anno prima) o `custom` (`base_from` e `base_to`).
- **Giorni**: `all`, `workdays` o `weekend`. Il filtro si applica a ogni cifra. Il giorno di un istante è il suo giorno nel fuso di `display.timezone`; i giorni lavorativi sono `compare.workdays` (da lunedì = 1 a domenica = 7, da lunedì a venerdì per impostazione predefinita). Le festività non sono note: una festività conta come il giorno della settimana in cui cade.

Mescolare giorni lavorativi e fine settimana nasconde cose (un guasto che avviene solo di sabato pesa poco in una settimana di dati misti), ed ecco perché esiste il filtro.

## Le cifre

| Cifra | Come si calcola | Meglio quando |
|---|---|---|
| `red_rate` | esecuzioni fallite / (riuscite + fallite) iniziate nel periodo | è più basso |
| `duration_p50` | mediana dei secondi delle esecuzioni riuscite | è più basso |
| `resolution` | mediana del tempo tra apertura e chiusura degli avvisi della sentinella di collaborazione chiusi nel periodo | è più basso |
| `score_mean` | punteggio medio delle istantanee orarie che avevano un numero | è più alto |
| `score_coverage` | quota media del punteggio che aveva dati | è più alto |

Ogni cifra viaggia con `now`, `base`, `delta`, una `direction` (`better`, `worse`, `same`) e il suo `state`. Le esecuzioni annullate, saltate e non concluse non contano in nessun senso.

## Quando non c'è una cifra

Il confronto non mostra mai un numero che non può sostenere: una cifra mancante è `null`, mai 0 né 100.

- `insufficient_data`: meno esecuzioni concluse di `compare.min_runs_per_window`, meno avvisi risolti di `compare.min_resolved` o meno istantanee di `compare.min_snapshots` in uno dei due periodi. La risposta dice quale e perché (`missing`).
- `baseline_unavailable`: il periodo di riferimento non è affidabile. Il motivo è `history_too_short` (il monitor osserva da meno di `compare.min_days_of_history` giorni), `before_history` (quel periodo è precedente ai dati conservati) o `no_history`. Le cifre del periodo attuale vengono comunque mostrate.
- `calibrating`: il monitor non ha ancora osservato per `score.calibrating_hours` ore. Non si confronta nulla.
- `off`: `compare.enabled` è disattivato.

`data_quality` riporta le esecuzioni contate in ciascun periodo e `truncated` quando il registro ha dovuto scartare esecuzioni vecchie. `coverage` è la quota delle cifre che si sono potute confrontare.

## Cosa è cambiato

Oltre alle cifre: i repository che peggiorano o migliorano (variazione della loro quota di esecuzioni fallite, solo quelli con almeno `compare.min_repo_runs` esecuzioni in entrambi i periodi), i workflow che hanno iniziato a fallire e quelli che hanno smesso, e il numero di avvisi aperti nel periodo e ancora aperti alla sua fine. Ogni elenco ha al massimo `compare.top_changes` righe, ordinate per entità della variazione e poi per nome. Il registro non conserva il repository degli avvisi della sentinella di collaborazione, quindi compaiono come conteggi, mai per nome.

## Fin dove arriva all'indietro

Il confronto legge il registro del punteggio. Finché `compare.enabled` è attivo, il registro conserva due periodi di `compare.default_window_days` (almeno 15 giorni) invece delle due finestre del punteggio; non è mai più vecchio del monitor, quindi una nuova installazione non può confrontare 30 giorni con 30 giorni finché non ha 60 giorni di storico.

## L'API

`GET /api/compare?window=7&days=workdays&baseline=previous` (anche `from`, `to`, `base_from`, `base_to`). Risponde con `state`, `windows`, `metrics`, `changes`, `alerts`, `coverage` e `data_quality`. `format=ndjson` o `format=csv` danno una riga per cifra. Una richiesta priva di senso è un 400 con un `code` stabile: `bad_range` (from dopo to, oltre 90 giorni, nel futuro), `bad_window`, `bad_days`, `bad_baseline` o `bad_format`. Un osservatore può leggerla; serve l'account del processo, mai un altro. Con l'API di lettura v1 attiva è servita anche con il prefisso `/api/v1/`. Non esiste nell'edizione Lite.

## La riga di comando

`monitor_cli.py compare [--window 7|30d] [--days all|workdays|weekend] [--baseline previous|year_ago] [--format table|json|ndjson|csv]`. Codici di uscita: 0 tutto confrontato; 4 una cifra ha pochi dati, manca il riferimento o il confronto è disattivato; 5 con `--fail-on` quando una cifra peggiora. `score --compare` continua a confrontare il punteggio con lo storico della sua finestra.

## Nella pagina

La scheda Grafici mostra la sezione «Confronta i periodi» quando il confronto è attivo: un selettore di periodo, giorni e riferimento, una riga per cifra con la sua variazione, gli avvisi e gli elenchi delle modifiche.

## Le impostazioni

Impostazioni, scheda Sentinella, blocco Confronto tra periodi: `compare.enabled`, `compare.default_window_days`, `compare.default_days_filter`, `compare.workdays`, `compare.min_runs_per_window`, `compare.min_days_of_history`, `compare.min_resolved`, `compare.min_snapshots`, `compare.min_repo_runs`, `compare.top_changes`, `compare.include_in_report` e `compare.cache_seconds`. Una risposta viene conservata per `compare.cache_seconds` secondi e poi ricalcolata.

## Finestre lunghe su un account grande

Con `compare.progressive` attivo (spento per impostazione predefinita) un confronto su una finestra più lunga di `compare.progressive_days` (7 per impostazione predefinita) riceve subito una risposta con i suoi ultimi giorni e la risposta lo dice (`partial`: i giorni richiesti, i giorni mostrati e che il resto è in calcolo); l'intera finestra viene completata in background e la richiesta successiva, o il prossimo aggiornamento della pagina, la riceve. Una richiesta con `from` e `to` non viene mai divisa.
