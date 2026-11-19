<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_SUPPLY.md) | [🇪🇸 Español](SENTINEL_SUPPLY_spa.md) | [🇫🇷 Français](SENTINEL_SUPPLY_fra.md) | [🇮🇹 Italiano](SENTINEL_SUPPLY_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](SENTINEL_SUPPLY_zho.md) | [🇯🇵 日本語](SENTINEL_SUPPLY_jpn.md) | [🇵🇹 Português](SENTINEL_SUPPLY_por.md)

# Der Lieferketten-Wächter

Der vierte Wächter, neben CI, Collab und Sicherheit. Er liest, ohne etwas auf GitHub zu schreiben, die Workflow-Dateien jedes Repositorys (`.github/workflows`, über die API, ohne Klon) und meldet, was einem verschobenen Tag oder einem Außenstehenden erlaubt, mit Token und Code des Repositorys zu handeln. Daraus macht er Meldungen des Tabs Meldungen (Herkunft Lieferkette). Er gehört zur Complete-Edition und ist standardmäßig aus (`sentinels.supply.enabled`); Lite hat keine Wächter.

Er hat einen eigenen Eintrag in der Gruppe Sentinel des Menüs, **Lieferketten-Sentinel** (Adresse `#sentinel-supply`), sichtbar, solange der Sentinel an ist: ein Panel mit den offenen Befunden jedes Repositorys, dem Stand seines Zyklus und dem, was nicht gelesen werden konnte; das Zeichen des Eintrags zählt die Fehler.

## Was er meldet

| Signal | Meldung | Stufe | Standardmäßig an |
|---|---|---|---|
| Ein `uses:` einer Action oder eines wiederverwendbaren Workflows ohne Bindung an einen vollständigen Commit-SHA (der Eigentümer kann den Tag verschieben) | `actions.supply.unpinned` | warning | ja |
| Ein `uses:`, das einem Branch folgt, der sich von selbst bewegt (`@main`, `@master`...): schlimmer als ein Tag | `actions.supply.mutable_ref` | warning | ja |
| Ein Workflow mit `permissions: write-all` | `actions.supply.permissions_wide` | warning | ja |
| Ein Workflow ohne `permissions:`-Block (das Token erhält die weitere Standardberechtigung) | `actions.supply.permissions_missing` | warning | ja |
| `pull_request_target` zusammen mit dem Checkout des Codes des Pull Requests | `actions.supply.pr_target_checkout` | error | ja |

Es gibt eine Meldung pro Repository und Signal, mit der Zahl der Funde, den betroffenen Dateien und einigen Beispielen (dem Namen einer Action) in den Details. Jedes Signal lässt sich abschalten (`sentinels.supply.signals.<Signal>.enabled`) und auf eine andere Stufe setzen (`info`, `warning`, `error`, `critical`). Ein `uses:` auf einen Workflow desselben Repositorys ist kein Drittanbieter und wird ausgelassen.

## Eine einzige Quelle der Wahrheit

Er hat keine eigenen Regeln: Die Funde stammen vom Workflow-Linter (`bin/lint_workflows.py`, demselben wie im Tab Wächter und auf der Kommandozeile); hier sind nur `unpinned_uses`, `permissions` und `pr_target` aktiv, alle anderen Regeln bleiben aus. Insbesondere ist die Regel aus, die nach in Dateien geschriebenen Geheimnissen sucht, sodass **der Wert eines Geheimnisses nie gelesen, gespeichert oder angezeigt wird**. Die Einstellungen `lint.own_owners` und `lint.unpinned_own` entscheiden weiter, wie eine Action des eigenen Kontos behandelt wird, und ein Kommentar `# monitor-lint: ignore REGEL` in einem Workflow bringt einen Fund an Ort und Stelle zum Schweigen.

## Ein Besitzer pro Fund

`security.workflow_write` (Sicherheits-Wächter) ist die Standardberechtigung des Repositorys, eine Einstellung von GitHub; die Signale hier betreffen den Inhalt jeder Workflow-Datei, sodass ein Repository denselben Fund nie von beiden meldet. Das Lint-Panel des Tabs Wächter bleibt ein Panel; die Meldungen des Tabs Meldungen zu diesen Signalen kommen nur von hier.

## Was er nicht prüfen konnte

Ein Repository, dessen Workflows sich nicht lesen lassen (kein Zugriff, SSO nicht autorisiert, Kontingent verbraucht, Ordner mit zu vielen Dateien), ist **keine** Meldung und **kein** Gesundheitszeugnis. Es steht im Status unter `unavailable`, mit Grund und Anzahl, und eine Stufe `ok` wird als `unknown` gezeigt, wenn das meiste des Betrachteten nicht lesbar war. Antwortet ein Repository mit Meldungen nicht mehr, bleiben sie eine Woche (mit `unread_since` markiert) und werden nie als behoben angekündigt. Ein Repository ohne Ordner `.github/workflows` wird gelesen und hat einfach nichts zu melden. Ein Repository, dessen Lesevorgänge weiter scheitern, wartet 5 Minuten, 30 Minuten und dann 6 Stunden bis zum nächsten Versuch.

