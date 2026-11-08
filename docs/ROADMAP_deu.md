# Roadmap

Ideen, die nicht in die aktuelle Version passten, ohne versprochene Reihenfolge. Es sind Richtungen, keine Zusagen; ein Issue oder ein Pull Request ist der beste Weg, eine voranzubringen.

## Erledigt in 1.6.6

Korrekturen nach 1.6.5: Der Netzwerkmodus funktioniert jetzt über HTTPS von der Seite aus (die Origin-Prüfung folgt dem Schema der Sitzung), jede vom Schema als sicher markierte Einstellung ändert nur der Rechner selbst, `act` gibt seinen Lauf nach Stopp frei und schließt seine Pipe, eine rote Leiste in den Einstellungen, wenn der Netzwerkmodus auf allen Schnittstellen lauscht, die Sitzung lässt sich per POST statt über die Adresse öffnen, ein Zähler verschluckter Fehler in `--doctor` und Info, `tools/make_screenshots.py` sagt, was es tut, und die Bilder sind neu aufgenommen, und das Änderungsprotokoll ist in acht Sprachen übersetzt.

## Erledigt in 1.6.5

Ein Release für Integrität und Sicherheit, ohne große neue Funktion: Ein grüner Commit braucht den erforderlichen Workflow des Repositorys, ein fehlgeschlagener Fetch stoppt den Start, der Katalog kann kein Werkzeug außerhalb des Werkzeugordners nennen und `dry_run`/`ref` nicht ändern, und ein Stapel ohne aufgezeichnete Commit-Prüfung wird nicht mehr zum Signieren angeboten; `act` bleibt im Arbeitsbereich und Stopp beendet den ganzen Prozessbaum samt Containern des Laufs; der Netzwerkmodus kann HTTPS liefern, sperrt falsche Token und akzeptiert nur IPv4; der Webhook lehnt Wiederholungen und Fluten ab; der MCP-Server übersteht fehlerhafte Nachrichten; `max_per_hour` zählt Nachrichten; Einstellungen werden unter einer Sperre gespeichert; das gespeicherte Token erreicht nur `gh`; `--doctor` warnt vor gefährlichen Kombinationen; der Test der sauberen Installation ist eine eigene Stufe der Release-Prüfung.

## Erledigt in 1.6.4

Isolationstests der Lite-Edition und der Demo, keinerlei Netzwerkanfrage, wenn die Versionsprüfung aus ist oder die Installation abgeschottet ist, ein README, das mit der Wahl des Starters beginnt, `--doctor --json`, eine dauerhafte Leiste für den Netzwerkmodus, die Hilfe und ihre Dokumente in acht Sprachen sowie die optionalen Funktionen (Netzwerkmodus, ein vom Monitor gespeichertes Token, Aktionen auf GitHub, `act`, lokale Kopie von Artefakten, eigene Runner, OpenTelemetry, FinOps nach Job-Labels); siehe Änderungsprotokoll und `ADVANCED.md`.

## Als Nächstes

Was 1.6.4 nicht erreicht hat, und warum:

- **Entschieden, nicht erledigt in 1.6.6**: die aktive Benachrichtigung einer externen KI (standardmäßig aus, eine erste Bestätigung je Anbieter, nur die bereits gefilterten Felder der geschlossenen Liste, ein Limit für Aufrufe und Kosten pro Stunde, der Schlüssel über den Namen einer Umgebungsvariable, und die KI führt nie eine Aktion aus) mit ihrer Variante eines ausgehenden Befehls (geschlossene Liste, keine Shell); und die Repositories mehrerer Besitzer auf einer Seite (der Monitor erkennt ein Repository nur am Namen und braucht daher den Besitzer in jeder Kennung; Grundlage für mehrere Konten). Jedes ist eine eigene Funktion mit eigenem Entwurf und eigenen Tests, deshalb schloss 1.6.6 zuerst die Korrekturen ab.
- **Die älteren Einträge des Änderungsprotokolls in den anderen sieben Sprachen**: Ab 1.6.6 zeigt die Hilfe den Verlauf in jeder Sprache, aber nur der neueste Eintrag ist übersetzt; die älteren behalten den englischen Text unter einem übersetzten Hinweis und werden Version für Version übersetzt, die neueste zuerst.
- **HTTPS hinter einem Proxy auf dem Standardport**: Die Prüfung vergleicht `Host` und `Origin` mit dem Port des Monitors; ein Proxy auf Port 443, der einen `Host` ohne Port weiterleitet, wird noch nicht unterstützt; die Seite funktioniert über einen direkten TLS-Port oder einen Proxy, der den Port beibehält.
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
