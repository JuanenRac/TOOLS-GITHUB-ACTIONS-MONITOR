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

Der Zustand ist **schlecht** (ein roter Workflow oder eine Meldung der Stufe kritisch oder Fehler), **Warnung** (eine Warnmeldung oder ein hängender Lauf), **OK** oder **nicht gesehen** (nichts zum Beurteilen). Ein Repository, das kein Wächter angesehen hat oder das ein Wächter nicht lesen konnte, wird nie als OK gezeigt: Es sagt „nicht vollständig gesehen von“ und nennt wen. Das Risiko ist die Zahl, nach der die Rangliste sortiert: Jeder rote Workflow (30), hängende Lauf (10), jede kritische Meldung (25), Fehlermeldung (10), Warnung (3) und Information (1) addiert Punkte, für alle Repositorys gleich.

## Wo man sie sieht

- Der Tab **Team**: die Rangliste (zuerst die Repositorys, die einen Menschen brauchen), die Summen, die Zahlen je Ökosystem und je Wächter und drei Filter: Ökosystem, Mindestschwere und ein Namensteil. Ein Klick auf ein Repository zeigt die Einzelheiten.
- Direktlinks für Wandbildschirme: `?view=team&chrome=0`, `?view=repos&chrome=0` und `?view=repo&repo=owner/name&chrome=0`.
- Die API: `GET /api/team/health?ecosystem=&severity=&q=&label=` und `GET /api/repos/<owner>/<repo>/health`. Beide brauchen das Recht, das Konto zu sehen; die Antworten tragen `schema: 1`. Ein unbekanntes Repository antwortet 404 mit `code: repo_unknown`.
- Die Lite-Edition behält ihre einfache Laufansicht und hat weder den Tab noch die Routen.
