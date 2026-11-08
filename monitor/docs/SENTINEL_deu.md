<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL.md) | [🇪🇸 Español](SENTINEL_spa.md) | [🇫🇷 Français](SENTINEL_fra.md) | [🇮🇹 Italiano](SENTINEL_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](SENTINEL_zho.md) | [🇯🇵 日本語](SENTINEL_jpn.md) | [🇵🇹 Português](SENTINEL_por.md)

# Der Wächter und seine Prüfungen A1-A13

Der **Wächter** ist die zweite Hälfte der vollständigen Ausgabe. Der *Monitor* zeigt, was gerade läuft und was fehlschlägt; der *Wächter* prüft das ganze Konto alle paar Minuten und beantwortet eine andere Frage: **was braucht einen Menschen**. Er liest GitHub (schreibt nie hinein), führt auf diesem Rechner eine kurze Chronik und macht aus allem dreizehn nummerierte Prüfungen, **A1 bis A13**, mit je einer Ampel.

**Die Lite-Ausgabe enthält ihn nicht.** `MONITOR_LITE_GITHUB_ACTIONS` (Port 8766) hat keinen Wächter: das Modul wird nicht einmal importiert, seine Endpunkte antworten mit 404. Die vollständige Ausgabe (`MONITOR_GITHUB_ACTIONS`, Port 8765) startet ihn selbst; abschalten mit `sentinel.enabled` (Einstellungen > Wächter). Beide Ausgaben nutzen dieselbe Regel für „rot auf main“ (A2), ihre Zahlen stimmen also überein.

## Start und Kosten

Er startet mit dem vollständigen Monitor und läuft im selben Prozess in einem eigenen Thread mit eigenem Budget an GitHub-Aufrufen (`sentinel.budget_per_hour`, standardmäßig 600, und `sentinel.max_calls_per_tick`). Liegt das GitHub-Kontingent unter `sentinel.min_rate_remaining`, fragt er nicht mehr und die Seite meldet die Pause wegen Kontingent. Nichts davon schreibt auf GitHub.

## Dateien, die er schreibt (neben dem Monitor, nie veröffentlicht)

| Datei | Inhalt |
|---|---|
| `ci_red.json` | Schema 2: je Repository die roten Workflows und die Stunden, die ein Release auf seine Signatur wartet. Stabiler Vertrag für andere Werkzeuge, siehe `CI_RED_SCHEMA_deu.md` und `CI_RED_BRIDGE_deu.md`. Ort: `sentinel.ci_red_file`. |
| `sentinel_history.json` | die Tagessummen (Alarme, Rot, Kandidaten) für Trends und „neu seit gestern“. |
| `sentinel_cache.json` | die letzten Antworten der langsamen Lesevorgänge, damit ein Neustart nicht alles neu erfragt. |
| `events_monitor.jsonl`, `events_state.json` | der Ereignisstrom (was rot wurde, was behoben wurde) mit stabilem `code` je Ereignis. |
| `SENTINEL_REPORT_*.txt` | der Tagesbericht, im Audit-Ordner gespeichert, wenn es ihn gibt. |

## So liest man ihn

Jede Prüfung hat eine von fünf Stufen: **ok** (nichts zu tun), **info** (gut zu wissen), **warn** (bald ansehen), **bad** (jetzt handeln) und **unknown** (noch nicht prüfbar: **unknown wird nie grün gezeigt**). Der Bericht oben im Reiter fasst alles in wenigen Zeilen zusammen; die Details öffnen sich je Prüfung. Ein im Monitor herausgefiltertes Repository wird nicht geprüft.

## Die Prüfungen

