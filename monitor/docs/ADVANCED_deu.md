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
- **HTTPS.** Mit deinem eigenen Zertifikat und Schlüssel (`listen.tls_cert_file`, `listen.tls_key_file`) liefert der Monitor selbst HTTPS aus; hinter einem Proxy, der das für dich übernimmt, setze `listen.secure_cookie`. In beiden Fällen sendet der Browser bei jeder Änderung `Origin: https://host:port`, und die Prüfung akzeptiert genau das Schema der Sitzung (das andere Schema, ein anderer Host, ein anderer Port oder ein fehlerhafter Origin werden abgelehnt). Die vom Browser verwendete Adresse muss den Port des Monitors enthalten, außer hinter einem HTTPS-Proxy auf dem Standardport 443, der `Host` und `Origin` ohne Port weiterleitet: trage seinen öffentlichen Namen in `listen.proxy_public_host` ein (nur ein Hostname, standardmäßig leer). Er zählt nur unter HTTPS, nur dieser eine Name wird ohne Port akzeptiert, und er lässt sich nur vom selben Rechner aus ändern.
- **Sitzung per POST öffnen.** Statt der Adresse mit `?access=` kannst du `POST /api/access` mit dem JSON `{"token": "..."}` senden: Das Token bleibt aus Adresszeile, Verlauf und Protokollen heraus, und das Cookie kommt in der Antwort zurück. Die Adresse mit `?access=` ist veraltet: Sie funktioniert standardmäßig weiter (nichts Eingerichtetes bricht) und nur bei einem `GET`, aber das Token bleibt im Verlauf, in den Protokollen und im `Referer`, und der Monitor antwortet mit einem `Deprecation`-Header. Schalte `listen.query_access` aus, um sie abzulehnen und die Sitzung nur mit `POST /api/access` oder dem Header `X-Monitor-Access` zu öffnen. Eine rote Leiste oben in den Einstellungen warnt, wenn `listen.host` `0.0.0.0` ist. Jede Einstellung, die das Schema als sicher markiert (nicht nur `listen.*`, `github_token.*`, `act.*` und `github_actions.*`: auch Webhook, KI-Aktionen, Benachrichtigungen, OpenTelemetry, Spiegel, Runner und Ausgaben), kann nur vom Rechner selbst geändert werden.
- **Erste Schritte beim Lauschen im Netzwerk.** Schalte zuerst `listen.query_access` aus (dann reist das Token nie in einer Adresse, einem Verlauf oder einem Log; öffne die Sitzung mit `POST /api/access` oder dem Header) und stelle HTTPS (ein Zertifikat in `listen.tls_cert_file` oder einen HTTPS-Proxy) oder ein VPN davor. Die Konsole wiederholt das beim Start des Netzwerkmodus, solange die alte Adresse noch akzeptiert wird.

## Teammodus: Benutzer und Rollen

Standardmäßig aus: eine Person nutzt den Monitor ohne Anmeldung. Mit `auth.enabled` an (ohne Neustart) ändert sich nichts, bis der erste Administrator existiert. Die Lite-Edition hat nie eine Anmeldung.

