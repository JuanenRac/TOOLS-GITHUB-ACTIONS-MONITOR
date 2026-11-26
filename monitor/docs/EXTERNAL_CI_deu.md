<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](EXTERNAL_CI.md) | [🇪🇸 Español](EXTERNAL_CI_spa.md) | [🇫🇷 Français](EXTERNAL_CI_fra.md) | [🇮🇹 Italiano](EXTERNAL_CI_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](EXTERNAL_CI_zho.md) | [🇯🇵 日本語](EXTERNAL_CI_jpn.md) | [🇵🇹 Português](EXTERNAL_CI_por.md)

# Externe CI-Quellen (nur lesend)

Ein auf GitHub gespiegeltes Repository wird vielleicht woanders gebaut. Der Monitor liest Buildbot, GitLab CI, Jenkins und Azure Pipelines und zeigt deren Fehler wie die von Actions. Er liest nur (GET); er startet, bricht und schreibt dort nichts. Editionen Complete und Full; standardmäßig aus.

## Einrichtung

`external_ci.enabled` einschalten und in `external_ci.sources` eine Zeile pro Quelle schreiben (Einstellungen > Externes CI). `repo` ist der Name, unter dem das Ergebnis erscheint.

```
buildbot;repo=my-mirror;url=https://buildbot.example.org;builders=linux+docs
gitlab;repo=my-mirror;url=https://gitlab.example.org;project=group/app;token_env=MY_GITLAB_VALUE
jenkins;repo=my-mirror;url=https://jenkins.example.org;job=folder/app;branch=main
azure;repo=my-mirror;url=https://dev.azure.com/my-org;project=my-project
```

## Rot, in Ordnung oder eingeschränkt

Der letzte beendete Build jedes Builders, jeder Pipeline oder jedes Jobs auf seinem Branch entscheidet, wie bei Actions: Merge-Anfragen sowie abgebrochene, übersprungene und unbekannte Zustände entscheiden nie. Ein Dienst, der nicht antwortet, etwas anderes liefert oder dem ein Builder fehlt, ist **eingeschränkt**, nie rot; frühere Fehler bleiben als veraltet stehen. Fehler erzeugen ci.external.red (Stufe `external_ci.alert.level`), gezählt, gemeldet und stummschaltbar wie ein Rot von Actions; ci.external.degraded ist eine Information. Stummschalten verdeckt nie eine Sicherheitswarnung. Jede Quelle wird höchstens alle `external_ci.refresh_seconds` (ab 300) gelesen, nach `external_ci.breaker.failures` Fehlern seltener.

## Sicherheit

Die Adresse wird beim Verbinden geprüft: dieser Computer, private Netze und Cloud-Metadaten werden ohne `external_ci.allow_private_targets` abgewiesen. Weiterleitungen und Links aus Antworten werden nicht verfolgt. Antworten sind durch `external_ci.max_bytes` und `external_ci.timeout_s` begrenzt. Zugangsdaten stehen nie in der Konfiguration: `token_env` enthält nur den NAMEN einer Umgebungsvariablen (GitLab: Lese-Token; Jenkins: `benutzer:token`; Azure: persönliches Token mit Build-Leserecht), ohne TLS nie an eine öffentliche Adresse. Das GitHub-Kontingent wird nicht verbraucht. Im Offline-Modus (`airgapped`) wird nichts gelesen; `doctor --egress` nennt die Hosts.

## Logs eines fehlgeschlagenen Builds

Standardmäßig aus (`external_ci.logs.enabled`). Nur das Ende wird geholt, begrenzt durch `external_ci.logs.max_kb` und `external_ci.logs.tail_lines`, ohne Terminalsequenzen und Steuerzeichen, bereinigt, `external_ci.logs.keep_hours` im Speicher. Es ist nicht vertrauenswürdiger Text und wird einer KI nie als Anweisung gegeben. Die Bereinigung erkennt nicht jedes Geheimnis.

## Test, Status, Befehlszeile

Einstellungen > Externes CI bietet **Verbindung testen**: eine Abfrage ohne Speichern (`POST /api/external-ci/probe`). Der CI-Reiter der Wächter zeigt jede Quelle; `GET /api/external-ci/status` liefert dasselbe, `GET /api/external-ci/log` ein Log. Befehle: `external-ci list`, `external-ci status` (Code 1 bei Rot oder eingeschränkt) und `external-ci probe --source "ZEILE"`.

## Noch nicht verifiziert

Alle vier Adapter wurden nur mit nachgebildeten Servern getestet (`tools/extci_fake_servers.py`). Jenkins und Azure Pipelines sind als **experimentell** gekennzeichnet (`external_ci.experimental`) und brauchen `external_ci.jenkins.enabled` / `external_ci.azure.enabled`. Weiterer Adapter: eine Funktion `(reader, source, cfg) -> (runs, missing)` in `integrations/external_ci/extci_adapters.py`, die nur über `reader` liest.

## Identität eines Repositorys, mehrere Eigentümer

Im Monitor ist ein Repository (Quelle, Eigentümer, Name), geschrieben als `repo_key` (`github:eigentümer/name`, `gitlab@host:gruppe/name`); die Routen nennen es weiter beim Namen. Zwei Repositorys gleichen Namens aus zwei Orten teilen weder Kennungen noch Läufe oder Warnungen: spiegeln zwei Server derselben Art denselben Namen, wird der Host an die Bezeichnung angehängt. Der Monitor merkt sich, welchem Eigentümer seine gespeicherten Daten gehören. Wechselt der Eigentümer, werden Stummschaltungen und Warnungsprotokoll der Repositorys und der letzte Stand des Ereignisstroms beiseitegelegt (aufbewahrt, nicht gelöscht), nachdem jede Datei nach `identity_backup/` kopiert wurde. Das geschieht nach einem Zyklus; `identity plan` zeigt es ohne Änderung, `identity apply` führt es sofort aus und `identity status` zeigt den Eintrag. `sources.multi_owner` (aus) erlaubt Konten verschiedener Eigentümer; Installationen, die schon mehrere haben, laufen weiter und der Doctor sagt es. `doctor` liest außerdem jede externe Quelle einmal.

Befehlszeile: `identity status`, `identity plan`, `identity apply`.
