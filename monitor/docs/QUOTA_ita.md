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

Sicurezza: il monitor legge la chiave in memoria solo per firmare un JWT di al massimo dieci minuti (con la libreria standard, senza bisogno di `openssl`; `openssl` è solo il ripiego) e non la copia, stampa né registra mai. Il token di installazione dura un'ora, resta in memoria ed è rinnovato cinque minuti prima. **Solo le letture** lo usano; le scritture e le azioni mantengono il tuo token. Se la App fallisce o manca di un permesso, la lettura viene ripetuta con il tuo token. La pagina mostra le due quote.

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

## Il programma openssl e un monitor per porta

Il monitor cerca `openssl` nel PATH e, se non c'è, dove lo tiene Git for Windows (`Git\usr\bin`, `Git\mingw64\bin` in Program Files e nei Programmi dell'utente) e nelle cartelle abituali di macOS e Linux, così lo trova anche un monitor avviato da un `.bat` o da un servizio. `github_app.openssl_path` (percorso assoluto del programma) ne sceglie uno a mano. `/api/github-app/status` mostra `openssl` e `openssl_path`, e il doctor dice quale firma quando non è quello del PATH.

In Windows la porta del monitor è aperta in esclusiva (SO_EXCLUSIVEADDRUSE): due processi non possono più ascoltare sull'8765 insieme. E un monitor che parte mentre un altro monitor risponde già sulla sua porta lo dice e si ferma invece di cercare un'altra porta.

## Ripartizione della quota: fonte preferita e riserva

Per impostazione predefinita ogni lettura va alla fonte (utente, GitHub App, secondo account) con più chiamate libere. Il blocco `readpool` lo cambia, nella scheda Quota delle impostazioni, con i valori prudenti di sempre (`auto`, riserva 0):

- `readpool.prefer.<tipo>` (`auto`, `user`, `app`, `extra`): la fonte che risponde per prima a un TIPO di lettura. I tipi si riconoscono dalla chiamata: `runs` (esecuzioni, workflow, check), `security` (code scanning, Dependabot, secret scanning), `issues` (issue e pull request), `history` (release, commit, tag, contenuti), `discovery` (organizzazioni, ricerca, elenchi di repository) e `other`. Se la fonte preferita fallisce o è sotto la sua riserva rispondono le altre, l'utente per ultimo.
- `readpool.reserve.<fonte>` (da 0 a 4000): chiamate lasciate libere in quella fonte. Finché una fonte ha al massimo le chiamate della sua riserva, il monitor non legge con essa se un'altra può. Usa `readpool.reserve.user` per lasciare chiamate al `gh` dei tuoi strumenti e agenti.

Scritture e azioni usano sempre il token dell'utente. La barra della quota e le modalità di lavoro (veloce e turbo) contano la SOMMA di tutte le fonti: il riquadro mostra la somma e il suggerimento il valore di ogni fonte, e la scheda Quota (Stato) aggiunge una riga con il totale accanto alla quota di utente, App e secondo account.

## Leggere meno: prima il webhook e le fonti gratuite

Le due vie sono **disattivate per impostazione predefinita** e riguardano solo i repository tranquilli (quelli le cui ultime esecuzioni sono tutte concluse e verdi). Un repository in esecuzione, rosso o toccato da un evento viene letto come sempre.

- `savings.webhook_first`: finché il webhook in ingresso è vivo (ha consegnato un evento negli ultimi `savings.webhook_window_minutes` minuti), un repository tranquillo non viene letto nel suo turno lento: GitHub avvisa quando succede qualcosa. Viene comunque letto per intero ogni `savings.webhook_full_minutes`. Senza un webhook vivo non cambia nulla.
- `savings.feeds.enabled`: prima di leggere con l'API un repository tranquillo, l'ultimo commit del suo ramo predefinito viene chiesto a una fonte che non consuma quota - il feed Atom pubblico dei commit, `git ls-remote`, o l'una o l'altra (`savings.feeds.method`: `atom`, `git`, `auto`). Se è il commit dell'ultima lettura completa, il repository resta com'è. Ogni `savings.feeds.max_age_minutes` viene comunque letto per intero. Solo repository pubblici: con uno privato, un errore o una risposta strana, il repository viene letto con l'API come sempre. Dal computer escono solo richieste GET verso github.com, mai una password, e non si scrive nulla. Non si usa se il monitor è isolato dalla rete (air-gapped).

