<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Änderungsprotokoll

Version des Werkzeugs selbst (Monitor + Wächter + Stapelwerkzeuge) mit eigenem Semver. Die Quelle ist das englische CHANGELOG.md; diese Datei enthält dieselben Versionen und Abschnitte.

## [Unreleased]

### Geändert

- **Neue Ordnerstruktur, gleiches Verhalten**: Der Code ist jetzt ein importierbares Paket in `src/github_actions_monitor/` (`app`, `accounts`, `sentinels`, `security`, `data_pipeline`, `integrations`, `cli`, `ui`, `i18n`, `util`); die Seite, die neutralen Beispiele mit `quotas.json` und die acht Sprachkataloge liegen in `assets/` (`static`, `examples`, `locales`); `make_release.py` liegt in `tools/`. Die Starter bleiben im Produktordner und starten `python -m github_actions_monitor` (komplett) oder `python -m github_actions_monitor.lite` (Lite): gleiche Adresse, gleicher Port. Die Daten des Nutzers (`actions_monitor.json`, Caches, Protokolle, `accounts/`, Kataloge) liegen weiter neben den Startern, nie in `src/`.

- Die Befehle der Anleitungen (`python read_report.py`, `python actions_monitor.py --doctor`, `python monitor_cli.py status` ...) funktionieren weiter: Eine kleine Einstiegsdatei mit demselben Namen bleibt im Produktordner, sodass auch die per Pfad registrierten Hooks und MCP-Server weiterlaufen. Das Release-Zip behält seinen Ordnernamen und enthält jetzt `src/`, `assets/` und `tools/`.

### Hinzugefügt

- `tools/migrate_layout.py` für einen Ordner, der eine flache Installation war: standardmäßig ein Probelauf; `--apply` kopiert Ihre Konfiguration nach `layout_backup_<Stempel>/config/` und VERSCHIEBT (nie löschen, nie überschreiben) die alten Module, die alte Seite, die alten Beispiele und `locales/` nach `layout_backup_<Stempel>/old_code/`. `--doctor` warnt, solange solche Reste existieren. `MIGRATING.md` beschreibt es in den acht Sprachen.

- **Teammodus: Benutzer, Rollen und Sitzungen** (`src/github_actions_monitor/security/auth.py`, `auth_http.py`, `auth_cli.py`; standardmäßig aus mit `auth.enabled`, eine einzelne Person merkt also nichts): Sobald der erste Administrator existiert (angelegt unter `/login` oder auf der Konsole, nur vom Rechner, auf dem der Monitor läuft, und nur einmal), braucht jede Anfrage eine Sitzung. Rollen `viewer` (liest), `maintainer` (schaltet zusätzlich stumm, bestätigt, ändert den Arbeitsmodus) und `admin` (zusätzlich Einstellungen, Benutzer und alles, was GitHub erreichen kann); eine Route, die niemand aufgeführt hat, ist für alle außer Admins gesperrt. Jeder Benutzer hat die Konten, die er sehen darf: ein anderes Konto per `?account=`, `X-Account-Id` oder Export antwortet 403. Passwörter werden als gesalzener scrypt-Hash gespeichert; die Sitzung ist ein HttpOnly-Cookie mit SameSite=Strict (Secure bei HTTPS) mit CSRF-Token bei jedem POST, oder ein Bearer-Token für Skripte und Apps (`auth.allow_bearer`); ein Benutzer wird nach `auth.max_failed_logins` falschen Passwörtern gesperrt, jede Adresse hat ein Anfragelimit, ein neues Passwort, eine neue Rolle oder ein neuer Zustand beendet die Sitzungen des Benutzers und es bleibt immer ein aktiver Administrator. Die Endpunkte `/api/auth/login`, `/api/auth/users` und `/api/auth/audit` melden Fehler als `{"error", "code"}`; `auth_audit.jsonl` hält Anmeldungen, Sperren, abgelehnte Anfragen und Benutzeränderungen ohne jedes Geheimnis fest. Die Lite-Edition hat nie eine Anmeldung, das Einmal-Token der Seite gilt weiterhin, und `python -m github_actions_monitor.security.auth_cli` stellt ein verlorenes Administratorpasswort wieder her. Sieben Einstellungen (`auth.*`) mit Hilfe in den acht Sprachen und ein Abschnitt in `docs/ADVANCED.md` in den acht Sprachen; `tests/test_auth.py` deckt die Regeln, die Rollen jeder Routenart, den Geltungsbereich zwischen Konten, das Cookie, CSRF, Bearer, Sperren und das Protokoll auf dem echten Server ab.

- Der Kontenüberwacher filtert nach Benutzer: `GET /api/accounts`, `/api/accounts/<id>/status`, die Seite eines Kontos und jede Anfrage mit `?account=` oder `X-Account-Id` zeigen und erreichen nur die dem Benutzer zugewiesenen Konten (ein Admin sieht alle), und der Monitor eines Kontos erfährt, wer handelt. Eine Stummschaltung im Tab Alarme hält jetzt fest, wer sie gemacht hat: `muted_by` in `GET /api/alerts` und im Verlauf der Stummschaltungen.

- **Die Seite des Teammodus zeigt, wer angemeldet ist**: Ein Feld in der Kopfzeile mit Name und Rolle (ein Text, nicht nur eine Farbe), das ein Menü zum Ändern des Passworts, zum Ansehen und Verwalten der Benutzer und des Protokolls (nur Administratoren) und zum Abmelden öffnet; beim ersten Mal, mit eingeschaltetem Modus und ohne Benutzer, verweist es auf `/login`. Jede Änderung der Seite trägt das CSRF-Token, eine beendete Sitzung führt zu `/login`, und ein falsches Token wird erneuert und einmal versucht. Im Einzelmodus und in der Lite-Edition zeichnet die Seite nichts und fragt nichts Neues; `tests/test_auth_page.py` führt den Wrapper von `fetch` in Node gegen ein falsches Netz aus.

### Sicherheit

- **Die Sperre bei falschen Tokens bremst wieder (Netzwerkmodus)**: Eine gesperrte Adresse, die nicht dieser Computer ist, wird abgewiesen, BEVOR ihr Token beurteilt wird, auf jedem Weg (Header, Cookie, `?access=` und `POST /api/access`); bisher konnte eine gesperrte Adresse weiter raten, und das richtige Token kam trotzdem durch. Wer an diesem Computer sitzt, wird nie aus dem eigenen Monitor ausgesperrt.

- **Ein deklarierter Reverse-Proxy lässt Loopback nicht mehr „dieser Computer“ bedeuten** (`listen.proxy_public_host`, `listen.secure_cookie` oder `listen.trusted_proxy`): Ein Proxy, der seine Weiterleitungs-Header vergisst, kann nicht mehr jeden Client des Internets zum Eigentümer machen. Wer am Rechner des Monitors sitzt, nutzt den neuen zweiten Port, der nur auf `127.0.0.1` lauscht (`listen.local_port`, 0 = aus, Neustart nötig, dasselbe Zugriffstoken). Mit `listen.trusted_proxy` werden falsche Tokens außerdem für alle Clients des Proxys zusammen gezählt (dreifaches Limit einer Adresse), sodass das Wechseln von `X-Forwarded-For` die Sperre nicht aushebelt.

- **Die Anleitung zum Reverse-Proxy** (`DEPLOYMENT.md`, acht Sprachen) enthält das ganze Rezept: öffentlicher `Host`, `X-Forwarded-For $proxy_add_x_forwarded_for`, `X-Forwarded-Proto`, Netzwerkmodus und Deklaration des Proxys; sie sagt nicht mehr, der Monitor habe „kein Login“, und weist darauf hin, dass `listen.trusted_proxy` einen Proxy auf demselben Computer voraussetzt.

- **`GET /api/settings` für einen Client des Netzwerks** liefert den Wert nur für die Einstellungen, die er ändern darf; bei jeder anderen Einstellung (Pfade von Schlüsseln und Tokens, Ordner, Namen von Variablen) sagt er nur, ob sie definiert ist.

- **Test jeder Route „nur dieser Computer“**: Eine Tabelle der Routen wird gegen einen echten Server mit einem Client außerhalb von Loopback durchlaufen (und der Quelltext wird geprüft, damit eine neue Route nicht vergessen wird).

- **Eine GitHub-Adresse passiert den Bereiniger nur in den Formen einer geschlossenen Liste** (ein Repository, ein Lauf mit Job oder Versuch, ein Commit, eine Issue, ein Pull Request, eine Datei); sie wird am ersten Zeichen abgeschnitten, das kein Buchstabe, keine Ziffer, kein Punkt, Bindestrich, Unterstrich oder Schrägstrich ist, und der Rest wird wie jeder Text bereinigt. Bisher gelangte ein an einen Link geklebtes Geheimnis (eine kodierte Abfrage, eine Liste mit Kommas, ein Doppelpunkt, ein undurchsichtiges Pfadsegment, eine E-Mail-Adresse, die in der Adresse beginnt) unverändert zur KI.

- **Der Hook des KI-Clients übergibt keinen Log-Text**: nur Repository, Workflow, Ergebnis und Link jeder Warnung. Die Anweisung, ohne Aufforderung zu handeln, ist entfallen; die Schlusszeile sagt nun, dass ein Log Text von Dritten enthalten kann, dass er nicht vertrauenswürdige Daten sind und dass darin gefundene Anweisungen nie befolgt werden. In den acht Sprachen.

### Behoben

- **Der Ereignisstrom für KIs stirbt nicht mehr an einer gewöhnlichen Log-Zeile**: Die Zeile des Feeds wird feldweise bereinigt und dann geschrieben, statt ein bereits geschriebenes JSON zu bereinigen (eine Ursache, die auf `password: x`, `token=x` oder `DB_PASSWORD=x` endete, zerstörte es). Eine Zeile, die sich nicht bereinigen lässt, wird übersprungen und der Strom läuft weiter; die Antworten des MCP-Servers werden genauso bereinigt. Im Bereiniger endet der Wert eines `Schlüssel=Wert`-Paares an einem Anführungszeichen, einem Komma oder einem Semikolon, und ein Wert in Anführungszeichen wird ganz bereinigt.

- **Was davon abhängt, wer fragt, beantwortet immer dein eigener Login**: `gh api user`, `user/orgs`, Benachrichtigungen, eine Suche nach `@me`, `gh auth` und `gh repo list` ohne Eigentümer gehen nie an die GitHub-App oder das zweite Konto, wie viele Aufrufe diese auch übrig haben (bei aktivem zweiten Konto konnte der Monitor dessen Inhaber als seinen Eigentümer nehmen und seine Organisationen auflisten).

- **Ein `gh`-Aufruf ist nur dann ein Lesen, wenn er auf einer Positivliste steht**: `gh api ENDPOINT` mit höchstens den Optionen `--jq`, `--paginate`, `-H` (von der Art, die ein Lesen sendet), `-i` und `--cache`. Die angehängten Schreibweisen eines Schreibens (`-XPOST`, `--method=DELETE`, `-fa=b`, `--field=a=b`, `--input=-`) und jede andere Option gehen an deinen Login, statt auf die Quellen verteilt zu werden.

- **Die Token-Datei des zweiten Kontos** (`extra_reader.file`) muss im Kontenordner des Monitors liegen (`accounts/` oder `MONITOR_ACCOUNTS_DIR`) und wird ohne Link-Folgen geöffnet, und nur wenn sie eine kleine normale Datei ist; außerhalb dieses Ordners ist die Einstellung leer. Der neue Schalter `extra_reader.any_folder` (standardmäßig aus, nur lokal) hebt die Ordnerregel für eine Datei auf, die woanders bleiben muss.

- **Einem Zentralpanel mit Datum in der Zukunft wird nicht mehr vertraut**: Sein Alter wurde auf null begrenzt und galt für immer als frisch; jetzt ist es veraltet, die Zusammenfassung sagt, dass dem Datum nicht zu trauen ist, und eine bis zu fünf Minuten vorgehende Uhr wird toleriert.

- **Der Test der Ports der Konten schlägt nicht mehr fehl, wenn Suiten gleichzeitig laufen**: Dem Supervisor kann gesagt werden, wo er mit der Suche nach freien Ports beginnen soll (Standard bleibt 18800), und die Tests fragen das System nach einem unbenutzten Bereich statt nach einem festen.

- **Eine kaputte Seite macht die CI rot**: Ein neuer Job (`page`, ohne `continue-on-error`) öffnet die Seite des Demo-Monitors in einem echten Browser (`tools/check_page.py`), geht durch jeden Tab und jeden Unter-Tab der Einstellungen, verlangt in jedem eine Mindestzahl von Feldern und schlägt bei jedem Fehler der Seite, jeder unbehandelten Promise und jedem console.error fehl. Eine absichtlich kaputte Seite (eine zweite Definition, eine Zuweisung an den Namen einer Funktion, ein Aufruf einer nicht vorhandenen Funktion) muss ihn scheitern lassen. Der Test, der doppelt definierte Funktionen sucht, erkennt nun auch eine eingerückte Deklaration, eine mit `async` und eine Zuweisung an den Namen einer Funktion.

## [1.7.9]

### Behoben

- Die Links der Runs, die die KI-Werkzeuge erhalten (Feed, Zusammenfassung, Zustand, Hook), wurden zu "https://github.[blob]" gekürzt: Der Redaktor hielt die Adresse für eine undurchsichtige Zeichenfolge. Vollständige https-Adressen von github.com bleiben jetzt unverändert; Tokens, Schlüssel, E-Mails, IP-Adressen und persönliche Pfade werden weiterhin bereinigt, auch innerhalb eines Links.

## [1.7.8]

### Hinzugefügt

- **`listen.trusted_proxy`** (standardmäßig aus, nur lokal, in den acht Sprachen): Hinter einem eigenen Reverse-Proxy auf demselben Computer wird ein Fehlversuch gegen die letzte Adresse von `X-Forwarded-For` statt gegen den Proxy gezählt, damit falsche Tokens einer Person nicht alle aussperren. Es ändert nur diese Zählung: Eine Anfrage über einen Proxy gilt weiterhin nie als dieser Computer.

### Behoben

- Die Einstellungsseite zeigte "Der lokale Monitor antwortet nicht" und keine Tabs: Die Box des Tabs Kontingent hatte denselben Namen wie eine ältere Funktion des Tabs Basis und wurde von ihr ersetzt. Die Kontingent-Box ist umbenannt, und ein Test schlägt jetzt fehl, wenn eine Funktion der Seite doppelt definiert ist.

## [1.7.7]

### Hinzugefügt

