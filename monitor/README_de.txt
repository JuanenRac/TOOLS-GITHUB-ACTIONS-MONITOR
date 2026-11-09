Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE

GITHUB-ACTIONS-MONITOR + WÄCHTER (Version 1.6.8)
================================================
WELCHE STARTEN? (ein neuer Nutzer entscheidet in zwei Minuten)
  KOMPLETT  MONITOR_GITHUB_ACTIONS.*       die Seite mit dem Wächter (Port 8765): Alarme, Signierwarteschlange, Analyse. Hier beginnen, wenn Sie mehrere Repositories haben.
  LITE      MONITOR_LITE_GITHUB_ACTIONS.*  dieselbe Seite ohne Wächter (Port 8766): was rot ist, hängt oder läuft. Leichter; läuft neben der kompletten.
  BATCH     BATCH_GITHUB_ACTIONS.*         nur wenn Sie Ihre eigenen Builds signieren und veröffentlichen.
  TERMINAL  python tui_textual.py (mit --lite für die Lite-Edition)   die interaktive Terminal-Anwendung; tui.py --once gibt einen Bildschirm aus.
  PRÜFEN    python actions_monitor.py --doctor (--json für Skripte)   sagt, was fehlt, und den genauen Befehl dagegen.
  AUSPROBIEREN  python actions_monitor.py --demo   die Seite mit erfundenen Daten: kein gh, keine Anmeldung, nichts von Ihnen wird berührt.

Voraussetzungen: Python 3.11+ und die GitHub CLI (`gh`), angemeldet (gh auth login). Sonst nichts: der Kern braucht keine Pakete (die Konsolenansicht tui.py nutzt das optionale Paket rich).
Kurzanleitung für die erste Benutzung: QUICKSTART_de.txt.

