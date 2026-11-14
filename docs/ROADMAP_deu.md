# Roadmap

Ideen, die nicht in die aktuelle Version passten, ohne versprochene Reihenfolge. Es sind Richtungen, keine Zusagen; ein Issue oder ein Pull Request ist der beste Weg, eine voranzubringen.

## In 1.8.0 (der nächste Release)

Alles hier Aufgeführte ist geschrieben und getestet; es ist entweder schon im Hauptzweig oder wartet in einem Pull Request. Nichts wird als an echten Diensten bewiesen ausgegeben (siehe „Als Nächstes“).

### Bereits im Hauptzweig

- Eine neue Ordnerstruktur (das Paket in `src/`, die Seite, die Beispiele und die Sprachen in `assets/`) mit einem Migrationswerkzeug, das eine alte flache Installation verschiebt, ohne etwas zu löschen.
- Eine Speicherschicht hinter einer einzigen Schnittstelle, mit dem Datei-Backend, das den Aufbau von `accounts/<id>/` beibehält, atomaren Schreibvorgängen und Sicherungen, die jedes Backend wiederherstellen kann.
- Ein optionales SQLite-Backend (standardmäßig aus), eine Datenbank je Konto, versionierte Migrationen, eine einstellbare Wartezeit und Werkzeuge, um den Zustand zwischen Datei-Backend und SQLite in beide Richtungen zu verschieben, zuerst mit einem Probelauf.
- Die Änderungshistorie ist bis 1.0.0 in den acht Sprachen übersetzt, und ein Test hält sie vollständig.
- Aufbewahrung und Rotation der Historie (Ereignisse und Analysen für eine Anzahl von Tagen, löschen oder archivieren, eine Prüfzeile je Durchlauf, eine Größenwarnung im Doctor; Zustand der Wächter und Konfiguration werden nie angefasst).

### Fertig und wartet auf das Zusammenführen

- Netzwerkmodus: Die Sperrbremse greift wieder, bevor das Token angesehen wird, ein deklarierter Reverse-Proxy gilt nie als dieser Rechner, entfernte Lesezugriffe auf die Einstellungen sind auf das begrenzt, was ein entfernter Client ändern darf, und die Bereitstellungsanleitung enthält das vollständige Rezept.
- Der KI-Feed wird Feld für Feld bereinigt, nur GitHub-Adressen geschlossener Formen passieren, und der Hook liefert keinen Log-Text, nur Repository, Workflow, Ergebnis und Link.
- Identitätsabfragen gehören immer dem Benutzer, ein Lesezugriff wird anhand einer Weißliste beurteilt, und die Token-Datei des zweiten Kontos bleibt im Kontenordner.
- Ein Rauchtest der Seite in einem echten Browser färbt die CI rot, wenn ein Reiter kaputt geht oder eine Funktion doppelt definiert ist.
- Eine einzeilige Fußleiste, die nur sagt, was die Felder oben nicht sagen, eine Zusammenfassung für die KI-Werkzeuge und ein Protokoll, die mit dem laufenden Monitor übereinstimmen, eine Seite, die anzeigt, wenn sie dem Monitor hinterherhinkt, und ein Ton, der sich mit einem Klick freischalten lässt und ein Neuladen übersteht.
- Ein optionales Lesen ruhiger Repositories über GraphQL (standardmäßig aus) mit eigener Abrechnung.
- Die aktive Benachrichtigung einer externen KI (standardmäßig aus, eine erste Bestätigung je Anbieter, nur die geschwärzten Felder einer geschlossenen Liste, eine Obergrenze für Aufrufe und Kosten pro Stunde, der Schlüssel über den Namen einer Variablen, und die KI führt nie eine Aktion aus).
- Die Terminal-Anwendung bearbeitet Listen und Zuordnungen.
- Teammodus (standardmäßig aus): Benutzer, Rollen (admin, maintainer, viewer) und Sitzungen im Speicher, eine Anmeldeseite, ein Bearer-Token für Clients, die kein Browser sind, stabile JSON-Fehler und eine Wiederherstellung eines Administrators über die Konsole dieses Rechners. Der Einzelmodus funktioniert weiter ohne Anmeldung, und die Lite-Ausgabe hat nie eine.
- Eine lebendigere Seite: animierte Symbole, Statuslämpchen, deren Bewegung ihrem Zustand folgt, Reaktionen auf Überfahren, Fokus und Klick; alles aus bei reduzierter Bewegung und schlank in der Lite-Ausgabe.

