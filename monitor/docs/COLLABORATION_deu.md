<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COLLABORATION.md) | [🇪🇸 Español](COLLABORATION_spa.md) | [🇫🇷 Français](COLLABORATION_fra.md) | [🇮🇹 Italiano](COLLABORATION_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](COLLABORATION_zho.md) | [🇯🇵 日本語](COLLABORATION_jpn.md) | [🇵🇹 Português](COLLABORATION_por.md)

# Ansichten der Zusammenarbeit und optionale Aktionen

Ansichten dessen, was auf jemanden wartet, und einige GitHub-Aktionen, die aus bleiben, bis Sie sie erlauben. Editionen Complete und Full.

## Einschalten

`actions.enabled` setzen (Einstellungen > Zusammenarbeit). Die Laufansichten stammen aus dem, was der Monitor ohnehin liest; Pull Requests, Warnungen und Workflows werden für wenige Repositorys je Zyklus gelesen (`actions.repos_per_cycle`, `actions.refresh_hours`). Der Kasten steht am Ende des Reiters Zusammenarbeit im Wächterbereich.

## Die Ansichten

Warten auf eine Person (Umgebungsfreigabe, Workflow eines Forks, Aktion erforderlich) getrennt vom Warten auf einen Runner. Der neueste Lauf jeder Spur (Workflow und Branch); ein roter kann für `actions.dismiss_days` Tage zurückgestellt werden, nur dieser Lauf, und wiederhergestellt werden. Offene Pull Requests als mergebar, hinter der Basis, Handlung nötig oder unbekannt, Bot-Updates nach Autor, Branch oder Label; `actions.hide_workflows` blendet Workflows aus. Repositorys mit kritischen oder hohen Abhängigkeitswarnungen mit Alter der ältesten und die NICHT gelesenen Repositorys namentlich. Mit `actions.dismissed_alerts`, wer Sicherheitswarnungen verworfen hat; wer nicht in `actions.dismiss_allowed` steht, löst eine Warnung aus.

## Auf GitHub schreiben

Es wird nur geschrieben, wenn `github_actions.enabled` an ist, die Aktion in `github_actions.allowed` steht und Sie den Plan bestätigen, der genau zeigt, was gesendet wird. Neue Aktionen: `update_branch`, `approve_fork`, `approve_deployment`, `force_cancel`, `enable_workflow`, `dispatch`. Die Ansichten SCHLAGEN nur vor: Bot-Updates mit roten Prüfungen, veraltete Branches, zu lange wartende oder laufende Läufe (`actions.queued_hours`, `actions.stuck_hours`), Treffer von `actions.cancel_policy`, wegen Inaktivität abgeschaltete Workflows (`actions.inactive_workflows`). Das Formular eines manuellen Workflows liest und prüft seine Eingaben. Mit `actions.forks_help` Fakten zum Autor eines Fork-Laufs; ohne Urteil.

## Die einzige automatische Aktion

`actions.auto_rerun` (aus) startet die fehlgeschlagenen Jobs eines nicht gestarteten oder abgelaufenen Laufs einmal neu, mit denselben Prüfungen. Nie ein zweites Mal; schlägt er erneut fehl, wird gewarnt.

## Hooks eigener Runner

Mit `actions.runner_hooks` hält ein Hook eines Runners auf diesem Rechner Start und Ende fest:

```
# ACTIONS_RUNNER_HOOK_JOB_STARTED
python /path/to/monitor/bin/monitor_cli.py runner-hook started
```

Für das Ende ACTIONS_RUNNER_HOOK_JOB_COMPLETED mit `completed`. Runner auf anderen Rechnern sind nicht abgedeckt.

## API und Befehlszeile

`GET /api/actions/state`, `GET /api/actions/dispatch-form`, `GET /api/actions/environments`, `GET /api/actions/fork-facts`, `POST /api/actions/plan`, `POST /api/actions/dismiss`.

```
python bin/monitor_cli.py actions status
python bin/monitor_cli.py actions proposals
python bin/monitor_cli.py runner-hook started
python bin/monitor_cli.py runner-hook completed
```

## Nicht verifiziert

Lesen und Schreiben wurden nur mit erfundenen Antworten getestet; keine der neuen Aktionen lief auf einem echten Repository.

## Alle Einstellungen

`actions.enabled` `actions.repos_per_cycle` `actions.refresh_hours` `actions.dismiss_days` `actions.hide_workflows` `actions.bot_authors` `actions.bot_branches` `actions.bot_labels` `actions.dismissed_alerts` `actions.dismiss_allowed` `actions.auto_rerun` `actions.cancel_policy` `actions.queued_hours` `actions.stuck_hours` `actions.forks_help` `actions.inactive_workflows` `actions.runner_hooks`
