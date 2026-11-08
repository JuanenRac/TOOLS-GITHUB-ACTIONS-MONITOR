# Roadmap

Ideen, die nicht in die aktuelle Version passten, ohne versprochene Reihenfolge. Es sind Richtungen, keine Zusagen; ein Issue oder ein Pull Request ist der beste Weg, eine voranzubringen.

## Erledigt in 1.6.5

Ein Release für Integrität und Sicherheit, ohne große neue Funktion: Ein grüner Commit braucht den erforderlichen Workflow des Repositorys, ein fehlgeschlagener Fetch stoppt den Start, der Katalog kann kein Werkzeug außerhalb des Werkzeugordners nennen und `dry_run`/`ref` nicht ändern, und ein Stapel ohne aufgezeichnete Commit-Prüfung wird nicht mehr zum Signieren angeboten; `act` bleibt im Arbeitsbereich und Stopp beendet den ganzen Prozessbaum samt Containern des Laufs; der Netzwerkmodus kann HTTPS liefern, sperrt falsche Token und akzeptiert nur IPv4; der Webhook lehnt Wiederholungen und Fluten ab; der MCP-Server übersteht fehlerhafte Nachrichten; `max_per_hour` zählt Nachrichten; Einstellungen werden unter einer Sperre gespeichert; das gespeicherte Token erreicht nur `gh`; `--doctor` warnt vor gefährlichen Kombinationen; der Test der sauberen Installation ist eine eigene Stufe der Release-Prüfung.

## Erledigt in 1.6.4

Isolationstests der Lite-Edition und der Demo, keinerlei Netzwerkanfrage, wenn die Versionsprüfung aus ist oder die Installation abgeschottet ist, ein README, das mit der Wahl des Starters beginnt, `--doctor --json`, eine dauerhafte Leiste für den Netzwerkmodus, die Hilfe und ihre Dokumente in acht Sprachen sowie die optionalen Funktionen (Netzwerkmodus, ein vom Monitor gespeichertes Token, Aktionen auf GitHub, `act`, lokale Kopie von Artefakten, eigene Runner, OpenTelemetry, FinOps nach Job-Labels); siehe Änderungsprotokoll und `ADVANCED.md`.

## Als Nächstes

Was 1.6.4 nicht erreicht hat, und warum:

- **Beschlossen, in 1.6.5 nicht erledigt** (das Release ist auf Integrität und Sicherheit beschränkt): die aktive Meldung an eine externe KI (standardmäßig aus, eine erste Bestätigung je Anbieter, nur die bereinigten Felder der geschlossenen Liste, ein Limit für Aufrufe und Kosten pro Stunde, der Schlüssel über den Namen einer Umgebungsvariable, und die KI führt nie eine Aktion aus) samt der Variante mit ausgehendem Befehl (geschlossene Liste, keine Shell); neue Screenshots (`tools/make_screenshots.py --web` lieferte auf dem Release-Rechner keine Ausgabe, sie werden also von Hand gemacht: `--demo` starten, die Seite öffnen und pro Reiter eine Aufnahme speichern); und die Repositories mehrerer Eigentümer auf einer Seite.
- **Mehrere Besitzer in einer Seite**: Der Monitor erkennt ein Repository allein an seinem Namen (Läufe, Wächter, Cache, Exporte); zwei Besitzer mit gleichnamigem Repository würden sich vermischen. Organisationen werden aufgelistet und jede von einem eigenen Monitor überwacht (`github_owner`). In einer Seite bräuchte jede Kennung den Besitzer.
- **Der Abrechnungsbericht mit einem Login, der ihn lesen darf**: Die echte Antwort für einen Login ohne den Scope `user` ist „nicht gefunden“, und der Monitor fällt auf die Schätzung zurück (geprüft); die Zahlen selbst wurden nicht mit einem Abrechnungskonto verglichen.
- **Die Preise größerer Runner** in `quotas.json` stammen aus dem Gedächtnis der öffentlichen Preisliste und sind als ungeprüft markiert; vergleiche sie mit der Abrechnungsseite von GitHub und bearbeite die Datei.
- **`gh copilot`**: Seine Optionen werden mit `gh copilot -- --help` geprüft, was die Copilot-Kommandozeile braucht; sie ist hier nicht installiert, die Optionen bleiben ungeprüft.
- **Benachrichtigungen, Webhook, Enterprise Server und die Dienstbeispiele** gegen echte Dienste: `tools/manual_check_live.py` prüft sie von Hand; sie brauchen deine Kanäle und Hosts und wurden hier nicht ausgeführt.
- **Die Terminal-Anwendung** bearbeitet die einfachen Einstellungen und zeigt den KI-Status; die Erklärung eines einzelnen roten Workflows und das Bearbeiten von Listen und Maps bleiben in der Seite.
- **Eine Prüfung auf neue Versionen, die herunterlädt oder installiert**: niemals; der Monitor sagt es nur.

## Später

- **Weitere Benachrichtigungsadapter**: ntfy, Microsoft Teams und E-Mail über ein lokales Relay.
- **Mehrere Konten in einer Seite**: Heute läuft jedes Konto in einem eigenen Monitor.
- **Hardware-Telemetrie der Runner** über einen Agenten: Heute wird nur ein optionaler Node-Exporter-Endpunkt gelesen.

## Ideen, die zuerst eine Entscheidung brauchen

- Eine Anmeldeseite, damit der Netzwerkmodus kein einmal eingegebenes Zugriffstoken braucht. Heute ist die Antwort das Zugriffstoken und, fürs Internet, ein Reverse-Proxy mit Authentifizierung (siehe `monitor/docs/DEPLOYMENT.md`).
- Die Logs eines fehlgeschlagenen Schritts in der Seite lesen, mit derselben Bereinigung wie beim KI-Assistenten.