| Prüfung | Was geprüft wird und die genaue Regel | Wo einstellbar | Stufe und was zu tun ist |
|---|---|---|---|
| **A1** | **Builds.** Ein Run, der länger als das Limit läuft oder wartet, ist *hängend*. Offene Issues mit dem Label `build-failed` oder `build-stuck` werden ebenfalls gelistet. Runs des Ereignisses `dynamic` (Dependabot-Interna) werden ignoriert. | `stuck_minutes` | **bad**, wenn etwas hängt oder ein Issue offen ist. Run öffnen, abbrechen oder neu starten; Issue nach der Behebung schließen. |
| **A2** | **Rotes CI.** Je Workflow-Datei der LETZTE ABGESCHLOSSENE Run auf dem STANDARD-Branch: rot, wenn er fehlschlug (`failure`, `timed_out`, `startup_failure`, `action_required`). Runs mit `cancelled`, `skipped`, `neutral` oder `stale`, laufende Runs und Runs anderer Branches sagen nichts und verdecken nie ein älteres Rot. *Serie* = aufeinanderfolgende Rots. Ist die Run-Liste eines Repositorys so lang wie die angeforderte Stichprobe, kann ein Workflow dahinter verschwinden: der Wächter fragt GitHub nach dem letzten Run jedes solchen Workflows. | `runs_per_repo`, `cold_runs_per_repo`, `sentinel.a2_full_sample_unknown`, `sentinel.a2_resolve_max_calls_per_tick`, `sentinel.a2_resolve_ttl_seconds` | **bad**, wenn ein Workflow rot ist; **unknown** (nie grün), wenn ein Repository keine Run-Daten hat oder ein Workflow nicht aufgelöst werden konnte. Workflow beheben oder neu starten; die Lite-Ausgabe zeigt dieselbe Zahl, als ungefähr markiert, weil sie den Standard-Branch rät. |
| **A3** | **Sicherheitsalarme.** Offene CodeQL-, Dependabot- und Secret-Scanning-Alarme je Repository mit Schweregrad und wie viele seit dem letzten Tag der Chronik neu sind. | `sentinel.alerts_hot_seconds`, `sentinel.alerts_cold_seconds` | **bad** bei jedem Secret-Alarm oder kritischen/hohen Alarm; **warn** bei jedem anderen; **unknown** beim Laden. Zuerst ein geleaktes Secret rotieren, dann den Rest aktualisieren oder verwerfen. |
| **A4** | **Dependabot-Pull-Requests.** Offene PRs von Dependabot mit Alter, *Major*-Sprung und Merge-Konflikt; PRs anderer Personen werden nur gezählt. | `sentinel.stale_pr_days` (7) | **warn**, wenn einer ein Major-Sprung ist oder kollidiert; **info**, wenn es nur PRs gibt. Grüne mergen; kollidierende rebasen oder schließen. |
| **A5** | **Releases.** (a) *Kandidat*: mindestens `candidate_min_entries` Einträge unter `[Unreleased]` im CHANGELOG und das letzte Release älter als `candidate_days` (oder keines). (b) Ein *grüner Build* eines Release-Workflows, neuer als das letzte Release. (c) *Wartet auf Signatur*: ein grüner Build älter als `pending_sign_hours`, nicht signiert und veröffentlicht; eine Signatur zählt nur, wenn sie gegen den öffentlichen Schlüssel des Ökosystems prüft. | `sentinel.candidate_days` (2), `sentinel.candidate_min_entries` (1), `sentinel.skip_candidate_prefixes`, `sentinel.pending_sign_hours` (24), `sentinel.require_verified_signature` | **warn** bei Kandidat oder offener Signatur; **info** bei grünen, noch nicht veröffentlichten Builds. Release schneiden oder Build signieren. |
| **A6** | **Hygiene.** Je Repository: Ruleset `protect-main` ist ACTIVE, Label `dependencies` existiert, die geforderten Dateien existieren (standardmäßig README, LICENSE, CHANGELOG, SECURITY), SHA-Pinning ist Pflicht, `allowed_actions` ist `selected`, und kein geplanter Workflow wurde von GitHub deaktiviert. | `sentinel.required_files`, `sentinel.hygiene_seconds` | **warn**, wenn ein Repository ein Problem hat; **info**, solange einige nicht geprüft sind. Jedes Problem nennt die Abhilfe. |
| **A7** | **Nutzung.** Actions-Minuten der letzten 24 Stunden und 7 Tage je Repository und Ökosystem, das verbleibende API-Kontingent und das *Budget* je Ökosystem: **ok** unter 80 %, **warn** ab 80 %, **over** ab 100 % der Obergrenze. | `sentinel.min_rate_remaining` (800), `sentinel.minutes_budget`, `sentinel.minutes_budget_period` (7d) | **warn**, wenn das Kontingent unter dem Limit liegt oder ein Budget 80 % erreicht. Aktualisierung verlangsamen oder lange Workflows kürzen. |
| **A8** | **Runden.** Liest die Audit- und Runden-Dateien im Audit-Ordner (die Muster von `sentinel.audit_files`) und zeigt ihren Stand. Leer, wenn es keinen Audit-Ordner gibt. | `sentinel.audit_files.*`, `audit_dir` | Nur **info**. Nichts zu tun. |
| **A9** | **Roadmaps.** Ob die GitHub-Projects-Boards der Ökosysteme *lebendig* sind: in den letzten 8 Tagen abgeglichen und nicht älter als ihre Definitionen. Braucht den Scope `read:project` von `gh`; ohne ihn arbeitet der Reiter mit den Definitionen und sagt, was fehlt. | (fixed: 8 days) | **warn**, wenn ein Board veraltet ist oder nie abgeglichen wurde; **unknown**, wenn nicht konfiguriert. |
| **A10** | **Oberfläche von Actions und Releases.** Fünfundzwanzig reine Lese-Prüfungen auf den Klonen und wenige Kaltaufrufe, in der Tabelle unten. Jede hat einen Schalter und, wo sinnvoll, einen Schwellwert. | `sentinel.surface.*` | Je Prüfung, siehe unten. Pausiert bei knappem Kontingent (der Bericht sagt es). |
| **A11** | **Release-Bereitschaft, Ökosystem-Gesundheit und Pins.** Bereitschaft je Repository (Einträge, CI, Version, Build, Signatur, nächster Schritt); eine Gesundheitsnote 0-100 je Ökosystem, die gewichtete Abzüge für Rot, Hänger, Secrets, hohe Alarme, Alarme, alte PRs, unsignierte Builds und Hygiene abzieht; und die Abhängigkeits-Pins, die zurückliegen. Eine Note erscheint nur, wenn `min_coverage` der Repositorys Daten hat. | `sentinel.readiness.*` (`warn_below` 70, `min_coverage` 0.5) | **warn**, wenn eine Note unter `warn_below` liegt; **info** bei zurückliegenden Repositorys; **unknown** bei zu wenig Daten. |
| **A12** | **Analytik.** p50 / p95 der Dauer jedes Workflows, der Wartezeit seiner Jobs und jedes Schritts; Workflows langsamer als üblich (`analytics.slow_factor`); *flaky* Workflows (fehlgeschlagen, dann im selben Commit bestanden). Nur ein Etikett: es ändert nie, was als rot zählt. | `analytics.*` | Keine eigene Ampel. Zuerst die langsamen und flaky ansehen. |
| **A13** | **Workflow-Linter.** Statische Regeln auf den lokalen Klonen: `unpinned_uses`, `permissions`, `secrets_in_clear`, `injection`, `pr_target`. Jeder Befund hat eine Stufe (Info / Warnung / Fehler); ein Kommentar `# monitor-lint: ignore REGEL Grund` oder `lint.ignore` schaltet einen stumm. | `lint.*` | Farbe des schlimmsten Befunds. Zuerst die Fehler beheben; die Seite filtert nach Stufe. |