- **Erster Administrator.** `/login` auf dem Rechner öffnen, auf dem der Monitor läuft, und ihn anlegen (nur von diesem Rechner und nur einmal; eine Anfrage über einen Proxy wird abgelehnt). Oder auf der Konsole: `python -m github_actions_monitor.security.auth_cli create-admin NAME --password-env VAR` (das Passwort steht nie in der Befehlszeile). Danach verlangt die Seite eine Anmeldung; `reset-password` und `revoke` desselben Werkzeugs stellen ein verlorenes Administratorpasswort wieder her.
- **Rollen.** `viewer` liest (jedes GET); `maintainer` schaltet zusätzlich Alarme stumm, bestätigt sie und ändert den Arbeitsmodus; `admin` ändert zusätzlich Einstellungen, Benutzer und alles, was GitHub oder die Außenwelt erreichen kann. Eine nicht aufgeführte Route ist für alle außer Admins gesperrt. Jeder Benutzer hat außerdem die Liste der Konten, die er sehen darf (Admins sehen alle): ein anderes Konto mit `?account=` oder `X-Account-Id` antwortet 403 `account_scope`, in der API und in den Exporten.
- **Sitzungen.** Der Browser erhält das Cookie `monitor_session` (HttpOnly, SameSite=Strict, Secure bei HTTPS) und ein CSRF-Token (`X-CSRF-Token`, von der Anmeldung und von `/api/auth/me` geliefert), das jedes POST senden muss. Ein Skript oder eine App nutzt `POST /api/auth/login` mit `{"client": "api"}` und sendet das erhaltene Token als `Authorization: Bearer msn_...` (nur solange `auth.allow_bearer` an ist; standardmäßig ist es aus). Das Einmal-Token der Seite (`session_guard`) gilt weiterhin zusätzlich zur Sitzung.
- **Passwörter** werden nur als gesalzener scrypt-Hash gespeichert und brauchen `auth.min_length` Zeichen. Nach `auth.max_failed_logins` falschen Passwörtern wird der Benutzer `auth.lockout_minutes` gesperrt, und jede Adresse hat ein eigenes Anfragelimit. Ein neues Passwort, eine neue Rolle oder ein neuer Zustand beendet die Sitzungen dieses Benutzers; es bleibt immer mindestens ein aktiver Administrator.
- **Endpunkte.** `/api/auth/login`, `logout`, `me`, `bootstrap`, `password`; für Admins `/api/auth/users` (mit `/update`, `/delete`, `/revoke`) und `/api/auth/audit`. Fehler sind JSON mit stabilem Code: `{"error": "...", "code": "..."}`.
- **Protokoll.** `auth_audit.jsonl` (private Datei; eine ältere Kopie bleibt erhalten) hält Anmeldungen, Sperren, abgelehnte Anfragen und Benutzeränderungen fest; nie ein Passwort, einen Hash oder ein Token. `auth.audit` schaltet es ab.
- **Mehrere Konten.** Mit den Konten aus `ACCOUNTS.md` listet `GET /api/accounts` nur die dem Benutzer zugewiesenen Konten auf, und nur diese erreichen `/api/accounts/<id>/status` und jede Anfrage mit `?account=` oder `X-Account-Id` (ein Admin sieht alle). Der Monitor eines Kontos erfährt, wer handelt; eine Stummschaltung im Tab Alarme hält daher fest, wer sie gemacht hat (`muted_by` in `GET /api/alerts` und im Verlauf der Stummschaltungen).
- **Die Seite.** Ein Feld in der Kopfzeile zeigt Name und Rolle der angemeldeten Person und öffnet ein Menü: mein Passwort ändern, die Benutzer und das Protokoll (Administratoren), abmelden. Jede Änderung der Seite trägt das CSRF-Token; im Einzelmodus und in der Lite-Edition zeichnet die Seite nichts und fragt nichts Neues.
- **Risiko.** Über unverschlüsseltes HTTP in einem Netz laufen Cookie und Passwörter im Klartext: HTTPS oder ein VPN nutzen, wie beim Netzwerkmodus.

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

## Sicherheitshinweise (vor dem Einschalten lesen)

