<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COLLABORATION.md) | [🇪🇸 Español](COLLABORATION_spa.md) | [🇫🇷 Français](COLLABORATION_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](COLLABORATION_deu.md) | [🇨🇳 简体中文](COLLABORATION_zho.md) | [🇯🇵 日本語](COLLABORATION_jpn.md) | [🇵🇹 Português](COLLABORATION_por.md)

# Viste di collaborazione e azioni facoltative

Viste di ciò che aspetta qualcuno e alcune azioni su GitHub che restano spente finché non le consenti. Edizioni Complete e Full.

## Attivazione

Attiva `actions.enabled` (Impostazioni > Collaborazione). Le viste delle esecuzioni vengono da ciò che il monitor già legge; pull request, avvisi e workflow si leggono per pochi repository a ciclo (`actions.repos_per_cycle`, `actions.refresh_hours`). Il riquadro è in fondo alla scheda Collaborazione dell'area Sentinella.

## Le viste

In attesa di una persona (approvazione di ambiente, workflow di un fork, azione richiesta), separata dall'attesa di un runner. L'ultima esecuzione di ogni corsia (workflow e ramo); un rosso si può accantonare per `actions.dismiss_days` giorni, solo quell'esecuzione, e ripristinare. Pull request aperte: unibili, indietro, da trattare o non noto, aggiornamenti di bot riconosciuti per autore, ramo o etichetta; `actions.hide_workflows` nasconde workflow. Repository con avvisi critici o alti con l'età del più vecchio, e i repository NON letti, per nome. Con `actions.dismissed_alerts`, chi ha scartato avvisi; uno scarto fuori da `actions.dismiss_allowed` genera un avviso.

## Scrivere su GitHub

Non si scrive nulla se `github_actions.enabled` non è attivo, l'azione non è in `github_actions.allowed` e non confermi il piano, che mostra esattamente l'invio. Nuove azioni: `update_branch`, `approve_fork`, `approve_deployment`, `force_cancel`, `enable_workflow`, `dispatch`. Le viste PROPONGONO soltanto: aggiornamenti di bot falliti, rami indietro, esecuzioni troppo in coda o in corso (`actions.queued_hours`, `actions.stuck_hours`), quelle che corrispondono a `actions.cancel_policy`, workflow disattivati per inattività (`actions.inactive_workflows`). Il modulo di un workflow manuale legge e controlla gli input. Con `actions.forks_help`, dati sull'autore di un'esecuzione di fork; senza giudizio.

## L'unica azione automatica

`actions.auto_rerun` (spento) rilancia una volta i job falliti di un'esecuzione non partita o scaduta, con gli stessi controlli. Mai una seconda volta; se fallisce di nuovo viene generato un avviso.

## Hook dei runner propri

Con `actions.runner_hooks`, un hook di un runner di questo computer registra inizio e fine:

```
# ACTIONS_RUNNER_HOOK_JOB_STARTED
python /path/to/monitor/bin/monitor_cli.py runner-hook started
```

Per la fine usa ACTIONS_RUNNER_HOOK_JOB_COMPLETED con `completed`. Un runner di un altro computer non è coperto.

## API e riga di comando

`GET /api/actions/state`, `GET /api/actions/dispatch-form`, `GET /api/actions/environments`, `GET /api/actions/fork-facts`, `POST /api/actions/plan`, `POST /api/actions/dismiss`.

```
python bin/monitor_cli.py actions status
python bin/monitor_cli.py actions proposals
python bin/monitor_cli.py runner-hook started
python bin/monitor_cli.py runner-hook completed
```

## Non verificato

Letture e scritture provate solo con risposte inventate; nessuna delle nuove azioni è stata eseguita su un repository reale.

## Tutte le impostazioni

`actions.enabled` `actions.repos_per_cycle` `actions.refresh_hours` `actions.dismiss_days` `actions.hide_workflows` `actions.bot_authors` `actions.bot_branches` `actions.bot_labels` `actions.dismissed_alerts` `actions.dismiss_allowed` `actions.auto_rerun` `actions.cancel_policy` `actions.queued_hours` `actions.stuck_hours` `actions.forks_help` `actions.inactive_workflows` `actions.runner_hooks`
