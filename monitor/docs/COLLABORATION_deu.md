<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COLLABORATION.md) | [🇪🇸 Español](COLLABORATION_spa.md) | [🇫🇷 Français](COLLABORATION_fra.md) | [🇮🇹 Italiano](COLLABORATION_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](COLLABORATION_zho.md) | [🇯🇵 日本語](COLLABORATION_jpn.md) | [🇵🇹 Português](COLLABORATION_por.md)

# Ansichten der Zusammenarbeit und optionale Aktionen

Ansichten dessen, was auf jemanden wartet, und einige GitHub-Aktionen, die aus bleiben, bis Sie sie erlauben. Editionen Complete und Full.

## Einschalten

`teamwork.enabled` setzen (Einstellungen > Zusammenarbeit). Die Laufansichten stammen aus dem, was der Monitor ohnehin liest; Pull Requests, Warnungen und Workflows werden für wenige Repositorys je Zyklus gelesen (`teamwork.repos_per_cycle`, `teamwork.refresh_hours`). Der Kasten steht am Ende des Reiters Zusammenarbeit im Wächterbereich.

## Die Ansichten

Warten auf eine Person (Umgebungsfreigabe, Workflow eines Forks, Aktion erforderlich) getrennt vom Warten auf einen Runner. Der neueste Lauf jeder Spur (Workflow und Branch); ein roter kann für `teamwork.dismiss_days` Tage zurückgestellt werden, nur dieser Lauf, und wiederhergestellt werden. Offene Pull Requests als mergebar, hinter der Basis, Handlung nötig oder unbekannt, Bot-Updates nach Autor, Branch oder Label; `teamwork.hide_workflows` blendet Workflows aus. Repositorys mit kritischen oder hohen Abhängigkeitswarnungen mit Alter der ältesten und die NICHT gelesenen Repositorys namentlich. Mit `teamwork.dismissed_alerts`, wer Sicherheitswarnungen verworfen hat; wer nicht in `teamwork.dismiss_allowed` steht, löst eine Warnung aus.

## Auf GitHub schreiben

Es wird nur geschrieben, wenn `github_actions.enabled` an ist, die Aktion in `github_actions.allowed` steht und Sie den Plan bestätigen, der genau zeigt, was gesendet wird. Neue Aktionen: `update_branch`, `approve_fork`, `approve_deployment`, `force_cancel`, `enable_workflow`, `dispatch`. Die Ansichten SCHLAGEN nur vor: Bot-Updates mit roten Prüfungen, veraltete Branches, zu lange wartende oder laufende Läufe (`teamwork.queued_hours`, `teamwork.stuck_hours`), Treffer von `teamwork.cancel_policy`, wegen Inaktivität abgeschaltete Workflows (`teamwork.inactive_workflows`). Das Formular eines manuellen Workflows liest und prüft seine Eingaben. Mit `teamwork.forks_help` Fakten zum Autor eines Fork-Laufs; ohne Urteil. Ein Deployment wird für jeweils eine Umgebung genehmigt, die in der Bestätigung genannt wird; wartet ein Lauf auf mehrere, fragt die Seite, welche.

## Die einzige automatische Aktion

`teamwork.auto_rerun` (aus) startet die fehlgeschlagenen Jobs eines nicht gestarteten oder abgelaufenen Laufs einmal neu, mit denselben Prüfungen. Nie ein zweites Mal; schlägt er erneut fehl, wird gewarnt.

## Einen Zeitplan wachhalten

GitHub schaltet die geplanten Workflows eines öffentlichen Repositorys nach 60 Tagen ohne Aktivität ab. Mit `teamwork.keep_alive_days` (0 = aus; zum Beispiel 45) erscheint ein öffentliches Repository ohne Push in dieser Zeit, dessen Workflows nach Zeitplan gelaufen sind, unter den Vorschlägen als `enable_workflow`, mit den verbleibenden Tagen. Es ist ein Vorschlag wie jeder andere: Nichts wird gesendet, bevor du ihn bestätigst. GitHub dokumentiert nicht, dass das Aktivieren eines aktiven Workflows die Zählung neu startet, und dies wurde nicht an einem echten Repository erprobt: Sicher ist ein neuer Commit.

## Hooks eigener Runner

Mit `teamwork.runner_hooks` hält ein Hook eines Runners auf diesem Rechner Start und Ende fest:

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

`teamwork.enabled` `teamwork.repos_per_cycle` `teamwork.refresh_hours` `teamwork.dismiss_days` `teamwork.hide_workflows` `teamwork.bot_authors` `teamwork.bot_branches` `teamwork.bot_labels` `teamwork.dismissed_alerts` `teamwork.dismiss_allowed` `teamwork.auto_rerun` `teamwork.cancel_policy` `teamwork.queued_hours` `teamwork.stuck_hours` `teamwork.forks_help` `teamwork.inactive_workflows` `teamwork.keep_alive_days` `teamwork.runner_hooks`
