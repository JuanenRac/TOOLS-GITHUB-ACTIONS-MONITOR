Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
GPL-3.0-or-later - see LICENSE

GITHUB-ACTIONS-MONITOR + WÄCHTER (Version 1.7.9)
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
KONFIG     actions_monitor.json (beim ersten Start aus assets/examples/actions_monitor.example.json erzeugt). Nützliche Schlüssel: github_owner (leer = das Konto von gh),
           language, ecosystems_file, targets_file, refresh_seconds, cold_refresh_seconds, max_workers, min_rate_remaining, sentinel.*
           ecosystems_file: gruppiert Repositories nach Namenspräfix (siehe assets/examples/ecosystems.example.json; "*" = alle Repositories). targets_file: Katalog der Builds für die
           Batch-Werkzeuge (siehe assets/examples/targets.example.json). profiles_file (assets/examples/profiles.example.json): Batch-Profile. Schlüssel, die mit "_" beginnen, sind Metadaten.
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

ÄNDERUNGSVERLAUF
  Alle Versionen, die neueste zuerst, stehen in CHANGELOG.md (in acht Sprachen in docs/CHANGELOG_*.md und in der Seite: Hilfe > Änderungsprotokoll).

HILFE, ÜBER UND PRÜFUNGEN (1.6.4)
---------------------------------
Die Seite hat eine Hilfe-Taste (rundes ?) und eine Über-Taste (i); in der Konsole: --help-topics, --help-search, --about und --doctor; --demo zeigt die Seite mit erfundenen Daten. Die Lite-Ausgabe startet mit eigenem Banner und Fenstertitel (LITE, Port 8766, ohne Wächter); die vollständige meldet COMPLETE, Port 8765, Wächter aktiv. Der Hinweis auf neue Versionen lässt sich abschalten (Einstellungen > Grundlagen).
