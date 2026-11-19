<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_SUPPLY.md) | [🇪🇸 Español](SENTINEL_SUPPLY_spa.md) | [🇫🇷 Français](SENTINEL_SUPPLY_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](SENTINEL_SUPPLY_deu.md) | [🇨🇳 简体中文](SENTINEL_SUPPLY_zho.md) | [🇯🇵 日本語](SENTINEL_SUPPLY_jpn.md) | [🇵🇹 Português](SENTINEL_SUPPLY_por.md)

# La sentinella della catena di fornitura

La quarta sentinella, accanto a quelle di CI, Collab e Sicurezza. Legge, senza scrivere nulla su GitHub, i file di workflow di ogni repository (`.github/workflows`, tramite API, senza clone) e segnala ciò che permette a un tag spostato o a un estraneo di agire con il token e il codice del repository. Li trasforma in avvisi della scheda Avvisi (origine Catena di fornitura). È nell'edizione Completa, spenta per impostazione predefinita (`sentinels.supply.enabled`); Lite non ha sentinelle.

Ha una voce propria nel gruppo Sentinella del menu, **Sentinella della catena di fornitura** (indirizzo `#sentinel-supply`), visibile finché la sentinella è accesa: un pannello con i rilievi aperti di ogni repository, lo stato del suo ciclo e ciò che non si è potuto leggere; il badge della voce conta gli errori.

## Cosa segnala

| Segnale | Avviso | Livello | Attivo di default |
|---|---|---|---|
| Un `uses:` di un'action o di un workflow riutilizzabile non fissato a un SHA di commit completo (il proprietario può spostare il tag) | `actions.supply.unpinned` | warning | sì |
| Un `uses:` che segue un branch che si muove da solo (`@main`, `@master`...): peggio di un tag | `actions.supply.mutable_ref` | warning | sì |
| Un workflow con `permissions: write-all` | `actions.supply.permissions_wide` | warning | sì |
| Un workflow senza blocco `permissions:` (il token riceve il permesso predefinito, più ampio) | `actions.supply.permissions_missing` | warning | sì |
| `pull_request_target` insieme al checkout del codice della pull request | `actions.supply.pr_target_checkout` | error | sì |

C'è un avviso per repository e segnale, con il numero di rilievi, i file in cui si trovano e qualche esempio (il nome di un'action) nei dettagli. Ogni segnale si può spegnere (`sentinels.supply.signals.<segnale>.enabled`) e portare a un altro livello (`info`, `warning`, `error`, `critical`). Un `uses:` di un workflow dello stesso repository non è di terzi e viene lasciato fuori.

## Una sola fonte di verità

Non ha regole proprie: i rilievi vengono dal linter dei workflow (`bin/lint_workflows.py`, lo stesso della scheda Sentinella e della riga di comando); qui sono attive solo `unpinned_uses`, `permissions` e `pr_target` e tutte le altre regole restano spente. In particolare la regola che cerca segreti scritti in un file è spenta, quindi **il valore di un segreto non viene mai letto, salvato né mostrato**. Le impostazioni `lint.own_owners` e `lint.unpinned_own` decidono ancora come trattare un'action del proprio account, e un commento `# monitor-lint: ignore REGOLA` in un workflow mette a tacere un rilievo sul posto.

## Un solo proprietario per ogni rilievo

`security.workflow_write` (sentinella Sicurezza) è il permesso predefinito del repository, un'impostazione di GitHub; i segnali di qui riguardano il contenuto di ogni file di workflow, quindi un repository non solleva mai lo stesso rilievo da entrambe. Il pannello del lint della scheda Sentinella resta un pannello; gli avvisi della scheda Avvisi su questi segnali vengono solo da qui.

## Cosa non ha potuto controllare

Un repository i cui workflow non si possono leggere (nessun accesso, SSO non autorizzato, quota esaurita, cartella con troppi file) **non** è un avviso e **non** è un certificato di salute. Compare nello stato sotto `unavailable`, con il motivo e quanti repository sono, e un livello `ok` viene mostrato come `unknown` quando la maggior parte di ciò che è stato guardato non si è potuta leggere. Se un repository smette di rispondere mentre ha avvisi, questi restano una settimana (segnati `unread_since`) e non vengono mai annunciati come risolti. Un repository senza cartella `.github/workflows` viene letto e semplicemente non ha nulla da segnalare. Un repository le cui letture continuano a fallire aspetta 5 minuti, 30 minuti e poi 6 ore prima del tentativo successivo.

