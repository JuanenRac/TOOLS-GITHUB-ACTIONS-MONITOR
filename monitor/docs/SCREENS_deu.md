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
| `ui.screen1_tabs` | Tabs von /screen/1, durch Kommas getrennt: now, al, charts, sent, sci, scol, ssec, team, fleet, repos, rep, trep, les, hist, cfg. Leer = alle. |
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

## Wandanzeigen: Übersicht, Gerade jetzt und Wächter

Drei Seiten für einen Monitor oder Fernseher, den niemand bedient. Sie haben kein Seitenmenü und keine Navigation, zeigen alles in einer Ansicht mit großer Schrift, animieren, was lebt, und lassen Fehler sanft blinken. Sie lesen nur: Keine Schaltfläche ändert etwas, und sie rufen GitHub nie auf (sie zeigen, was der Monitor schon hat).

| Adresse | Was sie zeigt |
|---|---|
| `/screen/overview` | Ring und Buchstabe der Bewertung; die Flotte (grün, rot, hängend, wartend); die letzten 24 Stunden und 7 Tage als Flächendiagramme; eine Heatmap der Repositories nach Stunde; was am längsten rot ist; Runner und Minuten; die letzten Ereignisse; das GitHub-Kontingent als Anzeige. |
| `/screen/now` | Was in dieser Minute geschieht: laufende Läufe mit Fortschritt und Dauer, die Warteschlange, Läufe, die auf Freigabe warten, aktuelle Fehlschläge, Merges und Releases, fällige Releases und eine Live-Linie der letzten zwei Stunden. |
| `/screen/sentinels` | Eine Karte je Wächter (A1 bis A12) mit Stufe, offenen Befunden, ob seine Quellen lesbar sind, dem letzten Durchlauf und einem Ring, der dem Durchlauf folgt; ein animiertes Radar, das markiert, was nicht stimmt, und die Warnungen nach Schweregrad. |

### Parameter der Adresse

Eine Adresse je Monitor. Ein Parameter kann ein Fenster ruhiger oder kleiner machen, als die Einstellungen erlauben, nie lauter.

| Parameter | Wirkung |
|---|---|
| `?monitor=1` bis `9` | Die Nummer, die neben dem Titel steht. |
| `?theme=dark`, `light` oder `contrast` | Farben; contrast ist weiß auf schwarz, für einen Bildschirm, der aus der Ferne gelesen wird. |
| `?density=compact`, `normal` oder `large` | Schriftgröße. `?scale=1.5` vergrößert alles (0,5 bis 3). |
| `?refresh=10` | Sekunden zwischen den Aktualisierungen (5 bis 120). |
| `?lang=de` | Sprache (en, es, de, fr, it, ja, zh, pt). |
| `?rotate=30` | Das Fenster wechselt alle 30 Sekunden von selbst zwischen Übersicht, Gerade jetzt und Wächtern (mindestens 5; 0 = keine Rotation). |
| `?blink=off` | Fehler behalten einen festen Schein statt zu blinken. Es kann nicht einschalten, was `screens.blink` ausgeschaltet lässt. |
| `?sound=on` | Ein kurzer Signalton bei einem neuen Fehler, nur wenn `screens.sound` es erlaubt. Standardmäßig aus. |

### Sprache der Anzeigen

Die Sprache einer Anzeige wird in dieser Reihenfolge bestimmt: `?lang=xx` in der Adresse; dann die auf der Hauptseite desselben Browsers gewählte Sprache (sie wird dort gespeichert, und eine in diesem Browser geöffnete Anzeige liest sie, sodass die Anzeige der Seite ohne Parameter folgt); dann die Sprache des Monitors (`MONITOR_LANG` oder die konfigurierte). Unterscheidet sich die gespeicherte Sprache einer Anzeige von der, in der sie ausgeliefert wurde, lädt sie einmal vor dem Zeichnen neu, mit angehängtem `?lang=` und erhaltenen übrigen Parametern (darunter `?rotate=`). Die acht Sprachen (en, es, de, fr, it, ja, zh, pt) sind dieselben wie auf der Seite: Titel, Beschriftungen, Zustände, Schweregrade, Einheiten und relative Zeiten („vor 5 Min.“) stammen aus dem Katalog, und Uhrzeit, Datum und Zahlen werden mit dem Gebietsschema der Sprache geschrieben (en-GB, es-ES, de-DE, fr-FR, it-IT, ja-JP, zh-CN, pt-PT). Der Link „Anzeige öffnen“ in den Einstellungen trägt bereits `?lang=` mit der Sprache der Seite. Ein Rechner, der keine Sprache wählt, bleibt bei Englisch: Die Sprache des Browsers entscheidet nicht.

### Einstellungen der Wandanzeigen

