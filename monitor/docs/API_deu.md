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

- `docs/schemas/api_contract.json` listet jeden lesenden Endpunkt mit seinen Schlüsseln und Typen in jeder Ausgabe sowie die Fehlercodes auf. Die lesbaren, aber nicht eingefrorenen Routen (Datenströme, Text, Exporte anderer Werkzeuge) stehen in derselben Datei unter `unfrozen`, jeweils mit ihrem Grund; `/api/data`, das die Läufe, die Repositories und das Kontingent liefert, ist eingefroren. Die Schlüssel reichen bis in die Elemente der Listen: Eine Liste, die in der Datei als `[{...}]` steht, beschreibt ihre Elemente (die ersten drei werden geprüft); so können die Läufe, Repositories und das Kontingent von `/api/data`, die Alarme von `/api/alerts` und `/api/auth/me` sich nicht ändern, ohne dass die Prüfung fehlschlägt.
- `python tools/check_api_contract.py` prüft einen laufenden Monitor dagegen (`--lite`, `--url`, `--token-file`) und gibt `CONTRACT=PASS` oder `CONTRACT=FAIL` aus; führe es nach jedem Upgrade des Monitors oder deines Clients aus.

## Lese-API v1 (standardmäßig automatisch)

- Stelle `api.v1_enabled` ein (Einstellungen, Erweitert, Lese-API v1): `auto` (Standard) antwortet, wenn der Monitor als Dienst läuft (ein Konto des Teammodus, das Docker-Image, die systemd-Unit), und bleibt für eine Person an einem Rechner geschlossen; `on` immer; `off` nie (das alte true und false bedeuten on und off). Wenn sie antwortet, wird jede Leseroute auch unter `/api/v1/` ausgeliefert (zum Beispiel `/api/v1/alerts`): dieselbe Antwort und dieselben Rollen, dazu der Header `X-API-Version: 1`. Solange sie geschlossen ist, in der Lite-Edition und für jede andere Versionsnummer antwortet das Präfix mit 404.
- `/api/v1/me`: wer fragt: `mode` (`individual` oder `team`), `authenticated`, `user`, sowie `role` und `accounts` der Team-Sitzung (null ohne eine), was die Sitzung darf (`capabilities`: `read`, `write`, `admin` und `v1_write`, immer false, weil das Präfix nur lesend ist), die `limits` der Listen, die Version des Monitors und die Version des Vertrags (`contract`, `1.0`: wächst mit jedem neuen Schlüssel und verliert nie einen).
- `/api/v1/repos`: die Repositories, die der Monitor beobachtet, je eine Zeile (`repo`, `ecosystem`, `state`, `risk`, `runs_24h`, `failures_24h`, `red_workflows`, `stuck_runs`, `alerts`, `last_run_at`). Filter `state`, `ecosystem` und `q`; `limit` (standardmäßig `api.default_limit`, höchstens `api.max_limit`); `cursor` (der `next_cursor` der vorigen Seite, signiert und gültig für `api.cursor_ttl_seconds`); `fields=a,b` oder `profile=compact` für kürzere Zeilen. Die Antwort wird mit gzip komprimiert, wenn der Client es akzeptiert.
- `/api/v1/openapi.json`: die OpenAPI-3-Beschreibung der gesamten eingefrorenen Lese-API, aus dem Vertrag (`docs/schemas/api_contract.json`) gebaut und nie von Hand geschrieben: jede eingefrorene Route mit den Schlüsseln und Typen, die sie verspricht, `x-lite` (was die Lite-Edition antwortet) und `x-local-only`. Die Routen, die der Vertrag nicht einfriert, sind experimentell: Sie antworten unter `/api/v1/` mit 404 und stehen nicht im Dokument, außer `api.experimental_routes` ist an (dann stehen sie mit `x-experimental` darin). Die alten Routen unter `/api/` ändern sich nie. Lade es mit `python bin/monitor_cli.py api openapi`.
- `python tools/api_contract_suite.py` ist die Vertragssuite für externe Clients (nur die Standardbibliothek, nur lesend): Gib ihr die Adresse eines Servers (`--url`) und ein Lese-Token (`--token-file`); sie nimmt das vom Server gelieferte Dokument als Beschreibung dessen, was zu prüfen ist: die Form jeder Route ohne Parameter, den Header `X-API-Version`, den Fehlerumschlag und seine stabilen Codes, die Seiten und ihre Cursor, `fields` und `profile=compact`, gzip und dass sich unter dem Präfix nichts schreiben lässt. Sie gibt eine Zeile je Prüfung und `API_CONTRACT=PASS` oder `API_CONTRACT=FAIL` aus (`--json` für ein Dokument); der Exit-Code ist 0, 1 oder 2 (nichts antwortet). `python bin/monitor_cli.py api contract-check` startet sie gegen den Monitor der Befehlszeile.
- Dieselben drei Dinge sind Werkzeuge des MCP-Servers (`python bin/mcp_server.py`, nur lesend, ohne Schalter): `api_me` (wen der Monitor im Client sieht), `api_openapi` (das Dokument oder mit `path` eine Route) und `api_contract_check` (die Vertragssuite, Antwort `{ok, checks, failed, rows}`). HTTP, die Befehlszeile (`api me`, `api openapi`, `api contract-check`) und MCP liefern dasselbe Dokument; ein Test vergleicht sie. Solange das Präfix geschlossen ist, sagen die Werkzeuge das in einer Zeile.
- Die beiden eigenen Routen antworten einen Fehler als `{"error": "bad_request", "code": "api.bad_cursor", "message": "..."}`: `error` und `code` sind stabil, `message` folgt der Sprache von `?lang=`. Codes: api.bad_cursor, api.bad_limit, api.unknown_field, api.bad_profile, api.server_error. Alles ist nur lesend: unter `/api/v1/` gibt es kein Schreiben. Die Form ist im Abschnitt `v1_endpoints` des Vertrags eingefroren und wird mit `python tools/check_api_contract.py --v1` gegen einen Monitor mit eingeschaltetem `api.v1_enabled` geprüft.

### Beispiele mit curl

Das Token ist das Zugriffstoken des Netzwerkmodus (oder nutze eine Sitzung des Teammodus); ohne Netzwerkmodus braucht man vom selben Rechner kein Token. Ein Client folgt `next_cursor`, bis es `null` ist, und liest zuerst `/api/v1/me`, um die Version des Vertrags und die Rechte der Sitzung zu kennen.

```
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/me
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?state=bad&limit=20&profile=compact"
curl -s -H "X-Monitor-Access: $(cat token.txt)" http://127.0.0.1:8765/api/v1/openapi.json -o openapi.json
curl -s -H "X-Monitor-Access: $(cat token.txt)" "http://127.0.0.1:8765/api/v1/repos?limit=50&cursor=THE_NEXT_CURSOR"
```

## Streams

- `GET /api/ai/stream` (die Meldungen) und `GET /api/live-events/stream` (die Ereignisse des Webhooks, `live.sse.enabled`) sind Server-Sent Events, nur lesend und standardmäßig aus; siehe [AI_ALERTS_deu.md](AI_ALERTS_deu.md) und [WEBHOOK_deu.md](WEBHOOK_deu.md).
- `POST /api/chatops/slack` und `POST /api/chatops/discord` nehmen die nur lesenden Befehle eines Chats an (standardmäßig aus, `chatops.enabled`). Sie nutzen nicht das Zugriffstoken: Der Nachweis ist die Signatur der Plattform, und eine Anfrage ohne gültige Signatur wird abgelehnt, bevor etwas gelesen wird. Siehe [CHATOPS_deu.md](CHATOPS_deu.md).
