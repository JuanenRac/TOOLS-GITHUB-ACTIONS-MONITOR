<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](QUOTA.md) | [🇪🇸 Español](QUOTA_spa.md) | [🇫🇷 Français](QUOTA_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](QUOTA_deu.md) | [🇨🇳 简体中文](QUOTA_zho.md) | [🇯🇵 日本語](QUOTA_jpn.md) | [🇵🇹 Português](QUOTA_por.md)

# Più quota, meno spesa

GitHub dà a ogni account una **quota limitata di chiamate all'API**, condivisa da tutti gli strumenti che la usano. Questa guida spiega come funziona e tutti i modi in cui il monitor ne spende meno.

## Come funziona la quota
- **REST**: 5000 chiamate all'ora per utente (60 senza accesso). **GraphQL** ha la sua, separata. Anche il `GITHUB_TOKEN` di un workflow in Actions ha la sua. Una **GitHub App** ha una quota propria, separata dalla tua, che cresce con i repository in cui è installata (circa 10 000 all'ora con 130 repository).
- Cosa conta e cosa no: una lettura condizionale che risponde `304 Not Modified` (ETag) non conta; chiedere `rate_limit` è gratis; `git push`, `git fetch` e `git clone` non usano l'API.

## I modi in cui il monitor risparmia
1. **Letture condizionali** (ETag e `304`): `cache.etag.enabled` (attivo per impostazione predefinita); la pagina mostra quante letture sono state risparmiate.
2. **Modalità risparmio**: solo i repository caldi ogni 4 minuti, il resto ogni 30; `modes.auto_low` (attivo) entra sotto 1000 chiamate rimaste e torna sopra 2500 o al rinnovo; preset in `modes.low`. La barra dice che le cifre possono essere vecchie, e quanto.
3. **Pannello centrale come base**: `central.source` (`off`, `git`, `http`) legge `data/sentinel.json` del tuo repository di profilo, aggiornato da un workflow con il proprio token; non spende nulla della tua quota. `central.max_age_minutes` (120): più vecchio di così è "in ritardo" e non è considerato affidabile.
4. **Un solo avviso quando la quota si esaurisce**: le letture si fermano fino al rinnovo, la pagina dice una volta "quota esaurita fino alle HH:MM" (non un errore per repository) e riprende da sola.
5. **Una GitHub App per le letture** (`github_app.*`), più sotto.
6. **GraphQL per i repository tranquilli (opzionale, disattivato per impostazione predefinita)**: `network.graphql_checks` legge a lotti (`network.graphql_batch`, 20 per impostazione predefinita) i repository che non sono caldi tramite GraphQL, che ha una quota propria; una chiamata sostituisce molte chiamate REST. Vede solo l'ultimo commit del ramo predefinito (un workflow che non vi è stato eseguito non compare) e non fornisce durate, tentativi né altri rami, quindi i repository caldi e quelli a cui GraphQL non risponde vengono letti con REST nello stesso ciclo. La contabilità (lotti, repository, punti, repository passati a REST) è nel riepilogo e nello stato per gli strumenti di IA.

## Una GitHub App, passo dopo passo
1. In GitHub, *Settings*, *Developer settings*, *GitHub Apps*, *New GitHub App*. Nessun webhook. Permessi **di sola lettura**: Actions, Checks, Code scanning alerts, Commit statuses, Contents, Dependabot alerts, Issues, Pull requests, Secret scanning alerts e Metadata.
2. *Generate a private key* e conserva il `.pem` **fuori da qualsiasi repository**, leggibile solo da te.
3. *Install App* sul tuo account, su tutti i repository da controllare.
4. Nel monitor: `github_app.enabled` attivo, `github_app.app_id` (il numero della App) e `github_app.key_path` (solo il PERCORSO della chiave). `github_app.installation_id` può restare vuoto.
5. Verifica con `GET /api/github-app/status` (solo da questo computer): mostra nome, installazione, permessi concessi e quota della App, mai la chiave né un token. Il doctor controlla `openssl`, il file della chiave e i suoi permessi.

Sicurezza: il monitor non legge, copia, stampa né registra mai la chiave; passa il suo percorso a `openssl`, che firma un JWT di al massimo dieci minuti. Il token di installazione dura un'ora, resta in memoria ed è rinnovato cinque minuti prima. **Solo le letture** lo usano; le scritture e le azioni mantengono il tuo token. Se la App fallisce o manca di un permesso, la lettura viene ripetuta con il tuo token. La pagina mostra le due quote.

