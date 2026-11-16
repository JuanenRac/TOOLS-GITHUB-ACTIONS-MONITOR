<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](HEALTH.md) | [🇪🇸 Español](HEALTH_spa.md) | [🇫🇷 Français](HEALTH_fra.md) | [🇮🇹 Italiano](HEALTH_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](HEALTH_zho.md) | [🇯🇵 日本語](HEALTH_jpn.md) | [🇵🇹 Português](HEALTH_por.md)

# Die Gesundheit eines Repositorys und des Teams

Nur Complete. Zwei schreibgeschützte Ansichten, gebildet aus dem, was der Monitor bereits hält (Läufe, rote und hängende Workflows, die offenen Meldungen jedes Wächters und die Release-Bereitschaft). Sie rufen nie GitHub auf.

## Woraus die Gesundheit eines Repositorys besteht

| Teil | Was er sagt |
|---|---|
| CI | Erfolge und Fehler der letzten 24 Stunden, die jetzt roten Workflows, die hängenden Läufe |
| Meldungen | alle offenen Meldungen der Wächter CI, Collab und Sicherheit, nach Wächter und Stufe |
| Release | die Zeile der Release-Bereitschaft, falls das Repository eine hat |
| Aktivität | wann der letzte Lauf begann und wie viele es in 7 Tagen gab |
| Wer hat es angesehen | der Lebenszyklus jedes Wächters: gesund, beeinträchtigt, pausiert, Fehler oder aus |

Der Zustand ist **schlecht** (ein roter Workflow oder eine Meldung der Stufe kritisch oder Fehler), **Warnung** (eine Warnmeldung oder ein hängender Lauf), **OK** oder **nicht gesehen** (nichts zum Beurteilen). Ein Repository, das kein Wächter angesehen hat oder das ein Wächter nicht lesen konnte, wird nie als OK gezeigt: Es sagt „nicht vollständig gesehen von“ und nennt wen. Das Risiko ist die Zahl, nach der die Rangliste sortiert: Jeder rote Workflow (30), hängende Lauf (10), jede kritische Meldung (25), Fehlermeldung (10), Warnung (3) und Information (1) addiert Punkte, für alle Repositorys gleich. Wenn alle Sentinels im Fehler, pausiert oder beeinträchtigt sind (oder alle aus sind und eine Woche lang nichts lief), wird ein ruhiges Repository als nicht gesehen angezeigt, nie als OK, und seine Zeile in der Rangliste trägt ein Sternchen und nennt die Sentinels, die es nicht lesen konnten (`not_fully_seen`; die Summen zählen sie ebenfalls).

## Wo man sie sieht

- Der Tab **Team**: die Rangliste (zuerst die Repositorys, die einen Menschen brauchen), die Summen, die Zahlen je Ökosystem und je Wächter und drei Filter: Ökosystem, Mindestschwere und ein Namensteil. Ein Klick auf ein Repository zeigt die Einzelheiten.
- Direktlinks für Wandbildschirme: `?view=team&chrome=0`, `?view=repos&chrome=0` und `?view=repo&repo=owner/name&chrome=0`.
- Die API: `GET /api/team/health?ecosystem=&severity=&q=&label=` und `GET /api/repos/<owner>/<repo>/health`. Beide brauchen das Recht, das Konto zu sehen; die Antworten tragen `schema: 1`. Ein unbekanntes Repository antwortet 404 mit `code: repo_unknown`.
- Die Lite-Edition behält ihre einfache Laufansicht und hat weder den Tab noch die Routen.

## Die Flottenansicht (Hunderte Repositories)

Der Tab **Team** hat einen zweiten Abschnitt, *Flotte*, für Konten mit Hunderten Repositories. Er gruppiert die Repositories (`fleet.group_by`: Ökosystem, Label, Zustand oder keine), ordnet jede Gruppe (`fleet.sort`: Risiko, Name, letzter Lauf oder Zustand) und zeichnet jeweils `fleet.page_size` Zeilen (standardmäßig 50) mit Zurück und Weiter. Die Seite holt alle Zeilen einmal von `GET /api/team/fleet?ecosystem=&severity=&q=&label=&group=&sort=&saved=` (nur lesend, höchstens 5.000 Zeilen; `truncated` zeigt ein Abschneiden an) und zeichnet nur eine Seite, die Größe des Kontos bremst sie also nicht.

Ein *Label* ist ein Muster von Repository-Namen: `fleet.labels` nimmt Zeilen wie `team-*=backend` an; das erste passende Muster gibt das Label, und die Gruppierung nach Label unterscheidet Organisationen oder Teams in einem Monitor. `fleet.saved_filters` nimmt Zeilen wie `attention=bad||backend|` an (Name, geringster Schweregrad, Ökosystem, Label, Text; jeder Teil nach dem Namen darf leer sein) und zeigt sie als fertige Filter. Die Rangliste über der Flotte bleibt unverändert.