- **Eine Prüfung, dass kein Text sein Feld verlässt** (`tools/check_overflow.py` und ein Test, der ohne Browser sauber übersprungen wird): Die Seite wird in einem Browser ohne Fenster in den acht Sprachen, breit und schmal, geöffnet, geht jeden Tab und jedes Fenster durch und schlägt fehl, wenn ein Text breiter ist als ein Feld mit Rand oder Hintergrund oder das Fenster verlässt.
- **`display.blink_red_tiles`** (standardmäßig an, im Tab Einstellungen, in den acht Sprachen): Die Kacheln oben und die Elemente der unteren Leiste, die rot werden, blinken sanft, bis die Ursache behoben ist; bei reduzierter Bewegung im System zeigen sie stattdessen einen festen, dickeren roten Rand.
- **Eine Doctor-Prüfung für die Zeitzone**: Eine Zone, die weder das System noch die eingebaute Tabelle kennt, wird gemeldet, und die Zeiten erscheinen dann in UTC (früher fielen sie ohne Hinweis auf die Zone des Computers zurück).
- **Der Tab Verlauf zeigt "n von N"**, wenn die Liste kürzer ist als das, was die Kopfzeile gezählt hat (der Monitor behält die 600 neuesten Läufe; die Daten enthalten `runs_total`).
- **Die Panels des Tabs Sentinel als Daten**: `GET /api/sentinel/panels` (nur lesend), das MCP-Werkzeug `sentinel_panels` und ein Abschnitt "Sentinel panels" in der Zusammenfassung liefern für A1..A13 und den zweiten Sentinel die Stufe, eine Zeile und die Zeilen, auf die zu reagieren ist, mit Repository und Link; die Zeilen eines Panels auf "handeln" oder "beobachten" werden zusätzlich zu Warnungen des Feeds (Klassen `real` und `watch`), sodass Stream, Hook, `alerts_open` und der Zähler echter Warnungen sie enthalten.
- **Ein "Bing Bing", wenn etwas Neues fehlschlägt** (die Einstellungen `sound`, in den acht Sprachen): Die Seite spielt zwei kurze Töne (Web Audio) nur bei NEUEM Rot oder verlorener Verbindung, nie bei einer Aktualisierung oder für schon Vorhandenes, mit Pause, Lautstärke und einem Chip "Ton" in der unteren Leiste, der den Browser-Ton freischaltet, stummschaltet und gemerkt wird; eine Schaltfläche "Ton testen" unter Dieser Browser; und `sound.server_beep` (standardmäßig aus, nur lokal) für den Fall, dass die Seite geschlossen ist (Windows-Beep, macOS `afplay`, Linux `canberra-gtk-play` oder die Terminalglocke, ohne Shell und ohne Netzwerk).
- **Alles, was der Monitor sagt, als Signale für ein KI-Werkzeug**: ein einziges Inventar (`signals.py`) mit Stufe (handeln / beobachten / Info), Zusammenfassung und Zeilen mit Repository, Link, Alter und nächstem Schritt für den Tab Jetzt und seine Kacheln, die Warnungen, die Repositories, die Sentinel-Panels A1..A13 und den zweiten Sentinel, das Kontingent, die Verbindung und die Gesundheit des Monitors; `GET /api/ai/state` (versioniert, nur lesend), eine Zusammenfassung mit "Was jetzt zu tun ist", "Offen" und "Gesundheit des Monitors" samt Zähler der Signale zum Handeln sowie die MCP-Werkzeuge `monitor_state`, `signals`, `diagnose` und `act`. Ein Test läuft über die Seite und schlägt fehl, wenn eine Kachel oder ein Tab weder im Inventar noch als dekorativ markiert ist.
- **Die Verbindung mit einem KI-Werkzeug ist in der Lite- und der vollständigen Edition gleich**: dieselben Kanäle (Zusammenfassung, Feed, `/api/ai/state`, Stream, MCP-Werkzeuge, `ai-hook`), derselbe Code und dieselben Einstellungen in beiden; der Zustand nennt `edition` und listet die Panels, die in Lite nicht existieren, damit ein fehlendes Panel nicht für fehlende Daten gehalten wird.
- **Ein Sparmodus (extremes Sparen des Kontingents)**: neben Normal, Schnell und Turbo liest `low` nur die heißen Repositories alle 4 Minuten und den Rest alle 30, mit kurzen Lauflisten, und sagt in der Leiste und in der Zusammenfassung, dass seine Zahlen alt sein können und wie alt; `modes.auto_low` (standardmäßig an) schaltet unter 1000 verbleibenden Aufrufen von selbst ein und über 2500 oder bei Erneuerung des Kontingents zurück (zwei verschiedene Zahlen, kein Hin und Her); die Werte stehen in `modes.low` der Datei.
- **Das zentrale Panel als Basis, die kein Kontingent verbraucht** (`central.source`: standardmäßig aus, `git` oder `http`; `central.max_age_minutes`, in den acht Sprachen): Der Monitor liest `data/sentinel.json` des Profil-Repositories (von einem Workflow mit eigenem Token alle halbe Stunde aktualisiert) mit einem einfachen git fetch oder der Rohdatei, zeigt "Quelle: zentrales Panel, vor N Min" im Zustand und in der Zusammenfassung, ignoriert eine veraltete Datei (über zwei Stunden) und sagt das, und fragt im Sparmodus die API nur für die Repositories live ab, die das Panel als rot nennt, solche mit laufendem Lauf und was das Panel nicht enthält.
- **Eine optionale GitHub-App für das Lesen** (`github_app.enabled`, standardmäßig aus, mit `app_id`, `key_path` und optionaler `installation_id`, in den acht Sprachen): Die Lesezugriffe des Monitors nutzen das Installations-Token einer App, deren Kontingent vom Kontingent des Nutzers getrennt ist und größer wird, je mehr Repositories sie abdeckt; das JWT (höchstens zehn Minuten) wird von `openssl` anhand des Schlüsselpfads signiert, den der Monitor nie liest, kopiert, druckt oder protokolliert; das Token gilt eine Stunde, liegt im Speicher und wird fünf Minuten früher erneuert; Schreibzugriffe und Aktionen behalten das Token des Nutzers; fällt die App aus oder fehlt eine Berechtigung, wird der Lesezugriff mit dem Token des Nutzers wiederholt; `GET /api/github-app/status` (nur dieser Computer) zeigt Name, Installation, gewährte Berechtigungen und Kontingent der App, nie den Schlüssel oder das Token; die Daten enthalten das Kontingent des Nutzers neben dem der App, und der Doctor prüft openssl, die Schlüsseldatei und ihre Rechte.
- **Zwei neue Leitfäden in den acht Sprachen**: `docs/AI_CONNECTION.md` (ein KI-Werkzeug verbinden: was es sieht, die fünf Kanäle, Schritt für Schritt, Sicherheit, Fehlersuche, was jede Edition zeigt) und `docs/QUOTA.md` ("Mehr Kontingent, weniger Verbrauch": wie das Kontingent funktioniert, alle Wege, mit denen der Monitor spart, eine GitHub-App Schritt für Schritt, das Kontingent zwischen Werkzeugen teilen, was man nicht tun sollte); beide sind aus der README und dem Hilfeindex verlinkt, und ein Test prüft, dass jede von ihnen genannte Einstellung existiert.
- **Die Hilfe wird bei jeder Änderung geprüft**: Eine Einstellung ohne Beschriftung und Hilfe in den acht Sprachen, ein Tab ohne Hilfethema oder eine Zeile des Änderungsprotokolls, die eine in Hilfe und Leitfäden fehlende Einstellung oder einen Endpunkt nennt, lassen die Tests nun scheitern; eine Hilfe-Checkliste steht in CONTRIBUTING und in der Pull-Request-Vorlage.
- **Ein Tab Kontingent in den Einstellungen** (in den acht Sprachen, auch in der Lite-Edition): die Modi und die Werte des Sparmodus (`modes.*`), das Sparen (`network.etag`, ein Alias, der zusammen mit `cache.etag.enabled` wirkt), das zentrale Panel, die GitHub-App und ein zweites Konto für das Lesen an einem Ort, mit Schaltflächen, die das Kontingent jeder Quelle mit ihrer Erneuerungszeit zeigen, die App und das zweite Konto testen, fehlende Berechtigungen der App auflisten und die empfohlenen Werte oder die Standardwerte anwenden.
- **Ein zweites Nur-Lese-Konto für das Lesen** (`extra_reader.enabled`, `extra_reader.file`): Die Einstellung enthält nur den PFAD einer Datei mit einem feingranularen Token, das der Monitor im Moment der Nutzung liest, im Speicher hält und nie speichert, druckt oder protokolliert; die Lesezugriffe verteilen sich nach den verbleibenden Aufrufen auf Ihre Anmeldung, die App und das zweite Konto, eine abgelehnte Quelle wird fünf Minuten ausgelassen und der Lesezugriff mit der nächsten wiederholt, und Schreibzugriffe und Aktionen nutzen es nie.
- **Buchführung der Lesezugriffe**: Zustand, Zusammenfassung und Daten nennen, wie viele bedingte Aufrufe gemacht wurden und wie viele mit 304 antworteten (kein Kontingent verbraucht), sowie das Kontingent jeder Quelle.
- **Wer das Kontingent verbraucht**: Der Monitor vergleicht in jedem Stundenfenster, was das ganze Konto verbraucht hat, mit seinen eigenen Aufrufen und nennt im Tab Kontingent, im Zustand und in der Zusammenfassung, wie viel andere Werkzeuge verbrauchen, mit einer Warnung, wenn sie den Großteil verbrauchen (GitHub sagt nicht, welches).
- **Der Stream trägt auch die übrigen Signale**: Das erschöpfte Kontingent, die abbrechende Verbindung, veraltete Daten, ein zurückliegendes zentrales Panel und die Gesundheitswarnungen werden zu Ereignissen des Feeds (und des Streams und des Hooks), wenn sie auftreten, sich ändern oder gelöst werden, nicht nur die roten Workflows und die Panels des Tabs Sentinel.
- **Der Batch-Versand speichert den Versuch des gefundenen Laufs** (`run_attempt` im Batch-Eintrag, aus dem Feld `attempt` von `gh run list`; leer, wenn `gh` es nicht liefert), und die Leitfäden zur KI-Verbindung und zum Kontingent beschreiben das zweite Nur-Lese-Konto.

### Geändert

- **Die untere Leiste wurde neu gestaltet**: Jedes Element ist ein Chip mit eigenem Rand, Verbindung und Kontingent übernehmen die Farbe ihres Zustands, die Uhr ist ein Rahmen mit großen, fetten, tabellarischen Ziffern, darüber das Datum und die Zone in kleiner Schrift, und die Leiste behält ihre Reihenfolge in schmalen Fenstern.
- **Jedes Feld lässt seinen Text umbrechen, statt ihn überstehen zu lassen** (Kacheln, Chips, Badges, Zellen, Überschriften, Fensterschaltflächen): Die Zeit der letzten Abfrage trägt ihre Zone getrennt in kleiner Schrift, die Warnungszeilen werden in schmalen Fenstern zweispaltig und die Kachelraster können unter ihren Inhalt schrumpfen.
- **Die Kacheln einer Zeile sind gleich hoch**, was auch immer ihr kleiner Text braucht.

### Behoben

- **Eine Zahl für die offenen Fehler**: Die Kachel "rot auf main", die Liste der Warnungen, die untere Leiste und die Zusammenfassung zählen dasselbe, einen Workflow, dessen letzter Lauf auf dem Standard-Branch fehlschlug (ein Fehler auf einem Arbeits-Branch erscheint nicht mehr als offene Warnung), und die Leiste sagt nie "keine Hinweise", solange Warnungen offen sind.
- **Der Start des Monitors nennt die Version nur einmal**: Die Zeile "GitHub Actions v...", die die Kopfzeile wiederholte, entfällt; Autor und Lizenz bleiben in einer Zeile.
- **Beschädigte Statusdateien** (Collab-Status, Sentinel-Cache und -Verlauf mit falscher Form) werden Eintrag für Eintrag ignoriert, statt den lesenden Code zu erreichen.
- **Ein erschöpftes GitHub-Kontingent ist EIN Hinweis, nicht ein Fehler pro Repository**: Das Lesen der Repositories pausiert bis zur Erneuerung (und setzt von selbst fort), die Liste der Warnungen sagt "GitHub-Kontingent erschöpft bis HH:MM ... (N Repositories nicht aktualisiert)", die untere Leiste ebenfalls, nichts wird rot und nichts erreicht Feed, Ton oder Zusammenfassung als Fehler; die Fehlertexte von `gh` werden auf eine Zeile gekürzt (ohne Rechtstext und Anfrage-ID), und viele Repositories mit derselben Fehlerart werden in einer Zeile zusammengefasst.
- **Info (und jede Seite) wartet nicht mehr auf das Netzwerk**: Die Prüfung auf eine neue Version des Monitors wurde in der Anfrage von /api/about gelesen, wenn ihre Antwort älter als ein Tag war; ein `gh` ohne Anmeldung oder ein langsames Netz ließ das Info-Fenster daher 10 bis 25 Sekunden brauchen; jetzt wird die Antwort aus dem Cache sofort geliefert und das Lesen übernimmt ein Thread im Hintergrund, immer nur einer.

## [1.7.6]

Die Verbindung zwischen Monitor und KI-Werkzeug: Der Feed stimmt immer mit der Seite überein, jede Warnung sagt, warum sie rot ist, ein Stream und drei MCP-Werkzeuge schieben die Neuigkeiten nach, ein Befehl installiert das Gate-Skript, die Leiste zeigt, ob eine KI verbunden ist, und jede Zustandsdatei gehört nur ihrem Besitzer.

### Hinzugefügt

- **Zusammenfassung und Feed folgen jeder Aktualisierung des Reiters Warnungen** (und jedem Lesen des Feeds und jedem Zyklus): früher hinkten sie einen Zyklus hinterher, sodass eine KI 10 Warnungen las, während die Seite 6 zeigte. `ALERTS_BRIEF.md` enthält jetzt `Updated:` in deiner Zeitzone und eine Maschinenzeile `updated_epoch:`, und `GET /api/ai/brief?fmt=json` ergänzt `updated`, `updated_local` und `age_seconds`. Ein Zyklus, dessen Daten noch nicht geladen sind, löst nie Warnungen auf.
- **`ai_alerts.diagnose`** (standardmäßig aus, im Reiter Einstellungen, in acht Sprachen): Jede Warnung eines neuen roten Laufs trägt `diagnosis`, den ersten fehlgeschlagenen Schritt und etwa zehn relevante Logzeilen, gelesen mit lesenden Aufrufen, von Geheimnissen bereinigt und in Größe und Läufen pro Zyklus begrenzt; ein Infrastrukturfehler im Log macht die Warnung vorübergehend.
- **`ai_alerts.cascade`**: Warnungen, die rot sind, weil ein anderes Repository rot ist (im Log oder in der Regel `ai_alerts.cascade.map` genannt), stehen in der Zusammenfassung darunter und tragen `origin`.
- **`GET /api/ai/stream`** (`ai_alerts.stream`, standardmäßig aus): Server-Sent Events, nur lesend, im Netzwerkmodus mit dem Zugriffstoken, in Zuhörern und Zeit begrenzt, mit `Last-Event-ID` fortsetzbar; die Lite-Edition hat ihn nicht.
- **MCP-Werkzeuge `alerts_open`, `alert_diagnose` und `alert_ack`** (das letzte nur mit `--allow-ack`) und ein Hinweis an die KI beim Verbinden, in den `instructions` und mit einer Benachrichtigung, wie viele echte Warnungen offen sind.
- **`monitor_cli.py ai-hook install|status|uninstall [--assistant|--cursor|--generic] [--scope project|user] [--dry-run]`** und das Gate-Skript `ai_hook.py` (nur Standardbibliothek): Es fügt der KI-Sitzung die Zusammenfassung hinzu und bittet die KI, nur mit `ai_alerts.client_hook.block_on_stop` (standardmäßig aus), vor dem Ende eines Zuges offene echte Warnungen anzusehen. Die Einstellungen des Werkzeugs werden zusammengeführt, nie ersetzt, eine Kopie der Datei bleibt erhalten, eine Datei ohne gültiges JSON wird unberührt abgelehnt, und alles Geschriebene ist reines ASCII. Die Werte liegen in `ai_alerts.client_hook` (Reiter Einstellungen, acht Sprachen).
- **Ein KI-Heartbeat** (`ai_alerts.heartbeat`): Stream, MCP-Server, Gate-Skript und Endpunkte vermerken ihren letzten Lesezugriff in einer kleinen lokalen Datei, und die untere Leiste zeigt, ob eine KI verbunden ist und wie lange ihr Lesen her ist.
- **`monitor_cli.py --token-file DATEI`** und eine Warnung auf stderr, wenn `--token` benutzt wird (es erscheint in der Prozessliste) oder die Token-Datei für andere Benutzer lesbar ist.
- Tests für jede Änderung, in einem temporären Ordner und offline, einschließlich des Modus jeder Zustandsdatei bei lockerem `umask`.

### Geändert

- **Jede Zustandsdatei des Monitors wird mit Modus 0600 angelegt** (die erzeugten Ordner mit 0700), über einen einzigen Helfer, `private_io.py`: Stummschaltungen, Ereignisse, Feed, Zusammenfassung, Caches, die Einstellungen und die Dateien des Installers für das Gate-Skript. Unter Windows kann das Programm die Modi nicht erzwingen (Ordner erben die Rechte ihres übergeordneten Ordners).
- **Beim Start des Netzwerkmodus** mit noch eingeschaltetem `listen.query_access` werden jetzt die ersten Schritte ausgegeben (ausschalten; HTTPS oder VPN nutzen), und die Hilfe von `listen.network` sowie die erweiterte Anleitung sagen dasselbe in acht Sprachen.
- **Der Warnungs-Feed für KI ist standardmäßig aus** (`ai_alerts.enabled`, war an): Eine neue Installation schreibt keinen Feed, bis du ihn einschaltest. Eine Installation, die schon einen Feed in ihrem Ordner hat, behält ihn an, und die Konsole sagt das beim Start einmal, sodass niemand, der ihn absichtlich nutzte, abgeschaltet wird.


### Sicherheit

- **Ausgehende Benachrichtigungen ignorieren die Proxy-Variablen der Umgebung** (`http_proxy`, `https_proxy`): Ein Proxy ließ die Prüfung die Adresse des Proxys statt der des Ziels beurteilen, und ein Proxy, der mit einer Weiterleitung antwortete, konnte die Anfrage ins lokale Netz schicken (auch an die Metadatenadresse einer Cloud). Die neue Einstellung `network.use_proxy` (standardmäßig aus, im Reiter Einstellungen, in acht Sprachen) verwendet sie wieder, und dann werden Ziel und Ziel jeder Weiterleitung geprüft, bevor der Proxy etwas erhält. Getestet mit einem Proxy, der auf die Metadatenadresse weiterleitet.
- **`/api/ai/actions/confirm`, `/api/ai/actions/unlock`, `/api/ai/test` und `/api/notify/test` gelten nur für diesen Rechner** im Netzwerkmodus (403 `local_only`), wie die anderen handelnden Endpunkte.
- **Ein `act`-Plan ist an seinen Workflow gebunden**: Der Plan merkt sich den aufgelösten Pfad und den SHA-256 der Datei, beides wird unmittelbar vor dem Start von `act` erneut geprüft; ein nach der Bestätigung geänderter, ersetzter oder entfernter Workflow läuft nicht (`workflow_changed`, mit Text in acht Sprachen).
- **Der macOS-Schlüsselbund bekommt das Token nicht mehr in einer Befehlszeile**: `security -i` liest den Befehl von der Standardeingabe, das Token steht also nicht in der Prozessliste.
- **Alles, was `gh` ausgibt, wird vor dem Speichern bereinigt**: das Protokoll der Aktionen für KI und das Detail einer abgelehnten Aktion laufen durch den Bereiniger, der jetzt auch die alten 40-Hex-Token und das vom Monitor gespeicherte Token abdeckt.
- **Die Liste abgelehnter Adressen ist begrenzt** (`localguard`): Die nächste Sperre entfernt alle abgelaufenen Sperren, nicht nur die der anfragenden Adresse, und hält nie mehr als 2000 Einträge.
- **Eine Stummschaltung, die nicht gespeichert werden konnte, gilt nicht als gespeichert**: `POST /api/alerts/mute` und `unmute` antworten `ok: false`, wenn die Datei nicht geschrieben werden konnte.
- **Die Befehlszeile zeigt bei einer Antwort der falschen Form nie einen Traceback**: eine Liste, `null` oder eine Zahl statt eines Objekts oder ein Feld des falschen Typs endet mit Exit-Code 4 und einer Meldung.
- **Ein Netzwerk-Client darf nur eine kurze Liste von Einstellungen schreiben** (Sprache, Zeitzone und Tempo der Seite): jeder Benachrichtigungskanal, jeder Pfad, jeder Name einer Umgebungsvariable und die Dateien, denen der Signier- und Versandablauf vertraut, werden vom Rechner des Monitors aus geändert. Eine später hinzugefügte Einstellung ist nur lokal, bis sie absichtlich aufgenommen wird.
- **Hinter einem Reverse-Proxy auf derselben Maschine** ist eine Anfrage mit Weiterleitungs-Header (`Forwarded`, `X-Forwarded-*`, `X-Real-IP`) oder mit dem öffentlichen Namen des Proxys nie „dieser Rechner“, und das Zugriffstoken wird vor der Sperre nach Adresse geprüft, sodass eine Flut falscher Token den Besitzer nicht aussperrt.
- **Aufrufe an diesen Rechner laufen nie über einen Proxy der Umgebung** (`netguard.local_open`, genutzt von der Befehlszeile, dem MCP-Server, den Terminalansichten und den Hooks), und die Befehlszeile folgt keiner Weiterleitung, sodass das Zugriffstoken nicht an eine andere Adresse weitergeschickt wird.
- **Jede Antwort verbietet das Einbetten in Frames** (`X-Frame-Options: DENY`, `frame-ancestors 'none'`, `nosniff`), die Seite prüft den `Host` wie die API, und jede Antwort, die über die veraltete Adresse `?access=` authentifiziert wurde, trägt den Header `Deprecation`.
- **Versand und Signierung**: Die vor einem Versand vorhandenen Läufe werden notiert, und nur ein neuer kann als unser gelten (ohne Uhren); zwei neue Kandidaten erfordern Prüfung; die Eingabe `ref` ist der geprüfte Commit; ein Pflicht-Workflow wird mit seiner DATEI verglichen, nie mit einem sichtbaren Namen; der Name eines Stapels steht in UTC.
- **Der Bereiniger des Feeds für KI deckt mehr Formate ab**: Namen, die auf `PASSWORD`, `PWD`, `SECRET` oder `TOKEN` enden, Zugangsdaten in einer Adresse, Webhooks von Slack und Discord, Telegram-Bot-Token, `glpat-`-, `npm_`- und `pypi-`-Token, private Schlüssel, lange Hexadezimalfolgen und das Zugriffstoken dieses Monitors. `get_run_failure` des MCP-Servers liest nur Repositories, die der Monitor beobachtet (oder `ai.allowed_repos`).
- **Von Hand bearbeitete Dateien** (Stummschaltungen, Update-Zustand) verlieren nur ihre fehlerhaften Einträge, und ein fehlerhafter Update-Zustand hält den Start nicht mehr an.
- **Zeitzonen**: Kairo folgt in der eingebauten Tabelle seit 2023 der Sommerzeit, und ein dem System unbekannter Zonenname wird im Reiter Einstellungen abgelehnt. Die vollständige Edition meldet die roten Workflows im Kopf wie die Lite-Edition, und `monitor_cli.py status` ohne Daten endet wie `health` mit Exit-Code 4.

