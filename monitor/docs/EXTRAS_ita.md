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

`github_app.share_reads`: il comando seguente stampa, su questo computer, un token di installazione della tua App GitHub valido un'ora, così il `gh` dei tuoi strumenti e agenti legge con la quota dell'App e non con la tua (`GH_TOKEN`). Il token va solo sullo standard output, mai in un file o in un registro, e il comando richiede `--read-only`; dai all'App permessi di sola lettura quando la crei. Senza `github_app.share_reads` rifiuta.

```
python bin/monitor_cli.py gh-token --read-only
```

## Non ancora qui

Il pannello di igiene dei workflow, il rapporto di coda, la vista release pronta o bloccata e il pannello della catena di fornitura non fanno parte di questa versione.
