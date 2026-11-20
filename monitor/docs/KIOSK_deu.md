<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](KIOSK.md) | [🇪🇸 Español](KIOSK_spa.md) | [🇫🇷 Français](KIOSK_fra.md) | [🇮🇹 Italiano](KIOSK_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](KIOSK_zho.md) | [🇯🇵 日本語](KIOSK_jpn.md) | [🇵🇹 Português](KIOSK_por.md)

# Kiosk: der Monitor auf einem Fernseher oder einer Wand

Das Kiosk-Profil ist die Seite des Monitors für einen Bildschirm, den niemand berührt: ohne Kopfzeile, ohne Tabs, mit größerer Schrift und, wenn Sie möchten, hohem Kontrast und einem Wechsel durch einige Tabs. Es verwendet, was die Seite schon kennt (`?screen=`, `?tabs=`, `?rotate=`, `?chrome=0`; siehe [SCREENS_deu.md](SCREENS_deu.md)), und fügt zwei Parameter hinzu. Es liest nichts von GitHub und schreibt nichts: Es bestimmt nur, wie die Seite aussieht.

Es ist **standardmäßig aus**. Ist `kiosk.enabled` aus, ignoriert die Seite `kiosk=1` in der Adresse, ein von anderswo kopierter Link ändert also nichts.

## Die Adresse

`python bin/monitor_cli.py kiosk [PRESET] [--account ID]` gibt sie aus; es braucht keinen laufenden Monitor. Zum Beispiel gibt `kiosk ops` aus:

```
http://127.0.0.1:8765/?screen=1&tabs=now,al,charts&chrome=0&kiosk=1&scale=150
```

| Parameter | Bedeutung |
|---|---|
| `kiosk=1` | schaltet das Profil ein (nur wenn `kiosk.enabled` an ist) |
| `scale=%` | die Schriftgröße, von 100 bis 400 (ein Wert außerhalb des Bereichs wird in ihn gebracht) |
| `contrast=1` / `contrast=0` | hoher Kontrast an oder aus für dieses Fenster (die Einstellung `kiosk.high_contrast` ist der Standard) |
| `rotate=SECONDS` | durch die Tabs von `tabs=` wechseln (der bestehende Parameter; der Befehl fügt ihn nur hinzu, wenn der Wechsel an ist) |
| `chrome=0`, `screen=`, `tabs=`, `account=` | die bestehenden |

## Presets

| Preset | Tabs |
|---|---|
| `ops` | Jetzt, Alarme, Diagramme |
| `team` | Alarme, Team-Gesundheit |
| `release` | Jetzt, Repositories, Berichte |
| `quiet` | nur Alarme |

## Einstellungen (Einstellungen, Befehlszeile und Kiosk)

| Einstellung | Standard | Bedeutung |
|---|---|---|
| `kiosk.enabled` | aus | schaltet das Profil ein |
| `kiosk.font_scale_percent` | 150 | die Schriftgröße, 100 bis 400 |
| `kiosk.high_contrast` | aus | schwarzer Hintergrund und weiße Linien |
| `kiosk.rotate_views` | aus | ein Preset mit mehreren Tabs wechselt den Tab von selbst; aus, zeigt der Bildschirm den ersten Tab des Presets |
| `kiosk.rotate_seconds` | 30 | wie lange jeder Tab bleibt (5 bis 600) |

Die Größe wird mit dem Zoom der Seite angewendet, jede Zahl und jede Tabelle wächst also mit. Ein Wert außerhalb seines Bereichs ist kein Fehler: Er wird durch den Standard ersetzt.
