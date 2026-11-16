<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ORGANIZATIONS.md) | [🇪🇸 Español](ORGANIZATIONS_spa.md) | [🇫🇷 Français](ORGANIZATIONS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](ORGANIZATIONS_deu.md) | [🇨🇳 简体中文](ORGANIZATIONS_zho.md) | [🇯🇵 日本語](ORGANIZATIONS_jpn.md) | [🇵🇹 Português](ORGANIZATIONS_por.md)

# Organizzazioni e account grandi

Come puntare il monitor a un'organizzazione, o a un account personale con centinaia di repository, e cosa fare quando una lettura torna vuota.

## 1. Il token più piccolo che funziona

Il monitor legge soltanto. Usa l'accesso di `gh` (`gh auth login`) o un token in `GH_TOKEN`, e dagli il minimo indispensabile.

| Tipo di token | Cosa dargli |
|---|---|
| **Classico** (personal access token) | `repo` per i repository privati (`public_repo` basta se tutto è pubblico) e `read:org` per elencare i repository e i team di un'organizzazione. Facoltativi: `security_events` (avvisi di code scanning, pannello A3), `read:project` (le bacheche Projects, pannello A9). Non servono `workflow` né scope di scrittura. |
| **A grana fine** | Un solo *proprietario della risorsa*: crea un token per organizzazione (o per account personale). Accesso ai repository: tutti, o quelli scelti. Permessi di sola lettura: Metadata, Actions, Contents, Pull requests, Issues, Administration (ruleset e regole di ramo), Code scanning alerts, Dependabot alerts, Secret scanning alerts. Un'organizzazione può richiedere che un proprietario approvi prima il token. |
| **GitHub App** | Legge con la quota dell'App invece della tua (vedi `QUOTA.md`). |

Un **account personale** (`github_owner` è un utente) non ha bisogno di altro per i propri repository. I repository di un'organizzazione di cui fai parte si leggono con un token il cui proprietario della risorsa (a grana fine) o i cui scope (classico) includano quell'organizzazione.

## 2. Single sign-on (SSO) e repository privati

Se l'organizzazione impone il SSO SAML, un token classico deve essere autorizzato per essa: su GitHub apri *Settings > Developer settings > Personal access tokens*, scegli il token e premi *Configure SSO > Authorize*. Un accesso fatto con `gh auth login` viene autorizzato nel browser quando accetti l'organizzazione. Fino ad allora GitHub risponde `403` (*Resource protected by organization SAML enforcement*) oppure, peggio, risponde `200` lasciando fuori i repository privati (l'intestazione `X-GitHub-SSO: partial-results`), cosa che sembra un'organizzazione con pochi repository.

Un token che non vede un repository privato riceve `404`, esattamente come se non esistesse. Quindi una risposta vuota può significare: SSO non autorizzato, uno scope o un permesso mancante, un repository privato che l'accesso non vede, o nessuna Actions. La sezione seguente li distingue.

## 3. `--doctor` lo spiega

`py -3 bin/actions_monitor.py --doctor` (anche `bin/monitor_cli.py doctor`) fa tre piccole letture e riporta due righe:

- **L'accesso può leggere l'account o l'organizzazione** (`access`): `ok` con il login e i suoi scope; oppure `warn` con la causa nel dettaglio: `sso` (non autorizzato, o repository privati nascosti), `rate_limited`, `scope` (manca un permesso), `not_found` (l'account non esiste o non è visibile), `forbidden`; `fail` quando GitHub rifiuta le credenziali. Un token a grana fine non ha scope da elencare e la riga lo dice.
- **Le letture all'ora rientrano nella quota** (`estimate`): i repository dell'account e le letture all'ora che richiederebbero le impostazioni attuali, rispetto alle 5.000 all'ora di un token personale. È una stima senza chiamate: il polling dei run (un decimo dei repository caldi, ogni `refresh_seconds`; gli altri ogni `cold_refresh_seconds`), la Sentinella (al massimo `sentinel.budget_per_hour`) e, quando i file di workflow si leggono senza cloni, la loro parte. `warn` oltre il 60 %. Per ridurla: alza `cold_refresh_seconds`, attiva la modalità Low, osserva meno repository (`repos`) o leggi con una GitHub App.

Le stesse cause sono scritte, con il repository, ovunque il monitor non abbia potuto leggere file di workflow: il pannello A13 della Sentinella li elenca come *non valutabili* con il motivo, mai come un "nessun dato" muto.

## 4. Osservare un account che non è tuo (osservatore senza permessi)

Qualsiasi token può leggere i repository pubblici di qualsiasi account, quindi puoi osservare un'organizzazione open source con un token privo di scope. Ciò che un osservatore non ottiene, e il monitor tratta come *sconosciuto* e mai come *a posto*: ruleset e protezione dei rami, avvisi di Dependabot, code scanning e secret scanning, impostazioni, e gli elenchi di run dei repository con Actions disattivate. I pannelli che ne dipendono (A3, parti di A6) restano vuoti o segnati come non valutabili per quei repository. Non si scrive mai nulla, quindi non serve alcun permesso di scrittura.

## 5. Limiti noti

- La quota è di 5.000 letture all'ora per un token personale; una GitHub App installata su un'organizzazione grande ne ha di più (vedi `QUOTA.md`). La stima qui sopra è il modo più rapido per sapere se ci stai dentro.
- Il monitor legge un campione degli ultimi run di ogni repository. Un repository che avvia centinaia di run all'ora si vede attraverso quel campione, non run per run.
- GitHub conserva i log e gli artefatti di un run per 90 giorni per impostazione predefinita; il monitor non può leggere ciò che GitHub ha eliminato.
- Un token a grana fine appartiene a un solo proprietario: osservare due organizzazioni richiede due token (due account del monitor, vedi `ACCOUNTS.md`).
- Le organizzazioni che richiedono l'approvazione dei token, o bloccano quelli classici, hanno bisogno che prima agisca un proprietario; nessuna impostazione del monitor può aggirarlo.
