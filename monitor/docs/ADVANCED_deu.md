<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Erweiterte Funktionen (alle standardmäßig aus)

Alles auf dieser Seite ist **aus, bis du es einschaltest** unter *Einstellungen > Erweitert* (oder in `actions_monitor.json`), und die Schlüssel, die entscheiden, wer den Monitor erreicht oder was er auf GitHub tun darf, sind als Sicherheitsoptionen markiert. Schalte nur ein, was du brauchst.

## Im Netzwerk lauschen

Standardmäßig antwortet die Seite nur auf `127.0.0.1`. Mit `listen.network` an (Neustart nötig) lauscht sie auch auf `listen.host`: eine private Adresse dieses Rechners oder `0.0.0.0` für alle Schnittstellen. Eine öffentliche Adresse wird abgelehnt.

- **Jede Anfrage braucht das Zugriffstoken** (Cookie, Header `X-Monitor-Access` oder `Authorization: Bearer`). Das Token ist der Wert der in `listen.token_env` genannten Umgebungsvariable (mindestens 16 Zeichen); ohne sie entsteht bei jedem Start ein Zufallstoken, das einmal in der Konsole erscheint. Öffne die dort ausgegebene Adresse einmal: Sie setzt das Cookie und führt zur sauberen Adresse.
- Das Einmal-Token der Seite ist erzwungen, die Seite zeigt auf jedem Tab eine rote Leiste, solange der Modus an ist, und die Schlüssel von `listen.*`, `github_token.*`, `act.*` und `github_actions.*` lassen sich nur vom Rechner selbst ändern.
- `listen.allowed_hosts` listet die Namen, unter denen die Seite geöffnet werden darf (Schutz gegen DNS-Rebinding).
- **Risiken.** Der Verkehr ist unverschlüsseltes HTTP: Wer dein Netz mitlesen kann, kann Token und Daten lesen. Nutze es nur in einem vertrauenswürdigen Netz oder setze einen Reverse-Proxy mit HTTPS davor (siehe `DEPLOYMENT.md`). Setze es nie dem Internet aus. Die Lite-Edition lauscht nie über diesen Rechner hinaus.

## Ein vom Monitor gespeichertes GitHub-Token

Standard bleibt deine eigene `gh`-Anmeldung. Mit `github_token.enabled` an kannst du unter Einstellungen > Erweitert ein Token einfügen: Es liegt im sicheren Speicher des Systems (Windows-DPAPI, macOS-Schlüsselbund, Linux Secret Service) und nur wenn dieser fehlt in einer Datei mit Rechten 600 (die Seite sagt es). Es wird nie in `actions_monitor.json`, ein Log, das Info-Fenster oder den Support-Text geschrieben und erreicht `gh` nur über die Umgebung des Prozesses. Die Schaltfläche **Token löschen** entfernt es überall.

## Aktionen auf GitHub

Mit `github_actions.enabled` an kann der Monitor einen fehlgeschlagenen Lauf wiederholen (`rerun_failed`, `rerun_run`, `rerun_job`), einen Lauf abbrechen (`cancel`), ein Issue oder einen Pull Request schließen (`close_issue`, `close_pr`) und einen mergen (`merge_pr`, mit `github_actions.merge_method`). Nur die Namen in `github_actions.allowed` sind nutzbar (standardmäßig `rerun_failed` und `cancel`). **Jede Aktion wird einzeln bestätigt**: Die Seite zeigt genau, was gesendet wird (Methode und Endpunkt), und sendet nichts, bis du diesen Plan mit dem Einmal-Token bestätigst. Das GitHub-Token braucht die Berechtigung (`workflow` für Läufe, `repo` für Issues und Pull Requests; sonst wird die Ablehnung von GitHub angezeigt). Jeder Versuch wird in `github_actions_log.jsonl` protokolliert. Der KI-Assistent hat keine Möglichkeit, eine davon zu starten.

## Einen Workflow hier mit act ausführen

Mit `act.enabled` an und den Einträgen `repository:datei.yml:ereignis` in `act.allowed` (alle drei exakt) führt eine Schaltfläche `act` auf dem lokalen Klon aus, nachdem du die genaue Befehlszeile bestätigt hast. Es werden keine echten Secrets übergeben (leere Secret-, Variablen-, Umgebungs- und Eingabedateien sowie eine minimale Umgebung ohne Token), die Ausgabe erscheint laufend, jeweils ein Lauf, mit dem Zeitlimit `act.timeout_seconds`, und du kannst ihn stoppen.

## Lokale Kopie von Artefakten

Mit `mirror.enabled` an und einem `mirror.folder` auf diesem Rechner werden die Artefakte beendeter Läufe dorthin kopiert (`mirror.max_per_cycle` pro Zyklus, `mirror.max_mb` für den Ordner, `mirror.keep_days` Aufbewahrung), jedes einmal, mit bereinigten Namen innerhalb des Ordners.

## Eigene Runner

Mit `runners.enabled` an zeigt Einstellungen > Erweitert jeden Runner als frei, belegt oder offline. Festplatte und Last erscheinen nur für Runner in `runners.metrics` ({Name: Adresse eines Node Exporters auf diesem Rechner oder einer privaten Adresse}).

## OpenTelemetry

Mit `otlp.enabled` an und einem `otlp.endpoint` (HTTPS oder HTTP auf diesem Rechner) gehen beendete Läufe als Traces und die Kopfzahlen als Metriken hinaus (OTLP/HTTP mit JSON), jeder Lauf einmal. Gesendet werden nur Repository, Workflow, Branch, Ereignis, Ergebnis und Dauer.

## Organisationen und Kosten

- `organizations.discover` listet die Organisationen des Logins unter Einstellungen > Basis. Um eine zu überwachen, starte einen zweiten Monitor mit darauf gesetztem `github_owner`.
- `finops.jobs_per_cycle` über 0 liest pro Zyklus die Labels der Jobs so vieler beendeter privater Läufe, damit die Minuten den richtigen Faktor nutzen (Linux, Windows, macOS und die größeren Runner aus `quotas.json`) statt eines angenommenen Systems. Mit dem Abrechnungsbericht an (`quota.billing_api`) erscheinen auch die Dollar für Codespaces und Packages, der genutzte Speicher und der Preis der Minuten über den enthaltenen.

## Gegen die echten Dienste prüfen

`python tools/manual_check_live.py` (im Repository) liest die Scopes deines Tokens, den Abrechnungsbericht, die Organisationen, die Runner und die Optionen von `gh copilot` und bittet einen laufenden Monitor, über deine Kanäle eine Testnachricht zu senden. Es fragt nie nach einem Geheimnis.
