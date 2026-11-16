<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](QUOTAS.md) | [🇪🇸 Español](QUOTAS_spa.md) | [🇫🇷 Français](QUOTAS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](QUOTAS_deu.md) | [🇨🇳 简体中文](QUOTAS_zho.md) | [🇯🇵 日本語](QUOTAS_jpn.md) | [🇵🇹 Português](QUOTAS_por.md)

# Quote e piani

Il monitor è usato da ogni tipo di account, quindi non ne presume nessuno. Le cifre qui sotto stanno in `monitor/assets/examples/quotas.json` (una copia chiamata `quotas.json` accanto ai lanciatori ha la precedenza) (modificalo per seguire i cambiamenti di GitHub senza una nuova versione del monitor) e sono state confrontate con la documentazione pubblica di GitHub; cambiano nel tempo, quindi usale come punto di partenza e guarda le pagine citate nel file. Scegli il tuo piano in **Impostazioni > Di base** (`account.plan`); finché è *sconosciuto* non viene mostrata alcuna cifra di quota.

## La quota dell'API

| Come accedi | Chiamate all'ora |
|---|---|
| Senza accesso | 60 all'ora per indirizzo |
| Il tuo accesso (`gh auth login`) o un token personale | 5.000 |
| Il token di un workflow (dentro Actions) | 1.000 per repository (15.000 su Enterprise Cloud) |
| Un'app su Enterprise Cloud | 15.000 |
| Una GitHub App altrove | 5.000, cresce con l'installazione fino a 12.500 |

La pagina mostra il limite reale letto dalle intestazioni di GitHub (`X-RateLimit-*`), mai un 5.000 presunto: è anche ciò che fa funzionare GitHub Enterprise Server (`GH_HOST`). Senza accesso (60 all'ora) suggerisce `gh auth login`. Esiste anche un limite *secondario* (non più di 100 richieste simultanee e raffiche): quando GitHub risponde così, il monitor attende almeno un minuto, poi raddoppia l'attesa fino a cinque minuti e non insiste mai.

## Minuti di Actions

| Piano | Incluso ogni mese (in denaro) | In minuti Linux | Archiviazione artefatti |
|---|---|---|---|
| Free | 12 $ | 2.000 | 500 MB |
| Pro | 18 $ | 3.000 | 1 GB |
| Team | 18 $ | 3.000 | 2 GB |
| Enterprise Cloud | 300 $ | 50.000 | 50 GB |

**I repository pubblici non costano minuti in nessun piano** (nemmeno i runner self-hosted); i runner più grandi si fatturano sempre. Un minuto si moltiplica per la tariffa del suo sistema: Windows vale circa 1,67 minuti Linux e macOS circa 10,3 (tariffe al minuto in `quotas.json`: 0,006 $ Linux, 0,010 $ Windows, 0,062 $ macOS). Ciò che il monitor mostra in **Impostazioni > Di base > Piano e quote** è una **stima**: la durata dei run delle ultime 24 ore, arrotondata al minuto, solo per i repository privati, con il sistema ipotizzato in `quota.default_runner`, e il ritmo di un giorno moltiplicato per i giorni del mese. Le cifre reali vengono solo dall'interruttore facoltativo `quota.billing_api` (spento per impostazione predefinita, sola lettura, richiede un accesso autorizzato a vedere la fatturazione; con un 403 o 404 la stima resta e lo dice). Un avviso parte tramite le notifiche una volta al mese a `quota.warn_percent` (75 %) e `quota.alert_percent` (90 %) dei minuti inclusi.

## Concorrenza e limiti

| Piano | Job contemporanei | di cui macOS |
|---|---|---|
| Free | 20 | 5 |
| Pro | 40 | 5 |
| Team | 60 | 5 |
| Enterprise | 500 | 50 |

Il pannello confronta i job in corso e in coda con il limite del tuo piano e avvisa al 90 % o quando dei job attendono con il limite pieno. Un job può durare al massimo 6 ore su un runner di GitHub (il pannello elenca quelli oltre l'80 %), un run di workflow dura al massimo 35 giorni e una matrice ha fino a 256 job.

## Cosa non è coperto

Non si seguono i prezzi per minuto extra, i runner più grandi, lo spazio usato, Codespaces e Packages; la tabella dei piani è un punto di partenza e i limiti di macOS cambiano. Nulla di tutto ciò è stato ancora provato con un rapporto di fatturazione reale: la lettura di `usageItems` segue la descrizione pubblica e degrada in silenzio.

## Limiti noti

- **Gli elenchi di esecuzioni sono campioni.** Il monitor legge le ultime `runs_per_repo` esecuzioni di ogni repository (20 per impostazione predefinita); un totale che GitHub smette di contare (2.500 o 40.000) è mostrato come *almeno*, e un repository il cui campione risale solo a poco tempo fa è contrassegnato come *copertura bassa*.
- **Il piano può essere `unknown`.** I repository privati e gratuiti non dicono quale piano abbia l'account: con `account.plan` su `unknown` le quote, i minuti inclusi e il limite di concorrenza sono mostrati come *sconosciuti* con le cifre che si possono sapere (minuti contati), mai come un errore. Scegli il piano per vedere le percentuali.
- **Un proprietario per monitor.** Un repository è identificato dal suo nome; per seguire un'altra organizzazione avvia un secondo monitor con il proprio `github_owner`.
- **La coda di merge** è seguita solo per il ramo predefinito (esecuzioni dell'evento `merge_group` su `gh-readonly-queue/<predefinito>/...`), e un'esecuzione della coda conta minuti come qualsiasi altra.
