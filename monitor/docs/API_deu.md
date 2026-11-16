<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](API.md) | [🇪🇸 Español](API_spa.md) | [🇫🇷 Français](API_fra.md) | [🇮🇹 Italiano](API_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](API_zho.md) | [🇯🇵 日本語](API_jpn.md) | [🇵🇹 Português](API_por.md)

# Die API für Clients

Worauf sich ein Skript, ein Wandbildschirm oder ein mobiler Client verlassen kann. Ab 2.0.0 sind die lesenden Endpunkte eingefroren: Ein Schlüssel des Vertrags behält Namen und Typ, neue Schlüssel dürfen hinzukommen, und nichts wird ohne neue Hauptversion entfernt oder geändert.

## Anfragen

- Im Standardmodus antwortet die API auf `127.0.0.1` ohne Anmeldung. Im Netzwerkmodus trägt jede Anfrage das Zugriffstoken im Header `X-Monitor-Access` (oder das Sitzungs-Cookie, oder einmal `POST /api/access`). Mit dem Teammodus meldet sich ein Skript bei `POST /api/auth/login` an.
- Ein Wort in der Abfrage, das ein Endpunkt nicht kennt, wird ignoriert. Die Antworten sind JSON in UTF-8, außer der Kurzfassung in Markdown und den Streams.

## Fehler

- Ein Fehler ist JSON `{"error": "Wort"}`, manchmal mit einem `code`. `401 access` heißt, das Token fehlt oder ist falsch, `403 forbidden`, dass die Anfrage nicht von dort kommt, wo sie erlaubt ist (auch ein fremder `Host`), `404`, dass der Pfad in dieser Ausgabe nicht existiert (die Lite-Ausgabe antwortet 404 auf alles, was nur die Vollausgabe hat), `429`, dass die Adresse gesperrt ist oder die Zuhörer voll sind.
- Ein abgelehntes Schreiben ändert nie etwas. Schreibende Aufrufe gehören nicht zum Vertrag.

## Der Vertrag

- `docs/schemas/api_contract.json` listet jeden lesenden Endpunkt mit seinen Schlüsseln und Typen in jeder Ausgabe sowie die Fehlercodes auf.
- `python tools/check_api_contract.py` prüft einen laufenden Monitor dagegen (`--lite`, `--url`, `--token-file`) und gibt `CONTRACT=PASS` oder `CONTRACT=FAIL` aus; führe es nach jedem Upgrade des Monitors oder deines Clients aus.

## Streams

- `GET /api/ai/stream` (die Meldungen) und `GET /api/live-events/stream` (die Ereignisse des Webhooks, `live.sse.enabled`) sind Server-Sent Events, nur lesend und standardmäßig aus; siehe [AI_ALERTS_deu.md](AI_ALERTS_deu.md) und [WEBHOOK_deu.md](WEBHOOK_deu.md).
