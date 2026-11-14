<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCREENS.md) | [🇪🇸 Español](SCREENS_spa.md) | [🇫🇷 Français](SCREENS_fra.md) | [🇮🇹 Italiano](SCREENS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](SCREENS_zho.md) | [🇯🇵 日本語](SCREENS_jpn.md) | [🇵🇹 Português](SCREENS_por.md)

# Bildschirme, Größen und Ausrichtung

Die Seite passt sich der Größe ihres Fensters an, vom Telefon bis 4K, hochkant oder quer, und ein Monitor kann mehrere Bildschirme bedienen, jeder mit den Tabs Ihrer Wahl. Nichts wird doppelt abgefragt: alle Bildschirme lesen denselben Zustand.

## Adressen

- `/` - die ganze Seite.
- `/screen/1`, `/screen/2`, `/screen/3` - die für diesen Bildschirm festgelegten Tabs (`ui.screen1_tabs` ...). Jede in einem Fenster des eigenen Monitors oder Fernsehers öffnen.
- `?orient=portrait` oder `?orient=landscape` erzwingt das Layout eines Fensters; `?tabs=now,charts` und `?rotate=30` legen Tabs und Sekunden dazwischen für ein Fenster fest.

## Einstellungen

| Einstellung | Wirkung |
|---|---|
| `ui.orientation` | auto folgt dem Fenster; portrait stapelt die Panels in einer Spalte; landscape behält das Nebeneinander. |
| `ui.rotate_seconds` | 0 = aus. Sekunden zwischen den Tabs eines Bildschirms mit mehr als einem. |
| `ui.screen1_tabs` | Tabs von /screen/1, durch Kommas getrennt: now, al, sent, charts, repos, hist, cfg. Leer = alle. |
| `ui.screen1_orientation` | auto, portrait oder landscape nur für /screen/1. |
| `ui.screen2_tabs` | Tabs von /screen/2. |
| `ui.screen2_orientation` | Ausrichtung von /screen/2. |
| `ui.screen3_tabs` | Tabs von /screen/3. |
| `ui.screen3_orientation` | Ausrichtung von /screen/3. |
| `ui.now_sort` | Reihenfolge von Läuft gerade für alle, die keine gewählt haben: ecosystem, severity, age, newest, repo, event oder state. |
| `ui.alerts_sort` | Reihenfolge des Tabs Meldungen für alle, die keine gewählt haben: server, severity, streak, class, age, newest, repo, origin oder state. |

## Reihenfolge der Listen

Der Abschnitt **Läuft gerade** auf dem ersten Tab ist nach Ökosystem sortiert, mit einer Überschrift je Ökosystem. Die Liste über dem Abschnitt ändert das: Ökosystem, Schweregrad (zuerst hängende, dann Runs mit fehlgeschlagenem Job, dann laufende, dann wartende), Alter (längste Laufzeit zuerst), neueste zuerst, Repository, Auslöser (push, pull_request, schedule...) und Status (laufend vor wartend). Die Auswahl wird für jede Person gemerkt: im Teammodus speichert sie der Server beim Benutzer (`GET` und `POST /api/auth/me/view`, sie folgt dem Benutzer also in einen anderen Browser), sonst dieser Browser. Bis jemand wählt, gilt `ui.now_sort` der Konfigurationsdatei (Ökosystem, wenn der Wert fehlt oder falsch ist). Die Schaltflächen **Alle aufklappen** und **Alle zuklappen** neben der Liste klappen alle Repositories des Abschnitts auf einmal auf oder zu, in jeder Reihenfolge; die Wahl wird pro Person am selben Ort gemerkt und übersteht eine Aktualisierung (ein danach von Hand geöffnetes oder geschlossenes Repository behält Ihre Wahl).

Die Liste des Tabs **Meldungen** behält die Reihenfolge des Monitors, bis jemand mit der Liste darüber eine andere wählt: Schweregrad (kritisch, Fehler, Warnung, Info), die längste Serie aufeinanderfolgender Fehler zuerst, Klasse (eine Fehler- oder kritische Meldung ist echt und steht vor den zu beobachtenden), die älteste zuerst, die neueste zuerst, Repository, Herkunft (der Wächter, der sie ausgelöst hat) und Status (offen vor stummgeschaltet). Sie wird auf dieselbe Weise gemerkt; bis jemand wählt, gilt `ui.alerts_sort` der Konfigurationsdatei (`server`, wenn der Wert fehlt oder falsch ist).

## Getestete Größen

Ein Browser-Test öffnet die Seite in jeder dieser Größen, geht alle Tabs durch und schlägt bei seitlichem Scrollen oder Text außerhalb seines Kastens fehl. Fenster ab 2400 px erhalten eine größere Schrift (ab 3200 px eine noch größere) statt eines gestreckten Layouts; ein höheres als breites Fenster stapelt die Panels.

| Größe | Art |
|---|---|
| 1920x1080 | Full HD |
| 2560x1080 | 21:9 |
| 3440x1440 | 21:9 |
| 5120x1440 | 32:9 |
| 3840x2160 | 4K |
| 1080x1920 | Full HD |
| 2160x3840 | 4K |
| 768x1024 | tablet |
| 390x844 | phone |

## Rezept für einen Arbeitsplatz mit zwei oder drei Bildschirmen

1. Auf dem Rechner, auf dem der Monitor läuft, `ui.screen1_tabs` auf `now,al`, `ui.screen2_tabs` auf `charts,repos` und für einen gedrehten Monitor `ui.screen2_orientation` auf `portrait` setzen.
2. `http://dieser-rechner:8765/screen/1` im Fenster des ersten Monitors und `/screen/2` im zweiten öffnen; F11 für Vollbild. Von einem anderen Rechner den Netzmodus mit Zugriffstoken nutzen.
3. Für einen Wandbildschirm, den niemand bedient, mehrere Tabs vergeben und `ui.rotate_seconds` auf 20-30 setzen.

## Bilder

Der Reiter Jetzt in vier Größen, mit erfundenen Daten (4K, ein 21:9-Monitor, ein gedrehter Monitor, ein Smartphone):

![4K 3840x2160](../../docs/screenshots/web_size_4k_light.png)

![Ultrawide 3440x1440](../../docs/screenshots/web_size_ultrawide_light.png)

![gedreht 1080x1920](../../docs/screenshots/web_size_portrait_light.png)

![Smartphone 390x844](../../docs/screenshots/web_size_phone_light.png)