## Costo

Un giro legge al massimo `sentinels.supply.max_repos_per_tick` repository (10 di default) e fa al massimo `sentinels.supply.max_calls_per_tick` chiamate (60): una per elencare i workflow di un repository e una in più per ogni file nuovo o modificato, perché un file il cui SHA non è cambiato non viene riletto. Vanno prima quelli letti da più tempo e un po' prima quelli con un avviso aperto; un ciclo ogni `sentinels.supply.refresh_seconds` (un'ora di default). La sentinella si ferma finché la quota rimasta è sotto `sentinels.supply.min_rate_remaining`. Il suo stato (`supply_state.json`) conserva gli avvisi aperti, quindi un riavvio non annuncia nulla di nuovo, e la prima occhiata a un repository non scrive eventi. `sentinels.supply.max_files_per_repo` limita i file letti in un repository; uno oltre il limite viene letto in parte e contato come parziale. Un giro smette anche di iniziare nuovi repository dopo `sentinels.supply.deadline_s` secondi (30 per impostazione predefinita; 0 = nessun limite): quelli non raggiunti aspettano il giro successivo e lo stato li elenca per nome come `unchecked` (con `round_cut`) invece di contarli come zero avvisi.

## Ignorare un rilievo

`sentinels.supply.ignore` accetta modelli `repository:file:regola` (con `*` per qualsiasi) che nominano la regola del linter, ad esempio `mioreponame:release.yml:unpinned_uses`; `unpinned_uses` è la regola dietro `unpinned` e `mutable_ref`, e `permissions` quella dei due segnali di permessi. I modelli di `lint.ignore` non si applicano qui.

`sentinels.supply.ignore_uses` accetta nomi `proprietario/repository` (con `*` per qualsiasi, per esempio `other-org/*`) di azioni o workflow riutilizzabili di un'altra organizzazione privata che l'accesso non può vedere e il cui riferimento il monitor non può giudicare: i loro riferimenti non fissati o mobili restano fuori dai rilievi e sono contati a parte come `uses_left_out` nello stato, quindi né segnalati per supposizione né nascosti.

## Eventi, notifiche e punteggio

Un nuovo rilievo scrive l'evento `security_new` e uno chiuso `security_fixed` (l'evento riporta `sentinel: supply` e il codice dell'avviso), quindi la casella Sicurezza delle preferenze di notifica di ogni utente e i canali decidono chi viene avvisato. Non si annuncia nulla la prima volta che si guarda un repository. Le metriche portano `supply_alerts`, `supply_findings`, `supply_penalty` (informativa: `sentinels.supply.penalty.per_finding`, 2, e `cap_per_repo`, 10, si leggono dal file), `supply_repos_checked`, `supply_repos_unreadable` e `supply_calls_last_hour`. Il punteggio non usa la penalità. L'API risponde a `GET /api/sentinel/supply` e la scheda Avvisi e `monitor_cli.py alerts --sentinel supply` filtrano per essa.

## Le impostazioni

Nella pagina Impostazioni, sotto-scheda Sentinella, blocco Catena di fornitura: `sentinels.supply.enabled`, `sentinels.supply.refresh_seconds`, `sentinels.supply.max_repos_per_tick`, `sentinels.supply.max_calls_per_tick`, `sentinels.supply.max_files_per_repo`, `sentinels.supply.min_rate_remaining`, `sentinels.supply.repos`, `sentinels.supply.ignore`, `sentinels.supply.ignore_uses`, `sentinels.supply.signals.unpinned.enabled`, `sentinels.supply.signals.unpinned.level`, `sentinels.supply.signals.mutable_ref.enabled`, `sentinels.supply.signals.mutable_ref.level`, `sentinels.supply.signals.permissions_wide.enabled`, `sentinels.supply.signals.permissions_wide.level`, `sentinels.supply.signals.permissions_missing.enabled`, `sentinels.supply.signals.permissions_missing.level`, `sentinels.supply.signals.pr_target_checkout.enabled`, `sentinels.supply.signals.pr_target_checkout.level`.

## Cosa non fa

Non scrive su GitHub (né pull request, né etichette, né issue), non propone lo SHA a cui fissare un'action e non legge il valore di alcun segreto.
