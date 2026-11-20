<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SOUNDS.md) | [🇪🇸 Español](SOUNDS_spa.md) | [🇫🇷 Français](SOUNDS_fra.md) | [🇮🇹 Italiano](SOUNDS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](SOUNDS_zho.md) | [🇯🇵 日本語](SOUNDS_jpn.md) | [🇵🇹 Português](SOUNDS_por.md)

# Töne

Die Seite macht ihre Töne selbst mit der Web-Audio-API, einen für jede Ereignisart, damit man nach Gehör erkennt, was passiert ist, ohne hinzusehen. Es gibt keine Audiodateien: die Töne entstehen im Browser, ohne Verbindung, und nichts wird irgendwohin gesendet. Zu jedem Ton gibt es auch einen sichtbaren Hinweis (die Kacheln, die Tabs, die Marken); der Ton ersetzt ihn nie.

| Art | Wann er ertönt | Der Ton |
|---|---|---|
| Rot | Ein Workflow, der nicht rot war, wird rot (ein neuer Fehler). | Zwei aufsteigende Töne, das klassische "Bing Bing". |
| Sicherheit oder ernst | Ein neuer Alarm des Sicherheits-Wächters, ein ernster (Fehler oder kritisch) Alarm des Zusammenarbeits-Wächters oder ein Konto, das blind geworden ist. | Drei tiefe Impulse. |
| Hängt | Ein hängender Build, eine Geister-Warteschlange oder ein Problem mit den Runnern. | Ein langes fallendes Gleiten. |
| Wertung | Die Wertung der Flotte fällt (`score.dropped`). | Drei fallende Töne. |
| Verbindung | Die Verbindung zu GitHub oder die dieser Seite zum Monitor geht verloren. | Zwei tiefe, lange Töne. |
| Warnung | Ein neuer Alarm der Stufe Warnung (eine ausstehende Signatur, ein altes Issue, ein wartender Pull Request). | Zwei gleiche mittlere Töne. |
| Gelöst | Ein roter Workflow wird grün, oder ein ernster Alarm verschwindet. | Drei aufsteigende Töne. |
| Bericht | Einer der optionalen Berichte zeigt einen Befund, der vorher nicht da war. | Zwei sanfte Glockentöne, hoch und dann tiefer. |
| Lektion | Die Lektionen aus den Fehlern zeigen eine neue Kategorie oder eine, die sich zu wiederholen oder zu gelten beginnt. | Drei schnelle hohe Töne. |
| Hinweis | Ein neuer Alarm der Stufe Info (zum Beispiel das Release des Originals eines Forks). | Ein sanfter Ping. |
| Wieder online | Die Verbindung zu GitHub oder dieser Seite mit dem Monitor kehrt nach einem Ausfall zurück. | Vier aufsteigende Töne. |

## Warum ein Browser stumm bleiben kann und was die Seite tut

- Ein Browser lässt eine Seite erst Töne abspielen, nachdem Sie darauf geklickt, getippt oder eine Taste gedrückt haben. Bis dahin zeigt die Leiste den Hinweis "Ton vom Browser blockiert: hier klicken zum Einschalten". Der erste Klick irgendwo entsperrt ihn.
- Was geschah, während der Ton blockiert war, wird aufbewahrt (höchstens zehn Minuten) und beim ersten Moment abgespielt: der Klick, die Seite, die wieder nach vorn kommt, oder die nächste Prüfung alle zwei Sekunden. Zwischen zwei Abfragen geht nichts verloren; was älter als zehn Minuten ist, ist eine alte Nachricht und wird nicht angekündigt.
- Der erste Blick der Seite merkt sich nur, was schon da ist; ein Neuladen innerhalb weniger Stunden merkt es sich ebenfalls, ein Fehler, der bei geschlossener Seite kam, ist also neu.
- Ein Tab im Hintergrund behält seinen Ton, solange der Browser die Seite wach hält; manche Browser pausieren versteckte Tabs nach einer Weile. Wandanzeigen und Seite bleiben am besten in einem sichtbaren Fenster.

## Kein Dauerlärm

- Eine Art, die gerade ertönt ist, wartet `sound.cooldown_seconds` (standardmäßig 30 s), bevor sie wieder ertönt.
- Mehrere Arten in einem Blick ergeben einen einzigen Schub: höchstens drei Muster, das ernsteste zuerst; der Rest wartet auf den nächsten Schub. Zwei Schübe überlagern sich nie.
- Ein stummgeschalteter Alarm (Tab Alarme) ertönt nie.

## Die Klangbibliothek

Neben den elf Klängen, die jede Ereignisart schon immer hatte, bringt der Monitor eine Bibliothek mit 54 Klängen (insgesamt 65) mit, die du jeder Ereignisart zuweisen kannst. Sie werden im Browser erzeugt (und für den Piepton dieses Rechners aus denselben Noten), es gibt also keine Audiodateien zum Herunterladen. Die Klänge der Arten sind die ersten elf; die übrigen sind frei zuweisbar: `bell`, `chime`, `ding_dong`, `doorbell`, `ding`, `ping_high`, `ping_low`, `tick_soft`, `tock_soft`, `double_tick`, `tick_tock`, `knock`, `knock_three`, `blip`, `bloop`, `bubble`, `drop`, `droplet`, `arpeggio_up`, `arpeggio_down`, `minor_up`, `minor_down`, `fanfare`, `level_up`, `coin`, `harp_up`, `harp_down`, `marimba`, `xylophone`, `pluck`, `cascade`, `sparkle`, `ascend`, `descend`, `notify_a`, `notify_b`, `notify_c`, `sweep_up`, `sweep_down`, `whistle_up`, `whistle_down`, `zap`, `laser`, `radar`, `sonar`, `beacon`, `heartbeat`, `alarm_fast`, `siren`, `klaxon`, `buzzer`, `gong`, `phone`, `cuckoo`.

