<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI_OPERATOR.md) | [🇪🇸 Español](CLI_OPERATOR_spa.md) | [🇫🇷 Français](CLI_OPERATOR_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](CLI_OPERATOR_deu.md) | [🇨🇳 简体中文](CLI_OPERATOR_zho.md) | [🇯🇵 日本語](CLI_OPERATOR_jpn.md) | [🇵🇹 Português](CLI_OPERATOR_por.md)

# La riga di comando per l'operatore

Le basi di `monitor_cli.py` sono in [CLI_ita.md](CLI_ita.md). Questa pagina è per chi vive in un terminale: come si scrivono le risposte (`--format`), come osservare (`watch`), come completare i comandi (`completions`), i codici di uscita e l'indirizzo per una TV (`kiosk`). Tutto ciò che segue legge l'API del monitor di questo computer (o quella di `--url`); niente scrive su GitHub e niente consuma la quota.

## Formati: `--format`

| Formato | Cosa ottieni |
|---|---|
| `text` | ciò che ogni comando ha sempre scritto. È il predefinito. |
| `table` | i record in colonne che stanno nella larghezza del terminale (i caratteri giapponesi e cinesi contano come due celle). Non c'è colore, quindi `NO_COLOR` è rispettato. |
| `plain` | un record per riga, i campi separati da una tabulazione, senza intestazione: per `grep`, `cut` e `awk`. Una tabulazione o un a capo dentro un testo diventa uno spazio. |
| `json` | il documento `{"ok", "exit", "data"}`. `--json` è la stessa cosa. |
| `ndjson` | un oggetto JSON per riga, uno per record (un avviso, un account, un repository, un evento). Un comando che risponde una sola cosa (`status`, `health`) dà una riga. |

`--format` prevale su `--json`, ed entrambi prevalgono sull'impostazione `cli.default_format` (predefinita `text`). I tre formati strutturati nascono dallo stesso documento di `--json`, quindi non discordano mai. Un elenco vuoto non stampa nulla in `ndjson` e `plain`.

## `watch`: la stessa lettura, ancora e ancora

```
python bin/monitor_cli.py watch status
python bin/monitor_cli.py watch alerts --interval 10 --format table
python bin/monitor_cli.py watch alerts --exit-on-change --format ndjson
```

`watch status|alerts` ripete la lettura del comando. Legge l'API del monitor, non GitHub, quindi un intervallo breve non consuma la quota. Le opzioni:

- `--interval SECONDI`: la pausa tra due letture. Il minimo è l'impostazione `cli.watch.min_interval_seconds` (2 per impostazione predefinita): un intervallo più breve viene portato a quel valore. Senza `--interval` la pausa è `cli.watch.default_interval_seconds` (5).
- `--once`: una lettura e fine (il codice di uscita è quello del comando).
- `--exit-on-change`: il ciclo termina con il codice di uscita **6** quando ciò che osserva non è più quello della prima lettura (l'insieme degli avvisi o le cifre dello stato). Un orologio che avanza non è un cambiamento. Senza l'opzione il codice 6 non compare mai.
- `--no-clear`: non cancellare lo schermo tra due letture (lo schermo viene cancellato solo su un terminale e solo in `text` e `table`).
- Un monitor che non si può leggere viene ritentato con una pausa sempre più lunga (l'intervallo raddoppiato, al massimo un minuto) e l'errore va sull'errore standard. **Ctrl-C** termina il ciclo con il codice 0.

## `completions`: completare i comandi

```
python bin/monitor_cli.py completions bash > ~/.local/share/bash-completion/completions/monitor_cli.py
python bin/monitor_cli.py completions zsh  > "${fpath[1]}/_monitor_cli"
python bin/monitor_cli.py completions fish > ~/.config/fish/completions/monitor_cli.py.fish
python bin/monitor_cli.py completions powershell | Out-String | Invoke-Expression
```

Lo script è scritto a partire dal vero parser della riga di comando, quindi offre esattamente i comandi, le parole e le opzioni che esistono: una nuova opzione non può essere dimenticata e un test confronta le due cose. Il comando si limita a **stampare**; non modifica alcun tuo file e non ha bisogno del monitor. Metti l'output dove la tua shell legge i completamenti, come sopra.

## Codici di uscita

| Codice | Significato |
|---|---|
| 0 | tutto bene (anche Ctrl-C in `watch`) |
| 1 | uso errato del comando |
| 2 | il monitor non è raggiungibile |
| 3 | il monitor o GitHub rifiuta la credenziale |
| 4 | il monitor risponde ma è degradato (offline, quota esaurita, ancora senza dati) o la risposta non è leggibile |
| 5 | `alerts --fail-on LIVELLO` ha trovato avvisi di quel livello o peggiori |
| 6 | `watch --exit-on-change` ha visto un cambiamento (solo quando si dà quell'opzione) |

I codici da 0 a 5 sono quelli di [CLI_ita.md](CLI_ita.md); un test mantiene questa tabella e il codice d'accordo.

## Esempi con `jq`

Questi esempi usano solo campi che fanno parte della forma stabile delle risposte, e un test li esegue contro un monitor finto (quando `jq` è installato).

```
monitor_cli.py alerts --json | jq -r '.data.alerts[] | select(.level=="critical") | .repo'
monitor_cli.py alerts --format ndjson | jq -r '.code'
monitor_cli.py status --json | jq '.data.red_workflows'
monitor_cli.py team --json | jq -r '.data.ranking[] | .repo'
```

## `kiosk`: l'indirizzo per una TV o una parete

`monitor_cli.py kiosk [ops|team|release|quiet]` stampa l'indirizzo del monitor per uno schermo che nessuno tocca. Vedi [KIOSK_ita.md](KIOSK_ita.md).

## Impostazioni

| Impostazione | Predefinito | Significato |
|---|---|---|
| `cli.default_format` | `text` | il formato quando non si dà né `--format` né `--json`: `text`, `table`, `plain`, `json` o `ndjson` |
| `cli.watch.min_interval_seconds` | 2 | la pausa più breve di `watch` (da 1 a 3600) |
| `cli.watch.default_interval_seconds` | 5 | la pausa di `watch` quando non si dà `--interval` (da 1 a 3600) |

## Cosa non fa questa versione

- `completions` non ha `--install`: non scrive mai nei file di un utente.
- Non esiste un comando `proposals`: il monitor non ha ancora una rotta di proposte su cui agire.

## `metrics`: le cifre per cron e per la posta

`monitor_cli.py metrics` scrive le cifre del monitor come una riga `nome=valore` ciascuna, in ordine fisso e senza altro sullo standard output: `repos`, `active`, `queued`, `failures_24h`, `successes_24h`, `red_workflows`, `alerts`, `alerts_info`, `alerts_warning`, `alerts_error`, `alerts_critical`, `allowance_remaining`, `allowance_limit` e `offline`. Una cifra non nota viene omessa, mai scritta come 0. Legge il monitor, mai GitHub.

Con `--if-problem` non scrive nulla ed esce con 0 quando non c'è alcun workflow rosso né alert di livello `--fail-on` (error per impostazione predefinita) o peggiore; altrimenti scrive le cifre ed esce con 5. cron invia per posta qualsiasi output, quindi questa riga manda un messaggio solo il giorno in cui qualcosa non va: `*/15 * * * * py -3 /opt/monitor/bin/monitor_cli.py metrics --if-problem`. Un monitor irraggiungibile non è mai silenzio: l'errore va sullo standard error e il codice è 2.
