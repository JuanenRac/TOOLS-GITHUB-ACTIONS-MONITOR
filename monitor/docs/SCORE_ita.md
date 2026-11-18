<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCORE.md) | [🇪🇸 Español](SCORE_spa.md) | [🇫🇷 Français](SCORE_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](SCORE_deu.md) | [🇨🇳 简体中文](SCORE_zho.md) | [🇯🇵 日本語](SCORE_jpn.md) | [🇵🇹 Português](SCORE_por.md)

# Il punteggio di un account

Un numero da 0 a 100, una lettera da A a E e una tendenza, per ogni account, costruiti solo con ciò che il monitor già conosce (le esecuzioni concluse e gli avvisi della sentinella di collaborazione). È nell'edizione Complete; Lite non ha punteggio.

## Di cosa è fatto

Una somma ponderata di cinque parti, ciascuna da 0 a 100. Una parte vale 100 al suo limite **buono**, 0 al suo limite **cattivo** ed è lineare nel mezzo. I pesi e i limiti sono impostazioni.

| Parte | Peso | Cosa misura | Buono | Cattivo |
|---|---|---|---|---|
| Affidabilità | 30 | quota delle esecuzioni concluse che riescono (le annullate e le saltate non contano) | 98 % | 50 % |
| Velocità | 15 | 95° percentile della durata delle esecuzioni riuscite | 10 min | 60 min |
| Ripristino | 15 | tempo mediano dal primo errore di un workflow al suo successo successivo; un workflow ancora in rosso conta il tempo per cui è in rosso finora | 30 min | 24 h |
| Collaborazione | 15 | tempo mediano in cui un avviso della sentinella di collaborazione resta aperto fino a sparire | 2 giorni | 14 giorni |
| Sicurezza | 25 | i punti che i rilievi aperti della sentinella di sicurezza tolgono a 100 (solo finché quella sentinella è attiva) | 0 punti | 100 punti |

La lettera è A da 90, B da 80, C da 70, D da 55 ed E sotto. La tendenza confronta il punteggio con la finestra immediatamente precedente: in salita, in discesa o stabile (una variazione inferiore a `score.trend_flat` punti è stabile).

## Quando non c'è un numero

Il punteggio non mostra mai un numero che non può sostenere. La risposta porta sempre il suo `state`, la sua `coverage` e la sua `data_quality`:

- **calibrating** (calibrazione): l'account è osservato da meno di `score.calibrating_hours` (24 per impostazione predefinita). Né numero né lettera.
- **insufficient_data** (dati insufficienti): meno di `score.min_runs` esecuzioni concluse nella finestra (20 per impostazione predefinita), oppure le parti con dati pesano meno di `score.min_coverage` del totale (metà per impostazione predefinita). Nessun numero.
- **scored** (valutato): un numero, una lettera e una tendenza. Una parte senza dati viene lasciata fuori e le altre vengono riscalate; questo abbassa la `coverage` (per esempio 0,85 con la sentinella di collaborazione spenta). Non conta mai come 0 né come 100.

La sicurezza è una parte come le altre, ma ha dati solo finché la sentinella di sicurezza è attiva e ha guardato abbastanza repository. Senza di essa la risposta dice `complete: false` ed elenca `security` in `missing_parts`, e le altre parti vengono riscalate: il numero non si legge mai come «tutto a posto». GitHub non dà uno storico dei rilievi, quindi la parte di sicurezza è la stessa nella finestra e in quella precedente: la tendenza mostra ciò che hanno fatto la CI e la collaborazione. I pesi sono 30, 15, 15, 15 e 25 per impostazione predefinita. Una finestra con esecuzioni e nessun errore non ha nulla da ripristinare: la sua parte di ripristino è piena, come un fatto e non come una lacuna.