| Einstellung | Was sie bewirkt |
|---|---|
| `screens.enabled` | Schaltet die drei Seiten ein. Aus: Jede Adresse antwortet mit 404. Standardmäßig aus. |
| `screens.default_theme` | dark (Standard), light oder contrast. |
| `screens.default_density` | compact, normal (Standard) oder large. |
| `screens.refresh_seconds` | Sekunden zwischen den Aktualisierungen eines Fensters (standardmäßig 10). Die Seiten lesen vom Monitor, nie von GitHub, eine kurze Zeit kostet also kein Kontingent. |
| `screens.rotate_seconds` | 0 (Standard) = keine Rotation; ab 5 wechselt ein Fenster durch die drei Seiten. |
| `screens.blink` | Fehler blinken sanft (standardmäßig an). |
| `screens.blink_calm_minutes` | Minuten, nach denen ein Fehler, um den sich niemand gekümmert hat, einen festen Schein behält statt zu blinken (standardmäßig 30; 0 = blinkt bis zur Lösung). |
| `screens.sound` | Ein Signalton bei einem neuen Fehler (standardmäßig aus). |
| `screens.burn_in_protection` | Verschiebt alles jede Minute um einige Pixel (standardmäßig an). |
| `screens.night_dim` | Dunkelt die Anzeigen zwischen `screens.night_dim_from_hour` (22) und `screens.night_dim_to_hour` (7) ab; standardmäßig aus. |
| `screens.show_repo_names` | all, public (Standard: private Repositories erscheinen als private-1, private-2...) oder none (jeder Name wird ausgeblendet). Für einen Bildschirm, den andere sehen können, public oder none verwenden. |

### Was sie zeigen und was sie verbergen

Die Daten kommen von `/api/screens/data?screen=overview` (oder `now`, `sentinels`): eine geschlossene Liste von Feldern, gebildet aus dem letzten Zyklus, dem Schnappschuss der Wächter, den Warnungen und der Bewertung. Sie enthält nie einen Link, einen Commit-Titel, einen Job-Namen, einen Benutzernamen oder einen Pfad dieses Rechners, und die Workflow-Namen ausgeblendeter Repositories werden ebenfalls ausgeblendet. Im Netzwerkmodus brauchen die Seiten dasselbe Zugriffstoken wie der Rest des Monitors, und die Antwort ist schreibgeschützt.

### Wie sie sich verhalten

- Fehler blinken weniger als zweimal pro Sekunde (nie als Stroboskop); ein neuer Fehler löst einen einzigen Blitz aus; ein Fehler, um den sich `screens.blink_calm_minutes` Minuten niemand gekümmert hat, behält einen festen Schein. Mit der Systemeinstellung für weniger Bewegung oder mit `?blink=off` blinkt und bewegt sich nichts. Ein Fehler wird nie nur durch Farbe gezeigt: Er trägt ein Symbol und ein Wort.
- Antwortet der Monitor nicht, sagt die Seite es, wird abgedunkelt und versucht es nach 5, 10, 20... Sekunden erneut (bis 60).
- Ein dauerhaft eingeschalteter Bildschirm ist gegen Einbrennen geschützt: Alles verschiebt sich jede Minute um einige Pixel, und die Seite kann nachts abdunkeln.

### Mehrere Monitore einrichten

1. Wählen Sie für jeden Monitor eine Adresse, zum Beispiel `/screen/overview?monitor=1`, `/screen/now?monitor=2` und `/screen/sentinels?monitor=3`; oder öffnen Sie ein einziges Fenster mit `?rotate=20`.
2. Öffnen Sie jede in Chrome oder Edge im Kioskmodus: `msedge --kiosk "http://dieser-rechner:8765/screen/now?monitor=2" --edge-kiosk-type=fullscreen` oder `chrome --kiosk "http://dieser-rechner:8765/screen/now?monitor=2"`; mit `--app=ADRESSE` statt `--kiosk` hat das Fenster keine Leisten. Ohne Kioskmodus bittet die unauffällige Schaltfläche am Seitenende um Vollbild.
3. Von einem anderen Rechner aus verwenden Sie den Netzwerkmodus: Das Zugriffstoken eines Betrachters genügt, weil diese Seiten nie schreiben.

## Bilder

Der Reiter Jetzt in vier Größen, mit erfundenen Daten (4K, ein 21:9-Monitor, ein gedrehter Monitor, ein Smartphone):

![4K 3840x2160](../../docs/screenshots/web_size_4k_light.png)

![Ultrawide 3440x1440](../../docs/screenshots/web_size_ultrawide_light.png)

![gedreht 1080x1920](../../docs/screenshots/web_size_portrait_light.png)

![Smartphone 390x844](../../docs/screenshots/web_size_phone_light.png)

Die drei Wandanzeigen in 4K und auf einem gedrehten Monitor, mit erfundenen Daten:

![Übersicht 4K 3840x2160](../../docs/screenshots/web_screen_overview_4k.png)

![Übersicht 1080x1920](../../docs/screenshots/web_screen_overview_portrait.png)

![Gerade jetzt 4K 3840x2160](../../docs/screenshots/web_screen_now_4k.png)

![Gerade jetzt 1080x1920](../../docs/screenshots/web_screen_now_portrait.png)

![Wächter 4K 3840x2160](../../docs/screenshots/web_screen_sentinels_4k.png)

![Wächter 1080x1920](../../docs/screenshots/web_screen_sentinels_portrait.png)