## [1.7.5]

Die Befehlszeile nimmt das Zugriffstoken unter seinem eigenen Namen, der Netzwerkmodus ist standardmäßig sicherer (die Adresse des Rechners wird vor dem Netz verborgen, die alte Adresse ?access= lässt sich abschalten, Benachrichtigungsziele im lokalen Netz werden abgelehnt, Warnung vor einfachem HTTP), Zeiten für Menschen nutzen deine eigene Zeitzone, ein Alarm lässt sich bis zur Änderung des Elements stummschalten, und falsche Zählungen und Prüfungen sind korrigiert.

### Hinzugefügt

- **`monitor_cli.py --token TOKEN`**, und das Zugriffstoken der Befehlszeile hat jetzt den Namen, den der Monitor selbst liest: `MONITOR_ACCESS_TOKEN`, dann sein Alias `MONITOR_TOKEN`, dann `--token` (eine Option erscheint in der Prozessliste, also der letzte Ausweg). Die Meldung eines abgelehnten Clients nennt die Variable. Getestet gegen einen falschen Monitor, der den Header verlangt.
- **Eine Warnung auf stderr**, wenn `monitor_cli.py` auf unverschlüsseltes `http` eines anderen Rechners zeigt (Token und Antworten würden unverschlüsselt reisen); die Antwort und `--json` bleiben unberührt.
- **`listen.query_access`** (standardmäßig an, im Tab Einstellungen, in den acht Sprachen): Ausgeschaltet wird die veraltete Adresse `?access=` abgelehnt, die Sitzung öffnet sich dann nur mit `POST /api/access` (Token im Body) oder dem Header. Die funktionierende Adresse antwortet mit einem `Deprecation`-Header, und die Konsole sagt, dass sie veraltet ist.
- **Eine Stummschaltung „bis sich das Element ändert"**: `POST /api/alerts/mute` nimmt `until_change` für einen Alarm; sie merkt sich das `updated_at` des Issues oder Pull Requests und endet sofort, wenn es sich ändert (neuer Kommentar, Push), oder nach Ablauf der Stunden, was zuerst eintritt. Die Alarme von Collab tragen jetzt `details.updated`.
- **Eine Doctor-Prüfung für ein Token, das mehrere Konten teilen** (`credential`): Sie vergleicht nur einen kurzen Fingerabdruck der Token, mit denen die Konten GitHub lesen würden (das vom Monitor gespeicherte Token oder `GH_TOKEN` / `GITHUB_TOKEN` der Umgebung), und listet die Konten, die eines teilen; das Token selbst wird nie gezeigt.
- Tests für jede Änderung, darunter ein Hygienetest des Webhooks: Eine Nutzlast mit Geheimnis, E-Mail, Commit-Nachricht und Token erreicht weder die Live-Liste noch den Feed noch eine Benachrichtigung, und die Live-Liste wird jetzt mit einer Liste erlaubter Felder gefiltert.

- **`notify.allow_private_targets`** (standardmäßig aus, im Tab Einstellungen, in den acht Sprachen): Ein Benachrichtigungsziel, das eine Loopback-, private (10.x, 172.16-31.x, 192.168.x, fc00::/7), Link-Local- (169.254.x, mit der Cloud-Metadatenadresse, fe80::/10), gemeinsame (100.64.0.0/10) oder reservierte Adresse ist oder dorthin aufgelöst wird, wird abgelehnt. Der Name wird einmal aufgelöst und der Socket zur geprüften Adresse geöffnet (ein Name, der seine Antwort ändert, kommt nicht durch), und jede Weiterleitung durchläuft dieselbe Regel. Die Kanäle `mqtt` und `http_local` bleiben per Definition nur lokal. Mit einem falschen Server und einem falschen Resolver getestet.
- **Eine Warnung zu einfachem HTTP im Netzwerkmodus**: Die Hilfe des Schalters `listen.network` sagt jetzt in den acht Sprachen, dass Token und Daten ohne HTTPS unverschlüsselt übertragen werden; die Konsole warnt beim Start im Netz ohne Zertifikat bereits.
- **Zeiten für Menschen in der eigenen Zeitzone**: Die Zeile `Last read` und die Stummschaltungen von `monitor_cli.py`, das Protokoll `actions_monitor_log.txt`, die Berichte des Wächters, die Kurzfassung für KIs und die Benachrichtigungen zeigten UTC (`...Z`), ohne es zu sagen, ein bis zwei Stunden neben der Wanduhr. Sie lesen sich jetzt wie `11:43:07 CET (10:43:07 UTC)`: die Zone des Rechners, ihr Name und daneben die UTC-Zeit. Die Sommerzeit wird beachtet (getestet um beide Zeitumstellungen und für Madrid, UTC, Tokio und New York).
- **`display.timezone`** (standardmäßig `local`, im Reiter Einstellungen und in den acht Sprachen): `utc` oder ein IANA-Name wie `Europe/Madrid` zeigt die Texte und die Uhren der Seite in dieser Zone; die Umgebungsvariable `MONITOR_TIMEZONE` hat Vorrang vor der Datei. Ohne Zeitzonendatenbank im System (Windows ohne `tzdata`) dient eine eingebaute Tabelle der üblichen Zonen.
- **Felder für Maschinen behalten UTC und bekommen ein lesbares Geschwisterfeld**: `generated_local` in `ci_red.json` und im lokalen Warteschlangen-Export, `updated_local` in `monitor_cli.py status --json` und in den Daten der Seite sowie eine Zeile `Updated:` in `ALERTS_BRIEF.md`. Die Uhren der Seite und die untere Leiste zeigen die Zone (`CET`, `JST` ...).
- **Ein Knopf „Bis zur Änderung“ im Reiter Alarme**: Er schaltet einen Alarm eines Issues oder Pull Requests stumm, bis sich dessen `updated_at` ändert (neuer Kommentar, Push), höchstens aber für die üblichen Stunden; der stummgeschaltete Alarm zeigt „stumm bis zur Änderung“. Texte in den acht Sprachen und ein Regressionstest.

### Geändert

- **Die API nennt die Ausgabe `complete`** (vorher `full`) in `/api/about`, `/api/statusbar`, `--doctor --json` und der Befehlszeile; `full` bleibt für das reserviert, was der Wächter ausführen darf. Die Seite und die Befehlszeile verstehen weiterhin beide Wörter.
- **Stummschaltungen gibt es nur vom Rechner des Monitors aus** (auch im Netzwerkmodus, bis es Ausgaben mit Benutzern gibt): Die Anleitung von Collab sagt es in den acht Sprachen, und ein Test hält die Route hinter dieser Regel.
- **Die Workflows dieses Repositorys nutzen auf einen vollständigen Commit festgelegte Actions**, mit der Version im Kommentar, und ein Test hält das so.

### Behoben