### Noch in Arbeit

- Stummschaltungen, die sich merken, wer sie gesetzt hat (braucht den Teammodus).

## Geplant, in dieser Reihenfolge

Jede Version enthält alles aus ihrem Abschnitt des Plans: nichts bleibt von einer früheren Version offen, und nichts wird auf die nächste verschoben. Nach 1.8.3 und nach 1.9.3 durchläuft das Produkt eine unabhängige Prüfung, deren Befunde in der folgenden Stabilisierungsversion geschlossen werden. 1.8.1 ist eine Korrekturversion von 1.8.0: Das Feld „Repositories werden geladen“ verschwindet mit dem letzten Repository, und das Neuladen der Seite holt die Daten sofort.

### 1.8.2 - Offizielles Docker-Image und Dienstmodus

Ein mehrstufiges Image mit unprivilegiertem Benutzer, Volumes für Daten und Konfiguration, dokumentierte Umgebungsvariablen, ein Compose-Beispiel mit optionalem Reverse-Proxy und TLS, eine systemd-Unit für die klassische Installation und eine tiefe Gesundheitsprüfung, die fehlschlägt, wenn der Supervisor oder der Zyklus eines Kontos hängt. Ein Zugangsdatum, das GitHub widerruft oder ablaufen lässt, markiert nur dieses Konto als blind, löst einen kritischen Systemalarm aus und lässt sich ersetzen, ohne den Supervisor neu zu starten. Sicherung, Aktualisierung und erster Start als Dienst sind dokumentiert; die Seite sagt, ob sie auf diesem Rechner, im Netzwerk oder hinter einem Proxy lauscht; die Kommandozeile arbeitet gegen einen entfernten Monitor. Die Lite-Ausgabe bleibt lokal. Außerdem: ein Bericht über die Wartezeit der Jobs in der Warteschlange je Runner.

### 1.8.3 - Benachrichtigungen je Benutzer

Einstellungen je Benutzer (Kanal, Wächter, niedrigste Stufe), ein Verteiler, der anhand von Einstellungen und Rollen entscheidet, wer benachrichtigt wird, Kanäle als einfache Plug-ins und Zusammenfassungen der noch ungelesenen Alarme. Außerdem: ein wegen der beobachteten Pfade übersprungener Job wird getrennt von einem roten Job angezeigt.

### 1.8.4 - Stabilisierung

Keine großen Funktionen. Isolation zwischen Konten, die Seite, der Speicher, Anmeldung und Rollen, Benachrichtigungen, ein GitHub, das zeitweise ausfällt, der Start nach einer unterbrochenen Migration, die Wiederherstellung nach einem Abbruch, ein erweiterter Doctor, die Stellen, die auf GitHub schreiben, Protokolle ohne Token, eine Sicherheits-Checkliste für den Teammodus und Dokumente, die zum Verhalten passen. Die Serie läuft nur bei Bedarf bis 1.8.9 weiter.

### 1.9.0 - Eine Bewertung

Metrik-Sammler je Konto und je Wächter (Erfolgsquote, Dauer, Zeit bis zur Behebung, Durchsatz), eine Bewertungs-Engine mit änderbaren Schwellen, ein Trend gegenüber dem Vorzeitraum, im Speicher abgelegte Momentaufnahmen, ein Bewertungs-Widget mit Sparkline, Alarme bei sinkender Bewertung und ein Kommandozeilen-Verb, das sie ausgibt.

### 1.9.1 - Sicherheitswächter