Un workflow ancora in rosso alla fine della finestra non viene dimenticato: la parte di ripristino conta il tempo per cui è in rosso finora, un limite inferiore che cresce finché il rosso dura; un errore che nessuno corregge abbassa quindi il numero ogni ora di più. Un errore corretto conta il suo tempo reale. Una riesecuzione di un'esecuzione conta come un'esecuzione in più del workflow, così si vedono sia il primo tentativo fallito sia il secondo in verde. Se aggiorni da una versione precedente, i numeri di un account con un workflow in rosso possono essere più bassi di prima. Quando nessuna parte ha dati, la risposta è `insufficient_data` con il motivo `no_data`. Il registro conserva al massimo 20000 esecuzioni: quando ha dovuto scartarne di appartenenti alla finestra attuale, `data_quality.truncated` è vero e `truncated` è tra i motivi, così che un tasso di successo che vede solo una parte della finestra non venga preso per completo. In `GET /api/score/global` un account con istantanea scaduta resta fuori dalla media e viene contato in `accounts_stale`, e `/metrics` non esporta `ghamon_score` per un'istantanea scaduta.

Nemmeno un guasto che attraversa il bordo della finestra viene dimenticato: la parte di recupero conta il tratto del rosso che cade nella finestra (la finestra precedente ha contato il proprio tratto, nessun giorno è contato due volte), e il registro conserva l'ultimo guasto di un workflow che nessuno ha riparato finché la regola del rosso lo mostra ancora (`ci.red_age_days`). Allo stesso modo un avviso della sentinella di collaborazione ancora aperto alla fine della finestra conta con il tempo trascorso da quando è aperto, un limite inferiore: lasciare avvisi irrisolti abbassa quindi la parte collaborazione invece di lasciarla senza dati. Se aggiorni da una versione precedente, i punteggi possono essere più bassi di prima.

Un repository non è sano perché non ha nulla da mostrare. Ogni repository osservato è *attivo* (un'esecuzione propria più recente di `ci.inactive_days` giorni), *dormiente* (non ha mai eseguito nulla di proprio) o *inattivo* (la sua esecuzione più recente è più vecchia): i repository dormienti e inattivi non sono né verdi né rossi e vengono contati a parte (`activity` dell'istantanea, le cifre `dormant` e `inactive_repos`, il suggerimento del chip), così un account con centinaia di fork non mostra un punteggio fatto di niente. Un repository che il monitor non ha potuto leggere è *sconosciuto*, mai dormiente. `ci.dormant_repos` disattiva il conteggio.

## La finestra

La finestra è il numero di giorni di esecuzioni che il punteggio guarda: `score.window_days`, 7 per impostazione predefinita, scelto dall'utente per ogni account. La finestra immediatamente precedente, della stessa durata, dà la tendenza. Il monitor tiene un piccolo registro delle esecuzioni concluse che ha visto, quindi la finestra può essere più lunga dell'elenco delle ultime esecuzioni mostrato dalla pagina. Un'istantanea viene salvata ogni ora e conservata quanto lo storico delle analisi (`retention.analytics_days`).

## Per repository e per account

Ogni account ha il proprio punteggio. Il dettaglio lo scompone per repository (solo le parti di CI, i peggiori per primi). Non esiste un numero unico per l'intera installazione. Solo a titolo informativo, `GET /api/score/global` del supervisore dà la media degli account valutati che chi chiede può vedere, ponderata per i loro repository con un numero e sempre con quanti account ne fanno parte; un account senza numero è elencato e lasciato fuori.

## Nella pagina

Una pastiglia nell'intestazione, accanto alle pastiglie di preparazione, mostra il punteggio: il numero, la lettera, una freccia con la variazione rispetto alla finestra precedente e una piccola linea degli ultimi giorni. Il suo colore segue la lettera (A e B verde, C ambra, D ed E rosso). Finché non c'è un numero è neutra e dice perché (calibrazione, dati insufficienti). Una stella dopo la lettera significa che una parte non è ancora conteggiata (oggi, la sicurezza): un numero alto non significa allora che sia tutto a posto. Al passaggio del mouse mostra la copertura, le parti con i loro pesi e il repository più debole. La pastiglia non compare in Lite né con il punteggio spento (`score.enabled`). Durante la calibrazione la pastiglia dice quanto manca di `score.calibrating_hours` (`data_quality.calibrating_hours`), con una barra e il giorno e l'ora in cui comparirà il numero; con dati insufficienti dice quale condizione non è soddisfatta (esecuzioni o copertura), e il suggerimento spiega anche perché una parte non conta (una sentinella spenta, che non ha finito la prima scansione o che ha letto troppo pochi repository).

