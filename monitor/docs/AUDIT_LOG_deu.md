<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](AUDIT_LOG.md) | [🇪🇸 Español](AUDIT_LOG_spa.md) | [🇫🇷 Français](AUDIT_LOG_fra.md) | [🇮🇹 Italiano](AUDIT_LOG_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](AUDIT_LOG_zho.md) | [🇯🇵 日本語](AUDIT_LOG_jpn.md) | [🇵🇹 Português](AUDIT_LOG_por.md)

# Das Aktionsprotokoll

Nur Complete, standardmäßig an. Neben dem Protokoll der Zugriffe (Anmeldungen, Sperren, Ablehnungen) führt der Monitor ein Protokoll der **Aktionen**: wer was wann und auf welchem Konto geändert hat. Eine Änderung der Einstellungen, eine Stummschaltung oder ihre Aufhebung, eine Änderung von Benutzern, Passwörtern, Benachrichtigungseinstellungen oder Zugangsdaten. Es ist je eine JSON-Zeile in `logs/audit_actions.jsonl`, nie neu geschrieben.

## Was eine Zeile sagt

`at`, `action` (ein schlichtes Wort wie `settings_change` oder `alert_mute`), `user`, `role`, `account`, `target` (eine kurze Kennung: ein Einstellungsname, ein Meldungscode), `result` (`ok`, `denied` oder `error`) und bei Bedarf `details`. **Nie kommt ein Wert oder ein Geheimnis hinein**: Eine Änderung der Einstellungen schreibt die Namen der Einstellungen, nicht ihre Werte; ein Schlüssel, dessen Name nach Geheimnis aussieht (token, password, key, cookie, authorization, session...), wird verworfen; jeder Text wird wie die Hinweise für KIs bereinigt und auf 200 Zeichen gekürzt.

## Die Kette

Jede Zeile trägt `prev` (den Hash der vorigen Zeile) und `hash` (den Hash ihrer selbst und von `prev`). Eine später geänderte, entfernte oder eingefügte Zeile bricht die Kette, und `GET /api/audit-log` sagt, wo (`chain.broken_at`). Über `audit_log.max_mb` wird der alte Teil als `audit_actions.jsonl.1` aufbewahrt und die Kette in der neuen Datei fortgesetzt. Die Kette zeigt Manipulation; sie kann nicht verhindern, dass jemand mit Zugriff auf die Datei alles löscht, also bewahre eine Kopie dort auf, wo es zählt. Bei mehreren Konten hat jedes Konto seine eigene Datei in seinem Ordner (`accounts/<id>/audit_actions.jsonl`) und die API antwortet nur mit den Zeilen des angefragten Kontos; die vor dieser Änderung geschriebenen Zeilen bleiben in der alten gemeinsamen Datei. Die Prüfung umfasst auch die rotierte Datei und die Verbindung zwischen beiden (`segments`, und `segment`, wenn eine Zeile gebrochen ist); `complete: false` bedeutet, dass die Kette nicht an ihrem ersten Glied beginnt, weil eine rotierte Datei durch eine spätere Rotation ersetzt oder gelöscht wurde. Mehrere Prozesse können dieselbe Datei beschreiben: Jede Zeile wird unter einer Sperre an die letzte wirklich darin stehende Zeile gekettet. Die Kette hat keinen geheimen Schlüssel: Wer die Datei schreiben kann, kann ihre neuesten Zeilen abschneiden oder sie mit neuen Hashes neu schreiben; wenn sie als Beweis dienen soll, bewahre eine Kopie woanders auf.

## Wer es liest

Ein Administrator (und die Person am Rechner, wenn es keinen Teammodus gibt). Ein Maintainer nur, wenn `audit_log.maintainers_can_read` an ist; sonst niemand. `GET /api/audit-log` antwortet mit den letzten 200 Zeilen und dem Zustand der Kette. Lite hat nichts davon.

## Einstellungen

Einstellungen, Tab Wächter, Block **Aktionsprotokoll**: `audit_log.enabled` (an), `audit_log.max_mb` (10) und `audit_log.maintainers_can_read` (aus).
