<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

# Änderungsprotokoll

Version des Werkzeugs selbst (Monitor + Wächter + Stapelwerkzeuge) mit eigenem Semver. Die Quelle ist das englische CHANGELOG.md; diese Datei enthält dieselben Versionen und Abschnitte.

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

> Diese Version liegt vorerst nur auf Englisch vor; die Übersetzung folgt in einer späteren Version.

### Hinzugefügt

- **A catch-all group** `rest` ("Everything else", prefix `*`) at the end of the example catalogue of ecosystems, so a new installation leaves no repository out.
- **An automatic group "Unclassified"** for the repositories that no group claims (setting `show_unclassified`, on by default; an explicit choice of ecosystems is respected).
- **A warning when the filter hides repositories**: a banner (complete and lite) says "your ecosystem filter hides N of the M repositories of the account" and names them.
- **The lite edition starts with what you already set up**: on its first start `actions_monitor_lite.json` copies from `actions_monitor.json` (when it exists) the account, the repositories and ecosystems to watch, the catalogue files, the exclusions, the language and the reading depth, and says so on the console. Without such a file its template watches all the ecosystems.
- **`tui.py --lite`** (or `MONITOR_MODE=lite`) reads the lite edition on port 8766.
- **`redrule.py`**, the single small rule of "red on main", used by the sentinel and by the lite edition (which marks the figure as approximate because it guesses the default branch).
- **`ghamon_etag_invalid_total`**, the count of damaged cache entries, in `/metrics`.
- Tests: header-data parity between the complete and the lite edition, the catch-all group, the hidden-repository count, the lite start, the webhook hot mark, the damaged cache entry, and that importing the monitor or the sentinel never loads Rich.
- Guides `LITE` and `SETTINGS` (eight languages) updated.

### Geändert

- **Both editions show the same header figures**: runs, failures, successes, compute minutes, running and queued are counted once, by the server, over the same 24 hours with each run counted once; the lite edition reads as deep as the complete one. The lite edition hides the "unsigned" tile.
- **A webhook event marks the repository as hot**, so the next cycle reads it again whatever the event said.
- The GitHub allowance tile is painted from the first moment, while the repositories are still loading.

### Behoben

- A new installation with the example catalogue saw almost no repository; the lite edition detected one repository out of 129 because its template filtered by ecosystem.
- **A damaged cache entry is only a miss**: it is thrown away and the endpoint is read again in full.
- "Red on main" and the compute minutes differed between the two editions.

### Sicherheit

- The lite edition never inherits the sentinel, the AI, the webhook, the outputs or the notifications, nor any secret, from the complete one; it writes neither `ci_red.json` nor a signing queue.

## [1.6.1]

> Diese Version liegt vorerst nur auf Englisch vor; die Übersetzung folgt in einer späteren Version.

### Hinzugefügt

- **The lite edition**, a second and simpler product in the same package: `MONITOR_LITE_GITHUB_ACTIONS.bat` / `.sh` / `.command` or `--lite` / `MONITOR_MODE=lite`. What is running and what failed, failures and successes of 24 hours, red on main, the history and the basic charts; a short Settings page (account, repositories and ecosystems, refresh, language, theme); its own file `actions_monitor_lite.json`, its own state files with the suffix `_lite` and port 8766, so both can run side by side.
- **`act` command in the repository panel**: for each workflow of the repository, `act -W .github/workflows/FILE -j JOB` ready to copy. The monitor never runs it (running it exists only as a confirmed action of the AI assistant).
- **A container example** (`deploy/Dockerfile`) that the CI builds.
- Guide `LITE` in eight languages, a Lite-versus-Complete table in every README and new screenshots of both editions in light and dark.
- The roadmap lists what did not fit: local mirror of artifacts, FinOps of the minutes, self-hosted runner status and an OTLP export, and the notes of the terminal view (why it uses Rich).

### Sicherheit

- The lite edition has no sentinel: it is not imported and its endpoints answer 404.

## [1.6.0]

> Diese Version liegt vorerst nur auf Englisch vor; die Übersetzung folgt in einer späteren Version.

### Hinzugefügt

