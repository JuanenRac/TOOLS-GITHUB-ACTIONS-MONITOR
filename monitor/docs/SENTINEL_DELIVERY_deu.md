<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_DELIVERY.md) | [🇪🇸 Español](SENTINEL_DELIVERY_spa.md) | [🇫🇷 Français](SENTINEL_DELIVERY_fra.md) | [🇮🇹 Italiano](SENTINEL_DELIVERY_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](SENTINEL_DELIVERY_zho.md) | [🇯🇵 日本語](SENTINEL_DELIVERY_jpn.md) | [🇵🇹 Português](SENTINEL_DELIVERY_por.md)

# Der Auslieferungs-Wächter

Der fünfte Wächter, neben CI, Collab, Sicherheit und Lieferkette. Er liest, ohne etwas in GitHub zu schreiben, die neuesten Releases, die neuesten Tags, das CHANGELOG und die genannten Versionsdateien jedes Repositorys (über die API, ohne Klon) und meldet, was gebaut, aber nicht ausgeliefert wurde. Daraus macht er Alarme im Reiter Alarme (Herkunft Auslieferung). Er gehört zur Edition Complete und ist standardmäßig aus (`sentinels.delivery.enabled`); Lite hat keine Wächter.

## Was er meldet

| Signal | Alarm | Stufe | Standardmäßig an |
|---|---|---|---|
| Das CHANGELOG hat Einträge unter `[Unreleased]` und das neueste veröffentlichte Release ist älter als `sentinels.delivery.unreleased_days` Tage (14) | `release.unreleased_pending` | info | ja |
| Ein Versions-Tag, der neuer ist als das neueste veröffentlichte Release und kein eigenes Release hat (ein Entwurf gilt nicht als ausgeliefert) | `release.tag_without_release` | warning | ja |
| Das neueste veröffentlichte Release hat eine leere Beschreibung | `release.release_without_notes` | info | ja |
| Die Versionsdateien aus `version_files` und die erste Versionsüberschrift des CHANGELOG geben nicht alle dieselbe Version an (`1.2` und `1.2.0` sind gleich) | `release.version_mismatch` | warning | ja |
| Ein Repository schreibt eine ältere Version fest als das neueste Release des Repositorys, das einen gemeinsamen Vertrag liefert (die Pin-Tabellen aus `sentinel.readiness.pins.sources`, Art `pin_table`) | `release.ecosystem_drift` | warning | ja |
| Dem neuesten veröffentlichten Release fehlt eine Datei für eines der Muster aus `expected_assets` (zum Beispiel `*.zip`, `SHA256SUMS*`) | `release.assets_missing` | warning | ja |

Es gibt einen Alarm je Repository und Signal, mit den Zahlen und einigen Tags, Mustern oder Versionen in den Details. Jedes Signal lässt sich abschalten (`sentinels.delivery.signals.<Signal>.enabled`) und mit einer anderen Stufe versehen (`info`, `warning`, `error`, `critical`). Ein Repository ganz ohne veröffentlichtes Release wird von den Signalen über Releases nicht beurteilt: Es nutzt sie nicht. Vorabversionen und Entwürfe gelten nie als neuestes Release.

## Ein Besitzer für jeden Befund

Das Bereitschafts-Panel des Reiters Wächter (A11) ist eine Zeile je Repository aus lokalen Klonen; dieser Wächter erzeugt Alarme mit stabiler Kennung, Stummschaltungen, Ereignissen und eigenem Zyklus, über die API ohne Klon gelesen. Die Signale über die Workflows eines Repositorys gehören dem Lieferketten-Wächter und die über die GitHub-Einstellungen dem Sicherheits-Wächter: Nichts wird doppelt gemeldet. Das optionale Plugin „Releases“ der Roadmap ersetzt dieser Wächter.

## Was er nicht prüfen konnte

