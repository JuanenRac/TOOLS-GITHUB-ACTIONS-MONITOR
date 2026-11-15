<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCORE.md) | [🇪🇸 Español](SCORE_spa.md) | [🇫🇷 Français](SCORE_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](SCORE_deu.md) | [🇨🇳 简体中文](SCORE_zho.md) | [🇯🇵 日本語](SCORE_jpn.md) | [🇵🇹 Português](SCORE_por.md)

# Il punteggio di un account

Un numero da 0 a 100, una lettera da A a E e una tendenza, per ogni account, costruiti solo con ciò che il monitor già conosce (le esecuzioni concluse e gli avvisi della sentinella di collaborazione). È nell'edizione Complete; Lite non ha punteggio.

## Di cosa è fatto

Una somma ponderata di quattro parti, ciascuna da 0 a 100. Una parte vale 100 al suo limite **buono**, 0 al suo limite **cattivo** ed è lineare nel mezzo. I pesi e i limiti sono impostazioni.

| Parte | Peso | Cosa misura | Buono | Cattivo |
|---|---|---|---|---|
| Affidabilità | 40 | quota delle esecuzioni concluse che riescono (le annullate e le saltate non contano) | 98 % | 50 % |
| Velocità | 20 | 95° percentile della durata delle esecuzioni riuscite | 10 min | 60 min |
| Ripristino | 20 | tempo mediano dal primo errore di un workflow al suo successo successivo | 30 min | 24 h |
| Collaborazione | 20 | tempo mediano in cui un avviso della sentinella di collaborazione resta aperto fino a sparire | 2 giorni | 14 giorni |

La lettera è A da 90, B da 80, C da 70, D da 55 ed E sotto. La tendenza confronta il punteggio con la finestra immediatamente precedente: in salita, in discesa o stabile (una variazione inferiore a `score.trend_flat` punti è stabile).

## Quando non c'è un numero

Il punteggio non mostra mai un numero che non può sostenere. La risposta porta sempre il suo `state`, la sua `coverage` e la sua `data_quality`:

- **calibrating** (calibrazione): l'account è osservato da meno di `score.calibrating_hours` (24 per impostazione predefinita). Né numero né lettera.
- **insufficient_data** (dati insufficienti): meno di `score.min_runs` esecuzioni concluse nella finestra (20 per impostazione predefinita), oppure le parti con dati pesano meno di `score.min_coverage` del totale (metà per impostazione predefinita). Nessun numero.
- **scored** (valutato): un numero, una lettera e una tendenza. Una parte senza dati viene lasciata fuori e le altre vengono riscalate; questo abbassa la `coverage` (per esempio 0,8 con la sentinella di collaborazione spenta). Non conta mai come 0 né come 100.

La sicurezza non è ancora una parte. Finché non lo sarà, ogni risposta dice `complete: false` ed elenca `security` in `missing_parts`, così un 85 non si legge mai come «tutto a posto».

## La finestra

La finestra è il numero di giorni di esecuzioni che il punteggio guarda: `score.window_days`, 7 per impostazione predefinita, scelto dall'utente per ogni account. La finestra immediatamente precedente, della stessa durata, dà la tendenza. Il monitor tiene un piccolo registro delle esecuzioni concluse che ha visto, quindi la finestra può essere più lunga dell'elenco delle ultime esecuzioni mostrato dalla pagina. Un'istantanea viene salvata ogni ora e conservata quanto lo storico delle analisi (`retention.analytics_days`).

## Per repository e per account

Ogni account ha il proprio punteggio. Il dettaglio lo scompone per repository (solo le parti di CI, i peggiori per primi). Non esiste un numero unico per l'intera installazione. Solo a titolo informativo, `GET /api/score/global` del supervisore dà la media degli account valutati che chi chiede può vedere, ponderata per i loro repository con un numero e sempre con quanti account ne fanno parte; un account senza numero è elencato e lasciato fuori.

## Nella pagina

Una pastiglia nell'intestazione, accanto alle pastiglie di preparazione, mostra il punteggio: il numero, la lettera, una freccia con la variazione rispetto alla finestra precedente e una piccola linea degli ultimi giorni. Il suo colore segue la lettera (A e B verde, C ambra, D ed E rosso). Finché non c'è un numero è neutra e dice perché (calibrazione, dati insufficienti). Una stella dopo la lettera significa che una parte non è ancora conteggiata (oggi, la sicurezza): un numero alto non significa allora che sia tutto a posto. Al passaggio del mouse mostra la copertura, le parti con i loro pesi e il repository più debole. La pastiglia non compare in Lite né con il punteggio spento (`score.enabled`).

## Per altri strumenti

Le metriche (`/metrics`, con l'uscita Prometheus attiva) portano tre serie senza etichette: `ghamon_score_scored` (1 quando l'account ha un numero), `ghamon_score_coverage` (la quota dei pesi con dati, da 0 a 1) e `ghamon_score` (il numero, solo quando c'è: non viene mai esportato come 0 quando manca). Il server MCP ha uno strumento di sola lettura `get_score` con la risposta dell'API. `--demo` mostra un punteggio inventato e non scrive nulla. La dashboard Grafana di esempio (`docs/grafana/monitor_dashboard.json`) ha un pannello del punteggio e uno del punteggio nel tempo.

## L'API

`GET /api/score` risponde con l'ultima istantanea dell'account: `state`, `score`, `letter`, `trend`, `parts`, `coverage`, `data_quality`, `complete`, `missing_parts`, `repos`, `age_seconds` e `stale` (vero se l'istantanea ha più di tre ore). `GET /api/score/history` risponde con i punti nel tempo, dal più vecchio al più recente (`?hours=` all'indietro da adesso, al massimo 90 giorni, e `?limit=`, al massimo 2000). Un numero assente è `null`, mai 0. Nella modalità squadra chi può vedere l'account può leggerne il punteggio; i pesi e i limiti sono impostazioni che solo un amministratore cambia.

## L'avviso in caso di calo

Quando il punteggio cala di `score.alert.drop_points` punti (10 per impostazione predefinita) o più rispetto alla finestra precedente, o passa a una lettera inferiore, la scheda Avvisi mostra l'avviso `score.dropped` (un avvertimento; critico se la lettera è E), con il punteggio vecchio e quello nuovo. Resta finché l'istantanea mostra il calo e sparisce quando il punteggio si riprende; si può silenziare come qualsiasi altro avviso. È attivo per il pannello per impostazione predefinita. Esce dai canali di notifica esterni (evento `score_dropped`) solo se `score.alert.notify_external` è attivo, il che non accade per impostazione predefinita, e solo nel momento in cui compare. `score.alert.enabled` disattiva l'avviso.

## Le impostazioni

Nella pagina Impostazioni, sotto-scheda Sentinella, blocchi Punteggio dell'account, Pesi del punteggio e Lettere del punteggio: `score.enabled`, `score.window_days`, `score.calibrating_hours`, `score.min_runs`, `score.min_coverage`, `score.trend_flat`, `score.weights.reliability`, `score.weights.speed`, `score.weights.recovery`, `score.weights.collaboration`, da `score.grades.A` a `score.grades.D`, `score.alert.enabled`, `score.alert.drop_points` e `score.alert.notify_external` (spento per impostazione predefinita). I limiti buono e cattivo di ogni parte si leggono dal file, sotto `score.limits` (vedi il file di esempio); non si modificano nella pagina.
