<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](API_V1.md) | [🇪🇸 Español](API_V1_spa.md) | [🇫🇷 Français](API_V1_fra.md) | [🇮🇹 Italiano](API_V1_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](API_V1_zho.md) | [🇯🇵 日本語](API_V1_jpn.md) | [🇵🇹 Português](API_V1_por.md)

# Die Lese-API v1, Schritt für Schritt

Eine Anleitung für alle, die einen Client (ein Skript, einen Wandbildschirm, eine Mobil-App, ein KI-Werkzeug) gegen die Lese-API des Monitors schreiben. Die Referenz jeder Route ist das OpenAPI-Dokument, das der Monitor selbst liefert; die Regeln des Vertrags (was eingefroren ist und was wachsen darf) stehen in [API_deu.md](API_deu.md). Hier der Weg, mit Befehlen, die ein Test gegen einen Monitor ausführt.

## 1. Ist die API offen?

Das Präfix `/api/v1/` antwortet von selbst, wenn der Monitor als Dienst läuft (ein Konto des Teammodus, das Docker-Image, die systemd-Einheit), und bleibt für eine Person an einem Rechner geschlossen und antwortet 404. Die Einstellung `api.v1_enabled` (`auto`, `on`, `off`) entscheidet. Ein Client beginnt mit der Frage, wer er ist: ein `404` heißt dort, dass die API geschlossen ist, nicht dass der Client falsch ist.

## 2. Sich ausweisen

Vom selben Rechner ohne Netzwerkmodus ist kein Token nötig. Im Netzwerkmodus trägt jede Anfrage das Zugriffstoken im Header `X-Monitor-Access`, hier aus einer Datei gelesen, damit es nie in einer Befehlszeile im Verlauf landet; im Teammodus meldet sich ein Skript bei `POST /api/auth/login` an. Ein Lese-Token ist alles, was ein Client dieser API braucht: unter dem Präfix wird nichts geschrieben.

## 3. Die Befehle

In dieser Reihenfolge: wer du bist und die Version des Vertrags (`/api/v1/me`), die Beschreibung jeder eingefrorenen Route (`/api/v1/openapi.json`), die Repositories seitenweise (`state`, `ecosystem` und `q` filtern; `limit`; `fields` oder `profile=compact` für kürzere Zeilen; `cursor` ist der `next_cursor` der vorigen Seite, bis er `null` ist), die mit gzip komprimierte Antwort und zwei Routen der alten API, die das Präfix mit derselben Antwort ebenfalls liefert.

```
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/me
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/openapi.json -o openapi.json
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?state=bad&limit=20&profile=compact"
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?fields=repo,state,risk&limit=5"
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=50&cursor=THE_NEXT_CURSOR"
curl -s --compressed -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=100"
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/health
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/alerts
```

## 4. Fehler

Ein Fehler der eigenen Routen ist ein JSON-Objekt mit drei Schlüsseln: `error` und `code` sind stabil und für Programme gedacht, `message` folgt der Sprache von `?lang=` und ist für Menschen gedacht. Die Codes sind api.bad_cursor, api.bad_limit, api.unknown_field, api.bad_profile und api.server_error. Jede Antwort des Präfixes, Fehler eingeschlossen, trägt den Header `X-API-Version: 1`. Jeder Fehler trägt außerdem `help`, einen Satz mit dem nächsten Schritt und der Anleitung dazu, in derselben Sprache (das Feld fehlt, wenn ein Code keinen hat; ein Programm, das es ignoriert, verliert nichts).

```
curl -s -i -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=0"
```

Die Antwort nach den Headern ist `{"error": "bad_request", "code": "api.bad_limit", "message": "..."}`.

## 5. Dasselbe von der Befehlszeile und von einem KI-Werkzeug

Drei Zugänge liefern dieselben Dokumente, und ein Test vergleicht sie: HTTP wie oben, die Befehlszeile (`python bin/monitor_cli.py api me`, `api openapi`, `api contract-check`; mit `--json` die Antwort als Daten) und der MCP-Server (`python bin/mcp_server.py`, nur lesend: die Werkzeuge `api_me`, `api_openapi` und `api_contract_check`).

## 6. Einen Server prüfen, bevor man sich auf ihn verlässt

`python tools/api_contract_suite.py --url URL --token-file token.txt` nimmt das Dokument, das der Server liefert, als Beschreibung dessen, was zu prüfen ist, und gibt eine Zeile je Prüfung sowie `API_CONTRACT=PASS` oder `API_CONTRACT=FAIL` aus. `python tools/check_api_contract.py --v1` führt dieselbe Suite aus und vergleicht zusätzlich die Antworten mit dem eingefrorenen Vertrag. Führe eines davon nach jedem Update des Monitors oder deines Clients aus; die CI des Monitors führt die Suite gegen eine Demo im Dienstmodus aus.