## Per altri strumenti

Le metriche (`/metrics`, con l'uscita Prometheus attiva) portano tre serie senza etichette: `ghamon_score_scored` (1 quando l'account ha un numero), `ghamon_score_coverage` (la quota dei pesi con dati, da 0 a 1) e `ghamon_score` (il numero, solo quando c'è: non viene mai esportato come 0 quando manca). Il server MCP ha uno strumento di sola lettura `get_score` con la risposta dell'API. `--demo` mostra un punteggio inventato e non scrive nulla. La dashboard Grafana di esempio (`docs/grafana/monitor_dashboard.json`) ha un pannello del punteggio e uno del punteggio nel tempo.

## L'API

`GET /api/score` risponde con l'ultima istantanea dell'account: `state`, `score`, `letter`, `trend`, `parts`, `coverage`, `data_quality`, `complete`, `missing_parts`, `repos`, `age_seconds` e `stale` (vero se l'istantanea ha più di tre ore). `GET /api/score/history` risponde con i punti nel tempo, dal più vecchio al più recente (`?hours=` all'indietro da adesso, al massimo 90 giorni, e `?limit=`, al massimo 2000). Un numero assente è `null`, mai 0. Nella modalità squadra chi può vedere l'account può leggerne il punteggio; i pesi e i limiti sono impostazioni che solo un amministratore cambia.

## L'avviso in caso di calo

Quando il punteggio cala di `score.alert.drop_points` punti (10 per impostazione predefinita) o più rispetto alla finestra precedente, o passa a una lettera inferiore, la scheda Avvisi mostra l'avviso `score.dropped` (un avvertimento; critico se la lettera è E), con il punteggio vecchio e quello nuovo. Resta finché l'istantanea mostra il calo e sparisce quando il punteggio si riprende; si può silenziare come qualsiasi altro avviso. È attivo per il pannello per impostazione predefinita. Esce dai canali di notifica esterni (evento `score_dropped`) solo se `score.alert.notify_external` è attivo, il che non accade per impostazione predefinita, e solo nel momento in cui compare. `score.alert.enabled` disattiva l'avviso.

## Le impostazioni

Nella pagina Impostazioni, sotto-scheda Sentinella, blocchi Punteggio dell'account, Pesi del punteggio e Lettere del punteggio: `score.enabled`, `score.window_days`, `score.calibrating_hours`, `score.min_runs`, `score.min_coverage`, `score.trend_flat`, `score.weights.reliability`, `score.weights.speed`, `score.weights.recovery`, `score.weights.collaboration`, `score.weights.security`, da `score.grades.A` a `score.grades.D`, `score.alert.enabled`, `score.alert.drop_points` e `score.alert.notify_external` (spento per impostazione predefinita). I limiti buono e cattivo di ogni parte si leggono dal file, sotto `score.limits` (vedi il file di esempio); non si modificano nella pagina.

## Rispetto al periodo precedente

Il confronto tra periodi (`GET /api/compare`, `monitor_cli.py compare`) mette il punteggio medio, la quota di esecuzioni fallite, le durate e il tempo di risoluzione degli avvisi di un periodo a confronto con il precedente, con lo stesso registro e le stesse istantanee orarie del punteggio. È disattivato per impostazione predefinita (`compare.enabled`) e dice `insufficient_data` o `baseline_unavailable` invece di inventare un numero. Vedi [COMPARE_ita.md](COMPARE_ita.md).
