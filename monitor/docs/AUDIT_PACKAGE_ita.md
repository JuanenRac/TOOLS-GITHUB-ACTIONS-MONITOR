<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AUDIT_PACKAGE.md) | [🇪🇸 Español](AUDIT_PACKAGE_spa.md) | [🇫🇷 Français](AUDIT_PACKAGE_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](AUDIT_PACKAGE_deu.md) | [🇨🇳 简体中文](AUDIT_PACKAGE_zho.md) | [🇯🇵 日本語](AUDIT_PACKAGE_jpn.md) | [🇵🇹 Português](AUDIT_PACKAGE_por.md)

# Pacchetto per il revisore

Ciò che serve a un revisore per verificare la modalità team, l'esposizione di rete e la gestione dei segreti di questo strumento: una lista di controllo, i rilievi delle revisioni precedenti con la correzione e il test che la mantiene, come eseguire i test e cosa è noto che resta.

## Lista di controllo della sicurezza della modalità team

- La modalità team (`auth.enabled`) è disattivata per impostazione predefinita; attivala solo dietro HTTPS o un proxy fidato (`listen.trusted_proxy`).
- Con la modalità team attiva e la rete aperta, il monitor non parte prima che esista il primo amministratore.
- Fino ad allora entra solo il computer stesso (lì si crea il primo amministratore).
- I token per script (`auth.allow_bearer`) sono disattivati per impostazione predefinita; una sessione ha bisogno del token CSRF per scrivere.
- Il processo di ogni account risponde solo al suo supervisore (una chiave ricevuta all'avvio).
- Nessun segreto viene scritto nel registro né nelle risposte dell'API; il file delle impostazioni è salvato sotto un blocco.
- Ogni richiesta che esce dal monitor (notifiche, OpenTelemetry, esportatori dei runner) segue la stessa regola: nessun indirizzo privato, nessun reindirizzamento verso uno.

## Rilievi, correzioni e test

| Rilievo | Correzione | Test |
|---|---|---|
| Con la modalità team e senza utenti, tutte le rotte erano aperte alla rete | Entra solo il computer stesso finché non esiste il primo amministratore, e la modalità rete non parte senza | `test_184_audit_auth.py::FirstAdministratorWindow, test_185_bootstrap_start.py` |
| Il processo di un account saltava i controlli della modalità team | Richiede la chiave del suo supervisore a ogni richiesta | `test_184_audit_auth.py::ChildAnswersOnlyToItsSupervisor` |
| Il salvataggio delle impostazioni proseguiva senza il blocco del file dopo un timeout | Il salvataggio viene rifiutato con un messaggio se il blocco resta preso per dieci secondi | `test_184_audit_hardening.py::ConfigurationLock` |
| Il comando della sentinella poteva essere una shell con argomenti | Il comando è un elenco la cui prima parola è il percorso completo di un programma che non è una shell, senza caratteri di controllo | `test_184_audit_hardening.py::NotifyCommand` |
| I token per script (bearer) erano attivi per impostazione predefinita | Disattivati per impostazione predefinita; solo un vero true li attiva | `test_184_audit_hardening.py::ScriptTokens` |
| Il feed per le IA era condiviso tra gli account, e aggiornamento, conferma e tetto degli avvisi potevano sorpassarsi | Un feed per account; aggiornamento, conferma e stato prendono lo stesso blocco; il tetto si riserva in un passo bloccato | `test_184_audit_feed.py (OneStepAtATime, CapOfTheNotices)` |
| La pausa dell'hook di uno strumento IA non era riservata in un passo; un esportatore di runner poteva reindirizzare il monitor; le chiamate a GitHub che non tornano si accumulavano | La pausa è tenuta con un blocco; i reindirizzamenti sono controllati e limitati; le chiamate abbandonate sono contate e limitate (`watchdog_max_abandoned`) | `test_184_audit_robustness.py (HookCooldown, Exporter, AbandonedCalls)` |
| Un nome che finiva con un a capo superava i controlli di id, repository e chiavi | Ogni controllo termina alla fine del testo (`\Z`) | `test_184_audit_anchors.py` |
| L'esportazione OpenTelemetry non rispettava la regola delle richieste in uscita; il proxy non era indicato come confine di fiducia; l'escape della pagina non aveva un test | L'esportazione passa per la stessa guardia (nessun indirizzo privato, nessun reindirizzamento); il confine è documentato nella guida; un test mantiene con escape ogni testo dell'API | `test_184_audit_network.py (Collector, ProxyIsAFrontierOfTrust, PageEscaping)` |
| Due monitor potevano ascoltare sulla stessa porta; l'openssl di Git for Windows non veniva trovato; i guasti inghiottiti di proposito non lasciavano traccia della loro origine | La porta viene presa in esclusiva e un secondo monitor rifiuta di partire; openssl è cercato dove lo tiene Git for Windows; ogni guasto inghiottito scrive una riga con tipo e luogo | `test_185_startup.py (OnePerPort, WhereIsOpenssl), test_185_degraded.py` |
| Le esecuzioni senza durata (lette via GraphQL) facevano fallire la sentinella a ogni ciclo | Una durata assente vale zero | `test_186_unfinished_rows.py` |

## Eseguire i test

Dalla cartella `monitor/`: `python -m unittest discover -s tests`. I test non richiedono rete né token GitHub. I test del browser vengono eseguiti se è installato Edge, Chrome o Chromium (o con `MONITOR_BROWSER_TESTS=1`). I file della tabella sono in `monitor/tests/`.

## Limiti noti

- Il proxy dell'ambiente (`network.use_proxy`, disattivato per impostazione predefinita) risolve i nomi da sé: il controllo del nome avviene prima. La garanzia forte deve venire dalla rete (un firewall che rifiuti gli indirizzi privati).
- Windows non può rendere privato un file solo con i permessi: i segreti sono cifrati con la chiave dell'utente dove il sistema lo offre.
- I test non dimostrano nulla su un GitHub reale, un proxy reale o un server di posta reale: usano doppioni locali.
