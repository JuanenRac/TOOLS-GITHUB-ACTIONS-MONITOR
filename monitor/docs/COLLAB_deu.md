<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COLLAB.md) | [🇪🇸 Español](COLLAB_spa.md) | [🇫🇷 Français](COLLAB_fra.md) | [🇮🇹 Italiano](COLLAB_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](COLLAB_zho.md) | [🇯🇵 日本語](COLLAB_jpn.md) | [🇵🇹 Português](COLLAB_por.md)

# Der Collab-Wächter: Issues und Pull Requests

Ein zweiter Wächter neben dem CI-Wächter. Er sieht sich die **offenen Issues und Pull Requests** deiner Repositories an und sagt dir, was einen Menschen braucht: vergessene Issues, kritische Labels, Reviews, die niemand macht, Entwürfe ohne Ende, Konflikte, die bleiben. Er hat eine eigene Uhr, ändert nie, was der CI-Wächter entscheidet, und **schreibt nie nach GitHub**. Er gehört zur vollständigen Ausgabe; die Lite-Ausgabe lädt ihn nicht.

## Einschalten

Er ist standardmäßig aus. Einstellungen > Wächter > Issues und Pull Requests, oder in `actions_monitor.json`:

```
"sentinels": {"collab": {"enabled": true, "refresh_seconds": 600, "max_repos_per_tick": 10, "repos": "all",
  "rules": {"issue_stale_days": 14, "issue_critical_labels": ["security", "critical"], "pr_review_pending_days": 3,
            "pr_draft_max_days": 30, "pr_conflict_days": 7, "watch_external_comments": false, "ignore_labels": ["monitor:ignore"]}}}
```

`repos` ist `"all"`, eine Liste von Repositories oder `{"ecosystems": [...]}`.

## Die Regeln (stabile Codes)

| Code | Stufe | Wann |
|---|---|---|
| `collab.issue.stale` | Warnung | ein offenes Issue ohne Aktivität seit `issue_stale_days` |
| `collab.issue.critical` | Fehler | ein offenes Issue mit einem Label aus `issue_critical_labels`, egal wie alt |
| `collab.issue.external` | Warnung | (nur mit `watch_external_comments`) ein Issue von jemandem außerhalb des Teams, das nach einem Tag niemand beantwortet hat |
| `collab.pr.review_pending` | Warnung | ein Pull Request mit angefragtem Review, der seit `pr_review_pending_days` wartet |
| `collab.pr.draft_old` | Info | ein Entwurfs-Pull-Request, der seit `pr_draft_max_days` offen ist |
| `collab.pr.conflict` | Warnung | ein Pull Request mit Konflikten seit `pr_conflict_days` |

Bots werden ausgelassen. Die Standardwerte sind absichtlich langsam: Ein Entwurf, der Monate wartet, ist in vielen Teams normal.

## Was es kostet

Eine Runde liest höchstens `max_repos_per_tick` Repositories, je zwei bedingte Anfragen (ein unverändertes Repository kostet kein Kontingent) und bis zu sechs Pull-Request-Details pro Runde. Sie pausiert, solange das Kontingent unter `min_rate_remaining` liegt. Der Zustand liegt in `collab_state.json` (im Ordner des Kontos, wenn es mehrere gibt); ein Neustart meldet also nichts doppelt.

## Weniger Lärm: ignorieren und stummschalten