## Quando più strumenti condividono la stessa quota
Tutti gli strumenti dell'account spendono le stesse 5000 chiamate all'ora. Un buon schema: un piccolo involucro di `gh` con una **cache condivisa** di un paio di minuti, una **riserva** (rifiuta di chiamare quando ne restano meno di circa 1000, tranne per l'urgente), il lavoro che richiede dati freschi **subito dopo il rinnovo**, e mai `gh run watch` (interroga di continuo). Per esempio, un involucro che salva la risposta di ogni lettura in un file temporaneo col nome del comando e la ripropone per 120 secondi, e controlla `gh api rate_limit` prima di ogni altra chiamata.

## Cosa NON fare
Non usare più account né più token dello stesso utente per aggirare il limite: è contro le regole di GitHub e può far bloccare l'account. Usa una App, il pannello centrale e la modalità risparmio.

## Impostazioni
| Impostazione | Predefinito |
|---|---|
| `cache.etag.enabled` | attivo |
| `modes.auto_low` / `modes.auto_low_enter` / `modes.auto_low_exit` | attivo / 1000 / 2500 |
| `modes.low.*` (`refresh_seconds`, `cold_refresh_seconds`, `runs_per_repo`, `hot_hours`) | 240 / 1800 / 10 / 2 |
| `min_rate_remaining` | 800 |
| `central.source` / `central.max_age_minutes` | off / 120 |
| `github_app.enabled` / `github_app.app_id` / `github_app.key_path` / `github_app.installation_id` | off / vuoto / vuoto / vuoto |

## Risoluzione dei problemi e FAQ
- *"quota esaurita fino alle HH:MM"*: aspetta; il monitor riprende da solo. Altri strumenti potrebbero spenderla: guarda i loro.
- *Le cifre sono vecchie*: la modalità risparmio è attiva (scelta o automatica); la barra lo dice.
- *La App non funziona*: guarda `/api/github-app/status` e il doctor: openssl, il percorso della chiave, i permessi.
- *`git fetch` costa quota?* No. Vedi anche [QUOTAS_ita.md](QUOTAS_ita.md) (piani e minuti) e [MODES_ita.md](MODES_ita.md).

## La scheda Quota e un secondo account
Tutto ciò che riguarda la quota è in un solo posto: *Impostazioni*, scheda *Quota*. Riunisce le modalità (`modes.auto_low`, `modes.auto_low_enter`, `modes.auto_low_exit` e i valori della modalità risparmio in `modes.low.*`), il risparmio (`network.etag`, insieme a `cache.etag.enabled`), il pannello centrale (`central.source`, `central.max_age_minutes`), la GitHub App (`github_app.*`) e un **secondo account per le letture**. I pulsanti della scheda mostrano la quota di ogni fonte (il tuo accesso, la App, il secondo account) con l'ora di rinnovo, provano la App e il secondo account, elencano i permessi che mancano alla App e applicano i valori consigliati o i predefiniti.

Il secondo account (`extra_reader.enabled`, `extra_reader.file`) è un account di sola lettura il cui token a grana fine sta in un file di testo fuori da qualsiasi repository, leggibile solo da te; l'impostazione contiene SOLO il percorso di quel file. Il monitor legge il token al momento dell'uso, lo tiene in memoria e non lo memorizza, stampa né registra mai. Le letture sono ripartite tra il tuo accesso, la App e il secondo account in base alle chiamate rimaste a ciascuno (la cifra della chiamata gratuita `rate_limit`, meno le letture fatte da allora); una fonte rifiutata viene lasciata fuori cinque minuti e la lettura viene ripetuta con la successiva. Le scritture e le azioni non lo usano mai. È per un account tuo (per esempio un secondo account personale con accesso in lettura ai repository), non un modo per aggirare il limite con account di altri. Il file deve stare nella cartella degli account del monitor (`accounts/`, o la cartella indicata da `MONITOR_ACCOUNTS_DIR`) e non viene mai letto tramite un collegamento; `extra_reader.any_folder` (spento per impostazione predefinita) toglie la regola della cartella. Ciò che dipende da chi chiede (il tuo account, le sue organizzazioni, le notifiche, una ricerca di `@me`, `gh auth`, `gh repo list` senza proprietario) viene sempre servito dal tuo login, e solo una semplice lettura `gh api ENDPOINT` (al massimo con le opzioni `--jq`, `--paginate`, `-H`, `-i` e `--cache`) viene distribuita tra le fonti: ogni altra chiamata va al tuo login.
