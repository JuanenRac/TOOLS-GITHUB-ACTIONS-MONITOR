# Roadmap

Ideen, die nicht in die aktuelle Version passten, ohne versprochene Reihenfolge. Es sind Richtungen, keine Zusagen; ein Issue oder ein Pull Request ist der beste Weg, eine voranzubringen.

## Erledigt in 1.7.3

Ein zweiter Wächter für Issues und Pull Requests (Collab, standardmäßig aus, nur lesend, mit eigener Uhr), ein Reiter Alarme mit den Alarmen aller Wächter und Filter nach Herkunft und Stufe, lokale Stummschaltungen, die von selbst enden (ein Alarm, eine Regel oder ein Wächter; `alerts.mute_hours`), das Label, das ein Element ignorieren lässt, `GET /api/alerts` und `GET /api/events`, eine Checkliste für die Live-Ansicht, eine Anleitung zum Collab-Wächter in acht Sprachen und neu gezeichnete Bilder.

## Erledigt in 1.7.2

Die Kopfzeile mit ihren Zahlen in einer lesbaren Reihenfolge und in einem Raster, das der Breite folgt; die Schnellsteuerung (nur heiße, Geschwindigkeit, Gesundheit der Ökosysteme) fest oben rechts; Einstellungen, Hilfe und Info nur in der Seitenleiste; der Hinweis auf eine neue Version nicht mehr in der Kopfzeile; und die Tests, die keine Dateien mehr neben dem Code hinterlassen.

## Erledigt in 1.7.1

Eine Seite mit Seitenleiste (das Logo, die Kontoauswahl, die Bereiche in einklappbaren Gruppen, die Hilfe) und sechzehn Designs zusätzlich zu automatisch, hell und dunkel, die des Studios des Alarmsystems; und der CI-Wächter hinter einem Vertrag (`BaseSentinel`, `Alert`, `SentinelRegistry`, `SentinelCI`), damit weitere Wächter hinzukommen können, ohne dass der Monitor wissen muss, was jeder tut. Was angezeigt und entschieden wird, ändert sich nicht.

## Erledigt in 1.7.0

Mehrere Konten in der kompletten Ausgabe, jedes ein eigener Monitor unter einem Supervisor (`accounts/<id>/`, `--accounts`, `--account`, `--migrate-accounts`), die API der Konten, ein Webhook für alle, die Seite mit Auswahl und den Karten aller Konten, die Ansichten per Adresse (`?view=` und `?chrome=0`) und die Live-Ansicht mit dem Zustand des Webhook-Empfängers. Die Lite-Ausgabe bleibt unverändert.

## Erledigt in 1.6.8

Der HTTPS-Proxy aus 1.6.7 wird gegen einen echten Proxy auf Port 443 geprüft (`tools/manual_check_live.py proxy` und Tests, die einen Client über TLS, einen Reverse-Proxy und den Monitor durchlaufen), die Bilder sind neu aufgenommen mit zwei neuen zum Netzwerkmodus, und die Änderungshistorie ist in den anderen sieben Sprachen bis 1.6.3 übersetzt.

## Erledigt in 1.6.7

Ein HTTPS-Proxy auf dem Standardport 443 funktioniert jetzt mit dem Netzwerkmodus (`listen.proxy_public_host`, standardmäßig leer: der eine öffentliche Name des Proxys wird ohne Port akzeptiert, nur unter HTTPS, und er lässt sich nur vom Rechner selbst ändern), und die Änderungshistorie ist in den anderen sieben Sprachen für 1.6.7, 1.6.6 und 1.6.5 übersetzt.

## Erledigt in 1.6.6

Korrekturen nach 1.6.5: Der Netzwerkmodus funktioniert jetzt über HTTPS von der Seite aus (die Origin-Prüfung folgt dem Schema der Sitzung), jede vom Schema als sicher markierte Einstellung ändert nur der Rechner selbst, `act` gibt seinen Lauf nach Stopp frei und schließt seine Pipe, eine rote Leiste in den Einstellungen, wenn der Netzwerkmodus auf allen Schnittstellen lauscht, die Sitzung lässt sich per POST statt über die Adresse öffnen, ein Zähler verschluckter Fehler in `--doctor` und Info, `tools/make_screenshots.py` sagt, was es tut, und die Bilder sind neu aufgenommen, und das Änderungsprotokoll ist in acht Sprachen übersetzt.

## Erledigt in 1.6.5

Ein Release für Integrität und Sicherheit, ohne große neue Funktion: Ein grüner Commit braucht den erforderlichen Workflow des Repositorys, ein fehlgeschlagener Fetch stoppt den Start, der Katalog kann kein Werkzeug außerhalb des Werkzeugordners nennen und `dry_run`/`ref` nicht ändern, und ein Stapel ohne aufgezeichnete Commit-Prüfung wird nicht mehr zum Signieren angeboten; `act` bleibt im Arbeitsbereich und Stopp beendet den ganzen Prozessbaum samt Containern des Laufs; der Netzwerkmodus kann HTTPS liefern, sperrt falsche Token und akzeptiert nur IPv4; der Webhook lehnt Wiederholungen und Fluten ab; der MCP-Server übersteht fehlerhafte Nachrichten; `max_per_hour` zählt Nachrichten; Einstellungen werden unter einer Sperre gespeichert; das gespeicherte Token erreicht nur `gh`; `--doctor` warnt vor gefährlichen Kombinationen; der Test der sauberen Installation ist eine eigene Stufe der Release-Prüfung.