- **Ignorier-Label**: Setze ein Label aus `ignore_labels` (standardmäßig `monitor:ignore`) **auf GitHub** an das Issue oder den Pull Request, und Collab löst dafür keinen Alarm aus. Der Monitor schreibt selbst nie Labels.
- **Stummschaltung im Monitor**: Im Reiter Alarme hat jeder Alarm Knöpfe, um diesen Alarm, seine Regel oder den ganzen Wächter für `alerts.mute_hours` Stunden stummzuschalten (standardmäßig 24, von 1 bis 720). Sie läuft von selbst ab, lässt sich jederzeit aufheben, und der Reiter führt einen kurzen Verlauf, was bis wann stummgeschaltet war. Es ist eine Notiz dieses Monitors; auf GitHub ändert sich nichts. Im Netzwerkmodus kann eine Stummschaltung nur von dem Rechner aus gesetzt (und aufgehoben) werden, auf dem der Monitor läuft (`this_computer`); ein Client im Netzwerk sieht sie und kann sie nicht ändern. Das bleibt so, bis eine spätere Ausgabe eigene Benutzer hat. Die Stummschaltung eines Alarms kann auch „bis sich das Element ändert" dauern (`until_change` in der Anfrage von `POST /api/alerts/mute`): Sie endet sofort, wenn sich das `updated_at` des Issues oder Pull Requests ändert, oder nach Ablauf der Stunden, was zuerst eintritt. Im Reiter Alarme ist das der Knopf **Bis zur Änderung**, der bei den Alarmen erscheint, die das `updated_at` ihres Elements tragen (die des Collab-Wächters); der stummgeschaltete Alarm zeigt dann „stumm bis zur Änderung“.

## Wo du es siehst

- Der Reiter **Alarme**: eine Liste für alle Wächter, Filter nach Herkunft (CI, Collab) und Stufe, auf Wunsch auch die stummen.
- Der Reiter Wächter: die Ebene *Issues und Pull Requests*.
- `GET /api/alerts?sentinel=collab&level=&muted=show|hide|only` und `GET /api/sentinel/collab`; `GET /api/events?sentinel=collab&since=` für die Ereignisse (`collab_new`, `collab_fixed`, die auch die Benachrichtigungskanäle senden, wenn du sie wählst; siehe NOTIFICATIONS).

## Grenzen

Pro Repository werden nur die ersten 100 offenen Issues und 100 offenen Pull Requests gelesen, die zuletzt aktualisierten zuerst. Collab schlägt nichts vor und führt nichts aus; Aktionen auf Issues und Pull Requests gehören zu einer späteren Ausgabe.

## Lesen mit der Such-API

Ist `sentinels.collab.search_api` an (standardmäßig aus), fragt der Collab-Wächter die offenen Issues und Pull Requests des ganzen Kontos in wenigen Aufrufen der Such-API ab statt zweier Listen je Repository. Die Such-API hat ein eigenes Kontingent (30 Aufrufe pro Minute), das das REST-Kontingent nicht belastet. Danach werden nur die Konflikte der geänderten Pull Requests gelesen. Die Alarme sind auf beide Arten gleich, ein Test vergleicht sie; fällt die Such-API aus, liest die Runde jedes Repository wie zuvor. Ein so gefundener Pull Request sagt nicht, ob ein Review angefordert wurde, die Regel für wartende Reviews zählt also nur, was die Listen liefern.

## Lange Listen: Seiten und was abgeschnitten wird

Eine GitHub-Seite hat 100 Einträge. Ein Repository kann Hunderte offene Issues und Pull Requests haben, 148 oder 348 Workflows oder eine Matrix mit mehr als 100 Jobs; der Monitor liest daher die nächste Seite, solange die letzte voll war, und sagt, wenn etwas übrig bleibt:

- **Issues und Pull Requests** (dieser Tab): bis zu `pagination.collab_pages` Seiten zu 100 für jede Liste eines Repositorys (die erste Seite behält ihr bedingtes Lesen, ein Repository mit weniger als 100 kostet nichts mehr). Ein Repository mit mehr als gelesen wurde, wird in der Fußzeile des Tabs gezählt; mit der Such-API (`sentinels.collab.search_api`) sagt die Fußzeile „N von M gesehen“, wenn das Konto mehr hat als die 1000 Ergebnisse der Suche.
- **Workflows eines Repositorys** (Hygiene): bis zu `pagination.workflow_pages` Seiten zu 100. Ist die Liste weiter abgeschnitten, sagt die Hygiene dieses Repositorys „N von M gesehen“, statt vollständig zu wirken.
- **Jobs eines Laufs** (Tab Jetzt): bis zu `pagination.job_pages` Seiten zu 100; eine abgeschnittene Matrix zeigt unter dem Lauf „Jobs: N von M gesehen“.

Die Standardwerte lesen für ein Repository, das auf eine Seite passt, nichts zusätzlich.