Ein Repository, das nicht gelesen werden kann (kein Zugriff, SSO nicht autorisiert, Kontingent verbraucht, eine Runde mit weniger Aufrufen, als ein Repository braucht), ist **kein** Alarm und **kein** Freibrief. Es steht im Status unter `unavailable`, mit Grund und Anzahl, und eine Stufe `ok` wird als `unknown` gezeigt, wenn das meiste Angesehene nicht gelesen werden konnte. Antwortet ein Repository nicht mehr, während es Alarme hat, bleiben sie eine Woche (markiert `unread_since`) und werden nie als behoben gemeldet. Eine Datei, die es nicht gibt (kein CHANGELOG an diesem Pfad, keine solche Versionsdatei), fehlt einfach. Die Pin-Tabellen werden einmal je Zyklus gelesen; eine nicht lesbare behält ihre Alarme und wird ebenfalls aufgeführt.

## Kosten

Eine Runde liest höchstens `sentinels.delivery.max_repos_per_tick` Repositorys (standardmäßig 10) und macht höchstens `sentinels.delivery.max_calls_per_tick` Aufrufe (60): einen für die Releases und einen für die Tags, einen für das CHANGELOG (mehr, wenn du mehrere Pfade nennst und die ersten nicht existieren) und einen je Versionsdatei. Ein abgeschaltetes Signal wird gar nicht gelesen. Die am längsten nicht gelesenen kommen zuerst, die mit offenem Alarm etwas früher; ein Zyklus alle `sentinels.delivery.refresh_seconds` (standardmäßig eine Stunde). Es gibt keine bedingten Anfragen: Die Kosten begrenzen diese Einstellungen, nicht eine Antwort 304. Der Wächter pausiert, solange das verbleibende Kontingent unter `sentinels.delivery.min_rate_remaining` liegt. Sein Zustand (`delivery_state.json`) hält die offenen Alarme, ein Neustart meldet also nichts erneut, und der erste Blick auf ein Repository schreibt kein Ereignis.

## Ereignisse, Benachrichtigungen und Bewertung

Ein neuer Befund schreibt das Ereignis `delivery_new`, ein geschlossener `delivery_fixed` (das Ereignis nennt `sentinel: delivery` und den Code des Alarms). Sie gehören zur Familie der Releases, nur Maintainer und Administratoren können sie wählen, und die Wahl des Wächters `ci` in den Benachrichtigungseinstellungen je Benutzer entscheidet, wer sie erhält; in keiner Standardliste von Ereignissen stehen sie. Die Metriken tragen `delivery_alerts`, `delivery_unreleased_repos`, `delivery_unreleased_days_max`, `delivery_repos_checked`, `delivery_repos_unreadable` und `delivery_calls_last_hour`. Die Bewertung nutzt sie nicht. Die API antwortet auf `GET /api/sentinel/delivery`, und der Reiter Alarme sowie `monitor_cli.py alerts --sentinel delivery` filtern danach.

## Die Einstellungen

Auf der Seite Einstellungen, Unterreiter Wächter, Block Auslieferung: `sentinels.delivery.enabled`, `sentinels.delivery.refresh_seconds`, `sentinels.delivery.max_repos_per_tick`, `sentinels.delivery.max_calls_per_tick`, `sentinels.delivery.min_rate_remaining`, `sentinels.delivery.repos`, `sentinels.delivery.unreleased_days`, `sentinels.delivery.unreleased_min_entries`, `sentinels.delivery.changelog_paths`, `sentinels.delivery.version_files`, `sentinels.delivery.expected_assets`, `sentinels.delivery.signals.unreleased_pending.enabled`, `sentinels.delivery.signals.unreleased_pending.level`, `sentinels.delivery.signals.tag_without_release.enabled`, `sentinels.delivery.signals.tag_without_release.level`, `sentinels.delivery.signals.release_without_notes.enabled`, `sentinels.delivery.signals.release_without_notes.level`, `sentinels.delivery.signals.version_mismatch.enabled`, `sentinels.delivery.signals.version_mismatch.level`, `sentinels.delivery.signals.ecosystem_drift.enabled`, `sentinels.delivery.signals.ecosystem_drift.level`, `sentinels.delivery.signals.assets_missing.enabled`, `sentinels.delivery.signals.assets_missing.level`.

## Was er nicht tut

Er schreibt nichts in GitHub (kein Tag, Release, Label, Pull Request oder Issue), veröffentlicht und signiert nichts, erstellt keine Vorschläge aus seinen Alarmen und liest den Inhalt keiner Datei außer dem CHANGELOG und den genannten Versionsdateien.