START      Windows: MONITOR_GITHUB_ACTIONS.bat | Linux: ./MONITOR_GITHUB_ACTIONS.sh | macOS: Doppelklick auf MONITOR_GITHUB_ACTIONS.command
           (öffnet http://127.0.0.1:<Port>, nur lokal). Auf jedem System geht auch:  python3 actions_monitor.py  (Windows: py -3 actions_monitor.py)
BATCHES    BATCH_GITHUB_ACTIONS.bat / .sh / .command  (gha_dispatch_all.py: plan, dispatch, status, finalize, hygiene). Optional, für alle, die ihre Builds lokal signieren.
WAS ER NIE TUT   Er lauscht nur auf 127.0.0.1, außer Sie schalten den Netzwerkmodus ein (Einstellungen > Erweitert: eine private Adresse, ein Zugriffstoken bei jeder Anfrage, eine Warnung in der Seite). Er speichert kein Token (er fragt `gh`), außer Sie schalten das optionale Token im sicheren Speicher des Systems ein. Von sich aus schreibt er nichts auf GitHub: nur die Batch-Befehle `dispatch --go`, `dispatch --real` und `finalize --execute` schreiben auf GitHub (Workflows starten, unsignierten Entwurf anlegen, veröffentlichen), und nur wenn du sie ausführst.
           Er signiert NICHTS und veröffentlicht NICHTS von selbst: Signieren und Veröffentlichen sind Befehle, die DU ausführst; der Monitor zeigt sie nur als Text.
           Keine KI im kritischen Pfad; der optionale KI-Erklärer ist standardmäßig aus.

SPRACHE    8 Sprachen: en, es, de, fr, it, ja, zh, pt (europäisches Portugiesisch). Der Start erfolgt auf ENGLISCH: die Sprache des Systems entscheidet nicht. Eine andere wählst du im Tab EINSTELLUNGEN der Seite
           (Zahnrad-Symbol; der Browser merkt sie sich), mit "language" in actions_monitor.json, mit der Umgebungsvariable MONITOR_LANG oder mit --lang CODE in den Kommandozeilenwerkzeugen (schlägt alles andere).
           Zeilen, die Skripte lesen (SKIP, DISPATCHED, READY, FAILED, Summary:, BUILD ONLY...), sind immer englisch.
KONFIG     actions_monitor.json (beim ersten Start aus actions_monitor.example.json erzeugt). Nützliche Schlüssel: github_owner (leer = das Konto von gh),
           language, ecosystems_file, targets_file, refresh_seconds, cold_refresh_seconds, max_workers, min_rate_remaining, sentinel.*
           ecosystems_file: gruppiert Repositories nach Namenspräfix (siehe ecosystems.example.json; "*" = alle Repositories). targets_file: Katalog der Builds für die
           Batch-Werkzeuge (siehe targets.example.json). profiles_file (profiles.example.json): Batch-Profile. Schlüssel, die mit "_" beginnen, sind Metadaten.
WORKSPACE  OPTIONAL: ein Ordner mit lokalen Klonen deiner Repositories (MONITOR_ROOT, "workspace_root" in der JSON-Datei oder ein übergeordneter Ordner mit der Datei .monitor-root).
           Ohne ihn startet der Monitor im REDUZIERTEN MODUS und sagt das: nur, was die GitHub-API liefert (keine lokale Signatur-Warteschlange, kein Audit-Bericht, kein CHANGELOG-Scan).
           Mit ihm gibt es zusätzlich Release-Kandidaten, die Signatur-Warteschlange und die Batch-Werkzeuge. Signaturprotokolle: "signed_dir"; Audit-Dateien: "audit_dir".
TESTS      py -3 -I -m unittest discover -s tests   (Linux/macOS: python3 -I -m unittest discover -s tests). Sie brauchen kein Netz.
PROBLEME   "API rate limit": Das gemeinsame Kontingent von gh (5000/Stunde) ist aufgebraucht; auf das Zurücksetzen warten (gh api rate_limit), refresh_seconds erhöhen / max_workers senken.
           Der Monitor bricht beim Start ab, wenn gh nicht antwortet. Eine beschädigte Cache-Datei wird ignoriert; sentinel_cache.json löschen, um den Cache neu zu beginnen.
           Starte den Monitor nach einer Aktualisierung des Pakets neu (ein laufender Prozess behält den alten Code).

WERKZEUGE  read_report.py [--lang CODE] [--json] [--export-status ORDNER] [--export-sign-queue DATEI]  gibt aus, was der laufende Monitor meldet (lokal, kein GitHub-Kontingent)
           gha_dispatch_all.py [--lang CODE] plan|dispatch|status|finalize|hygiene    Batch von GitHub-Actions-Builds (auf deinem PC wird nichts kompiliert)
           release_notes.py REPO [--since TAG] [--out DATEI]    Entwurf von Release-Notes aus Commits (ein Vorschlag; veröffentlicht nichts)
           release_candidates.py    Projekte mit Einträgen in CHANGELOG [Unreleased] und alter letzter Release (nur lesend)
EREIGNISSE Der Wächter schreibt pro ÄNDERUNG (neues Rot, wiederhergestellte CI, hängender Build, neue Warnungen ...) eine JSON-Zeile in events_monitor.jsonl. Jede Zeile hat einen
           stabilen `code` (nie sprachabhängig), `kind`, `level`, `repo`, `args` und `text` (in der konfigurierten Sprache). `tail -F` folgt der Datei.
ROTE CI    Ein einziges Kriterium: der LETZTE beendete Lauf jedes Workflows auf dem Standard-Branch. Rot = failure, timed_out, startup_failure oder action_required.
           cancelled, skipped, neutral und stale zählen nicht.

NEU IN 1.5.1 (Verlauf: CHANGELOG.md)
  - Tab EINSTELLUNGEN: neue Gruppe „Externe KI für den Wächter“ (ai.provider none / ollama / openai-compatible, Modell, Adresse von Ollama (nur dieser Rechner), ein https-Endpunkt, der NAME der Umgebungsvariable mit dem Schlüssel, Aufrufe pro Tag). Der Schlüssel selbst wird nie gespeichert. Standardmäßig aus; ein externer Dienst erhält Daten deiner Repositories.
  - migrate_state.py: bringt die vor 1.5.0 geschriebenen Dateien auf die neuen Namen. `python migrate_state.py` ist ein Probelauf; `--apply` kopiert (die alten bleiben), `--move` benennt um. Nichts wird überschrieben. Eine Seite in docs/MIGRATING.md, in 8 Sprachen.
  - Erster Start ohne eigene Katalogdateien: Der Monitor meldet, dass er die Beispiele verwendet (Konsole), und `--init-catalog` erstellt bearbeitbare Kopien von ecosystems.json, targets.json und profiles.json.
  - Python 3.11 oder neuer (getestet mit 3.11 und 3.13 unter Windows, Linux und macOS).

NEU IN 1.5.0 (Verlauf: CHANGELOG.md)
  - Tab EINSTELLUNGEN: Werte von actions_monitor.json auf der Seite ändern (Liste erlaubter Schlüssel mit Typ und Bereich, geprüft, Kopie in config_backups/ vor jedem Speichern, nie Tokens oder Geheimnisse; docs/SETTINGS.md).
  - Schaltflächen mit Relief, die aufleuchten und einsinken, SVG-Symbole mit Namen und Tooltip in 8 Sprachen, das Aussehen des Status-Dashboards, lebendige Balken und Zahlen (alles stoppt bei prefers-reduced-motion).
  - Optionale Ausgaben, standardmäßig aus, nur auf 127.0.0.1: /metrics (Prometheus), /api/outputs/grafana.json (Grafana JSON / Infinity), /api/outputs/dashboard.json (docs/OUTPUTS.md, Beispiel-Dashboard in docs/grafana/).
  - Neutrales Paket: deine Ökosysteme, Ziele und Profile liegen außerhalb (ecosystems_file, targets_file, profiles_file; tools_dir für die lokalen Signaturwerkzeuge); standardmäßig Englisch; Datei- und Ordnernamen englisch.
  BEIM UPDATE von 1.4.x: diese Namen haben sich geändert (die alten werden dort weiter gelesen, wo eine Datei existieren kann; geschrieben werden nur die neuen):
  leer_parte.py -> read_report.py          eventos.py -> events.py          parte_history.py -> report_history.py
  LOTE_GITHUB_ACTIONS.bat/.sh/.command -> BATCH_GITHUB_ACTIONS.bat/.sh/.command
  eventos_monitor.jsonl -> events_monitor.jsonl          eventos_estado.json -> events_state.json
  PARTE_CENTINELA_DIA_<day>.* -> SENTINEL_REPORT_DAY_<day>.*     PARTE_CENTINELA_<time>.txt -> SENTINEL_REPORT_<time>.txt     CANDIDATAS_RELEASE.txt -> RELEASE_CANDIDATES.txt
  <signed_dir>/lotes/lote_<time>.json -> <signed_dir>/batches/batch_<time>.json     parte_history_days -> report_history_days     monitor_y_centinela.zip -> github_actions_monitor.zip
  sentinel.audit_files: names of the A8 audit files (neutral defaults RECONCILIATION_TOTAL_*.txt, ROUNDS_MAP_2*.txt, ROUNDS_MAP_EXTRA_*.txt)
  ci_red.json and --export-status: unchanged (a contract).

NEU IN 1.4.2 (Verlauf: CHANGELOG.md)
  Fragt A2 nach dem letzten Run eines verdeckten Workflows, zählt ein laufender oder abgebrochener Run nicht mehr als gesehen (er könnte ein früheres Rot verdecken): Der Wächter
  holt die letzten abgeschlossenen Runs dieses Workflows und nimmt den ersten mit echtem Ergebnis (cancelled und skipped werden ignoriert). Gibt es keinen im Standardbranch, bleibt nur dieser Workflow unschlüssig.

NEU IN 1.4.1 (Verlauf: CHANGELOG.md)
  A2 meldet ein ganzes Repository nicht mehr als nicht aussagekräftig, nur weil die Lauf-Stichprobe voll ist: für jeden Workflow des Klons, der in der
  Stichprobe fehlt, wird bei GitHub der letzte Lauf genau dieses Workflows auf dem Standard-Branch abgefragt (nur lesend, gleiche Kontingent-Schranke wie A10,
  begrenzt durch sentinel.a2_resolve_max_calls_per_tick, Antworten gespeichert sentinel.a2_resolve_ttl_seconds). Rot zählt als rot; ein Workflow ohne Lauf auf dem
  Branch bleibt offen und das Panel nennt ihn.

NEU IN 1.4.0 (Verlauf: CHANGELOG.md)
  Bereich A11 "Bereitschaft": Release-Bereitschaft je Repository (CI des Standard-Branches und sein Commit, Version über der letzten Release, Build, Signatur, nächster
  Schritt), Gesundheit der Ökosysteme (Punktzahl nur aus echten Zählungen, zurückgehalten, wenn zu wenige Repositories Daten haben) und fixierte Versionen, die hinter ihrem
  Anbieter liegen (aus Versionsdateien der lokalen Klone gelesen, konfiguriert in sentinel.readiness.pins.sources). Nur lesend; nichts wird geschätzt.

NEU IN 1.3.0 (Verlauf: CHANGELOG.md)
  8 Sprachen in Seite, Kommandozeile, Ereignissen und Berichten; Sprachauswahl; Ökosysteme, Ziele und GitHub-Konto als Daten (github_owner, ecosystems_file,
  targets_file); optionaler Workspace mit ehrlichem reduziertem Modus; Urheberangabe und GPL-3.0-or-later in jeder Datei; LICENSE, NOTICE, AUTHORS;
  README und QUICKSTART in 8 Sprachen.
LIZENZ     GPL-3.0-or-later (siehe LICENSE und NOTICE). Copyright (C) 2026 JuanenRac (Electro Hobby 3D).

HILFE, ÜBER UND PRÜFUNGEN (1.6.4)
---------------------------------
Die Seite hat eine Hilfe-Taste (rundes ?) und eine Über-Taste (i); in der Konsole: --help-topics, --help-search, --about und --doctor; --demo zeigt die Seite mit erfundenen Daten. Die Lite-Ausgabe startet mit eigenem Banner und Fenstertitel (LITE, Port 8766, ohne Wächter); die vollständige meldet COMPLETE, Port 8765, Wächter aktiv. Der Hinweis auf neue Versionen lässt sich abschalten (Einstellungen > Grundlagen).

NEU IN 1.6.8 (Proxy wirklich geprüft; Verlauf: CHANGELOG.md)
  Der HTTPS-Proxy aus 1.6.7 wird gegen einen echten Proxy auf Port 443 geprüft (tools/manual_check_live.py proxy im Repository) und mit Tests, die die ganze Kette durchlaufen. Das
  Änderungsprotokoll ist bis 1.6.3 übersetzt (Hilfe > Änderungsprotokoll). Keine Einstellung ändert sich.

NEU IN 1.6.7 (HTTPS-Proxy auf dem Standardport; Verlauf: CHANGELOG.md)
  Neue Einstellung listen.proxy_public_host (standardmäßig leer): Der öffentliche Name eines HTTPS-Proxys auf Port 443, der Host und Origin ohne Port weiterleitet, wird unverändert
  akzeptiert, nur unter HTTPS, und lässt sich nur vom Rechner selbst ändern. Das Änderungsprotokoll ist für 1.6.7, 1.6.6 und 1.6.5 übersetzt (Hilfe > Änderungsprotokoll).

NEU IN 1.6.6 (Korrekturen am Netzwerkmodus und an act; Verlauf: CHANGELOG.md)
  Der Netzwerkmodus über HTTPS funktioniert von der Seite aus (der Origin folgt dem Schema der Sitzung); jede als sicher markierte Einstellung ändert nur der Rechner selbst; POST /api/access
  öffnet die Sitzung ohne Token in der Adresse; rote Leiste in den Einstellungen, wenn er auf allen Schnittstellen lauscht; Zähler verschluckter Fehler in --doctor und Info. act: Stopp gibt
  den Lauf frei und die Pipe wird geschlossen. Das Änderungsprotokoll ist in acht Sprachen übersetzt (Hilfe > Änderungsprotokoll).

NEU IN 1.6.5 (Integrität und Sicherheit; Verlauf: CHANGELOG.md)
  Stapel: Grüne CI heißt, der erforderliche Workflow lief durch (dispatch.required_ci), ein fehlgeschlagenes git fetch stoppt den Start, targets.json kann kein Werkzeug außerhalb des
  Werkzeugordners nennen und dry_run/ref nicht ändern, und finalize bietet nur Läufe an, deren Stapel die Commit-Prüfung aufgezeichnet hat (finalize --accept-legacy für alte Stapel). act bleibt
  im Arbeitsbereich und Stopp beendet den ganzen Baum. Netzwerkmodus: optionales HTTPS, Sperre nach falschen Token, nur IPv4. Webhook: keine Wiederholungen. Benachrichtigungen:
  max_per_hour zählt Nachrichten. --doctor warnt vor gefährlichen Kombinationen.