Um einer Art einen anderen Klang zu geben, schreibe `art=klang`-Paare durch Kommas getrennt in `sound.voices`, zum Beispiel `new_red=coin,warning=drop`. Die Arten sind `new_red`, `sentinel`, `stuck`, `score_drop`, `connection_lost`, `warning`, `resolved`, `report`, `lesson`, `info`, `live_recovered`. Ein Name, der nicht in der Bibliothek steht, wird ignoriert und die Art behält ihren eigenen Klang. Die Wandanzeigen können in `screens.sound_voices` eine eigene Liste und in `screens.sound_volume` eine eigene Lautstärke haben. Kein Klang dauert länger als eine Sekunde, und alle unterscheiden sich voneinander.

Zwei optionale Hintergründe, beide standardmäßig aus: `sound.ambient` (zwei sehr leise tiefe Töne, ruhig, solange nichts rot ist, rauer, solange etwas rot ist) und `sound.tick` (ein sehr kurzes trockenes Klicken alle `sound.tick_seconds`, damit ein eingefrorener Bildschirm zu hören ist). Beide folgen dem Stummschalter, dem Hauptschalter und den Ruhezeiten.

## Einstellungen (Einstellungen, Ton)

Alle stehen in der Konfigurationsdatei und im Tab Einstellungen; Lautstärke, Thema und Schalter wirken sofort.

| Einstellung | Was sie tut |
|---|---|
| `sound.enabled` | Hauptschalter aller Töne der Seite. |
| `sound.on_new_red`, `sound.on_connection_lost`, `sound.on_warning`, `sound.on_resolved`, `sound.on_report`, `sound.on_lesson`, `sound.on_sentinel`, `sound.on_stuck`, `sound.on_score_drop`, `sound.on_info`, `sound.on_live_recovered` | Ein Schalter je Art (standardmäßig alle an). |
| `sound.theme` | `classic` (klare Töne) oder `soft` (tiefere, rundere, langsamere Töne). Jede Art behält in beiden ihren Rhythmus. |
| `sound.volume` | 1 bis 100, standardmäßig mäßig. |
| `sound.cooldown_seconds` | Pause zwischen zwei Tönen derselben Art. |
| `sound.quiet_enabled`, `sound.quiet_from_hour`, `sound.quiet_to_hour` | Ruhezeiten (standardmäßig aus): zwischen den beiden Uhrzeiten dieses Rechners ertönt nichts; sie dürfen über Mitternacht gehen. |
| `sound.server_beep` | Standardmäßig aus. Der Monitor selbst ertönt auf diesem Rechner, wenn keine Seite geöffnet ist oder der Browser den Ton sperrt: ein Muster für jede Ereignisart der Tabelle oben (Windows-Töne, macOS-Systemklänge, canberra-Ereignisse unter Linux), mit denselben Schaltern und Ruhezeiten wie die Seite, in einem Schub von höchstens drei Arten; nur lokal. |
| `sound.voices` | Gibt einer Ereignisart einen anderen Klang der Bibliothek (`art=klang`-Paare, durch Kommas getrennt). Standardmäßig leer. |
| `sound.ambient`, `sound.ambient_volume` | Hintergrundklang (standardmäßig aus) und seine Lautstärke, 1 bis 50. |
| `sound.tick`, `sound.tick_seconds` | Uhrticken (standardmäßig aus) und die Sekunden zwischen den Ticks, 1 bis 60. |
| `screens.sound_voices`, `screens.sound_volume` | Dasselbe wie `sound.voices`, nur für die Wandanzeigen, und ihre eigene Lautstärke (0 = die von `sound.volume`). |

## Jeden Ton testen

Unter Einstellungen, Oberfläche, spielt die Schaltfläche "Ton testen" das klassische Bing Bing, und je eine Schaltfläche pro Art spielt diese Art mit Lautstärke und Thema der Einstellungen. Die Marke "Ton" der Fußleiste schaltet in diesem Browser alles stumm.

## Wandanzeigen

Die Wandanzeigen (`/screen/...`) verwenden dieselben Töne mit demselben Thema, derselben Lautstärke, denselben Schaltern und Ruhezeiten. Sie sind standardmäßig aus: `screens.sound` muss an sein und das Fenster braucht `?sound=on`. Eine Anzeige, die niemand berührt, kann den vom Browser verlangten Klick nicht bekommen: Starten Sie den Browser der Anzeige mit seiner Option "Audio ohne Geste erlauben" (in Chromium `--autoplay-policy=no-user-gesture-required`) oder klicken Sie einmal ins Fenster.

## Wo es gespeichert wird

Die Stummmarke merkt sich jeder Browser; was die Seite von ihrem letzten Blick weiß, bleibt ebenfalls im Browser. Von den Tönen wird nichts an einen Server gesendet.
