<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](FLEET_APIS.md) | [🇪🇸 Español](FLEET_APIS_spa.md) | [🇫🇷 Français](FLEET_APIS_fra.md) | [🇮🇹 Italiano](FLEET_APIS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](FLEET_APIS_zho.md) | [🇯🇵 日本語](FLEET_APIS_jpn.md) | [🇵🇹 Português](FLEET_APIS_por.md)

# Flotte nach Rolle und Gruppe, Lese-APIs und Demo-Seite

## Rollen und Gruppen

Am Ende des Reiters Flotte: der schlechteste Zustand jeder Gruppe (Ökosystem) mit Link zu ihrem eigenen Bildschirm `/g/<Schlüssel>` und eine Spalte je Workflow-Rolle (`fleet.roles`). Ungelesenes ist `unbekannt`, nie in Ordnung.

## Abschalten

`fleet.disabled` nimmt Namen, Muster oder `group:<Schlüssel>`; ab dem nächsten Zyklus werden sie ohne Neustart nicht mehr gelesen. Editionen Complete und Full.

## Lese-APIs

`GET /api/fleet/columns` `GET /api/fleet/group?slug=` `GET /api/cctray.xml` `GET /api/cctray.json` `GET /api/security/secrets` `GET /api/security/code-scanning`. Alle nur lesend, mit denselben Zugriffsprüfungen; bei aktiver versionierter API auch unter `/api/v1/`. `fleet.cctray` liefert den CCTray-Feed, `fleet.security_api` Zählungen der Secret- und Code-Scanning-Warnungen je Repository (nie ein Secret) und nennt Ungelesenes. Beide ab Werk aus.

## Berichts-Fingerabdruck

Berichte und KI-Briefs tragen `report_digest`: SHA-256 über Fakten, Monitorversion, Regelversion und Urteil. Gleicher Wert heißt gleicher Inhalt. Es ist keine Signatur.

## Demo-Seite

Eine statische Kopie der Demo (erfundene Daten, keine Anmeldung, keine Aktion, keine fremden Anfragen) und eine Workflow-Prüfung im Browser mit Pyodide (nichts wird hochgeladen):

```
python tools/make_public_demo.py demo-site
```

Der Workflow *Demo site* hält sie als Artefakt. Die Veröffentlichung ist eine eigene Entscheidung des Repository-Eigentümers; nichts veröffentlicht sie von selbst. Die Browser-Prüfung wurde nicht auf einer veröffentlichten Seite erprobt.

## Alle Einstellungen

`fleet.disabled` `fleet.roles` `fleet.cctray` `fleet.security_api`
