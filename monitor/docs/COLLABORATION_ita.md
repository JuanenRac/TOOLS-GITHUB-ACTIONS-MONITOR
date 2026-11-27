<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COLLABORATION.md) | [🇪🇸 Español](COLLABORATION_spa.md) | [🇫🇷 Français](COLLABORATION_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](COLLABORATION_deu.md) | [🇨🇳 简体中文](COLLABORATION_zho.md) | [🇯🇵 日本語](COLLABORATION_jpn.md) | [🇵🇹 Português](COLLABORATION_por.md)

# Viste di collaborazione e azioni facoltative

Viste di ciò che aspetta qualcuno e alcune azioni su GitHub che restano spente finché non le consenti. Edizioni Complete e Full.

## Attivazione

Attiva `teamwork.enabled` (Impostazioni > Collaborazione). Le viste delle esecuzioni vengono da ciò che il monitor già legge; pull request, avvisi e workflow si leggono per pochi repository a ciclo (`teamwork.repos_per_cycle`, `teamwork.refresh_hours`). Il riquadro è in fondo alla scheda Collaborazione dell'area Sentinella.

## Le viste

In attesa di una persona (approvazione di ambiente, workflow di un fork, azione richiesta), separata dall'attesa di un runner. L'ultima esecuzione di ogni corsia (workflow e ramo); un rosso si può accantonare per `teamwork.dismiss_days` giorni, solo quell'esecuzione, e ripristinare. Pull request aperte: unibili, indietro, da trattare o non noto, aggiornamenti di bot riconosciuti per autore, ramo o etichetta; `teamwork.hide_workflows` nasconde workflow. Repository con avvisi critici o alti con l'età del più vecchio, e i repository NON letti, per nome. Con `teamwork.dismissed_alerts`, chi ha scartato avvisi; uno scarto fuori da `teamwork.dismiss_allowed` genera un avviso.

## Scrivere su GitHub

Non si scrive nulla se `github_actions.enabled` non è attivo, l'azione non è in `github_actions.allowed` e non confermi il piano, che mostra esattamente l'invio. Nuove azioni: `update_branch`, `approve_fork`, `approve_deployment`, `force_cancel`, `enable_workflow`, `dispatch`. Le viste PROPONGONO soltanto: aggiornamenti di bot falliti, rami indietro, esecuzioni troppo in coda o in corso (`teamwork.queued_hours`, `teamwork.stuck_hours`), quelle che corrispondono a `teamwork.cancel_policy`, workflow disattivati per inattività (`teamwork.inactive_workflows`). Il modulo di un workflow manuale legge e controlla gli input. Con `teamwork.forks_help`, dati sull'autore di un'esecuzione di fork; senza giudizio. Un deployment si approva per un ambiente alla volta, indicato nella conferma; se un'esecuzione ne attende diversi, la pagina chiede quale.

## L'unica azione automatica

`teamwork.auto_rerun` (spento) rilancia una volta i job falliti di un'esecuzione non partita o scaduta, con gli stessi controlli. Mai una seconda volta; se fallisce di nuovo viene generato un avviso.

## Tenere viva una pianificazione

GitHub spegne i workflow pianificati di un repository pubblico dopo 60 giorni senza attività. Con `teamwork.keep_alive_days` (0 = disattivato; per esempio 45), un repository pubblico senza push per quel tempo e con workflow eseguiti da pianificazione compare tra le proposte come `enable_workflow`, con i giorni rimasti. È una proposta come le altre: non si invia nulla finché non la confermi. GitHub non documenta che attivare un workflow già attivo riavvii il conteggio, e questo non è stato provato su un repository reale: il modo sicuro è un nuovo commit.

## Hook dei runner propri

Con `teamwork.runner_hooks`, un hook di un runner di questo computer registra inizio e fine:

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

`teamwork.enabled` `teamwork.repos_per_cycle` `teamwork.refresh_hours` `teamwork.dismiss_days` `teamwork.hide_workflows` `teamwork.bot_authors` `teamwork.bot_branches` `teamwork.bot_labels` `teamwork.dismissed_alerts` `teamwork.dismiss_allowed` `teamwork.auto_rerun` `teamwork.cancel_policy` `teamwork.queued_hours` `teamwork.stuck_hours` `teamwork.forks_help` `teamwork.inactive_workflows` `teamwork.keep_alive_days` `teamwork.runner_hooks`
