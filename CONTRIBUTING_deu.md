# Zu GitHub Actions Monitor beitragen

## Technologie
- **Sprache**: Python 3.11 oder neuer, der Kern braucht keine Pakete (die Terminalansicht `bin/tui.py` nutzt Rich, das optional ist; die Tests überspringen, was es braucht, wenn es fehlt).
- **Oberfläche**: eine lokale Webseite (`monitor/assets/static/actions_monitor.html`) auf `127.0.0.1` sowie Kommandozeilenwerkzeuge.
- **Datenquelle**: der offizielle GitHub-Kommandozeilenclient `gh` (standardmäßig nur lesende Aufrufe).

## Richtlinien
1. **Erst die Tests**: `python -m unittest discover -s monitor/tests` muss vor einem Pull Request bestehen. Offline: Die Tests rufen GitHub nie auf. Um die echten Dienste von Hand zu prüfen, nutze `python tools/manual_check_live.py`.
2. **Acht Sprachen**: Jeder Text, den ein Nutzer liest, steht in `monitor/assets/locales/<lang>.json` für en, es, de, fr, it, ja, zh und pt (europäisches Portugiesisch). Ein neuer Schlüssel kommt in alle acht Dateien; die Tests prüfen, dass sie dieselben Schlüssel haben.
3. **Keine Geheimnisse**: Standardmäßig speichert der Monitor kein Token (er fragt `gh`); das einzige optionale Token liegt nur im sicheren Speicher des Systems (`secretstore.py`). Füge keinen Code hinzu, der Zugangsdaten anderswo liest, ausgibt, protokolliert oder schreibt, und committe nie eine echte `actions_monitor.json`.
4. **Sicher im Standard**: Alles, was auf GitHub schreibt, ein Programm startet, einen Netzwerkport öffnet oder Daten nach außen sendet, ist standardmäßig aus, hat einen eigenen Schalter unter Einstellungen > Erweitert, verlangt eine eigene Bestätigung und lauscht auf `127.0.0.1`, solange der Netzwerkmodus nicht an ist. Eine solche Funktion kommt mit Tests, die beweisen, dass sie ohne Schalter, ohne Bestätigung und ohne Token ablehnt und dass nichts in ein Log gelangt.
5. **Kleine Schritte**: eine Änderung pro Pull Request, mit der passenden Zeile in `CHANGELOG.md`.
6. **Bilder**: Bearbeite `docs/architecture.json` oder `docs/structure.json` und führe `python tools/make_architecture.py` / `python tools/make_structure.py` aus; bearbeite das SVG nie von Hand.
7. **Änderungsprotokoll in acht Sprachen**: Jeder neue Eintrag in `monitor/CHANGELOG.md` bekommt seine Übersetzung in `monitor/docs/CHANGELOG_<spa|deu|fra|ita|jpn|zho|por>.md` (gleiche Versionen und Abschnitte; ein noch nicht übersetzter Eintrag behält den englischen Text unter einem übersetzten Hinweis). `python tools/make_help_index.py --check` und das Release-Gate schlagen fehl, wenn eine Version in einer Übersetzung fehlt.
8. **Jede Version prüft die ganze Hilfe**: Lies vor einem Release (in seinem Release-Pull-Request) JEDES Hilfethema - das README des Repositorys und seine Übersetzungen (Auf einen Blick, Was es tut, Projektstatus, Tests, Repository-Struktur, Dokumentation, Sicherheit), jede Anleitung in `monitor/docs/`, die Schnellstarts und die READMEs des Pakets - und korrigiere jede Zahl, Version, jeden Befehl, Pfad, jedes Bild und jede Funktionsliste, die veraltet ist, in den acht Sprachen. Die Generatoren und Tests der Hilfe (`tools/make_glance.py`, `tools/make_help_index.py`, `tools/make_screenshots.py`, `monitor/tests/test_190_help_current.py`) erfassen nur einen Teil.

## Eine Statusseite nach jeder Version aktualisieren

`.github/workflows/dashboard-dispatch.yml` läuft, nachdem der Workflow `CI` auf `main` grün endet (nur Push-Ereignisse). Definiert die Betreuerin oder der Betreuer das optionale Repository-Secret `ECOSYSTEM_DASHBOARD_DISPATCH_TOKEN`, bittet er ein Dashboard-Repository, seine Versionstabelle zu aktualisieren; ohne das Secret endet er still, hat keine Berechtigungen und ändert oder verzögert die CI nie. Die Version in `electro-hobby-3d.project.json` muss bei jeder Version gleich `tool_version.py` sein; ein Test prüft das.

- Hilfe-Checkliste: die Einstellungshilfe (`cfg.h.<Schlüssel>`) jeder neuen Einstellung, die Hilfe des geänderten Tabs, die Leitfäden in `monitor/docs/`, die acht Sprachen, der Hilfeindex (`python tools/make_help_index.py`) und das Änderungsprotokoll.

## Prüfungen der CI, die den Ablauf schützen

- **Tests ohne Netz**: `sh tools/run_offline_tests.sh discover -s monitor/tests` führt die ganze Suite in einem Netzwerk-Namensraum aus, der nur das Loopback hat. Ein Test, der das Internet braucht, scheitert dort.
- **Prüfung der Abhängigkeiten**: `python tools/audit_dependencies.py` führt `pip-audit` für die von der CI installierten Pakete aus. Eine Unterdrückung in `.github/audit-suppressions.json` braucht `id`, `reason` und `expires` (höchstens 180 Tage entfernt); eine abgelaufene scheitert, ebenso eine tote (die Schwachstelle wird nicht mehr gefunden).
- **Rauchtest externer Quellen**: der wöchentliche Workflow `sources-smoke.yml` führt `tools/smoke_sources.py` gegen die echte Statusseite, die Advisories, die Beschreibung der REST-API und das letzte Release aus und scheitert, wenn eine ihr Format geändert hat.
- **Grenzen**: `tools/limits_check.py` betreibt den Monitor mit einem Konto von 120 Workflows in einem Container mit einem Prozessor und 512 MB.
- **Reihenfolge des Releases**: das GitHub-Release als ENTWURF anlegen und den Tag `vX.Y.Z` pushen; `release-image.yml` baut und veröffentlicht das Image und veröffentlicht den Entwurf erst, wenn es für beide Plattformen unter seinem Tag antwortet. Das Werkzeug zum Veröffentlichen legt das Release als ENTWURF an, lädt `github_actions_monitor.zip`, `SHA256SUMS` und `monitor_updater.py` hoch, prüft, dass alle da sind, und veröffentlicht erst dann (unveränderliche Releases nehmen danach keine Datei mehr an); mit dem Image zuerst pusht es den Tag und `release-image.yml` veröffentlicht den Entwurf.