## Die Prüfungen von A10

Alle sind reine Lese-Vorschläge für einen Menschen; der Monitor schließt nie ein Issue, mergt keinen Pull Request und veröffentlicht kein Release. Abschalten mit `sentinel.surface.checks.<name>.enabled`.

| Prüfung | Wonach sie sucht | Standard |
|---|---|---|
| `workflows_disabled` | Manuell deaktivierte Workflows | on |
| `dead_schedule` | Zeitpläne ohne Ausführungen | on · days=14 |
| `unpinned_uses` | uses: nicht per SHA fixiert | on |
| `broad_permissions` | Zu weit gefasste Berechtigungen (write-all) | on |
| `pr_target` | pull_request_target mit Checkout des PR | on |
| `stuck_concurrency` | Festgefahrene Concurrency (wartende Läufe desselben Workflows) | on · minutes=60 |
| `matrix_os` | Fehler nur auf einem System der Matrix | on · max_per_tick=4 |
| `artifacts` | Artifact-Kosten | on · max_mb=500, retention_days=30 |
| `required_checks` | Pflicht-Checks, die rot sind oder fehlen | on |
| `release_assets` | Unvollständig veröffentlichte Releases | on · recent_days=30, required |
| `tag_vs_version` | Release-Tag vs. Version in Manifest/CHANGELOG | on |
| `packages` | GitHub Packages | on |
| `drafts` | Vergessene Entwürfe und Vorab-Releases | on · days=14 |
| `security_aged` | Kritische/hohe Warnungen nach Alter (Repository-Rangliste) | on · days=30 |
| `coverage` | Sicherheitsabdeckung (CodeQL / Dependabot) | on |
| `secret_resolved` | Secret Scanning: offen vs. gelöst | on |
| `dependabot_priority` | Dependabot nach Priorität | on |
| `issue_close` | Issues, die geschlossen werden könnten (nur Vorschlag) | on |
| `milestones` | Überfällige Meilensteine pro Ökosystem | on |
| `pr_human` | Veraltete PRs von Menschen | on · days=7 |
| `pr_workflow_touch` | PRs, die Workflows oder CODEOWNERS ändern (Priorität) | on |
| `merge_queue` | Merge-Warteschlange: genehmigt mit grüner CI | on |
| `maturity` | Reifegrad im Manifest vs. Nachweis | on |
| `parity` | Gebrochene README-Parität der 8 Sprachen | on |
| `attestation` | Build-Attestierungen | on · max_per_tick=3 |

## Wo alles eingestellt wird

Jeder Schwellwert oben ist eine Einstellung der Reiter **Wächter**, **Oberflächenprüfungen (A10)**, **Bereitschaft (A11)**, **Ordner und Dateien**, **Analytik** und **Workflow-Linter** der Einstellungsseite und ein Schlüssel von `actions_monitor.json`. Die vollständige Liste mit Bereichen steht in `SETTINGS_deu.md`. Das Hilfe-Panel und `--help-topics sentinel` zeigen diese Seite offline.
