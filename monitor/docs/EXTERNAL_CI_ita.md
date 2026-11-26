<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](EXTERNAL_CI.md) | [🇪🇸 Español](EXTERNAL_CI_spa.md) | [🇫🇷 Français](EXTERNAL_CI_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](EXTERNAL_CI_deu.md) | [🇨🇳 简体中文](EXTERNAL_CI_zho.md) | [🇯🇵 日本語](EXTERNAL_CI_jpn.md) | [🇵🇹 Português](EXTERNAL_CI_por.md)

# Fonti CI esterne (sola lettura)

Un repository replicato su GitHub può essere compilato altrove. Il monitor legge Buildbot, GitLab CI, Jenkins e Azure Pipelines e ne mostra gli errori come quelli di Actions. Legge soltanto (GET); non avvia, annulla né scrive nulla. Edizioni Complete e Full; disattivato di default.

## Configurazione

Attivare `external_ci.enabled` e scrivere una riga per fonte in `external_ci.sources` (Impostazioni > CI esterna). `repo` è il nome con cui viene mostrato il risultato.

```
buildbot;repo=my-mirror;url=https://buildbot.example.org;builders=linux+docs
gitlab;repo=my-mirror;url=https://gitlab.example.org;project=group/app;token_env=MY_GITLAB_VALUE
jenkins;repo=my-mirror;url=https://jenkins.example.org;job=folder/app;branch=main
azure;repo=my-mirror;url=https://dev.azure.com/my-org;project=my-project
```

## Rosso, corretto o degradato

Decide l'ultima build conclusa di ogni builder, pipeline o job sul suo ramo, come per Actions: richieste di unione e stati annullati, saltati o sconosciuti non decidono mai. Un servizio che non risponde, risponde altro o non ha un builder è **degradato**, mai rosso; gli errori già visti restano, segnati come vecchi. Gli errori generano ci.external.red (livello `external_ci.alert.level`), contati, notificati e silenziati come un rosso di Actions; ci.external.degraded è informativo. Silenziarli non silenzia mai un avviso di sicurezza. Ogni fonte è letta al massimo ogni `external_ci.refresh_seconds` (300 o più) e meno spesso dopo `external_ci.breaker.failures` errori.

## Sicurezza

L'indirizzo è controllato alla connessione: questo computer, reti private e metadati cloud sono rifiutati salvo `external_ci.allow_private_targets`. Non si seguono reindirizzamenti né link nelle risposte. Le risposte sono limitate da `external_ci.max_bytes` e `external_ci.timeout_s`. Nessuna credenziale è scritta nella configurazione: `token_env` contiene solo il NOME di una variabile d'ambiente (GitLab: token di lettura; Jenkins: `utente:token`; Azure: token personale con lettura Build) e non è inviata senza TLS a un indirizzo pubblico. Non consuma la quota di GitHub. In modalità offline (`airgapped`) non si legge nulla; `doctor --egress` elenca gli host.

## Log di una build fallita

Disattivato di default (`external_ci.logs.enabled`). Si chiede solo la fine, limitata da `external_ci.logs.max_kb` e `external_ci.logs.tail_lines`, senza sequenze di terminale né caratteri di controllo, depurata, tenuta in memoria per `external_ci.logs.keep_hours`. È testo non affidabile, mai dato a un'IA come istruzione. La depurazione non riconosce ogni segreto.

## Prova, stato, riga di comando

In Impostazioni > CI esterna c'è **Prova connessione**: una lettura senza salvare (`POST /api/external-ci/probe`). La scheda CI delle sentinelle mostra ogni fonte; `GET /api/external-ci/status` dà lo stesso e `GET /api/external-ci/log` un log. Comandi: `external-ci list`, `external-ci status` (codice 1 se rosso o degradato) e `external-ci probe --source "RIGA"`.

## Non ancora verificato

I quattro adattatori sono stati provati solo con server fittizi (`tools/extci_fake_servers.py`). Jenkins e Azure Pipelines hanno l'etichetta **sperimentale** (`external_ci.experimental`) e richiedono `external_ci.jenkins.enabled` / `external_ci.azure.enabled`. Per un altro adattatore: una funzione `(reader, source, cfg) -> (runs, missing)` in `integrations/external_ci/extci_adapters.py` che legga solo tramite `reader`.

## Identità di un repository, più proprietari

Dentro il monitor un repository è (fonte, proprietario, nome), scritto `repo_key` (`github:proprietario/nome`, `gitlab@host:gruppo/nome`); le rotte continuano a chiamarlo per nome. Due repository con lo stesso nome da due luoghi non condividono identificativi, esecuzioni o avvisi: quando due server dello stesso tipo rispecchiano lo stesso nome, all'etichetta si aggiunge l'host. Il monitor annota a quale proprietario appartengono i dati salvati. Se il proprietario cambia, i silenziamenti e il registro degli avvisi dei repository e l'ultimo stato del flusso di eventi vengono messi da parte (conservati, non cancellati), dopo aver copiato ogni file in `identity_backup/`. Avviene dopo un ciclo; `identity plan` lo mostra senza cambiare nulla, `identity apply` lo fa subito e `identity status` mostra l'annotazione. `sources.multi_owner` (spento) permette di registrare account di proprietari diversi; le installazioni che ne hanno già più di uno continuano a funzionare e il doctor lo segnala. `doctor` legge inoltre una volta ogni fonte esterna.

Riga di comando: `identity status`, `identity plan`, `identity apply`.