## Kosten

Eine Runde liest höchstens `sentinels.supply.max_repos_per_tick` Repositories (standardmäßig 10) und macht höchstens `sentinels.supply.max_calls_per_tick` Aufrufe (60): einen zum Auflisten der Workflows eines Repositorys und einen weiteren für jede neue oder geänderte Datei, denn eine Datei, deren SHA sich nicht änderte, wird nie erneut gelesen. Zuerst kommen die am längsten nicht gelesenen, etwas früher die mit offener Meldung; ein Zyklus alle `sentinels.supply.refresh_seconds` (standardmäßig eine Stunde). Der Wächter pausiert, solange das verbleibende Kontingent unter `sentinels.supply.min_rate_remaining` liegt. Sein Zustand (`supply_state.json`) hält die offenen Meldungen, ein Neustart kündigt also nichts erneut an, und der erste Blick auf ein Repository schreibt kein Ereignis. `sentinels.supply.max_files_per_repo` begrenzt die in einem Repository gelesenen Dateien; ein Repository darüber wird nur teilweise gelesen und als teilweise gezählt. Eine Runde beginnt außerdem nach `sentinels.supply.deadline_s` Sekunden keine neuen Repositorys mehr (Standard 30; 0 = kein Limit): Die nicht erreichten warten auf die nächste Runde, und der Status führt sie namentlich als `unchecked` (mit `round_cut`) auf, statt sie als null Alarme zu zählen.

## Einen Fund ignorieren

`sentinels.supply.ignore` nimmt Muster `Repository:Datei:Regel` (mit `*` für beliebig), die die Regel des Linters nennen, zum Beispiel `meinrepo:release.yml:unpinned_uses`; `unpinned_uses` ist die Regel hinter `unpinned` und `mutable_ref`, `permissions` die hinter den beiden Berechtigungssignalen. Die Muster von `lint.ignore` gelten hier nicht.

`sentinels.supply.ignore_uses` nimmt Namen `Eigentümer/Repository` (mit `*` für beliebig, etwa `other-org/*`) von Actions oder wiederverwendbaren Workflows einer anderen privaten Organisation, die der Zugang nicht sehen kann und deren Referenz der Monitor nicht beurteilen kann: Ihre nicht fixierten oder beweglichen Referenzen bleiben aus den Befunden heraus und werden im Status getrennt als `uses_left_out` gezählt, also weder auf Verdacht gemeldet noch versteckt.

## Ereignisse, Benachrichtigungen und Bewertung

Ein neuer Fund schreibt das Ereignis `security_new`, ein geschlossener `security_fixed` (das Ereignis trägt `sentinel: supply` und den Code der Meldung); das Feld Sicherheit der Benachrichtigungseinstellungen jedes Benutzers und die Kanäle entscheiden also, wer es erfährt. Beim ersten Blick auf ein Repository wird nichts angekündigt. Die Metriken enthalten `supply_alerts`, `supply_findings`, `supply_penalty` (informativ: `sentinels.supply.penalty.per_finding`, 2, und `cap_per_repo`, 10, werden aus der Datei gelesen), `supply_repos_checked`, `supply_repos_unreadable` und `supply_calls_last_hour`. Die Bewertung nutzt den Abzug nicht. Die API antwortet auf `GET /api/sentinel/supply`, und der Tab Meldungen sowie `monitor_cli.py alerts --sentinel supply` filtern danach.

## Die Einstellungen

Auf der Seite Einstellungen, Unter-Tab Wächter, Block Lieferkette: `sentinels.supply.enabled`, `sentinels.supply.refresh_seconds`, `sentinels.supply.max_repos_per_tick`, `sentinels.supply.max_calls_per_tick`, `sentinels.supply.max_files_per_repo`, `sentinels.supply.min_rate_remaining`, `sentinels.supply.repos`, `sentinels.supply.ignore`, `sentinels.supply.ignore_uses`, `sentinels.supply.signals.unpinned.enabled`, `sentinels.supply.signals.unpinned.level`, `sentinels.supply.signals.mutable_ref.enabled`, `sentinels.supply.signals.mutable_ref.level`, `sentinels.supply.signals.permissions_wide.enabled`, `sentinels.supply.signals.permissions_wide.level`, `sentinels.supply.signals.permissions_missing.enabled`, `sentinels.supply.signals.permissions_missing.level`, `sentinels.supply.signals.pr_target_checkout.enabled`, `sentinels.supply.signals.pr_target_checkout.level`.

## Was er nicht tut

Er schreibt nicht auf GitHub (kein Pull Request, kein Label, kein Issue), schlägt keinen SHA zum Festnageln einer Action vor und liest den Wert keines Geheimnisses.
