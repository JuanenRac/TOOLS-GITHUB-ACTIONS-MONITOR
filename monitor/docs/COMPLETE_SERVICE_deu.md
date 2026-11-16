<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COMPLETE_SERVICE.md) | [🇪🇸 Español](COMPLETE_SERVICE_spa.md) | [🇫🇷 Français](COMPLETE_SERVICE_fra.md) | [🇮🇹 Italiano](COMPLETE_SERVICE_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](COMPLETE_SERVICE_zho.md) | [🇯🇵 日本語](COMPLETE_SERVICE_jpn.md) | [🇵🇹 Português](COMPLETE_SERVICE_por.md)

# Vollausgabe als Dienst

Für einen Monitor, der dauerhaft auf einem Server oder in einem Container läuft und von anderen Personen oder Programmen gelesen wird. Dies fasst die Entscheidungen zusammen; Einzelheiten, Befehle und die Tabelle der Variablen stehen in [DEPLOYMENT_deu.md](DEPLOYMENT_deu.md).

## Wie er lauscht

- Auf drei Arten: nur dieser Rechner (Standard, ohne Anmeldung), das Netzwerk (`listen.network` an, `listen.host` und das Zugriffstoken bei jeder Anfrage) oder hinter einem Proxy (`listen.proxy_public_host`, `listen.secure_cookie` oder `listen.trusted_proxy`).
- Stelle HTTPS (ein Zertifikat oder einen Proxy) oder ein VPN vor den Netzwerkmodus: Über einfaches HTTP laufen Token und Passwörter im Klartext.

## Wie man ihn betreibt

- Das offizielle Image, Docker Compose mit optionalem Proxy oder eine klassische Installation mit systemd; alle starten `python -m github_actions_monitor.service` ohne Browser.
- Die Ports sind 8765 für die Vollausgabe und 8766 für die Lite-Ausgabe (`ports.complete`, `ports.lite`).

## Im Blick behalten

- `GET /api/health` ruft GitHub nicht auf; `GET /api/health?deep=1` antwortet mit 503, wenn ein Aktualisierungszyklus hängt, und `python -m github_actions_monitor.cli.healthcheck` führt diesen Aufruf für einen Container oder Dienstmanager aus.
- Wenn GitHub die Anmeldung widerruft, ersetze die Zugangsdaten über die Befehlszeile, den Administrator-Endpunkt oder `SIGHUP`; ein Neustart behebt eine verlorene Anmeldung nicht.

## Über Monate

- Wähle Dateien oder SQLite und die Aufbewahrung in [STORAGE_deu.md](STORAGE_deu.md), sichere vor jedem Upgrade und lies [MIGRATING_deu.md](MIGRATING_deu.md).
- Für Personen, die sich anmelden, ist der Teammodus in [COMPLETE_TEAM_deu.md](COMPLETE_TEAM_deu.md) beschrieben; der Vertrag, auf den sich Programme verlassen können, steht in [API_deu.md](API_deu.md).