- **Issues, die geschlossen werden könnten** (Oberflächenprüfung): Ein grüner Lauf eines anderen Workflows schlägt nicht mehr vor, ein Issue zu schließen; das Issue muss den Workflow nennen (mit seinem Namen oder seiner Datei, „Firmware build failed" für `firmware-build.yml`), und genau dieser Workflow braucht einen späteren grünen Lauf auf dem Standard-Branch. Ein Issue ohne Workflow-Namen schlägt nichts vor.
- **Tag gegenüber Manifest** (Oberflächenprüfung): Liegt der Tag des letzten Releases vor dem aus dem Klon gelesenen Manifest, wird das Manifest des Standard-Branches auf GitHub einmal für dieses Release gelesen (der Klon kann nach einem Release hinterherhinken), und die Warnung verschwindet, wenn es diese Version schon hatte; Tags, die keine Versionen sind (`meshes-1`), werden ignoriert.
- **Nächster Schritt eines Release-Kandidaten**: Ein Repository, dessen Release einen signierten Build braucht, sagt jetzt „in Actions bauen und signieren", getrennt von „Version erhöhen", „signieren" und „veröffentlichen"; Repositories von anderswo betreuten Ökosystemen bleiben aus den Kandidaten heraus (getestet).
- **Laufende und wartende Runs werden nur einmal gezählt**: die Kacheln „laufend“ und „in der Warteschlange“, die Liste „Passiert gerade“, die Statusleiste (neues Element „N laufend · M in der Warteschlange“, auch in `/api/statusbar` als `runs`) und `monitor_cli status` liefern für dieselben Daten dieselben Zahlen, in beiden Editionen. Verbergen die Filter der Seite (Ökosystem, Zustand, Suche, eine Liste aus einer Kachel) Runs, zeigen die Kacheln „3 von 13“ und die Liste beginnt mit „Zeige 3 von 14 (Filter aktiv)“; ein im Browser gespeicherter Filter wirkt so nicht mehr wie ein Widerspruch. Die Liste der aktiven Runs verwirft außerdem einen doppelt gelesenen Run. Texte in den acht Sprachen und Tests für beide Editionen.

### Sicherheit

- **`/api/statusbar` gibt die Adresse des Rechners im lokalen Netz (`lan_address`) im Netzwerkmodus nicht mehr an einen Client des Netzes weiter**; die Leiste wird ohne sie gezeichnet.
- Die veraltete Adresse `?access=` wird nur bei einem `GET` beachtet.

## [1.7.4]

Eine Leiste am Fuß der Seite für die Hinweise und die Fakten des Monitors, ein Vollbild-Knopf, Tabellen, die nach einer oder mehreren Spalten sortieren, mit den Spalten deiner Wahl, und die Befehlszeile als Client des laufenden Monitors.

### Hinzugefügt

- **Eine Statusleiste am Fuß der Seite** (alle Ausgaben) anstelle der Urheberzeile. Links der wichtigste Hinweis (rot vor gelb) mit der Zahl der übrigen und einem Knopf, der ein Fenster mit allen öffnet, neueste zuerst, mit Filter nach Stufe; ohne Hinweise sagt sie das. Rechts die Verbindung (eine Lampe: GitHub online, offline oder Kontingent knapp), das Kontingent und wann es sich erneuert, die letzte Lesung, der Arbeitsmodus, wie viele Wächter an sind, die überwachten Repositories, das Konto, Version und Ausgabe, die Adresse des Monitors und Datum und Uhrzeit. Sie folgt der Fensterbreite: Die zweitrangigen Angaben klappen auf schmalen Bildschirmen weg. `GET /api/statusbar` liefert ihr die Fakten, die GitHub-Daten nicht tragen (kein GitHub-Aufruf, kein Geheimnis).
- **Ein Vollbild-Knopf** in der oberen rechten Ecke (die Fullscreen-API; ein zweiter Druck beendet es), mit Symbol und Text in den acht Sprachen.
- **Sortierbare Tabellen**: Repositories und Verlauf sortieren per Klick auf eine Spaltenüberschrift (auf, ab, keine), nach mehreren Spalten zugleich mit Umschalt+Klick (jeder Schlüssel zeigt Nummer und Richtung), leere Werte immer zuletzt, und die Reihenfolge wird gemerkt. Eine Spaltenauswahl fügt weitere Spalten hinzu: Lauf-Nummer, Auslöser, kurzer Commit, Versuch, Wartezeit, Datei und Ökosystem im Verlauf; Ökosystem, Lauf-Nummer, Auslöser, Commit, Versuch, Wartezeit, Läufe in 24 h, Standard-Branch, Sichtbarkeit, letzter Push und offene Pull Requests bei den Repositories. Der Monitor sendet jetzt die Lauf-Nummer und die Wartezeit jedes Laufs und einen kleinen Faktenblock je Repository (aus dem, was er schon gelesen hat; nichts Neues von GitHub).
- **`monitor_cli.py`**, die Befehlszeile als Client des laufenden Monitors (`status`, `health` oder `check`, `doctor`, `accounts`, `alerts`, `live`): Sie liest `GET /api/...` auf diesem Rechner oder unter `--url` / `MONITOR_URL`, gibt Text oder mit `--json` ein JSON-Dokument aus, kennt `--account`, `--sentinel`, `--level`, `--muted`, `--timeout` und `--lang` und nutzt stabile Exit-Codes (0 gut, 1 falsche Verwendung, 2 Monitor nicht erreichbar, 3 Zugangsdaten abgelehnt, 4 eingeschränkt, 5 Alarme gefunden mit `--fail-on`). `health` unterscheidet einen Monitor, der nicht antwortet, von einer fehlgeschlagenen GitHub-Anmeldung und von einem erschöpften Kontingent. Die Lite-Ausgabe beantwortet `status`, `doctor` und `health`. Sie schreibt nie nach GitHub; das Zugriffstoken des Netzwerkmodus steht in `MONITOR_TOKEN`. Die älteren Werkzeuge funktionieren weiter. Anleitung in acht Sprachen (`CLI.md`).
- Tests zu jeder Änderung, darunter die Sortierlogik, die mit Node wirklich ausgeführt wird, wo es installiert ist, die Befehle gegen einen falschen Monitor, jeder Exit-Code und ein Test, dass jedes Änderungsprotokoll in jeder Sprache seine Versionen von der neuesten zur ältesten auflistet, mit denselben Versionen wie die Quelle.

### Geändert

- **Die roten und gelben Hinweise stehen nicht mehr oben auf der Seite**: Dieselben Hinweise erscheinen in der Leiste am Fuß (der wichtigste) und in ihrem Fenster (alle).
- **Die README des Pakets** (`README_<Sprache>.txt`) trägt keinen Versionsverlauf mehr: Sie verweist auf das Änderungsprotokoll.
- Die Bilder der README, der Architektur und der Struktur sind für diese Version neu gezeichnet, mit einem Bild der neuen Tabellen und der Leiste.

### Entfernt

- **Die Urheberzeile am Fuß der Seite**: Autor und Lizenz stehen unter Info.

## [1.7.3]

Ein zweiter Wächter für Issues und Pull Requests, ein Reiter mit den Alarmen aller Wächter und Stummschaltungen, die von selbst enden. Collab liest nur; nichts davon schreibt nach GitHub.

### Hinzugefügt

- **Der Collab-Wächter** (`sentinel_collab.py`, nur vollständige Ausgabe, standardmäßig aus): die offenen Issues und Pull Requests deiner Repositories, mit einer eigenen Uhr (`sentinels.collab.refresh_seconds`), die den CI-Wächter nie beeinflusst. Sechs Regeln mit stabilen Codes: `collab.issue.stale`, `collab.issue.critical`, `collab.issue.external`, `collab.pr.review_pending`, `collab.pr.draft_old` und `collab.pr.conflict`. Er liest mit bedingten Anfragen (ein unverändertes Repository kostet kein Kontingent), höchstens `max_repos_per_tick` Repositories pro Runde, pausiert unter `min_rate_remaining`, hält seinen Zustand in `collab_state.json` (im Ordner jedes Kontos) und meldet nur Änderungen. Bots werden ausgelassen. Seine Ebene *Issues und Pull Requests* liegt im Reiter Wächter, und `GET /api/sentinel/collab` liefert sie.
- **Zwei neue Ereignisse**, `collab_new` und `collab_fixed`, für den Verlauf und alle Benachrichtigungskanäle (sie stehen in der Ereignisliste der Kanäle und im Ereignisschema).
- **Der Reiter Alarme** (vollständige Ausgabe): eine Liste mit den Alarmen aller Wächter, jeder mit Herkunft (CI oder Collab) und Stufe, ein Filter nach Herkunft und Stufe, ein Link nach GitHub und ein roter Punkt am Reiter mit den offenen Fehlern. `?view=alerts&sentinel=collab` öffnet ihn gefiltert.
- **Stummschaltungen mit Ende** (`alert_center.py`): Im Reiter Alarme lässt sich ein Alarm, eine Regel (ihr Code) oder ein ganzer Wächter für `alerts.mute_hours` Stunden stummschalten (standardmäßig 24, von 1 bis 720). Eine Stummschaltung läuft von selbst ab, lässt sich sofort aufheben, und ein kurzer Verlauf sagt, was seit wann bis wann stumm war. Es ist eine Notiz des Monitors, pro Konto in `alert_mutes.json`; auf GitHub ändert sich nichts.
- **`ignore_labels`** in den Regeln von Collab (standardmäßig `monitor:ignore`): Ein Issue oder Pull Request, das eine Person auf GitHub so beschriftet hat, löst keinen Alarm aus. Der Monitor schreibt nie Labels.
- **`GET /api/alerts`** (`?sentinel=`, `?level=`, `?muted=show|hide|only`) und **`GET /api/events`** (`?sentinel=`, `?since=`), beide nur lesend und pro Konto; `POST /api/alerts/mute` und `/api/alerts/unmute` (nur von diesem Rechner, Einmal-Token, wie jede andere Änderung).
- **Eine Checkliste in der Live-Ansicht** (Geheimnis mit 32 Zeichen oder mehr, Weiterleitung oder Tunnel zu `/api/webhook`, das Testereignis von GitHub, das Kontingent beobachten) und dieselben Schritte in der Webhook-Anleitung.
- **Eine Anleitung zum Collab-Wächter** in den acht Sprachen (`COLLAB.md`), von der Hilfe gefunden.
- Tests zu jeder Änderung: die Regeln und ihre stabilen Codes, die Kosten (bedingte Lesezugriffe, die Obergrenze pro Runde, die Pause), dass er nur liest, die Stummschaltungen (Bereiche, Ende, Grenzen, Verlauf, eine beschädigte Datei), das Ignorier-Label, die Endpunkte, dass Lite nichts davon hat, die Zustandsdateien jedes Kontos und der Demo und die Texte in den acht Sprachen.

### Geändert

- Die Einstellungsseite hat zwölf Collab-Einstellungen in einem Block des Reiters Wächter und daneben `alerts.mute_hours`.
- Die Dateien `alert_mutes.json`, `collab_state.json`, `ai_alerts_state.json` und `ALERTS_BRIEF.md` werden nie eingecheckt und reisen nie in einem Paket mit.

## [1.7.2]

Eine Kopfzeile, die sich in Reihenfolge lesen lässt und zum Fenster passt, die Schnellsteuerung fest in der oberen rechten Ecke, Info in der Seitenleiste und das Ende des Hinweises auf eine neue Version. Die Tests hinterlassen keine Dateien mehr neben dem Code; genau das hatte die Einstellungen einer Person durch die neutrale Vorlage ersetzt.

### Geändert

- **Die Zahlen der Kopfzeile, geordnet und in einem Raster** (alle Editionen): die erste Zeile geht jetzt von dem, was gerade läuft, zu dem, was Aufmerksamkeit braucht (laufend, wartend, Fehler, Erfolge, Rechenminuten, offene Issues, rote Workflows auf main, unsigniert), die zweite behält die Technik (Repositorys, heiß, Modus, gesparte Lesungen, Kontingent, Verbindung, aktualisiert). Jede Zeile ist ein Raster aus acht Spalten, vier oder zwei je nach Breite ihres eigenen Blocks, sodass beide Zeilen ihre Zeilen bei jeder Fensterbreite füllen, ab einem 1080p-Bildschirm aufwärts (eine Kachel erzwingt nie eine eigene Breite). Die lange Kontingent-Kachel belegt zwei Spalten.
- **Die Schnellsteuerung bleibt in der oberen rechten Ecke**: der Knopf für nur heiße, die Geschwindigkeitsliste (normal, schnell, Turbo) und die Gesundheitsmarken der Ökosysteme (und die Hinweise zu Budget und Pause) sind dort fest, in einer eigenen Spalte, und brechen darin um, ohne die Zahlen zu verschieben. Unter 1100 Punkten Breite rückt die Ecke über die Zahlen. Die Seite aller Konten blendet sie aus, wie sie die Zahlen ausblendet.
- **Einstellungen, Hilfe und Info sind nur noch in der Seitenleiste**: die Knöpfe für Zahnrad, Fragezeichen und Information verlassen die Kopfzeile. Einstellungen war schon ein Bereich der Leiste; Hilfe zu diesem Reiter bleibt am Fuß und **Info** kommt daneben. Die Anleitung der Einstellungen sagt das in den acht Sprachen.

### Entfernt

- **Der Hinweis auf eine neue Version in der Kopfzeile** (das orange Abzeichen) samt Code und Stil. Das Info-Fenster sagt weiterhin, ob es eine neuere Version gibt, die Konsole auch; die Einstellung `updates.check` und der Zwischenspeicher von 24 Stunden sind dieselben.

### Behoben

- **Die neutrale Vorlage konnte die Einstellungen einer Person ersetzen.** Drei Testgruppen (die Isolation von Lite, das Einmal-Token und der Lite-Teil der Konten) starteten einen Monitor, dessen erster Start `actions_monitor.json` oder `update_check.json` neben den Code schreibt, und nichts entfernte sie; kopierte man den Ordner `monitor/` über eine Installation, wurden die Einstellungen der Person (ihr eigener Ökosystem-Katalog) durch die Vorlage ersetzt, und alle Repositorys landeten in der Gruppe „Everything else“ (eine Ecke, die „Everything else 54“ zeigte). Jeder dieser Tests entfernt nun, was er erzeugt hat, und ein Test belegt es. Das Paket enthielt nie die Einstellungen oder den Katalog von jemandem und tut es weiterhin nicht.

## [1.7.1]

Eine neue Seite und derselbe Wächter hinter einem Vertrag. Die Seite hat links eine Seitenleiste mit dem Logo, den Bereichen in Gruppen und sechzehn Designs; der CI-Wächter ist jetzt einer der Wächter einer Registry, und genau das lässt die nächsten kommen. Was der Monitor zeigt und entscheidet, ändert sich nicht.

### Hinzugefügt

- **Eine Seitenleiste** (alle Editionen): das Logo des Werkzeugs (ein SVG, das mit den Farben des Designs gezeichnet wird und stillsteht, wenn das System weniger Bewegung verlangt), die Kontoauswahl, die Bereiche in drei einklappbaren Gruppen (Beobachten, Daten, System) und die Hilfe. Die Leiste lässt sich auf ihre Symbole einklappen, beide Wahlen merkt sich der Browser. Die obere Leiste zeigt den Namen des Bereichs und die Werkzeuge. Die Pfeiltasten, auch nach oben und unten, wechseln zwischen den Bereichen. Auf einem kleinen Bildschirm steht die Leiste oben. `?chrome=0` blendet sie aus, wie es die Reiterleiste ausblendete.
- **Sechzehn Designs** zusätzlich zu automatisch, hell und dunkel: die des Studios des Alarmsystems (Armor, Aqua, Midnight, Ember, Forest, Violet, Solar, Ice, Crimson, Mono, High contrast, Metallic, Professional, Videogame, Terminal und Blueprint), auswählbar in einer Liste unter Einstellungen > Dieser Browser oder mit `?theme=`. Jedes legt die Seite, die Seitenleiste, die Flächen, die Linien, den Text, den Akzent, die Ecken und die Schrift fest. Grün, Rot, Bernstein und Blau behalten in allen ihre Bedeutung, aufgehellt oder abgedunkelt, wo ein Design es braucht, damit jede Zahl mit 4,5:1 oder mehr lesbar ist; der Text einer Marke folgt ihrer Farbe.
- **`BaseSentinel`, `Alert` und `SentinelRegistry`** (`sentinel_base.py`, `sentinel_registry.py`; nur die vollständige Edition): der Vertrag eines Wächters (`start`, `stop`, `tick`, `get_status`, `get_alerts`, `get_metrics`, `get_config_schema`, `refresh_seconds`), ein Alarm mit stabilem Code, der nie von der Sprache abhängt (`ci.red`, `ci.stuck`, `ci.pending_sign`) und dem Konto, zu dem er gehört, und eine Registry, die jedem Wächter eine eigene Uhr gibt. `sentinels.<name>.enabled` in `actions_monitor.json` schaltet einen ein oder aus; ohne sie entscheidet `sentinel.enabled` wie immer, und wo beide etwas sagen, gewinnt der neue Block.
- **`SentinelCI`** (`sentinel_ci.py`): der Wächter von jeher hinter diesem Vertrag. Er hält den alten `Sentinel` und ändert nicht, wie dieser entscheidet: dieselbe Regel für Rot (der letzte abgeschlossene Lauf jedes Workflows auf dem Standardzweig), dieselben Dateien, dieselbe Schleife, derselbe Schnappschuss.
- Tests für jede Änderung dieser Version: der Vertrag, die Registry und ihre Schalter, der CI-Wächter und seine Alarme in zwei Sprachen, dass die Lite-Edition nichts davon lädt, die Seitenleiste und die sechzehn Designs (dass jedes alle Variablen definiert und dass Text, kleiner grauer Text, Akzent und die vier Statusfarben mit 4,5:1 auf Seite und Flächen lesbar sind).

### Geändert

- Das Design wird in einer Liste unter Einstellungen > Dieser Browser gewählt (früher ein Knopf, der automatisch, hell und dunkel durchlief); ein von einer früheren Version gespeichertes Design wird weiter verstanden.
- Die Farbe einer Marke, eines Balkens und einer Meldung, die weiß auf Rot, Bernstein oder Grün war, ist jetzt die, die auf dieser Farbe im verwendeten Design lesbar ist.
- Der Wächter wird über die Registry gestartet; `SENTINEL["obj"]` ist weiterhin der CI-Wächter, alles, was ihn etwas fragte, funktioniert also weiter. Die Ereignisse, die Dateien und die Endpunkte sind dieselben.

### Behoben

- Ein Test der 1.7.0 las die Ausgabe von `tasklist` mit der falschen Codepage und konnte auf einem Windows mit anderer Sprache fehlschlagen.
- **Eine Ablehnung konnte unterwegs verloren gehen** (alle Editionen): ein POST, den der Monitor ablehnte, bevor er seinen Rumpf las (fehlendes Token, zu großer Rumpf), schloss die Verbindung mit ungelesenen Daten, und Windows, manchmal auch Linux, antwortete mit einem Reset: der Client sah eine abgebrochene Verbindung statt des geschuldeten 403. Der Monitor liest und verwirft jetzt nach der Antwort, was vom Rumpf übrig ist (bis 1 MB, höchstens 2 Sekunden), sodass die Antwort immer ankommt. Die Ablehnung selbst, ihr Code und ihr Text sind dieselben. Ein Test sendet die Kopfzeilen, wartet und sendet den Rumpf, und schlägt ohne dies fehl.

## [1.7.0]

Mehrere Konten in der kompletten Ausgabe, jedes ein eigener Monitor, und eine Seite, die sie kennt. Die Lite-Ausgabe bleibt unverändert: ein Konto, und sie zeigt die neuen Optionen nicht einmal.

### Hinzugefügt

- **Mehrere Konten** (nur die komplette Ausgabe). Ein Ordner `accounts/<id>/` pro Konto (eine Person oder eine Organisation) mit eigener `actions_monitor.json`, eigenem Cache, eigenen Ereignissen, eigener Analytik, eigenem Wächterzustand und eigenen Protokollen; `accounts/global.json` ist optional (`default_account`, `enabled_accounts`) und `MONITOR_ACCOUNTS_DIR` verschiebt den Ordner. Die ID besteht aus Kleinbuchstaben, Ziffern, `_` und `-` (bis zu 40), ist also immer ein sicherer Ordnername. Ohne einen Ordner `accounts/` ändert sich nichts: ein Konto, seine Dateien neben dem Code.
- **Ein Supervisor** (`accounts_supervisor.py`): Mit einem Ordner `accounts/` startet `python actions_monitor.py` einen kleinen Prozess auf dem üblichen Port, der pro Konto einen Monitor ausführt (`account_child.py`), jeden auf einem eigenen Port von `127.0.0.1`. Ein Absturz, eine langsame Antwort oder ein Ratenlimit eines Kontos berührt nie ein anderes; ein ausgefallenes Konto wird mit wachsender Wartezeit neu gestartet (2, 5, 15, 30, 60, dann 120 Sekunden), und die Übersicht meldet es in der Zwischenzeit als ausgefallen. Er liest nichts von GitHub und schreibt nichts; beim Beenden werden alle von ihm gestarteten Prozesse beendet, auch unter Windows.
- **Die API der Konten**: `GET /api/accounts` (die Übersicht), `GET /api/accounts/<id>/status`, und jede andere `/api/`-Anfrage geht an das mit `?account=<id>` oder dem Header `X-Account-Id` genannte Konto (ohne Angabe das Standardkonto; ein unbekanntes Konto ergibt 404). Die Zugriffsregeln sind die eines einzelnen Monitors, und das Einmal-Token einer Änderung wird bei demselben Konto angefordert, an das die Änderung geht.
- **Ein Webhook für alle**: `POST /api/webhook` ist eine einzige Adresse für die Installation; der Supervisor liest nur den Eigentümer in `repository.full_name` und reicht das Ereignis unverändert an das Konto weiter, dessen `github_owner` dieser Eigentümer ist und das die Signatur mit seinem eigenen Geheimnis prüft. Ein Eigentümer, den niemand beobachtet, wird beantwortet und ignoriert.
- **`--accounts`, `--account <id>` und `--migrate-accounts [--apply]`**: listen die Konten, führen nur eines als gewöhnlichen Monitor aus und verschieben das alte Layout nach `accounts/default/`. Die Migration ist ein Probelauf, außer mit `--apply`, verschiebt oder löscht die Originale nie, verweigert einen zweiten Lauf und berührt die Dateien der Lite-Ausgabe nicht.
- **Die Seite mit mehreren Konten**: eine Kontoauswahl unter der Kopfzeile und ein Eintrag **Alle Konten** mit einer Karte pro Konto (Zustand, Repositorys, laufend, fehlerhaft). Jedes Fenster behält sein eigenes Konto und seine Ansicht, die aus der Adresse gelesen werden.
- **Ansichten per Adresse** (`?view=now|alerts|charts|repos|settings|live` und `?chrome=0`, ein Bildschirm ohne Kopfzeilen-Tasten, Tabs und Filter für eine Wand oder einen zweiten Monitor). Die Ansicht **Live** zeigt die letzten von GitHub gesendeten Ereignisse, den Zustand des Webhook-Empfängers (nie das Geheimnis) und eine Auswahl des Arbeitsmodus. `GET /api/live-status` ist ihre Quelle.
- `tools/demo_accounts.py` für die Bilder, die Anleitung `ACCOUNTS.md` in acht Sprachen und Tests für jede Änderung (die Suite wuchs von 866 auf 914).

### Geändert

- Die Zustandsdateien eines Monitors, der ein Konto von mehreren ist, liegen über `state_dir()` in seinem Ordner; ein einzelner Monitor hält sie wie immer neben dem Code.
- Die Bilder des README sind neu aufgenommen, und das README zeigt in acht Sprachen die Konten.

### Sicherheit

- Der Supervisor und die Konten lauschen nur auf `127.0.0.1`, außer der Netzwerkmodus ist an. Der Webhook hat keine Host-Prüfung und kein Zugriffstoken (ein Tunnel ändert den Host), und sein Beweis ist weiterhin der HMAC von GitHub; ein Cookie der Sitzung wird nie an ein Konto weitergegeben.

### Behoben

- Die Live-Ansicht von 1.6.8 hatte keinen Zustand des Empfängers: Bei ausgeschaltetem Webhook oder einem Geheimnis unter 32 Zeichen sagte sie nichts, jetzt sagt sie, was von beidem zutrifft.

## [1.6.8]

Der HTTPS-Proxy aus 1.6.7 wird jetzt gegen einen echten Proxy geprüft, die Bilder sind neu aufgenommen, und die Änderungshistorie ist bis 1.6.3 übersetzt.

### Hinzugefügt

- `python tools/manual_check_live.py proxy HOST [PORT] [VERBINDEN]`: prüft über deinen echten HTTPS-Proxy auf Port 443, dass die Seite hineingelassen wird (die Sitzung öffnet sich mit dem Zugriffstoken im Body, und das Cookie kommt `Secure` und `HttpOnly` zurück) und dass drei Anfragen abgelehnt bleiben (das andere Schema, ein anderer Hostname, der Name mit Port). Es liest das Zugriffstoken aus `MONITOR_ACCESS_TOKEN`, gibt es nie aus und sagt ohne Argumente, was in nginx oder Caddy einzutragen ist.
- `tools/demo_monitor.py --network` zeigt die Seite so, wie sie im Netzwerkmodus aussieht (die dauerhafte rote Leiste, in den Einstellungen die Warnung für alle Schnittstellen und der neue Proxy-Name), damit sie fotografiert werden kann; die Demo lauscht weiterhin nur auf `127.0.0.1`. `tools/make_screenshots.py` nimmt damit zwei neue Bilder auf: `web_network_now` und `web_network_settings`.
- Tests, die die ganze Kette durchlaufen: ein Client über echtes TLS, ein Reverse-Proxy, der das TLS beendet und `Host` und `Origin` ohne Port weiterleitet, und dahinter der echte Monitor. Sie prüfen, dass eine Änderung von der Seite aus die Einstellungen erreicht, dass dieselbe Anfrage ohne `listen.proxy_public_host` abgelehnt wird, dass ein falsches Schema, ein falscher Name oder Port abgelehnt bleibt, dass sich die Sitzung öffnet und das Cookie `Secure` ist und dass die Prüfung von Hand mit dem Proxy übereinstimmt und nie das Token ausgibt (die Suite wuchs von 858 auf 866).

### Geändert

- Die Änderungshistorie (Hilfe > Änderungsprotokoll) ist in den anderen sieben Sprachen von 1.6.8 bis 1.6.3 übersetzt (1.6.7 und 1.6.5 waren es schon); die Einträge vor 1.6.3 behalten den englischen Text unter einem übersetzten Hinweis.
- Die Bilder des README sind neu aufgenommen, 76 insgesamt, und das README zeigt in acht Sprachen den Untertab Erweitert der Einstellungen und die zwei Bilder des Netzwerkmodus.
- `docs/MIGRATING.md` hat einen Block von 1.6.7 auf 1.6.8, und die Roadmap in acht Sprachen führt auf, was bleibt: die älteren Einträge der Historie und die Prüfungen, die deine eigenen Dienste brauchen.

### Behoben

- Die Historie von 1.6.7 sagte, nur 1.6.7 und 1.6.5 seien übersetzt und der Proxy nur mit der Prüfung getestet; diese Version übersetzt den Rest bis 1.6.3 und prüft den Proxy durchgängig, wie oben beschrieben.

## [1.6.7]

Ein HTTPS-Proxy auf dem Standardport 443 funktioniert jetzt mit dem Netzwerkmodus, und ein weiterer Teil der Änderungshistorie ist übersetzt.

### Hinzugefügt

- `listen.proxy_public_host` (Einstellungen > Erweitert > Netzwerk, standardmäßig leer): der öffentliche Hostname eines HTTPS-Proxys auf dem Standardport 443, der `Host` und `Origin` ohne Port weiterleitet. Bisher verglich die Prüfung beide mit dem Port des Monitors, sodass ein solcher Proxy abgelehnt wurde; dieser eine Name wird jetzt unverändert akzeptiert. Er zählt nur, solange der Netzwerkmodus an ist und die Sitzung HTTPS nutzt (direktes TLS oder `listen.secure_cookie`), muss ein einfacher Hostname sein (ein Port, ein Pfad, ein Benutzer, ein Leerzeichen oder ein IPv6-Literal machen ihn leer), kann wie jede vom Schema als `secure` markierte Einstellung nur vom Rechner selbst geändert werden, und sein Label und seine Hilfe gibt es in acht Sprachen.
- Tests für jede Änderung dieser Version (die Suite wuchs von 843 auf 858, und die neue Datei prüft die Prüfung, den Wert, das Schema und die Texte).

### Sicherheit

- Die Ausnahme der Prüfung ist so eng wie möglich: Nur dieser Name wird ohne Port akzeptiert, nie ein anderer Host ohne Port, nie über einfaches HTTP, und der `Origin` muss denselben Namen mit dem Schema `https` tragen (ein anderes Schema, ein Port, ein Pfad, ein Benutzer oder ein anderer Host werden weiterhin abgelehnt). Der Name des Proxys erscheint nie im öffentlichen Zustand der Prüfung.

### Geändert

- Die Änderungshistorie (Hilfe > Änderungsprotokoll) ist in den anderen sieben Sprachen für 1.6.7 und 1.6.5 übersetzt (1.6.6 war es schon); die älteren Einträge behalten den englischen Text unter einem übersetzten Hinweis und folgen, die neuesten zuerst.
- `docs/ADVANCED.md` (acht Sprachen) erklärt den Proxy auf dem Standardport, statt zu sagen, er werde nicht unterstützt, `docs/MIGRATING.md` hat einen Block von 1.6.6 auf 1.6.7, und die Einstellungsanleitung und der Index der Hilfe sind neu erzeugt.

## [1.6.6]

Korrekturen am Netzwerkmodus und an `act`, die offenen Punkte aus 1.6.5 und die Änderungshistorie in acht Sprachen.

### Hinzugefügt

- Eine dauerhafte rote Leiste oben in den Einstellungen, wenn der Netzwerkmodus auf allen Schnittstellen lauscht (`listen.host` = `0.0.0.0`), in acht Sprachen. Bisher sagte das nur `--doctor`.
- `POST /api/access` mit `{"token": "..."}`: öffnet die Sitzung des Netzwerkmodus mit dem Zugriffstoken im Body, sodass es nie in einer Adresszeile, im Verlauf oder in einem Protokoll steht. Dieselben Prüfungen wie bei jeder Anfrage (Host, Origin, Sperre nach falschen Tokens, Vergleich in konstanter Zeit); das Cookie kommt `HttpOnly`, `SameSite=Strict` und bei HTTPS `Secure` zurück. Die Adresse mit `?access=` aus 1.6.5 funktioniert weiter.
- Ein Zähler für die Fehler, die der Monitor absichtlich verschluckt (`degraded.py`): eine strukturierte Zeile in der Konsole je Fehler, eine Zählung nach Herkunft in `degraded.json` neben dem Monitor, die neue `--doctor`-Prüfung `degraded` und eine Zeile „Verschluckte Fehler“ im Info-Fenster. Das Verhalten bleibt gleich: Sie halten den Monitor weiterhin nie an.
- Die Änderungshistorie (Hilfe > Änderungsprotokoll) hat jetzt je Sprache eine Übersetzungsdatei `docs/CHANGELOG_<Sprache>.md` mit denselben Versionen und Abschnitten wie die englische Quelle; `tools/make_help_index.py --check` und ein Test schlagen fehl, wenn eine Version in einer Übersetzung fehlt. Noch nicht übersetzte Einträge sagen das in der Sprache des Lesers.
- Tests für jede Änderung dieser Version (die Suite wuchs von 811 auf 843).

### Behoben

- **Der Netzwerkmodus über HTTPS war von der Seite aus unbrauchbar.** Die Same-Origin-Prüfung akzeptierte nur einen `http://`-Origin; bei direktem TLS oder einem HTTPS-Proxy (`listen.secure_cookie`) wurde das eigene `Origin: https://...` des Browsers abgelehnt und jede Änderung (Einstellungen, Bestätigungen) bekam 403. Die Prüfung bildet den erlaubten Origin jetzt aus dem Schema der Sitzung (https oder http, nie beides), vergleicht Host und Port exakt und lehnt fehlerhafte Origins ab. Getestet mit einem echten TLS-Server und einem vom Test erzeugten Zertifikat.
- `act`: Stop gibt den Lauf jetzt frei, sodass der nächste Start nicht mehr für immer `busy` meldet, wenn der Prozess nicht endet; ein verspäteter Worker berührt nie einen neueren Lauf; Ausgabe-Pipe und Timer werden in jedem Fall geschlossen (normales Ende, Zeitlimit, Stop, unerwarteter Fehler) und die Suite gibt keine `ResourceWarning` mehr aus.
- `tools/make_screenshots.py` konnte grußlos enden: Der Browser läuft ohne abgefangene Pipes und mit Zeitlimit, ein fehlender Browser oder eine nicht startende Demo wird gemeldet, `MONITOR_BROWSER` nennt einen Browser von Hand, und der Exit-Code ist 1, wenn ein Bild nicht entstand.

### Sicherheit

- Im Netzwerkmodus kann jede Einstellung, die das Schema als `secure` markiert, nur vom Rechner selbst geändert werden, nicht mehr nur die vier bisherigen Familien (`listen.`, `github_token.`, `act.`, `github_actions.`): auch Webhook, KI-Aktionen, Benachrichtigungen, OpenTelemetry, Spiegel, Runner, Ausgaben und der Rest. Die Liste wird aus dem Schema gelesen, daher ist eine neue sichere Einstellung abgedeckt, ohne dass jemand daran denken muss; ein Test geht sie alle durch.

### Geändert

- Die Bilder von Info, Hilfe, Jetzt, Basis und Erweitert in README und Anleitungen wurden neu aufgenommen.
- `docs/ADVANCED.md` (acht Sprachen): HTTPS mit eigenem Zertifikat oder hinter einem Proxy, die Origin-Regel, die per POST geöffnete Sitzung und die Warnleiste.

## [1.6.5]

Eine Version für Integrität und Sicherheit: keine große neue Funktion. Was sich nicht beweisen lässt, gilt nicht mehr als sicher.

### Hinzugefügt

- Neue Einstellungen, alle mit konservativem Standardwert: `dispatch.required_ci` (und in der Datei `dispatch.required_ci_repos` und `dispatch.required_ci_profiles`), `act.allow_symlinks`, `listen.tls_cert_file`, `listen.tls_key_file`, `listen.secure_cookie`, `listen.max_failed_attempts`, `webhook.replay_seconds`, `webhook.max_per_minute`; die Einstellungsanleitung wird neu erzeugt.
- `finalize --accept-legacy` für Stapel, die eine ältere Version geschrieben hat, sowie die `--doctor`-Prüfungen `risks` und `backend` (acht Sprachen).
- Tests für jede Änderung dieser Version (die Suite wuchs von 729 auf mehr als 800).

### Sicherheit

- **Ein grüner Commit braucht die verpflichtende CI.** `gha_dispatch_all.py` hält einen Commit nur für grün, wenn die verpflichtenden Workflow-Dateien darauf erfolgreich waren (standardmäßig `ci.yml`; `dispatch.required_ci`, `dispatch.required_ci_repos`, `dispatch.required_ci_profiles`), nichts fehlschlug, ablief oder auf eine Freigabe wartet (`action_required` blockiert wie ein Fehler), nichts mehr läuft und die Liste der Läufe vollständig ist (es liest bis zu fünf Seiten; eine längere Liste ist nicht grün).
- **Ein fehlgeschlagenes `git fetch` stoppt den Versand** dieses Repositorys, git-Befehle haben ein Zeitlimit und die Commit-IDs werden geprüft; ein alter `origin/main` gilt nie als Beweis.
- **Der Katalog kann seinen Ordner nicht verlassen und den Versand nicht ändern.** `tool` muss ein einfacher Dateiname im Werkzeugordner sein (Links, die ihn verlassen, werden ebenfalls abgelehnt); `extra` darf nur Workflow-Eingaben der Form `-f key=value` enthalten (nie `dry_run`, `ref`, `-R`, `--ref`); `finalize_flags` nur lange Flags; die Argumente von `gh workflow run` werden aus den geprüften Teilen gebaut und beim Auslösen des Stapels erneut geprüft.
- **Alte Stapel werden nicht blind signiert.** `finalize` bietet nur einen Lauf zum Signieren an, dessen Stapel festgehalten hat, auf dem geprüften Commit gebaut worden zu sein. Ein von einer älteren Version geschriebener Stapel ist `needs_review`; `finalize --accept-legacy` liest den Lauf erneut von GitHub, akzeptiert ihn nur, wenn sein Commit der festgehaltene ist, warnt und verlangt vor jeder Signatur das Wort LEGACY.
- **`act` bleibt im Arbeitsbereich.** Der Klon wird aufgelöst und muss ein echter Ordner des Arbeitsbereichs sein (ein Link, ein Name mit `..` oder ein `.github`, das woanders hinzeigt, wird abgelehnt; `act.allow_symlinks` erlaubt einen Link auf einen Klon). Zeitlimit und Stop beenden den gesamten Prozessbaum, den der Lauf gestartet hat (eine Prozessgruppe unter Linux und macOS, `taskkill /T` auf die eigene PID unter Windows), und entfernen die `act-`-Container, die dieser Lauf erzeugt hat.
- **Netzwerkmodus**: HTTPS direkt mit deinem eigenen Zertifikat und Schlüssel (`listen.tls_cert_file`, `listen.tls_key_file`; TLS 1.2 oder neuer; der Monitor startet nicht über einfaches HTTP, wenn sie nicht nutzbar sind) oder das `Secure`-Cookie hinter einem HTTPS-Proxy (`listen.secure_cookie`); das Zugriffstoken verlässt sofort die Adressleiste (Weiterleitung, kein `Referer`); eine Adresse, die zu viele falsche Tokens sendet, wird fünf Minuten lang abgelehnt (`listen.max_failed_attempts`); die Adresse der Seite ist die, auf der der Server lauscht; es werden nur IPv4-Adressen akzeptiert, in den Einstellungen wie in der Prüfung; die Konsole sagt, wenn die Verbindung einfaches HTTP ist.
- **Webhook**: Jede Zustellung braucht ihre `X-GitHub-Delivery`-ID, und eine wiederholte wird `webhook.replay_seconds` lang ignoriert; ein Repository kann höchstens `webhook.max_per_minute` akzeptierte Ereignisse pro Minute auslösen; der Eigentümer in `full_name` muss das beobachtete Konto sein; eine Adresse ist im Netzwerkmodus auf 120 Anfragen pro Minute begrenzt; ein akzeptiertes Ereignis verwirft die gespeicherten bedingten Abfragen dieses Repositorys und markiert es für den nächsten Zyklus; ein Signatur-Header mit ungewöhnlichen Zeichen wird schlicht abgelehnt.
- **MCP-Server**: Eine Nachricht mit falscher Form (Parameter, Argumente, ID, Methode) erhält einen Fehler nur für diese Nachricht, ein unerwarteter Defekt in einem Werkzeug ist ein interner Fehler, der den Server nicht beendet, und eine Zeile über 64 KB wird abgelehnt.
- **Das gespeicherte GitHub-Token geht nur an `gh`.** Es wird nicht mehr in die Umgebung des Monitors gelegt, sodass `act`, dein Benachrichtigungsbefehl und jeder andere Kindprozess es nicht erben können.
- **Ein GET schreibt nie.** Die Kopie des Tagesberichts im Audit-Ordner ist ein POST mit dem Einmal-Token (`/api/sentinel/parte/save`); `?save=1` beim GET ist entfallen.
- `--doctor` nennt gefährliche Kombinationen (Netzwerkmodus auf allen Schnittstellen, KI-Aktionen, die bei aktivem Netzwerkmodus ausführen, `act` bei aktivem Netzwerkmodus, das Token in einer einfachen Datei) und zeigt, wo das Token liegt, nie das Token.

### Behoben

- `max_per_hour` der Benachrichtigungen begrenzt jetzt Nachrichten (eine Einheit pro Kanal, sofort unter einer Sperre gebucht) und nicht Ereignisse; ein Kanal, der nicht senden kann, bucht nichts.
- Zwei gleichzeitige Speichervorgänge der Einstellungen verlieren nicht mehr einen von beiden (eine Sperre im Prozess und eine Sperrdatei).
- Der Export der Signaturwarteschlange sagt, warum er nicht geschrieben hat (ein abgelehntes Laufwerk oder Netzwerkpfad, ein Ordner statt einer Datei, der Systemfehler), statt nur abzulehnen.
- Die Wartezeit beim sekundären Limit und die Wiederholung nach einer Zeitüberschreitung tragen einen zufälligen Jitter.
- Der Test, der das Zip in einem sauberen Ordner entpackt, gehört nicht mehr zur gewöhnlichen Suite: `make_release.py` führt die Suite einmal mit Zeitlimit aus, dann die saubere Installation als eigene Stufe, und zeigt stdout und stderr, wenn eine fehlschlägt.

### Geändert

- Die Anleitungen zu Benachrichtigungen, Webhook, erweiterten Funktionen, Ausgaben, KI-Warnungen und Migration sagen all das in acht Sprachen; `docs/MIGRATING.md` hat einen Block von 1.6.4 auf 1.6.5.

## [1.6.4]

### Hinzugefügt

- **Warnungen für KIs**: Der Monitor schreibt einen lokalen, schreibgeschützten Feed (`ai_alerts.jsonl`, eine Zeile pro Ereignis, und `ALERTS_BRIEF.md`, in jedem Zyklus neu geschrieben, standardmäßig 2 KB) mit einer Warnung pro rotem Workflow: stabile ID, Schweregrad, wahrscheinliche Ursache als echt oder vorübergehend unterschieden mit bearbeitbaren Regeln, vorgeschlagene Aktion und ein Zustand (offen, bestätigt, von selbst gelöst, wenn der Workflow wieder grün wird). Alles läuft durch einen Bereiniger für Tokens, Schlüssel, E-Mail-Adressen, IP-Adressen und Home-Ordner. `GET /api/ai/brief` und `GET /api/ai/alerts`, ein optionaler schreibgeschützter MCP-Server (`mcp_server.py`: `get_alerts`, `get_red_repos`, `get_run_failure`, `get_quota` und `ack_alert` mit `--allow-ack`), eine Benachrichtigung, wenn eine neue ECHTE Warnung erscheint, ein optionaler Hook zu einer Adresse auf diesem Rechner (aus) und ein optionales `ai_hint` in `ci_red.json`. Neue Anleitung `AI_ALERTS.md` in acht Sprachen.
- **Optionale Funktionen, alle standardmäßig aus, jede mit eigenem Schalter unter Einstellungen > Erweitert** und Tests, die belegen, dass sie ohne Schalter, Bestätigung oder Token ablehnen: der Netzwerkmodus (eine private Adresse, ein Zugriffstoken für jede Anfrage, akzeptierte Hostnamen, eine dauerhafte rote Leiste, Expositionsschlüssel, die nur vom Rechner selbst änderbar sind); ein vom Monitor gehaltenes GitHub-Token im sicheren Speicher des Systems (Windows DPAPI, macOS Keychain, Linux Secret Service, sonst eine Datei mit Rechten 600) und nie in einer Einstellung, einem Protokoll oder einer Antwort, mit Löschknopf; Aktionen auf GitHub (erneut ausführen, abbrechen, schließen, mergen), jede einzeln bestätigt, nachdem genau angezeigt wurde, was gesendet wird; einen Workflow hier mit `act` aus einer geschlossenen Liste ausführen, ohne echte Secrets; eine lokale Kopie von Artefakten; eigene Runner (frei, belegt, offline, optional Festplatte und Last); OpenTelemetry-Export (Traces und Metriken, OTLP/HTTP JSON); die Organisationen des Logins; FinOps nach Job-Labels (Linux, Windows, macOS und größere Runner), der Preis der Minuten über den enthaltenen hinaus, Codespaces, Packages und Speicher aus dem Abrechnungsbericht. Neue Anleitung `ADVANCED.md` in acht Sprachen und `tools/manual_check_live.py`, um die echten Dienste von Hand auszuprobieren.
- `--doctor --json`; der Doctor meldet auch belegte Ports, das verbleibende Kontingent, ob du eine eigene Ziele-Datei hast, das Einmal-Token und die Exposition. Das README des Pakets beginnt mit der Wahl des Starters (komplett, lite, Stapel, Terminal, Doctor, Demo).
- Die Terminal-Anwendung bearbeitet die einfachen Einstellungen (nicht die Sicherheitseinstellungen) und hat einen KI-Tab; ein dauerhafter Hinweis für Einstellungen, die einen Neustart brauchen, übersteht ein Neuladen; die Kopfzeile zeigt, wenn das A10 des Wächters wegen Kontingent pausiert ist und wie viel vom Minutenbudget verbraucht ist; die Begrüßung merkt sich auch der Server.
- `redrule.py` ignoriert die dynamischen Läufe von Abhängigkeits-Updates wie das Dashboard, und die gemeinsamen Fälle der Regel sind jetzt eine Test-Fixture.

### Geändert

- **Die Hilfe ist in acht Sprachen vollständig**: Die Dokumente zu Roadmap, Mitwirken, Sicherheit und Support sind übersetzt, die festen Beschriftungen des Änderungsprotokolls sind übersetzt und seine Einträge sind mit einem übersetzten Hinweis als nur englisch gekennzeichnet; `tools/make_help_index.py --check` und ein Test schlagen fehl, wenn einem Thema eine Sprache fehlt. Eine Suche zeigt höchstens 30 Treffer, und ein riesiges Dokument hält den Server-Thread nicht mehr auf.
- Die rote Kachel zählt Workflows in beiden Ausgaben und sagt, in wie vielen Repositorys. Die Lite-Ausgabe übernimmt beim ersten Start den Aktualisierungsrhythmus der kompletten.
- Ein vorübergehender Fehler (ein TLS-Schluckauf, ein 5xx) wird mit exponentiellem Backoff wiederholt und erst nach drei Zyklen in Folge als Fehler angezeigt; das letzte Bild bleibt.
- Die Terminalansicht der Lite-Ausgabe fragt nicht mehr nach dem Wächter; die Lite-Ausgabe lädt das Wächter-Modul nie (die lokale Prüfung zog nach `localguard.py` um).
- `--demo` leitet jede Datei, die es schreiben könnte (Protokolle, Caches, Ereignis-Feed, Verlauf, Begrüßung), in seinen temporären Ordner um.

### Sicherheit

- Bei ausgeschaltetem `updates.check` oder eingeschaltetem `airgapped` stellt der Monitor für den Update-Hinweis überhaupt keine Netzwerkanfrage (getestet).
- Gegen die echte GitHub-API geprüft: Die Scopes des Tokens werden korrekt gelesen, die Liste der Organisationen und der Abrechnungsbericht degradieren still (ein Login ohne den Scope `user` erhält „nicht gefunden“, und der Monitor behält die Schätzung).

## [1.6.3]

### Hinzugefügt

- **Info-Panel** (die **i**-Taste der Kopfzeile, in beiden Ausgaben): Version, Ausgabe, Autor, Lizenz, Python und System, Links (Repository, Releases, Änderungsprotokoll, Dokumentation, Issues), die verwendeten Dateien (nur lesend), der Zustand des Servers, die Danksagungen der Bibliotheken und eine Taste, die die Informationen für den Support kopiert (kein Secret, kein Token, der Home-Ordner als `~`). `GET /api/about` und `--about` in der Konsole.
- **Hilfe-Panel** (die **?**-Taste, die Taste `?` und ein „?“ in der Tab-Leiste, das die Seite des aktuellen Tabs öffnet): die gesamte Dokumentation (README, Schnellstart, jede Anleitung, Roadmap, Änderungsprotokoll, Mitwirken, Sicherheit) als durchsuchbarer Index, in der Sprache der Seite und auf Englisch, wo ein Dokument nicht übersetzt ist, vom lokalen Server ohne Internet ausgeliefert. Er wird von `tools/make_help_index.py` aus den echten Dokumenten gebaut (`--check` in der CI), sodass kein Text doppelt geschrieben wird; das Markdown wird sicher dargestellt (alles maskiert, keine Bilder geladen, nur `http(s)`-Links und Links zu anderen Dokumenten). In der Konsole: `--help-topics [THEMA]` und `--help-search WÖRTER`.
- **Hinweis auf eine neuere Version**: ein dezentes Abzeichen in der Kopfzeile, eine Zeile in Info, in der Konsole und in `--doctor`, wenn ein neueres Release veröffentlicht ist. Eine schreibgeschützte Anfrage pro Tag an die öffentliche Release-Seite, über denselben Client wie alles andere (bedingte Abfrage), lädt oder installiert nie etwas, sendet nichts über dich, ignoriert Vorabversionen, vergleicht Versionen als Zahlen (1.6.10 ist neuer als 1.6.9), schweigt offline und ist mit `updates.check` oder in einer abgeschotteten Installation (`airgapped`) aus.
- **Einstellungen > Grundlagen**, der erste Tab: Browser beim Start öffnen, der Update-Hinweis, der Schalter für abgeschottete Installation, das Einmal-Token, die Erkennungsoptionen, die Lebenszyklusregeln sowie Plan und Kontingente. Darunter, was der Monitor im Konto gefunden hat (Besitzer, gefundene, beobachtete und ausgelassene Repositorys), die Neuigkeiten und die vorgeschlagenen Gruppen.
- **`--doctor`**: Python, `gh`, der Login, das Kontingent, das Netzwerk, die Schreibberechtigung des Ordners, ein freier Port und die optionalen Docker, Rich und Textual; jeder Fehler kommt mit dem genauen Befehl, der ihn behebt, in acht Sprachen.
- **`--demo`**: die Seite mit erfundenen Daten, ohne `gh`, ohne Login und ohne Netzwerk; nichts von dir wird gelesen oder geschrieben.
- **Eine Begrüßung in drei Schritten** beim ersten Öffnen der Seite (was er tut, was er in deinem Konto gefunden hat, wohin es danach geht).
- **Automatische Erkennung**: Ereignisse für ein neues, verschwundenes, archiviertes oder wieder aktiviertes Repository (Konsole, Einstellungen > Grundlagen und in der kompletten Ausgabe die Benachrichtigungen); eine vorgeschlagene Gruppe, wenn drei oder mehr nicht zugeordnete Repositorys ein Präfix teilen, erst nach deiner Bestätigung und mit einer Kopie der Datei hinzugefügt; Lebenszyklusregeln, um Forks sowie leere und private Repositorys auszulassen; eine optionale automatische Aktualisierungshäufigkeit, die der echten Aktivität im Rahmen des Aufrufbudgets folgt.
- **Ein Einmal-Token** (`session_guard`, standardmäßig an), das die Seite unmittelbar vor dem Speichern einer Einstellung oder dem Bestätigen einer Aktion verlangt, und eine **Neustart-Leiste** auf jedem Tab, solange eine gespeicherte Einstellung auf einen Neustart wartet.
- **Stufen des Workflow-Linters** (Information, Warnung, Fehler) als Filter in der Seite und `Scripts` in der Terminal-Anwendung.
- **Kontingente und Pläne für jede Art von Konto**: dein Plan unter Einstellungen > Grundlagen; die Zahlen (enthaltene Minuten als Geld, Tarife je System, Parallelität, Grenzen eines Jobs und eines Laufs, Kontingente der API) liegen in `quotas.json`, die du ohne neue Version bearbeiten kannst; abrechenbare Minuten getrennt von Uhrminuten (öffentliche Repositorys kosten nichts, private nutzen den Multiplikator von Windows oder macOS), eine als Schätzung markierte Monatsprognose, eine Warnung einmal im Monat bei 75 % und 90 % der enthaltenen Minuten über die Benachrichtigungen, laufende und wartende Jobs gegen das Limit des Plans, Jobs nahe dem 6-Stunden-Limit und die Art des Tokens, aus den eigenen Headern von GitHub gelesen (mit dem Rat, sich anzumelden, wenn nur noch 60 Aufrufe pro Stunde übrig sind). Die echte Nutzung kommt nur aus dem optionalen, schreibgeschützten Abrechnungsbericht (`quota.billing_api`, standardmäßig aus, still bei 403 oder 404). `GET /api/quota`.
- **Arbeitsmodi: normal, schnell und Turbo** (`modes.py`, Anleitung `MODES`): eine Auswahl mit Tachometer-Symbol in der Kopfzeile und `--mode` / `--mode-minutes` in der Konsole, in beiden Ausgaben. Die Voreinstellungen liegen im Block `modes` der Konfiguration; vor dem Start zeigt die Seite die Aufrufe pro Stunde im ungünstigsten Fall, was die bedingten Abfragen üblicherweise sparen und wie lange das verbleibende Kontingent reichen würde; er kehrt von selbst zu normal zurück, wenn die Zeit abgelaufen ist oder das Kontingent unter `min_rate_remaining` fällt, mit einem Hinweis; ohne Login (60 Aufrufe pro Stunde) werden schnell und Turbo mit Begründung abgelehnt; er braucht das Einmal-Token, lebt im Speicher und das Konsolen-Banner nennt ihn. `GET` und `POST /api/mode`.
- **Nach einem sekundären Ratenlimit** wartet der Monitor mindestens eine Minute und verdoppelt dann die Wartezeit bis fünf Minuten, statt schnell erneut zu versuchen.
- **Die interaktive Terminal-Anwendung** `tui_textual.py` (optional, `pip install textual`): Tabs Übersicht, Repositorys, Builds, Leistung, Scripts und Einstellungen (die Grundschalter), ein Filter, die Stufen des Linters, Aktualisieren, im Browser öffnen, Info und Hilfe; `--lite` zeigt die Lite-Tabs. Die einfache Rich-Ansicht (`tui.py`, `--once`) bleibt und hat ebenfalls `--about` und `--help-topics`.
- **Die Ausgabe ist auf einen Blick klar**: ein Start-Banner (`GitHub Actions Monitor LITE 1.6.3 · Port 8766 · actions_monitor_lite.json · ohne Wächter · http://127.0.0.1:8766/` oder COMPLETE · Port 8765 · Wächter aktiv), der Titel des Konsolen- und des Terminalfensters, das Tag `[LITE]` / `[COMPLETE]` in den Statuszeilen, in `--doctor` und in den Terminalansichten sowie derselbe Titel in den Startern.
- Neue Anleitungen in acht Sprachen: **Der Wächter und seine Prüfungen A1-A13** (was er ist, wie er startet, welche Dateien er schreibt, wie man ihn liest, die genaue Regel, die Einstellung und die Aktion jeder Prüfung sowie die fünfundzwanzig Prüfungen von A10; ein Test hält Anleitung und Code in Übereinstimmung), **Kontingente und Pläne** und **Deine ersten fünf Minuten** (`FIRST_STEPS`); die Migrationsanleitung hat einen Block von 1.5.x auf 1.6.x und das README eine Auswahl zwischen den beiden Ausgaben.
- Tests für alles davon (die semantischen Versionen, der Hinweis offline, abgeschaltet und abgeschottet, das sichere Markdown, der Index, das Einmal-Token, die Erkennung, `--doctor`, die Kontingente für öffentliche und private Repositorys, Windows und macOS, ohne Token, Enterprise und ein 403 des Abrechnungsberichts, das Banner und die Starter).

### Geändert

- Die Einstellungsseite beginnt mit dem Tab **Grundlagen**; die Anleitung `SETTINGS` wird damit erzeugt.
- Der Monitor listet die Repositorys des Kontos mit ihrer Art (archiviert, Fork, privat, leer); ein älteres `gh` ohne diese Felder fällt auf die einfache Liste zurück.

### Sicherheit

- Nichts Neues schreibt auf GitHub. Der Update-Hinweis, der Abrechnungsbericht und die Erkennung sind schreibgeschützt und abschaltbar; keiner sendet Daten über dich. Die Panels Hilfe und Info werden von diesem Rechner ausgeliefert, und der Supporttext enthält kein Secret.
- Das Schreiben einer Einstellung, das Bestätigen einer Aktion des KI-Assistenten und das Hinzufügen einer vorgeschlagenen Gruppe brauchen das Einmal-Token der Seite.

## [1.6.2]

### Hinzugefügt

- **Eine Sammelgruppe** `rest` („Alles andere“, Präfix `*`) am Ende des Beispielkatalogs der Ökosysteme, damit eine neue Installation kein Repository auslässt.
- **Eine automatische Gruppe „Nicht zugeordnet“** für die Repositories, die keine Gruppe beansprucht (Einstellung `show_unclassified`, standardmäßig an; eine ausdrückliche Auswahl von Ökosystemen wird respektiert).
- **Eine Warnung, wenn der Filter Repositories verbirgt**: Ein Banner (vollständig und Lite) sagt „dein Ökosystem-Filter verbirgt N der M Repositories des Kontos“ und nennt sie.
- **Die Lite-Ausgabe startet mit dem, was du schon eingerichtet hast**: Beim ersten Start kopiert `actions_monitor_lite.json` aus `actions_monitor.json` (falls vorhanden) das Konto, die zu überwachenden Repositories und Ökosysteme, die Katalogdateien, die Ausschlüsse, die Sprache und die Lesetiefe und sagt das in der Konsole. Ohne eine solche Datei überwacht ihre Vorlage alle Ökosysteme.
- **`tui.py --lite`** (oder `MONITOR_MODE=lite`) liest die Lite-Ausgabe auf Port 8766.
- **`redrule.py`**, die eine kleine Regel für „rot auf main“, genutzt vom Wächter und von der Lite-Ausgabe (die die Zahl als ungefähr kennzeichnet, weil sie den Standard-Branch rät).
- **`ghamon_etag_invalid_total`**, die Zahl beschädigter Cache-Einträge, in `/metrics`.
- Tests: Gleichheit der Kopfzeilendaten zwischen vollständiger und Lite-Ausgabe, die Sammelgruppe, die Zahl verborgener Repositories, der Lite-Start, die Heiß-Markierung durch den Webhook, der beschädigte Cache-Eintrag und dass das Importieren des Monitors oder des Wächters nie Rich lädt.
- Anleitungen `LITE` und `SETTINGS` (acht Sprachen) aktualisiert.

### Geändert

- **Beide Ausgaben zeigen dieselben Kopfzeilenzahlen**: Läufe, Fehler, Erfolge, Rechenminuten, laufende und wartende werden einmal vom Server gezählt, über dieselben 24 Stunden und mit jedem Lauf nur einmal; die Lite-Ausgabe liest so tief wie die vollständige. Die Lite-Ausgabe blendet die Kachel „unsigniert“ aus.
- **Ein Webhook-Ereignis markiert das Repository als heiß**, sodass der nächste Zyklus es erneut liest, was auch immer das Ereignis sagte.
- Die Kachel für das GitHub-Kontingent wird vom ersten Moment an gezeichnet, während die Repositories noch laden.

### Behoben

- Eine neue Installation mit dem Beispielkatalog sah fast kein Repository; die Lite-Ausgabe erkannte ein Repository von 129, weil ihre Vorlage nach Ökosystem filterte.
- **Ein beschädigter Cache-Eintrag ist nur ein Fehlgriff**: Er wird verworfen und der Endpunkt vollständig neu gelesen.
- „Rot auf main“ und die Rechenminuten wichen zwischen den beiden Ausgaben ab.

### Sicherheit

- Die Lite-Ausgabe erbt von der vollständigen nie den Wächter, die KI, den Webhook, die Ausgaben oder die Benachrichtigungen und kein Geheimnis; sie schreibt weder `ci_red.json` noch eine Signierwarteschlange.

## [1.6.1]

### Hinzugefügt

- **Die Lite-Ausgabe**, ein zweites, einfacheres Produkt im selben Paket: `MONITOR_LITE_GITHUB_ACTIONS.bat` / `.sh` / `.command` oder `--lite` / `MONITOR_MODE=lite`. Was läuft und was fehlschlug, Fehler und Erfolge der 24 Stunden, rot auf main, der Verlauf und die einfachen Diagramme; eine kurze Einstellungsseite (Konto, Repositories und Ökosysteme, Aktualisierung, Sprache, Design); eine eigene Datei `actions_monitor_lite.json`, eigene Zustandsdateien mit dem Suffix `_lite` und Port 8766, sodass beide nebeneinander laufen können.
- **Befehl `act` im Repository-Panel**: Für jeden Workflow des Repositorys steht `act -W .github/workflows/DATEI -j JOB` zum Kopieren bereit. Der Monitor führt ihn nie aus (das Ausführen gibt es nur als bestätigte Aktion des KI-Assistenten).
- **Ein Container-Beispiel** (`deploy/Dockerfile`), das die CI baut.
- Anleitung `LITE` in acht Sprachen, eine Tabelle Lite gegen Vollständig in jeder README und neue Bilder beider Ausgaben in hell und dunkel.
- Der Fahrplan nennt, was nicht mehr hineinpasste: lokaler Spiegel der Artefakte, FinOps der Minuten, Status eigener Runner und ein OTLP-Export, sowie die Anmerkungen zur Terminal-Ansicht (warum sie Rich nutzt).

### Sicherheit

- Die Lite-Ausgabe hat keinen Wächter: Er wird nicht importiert und seine Endpunkte antworten mit 404.

## [1.6.0]

### Hinzugefügt

- **Bedingte Lesezugriffe (ETag)**: Jedes Lesen der Laufübersichten sendet `If-None-Match`; eine Antwort `304 Not Modified` kostet kein Kontingent. Die Kopfzeile und `ghamon_etag_saved_total` zählen die gesparten Lesezugriffe; `cache.etag.*` im Reiter Einstellungen.
- **Robustheit bei Netzunterbrechungen**: Wenn alle Lesezugriffe eines Zyklus an einem Verbindungsproblem scheitern, behält die Seite das letzte Bild mit einem Offline-Banner und macht von selbst weiter; Ereignisse `offline` und `online` (sie lassen sich melden) und `ghamon_offline`.
- **Analyse** (Abschnitt A12 des Reiters Wächter, `/api/analytics`, `/metrics`, die JSON-Quelle für Grafana): p50 / p95 der Dauer jedes Workflows, der Wartezeit seiner Jobs und jedes Schritts; Workflows, die langsamer als gewöhnlich wurden; **wackelige** Workflows (fehlgeschlagen, dann mit demselben Commit bestanden oder einen weiteren Versuch gebraucht), nur ein Etikett, das nie ändert, was als rot zählt.
- **Eingehender Webhook in Echtzeit**: Ein signiertes `workflow_run`-Ereignis aktualisiert die Laufliste seines Repositorys, ohne GitHub zu lesen; `workflow_job`-Ereignisse bringen Warte- und Schrittzeiten; es werden nur kurze, geprüfte Felder behalten (`/api/live-events`).
- **Workflow-Linter**: `lint_workflows.py` (nicht per SHA festgelegte Actions, fehlende oder weite Berechtigungen, Geheimnisse im Klartext, Injection, `pull_request_target` mit dem Code der PR), Regeln einzeln schaltbar mit eigener Schwere, eine Zeile im Tagesbericht und der Abschnitt A13. Ein Kommentar `# monitor-lint: ignore REGEL Grund` oder die Einstellung `lint.ignore` unterdrückt einen Fund.
- **Benachrichtigungen** (standardmäßig aus): Telegram, Discord, Slack, Matrix, MQTT und eine lokale HTTP-Adresse, ein Limit pro Stunde, ein Testknopf und ein dokumentierter Adapter-Vertrag (`monitor/docs/schemas/notification_event.schema.json`).
- **KI-Assistent**: neue Anbieter `anthropic` (Messages-API, das Modell wählst du) und `copilot` (`gh copilot` mit deiner eigenen Anmeldung, nur Text, keine Werkzeuge); neue Aufgaben (Tagesbericht, Versionshinweise, eine Frage zu einem Repository); Einstellungen für die Ereignisarten, die Repositories, die Sprache und die Grenzen, ein Testknopf und die Nutzung des Tages. Eine geschlossene Liste von Aktionen (`gh run rerun`, `gh issue close`, `act`), standardmäßig nur VORGESCHLAGEN.
- **Die Zahlen der Kopfzeile sind Kacheln** mit Symbol, großer Zahl und kleinem Etikett, nach Zustand gefärbt, mit Tooltip, einem Klick, der zum Reiter führt, zählenden Zahlen und einem Skelett, das sofort die zuletzt bekannten Werte zeigt; auch die zweite Zeile (Repositories, heiß, Modus, gesparte Lesezugriffe, GitHub-Kontingent mit Balken und Live-Countdown, Verbindung, letzte Aktualisierung und Ladefortschritt) besteht aus Kacheln.
- **Terminal-Ansicht**: `tui.py` zeichnet ein Live-Raster in der Konsole (nur lesend, optional, braucht das Paket `rich`; der Monitor und seine Tests brauchen kein Paket).
- **Für Server und größere Konten**: `GET /api/health`, `GH_HOST` für GitHub Enterprise Server (jeder Link der Seite folgt ihm), `discover_limit`, Mindestberechtigungen je Funktion und eine Anleitung, ihn als Dienst (systemd, launchd, eine geplante Aufgabe, ein Container) und hinter einem Reverse-Proxy zu betreiben.
- Veröffentlichte JSON-Schemas von `ci_red.json`, des öffentlichen Exports und des Benachrichtigungsereignisses (`monitor/docs/schemas`) sowie ein öffentlicher Fahrplan (`docs/ROADMAP.md`).
- Neue Anleitungen in acht Sprachen: Benachrichtigungen, der KI-Assistent, Analyse, Konsolenwerkzeuge und Betrieb; die Webhook-Anleitung deckt die Echtzeit-Ereignisse ab. Alle Bilder wurden neu erstellt (hell und dunkel, Konsolenwerkzeuge eingeschlossen) mit `tools/make_screenshots.py` und erfundenen Daten.

### Geändert

- **Einstellungen**: neue Unterreiter für Lesezugriffe und Cache, Benachrichtigungen, Analyse, den Linter und die Terminal-Ansicht; die Unterreiter für KI und Webhook haben alle ihre Optionen.

### Behoben

- **Der Linter schlägt bei Platzhaltern keinen Fehlalarm mehr**: Ein Wert, der wie ein Geheimnis aussieht, wird eingestuft (ein bekanntes Token-Format oder eine lange Zeichenfolge mit hoher Entropie ist ernst, ein lesbarer Platzhalter wie `placeholder` oder `changeme` nur eine Information, alles andere eine Warnung; Verweise und leere Werte sind kein Fund), und sein Wert wird nie ausgegeben oder gespeichert.
- **Ein Browser, der seinen Tab beim Laden der Seite schließt oder neu lädt, erzeugt keinen Traceback mehr** (`ConnectionAbortedError`, `ConnectionResetError`, `BrokenPipeError`): Sie werden in `ghamon_client_disconnects_total` gezählt; ein echter Fehler wird weiterhin gezeigt.

### Sicherheit

- Der eingehende Webhook bleibt standardmäßig aus, auf `127.0.0.1`, mit verpflichtendem HMAC.
- Geheimnisse der Benachrichtigungen liegen nur in Umgebungsvariablen; Hosts sind fest; Benachrichtigungen schreiben nie nach GitHub.
- KI-Aktionen: Eine auszuführen braucht einen eigenen Schalter und jedes Mal eine Bestätigung des vollständigen Befehls, nur auf Zielen, die der Monitor ohnehin überwacht, mit einem Limit pro Stunde, einem lokalen Protokoll und einer Sperre nach zwei Fehlschlägen in Folge.

## [1.5.2]

### Hinzugefügt

- **Der Reiter Einstellungen ist in Unterreiter gegliedert**, vom Gewöhnlichen zum Fortgeschrittenen geordnet (Dieser Browser, Allgemein, Aktualisierung und Grenzen, Wächter, Oberflächenprüfungen A10, Bereitschaft A11, Ordner und Dateien, Ausgaben, Externe KI, Eingehender Webhook). In einem Unterreiter stehen die Einstellungen in Blöcken mit Titel, deren erstes Feld der Hauptschalter ist (der Rest des Blocks wird gedimmt, solange er aus ist). Jedes Feld zeigt Einheit und Bereich, ein Abzeichen (braucht Neustart / gilt sofort), ein Abzeichen für die Sicherheitsoptionen, die im konservativen Zustand starten, und eine Hilfezeile. Ein Suchfeld filtert alle Unterreiter, jeder Unterreiter zählt seine ungespeicherten Änderungen, Speichern und Verwerfen bleiben sichtbar, die Pfeiltasten, Pos1 und Ende bewegen zwischen den Reitern, und der Browser merkt sich den zuletzt benutzten Unterreiter.
- **Jede Einstellung der Konfigurationsdatei steht jetzt auf der Seite**: die A10-Prüfungen (ein Schalter je Prüfung und ihre Grenzen), die Gewichte der Ökosystem-Gesundheitsbewertung, die Quellen der festgelegten Versionen, die Obergrenzen der Actions-Minuten, die erforderlichen Dateien, die Muster der Prüfdateien, die Heißzeit des Wächters, die Regel für unbekannte Stichproben von A2, die Kandidatenpräfixe, die Liste der Repositories und der Schalter des eingehenden Webhooks.
- **Signierwarteschlange nach Vertrauen**: Jede Zeile sagt `verified`, `unknown` oder `failed`; der Reiter Wächter hat einen Signaturfilter mit der Zahl jeder Art; `read_report.py --sign-trust` filtert die Konsolenliste und den Export, und die exportierten Zeilen tragen `trust`.
- **Bereitschaftschips in der Kopfzeile**: ein farbiger Chip je Ökosystem mit seiner Gesundheitsbewertung.
- **Ein minimales Grafana-Board** (`red_by_ecosystem.json`) und ein Test, der jede Metrik beider Boards gegen das prüft, was `/metrics` liefert.
- Neue Anleitung `WEBHOOK` (Modus nur aktualisieren) und ein kommentiertes Beispiel der Pin-Quellen, in acht Sprachen.
- `tools/make_settings_doc.py` schreibt die Einstellungstabelle der Anleitungen aus dem Schema und den Texten der Seite, und die CI prüft sie.

### Geändert

- **Der Tagesbericht fasst die Vorschläge zum Schließen von Issues zusammen** in einer Zeile je Repository (der Monitor schließt weiterhin nichts).
- **Der Vertrag des Profil-Dashboards** ist dokumentiert und durch einen Test geprüft (`/api/outputs/dashboard.json` ist genau das Dokument von `ci_red.json`; der öffentliche Export trägt nie die Signierseite).

### Sicherheit

- Das gemeinsame Geheimnis des Webhooks wird nie auf der Seite gezeigt: Sie sagt nur, ob es definiert ist.

## [1.5.1]

### Hinzugefügt

- **Die Einstellungsseite kann die externe KI des Wächters festlegen** (Gruppe „Externe KI für den Wächter“): `ai.provider` (`none` / `ollama` / `openai-compatible`), `ai.model`, `ai.ollama_url` (nur dieser Rechner), `ai.base_url` (nur https), `ai.api_key_env` und `ai.daily_limit`. Standardmäßig aus; ein externer Dienst erhält Daten deiner Repositories.
- **`migrate_state.py`**: bringt die vor 1.5.0 geschriebenen Dateien auf die neuen Namen (Ereignisse, Berichtsverlauf, Release-Kandidaten, Stapelprotokolle, die Einstellung `report_history_days`). Standardmäßig ein Probelauf; `--apply` kopiert und behält die alten Dateien, `--move` benennt sie um; nichts Vorhandenes wird überschrieben. Einseitige Anleitung in `docs/MIGRATING.md`, in acht Sprachen.
- **`--init-catalog`** erstellt bearbeitbare `ecosystems.json`, `targets.json` und `profiles.json` aus den Beispielen.
- Ein Test stellt sicher, dass kein Dokument den Leser zu einem Befehl schickt, der in 1.5.0 umbenannt wurde (nur die Tabellen alter und neuer Namen und die Migrationsanleitungen dürfen sie nennen).
- Die Version in jeder README.

### Geändert

- **Erster Start ohne eigene Katalogdateien**: Die Konsole sagt, dass die Beispieldateien verwendet werden.
- Python 3.11 oder neuer ist das dokumentierte Minimum (getestet mit 3.11 und 3.13 unter Windows, Linux und macOS).

### Sicherheit

- Es lässt sich nur der NAME der Umgebungsvariablen festlegen, die den KI-Schlüssel enthält: Der Schlüssel selbst wird nie angezeigt oder gespeichert.

## [1.5.0]

**Hinweis zur Aktualisierung (zuerst lesen).** Mehrere Dateien und Einstellungen haben jetzt englische Namen. Nichts geht verloren: Die alten Namen werden weiterhin GELESEN, wo eine von einer früheren Version geschriebene Datei existieren kann, und die neuen Namen sind die einzigen, die geschrieben werden.

| Vor 1.5.0 | Ab 1.5.0 |
|---|---|
| `leer_parte.py` | `read_report.py` |
| `eventos.py` | `events.py` |
| `parte_history.py` | `report_history.py` |
| `LOTE_GITHUB_ACTIONS.bat` / `.sh` / `.command` | `BATCH_GITHUB_ACTIONS.bat` / `.sh` / `.command` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` (kopiere oder benenne sie um, um den Ereignisverlauf zu behalten) |
| `PARTE_CENTINELA_DIA_<day>.txt/.json` (Berichtsverlauf) | `SENTINEL_REPORT_DAY_<day>.txt/.json` (die alten werden weiterhin gelesen) |
| `PARTE_CENTINELA_<time>.txt` (gespeicherter Bericht) | `SENTINEL_REPORT_<time>.txt` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_<time>.json` | `<signed_dir>/batches/batch_<time>.json` (die alten Protokolle werden weiterhin gelesen) |
| `parte_history_days` (Einstellung) | `report_history_days` (der alte Name wird weiterhin gelesen) |
| `monitor_y_centinela.zip` und Ordner | `github_actions_monitor.zip` und Ordner; `LEEME_CORREO.txt` heißt `README_MAIL.txt` |
| A8 suchte `RECONCILIACION_TOTAL_AUDITORIAS_*.txt`, `MAPA_DE_RONDAS_*` | die Namen stehen in `sentinel.audit_files` (neutrale Standardwerte `RECONCILIATION_TOTAL_*.txt`, `ROUNDS_MAP_2*.txt`, `ROUNDS_MAP_EXTRA_*.txt`); trage dort deine eigenen ein |
| `ci_red.json`, sein Schema und die Dateien von `--export-status` | unverändert (sie sind ein Vertrag) |

- **Standardmäßig Englisch.** Die Systemsprache entscheidet nicht mehr: Die Werkzeuge starten auf Englisch, bis du im Reiter Einstellungen, mit `language` in `actions_monitor.json`, `MONITOR_LANG` oder `--lang` eine andere wählst.
- **Ein sauberes, neutrales Paket.** `ecosystems.json`, `targets.json` und `profiles.json` gehören nicht mehr zum Paket: Nur die Dateien `*.example.json` reisen mit, und eine fehlende Standarddatei fällt auf ihr Beispiel zurück. Deine eigenen Dateien liegen, wo du willst, und werden mit `ecosystems_file`, `targets_file` und dem neuen `profiles_file` benannt; der Ordner deiner lokalen Signierwerkzeuge ist das neue `tools_dir`. Die Tests nutzen eigene Testdaten (`tests/fixtures`).
- **Reiter Einstellungen.** Ein neuer Reiter ändert die Werte von `actions_monitor.json` von der Seite aus: eine Whitelist von Schlüsseln mit Typ und Bereich, eine als Ganzes abgelehnte Anfrage, wenn ein Wert ungültig ist, eine Kopie der vorherigen Datei in `config_backups/` vor jedem Speichern (die letzten zehn bleiben), ein atomares Schreiben, nur auf 127.0.0.1 mit denselben Host- und Origin-Prüfungen wie jeder andere Endpunkt, nur JSON. Tokens, Geheimnisse, Signierschlüssel und der Befehl des Wächters stehen nicht in der Liste: Sie werden nie gezeigt und nie geschrieben, und jeder andere Schlüssel der Datei bleibt, wie er war. Jede Einstellung sagt, ob sie einen Neustart braucht. Die Sprachauswahl, das Design und die dichte Ansicht sind dorthin umgezogen.
- **Knöpfe und Symbole.** Knöpfe haben Relief, leuchten beim Überfahren auf und sinken beim Drücken ein; die Symbolknöpfe sind Inline-SVG mit zugänglichem Namen und Tooltip in den 8 Sprachen. Farben, Schrift, Karten, Balken und der Ring folgen dem Status-Dashboard des Profil-Repositorys.
- **Leben in den Diagrammen.** Balken wachsen ein, was rot ist oder läuft, pulsiert dezent, die Zahlen der Kopfzeile zählen hoch, das Überfahren eines Balkens hebt ihn hervor und gibt seinen Text als Tooltip, Breiten ändern sich sanft; all das stoppt bei `prefers-reduced-motion`.
- **Ausgaben für andere Werkzeuge (standardmäßig aus, nur 127.0.0.1, kein neues Token).** `/metrics` im Prometheus-Format (rote Workflows je Ökosystem und Repository, rote Serien und Stunden, auf Signatur wartende Builds, A10 pausiert, verbleibendes Kontingent, unvollständiger Schnappschuss ...), `/api/outputs/grafana.json` für die Grafana-JSON-/Infinity-Quelle und `/api/outputs/dashboard.json` (das Dokument `ci_red.json`) für das Status-Dashboard. Ein importierbares Grafana-Dashboard liegt in `docs/grafana/`, die Einzelheiten in `docs/OUTPUTS.md`.
- **Bericht:** eine Zeile (Code `tag_vs_manifest`), wenn ein Release-Tag der Version des Manifests voraus ist; die Zahl der unsignierten ist nach der längsten Wartezeit geordnet und nennt sie; das Repository-Panel schlägt den Befehl `gh issue close` vor (nie ausgeführt) für ein Fehler-Issue, dessen Workflow wieder grün ist; das Stapelprofil `hil` ist in `profiles.example.json` dokumentiert; Tests für `finalize` und für `monitor_link`.
- **Doku:** `docs/SETTINGS.md`, `docs/OUTPUTS.md`, README und QUICKSTART in den 8 Sprachen aktualisiert, Bilder mit erfundenen Repositories erstellt.

## [1.4.5]

- **Der Bericht sagt, wann der Schnappschuss unvollständig ist:** eine Zeile mit dem stabilen Code `incomplete` (lädt noch, kein lokaler Arbeitsbereich, Fehler beim Lesen) direkt nach der Schlagzeile, damit niemand auf eine halb gelesene Liste roter Repositories oder der Signierwarteschlange reagiert.
- **Signierübersicht:** eine Zeile, wie viele Releases auf ihre Signatur warten (verifiziert / nicht geprüft / Prüfung fehlgeschlagen) und wie viele Builds absichtlich nur gebaut werden, damit „absichtlich nicht signiert“ nicht mit „Signatur fehlt“ verwechselt wird (Code `sign_summary`).
- **A10 wegen des Kontingents pausiert, steht im Bericht** (Code `a10_paused`) mit dem verbleibenden und dem benötigten Kontingent und den drei Reglern, die es steuern.
- Texte in den 8 Sprachen; Tests für die drei Zeilen.

## [1.4.4]

- **Autor und Lizenz sind immer sichtbar:** Das Web-Panel hat eine Fußzeile mit Autor und Lizenz, `read_report.py --version` und das neue `gha_dispatch_all.py --version` geben sie unter der Version aus, und der Monitor gibt beim Start dieselbe Zeile aus. Der Text liegt in den 8 Sprachen vor (`ui.about`); Autor und Lizenz stammen aus `tool_version.py`.
- **Die Brücke zum Dashboard ist aufgeschrieben:** `docs/CI_RED_BRIDGE.md` sagt, was `ci_red.json` enthält (Schema 2, `complete`), wie man sie exportiert und was ein Leser prüfen muss; der Monitor pusht oder committet weiterhin nie.
- Tests für die Autorenzeile in den 8 Sprachen, die Fußzeile, beide `--version`-Schalter und die Startzeile.

## [1.4.3]

- **Ein Workflow, der nur bei Pull Requests läuft, macht A2 nicht mehr unschlüssig:** `pull_request` und `pull_request_target` gehören jetzt zu den Ereignissen, deren Läufe nie auf dem Standard-Branch liegen (wie `workflow_dispatch`, `release` und `workflow_call`); von einem Workflow wie einer Vertrags-Integrationsprüfung, die nur bei Pull Requests läuft, wird also kein letzter Lauf auf main verlangt. Ein Workflow, der auch `push` oder `schedule` hat, zählt weiterhin. Tests für beide Fälle.

## [1.4.2]

- **A2 zählt einen laufenden oder abgebrochenen Lauf nicht mehr als gesehen:** Beim Auflösen eines verborgenen Workflows fragt der Wächter jetzt nach den letzten abgeschlossenen Läufen dieses Workflows auf dem Standard-Branch (`gh run list -w <Datei> --branch <Standard> --status completed -L 10`, nur lesend) und nimmt den ersten mit einem echten Ergebnis. Ein abgebrochener oder übersprungener Lauf (und alles ohne Ergebnis) wird ignoriert und kann so kein früheres Rot mehr verdecken; ein Workflow ohne abgeschlossenen Lauf mit Ergebnis auf dem Branch bleibt für sich unschlüssig. Dieselbe Kontingent-Schranke, dieselbe Aufruf-Grenze und derselbe Cache wie zuvor.

## [1.4.1]

- **A2 löst einen verborgenen Workflow auf, statt für das ganze Repository aufzugeben:** Hat ein Repository eine vollständige Laufstichprobe und fehlt darin ein Workflow seines Klons (einer, der auf dem Standard-Branch laufen kann), fragt der Wächter GitHub nach dem letzten Lauf GENAU dieses Workflows auf dem Standard-Branch (`gh run list -w <Datei> --branch <Standard> -L 1`, nur lesend). Eine rote Antwort zählt in A2 als rot; eine grüne nimmt den Workflow aus der Liste der Unschlüssigen; ein Workflow ohne Lauf auf dem Branch bleibt für sich unschlüssig, und das Panel nennt ihn (`repo/datei.yml (kein Lauf auf dem Standard-Branch)`) statt nur das Repository. Ohne Kontingent (dieselbe Schranke wie A10: `min_rate_remaining` x `surface.min_rate_factor`, plus das Stundenbudget) bleibt der Workflow unschlüssig, und das Panel sagt warum. Neue Optionen `sentinel.a2_resolve_max_calls_per_tick` (4; 0 = nie fragen) und `sentinel.a2_resolve_ttl_seconds` (3600, wie lange eine Antwort behalten wird; sie wird auch in der Cache-Datei gespeichert). Der Schnappschuss trägt `a2.inconclusive_workflows` (Etiketten) und `a2.inconclusive_details`; `a2.inconclusive` bleibt die Liste der Repositories. 5 neue Texte in den 8 Sprachen und ein umformuliertes `ui.a2_inconclusive`.

## [1.4.0]

- **Neue Ebene A11 „Bereitschaft“ (nur lesend, nur echte Daten):** ein Panel des Reiters Wächter, eine Ampel in dessen Kopf und zwei Zeilen des Berichts. Sie wird mit `sentinel.readiness.enabled` geschaltet und in `readiness.py` beschrieben.
  - **Release-Bereitschaft:** eine Zeile je Repository mit mindestens `candidate_min_entries` Einträgen in `[Unreleased]` (externe Ökosysteme ausgenommen): die CI des Standard-Branches (die einzige Regel von A2) mit dem Commit, auf dem sie lief, ob die vom Klon deklarierte Version (`*.project.json`, sonst `pyproject.toml`, sonst die erste CHANGELOG-Überschrift) schon über dem letzten Release liegt, ob es einen Build nach diesem Release gibt, ob er signiert ist (die Zustände von A5) und der nächste Schritt (`rote CI beheben`, `auf Laufdaten warten`, `Version erhöhen`, `in Actions bauen`, `signieren`, `veröffentlichen`, `schneiden und veröffentlichen`). Eine grüne CI über einer vollen Laufstichprobe, die einen älteren Workflow verbergen kann, sagt das.
  - **Gesundheit des Ökosystems:** je Ökosystem 100 minus gewichtete Zahlen von roter CI, hängenden Builds, Geheimnissen, schweren Warnungen, anderen Warnungen, Dependabot-PRs älter als `stale_pr_days`, auf Signatur wartenden Builds und Repositories mit Hygieneproblemen (`sentinel.readiness.health.weights`); die Teile, die die Bewertung senken, werden aufgelistet. Keine Bewertung (`?`), wenn weniger als `min_coverage` (0,5) der Repositories des Ökosystems Laufdaten und Warnungen haben. Der Bericht warnt, wenn eine Bewertung unter `warn_below` (70) liegt.
  - **Abhängigkeits-Pins:** Repositories, die eine ältere Version festlegen als das Repository, das den Vertrag oder die Bibliothek liefert. Wo die Pins liegen, ist Datenfrage (`sentinel.readiness.pins.sources`): eine JSON-Tabelle der Pins im Anbieter (`pin_table`) oder Lock-Dateien in den Verbrauchern (`lock_files`, die älteste gefundene zählt). Einfaches Lesen von Dateien der lokalen Klone, zwischengespeichert `pins.refresh_seconds`; ein Ökosystem ohne konfigurierte Quelle wird als ohne aufgeführt, und nichts wird geraten. Das mitgelieferte Beispiel hat keine Quelle.
  - 60 neue Texte in den 8 Sprachen; `tests/test_readiness.py` (Regeln, Gewichte, Abdeckung, Pins auf einem temporären Baum, die Seite und die 8 Kataloge).
- **`docs/CI_RED_SCHEMA.md`:** sagt ausdrücklich, dass der PC weder `ci_red.json` noch `pending_sign` in ein Repository oder Dashboard veröffentlicht (die Signierseite ist per Entscheidung lokal); ein öffentlicher Verbraucher berechnet die Regel aus den öffentlichen Läufen neu oder nutzt `read_report.py --export-status`.
- **Kontingent-Abstimmung anhand des Protokolls (`actions_monitor_log.txt`, 3 Tage, 889 Messwerte):** Das gemeinsame Kontingent lag seit dem 5. November in 11 % der Messwerte unter der Untergrenze (`min_rate_remaining` 1500) und in 45 % unter 3000; der Stundenverbrauch lag in den meisten Stunden bei 3000-5000 Aufrufen und erreichte in manchen das Limit. In der `actions_monitor.json` des Maintainers: `refresh_seconds` 120 -> 180 (der echte Zyklus hatte einen Median von 139 s) und `sentinel.surface.min_rate_factor` 2,0 -> 1,5 (die kalten Aufrufe von A10 sind etwa 260 am Tag, können also über 2250 laufen; mit 3000 warteten sie fast die Hälfte der Zeit). `max_repos_per_tick` (6) und der tägliche kalte Zyklus bleiben: Sie kosten weniger als 1 % des Kontingents. Das mitgelieferte Beispiel behält seine neutralen Standardwerte.

## [1.3.3]

- **A2 ignoriert Workflows, die nie auf dem Standard-Branch laufen:** Beim Entscheiden, ob eine volle Laufstichprobe einen Workflow verbirgt, werden Dateien des Klons, deren `on:` weder `push`, `pull_request` noch `schedule` für den Branch hat (nur `workflow_dispatch`, `release`, ein reines Tag-`push` ohne `branches` oder `workflow_call`), nicht mehr in der Stichprobe erwartet. `on:` wird nur mit der Standardbibliothek gelesen (Zeichenfolge, Liste, Map und der YAML-Schlüssel `true`); lässt es sich nicht lesen, zählt der Workflow wie zuvor. Der Workflow-Scan trägt das neue Feld `main_triggered` (`true`/`false`/`null`).

## [1.3.2]

- **A2 zeigt `unknown` statt grün, wenn seine Stichprobe voll und unschlüssig ist:** Ein Repository, dessen Laufliste so lang ist wie die angeforderte Stichprobe (`runs_per_repo` / `cold_runs_per_repo` des Monitors, die die Prüfung bisher nicht sah) und dessen Klon eine Workflow-Datei ohne Lauf in dieser Stichprobe hat (oder keinen Klon hat), wird als unschlüssig aufgeführt, und A2 ist `unknown`, außer etwas ist rot. Neue Option `sentinel.a2_full_sample_unknown` (Standard `true`; `false` = nur informativ wie zuvor). Die Seite listet die Repositories.
- **`profiles.example.json`:** eine neutrale Vorlage für Stapelprofile, passend zu `targets.example.json` und `ecosystems.example.json`. Ein Test (und die Release-Schranke) prüft sie gegen diese Kataloge, nicht gegen die des Maintainers, und stellt sicher, dass jedes Profil mindestens ein Ziel auswählt.
- **Prüfung der sauberen Installation in `make_release`:** Bevor etwas im Ausgabeordner liegen bleibt, wird das Zip in ein neues, leeres temporäres Verzeichnis entpackt, und von dort mit `python -I` muss jedes Mitglied vorhanden sein, jedes Modul kompilieren, `read_report.py --version` laufen und die ganze Suite bestehen; jede Lücke lässt das Release scheitern.
- **Formulierung:** README und QUICKSTART in den 8 Sprachen sagen jetzt, dass das Paket von sich aus nichts nach GitHub schreibt und dass nur `dispatch --go`, `dispatch --real` und `finalize --execute` (die du ausführst) es tun.
- **A10-Kontingent:** Der Anteil des Aufrufbudgets des Wächters pro Zyklus, den A10 nutzen darf, ist jetzt `sentinel.surface.budget_share` (Standard `0.5`, wie zuvor, aber konfigurierbar); die Seite zeigt „A10 wegen Kontingent pausiert“ mit dem verbleibenden und dem benötigten Kontingent (`min_rate_remaining` x `min_rate_factor`), solange die kalten Aufrufe warten.

## [1.3.1]

- **Ein auf einem anderen Commit gebauter Lauf wird nie zum Signieren angeboten:** Konnte `dispatch` nur einen jüngeren Lauf eines anderen Commits finden (`sha_matched` falsch), listet `finalize` ihn jetzt als nicht bereit mit dem Grund und gibt keinen Signierbefehl aus; ein alter Stapel ohne das Feld verhält sich wie zuvor. Tests mit zwei gleichzeitigen Läufen verschiedener Commits.
- **`/api/data` läuft durch dieselbe Host-/Origin-Wache wie die anderen Routen** des lokalen Servers (DNS-Rebinding).

## [1.3.0]

Zum Teilen gemacht: acht Sprachen, Urheberschaft und Lizenz in jeder Datei, keine privaten Daten und nichts an ein GitHub-Konto gebunden.

- **8 Sprachen** (en, es, de, fr, it, ja, zh, pt = europäisches Portugiesisch) für die Seite, die Befehlszeilenwerkzeuge, die Starter, die Ereignisse, die Berichte und die Fehlermeldungen. `i18n.py` + `locales/<Sprache>.json` (ein flacher Katalog je Sprache, nur Standardbibliothek, `t("Schlüssel", name=wert)` mit Rückfall auf Englisch). Die Sprache ist `language` in `actions_monitor.json` (Standard: die Systemsprache, Englisch, wenn nicht unterstützt), eine Auswahl in der Kopfzeile der Seite (der Browser merkt sie sich), `MONITOR_LANG` / `JUANENRAC_LANG` oder `--lang CODE` in jedem Werkzeug (sie schlägt alles andere). Technische Namen, Befehle, Pfade und die Marker, die Skripte lesen (`SKIP`, `DISPATCHED`, `READY`, `FAILED`, `Summary:`, `BUILD ONLY`, `WOULD DISPATCH` ...), werden nie übersetzt. Ereignisse in `events_monitor.jsonl` tragen jetzt neben dem Text einen stabilen `code` (und `args`), sodass niemand eine Sprache auswerten muss.
- Ein Test prüft, dass die 8 Kataloge genau dieselben Schlüssel haben, keiner leer ist, dieselben `{Platzhalter}` enthalten, dass jeder von Code und Seite verwendete Schlüssel existiert und dass kein sichtbarer Text im Code `t()` umgeht.
- README und QUICKSTART in den 8 Sprachen (`README_<Sprache>.txt`, `QUICKSTART_<Sprache>.txt`); `README.txt` ist jetzt eine kurze Sprachauswahl mit dem Schnellstart.
- **Urheberschaft und Lizenz**: Jede Quelldatei trägt „Copyright (C) 2026 JuanenRac (Electro Hobby 3D)“ und „GPL-3.0-or-later - see LICENSE“; JSON-Datendateien tragen `_author` / `_license`; `LICENSE` (GPL-3.0-Text), `NOTICE` und `AUTHORS` reisen im Zip mit. `make_release.py` weigert sich zu bauen, wenn einer Datei sie fehlen, wenn private Daten mitreisen würden, wenn die Locales abweichen oder wenn ein Starter sein Ausführungsbit verliert.
- **Teilbar**: `github_owner` in der Konfiguration (Standard: das Konto von `gh`) ersetzt die Konstante, die über drei Module verstreut war; die Ökosystem-Präfixe und die Signierwerkzeuge sind Daten (`ecosystems.json`, neutral `ecosystems.example.json`; `"*"` = jedes Repository; `"external": true` = nur gemeldet) und ebenso die Ziele (`targets.json` ist der echte Katalog des Maintainers, `targets.example.json` der neutrale; `targets_file` / `ecosystems_file` wählen sie; Schlüssel, die mit `_` beginnen, sind Metadaten). Die Beispielkonfiguration ist neutral. Nichts davon fügt dem heißen Zyklus einen Aufruf hinzu.
- **Der Arbeitsbereich ist optional**: Ohne lokale Klone startet der Monitor in einem reduzierten Modus (nur was die GitHub-API liefert: keine lokale Signierwarteschlange, kein Prüfbericht, kein CHANGELOG-Scan) und sagt das auf der Seite, im Bericht und beim Start, statt anzuhalten. `MONITOR_ROOT` / `MONITOR_AUDIT_DIR` / `MONITOR_SIGNED_DIR` und `signed_dir` kamen neben die alten Namen. Die Fahrplan-Ebene (A9) ist ebenfalls optional.
- Starter: Menüs und Meldungen kommen aus `launcher_msg.py` (deine Sprache); Kommentare auf Englisch; Kopfzeile in jeder Datei.
- Korrektur: `workspace_root()` beendet den Monitor nicht mehr, wenn der Wächter ohne Arbeitsbereich startet.

## [1.2.0]

Was fehlte und was sich sonst auf GitHub tun lässt, alles nur lesend und lokal.

**Teil A - was fehlte**
- Das Schema 2 von `ci_red.json` ist jetzt ein dokumentierter Vertrag: `docs/CI_RED_SCHEMA.md` (Form, die eine Regel für „rot“, was nur für den Besitzer ist). Vom PC wird nichts veröffentlicht. Optionale, ausdrückliche Exporte (nie ein Commit oder Push): `read_report.py --export-status DIR` schreibt NUR die Rot-Liste (`ci_status_public.json/.md`); `read_report.py --export-sign-queue FILE` (.json/.csv) schreibt die globale Signierwarteschlange mit den lokalen Befehlen.
- Attestierung: Die Signierwarteschlange zeigt, ob der Build eine Attestierung hat (Vorhandensein anhand des Digests der signierten Dateien, eine Abfrage je Eintrag, keine Signaturprüfung; Schalter `sentinel.surface.checks.attestation`). Eine fehlende ist eine Zeile im Bericht.
- Mehr geprüfte Formate: HYDRA `hydra-sign` (`DATEI.sig` = Base64-Ed25519 über die Bytes der Datei, der festgelegte Release-Schlüssel, blockweise gelesen) wird endgültig geprüft; URTC `.imgsig` hat sein strenges Format geprüft (152 Hexziffern + LF; fehlerhaft = ungültig) und bleibt „unknown“, wenn es wohlgeformt ist (die signierte Nachricht braucht auch den Build-Header, den der Signierordner nicht trägt); ARMOR-APKs werden im APK von apksigner signiert und bleiben „unknown“.
- `HYDRA-UMC-OS` ist in `targets.json` absichtlich gekennzeichnet (`"build_only": true` + `reason`): `plan` führt es unter BUILD ONLY auf, und es ist keine Waise mehr. Die Signierwerkzeuge wurden nicht angefasst (sein Workflow nimmt andere Eingaben und ein anderes Signaturschema).
- Korrektur: `ci_red.target_path` wies jeden Windows-Pfad mit Backslashes (`C:\...`) zurück; nur Schrägstriche wurden akzeptiert.

**Teil B - die A10-Ebene „Oberfläche von Actions und Releases“** (`surface.py`, neuer Abschnitt des Reiters, ein Schalter und eine Schwelle je Prüfung unter `sentinel.surface`)
- Actions: von Hand deaktivierte Workflows, Zeitpläne ohne Lauf in N Tagen (nur wenn die Laufstichprobe das Fenster abdeckt), nicht per SHA festgelegte `uses:` (wiederverwendbare Workflows gesondert gekennzeichnet), `permissions: write-all`, `pull_request_target` mit Checkout der PR, hängende Concurrency-Warteschlangen, Fehler nur auf einem OS einer Matrix, Kosten und Aufbewahrung von Artefakten, erforderliche Statusprüfungen, die rot sind oder fehlen (GraphQL), `dispatch --profile release|nightly|hil` mit einem Kanarienvogel (nur das erste Ziel, der Rest nur bei Grün) und einer Kontingent-Schranke (`--min-rate`, schließt im Zweifel). Profile liegen in `profiles.json`.
- Releases: erwartete Assets je Zieltyp (Warnung bei unvollständig veröffentlichtem Release), Tag gegen Manifest gegen CHANGELOG, GitHub Packages, vergessene Entwürfe und Vorabversionen, `release_notes.py` (ein ENTWURF von Hinweisen aus den Commits seit dem letzten Tag; er veröffentlicht nichts).
- Sicherheit: kritische/hohe Warnungen nach Alter mit einer Rangliste der Repositories, Abdeckung (ein Stack ohne CodeQL/Dependabot), offene gegenüber gelösten Secret-Scanning-Funden, Dependabot nach Priorität (Runtime-Major zuerst, nur CI zuletzt).
- Issues und PRs: Vorschlag `gh issue close` für Build-Issues, deren CI wieder grün ist (ein Ereignis mit dem Text; nie wird etwas geschlossen), überfällige Meilensteine, alte menschliche PRs, PRs, die Workflows oder CODEOWNERS berühren, die Merge-Queue (genehmigt mit grünen Prüfungen). Veraltete Board-Karten: AUSSTEHEND (braucht Lesezugriffe je Element und eine Schwelle).
- Manifest gegen Beleg (Reife), Paritätsfehler der README in 8 Sprachen, Actions-Minuten je Ökosystem in der Kopfzeile, im Bericht und in A7.
- `finalize --execute` sagt jetzt dem laufenden Monitor (127.0.0.1), nur die signierten Repositories zu aktualisieren und `ci_red.json` sofort neu zu schreiben (`monitor_link.py`).
- Optionaler Empfänger für signierte Webhooks (`webhook.enabled`, standardmäßig aus, nur 127.0.0.1, HMAC mit einem gemeinsamen Geheimnis aus der Konfiguration, nie ein GitHub-Token).
- Kosten: nichts im heißen Zyklus. Kalt, über Ticks verteilt und innerhalb des Stundenbudgets: 2 REST-Aufrufe je Repository und Tag, eine GraphQL-Abfrage je 15 Repositories und Tag, 3 für Packages, dazu die Jobs roter Läufe und die Attestierungsabfragen der Signierwarteschlange, und nur solange das Kontingent über dem Doppelten von `min_rate_remaining` liegt. Der heiße GraphQL-Durchlauf fragt 3 weitere Felder je Knoten ab (Datum der Warnungen, Review-Entscheidung, Prüfstatus): kein zusätzlicher Aufruf.
- Die Schranke vergleicht außerdem `sentinel.surface` der Beispieldatei mit den Standardwerten und validiert `profiles.json`.

## [1.1.1]

- **Plattformübergreifend:** Der Monitor und die Stapelwerkzeuge laufen unter Windows, macOS und Linux. Starter `MONITOR_GITHUB_ACTIONS.sh`/`.command` und `BATCH_GITHUB_ACTIONS.sh`/`.command` (das Zip behält die Ausführungsberechtigung, und make_release weist Windows-Zeilenenden darin zurück).
- Neues `platform_compat.py`: der Befehl, der ein Kindwerkzeug startet (`py -3` unter Windows, der aktuelle Interpreter sonst), der Text der Befehle, die `finalize` zeigt (cmd/PowerShell- oder POSIX-Quoting), UTF-8-Konsole und ein Hinweis, wie man `gh` auf jedem System installiert.
- Neue Tests des plattformübergreifenden Teils (Windows und POSIX von jedem System aus simuliert).

## [1.1.0]

Signaturvertrauen, eine stabile Brücke zum Dashboard, Waisen und Konventionen in den Stapelwerkzeugen und eine nützlichere Seite.

- Signaturvertrauen: `sigverify.py` (Standardbibliothek, nur lesend, kein Netz) prüft den Signierordner `_firmados/<REPO>/release-<Version>/` gegen den ÖFFENTLICHEN Schlüssel, den jedes Ökosystem festlegt (URTC `release_sign.py`, der ARMOR-Helfer `PACKAGE_PUBLIC_KEY`, der HYDRA-Updater `RELEASES_PUBLIC_KEY` oder `sentinel.signature_pubkeys`). Jeder Zustand trägt jetzt `signature_kind` (none | dev | release) und `signature_verified` (true | false | "unknown"); nur eine Release-Signatur, die sich verifizieren lässt (`trusted`), senkt den Alarm „Signatur ausstehend“, außer „veröffentlicht“. Eine Signatur, die sich nicht verifizieren lässt, behält den Alarm und sagt das im Bericht. `sentinel.require_verified_signature` (Standard true; false = die Regel von 1.0.0). Formate, die dieses Modul nicht prüfen kann (.sig2, .hdr2, .imgsig, APK, hydra-sign), sind „unknown“, nie „false“. Die Build-Attestierung braucht weiterhin das Netz und bleibt bei den Signierwerkzeugen.
- Schema 2 von `ci_red.json`: je Repository eine Liste `pending_sign` (Workflow, Stunden, Zustand, signature_kind, signature_verified, last_build_at, url) neben den roten Workflows, dazu `schema`, `pending_sign_repos` und die Schwelle; das Format ist in `ci_red.py` dokumentiert und wird nur erweitert.
- Eine Definition von „letzter Lauf auf main“ (`signstate.completed_runs`), geteilt von der Rot-Prüfung, der Prüfung „grün ohne Release“ und den Zielzuständen.
- `ci_red.target_path` weist D:-Pfade, WSL-/Git-Bash-Formen von D: und Laufwerks-/UNC-Pfade zurück, die das laufende System nicht nutzen kann; die Tests simulieren beide Systeme, und die ganze Suite besteht jetzt unter Linux.
- `gha_dispatch_all.py plan` endet immer mit dem Abschnitt „Signatur-Waisen“ (grüne CI + bekannte `*-build.yml` + kein Ziel); die Abdeckung gilt je Repository UND Workflow.
- Konvention für Ziele (Ökosystem-Präfix -> Standard-Signierwerkzeug, Workflow in der bekannten Liste); `targets.json` enthält nur die Ausnahmen und gewinnt immer. `hygiene --write-candidates` schreibt die vorgeschlagenen Einträge in `targets.candidates.json` (nie von selbst angewendet, nie verpackt).
- Seite: anklickbare Kopfzähler „rot auf main“ und „unsigniert“ (filtern die Repositories; der zweite fokussiert auch die Signierwarteschlange), die Signierwarteschlange mit ihren Befehlen und einem Kopieren-Knopf, Repository-Panel mit gebaut / signiert / veröffentlicht, Signaturart und Verifizierung sowie dem vorgeschlagenen Befehl; ein Abzeichen in der Kopfzeile, wenn ein Minutenbudget 80 % erreicht (rot bei Überschreitung); „gestern gegen heute“ vergleicht auch Budgetwarnungen und die Zeilen des Berichts.

Nicht umgesetzt: das Lesen der Build-Attestierung / SBOM (Netz); `HYDRA-UMC-OS` hat einen Build-Workflow, aber sein Signierwerkzeug unterstützt ihn noch nicht (als Waise aufgeführt).

## [1.0.0]

Erste nummerierte Version. Was das Paket tut:

- Monitor für GitHub Actions der vier Ökosysteme (lokale Webseite, Lauf-Cache, hängende Builds, build-failed-/build-stuck-Issues).
- Wächter-Ebene A (nur lesend, keine KI nötig): A1 hängende Builds, A2 rote CI (ein einziges Kriterium: der letzte abgeschlossene Lauf jedes Workflows auf dem Standard-Branch), A3 CodeQL-/Dependabot-/Geheimnis-Warnungen, A4 Dependabot-Pull-Requests, A5 Releases (Kandidaten, grüne Builds ohne Release, ausstehende Signatur), A6 Hygiene, A7 Verbrauch (Minuten und API-Kontingent), A8 Audits und Runden, A9 Fahrplan-Boards.
- Expliziter Zustand jedes Build-Ziels: built_on_gha -> signed_local (none | dev | release) -> published, mit `last_build_at`, `last_signed_at`, `signature_kind` und den echten Wartestunden; lokale Stapel- und Signierordner-Protokolle senken den Alarm „Signatur ausstehend“, ohne auf GitHub zu warten.
- Signierwarteschlange des Tages (`a5.sign_queue`): das Dringendste zuerst, mit dem genauen finalize-Befehl jedes Ziels.
- Budget der Actions-Minuten je Ökosystem (`sentinel.minutes_budget`, standardmäßig leer): Warnung bei 80 % im Bericht und als Ereignis.
- Ereignisstrom (`events_monitor.jsonl`) und `ci_red.json` (Repository -> rote Workflows + Stunden bis zur Signatur), atomar geschrieben.
- Stapelwerkzeuge: `gha_dispatch_all.py plan|dispatch|status|finalize|hygiene` mit `--only` oder `--ecosystem`, `plan --json`, `finalize --json`, ein Wiederholungsversuch eines fehlgeschlagenen Dispatch am Ende des Stapels, Ziele als Daten in `targets.json`.
- `read_report.py`: der Bericht als Klartext vom laufenden Monitor, ohne API-Kontingent zu verbrauchen.
- `make_release.py`: Qualitätsschranke (Unit-Tests, sauberes Zip, vollständige Beispielkonfiguration, Übereinstimmung von Version und Changelog) und SHA256SUMS.

In dieser Version nicht umgesetzt: das Prüfen der Release-Signaturen gegen den öffentlichen Schlüssel und der Build-Attestierung durch den Wächter (je Ökosystem andere Signaturformate; die Attestierung braucht das Netz; die Signierwerkzeuge prüfen beides vor dem Veröffentlichen).