Der dritte Wächter: Dependabot, Code-Scanning, Secret-Scanning, Branch-Schutz, Workflow-Berechtigungen und Code-Besitzer, mit Regeln je Signalart, demselben Filter im Reiter Alarme und einem Abzug in der Bewertung für offene kritische Alarme. Optional, im selben Release: Workflow-Hygiene (Actions, die nicht an einen Commit gebunden sind, Jobs ohne Zeitlimit, Workflows ohne Berechtigungen oder ohne Nebenläufigkeitsregel, gefährliche Nutzung von pull_request_target), aufgebaut auf dem Workflow-Prüfer, den das Projekt schon hat.

### 1.9.2 - Gesundheit von Repository und Team

Eine Gesundheitsansicht je Repository (CI, Issues und Pull Requests, Sicherheit, Release-Bereitschaft, Aktivität) und eine fürs Team mit Rangliste, Summen und Filtern; Seiten für beide mit Direktlinks für Wandbildschirme. Optional, im selben Release: ein Panel nächtlicher Benchmarks gegen ein Budget (Median gegen eine Basislinie je Maschinenklasse) und ein Panel mit Software-Stücklisten und Attestierungen jedes Releases.

### 1.9.3 - Geplante Berichte und Prüfprotokoll

Berichtsvorlagen in HTML und Markdown (PDF optional) mit Bewertung, wichtigsten Alarmen und Änderungen, ein Planer und ein nur anhängendes Prüfprotokoll, wer was wann getan hat, ohne jedes Geheimnis darin. Optional, im selben Release: eine Ansicht „Release bereit / blockiert“ mit dem letzten grünen Commit jedes Repositorys.

### 1.9.4 - Stabilisierung der dritten Phase

Derselbe Abschluss wie bei 1.8.4 für Bewertung, Sicherheitswächter, Gesundheitsansichten, Berichte und Prüfprotokoll; die Kosten an API-Aufrufen bei drei laufenden Wächtern; eine Bewertung, die stimmig bleibt, wenn ein Wächter aus ist.

### 2.0.0 - Reife

Eine Hauptversion, die technische Schulden abbaut und die öffentlichen Schnittstellen einfriert: Wächter, Speicher, Alarme, das Ereignisschema und die Lese-API, mit einer Suite von Vertragstests, die Clients gegen jedes Release ausführen können. Eine Anleitung für jede Nutzungsart (Lite, einzeln, Dienst, Team) und eine Referenz für Einstellungen, Ereignisse, Metriken und API. Ab 2.0.1 gibt es ein Polster für das, was erst bei langer echter Nutzung auftaucht.

Die Workflows des Monitors selbst halten ein, was der Hygiene-Wächter von anderen verlangen wird: an einen Commit gebundene Actions, minimale Berechtigungen und ein Zeitlimit für jeden Job.

## Erledigt in 1.7.9

### Behoben

## Erledigt in 1.7.8

### Hinzugefügt

## Erledigt in 1.7.7

### Hinzugefügt

## Erledigt in 1.7.6

Die Verbindung zwischen Monitor und KI-Werkzeug: Der Feed stimmt immer mit der Seite überein, jede Warnung sagt, warum sie rot ist, ein Stream und drei MCP-Werkzeuge schieben die Neuigkeiten nach, ein Befehl installiert das Gate-Skript, die Leiste zeigt, ob eine KI verbunden ist, und jede Zustandsdatei gehört nur ihrem Besitzer.

## Erledigt in 1.7.5

Die Befehlszeile nimmt das Zugriffstoken unter seinem eigenen Namen, der Netzwerkmodus ist standardmäßig sicherer (die Adresse des Rechners wird vor dem Netz verborgen, die alte Adresse ?access= lässt sich abschalten, Benachrichtigungsziele im lokalen Netz werden abgelehnt, Warnung vor einfachem HTTP), Zeiten für Menschen nutzen deine eigene Zeitzone, ein Alarm lässt sich bis zur Änderung des Elements stummschalten, und falsche Zählungen und Prüfungen sind korrigiert.

