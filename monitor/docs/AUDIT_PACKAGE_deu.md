<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AUDIT_PACKAGE.md) | [🇪🇸 Español](AUDIT_PACKAGE_spa.md) | [🇫🇷 Français](AUDIT_PACKAGE_fra.md) | [🇮🇹 Italiano](AUDIT_PACKAGE_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](AUDIT_PACKAGE_zho.md) | [🇯🇵 日本語](AUDIT_PACKAGE_jpn.md) | [🇵🇹 Português](AUDIT_PACKAGE_por.md)

# Paket für den Prüfer

Was ein Prüfer braucht, um den Teammodus, die Netzwerkfreigabe und den Umgang mit Geheimnissen dieses Werkzeugs zu prüfen: eine Checkliste, die Befunde früherer Prüfungen mit ihrer Behebung und dem Test, der sie behoben hält, wie man die Tests ausführt und was bekannt offen ist.

## Sicherheits-Checkliste des Teammodus

- Der Teammodus (`auth.enabled`) ist standardmäßig aus; nur hinter HTTPS oder einem vertrauenswürdigen Proxy einschalten (`listen.trusted_proxy`).
- Bei eingeschaltetem Teammodus und offenem Netz startet der Monitor nicht, bevor es den ersten Administrator gibt.
- Bis dahin kommt nur der Rechner selbst hinein (dort wird der erste Administrator angelegt).
- Tokens für Skripte (`auth.allow_bearer`) sind standardmäßig aus; eine Sitzung braucht zum Schreiben das CSRF-Token.
- Der Prozess jedes Kontos antwortet nur seinem Supervisor (ein Schlüssel, den er beim Start erhält).
- Kein Geheimnis gelangt in das Protokoll oder in die Antworten der API; die Einstellungsdatei wird unter einer Sperre gespeichert.
- Jede Anfrage, die den Monitor verlässt (Benachrichtigungen, OpenTelemetry, Runner-Exporter), folgt derselben Regel: keine private Adresse und keine Weiterleitung auf eine.

## Befunde, Behebungen und Tests

| Befund | Behebung | Test |
|---|---|---|
| Bei Teammodus ohne Benutzer waren alle Routen für das Netz offen | Nur der Rechner selbst kommt hinein, bis es den ersten Administrator gibt; der Netzmodus startet ohne ihn nicht | `test_184_audit_auth.py::FirstAdministratorWindow, test_185_bootstrap_start.py` |
| Der Prozess eines Kontos umging die Prüfungen des Teammodus | Er verlangt bei jeder Anfrage den Schlüssel seines Supervisors | `test_184_audit_auth.py::ChildAnswersOnlyToItsSupervisor` |
| Das Speichern der Einstellungen lief nach einem Timeout ohne die Dateisperre weiter | Das Speichern wird mit einer Meldung abgelehnt, wenn die Sperre zehn Sekunden belegt bleibt | `test_184_audit_hardening.py::ConfigurationLock` |
| Der Befehl des Wächters konnte eine Shell mit Argumenten sein | Der Befehl ist eine Liste, deren erstes Wort der volle Pfad eines Programms ist, das keine Shell ist, ohne Steuerzeichen | `test_184_audit_hardening.py::NotifyCommand` |
| Tokens für Skripte (Bearer) waren standardmäßig an | Standardmäßig aus; nur ein echtes true schaltet sie ein | `test_184_audit_hardening.py::ScriptTokens` |
| Der Feed für die KIs wurde von allen Konten geteilt, und Aktualisierung, Quittierung und Meldungsgrenze konnten sich überholen | Ein Feed je Konto; Aktualisierung, Quittierung und Status nehmen dieselbe Sperre; die Grenze wird in einem gesperrten Schritt reserviert | `test_184_audit_feed.py (OneStepAtATime, CapOfTheNotices)` |
| Die Pause des Hooks eines KI-Werkzeugs wurde nicht in einem Schritt reserviert; ein Runner-Exporter konnte den Monitor umleiten; nie zurückkehrende GitHub-Aufrufe häuften sich | Die Pause wird mit einer Sperre gehalten; Weiterleitungen werden geprüft und begrenzt; verlassene Aufrufe werden gezählt und begrenzt (`watchdog_max_abandoned`) | `test_184_audit_robustness.py (HookCooldown, Exporter, AbandonedCalls)` |
| Ein Name mit Zeilenumbruch am Ende bestand die Prüfungen von IDs, Repositories und Schlüsseln | Jede Prüfung endet am Ende des Textes (`\Z`) | `test_184_audit_anchors.py` |
| Der OpenTelemetry-Export folgte nicht der Regel für ausgehende Anfragen; der Proxy galt nicht als Vertrauensgrenze; das Escaping der Seite hatte keinen Test | Der Export geht durch dieselbe Wache (keine private Adresse, keine Weiterleitung); die Grenze steht in der Hilfe; ein Test hält jeden Text der API maskiert | `test_184_audit_network.py (Collector, ProxyIsAFrontierOfTrust, PageEscaping)` |
| Zwei Monitore konnten auf einem Port lauschen; openssl von Git for Windows wurde nicht gefunden; absichtlich verschluckte Fehler ließen keine Spur ihrer Herkunft | Der Port wird exklusiv belegt und ein zweiter Monitor startet nicht; openssl wird dort gesucht, wo Git for Windows es ablegt; jeder verschluckte Fehler schreibt eine Zeile mit Art und Ort | `test_185_startup.py (OnePerPort, WhereIsOpenssl), test_185_degraded.py` |
| Läufe ohne Dauer (über GraphQL gelesen) ließen den Wächter in jedem Zyklus scheitern | Eine fehlende Dauer zählt als null | `test_186_unfinished_rows.py` |

## Tests ausführen

Im Ordner `monitor/`: `python -m unittest discover -s tests`. Die Tests brauchen weder Netz noch GitHub-Token. Die Browser-Tests laufen, wenn Edge, Chrome oder Chromium installiert ist (oder mit `MONITOR_BROWSER_TESTS=1`). Die Dateien der Tabelle liegen in `monitor/tests/`.

## Bekannte Grenzen

- Der Proxy der Umgebung (`network.use_proxy`, standardmäßig aus) löst Namen selbst auf: die Prüfung des Namens geschieht davor. Die starke Garantie muss vom Netz kommen (eine Firewall, die private Adressen ablehnt).
- Windows kann eine Datei nicht allein durch Rechte privat machen: Die Geheimnisse werden, wo das System es bietet, mit dem Schlüssel des Benutzers verschlüsselt.
- Die Tests beweisen nichts über ein echtes GitHub, einen echten Proxy oder einen echten Mailserver: Sie nutzen lokale Doubles.
