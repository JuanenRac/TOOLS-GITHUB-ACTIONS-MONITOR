<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_SECURITY.md) | [🇪🇸 Español](SENTINEL_SECURITY_spa.md) | [🇫🇷 Français](SENTINEL_SECURITY_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](SENTINEL_SECURITY_deu.md) | [🇨🇳 简体中文](SENTINEL_SECURITY_zho.md) | [🇯🇵 日本語](SENTINEL_SECURITY_jpn.md) | [🇵🇹 Português](SENTINEL_SECURITY_por.md)

# La sentinella di sicurezza

La terza sentinella, accanto a quella della CI e a Collab. Legge, senza scrivere nulla su GitHub, ciò che GitHub stesso dice essere aperto o mancante in materia di sicurezza per ogni repository, e lo trasforma in avvisi della scheda Avvisi (origine Sicurezza). È nell'edizione Complete, spenta per impostazione predefinita (`sentinels.security.enabled`); Lite non ha sentinelle.

## Cosa legge e cosa segnala

| Segnale | Avviso | Livello | Attivo per impostazione predefinita |
|---|---|---|---|
| Avvisi Dependabot aperti di gravità `min_severity` o superiore (high per impostazione predefinita) | `security.dependabot` | critico se uno è critico, errore se uno è alto, altrimenti avvertimento | sì |
| Avvisi di analisi del codice aperti di gravità `min_severity` o superiore | `security.code_scanning` | uguale | sì |
| Avvisi di scansione dei segreti aperti | `security.secret` | sempre critico (un segreto trovato da GitHub è un segreto esposto) | sì |
| Il branch predefinito non ha protezione | `security.branch_unprotected` | avvertimento | sì |
| I workflow ricevono il permesso di scrittura per impostazione predefinita | `security.workflow_write` | avvertimento | sì |
| Non c'è un file CODEOWNERS | `security.codeowners_missing` | informazione | no |

C'è un avviso per repository e segnale, con i conteggi per gravità nei dettagli. Ogni segnale si può spegnere (`sentinels.security.signals.<segnale>.enabled`) e, per Dependabot e l'analisi del codice, avere un'altra gravità minima. Di un repository archiviato non si chiede altro.

## Cosa non ha potuto controllare

Una fonte a cui GitHub non risponde per un repository (la funzione è spenta lì, o l'accesso non può leggerla: 403, 404) **non** è un avviso e **non** è un certificato di buona salute. È elencata nello stato sotto `unavailable`, con quanti repository riguarda, e la pagina lo dice. L'unica eccezione è la protezione del branch predefinito: GitHub risponde 404 per un branch che non ne ha, e quello è il rilievo; un 403 lì è solo non leggibile.

Quando la maggior parte di ciò che pesa nella penalità (Dependabot, code scanning, segreti) non si può leggere, il livello è `unknown` e non `ok`, e la parte sicurezza del punteggio viene esclusa invece di contare come 100; lo stato mostra `sources_readable` e `sources_total`. Se una fonte smette di rispondere mentre un avviso è aperto, l'avviso resta per una settimana (segnato con `unread_since`) e non viene mai annunciato come risolto. Un repository le cui letture continuano a fallire aspetta 5 minuti, 30 minuti e poi 6 ore prima del tentativo successivo, così pochi repository guasti non consumano mai l'intero giro.

Una fonte che il piano dell'account non ha (protezione dei branch o code scanning di un repository privato nel piano gratuito: GitHub risponde che la funzione richiede un altro piano) si distingue da un rifiuto e da una funzione disattivata: la pagina e `unavailable_why` dello stato dicono `N/A (piano)`, `N/A (nessun accesso)` o `N/A (disattivato)`. Con `sentinels.security.plan_na` attiva (predefinito) le fonti del primo tipo restano fuori dal conteggio del leggibile e dalla copertura del voto e sono contate a parte come `sources_na_plan`; nessuno dei tre casi è un rilievo né un attestato di pulizia, e una sentinella il cui piano non ha nulla di ciò che pesa è `unknown` e non dà al voto alcuna parte sicurezza. Disattivata, contano come fonti non leggibili.

Ora ogni sentinella dichiara il suo **ciclo di vita**: `healthy` (sano), `degraded` (degradato: alcune letture falliscono, una fonte non è leggibile o non ha finito il primo giro), `paused` (in pausa, in attesa della quota di GitHub), `error` (fallisce e non ha ancora letto nulla) oppure `off` (spenta). «Nessun avviso» significa qualcosa solo quando il ciclo di vita è `healthy`.

## Costo

Un giro legge al massimo `sentinels.security.max_repos_per_tick` repository (5 per impostazione predefinita), prima quelli guardati meno di recente e un po' prima quelli con un avviso aperto, con un ciclo ogni `sentinels.security.refresh_seconds` (30 minuti per impostazione predefinita). Ogni repository costa al massimo sette letture, quasi tutte condizionali: un repository che non è cambiato non consuma quota; il file CODEOWNERS, quando richiesto, si cerca al massimo una volta al giorno. La sentinella si mette in pausa finché la quota rimasta è inferiore a `sentinels.security.min_rate_remaining`. Il suo stato (`security_state.json`) conserva gli avvisi aperti, quindi un riavvio non annuncia di nuovo nulla, e il primo sguardo a un repository non scrive eventi. Un giro smette anche di iniziare nuovi repository dopo `sentinels.security.deadline_s` secondi (30 per impostazione predefinita; 0 = nessun limite): quelli non raggiunti aspettano il giro successivo e lo stato li elenca per nome come `unchecked` (con `round_cut`) invece di contarli come zero avvisi.

## Un solo proprietario per rilievo

I pannelli della scheda Sentinella che già mostravano cifre di sicurezza (avvisi per repository, avvisi vecchi, copertura di Dependabot e CodeQL, pull request di Dependabot) restano pannelli. Gli avvisi della scheda Avvisi su questi segnali vengono solo da questa sentinella, quindi nulla è sollevato due volte. Il contenuto di ogni file di workflow (action non fissate a un commit, `write-all`, nessun blocco di permessi, `pull_request_target` con checkout) spetta alla [sentinella della catena di fornitura](SENTINEL_SUPPLY_ita.md); `security.workflow_write` resta qui perché è un'impostazione del repository.

## Eventi e notifiche

Un nuovo rilievo scrive l'evento `security_new` e uno chiuso `security_fixed` nel flusso, a cui sono agganciati i canali di notifica; sono due tipi che la persona può chiedere nelle impostazioni delle notifiche, e le preferenze per utente hanno una casella Sicurezza. Non si annuncia nulla la prima volta che si guarda un repository.

## Le impostazioni

Nella pagina Impostazioni, sotto-scheda Sentinella, blocco Sicurezza: `sentinels.security.enabled`, `sentinels.security.refresh_seconds`, `sentinels.security.max_repos_per_tick`, `sentinels.security.min_rate_remaining`, `sentinels.security.repos`, `sentinels.security.plan_na`, `sentinels.security.signals.dependabot.enabled`, `sentinels.security.signals.dependabot.min_severity`, `sentinels.security.signals.code_scanning.enabled`, `sentinels.security.signals.code_scanning.min_severity`, `sentinels.security.signals.secret.enabled`, `sentinels.security.signals.branch.enabled`, `sentinels.security.signals.workflow.enabled` e `sentinels.security.signals.codeowners.enabled`. I punti che ogni rilievo toglie alla parte di sicurezza del punteggio (`sentinels.security.penalty`) si leggono dal file; vedi il file di esempio.
