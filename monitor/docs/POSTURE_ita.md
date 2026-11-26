<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](POSTURE.md) | [🇪🇸 Español](POSTURE_spa.md) | [🇫🇷 Français](POSTURE_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](POSTURE_deu.md) | [🇨🇳 简体中文](POSTURE_zho.md) | [🇯🇵 日本語](POSTURE_jpn.md) | [🇵🇹 Português](POSTURE_por.md)

# Postura di repository e organizzazione

Un elenco di controlli, in sola lettura, su come sono protetti repository e organizzazione: webhook, impostazioni di Actions, scansioni, rami, chiavi di distribuzione, età dei segreti, app, release. Non si modifica nulla su GitHub. Edizioni Complete e Full; disattivata di default.

## Attivazione

Attivare `posture.enabled` (Impostazioni > Postura). Si leggono pochi repository per ciclo (`posture.repos_per_cycle`), ciascuno al massimo ogni `posture.refresh_hours`; consuma quota di GitHub. `posture.org_checks` aggiunge l'organizzazione.

## Cosa si controlla

Ogni rilievo indica il suo posto nei rischi OWASP Top 10 CI/CD e nella guida CIS sulla catena di fornitura. La corrispondenza aiuta a leggere; non è una certificazione.

| Area | Identificatori |
|---|---|
| Consegne dei webhook | webhook.no_secret webhook.plain_http webhook.tls_off |
| Impostazioni di Actions | actions.token_write actions.approves_prs actions.all_allowed actions.sha_not_required actions.fork_approval |
| Codice e dipendenze | scan.no_code scan.no_credentials scan.no_push_protection scan.no_dependency_alerts repo.no_policy repo.no_update_tool |
| Rami | branch.unprotected branch.no_review branch.bypass branch.release_unprotected branch.merged_unreviewed |
| Chiavi e segreti | deploy.write deploy.old stored.old |
| Organizzazione | org.no_two_factor org.default_write org.public_creation org.app_broad org.settings_changed |
| Esecutori | runner.not_hardened runner.coverage_lost |
| Release pubblicate | release.asset_replaced release.asset_removed release.tag_moved release.outside_window |

## Copertura onesta

Ciò che GitHub rifiuta o non risponde è elencato come **non verificato**, mai come corretto, e i rilievi precedenti di quell'area restano. Molte impostazioni richiedono diritti di lettura di amministrazione: il report elenca il permesso di ogni gruppo e quelli negati. Di un webhook si conserva solo l'host; di un segreto nome e date. Le release si confrontano con quanto visto prima: la prima lettura memorizza soltanto. Repository archiviati e fork sono saltati.

## Linea di base e opzioni

`posture.profile` è basic o strict. `posture.types` assegna a modelli un tipo (`standard`, `library`, `internal`, `sandbox`) con la sua base; `posture.skip` esclude controlli. `posture.release_branches` sono modelli di rami protetti. `posture.deploy_max_days` e `posture.stored_max_days` fissano le età. Disattivati finché non richiesti: `posture.audit_log` (audit dell'organizzazione, GitHub Enterprise), `posture.review_sample` (modifiche unite senza approvazione), `posture.runner_runs` (passo di protezione davvero eseguito). `posture.releases` sorveglia file sostituiti e tag spostati; `posture.release_window` fissa l'orario.

## Dove vederla

La scheda Sicurezza delle sentinelle mostra i rilievi, la maturità della catena di sicurezza di ogni repository, una cronologia giornaliera e i permessi. `posture.alerts` porta ogni rilievo negli Avvisi, dove si può silenziare. API: `GET /api/posture`. Riga di comando:

```
posture status
posture matrix
posture check --repo-name my-repo
```

## Limiti

I token granulari dei membri non si leggono (GitHub li elenca solo a una GitHub App) e non si gestisce una seconda app di scrittura. I controlli di organizzazione sono stati provati solo con risposte inventate.