- **Conditional reads (ETag)**: every read of the run lists sends `If-None-Match`; a `304 Not Modified` answer costs no quota. The header and `ghamon_etag_saved_total` count the reads saved; `cache.etag.*` in the Settings tab.
- **Resilience to network cuts**: when every read of a cycle fails with a connection problem the page keeps the last picture with an offline banner and resumes by itself; `offline` and `online` events (they can be notified) and `ghamon_offline`.
- **Analytics** (section A12 of the Sentinel tab, `/api/analytics`, `/metrics`, the Grafana JSON source): p50 / p95 of the duration of each workflow, of the queue time of its jobs and of each step; workflows that got slower than usual; **flaky** workflows (failed, then passed on the same commit, or needed another attempt), only a label that never changes what counts as red.
- **Incoming webhook in real time**: a signed `workflow_run` event updates the run list of its repository without reading GitHub, `workflow_job` events bring queue and step times; only short validated fields are kept (`/api/live-events`).
- **Workflow linter**: `lint_workflows.py` (actions not pinned by SHA, missing or broad permissions, secrets in clear text, injection, `pull_request_target` with the PR's code), rules switchable with their own severity, a line in the daily report and the section A13. A comment `# monitor-lint: ignore RULE reason` or the setting `lint.ignore` silences a finding.
- **Notifications** (off by default): Telegram, Discord, Slack, Matrix, MQTT and a local HTTP address, a limit per hour, a test button and a documented adapter contract (`monitor/docs/schemas/notification_event.schema.json`).
- **AI assistant**: new providers `anthropic` (Messages API, the model is yours to choose) and `copilot` (`gh copilot` with your own login, text only, no tools); new tasks (daily report, release notes, a question about a repository); settings for the kinds of event, the repositories, the language and the limits, a test button and the use of the day. A closed list of actions (`gh run rerun`, `gh issue close`, `act`), only PROPOSED by default.
- **The figures of the header are tiles** with an icon, a big figure and a small label, coloured by state, with a tooltip, a click that leads to the tab, counting figures and a skeleton that shows the last known values at once; the second line (repositories, hot, mode, reads saved, GitHub allowance with a bar and a live countdown, connection, last update and the loading progress) is made of tiles too.
- **Terminal view**: `tui.py` draws a live grid in the console (read-only, optional, needs the package `rich`; the monitor and its tests need no package).
- **For servers and bigger accounts**: `GET /api/health`, `GH_HOST` for GitHub Enterprise Server (every link of the page follows it), `discover_limit`, minimum permissions per feature, and a guide to run it as a service (systemd, launchd, a scheduled task, a container) and behind a reverse proxy.
- Published JSON schemas of `ci_red.json`, of the public export and of the notification event (`monitor/docs/schemas`), and a public roadmap (`docs/ROADMAP.md`).
- New guides in eight languages: notifications, the AI assistant, analytics, console tools and deployment; the webhook guide covers the real-time events. All screenshots were redone (light and dark, console tools included) with `tools/make_screenshots.py` and invented data.

### Geändert

- **Settings**: new sub-tabs for reads and cache, notifications, analytics, the linter and the terminal view; the AI and webhook sub-tabs have all their options.

### Behoben

- **The linter no longer cries wolf on placeholders**: a value that looks like a secret is classified (a known token format or a long high-entropy string is serious, a readable filler such as `placeholder` or `changeme` is only information, anything else a warning; references and empty values are no finding) and its value is never printed or stored.
- **A browser that closes or reloads its tab while the page is loading no longer prints a traceback** (`ConnectionAbortedError`, `ConnectionResetError`, `BrokenPipeError`): they are counted in `ghamon_client_disconnects_total`; a real error is still shown.

### Sicherheit

- The incoming webhook stays off by default, on `127.0.0.1`, with a mandatory HMAC.
- Notification secrets live only in environment variables; hosts are fixed; notifications never write to GitHub.
- AI actions: running one needs its own switch and a confirmation of the full command each time, only on targets the monitor already watches, with a limit per hour, a local log and a lock after two failures in a row.

## [1.5.2]

> Diese Version liegt vorerst nur auf Englisch vor; die Übersetzung folgt in einer späteren Version.

### Hinzugefügt

- **The Settings tab is organised in sub-tabs**, ordered from the common to the advanced (This browser, General, Refresh and limits, Sentinel, Surface checks A10, Readiness A11, Folders and files, Outputs, External AI, Incoming webhook). Inside a sub-tab the settings sit in titled blocks whose first field is the main switch (the rest of the block dims while it is off). Every field shows its unit and range, a badge (needs a restart / applies now), a badge for the safety options that start in their conservative state, and one line of help. A search box filters all the sub-tabs, each sub-tab counts its unsaved changes, Save and Discard stay visible, the arrow keys, Home and End move between the tabs and the last sub-tab used is remembered by the browser.
- **Every setting of the configuration file is in the page now**: the A10 checks (a switch per check and its limits), the weights of the ecosystem health score, the sources of the pinned versions, the Actions-minutes ceilings, the required files, the audit file patterns, the hot period of the sentinel, the unknown-sample rule of A2, the candidate prefixes, the list of repositories and the switch of the incoming webhook.
- **Signing queue by trust**: each row says `verified`, `unknown` or `failed`; the Sentinel tab has a Signature filter with the count of each kind; `read_report.py --sign-trust` filters the console list and the export, and the exported rows carry `trust`.
- **Readiness chips in the header**: one coloured chip per ecosystem with its health score.
- **A minimal Grafana board** (`red_by_ecosystem.json`) and a test that checks every metric of both boards against what `/metrics` serves.
- New guide `WEBHOOK` (refresh-only mode) and a commented example of the pin sources, in eight languages.
- `tools/make_settings_doc.py` writes the settings table of the guides from the schema and the texts of the page, and the CI checks it.

### Geändert

- **The daily report groups the issue-closing suggestions** in one line per repository (the monitor still closes nothing).
- **The contract of the profile dashboard** is documented and checked by a test (`/api/outputs/dashboard.json` is exactly the document of `ci_red.json`; the public export never carries the signing side).

### Sicherheit

- The shared secret of the webhook is never shown in the page: it only says whether it is defined.

## [1.5.1]

> Diese Version liegt vorerst nur auf Englisch vor; die Übersetzung folgt in einer späteren Version.

### Hinzugefügt

- **The settings page can set the external AI of the sentinel** (group "External AI for the sentinel"): `ai.provider` (`none` / `ollama` / `openai-compatible`), `ai.model`, `ai.ollama_url` (only this computer), `ai.base_url` (https only), `ai.api_key_env` and `ai.daily_limit`. Off by default; an outside service receives data of your repositories.
- **`migrate_state.py`**: brings the files written before 1.5.0 to the new names (events, report history, release candidates, batch records, the `report_history_days` setting). A dry run by default; `--apply` copies and keeps the old files, `--move` renames them; nothing that exists is overwritten. One-page guide in `docs/MIGRATING.md`, in eight languages.
- **`--init-catalog`** creates editable `ecosystems.json`, `targets.json` and `profiles.json` from the examples.
- A test makes sure no document sends the reader to a command that was renamed in 1.5.0 (only the tables of old and new names and the migration guides may name them).
- The version in every README.

### Geändert

- **First start without catalogue files of your own**: the console says the example files are in use.
- Python 3.11 or newer is the documented minimum (tested on 3.11 and 3.13 on Windows, Linux and macOS).

### Sicherheit

- Only the NAME of the environment variable that holds the AI key can be set: the key itself is never shown or saved.

## [1.5.0]

> Diese Version liegt vorerst nur auf Englisch vor; die Übersetzung folgt in einer späteren Version.

**Update notice (read this first).** Several files and settings have English names now. Nothing is lost: the old names are still READ where a file written by an earlier version may exist, and the new names are the only ones written.

| Before 1.5.0 | From 1.5.0 |
|---|---|
| `leer_parte.py` | `read_report.py` |
| `eventos.py` | `events.py` |
| `parte_history.py` | `report_history.py` |
| `LOTE_GITHUB_ACTIONS.bat` / `.sh` / `.command` | `BATCH_GITHUB_ACTIONS.bat` / `.sh` / `.command` |
| `eventos_monitor.jsonl`, `eventos_estado.json` | `events_monitor.jsonl`, `events_state.json` (copy or rename them to keep the history of events) |
| `PARTE_CENTINELA_DIA_<day>.txt/.json` (report history) | `SENTINEL_REPORT_DAY_<day>.txt/.json` (the old ones are still read) |
| `PARTE_CENTINELA_<time>.txt` (saved report) | `SENTINEL_REPORT_<time>.txt` |
| `CANDIDATAS_RELEASE.txt` | `RELEASE_CANDIDATES.txt` |
| `<signed_dir>/lotes/lote_<time>.json` | `<signed_dir>/batches/batch_<time>.json` (the old records are still read) |
| `parte_history_days` (setting) | `report_history_days` (the old name is still read) |
| `monitor_y_centinela.zip` and folder | `github_actions_monitor.zip` and folder; `LEEME_CORREO.txt` is `README_MAIL.txt` |
| A8 looked for `RECONCILIACION_TOTAL_AUDITORIAS_*.txt`, `MAPA_DE_RONDAS_*` | the names are `sentinel.audit_files` (neutral defaults `RECONCILIATION_TOTAL_*.txt`, `ROUNDS_MAP_2*.txt`, `ROUNDS_MAP_EXTRA_*.txt`); set your own there |
| `ci_red.json`, its schema and the `--export-status` files | unchanged (they are a contract) |

- **English by default.** The language of the system no longer decides: the tools start in English until you choose another one in the Settings tab, with `language` in `actions_monitor.json`, `MONITOR_LANG` or `--lang`.
- **A clean, neutral package.** `ecosystems.json`, `targets.json` and `profiles.json` are no longer part of the package: only the `*.example.json` files travel, and a missing default file falls back to its example. Your own files live anywhere and are named by `ecosystems_file`, `targets_file` and the new `profiles_file`; the folder of your local signing tools is the new `tools_dir`. The tests use their own fixtures (`tests/fixtures`).
- **Settings tab.** A new tab changes the values of `actions_monitor.json` from the page: a whitelist of keys with their type and range, one request refused as a whole when a value is invalid, a copy of the previous file in `config_backups/` before every save (the last ten are kept), an atomic write, only on 127.0.0.1 with the same Host and Origin checks as every other endpoint, JSON only. Tokens, secrets, signature keys and the command of the sentinel are not in the list: they are never shown and never written, and every other key of the file is kept as it was. Each setting says whether it needs a restart. The language selector, the theme and the dense view moved there.
- **Buttons and icons.** Buttons have relief, light up on hover and sink when pressed; the icon buttons are inline SVG with an accessible name and a tooltip in the 8 languages. Colours, type, cards, bars and the ring follow the status dashboard of the profile repository.
- **Life in the charts.** Bars grow in, what is red or running has a discreet pulse, the figures of the header count up, hovering a bar highlights it and gives its text as a tooltip, widths change smoothly; all of it stops with `prefers-reduced-motion`.
- **Outputs for other tools (off by default, 127.0.0.1 only, no new token).** `/metrics` in the Prometheus format (red workflows per ecosystem and repository, red streaks and hours, builds waiting for a signature, A10 paused, allowance left, incomplete snapshot...), `/api/outputs/grafana.json` for the Grafana JSON / Infinity source and `/api/outputs/dashboard.json` (the `ci_red.json` document) for the status dashboard. An importable Grafana dashboard is in `docs/grafana/` and the details in `docs/OUTPUTS.md`.
- **Report:** a line (code `tag_vs_manifest`) when a release tag is ahead of the version of the manifest; the unsigned figure is ordered by the longest wait and says how long it is; the repository panel suggests the `gh issue close` command (never run) for a failure issue whose workflow is green again; the `hil` batch profile is documented in `profiles.example.json`; tests for `finalize` and for `monitor_link`.
- **Docs:** `docs/SETTINGS.md`, `docs/OUTPUTS.md`, README and QUICKSTART in the 8 languages updated, screenshots made with invented repositories.

## [1.4.5]

> Diese Version liegt vorerst nur auf Englisch vor; die Übersetzung folgt in einer späteren Version.

- **The report says when the snapshot is incomplete:** a line with the stable code `incomplete` (still loading, no local workspace, errors while reading) right after the headline, so nobody acts on a half-read list of red repositories or signing queue.
- **Signing summary:** one line with how many releases wait to be signed (verified / not checked / failed the check) and how many builds are build-only on purpose, so "not signed on purpose" is not confused with "signature missing" (code `sign_summary`).
- **A10 paused for the quota is said in the report** (code `a10_paused`) with the allowance left and needed, and the three knobs that control it.
- Texts in the 8 languages; tests for the three lines.

## [1.4.4]

> Diese Version liegt vorerst nur auf Englisch vor; die Übersetzung folgt in einer späteren Version.

- **Author and licence are always visible:** the web panel has a footer with the author and the licence, `read_report.py --version` and the new `gha_dispatch_all.py --version` print them under the version, and the monitor prints the same line when it starts. The text is in the 8 languages (`ui.about`); the author and the licence come from `tool_version.py`.
- **Bridge to the dashboard written down:** `docs/CI_RED_BRIDGE.md` says what `ci_red.json` contains (schema 2, `complete`), how to export it and what a reader must check; the monitor still never pushes or commits.
- Tests for the author line in the 8 languages, the footer, both `--version` flags and the start-up line.

## [1.4.3]

> Diese Version liegt vorerst nur auf Englisch vor; die Übersetzung folgt in einer späteren Version.

- **A workflow that only runs on pull requests no longer makes A2 inconclusive:** `pull_request` and `pull_request_target` join the events whose runs never sit on the default branch (like `workflow_dispatch`, `release` and `workflow_call`), so a workflow such as a contract integration check that only runs on pull requests is not asked for a last run on main. A workflow that also has `push` or `schedule` still counts. Tests for both cases.

## [1.4.2]

> Diese Version liegt vorerst nur auf Englisch vor; die Übersetzung folgt in einer späteren Version.

- **A2 no longer counts a run in progress or a cancelled one as seen:** when it resolves a hidden workflow, the Sentinel now asks for the last completed runs of that workflow on the default branch (`gh run list -w <file> --branch <default> --status completed -L 10`, read only) and uses the first one with a real conclusion. A cancelled or skipped run (and anything without a conclusion) is ignored, so it can no longer hide an earlier red; a workflow with no completed run with a conclusion on the branch stays inconclusive on its own. Same quota gate, call limit and cache as before.

## [1.4.1]

> Diese Version liegt vorerst nur auf Englisch vor; die Übersetzung folgt in einer späteren Version.

- **A2 resolves a hidden workflow instead of giving up on the whole repository:** when a repository has a full run sample and a workflow of its clone (one that can run on the default branch) is missing from it, the Sentinel asks GitHub for the last run of THAT workflow on the default branch (`gh run list -w <file> --branch <default> -L 1`, read only). A red answer counts as red in A2; a green one removes the workflow from the inconclusive list; a workflow with no run on the branch stays inconclusive on its own and the panel names it (`repo/file.yml (no run on the default branch)`) instead of only the repository. Without quota (same gate as A10: `min_rate_remaining` x `surface.min_rate_factor`, plus the hourly budget) the workflow stays inconclusive and the panel says why. New options `sentinel.a2_resolve_max_calls_per_tick` (4; 0 = never ask) and `sentinel.a2_resolve_ttl_seconds` (3600, how long an answer is kept; it is also saved in the cache file). The snapshot carries `a2.inconclusive_workflows` (labels) and `a2.inconclusive_details`; `a2.inconclusive` is still the list of repositories. 5 new texts in the 8 languages and a reworded `ui.a2_inconclusive`.

## [1.4.0]

> Diese Version liegt vorerst nur auf Englisch vor; die Übersetzung folgt in einer späteren Version.

- **New layer A11 "Readiness" (read only, real data only):** a panel of the Sentinel tab, a traffic light in its header and two lines of the report. It is switched with `sentinel.readiness.enabled` and described in `readiness.py`.
  - **Release readiness:** one row per repository with at least `candidate_min_entries` entries in `[Unreleased]` (external ecosystems excluded): CI of the default branch (the single rule of A2) with the commit it ran on, whether the version the clone declares (`*.project.json`, else `pyproject.toml`, else the first CHANGELOG heading) is already above the last release, whether a build exists after that release, whether it is signed (the states of A5), and the next step (`fix the red CI`, `wait for run data`, `bump the version`, `build in Actions`, `sign`, `publish`, `cut and publish`). A green CI over a full run sample that may hide an older workflow says so.
  - **Ecosystem health:** per ecosystem, 100 minus weighted counts of red CI, stuck builds, secrets, serious alerts, other alerts, Dependabot PRs older than `stale_pr_days`, builds waiting for signing and repositories with hygiene problems (`sentinel.readiness.health.weights`); the parts that lower the score are listed. No score is shown (`?`) when fewer than `min_coverage` (0.5) of the repositories of the ecosystem have run data and alerts. The report warns when a score is under `warn_below` (70).
  - **Dependency pins:** repositories that pin an older version than the one of the repository that provides the contract or library. Where the pins live is data (`sentinel.readiness.pins.sources`): a JSON table of pins in the provider (`pin_table`) or lock files in the consumers (`lock_files`, the oldest one found counts). Plain file reads of the local clones, cached `pins.refresh_seconds`; an ecosystem without a configured source is listed as having none, and nothing is guessed. The shipped example has no source.
  - 60 new texts in the 8 languages; `tests/test_readiness.py` (rules, weights, coverage, pins on a temporary tree, the page and the 8 catalogues).
- **`docs/CI_RED_SCHEMA.md`:** says explicitly that the PC publishes neither `ci_red.json` nor `pending_sign` to any repository or dashboard (the signing side is local by decision); a public consumer recomputes the rule from the public runs or uses `read_report.py --export-status`.
- **Quota tuning from the log (`actions_monitor_log.txt`, 3 days, 889 samples):** the shared allowance was under the floor (`min_rate_remaining` 1500) in 11% of the samples since 5 November and under 3000 in 45%; the hourly burn was 3000-5000 calls in most hours and reached the limit in some. In the maintainer's `actions_monitor.json`: `refresh_seconds` 120 -> 180 (the real cycle was a median of 139 s) and `sentinel.surface.min_rate_factor` 2.0 -> 1.5 (the cold calls of A10 are about 260 a day, so they can run above 2250; with 3000 they waited almost half of the time). `max_repos_per_tick` (6) and the daily cold cycle stay: they cost less than 1% of the allowance. The shipped example keeps its neutral defaults.

## [1.3.3]

> Diese Version liegt vorerst nur auf Englisch vor; die Übersetzung folgt in einer späteren Version.

- **A2 ignores workflows that never run on the default branch:** when deciding whether a full run sample hides a workflow, the files of the clone whose `on:` has no `push`, `pull_request` or `schedule` for the branch (only `workflow_dispatch`, `release`, tag-only `push` without `branches`, or `workflow_call`) are no longer expected in the sample. `on:` is read with the standard library only (string, list, map, and the YAML `true` key); if it cannot be parsed the workflow counts as before. The workflow scan carries the new field `main_triggered` (`true`/`false`/`null`).

## [1.3.2]

> Diese Version liegt vorerst nur auf Englisch vor; die Übersetzung folgt in einer späteren Version.

- **A2 shows `unknown` instead of green when its sample is full and inconclusive:** a repository whose list of runs is as long as the sample asked for (`runs_per_repo` / `cold_runs_per_repo` of the monitor, which the check did not see before) and whose clone has a workflow file with no run in that sample (or that has no clone) is listed as inconclusive, and A2 is `unknown` unless something is red. New option `sentinel.a2_full_sample_unknown` (default `true`; `false` = only informative as before). The page lists the repositories.
- **`profiles.example.json`:** a neutral batch-profiles template that matches `targets.example.json` and `ecosystems.example.json`. A test (and the release gate) validates it against those catalogues, not the maintainer's, and checks that every profile selects at least one target.
- **Clean-install check in `make_release`:** before anything is left in the output folder the zip is extracted into a new, empty temporary directory and, from there with `python -I`, every member must be present, every module must compile, `read_report.py --version` must run and the whole suite must pass; any gap fails the release.
- **Wording:** README and QUICKSTART in the 8 languages now say that the package writes nothing to GitHub on its own and that only `dispatch --go`, `dispatch --real` and `finalize --execute` (which you run) do.
- **A10 quota:** the share of the sentinel's per-tick call budget that A10 may use is now `sentinel.surface.budget_share` (default `0.5`, as before but configurable); the page shows "A10 paused for quota" with the allowance left and the one needed (`min_rate_remaining` x `min_rate_factor`) while the cold calls wait.

## [1.3.1]

> Diese Version liegt vorerst nur auf Englisch vor; die Übersetzung folgt in einer späteren Version.

- **A run built on another commit is never offered for signing:** when `dispatch` could only find a recent run of another commit (`sha_matched` false), `finalize` now lists it as not ready with the reason and gives no signing command; an old batch without the field behaves as before. Tests with two concurrent runs of different commits.
- **`/api/data` goes through the same Host/Origin guard as the other routes** of the local server (DNS rebinding).

## [1.3.0]

> Diese Version liegt vorerst nur auf Englisch vor; die Übersetzung folgt in einer späteren Version.

Made to be shared: eight languages, authorship and licence in every file, no private data, and nothing tied to one GitHub account.

- **8 languages** (en, es, de, fr, it, ja, zh, pt = European Portuguese) for the page, the command line tools, the launchers, the events, the reports and the error
  messages. `i18n.py` + `locales/<lang>.json` (one flat catalogue per language, standard library only, `t("key", name=value)` with a fallback to English). The language
  is `language` in `actions_monitor.json` (default: the system language, English if unsupported), a selector in the header of the page (remembered by the browser),
  `MONITOR_LANG` / `JUANENRAC_LANG`, or `--lang CODE` in every tool (it wins over the rest). Technical names, commands, paths and the markers that scripts read
  (`SKIP`, `DISPATCHED`, `READY`, `FAILED`, `Summary:`, `BUILD ONLY`, `WOULD DISPATCH`...) are never translated. Events in `events_monitor.jsonl` now carry a stable
  `code` (and `args`) next to the text, so nobody has to parse a language.
- A test checks that the 8 catalogues have exactly the same keys, none empty, the same `{placeholders}`, that every key used by the code and the page exists, and that no
  visible string in the code bypasses `t()`.
- README and QUICKSTART in the 8 languages (`README_<lang>.txt`, `QUICKSTART_<lang>.txt`); `README.txt` is now a short language chooser with the quick start.
- **Authorship and licence**: every source file carries "Copyright (C) 2026 JuanenRac (Electro Hobby 3D)" and "GPL-3.0-or-later - see LICENSE"; JSON data files carry
  `_author` / `_license`; `LICENSE` (GPL-3.0 text), `NOTICE` and `AUTHORS` travel in the zip. `make_release.py` refuses to build when a file lacks them, when private data
  would travel, when the locales differ, or when a launcher loses its executable bit.
- **Shareable**: `github_owner` in the configuration (default: the account of `gh`) replaces the constant that was spread over three modules; the ecosystem prefixes and the
  signing tools are data (`ecosystems.json`, neutral `ecosystems.example.json`; `"*"` = every repository; `"external": true` = only reported) and so are the targets (`targets.json`
  is the maintainer's real catalogue, `targets.example.json` the neutral one; `targets_file` / `ecosystems_file` choose them; keys that start with `_` are metadata).
  The example configuration is neutral. Nothing of this adds a call to the hot cycle.
- **The workspace is optional**: without local clones the monitor starts in a reduced mode (only what the GitHub API gives: no local signing queue, no audit report, no
  CHANGELOG scan) and says so on the page, in the report and at start, instead of stopping. `MONITOR_ROOT` / `MONITOR_AUDIT_DIR` / `MONITOR_SIGNED_DIR` and `signed_dir`
  were added next to the old names. The roadmap layer (A9) is optional too.
- Launchers: menus and messages come from `launcher_msg.py` (your language); comments in English; header on every file.
- Fix: `workspace_root()` no longer ends the monitor when the sentinel starts without a workspace.

## [1.2.0]

> Diese Version liegt vorerst nur auf Englisch vor; die Übersetzung folgt in einer späteren Version.

What was missing and what else can be done on GitHub, all of it read only and local.

**Part A - what was missing**
- `ci_red.json` schema 2 is now a documented contract: `docs/CI_RED_SCHEMA.md` (shape, the one rule of "red", what is for the owner only). Nothing is
  published from the PC. Optional, explicit exports (never a commit or a push): `read_report.py --export-status DIR` writes ONLY the red list
  (`ci_status_public.json/.md`); `read_report.py --export-sign-queue FILE` (.json/.csv) writes the global signing queue with the local commands.
- Attestation: the signing queue shows whether the build has an attestation (existence by digest of the signed files, one lookup per entry, no signature
  check; switch `sentinel.surface.checks.attestation`). A missing one is a line in the report.
- More verified formats: HYDRA `hydra-sign` (`FILE.sig` = base64 Ed25519 over the bytes of the file, the pinned release key, read in blocks) is checked
  definitively; URTC `.imgsig` has its strict format checked (152 hex digits + LF; malformed = not valid) and stays "unknown" when well formed (the signed
  message also needs the build header, which the signed folder does not carry); ARMOR APKs are signed inside the APK by apksigner and stay "unknown".
- `HYDRA-UMC-OS` is labelled on purpose in `targets.json` (`"build_only": true` + `reason`): `plan` lists it under BUILD ONLY and it is no longer an orphan.
  The signing tools were not touched (its workflow takes other inputs and a different signature scheme).
- Fix: `ci_red.target_path` refused every Windows path written with backslashes (`C:\...`); only forward slashes were accepted.

**Part B - the A10 layer "Actions & releases surface"** (`surface.py`, new section of the tab, a switch and a threshold per check under `sentinel.surface`)
- Actions: workflows disabled by hand, schedules with no run in N days (only when the sample of runs covers the window), `uses:` not pinned by SHA
  (reusable workflows flagged apart), `permissions: write-all`, `pull_request_target` with a checkout of the PR, stuck concurrency queues, failures on only one
  OS of a matrix, artifact cost and retention, required status checks that are red or missing (GraphQL), `dispatch --profile release|nightly|hil` with a canary
  (the first target alone, the rest only if it is green) and a quota gate (`--min-rate`, fails closed). Profiles live in `profiles.json`.
- Releases: expected assets per kind of target (alert when a release was published incomplete), tag vs manifest vs CHANGELOG, GitHub Packages, forgotten drafts
  and pre-releases, `release_notes.py` (a DRAFT of notes from the commits since the last tag; it publishes nothing).
- Security: critical/high alerts by age with a ranking of repositories, coverage (a stack without CodeQL/Dependabot), secret scanning open vs resolved,
  Dependabot by priority (runtime major first, CI-only last).
- Issues and PRs: suggestion of `gh issue close` for build issues whose CI is green again (an event with the text; nothing is ever closed), overdue milestones,
  old human PRs, PRs that touch workflows or CODEOWNERS, the merge queue (approved with green checks). Stale board cards: PENDING (needs per-item reads and a threshold).
- Manifest vs evidence (maturity), 8-language README parity failures, Actions minutes per ecosystem in the header, the report and A7.
- `finalize --execute` now tells the running monitor (127.0.0.1) to refresh just the signed repositories and rewrite `ci_red.json` at once (`monitor_link.py`).
- Optional signed webhook receiver (`webhook.enabled`, off by default, 127.0.0.1 only, HMAC with a shared secret from the config, never a GitHub token).
- Cost: nothing in the hot cycle. Cold, spread over ticks and inside the hourly budget: 2 REST calls per repository per day, one GraphQL query per 15
  repositories per day, 3 for Packages, plus the jobs of red runs and the attestation lookups of the signing queue, and only while the allowance is above
  twice `min_rate_remaining`. The hot GraphQL pass asks for 3 more fields per node (alert dates, review decision, checks state): no extra call.
- The gate also compares `sentinel.surface` of the example file with the defaults and validates `profiles.json`.

## [1.1.1]

> Diese Version liegt vorerst nur auf Englisch vor; die Übersetzung folgt in einer späteren Version.

- **Cross-platform:** the monitor and the batch tools work on Windows, macOS and Linux. Launchers `MONITOR_GITHUB_ACTIONS.sh`/`.command` and `BATCH_GITHUB_ACTIONS.sh`/`.command` (the zip keeps the executable permission and make_release rejects Windows line endings in them).
- New `platform_compat.py`: the command that starts a child tool (`py -3` on Windows, the current interpreter elsewhere), the text of the commands that `finalize` shows (cmd/PowerShell or POSIX quoting), UTF-8 console and a notice with the way to install `gh` on each system.
- New tests of the cross-platform part (Windows and POSIX simulated from any system).

## [1.1.0]

> Diese Version liegt vorerst nur auf Englisch vor; die Übersetzung folgt in einer späteren Version.

Signature trust, a stable bridge to the dashboard, orphans and conventions in the batch tools, and a more useful page.

- Signature trust: `sigverify.py` (standard library, read only, no network) checks the signed folder `_firmados/<REPO>/release-<version>/` against the PUBLIC
  key each ecosystem pins (URTC `release_sign.py`, ARMOR helper `PACKAGE_PUBLIC_KEY`, HYDRA updater `RELEASES_PUBLIC_KEY`, or `sentinel.signature_pubkeys`).
  Every state now carries `signature_kind` (none | dev | release) and `signature_verified` (true | false | "unknown"); only a release signature that verifies
  (`trusted`) lowers the pending-signature alert, besides "published". A signature that does not verify keeps the alert and says so in the report.
  `sentinel.require_verified_signature` (default true; false = the 1.0.0 rule). Formats this module cannot check (.sig2, .hdr2, .imgsig, APK, hydra-sign) are
  "unknown", never "false". The build attestation still needs the network and stays with the signing tools.
- `ci_red.json` schema 2: per repository a `pending_sign` list (workflow, hours, state, signature_kind, signature_verified, last_build_at, url) next to the red
  workflows, plus `schema`, `pending_sign_repos` and the threshold; the format is documented in `ci_red.py` and is only ever extended.
- One definition of "last run on main" (`signstate.completed_runs`) shared by the red check, the green-without-release check and the target states.
- `ci_red.target_path` refuses D: paths, WSL/Git Bash forms of D: and drive/UNC paths that the running system cannot use; the tests simulate both systems
  and the whole suite now passes on Linux.
- `gha_dispatch_all.py plan` always ends with the section "Signature orphans" (green CI + known `*-build.yml` + no target); coverage is by repository AND workflow.
- Convention for targets (ecosystem prefix -> default signing tool, workflow in the known list); `targets.json` only holds the overrides and always wins.
  `hygiene --write-candidates` writes the proposed entries to `targets.candidates.json` (never applied by itself, never packaged).
- Page: clickable header counters "red on main" and "unsigned" (filter the repositories; the second one also focuses the signing queue), the signing queue
  with its commands and a copy button, repository panel with build / signed / published, signature kind and verification, and the suggested command;
  a header badge when a minutes budget reaches 80 % (red when exceeded); "yesterday vs today" also compares budget warnings and the lines of the report.

Not done: reading the build attestation / SBOM (network); `HYDRA-UMC-OS` has a build workflow but its signing tool does not support it yet (listed as an orphan).

## [1.0.0]

> Diese Version liegt vorerst nur auf Englisch vor; die Übersetzung folgt in einer späteren Version.

First numbered version. What the package does:

- Monitor of GitHub Actions for the four ecosystems (local web page, run cache, stuck builds, build-failed/build-stuck issues).
- Sentinel layer A (read only, no AI needed): A1 stuck builds, A2 red CI (one criterion: last completed run of each workflow on the default
  branch), A3 CodeQL/Dependabot/secret alerts, A4 Dependabot pull requests, A5 releases (candidates, green builds without a release,
  pending signature), A6 hygiene, A7 consumption (minutes and API allowance), A8 audits and rounds, A9 roadmap boards.
- Explicit state of each build target: built_on_gha -> signed_local (none | dev | release) -> published, with `last_build_at`,
  `last_signed_at`, `signature_kind` and the real hours waiting; local batch and signed-folder records lower the pending-signature
  alert without waiting for GitHub.
- Signing queue of the day (`a5.sign_queue`): most urgent first, with the exact finalize command of each target.
- Budget of Actions minutes per ecosystem (`sentinel.minutes_budget`, empty by default): warning at 80 % in the report and as an event.
- Event feed (`events_monitor.jsonl`) and `ci_red.json` (repository -> red workflows + hours pending signature), written atomically.
- Batch tools: `gha_dispatch_all.py plan|dispatch|status|finalize|hygiene` with `--only` or `--ecosystem`, `plan --json`,
  `finalize --json`, one retry of a failed dispatch at the end of the batch, targets as data in `targets.json`.
- `read_report.py`: the report as plain text from the running monitor, without spending API quota.
- `make_release.py`: quality gate (unit tests, clean zip, complete example configuration, version/changelog agreement) and SHA256SUMS.

Not done in this version: verifying release signatures against the public key and the build attestation from the sentinel
(different signature formats per ecosystem; the attestation needs the network; the signing tools verify both before publishing).
