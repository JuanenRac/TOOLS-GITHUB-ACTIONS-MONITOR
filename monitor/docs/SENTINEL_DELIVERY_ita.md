<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_DELIVERY.md) | [🇪🇸 Español](SENTINEL_DELIVERY_spa.md) | [🇫🇷 Français](SENTINEL_DELIVERY_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](SENTINEL_DELIVERY_deu.md) | [🇨🇳 简体中文](SENTINEL_DELIVERY_zho.md) | [🇯🇵 日本語](SENTINEL_DELIVERY_jpn.md) | [🇵🇹 Português](SENTINEL_DELIVERY_por.md)

# La sentinella di consegna

La quinta sentinella, accanto a quelle di CI, Collab, Sicurezza e Catena di fornitura. Legge, senza scrivere nulla su GitHub, le ultime release pubblicate, gli ultimi tag, il CHANGELOG e i file di versione indicati di ogni repository (tramite l'API, senza clone) e segnala ciò che è stato costruito ma non consegnato. Ne fa avvisi della scheda Avvisi (origine Consegna). È nell'edizione Complete, spenta per impostazione predefinita (`sentinels.delivery.enabled`); Lite non ha sentinelle.

## Cosa segnala

| Segnale | Avviso | Livello | Attivo per impostazione predefinita |
|---|---|---|---|
| Il CHANGELOG ha voci sotto `[Unreleased]` e l'ultima release pubblicata ha più di `sentinels.delivery.unreleased_days` giorni (14) | `release.unreleased_pending` | info | sì |
| Un tag di versione più recente dell'ultima release pubblicata e senza una release propria (una bozza non conta come consegnata) | `release.tag_without_release` | warning | sì |
| L'ultima release pubblicata ha la descrizione vuota | `release.release_without_notes` | info | sì |
| I file di versione di `version_files` e la prima intestazione con versione del CHANGELOG non dichiarano tutti la stessa versione (`1.2` e `1.2.0` sono la stessa) | `release.version_mismatch` | warning | sì |
| Un repository fissa una versione più vecchia dell'ultima del repository che fornisce un contratto condiviso (le tabelle di fissaggio di `sentinel.readiness.pins.sources`, tipo `pin_table`) | `release.ecosystem_drift` | warning | sì |
| L'ultima release pubblicata non ha un file per uno dei modelli di `expected_assets` (per esempio `*.zip`, `SHA256SUMS*`) | `release.assets_missing` | warning | sì |

C'è un avviso per repository e segnale, con i numeri e alcuni tag, modelli o versioni nei dettagli. Ogni segnale si può spegnere (`sentinels.delivery.signals.<segnale>.enabled`) e avere un altro livello (`info`, `warning`, `error`, `critical`). Un repository senza alcuna release pubblicata non è giudicato dai segnali sulle release: non le usa. Le pre-release e le bozze non sono mai prese per l'ultima release.

## Un proprietario per ogni rilievo

Il pannello di prontezza della scheda Sentinella (A11) è una riga per repository ricavata da cloni locali; questa sentinella produce avvisi con identificatore stabile, silenziamenti, eventi e ciclo proprio, letti tramite l'API senza clone. I segnali sui workflow di un repository sono della sentinella Catena di fornitura e quelli sulle impostazioni di GitHub di Sicurezza: nulla viene generato due volte. Il plugin opzionale «Releases» della roadmap è sostituito da questa sentinella.

## Cosa non ha potuto verificare

Un repository che non si può leggere (nessun accesso, SSO non autorizzato, quota esaurita, un giro con meno chiamate di quante ne serva a un repository) **non** è un avviso e **non** è un esito pulito. È elencato nello stato sotto `unavailable`, con il motivo e quanti, e un livello `ok` appare come `unknown` quando la maggior parte di ciò che è stato guardato non si è potuta leggere. Se un repository smette di rispondere mentre ha avvisi, questi restano una settimana (contrassegnati `unread_since`) e non vengono mai annunciati come risolti. Un file che non esiste (nessun CHANGELOG in quel percorso, nessun file di versione di quel tipo) semplicemente manca. Le tabelle di fissaggio si leggono una volta per ciclo; una che non si può leggere conserva i suoi avvisi ed è elencata anch'essa.

## Costo

Un giro legge al massimo `sentinels.delivery.max_repos_per_tick` repository (10 per impostazione predefinita) e fa al massimo `sentinels.delivery.max_calls_per_tick` chiamate (60): una per le release e una per i tag, una per il CHANGELOG (di più se indichi più percorsi e i primi non esistono) e una per ogni file di versione. Un segnale spento non si legge affatto. Quelli letti da più tempo vengono per primi e quelli con un avviso aperto un po' prima; un ciclo ogni `sentinels.delivery.refresh_seconds` (un'ora per impostazione predefinita). Non ci sono richieste condizionali: il costo è limitato da queste impostazioni, non da una risposta 304. La sentinella si ferma finché la quota rimasta è inferiore a `sentinels.delivery.min_rate_remaining`. Il suo stato (`delivery_state.json`) conserva gli avvisi aperti, quindi un riavvio non annuncia nulla di nuovo, e la prima occhiata a un repository non scrive alcun evento.

## Eventi, notifiche e punteggio

Un nuovo rilievo scrive l'evento `delivery_new` e uno chiuso `delivery_fixed` (l'evento dice `sentinel: delivery` e il codice dell'avviso). Appartengono alla famiglia delle release: solo manutentori e amministratori possono sceglierli, e la scelta della sentinella `ci` nelle preferenze di notifica di ogni utente decide chi li riceve; non sono in nessun elenco di eventi predefinito. Le metriche portano `delivery_alerts`, `delivery_unreleased_repos`, `delivery_unreleased_days_max`, `delivery_repos_checked`, `delivery_repos_unreadable` e `delivery_calls_last_hour`. Il punteggio non le usa. L'API risponde a `GET /api/sentinel/delivery` e la scheda Avvisi e `monitor_cli.py alerts --sentinel delivery` filtrano per essa.

## Le impostazioni

Nella pagina Impostazioni, sotto-scheda Sentinella, blocco Consegna: `sentinels.delivery.enabled`, `sentinels.delivery.refresh_seconds`, `sentinels.delivery.max_repos_per_tick`, `sentinels.delivery.max_calls_per_tick`, `sentinels.delivery.min_rate_remaining`, `sentinels.delivery.repos`, `sentinels.delivery.unreleased_days`, `sentinels.delivery.unreleased_min_entries`, `sentinels.delivery.changelog_paths`, `sentinels.delivery.version_files`, `sentinels.delivery.expected_assets`, `sentinels.delivery.signals.unreleased_pending.enabled`, `sentinels.delivery.signals.unreleased_pending.level`, `sentinels.delivery.signals.tag_without_release.enabled`, `sentinels.delivery.signals.tag_without_release.level`, `sentinels.delivery.signals.release_without_notes.enabled`, `sentinels.delivery.signals.release_without_notes.level`, `sentinels.delivery.signals.version_mismatch.enabled`, `sentinels.delivery.signals.version_mismatch.level`, `sentinels.delivery.signals.ecosystem_drift.enabled`, `sentinels.delivery.signals.ecosystem_drift.level`, `sentinels.delivery.signals.assets_missing.enabled`, `sentinels.delivery.signals.assets_missing.level`.

## Cosa non fa

Non scrive su GitHub (né tag, release, etichette, pull request o issue), non pubblica né firma nulla, non crea proposte dai suoi avvisi e non legge il contenuto di alcun file tranne il CHANGELOG e i file di versione indicati.