- **Netzwerkmodus**: nur in einem vertrauenswürdigen Netz verwenden. Das Zugriffstoken ersetzt keine Verschlüsselung; über einfaches HTTP laufen Token und Daten im Klartext. Einen HTTPS-Proxy davorschalten (und `listen.secure_cookie` setzen) oder dem Monitor ein eigenes Zertifikat samt Schlüssel geben (`listen.tls_cert_file`, `listen.tls_key_file`): Dann liefert er selbst HTTPS (TLS 1.2 oder neuer) und startet nicht, wenn die Dateien nicht nutzbar sind. Eine private Adresse dieses Rechners ist besser als alle Schnittstellen. Es werden nur IPv4-Adressen akzeptiert. Nach dem ersten Besuch wird das Token aus der Adresszeile entfernt; das Cookie ist HttpOnly, SameSite=Strict (und Secure bei HTTPS). Eine Adresse, die innerhalb einer Minute `listen.max_failed_attempts` falsche Token sendet, wird fünf Minuten abgelehnt. `/metrics` und `dashboard.json` listen deine Repositories auf: Im Netzwerkmodus brauchen sie ebenfalls das Token.
- **Aktionen auf GitHub**: **standardmäßig aus, eine Bestätigung je Aktion, geschlossene Liste** (Lauf oder Job wiederholen, abbrechen, Issue oder Pull Request schließen, einen Pull Request mergen, wenn du ihn freigibst). Branches oder Repositories löschen sowie Geheimnisse und Einstellungen gibt es **nicht**. Die KI kann eine kleinere Liste vorschlagen (`rerun_failed`, `rerun_run`, `close_issue`) und merged nie.
- **act**: standardmäßig aus, jeder Lauf bestätigt, geschlossene Liste `Repository:Datei:Ereignis`, keine echten Geheimnisse. Der Klon muss ein echter Ordner im Arbeitsbereich sein: Ein Ordner, der ein Link an eine andere Stelle ist, wird abgelehnt, außer `act.allow_symlinks` ist an. Zeitlimit und Stopp beenden den ganzen Prozessbaum des Laufs und entfernen die dabei erzeugten `act-`-Container.
- **Dein eigenes Token** liegt im Speicher des Systems, wenn es einen gibt; die einfache Datei (Rechte 600) ist der schwächste Speicher. Es geht nur an `gh`, nie an `act` oder deine Befehle. `--doctor` zeigt den Speicher, nie das Token.
- **Zu vermeidende Kombinationen** (`--doctor` nennt sie): Netzwerkmodus auf allen Schnittstellen; KI-Aktionen, die bei aktivem Netzwerkmodus ausführen; `act` bei aktivem Netzwerkmodus; das Token in einer einfachen Datei.
- Der MCP-Server spricht nur über Standardeingabe und -ausgabe; niemals hinter einen Netzwerkport legen.

`listen.trusted_proxy` (standardmäßig aus): nur wenn ein EIGENER Reverse-Proxy auf DEMSELBEN Computer der einzige Zugang ist. Fehlversuche werden dann der letzten Adresse aus `X-Forwarded-For` zugerechnet (die dein Proxy anfügt: in nginx `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`) und nicht dem Proxy, außerdem allen Clients des Proxys zusammen mit einem dreimal höheren Limit. Der Monitor glaubt diesen Header bei jeder Verbindung über Loopback; nutze es daher nie mit einem Proxy auf einem anderen Rechner und lass es aus, wenn jemand anderes den Monitor direkt erreichen kann. Ist ein Proxy deklariert (`listen.proxy_public_host`, `listen.secure_cookie` oder `listen.trusted_proxy`), gilt nichts, was am Hauptport ankommt, als dieser Computer; `listen.local_port` (0 = aus, sonst 1024 bis 65535) öffnet einen zweiten Port, der nur auf `127.0.0.1` lauscht, für die Person am Rechner des Monitors (siehe Bereitstellungsanleitung).

## Die Aktualisierungsschleife: Herzschlag und Wächter

`/api/data` liefert zusätzlich `loop`: die Phase des Aktualisierungszyklus (`collect`, `maintain`, `publish`, `log`, `extras`, `idle`), wie lange der Zyklus läuft, den letzten guten Zyklus, den letzten Fehler samt Phase, die Neustarts und jedes Problem beim Schreiben des Protokolls oder der Übersicht für die KI. Die untere Leiste der Seite zeigt es rot, wenn ein Zyklus viel zu lange läuft, und als Warnung, wenn eine Datei nicht geschrieben werden kann. Ein Wächter startet einen Zyklus, der länger als `watchdog_minutes` läuft (Standard 10, 0 schaltet ihn aus), in einem neuen Thread neu, nachdem er die Traceback aller Threads in `actions_monitor_log.txt` geschrieben hat.
