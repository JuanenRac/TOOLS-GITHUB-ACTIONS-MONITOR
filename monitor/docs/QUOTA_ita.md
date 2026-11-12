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
GraphQL non si usa per le esecuzioni dei workflow: non le offre.

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