Quanto costa: un'esecuzione che parte senza un push (una pianificazione, un nuovo tentativo) su un repository tranquillo si vede alla lettura completa successiva, non subito. La scheda Quota (Stato) mostra le letture risparmiate da ciascuna via da quando il monitor è partito (circa una chiamata dell'API ciascuna): letture condizionali, GraphQL, prima il webhook, feed Atom, git e pannello centrale.

## Account grandi: cosa copre l'elenco di esecuzioni, e un budget

Un repository che avvia centinaia di esecuzioni all'ora riempie in pochi minuti un elenco di 20-100 esecuzioni, quindi un errore più vecchio o un workflow che gira di rado semplicemente non c'è. Il monitor lo dice invece di sembrare verde:

- **Copertura**: la tabella dei repository mostra fin dove arriva ogni elenco. Un elenco pieno che risale per meno di `sampling.min_coverage_minutes` è segnato come *copertura bassa*; un elenco più corto di quanto richiesto è *completo* (contiene tutta la storia); un totale di 2.500 o 40.000 è il punto in cui GitHub smette di contare, perciò si mostra come *almeno*. Il blocco `sampling` di `GET /api/data` porta le stesse cifre.
- **Seconda occhiata**: con `sampling.default_branch_probe` attiva, un elenco pieno chiede anche i push sul ramo predefinito (senza pull request), una richiesta in più per lettura, così le esecuzioni che decidono il rosso su main non vengono spinte fuori da pull request e pianificazioni.
- **Sguardo alle esecuzioni in corso**: con `sampling.active_probe` attiva, un elenco pieno chiede anche, in due richieste leggere, le esecuzioni ancora `in_progress` e quelle `queued`, così un'esecuzione lunga iniziata prima della finestra dell'elenco non si perde né appare come terminata. Due richieste in più per repository pieno e per lettura; disattivata per impostazione predefinita.
- **A2 insieme**: a un repository con `sentinel.a2_resolve_batch_min` o più workflow da cercare si chiedono una sola volta le esecuzioni completate più recenti del ramo predefinito (al massimo `sentinel.a2_resolve_batch_pages` pagine da 100) e si risolvono insieme; ciò che quell'elenco non mostra si chiede uno alla volta. Con 100 o più workflow servono pochi cicli invece di quattro workflow per ciclo.
- **Budget**: `sampling.api_budget_per_hour` (0 = nessuno) limita le richieste di elenchi di esecuzioni in un'ora. Oltre, si leggono per primi i repository con un workflow rosso, un decimo del budget è sempre riservato a loro e gli altri attendono; la pagina dice quanti. La stima delle richieste all'ora per il numero di repository e gli intervalli si mostra da 3.500 in poi (GitHub consente 5.000 all'ora) o quando c'è un budget.

I valori predefiniti non cambiano nulla per un account con pochi repository: la seconda occhiata e il budget sono disattivati, e il segno di copertura bassa compare solo quando un elenco pieno risale per meno di mezz'ora.

## Quando l'App è attiva e non viene usata

Se `github_app.enabled` è attivo ma l'App non riesce a dare un token, le letture proseguono con il tuo token e la quota è la minore, quella dell'utente. Non è mai silenzioso: il doctor diventa ambra con la causa, un errore viene annotato una volta nell'elenco degli errori inghiottiti e la scheda Quota mostra una riga `GitHub App` con la causa e il limite in uso. Le cause: la chiave non è leggibile o non è una chiave RSA senza passphrase (`key_unreadable`), la chiave non ha potuto firmare (`sign_failed`), l'App non è installata sull'account (`app_not_installed`), GitHub ha rifiutato il token (`token_refused`) e l'App è attiva senza il suo numero o il file della chiave (`not_configured`). La stessa nota è in `GET /api/quota` come `app` e in `GET /api/github-app/status` come `signer` e `code`.
