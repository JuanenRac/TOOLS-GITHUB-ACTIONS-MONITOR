<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](EXTRAS.md) | [🇪🇸 Español](EXTRAS_spa.md) | [🇫🇷 Français](EXTRAS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](EXTRAS_deu.md) | [🇨🇳 简体中文](EXTRAS_zho.md) | [🇯🇵 日本語](EXTRAS_jpn.md) | [🇵🇹 Português](EXTRAS_por.md)

# Extra facoltativi

Entrambi sono **disattivati per impostazione predefinita** e si attivano nelle Impostazioni.

## Il registro del passo fallito

`logs.failed_step.enabled`: un avviso di un'esecuzione fallita riceve un pulsante **Passo fallito**. Una pressione legge da GitHub i job e il registro di errore di quell'esecuzione (due chiamate della tua quota), mostra il passo fallito e le sue ultime righe rilevanti (`logs.failed_step.lines`, `logs.failed_step.max_bytes`) e tiene la risposta in memoria, quindi premere di nuovo non costa nulla. Il testo è ripulito da token, chiavi, indirizzi e cartella personale. Si possono interrogare solo repository che il monitor controlla, con `GET /api/run-log?repo=&run=`; in modalità team, solo un amministratore.

## Un token di sola lettura dell'App GitHub per i tuoi strumenti

`github_app.share_reads`: il comando seguente stampa, su questo computer, un token di installazione della tua App GitHub valido un'ora, così il `gh` dei tuoi strumenti e agenti legge con la quota dell'App e non con la tua (`GH_TOKEN`). Il token va solo sullo standard output, mai in un file o in un registro, e il comando richiede `--read-only`; dai all'App permessi di sola lettura quando la crei. Senza `github_app.share_reads` rifiuta. Il token viene richiesto a parte rispetto a quello del monitor, con soli permessi di lettura; se la risposta contiene un permesso di scrittura il comando rifiuta di stamparlo.

```
python bin/monitor_cli.py gh-token --read-only
```

## Quattro rapporti facoltativi

Tutti e quattro sono disattivati per impostazione predefinita. Compaiono in un blocco "Rapporti facoltativi" in fondo alla scheda Avvisi e in `GET /api/reports`. Quelli che leggono GitHub spendono al massimo `reports.max_calls_per_cycle` chiamate per ciclo, leggono pochi repository ogni volta e tengono in memoria per un giorno ciò che leggono.

- `reports.workflow_hygiene.enabled`: legge i file di workflow dei repository ed elenca ciò che è scritto male - action non fissate a un commit, permessi non limitati, un job senza `timeout-minutes`, nessun gruppo `concurrency`, rischi di `pull_request_target` e injection, segreti in chiaro (le regole del linter del pannello A13, che legge cloni locali, più le due nuove).
- `reports.queue.enabled`: legge i job di alcune esecuzioni concluse che hanno aspettato e dice quanto ha aspettato un job prima di partire per ogni tipo di runner (Linux, Windows, macOS, più grandi, self-hosted).
- `reports.release_view.enabled`: nessuna chiamata; da ciò che la sentinella sa dice quali repository sono PRONTI per una release (voci nel changelog o una build verde che nessuno ha pubblicato, nulla di rosso, nessuna firma in attesa) e quali BLOCCATI, e perché.
- `reports.supply_chain.enabled`: legge l'ultima release dei repository e dice, dai nomi dei file, se contiene una distinta dei materiali software (SBOM), checksum e una firma o attestazione. I file non vengono mai scaricati.
