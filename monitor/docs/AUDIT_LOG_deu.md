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

Jede Zeile trägt `prev` (den Hash der vorigen Zeile) und `hash` (den Hash ihrer selbst und von `prev`). Eine später geänderte, entfernte oder eingefügte Zeile bricht die Kette, und `GET /api/audit-log` sagt, wo (`chain.broken_at`). Über `audit_log.max_mb` wird der alte Teil als `audit_actions.jsonl.1` aufbewahrt und die Kette in der neuen Datei fortgesetzt. Die Kette zeigt Manipulation; sie kann nicht verhindern, dass jemand mit Zugriff auf die Datei alles löscht, also bewahre eine Kopie dort auf, wo es zählt.

## Wer es liest

Ein Administrator (und die Person am Rechner, wenn es keinen Teammodus gibt). Ein Maintainer nur, wenn `audit_log.maintainers_can_read` an ist; sonst niemand. `GET /api/audit-log` antwortet mit den letzten 200 Zeilen und dem Zustand der Kette. Lite hat nichts davon.

## Einstellungen

Einstellungen, Tab Wächter, Block **Aktionsprotokoll**: `audit_log.enabled` (an), `audit_log.max_mb` (10) und `audit_log.maintainers_can_read` (aus).