## Erledigt in 1.6.4

Isolationstests der Lite-Edition und der Demo, keinerlei Netzwerkanfrage, wenn die Versionsprüfung aus ist oder die Installation abgeschottet ist, ein README, das mit der Wahl des Starters beginnt, `--doctor --json`, eine dauerhafte Leiste für den Netzwerkmodus, die Hilfe und ihre Dokumente in acht Sprachen sowie die optionalen Funktionen (Netzwerkmodus, ein vom Monitor gespeichertes Token, Aktionen auf GitHub, `act`, lokale Kopie von Artefakten, eigene Runner, OpenTelemetry, FinOps nach Job-Labels); siehe Änderungsprotokoll und `ADVANCED.md`.

## Als Nächstes

Was 1.6.4 nicht erreicht hat, und warum:

- **Entschieden, nicht erledigt in 1.6.6**: die aktive Benachrichtigung einer externen KI (standardmäßig aus, eine erste Bestätigung je Anbieter, nur die bereits gefilterten Felder der geschlossenen Liste, ein Limit für Aufrufe und Kosten pro Stunde, der Schlüssel über den Namen einer Umgebungsvariable, und die KI führt nie eine Aktion aus) mit ihrer Variante eines ausgehenden Befehls (geschlossene Liste, keine Shell); und die Repositories mehrerer Besitzer auf einer Seite (der Monitor erkennt ein Repository nur am Namen und braucht daher den Besitzer in jeder Kennung; Grundlage für mehrere Konten). Jedes ist eine eigene Funktion mit eigenem Entwurf und eigenen Tests, deshalb schloss 1.6.6 zuerst die Korrekturen ab.
- **Die älteren Einträge des Änderungsprotokolls in den anderen sieben Sprachen**: Die Hilfe zeigt den Verlauf in jeder Sprache, und 1.6.8 bis 1.6.3 sind übersetzt; 1.6.2 und ältere behalten den englischen Text unter einem übersetzten Hinweis und werden Version für Version übersetzt, von der neuesten zur ältesten.
- **Mehrere Eigentümer in einem Prozess und einer Seite**: Seit 1.7.0 ist jedes Konto ein eigener Monitor und die Seite zeigt sie nebeneinander, aber innerhalb eines Monitors wird ein Repository weiter nur über seinen Namen erkannt, sodass sich zwei Eigentümer im selben Monitor mischen würden. Die Konten von 1.7.0 sind der Weg, sie getrennt zu halten; sie in einen Prozess zu holen, mit dem Eigentümer in jedem Bezeichner, ist das, was bleibt.
- **Der Abrechnungsbericht mit einem Login, der ihn lesen darf**: Die echte Antwort für einen Login ohne den Scope `user` ist „nicht gefunden“, und der Monitor fällt auf die Schätzung zurück (geprüft); die Zahlen selbst wurden nicht mit einem Abrechnungskonto verglichen.
- **Die Preise größerer Runner** in `quotas.json` stammen aus dem Gedächtnis der öffentlichen Preisliste und sind als ungeprüft markiert; vergleiche sie mit der Abrechnungsseite von GitHub und bearbeite die Datei.
- **`gh copilot`**: Seine Optionen werden mit `gh copilot -- --help` geprüft, was die Copilot-Kommandozeile braucht; sie ist hier nicht installiert, die Optionen bleiben ungeprüft.
- **Benachrichtigungen, Webhook, Enterprise Server und die Dienstbeispiele** gegen echte Dienste: `tools/manual_check_live.py` prüft sie von Hand; sie brauchen deine Kanäle und Hosts und wurden hier nicht ausgeführt.
- **Die Terminal-Anwendung** bearbeitet die einfachen Einstellungen und zeigt den KI-Status; die Erklärung eines einzelnen roten Workflows und das Bearbeiten von Listen und Maps bleiben in der Seite.
- **Eine Prüfung auf neue Versionen, die herunterlädt oder installiert**: niemals; der Monitor sagt es nur.

## Später

- **Weitere Benachrichtigungsadapter**: ntfy, Microsoft Teams und E-Mail über ein lokales Relay.
- **Mehrere Konten in einer Seite**: in 1.7.0 erledigt, jedes Konto in einem eigenen Monitor unter einem Supervisor.
- **Hardware-Telemetrie der Runner** über einen Agenten: Heute wird nur ein optionaler Node-Exporter-Endpunkt gelesen.

## Ideen, die zuerst eine Entscheidung brauchen

- Eine Anmeldeseite, damit der Netzwerkmodus kein einmal eingegebenes Zugriffstoken braucht. Heute ist die Antwort das Zugriffstoken und, fürs Internet, ein Reverse-Proxy mit Authentifizierung (siehe `monitor/docs/DEPLOYMENT.md`).
- Die Logs eines fehlgeschlagenen Schritts in der Seite lesen, mit derselben Bereinigung wie beim KI-Assistenten.