## Erledigt in 1.7.4

Eine Leiste am Fuß der Seite mit dem wichtigsten Hinweis (und einem Fenster mit allen), der Verbindung, dem Kontingent, der letzten Lesung, dem Modus, der Adresse und der Uhr; ein Vollbild-Knopf; Tabellen für Repositories und Verlauf, die nach einer oder mehreren Spalten sortieren, mit den Spalten deiner Wahl; `monitor_cli.py`, die Befehlszeile als Client des laufenden Monitors (`status`, `health`, `alerts`, `accounts`, `live`, `doctor`) mit `--json` und stabilen Exit-Codes samt Anleitung in acht Sprachen; die auf Reihenfolge geprüften Änderungsprotokolle, die README des Pakets ohne Verlauf darin und neu gezeichnete Bilder.

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

- **Mehrere Eigentümer in einem Prozess und einer Seite**: Seit 1.7.0 ist jedes Konto ein eigener Monitor und die Seite zeigt sie nebeneinander, aber innerhalb eines Monitors wird ein Repository weiterhin nur über seinen Namen identifiziert, sodass zwei Eigentümer im selben Monitor sich vermischen würden. Sie in einen Prozess zu bringen, verlangt den Eigentümer in jedem Bezeichner (die Abfragen, die Alarm-Kennungen, die Listen der Einstellungen, die Wächter und die Seite); ohne Repositories zweier echter Eigentümer ließ es sich nicht belegen, daher bleiben die Konten von 1.7.0 der Weg, sie getrennt zu halten.
- **Der Abrechnungsbericht mit einem Login, der ihn lesen darf**: Die echte Antwort für einen Login ohne den Scope `user` ist „nicht gefunden“, und der Monitor fällt auf die Schätzung zurück (geprüft); die Zahlen selbst wurden nicht mit einem Abrechnungskonto verglichen.
- **Die Preise größerer Runner** in `quotas.json` stammen aus dem Gedächtnis der öffentlichen Preisliste und sind als ungeprüft markiert; vergleiche sie mit der Abrechnungsseite von GitHub und bearbeite die Datei.
- **`gh copilot`**: Seine Optionen werden mit `gh copilot -- --help` geprüft, was die Copilot-Kommandozeile braucht; sie ist hier nicht installiert, die Optionen bleiben ungeprüft.
- **Benachrichtigungen, Webhook, Enterprise Server und die Dienstbeispiele** gegen echte Dienste: `tools/manual_check_live.py` prüft sie von Hand; sie brauchen deine Kanäle und Hosts und wurden hier nicht ausgeführt.
- **Die Terminal-Anwendung** bearbeitet die einfachen Einstellungen, Listen und Zahlen-Maps und zeigt den KI-Status; die Erklärung eines einzelnen roten Workflows bleibt auf der Seite.
- **Nur der Eigentümer kann sie an einer echten Installation belegen**: mehrere Konten mit dem Collab-Wächter auf echten Repositories, eine GitHub App und ein zweites Nur-Lese-Konto mit echten Schlüsseln sowie der HTTPS-Proxy mit einem echten Zertifikat. Sie werden von Hand geprüft (`tools/manual_check_live.py`) und nicht als erledigt ausgegeben.
- **Eine Prüfung auf neue Versionen, die herunterlädt oder installiert**: niemals; der Monitor sagt es nur.

## Später

- **Weitere Benachrichtigungsadapter**: ntfy, Microsoft Teams und E-Mail über ein lokales Relay.
- **Mehrere Konten in einer Seite**: in 1.7.0 erledigt, jedes Konto in einem eigenen Monitor unter einem Supervisor.
- **Hardware-Telemetrie der Runner** über einen Agenten: Heute wird nur ein optionaler Node-Exporter-Endpunkt gelesen.

## Ideen, die zuerst eine Entscheidung brauchen

- Die Logs eines fehlgeschlagenen Schritts in der Seite lesen, mit derselben Bereinigung wie beim KI-Assistenten.
