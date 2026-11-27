<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AUDIT_LOG.md) | [🇪🇸 Español](AUDIT_LOG_spa.md) | [🇫🇷 Français](AUDIT_LOG_fra.md) | [🇮🇹 Italiano](AUDIT_LOG_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](AUDIT_LOG_zho.md) | [🇯🇵 日本語](AUDIT_LOG_jpn.md) | [🇵🇹 Português](AUDIT_LOG_por.md)

# Das Aktionsprotokoll

Nur Complete, standardmäßig an. Neben dem Protokoll der Zugriffe (Anmeldungen, Sperren, Ablehnungen) führt der Monitor ein Protokoll der **Aktionen**: wer was wann und auf welchem Konto geändert hat. Eine Änderung der Einstellungen, eine Stummschaltung oder ihre Aufhebung, eine Änderung von Benutzern, Passwörtern, Benachrichtigungseinstellungen oder Zugangsdaten. Es ist je eine JSON-Zeile in `logs/audit_actions.jsonl`, nie neu geschrieben. Er hält auch fest, was bestätigt wird: eine Aktion auf GitHub (erneut ausführen, abbrechen, auslösen, mergen), ein Lauf mit `act`, das Speichern oder Löschen des gespeicherten Tokens, eine Änderung des Arbeitsmodus, eine durch die Erkennung hinzugefügte Gruppe, eine hinzugefügte Lehre, ein jetzt geschriebener Bericht, die Anmeldung des Kontos und die Aktionen der KI. Die Zeile nennt, was bestätigt wurde, und das Ergebnis, nie den Inhalt der Anfrage. Jede POST-Route wird entweder aufgezeichnet oder mit Begründung als ausgenommen geführt, und ein Test schlägt fehl, wenn eine neue Route keines von beidem ist.

## Was eine Zeile sagt

`at`, `action` (ein schlichtes Wort wie `settings_change` oder `alert_mute`), `user`, `role`, `account`, `target` (eine kurze Kennung: ein Einstellungsname, ein Meldungscode), `result` (`ok`, `denied` oder `error`) und bei Bedarf `details`. **Nie kommt ein Wert oder ein Geheimnis hinein**: Eine Änderung der Einstellungen schreibt die Namen der Einstellungen, nicht ihre Werte; ein Schlüssel, dessen Name nach Geheimnis aussieht (token, password, key, cookie, authorization, session...), wird verworfen; jeder Text wird wie die Hinweise für KIs bereinigt und auf 200 Zeichen gekürzt.

## Die Kette

Jede Zeile trägt `prev` (den Hash der vorigen Zeile) und `hash` (den Hash ihrer selbst und von `prev`). Eine später geänderte, entfernte oder eingefügte Zeile bricht die Kette, und `GET /api/audit-log` sagt, wo (`chain.broken_at`). Über `audit_log.max_mb` wird der alte Teil als `audit_actions.jsonl.1` aufbewahrt und die Kette in der neuen Datei fortgesetzt. Die Kette zeigt Manipulation; sie kann nicht verhindern, dass jemand mit Zugriff auf die Datei alles löscht, also bewahre eine Kopie dort auf, wo es zählt. Bei mehreren Konten hat jedes Konto seine eigene Datei in seinem Ordner (`accounts/<id>/audit_actions.jsonl`) und die API antwortet nur mit den Zeilen des angefragten Kontos; die vor dieser Änderung geschriebenen Zeilen bleiben in der alten gemeinsamen Datei. Die Prüfung umfasst auch die rotierte Datei und die Verbindung zwischen beiden (`segments`, und `segment`, wenn eine Zeile gebrochen ist); `complete: false` bedeutet, dass die Kette nicht an ihrem ersten Glied beginnt, weil eine rotierte Datei durch eine spätere Rotation ersetzt oder gelöscht wurde. Mehrere Prozesse können dieselbe Datei beschreiben: Jede Zeile wird unter einer Sperre an die letzte wirklich darin stehende Zeile gekettet. Die Kette hat keinen geheimen Schlüssel: Wer die Datei schreiben kann, kann ihre neuesten Zeilen abschneiden oder sie mit neuen Hashes neu schreiben; wenn sie als Beweis dienen soll, bewahre eine Kopie woanders auf. Mit `audit_log.keep_generations` (standardmäßig 5, 1 bis 20) bleiben die alten Teile als `.1`, `.2` und so weiter erhalten: Die neueste ist `.1`, Älteres als diese Anzahl Dateien wird gelöscht, und `GET /api/audit-log` prüft die Kette über alle.

## Wer es liest

Ein Administrator (und die Person am Rechner, wenn es keinen Teammodus gibt). Ein Maintainer nur, wenn `audit_log.maintainers_can_read` an ist; sonst niemand. `GET /api/audit-log` antwortet mit den letzten 200 Zeilen und dem Zustand der Kette. Lite hat nichts davon. Ein Viewer wird schon an der Tür abgewiesen. Das Ausschalten des Protokolls schreibt seine eigene letzte Zeile (die Änderung, die es ausgeschaltet hat). Eine Zeile, die nicht geschrieben werden kann, wird gezählt: `write_failures` und `last_write_error_at` in der Antwort sowie ein Degradationshinweis. Fehlgeschlagene Änderungen des eigenen Passworts werden hier nicht geschrieben (das Zugriffsprotokoll behält sie).

## Einstellungen

Einstellungen, Tab Wächter, Block **Aktionsprotokoll**: `audit_log.enabled` (an), `audit_log.max_mb` (10) und `audit_log.maintainers_can_read` (aus). `audit_log.keep_generations` (5) ist die Zahl der aufbewahrten rotierten Dateien. `audit_log.required` (aus) lehnt die Aktionen, die protokolliert werden müssen (die Bestätigungen von Aktionen auf GitHub, der Modus, die Stummschaltungen, die Zugangsdaten...), mit 503 ab, solange das Protokoll nicht geschrieben werden kann; die Einstellungen bleiben offen, damit man es beheben kann.

Eine jetzt erstellte Sicherung (`POST /api/ops/backup`) und die Bereinigung auf Anforderung (`POST /api/ops/purge`, auch ein Probelauf) werden als `backup_run` und `purge_run` protokolliert: Die Zeile nennt, wer sie verlangt hat, und das Ergebnis, nie den Inhalt der Sicherung.

## Signierte Prüfpunkte, Bereinigung und Export

Mit `audit_checkpoints.enabled` wird die Kette mit einem Schlüssel der Installation signiert; das Protokoll lässt sich bereinigen und anderswohin kopieren: siehe [COMPLIANCE_deu.md](COMPLIANCE_deu.md). Unter `retention.legal_hold` wird nicht rotiert oder bereinigt.
