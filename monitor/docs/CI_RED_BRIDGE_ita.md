<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CI_RED_BRIDGE.md) | [🇪🇸 Español](CI_RED_BRIDGE_spa.md) | [🇫🇷 Français](CI_RED_BRIDGE_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](CI_RED_BRIDGE_deu.md) | [🇨🇳 简体中文](CI_RED_BRIDGE_zho.md) | [🇯🇵 日本語](CI_RED_BRIDGE_jpn.md) | [🇵🇹 Português](CI_RED_BRIDGE_por.md)

# Dal monitor alla dashboard: `ci_red.json`

Che cosa scrive il monitor, come esportarlo e che cosa serve a chi legge il file. Il monitor si limita a leggere GitHub e a scrivere file locali: non esegue mai push, non esegue mai commit e non chiude mai nulla da solo.

## Che cosa scrive il monitor

`ci_red.json` accanto a `bin/actions_monitor.py`, aggiornato dopo ogni passaggio della sentinella (schema 2):

| Campo | Significato |
|---|---|
| `schema` | `2`. I campi vengono solo aggiunti, mai rinominati. |
| `generated` | Ora UTC del passaggio. |
| `tool_version` | Versione dello strumento che ha scritto il file. |
| `complete` | `true` quando ogni repository monitorato è stato letto in quel passaggio. `false` durante il caricamento, quando la quota delle API è risultata insufficiente o quando mancano dei cloni: non agire sull'elenco dei repository rossi né sulla coda di firma finché non è `true`. |
| `red_repos` / `pending_sign_repos` | Conteggi. |
| `repos.<NAME>.ecosystem` | `armor`, `urtc`, `hydra`, `eh3d` oppure `other`. |
| `repos.<NAME>.red[]` | Una voce per ogni workflow la cui ultima esecuzione completata sul ramo predefinito è fallita: `workflow`, `conclusion`, `since`, `streak`, `url`. |
| `repos.<NAME>.pending_sign[]` e `pending_sign_hours` | Release compilate e non ancora firmate, e l'età della più vecchia. |

## Come esportarlo

```
py -3 bin/read_report.py --export-status DIR          # ci_status_public.json + .md, solo ciò che può essere pubblicato
py -3 bin/read_report.py --export-sign-queue FILE     # la coda di firma
```

Entrambi leggono il monitor in esecuzione su `127.0.0.1` (senza quota di GitHub). Si rifiutano di scrivere mentre lo snapshot è in caricamento e ne spiegano il motivo; in tal caso il codice di uscita non è zero.

## Che cosa serve a chi legge (il generatore della dashboard)

1. Leggere `schema`; accettare qualsiasi valore `>= 2` e ignorare i campi sconosciuti.
2. Leggere `complete`; quando è `false`, mantenere l'ultima esportazione completa invece di sostituirla.
3. Mostrare `generated` accanto ai numeri, così un file obsoleto si nota subito.
4. Usare `repos.<NAME>.red[].url` come collegamento; non ricostruirlo mai.

## Che cosa non fa il monitor

Non pubblica il file, non esegue push sul repository del profilo e non tocca alcun workflow. Portare l'esportazione alla dashboard è un passaggio del proprietario (o di un workflow del repository del profilo che legge il file esportato).

## Il dashboard del profilo (contratto del consumatore)

Il dashboard di stato di un repository di profilo può leggere lo stesso documento in due modi: dal monitor in esecuzione (`GET /api/outputs/dashboard.json`, spento finché `outputs.dashboard.enabled` non è attivo, solo questo computer) o dal file scritto da `py -3 bin/read_report.py --export-status DIR` (solo i workflow rossi, mai il lato firma). Ciò su cui il dashboard può contare, verificato da un test di questo repository:

1. `schema` vale `2` e i campi si aggiungono soltanto.
2. Il documento servito è esattamente quello di `ci_red.json`.
3. `complete: false` significa: conserva l'ultima immagine completa.
4. L'esportazione pubblica ha le chiavi `schema`, `generated`, `tool_version`, `complete`, `red_repos` e `red`, e nulla dello stato di firma.

Il monitor non spinge mai il file nel repository del profilo; portarlo lì è un passo del suo proprietario.
