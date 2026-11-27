<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](TRAFFIC.md) | [🇪🇸 Español](TRAFFIC_spa.md) | [🇫🇷 Français](TRAFFIC_fra.md) | [🇮🇹 Italiano](TRAFFIC_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](TRAFFIC_zho.md) | [🇯🇵 日本語](TRAFFIC_jpn.md) | [🇵🇹 Português](TRAFFIC_por.md)

# Downloads und Zugriffe

Ein auf diesem Rechner gespeicherter Verlauf, wie oft die Dateien Ihrer Releases heruntergeladen werden, sowie der Besuche und Klone der gewählten Repositorys. GitHub behält Besuche und Klone nur 14 Tage und führt keinen Verlauf der Downloads; was nicht gespeichert wird, ist verloren. Edition Complete; standardmäßig aus.

## Einschalten

Schalten Sie `traffic.enabled` ein (Einstellungen > Downloads und Zugriffe) und tragen Sie die Repositorys in `traffic.repos` ein, eines pro Zeile: ein Name (des beobachteten Kontos) oder Eigentümer/Name, höchstens 50. Bei leerer Liste wird nichts gelesen. Die Tafel erscheint im Reiter Repositorys.

## Was gelesen wird und was es kostet

Nur GET-Anfragen, nach einem Zyklus: jedes gewählte Repository höchstens einmal am Tag (UTC), `traffic.repos_per_cycle` davon pro Zyklus. Ein Repository kostet eine bis fünf Anfragen Ihres GitHub-Kontingents (Releases, bis zu 300; Besuche; Klone). Ist das Kontingent erschöpft, wird angehalten und später erneut versucht. `traffic.views_clones` schaltet Besuche und Klone aus. Installationen ohne Netz lesen nichts. Gewartet wird auch, solange die Verbindung fehlt, die erste Lesung läuft oder höchstens doppelt so viele Anfragen wie `min_rate_remaining` übrig sind.

## Berechtigungen

Besuche und Klone erhält nur ein Token mit Schreibzugriff (push) auf das Repository. Ohne ihn sagt es die Tafel für dieses Repository; das ist kein Fehler und die Downloads werden weiter gespeichert.

## Was die Zahlen bedeuten

Downloadzahlen sind anonym, enthalten Roboter und Spiegel und zählen die Archive "Source code" nicht, die GitHub einem Release hinzufügt. Neue Downloads vergleichen eine Lesung mit der vorigen, nur für die noch vorhandenen Dateien. Ein nicht gelesener Tag ist eine Lücke, nie eine Null.

## Export und Datenschutz

Die Tafel exportiert zwei CSV-Dateien: eine Zeile je Repository und Tag und eine je Release-Datei und Tag, an dem sich ihre Zahl änderte. `monitor_cli.py traffic export` gibt die erste aus. Tage, die älter als `traffic.keep_days` sind, werden gelöscht. Der Verlauf bleibt im Datenordner dieses Rechners; nichts wird irgendwohin gesendet.
