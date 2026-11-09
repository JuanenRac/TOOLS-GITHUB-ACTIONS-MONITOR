<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ACCOUNTS.md) | [🇪🇸 Español](ACCOUNTS_spa.md) | [🇫🇷 Français](ACCOUNTS_fra.md) | [🇮🇹 Italiano](ACCOUNTS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](ACCOUNTS_zho.md) | [🇯🇵 日本語](ACCOUNTS_jpn.md) | [🇵🇹 Português](ACCOUNTS_por.md)

# Mehrere Konten

Die komplette Ausgabe kann mehrere GitHub-Konten (eine Person oder eine Organisation) gleichzeitig beobachten. Jedes Konto ist ein eigener Monitor: ein getrennter Prozess mit eigenem Ordner, eigenem Port auf `127.0.0.1`, eigener Konfiguration und eigener Messung des GitHub-Kontingents. Ein Absturz, eine langsame Antwort oder ein Ratenlimit eines Kontos berührt die anderen nie. Die Lite-Ausgabe hat ein Konto und nichts davon: Sie zeigt nicht einmal die folgenden Optionen.

## Wenn nichts zu tun ist

Ohne einen Ordner `accounts/` arbeitet der Monitor genau wie bisher: ein Konto, seine Dateien neben dem Code. Du liest nur weiter, wenn du mehr als eines willst.

## Der Ordner der Konten

```
accounts/
  global.json              optional: {"default_account": "personal", "enabled_accounts": "all"}
  personal/
    actions_monitor.json   die Konfiguration dieses Kontos (sein github_owner, repos, Wächter...)
  org-acme/
    actions_monitor.json
```

Die ID eines Kontos besteht aus Kleinbuchstaben, Ziffern, `_` und `-` (bis zu 40 Zeichen), weil sie ein Ordnername ist; alles andere wird abgelehnt. `enabled_accounts` ist `"all"` oder eine Liste; `default_account` ist das Konto, das sich öffnet, wenn keines verlangt wird. `MONITOR_ACCOUNTS_DIR` verschiebt den Ordner. Jedes Konto hält Cache, Ereignisse, Analytik, Wächterzustand und Protokolle in seinem eigenen Ordner, sodass sich zwei Konten nie eine Datei teilen.

## Von einem Konto zu mehreren

```
python actions_monitor.py --migrate-accounts          # zeigt, was kopiert würde, schreibt nichts
python actions_monitor.py --migrate-accounts --apply  # kopiert es nach accounts/default/
python actions_monitor.py --accounts                  # listet die Konten
```

Die Originale werden nie verschoben oder gelöscht: Du löschst sie selbst, wenn du alles geprüft hast. Ein zweiter Lauf verweigert sich, damit sich zwei Zustände nie mischen. Um ein Konto hinzuzufügen, lege `accounts/<id>/actions_monitor.json` mit seinem `github_owner` an (kopiere die Vorlage `actions_monitor.example.json`).

## Ausführen

`python actions_monitor.py` mit einem Ordner `accounts/` startet den Supervisor, einen kleinen Prozess auf dem üblichen Port (8765), der pro Konto einen Monitor startet und der Seite und den Werkzeugen eine einzige Adresse gibt. Er liest nichts von GitHub und schreibt nichts. Stirbt ein Konto, startet er es mit wachsender Wartezeit neu (2, 5, 15, 30, 60 und danach 120 Sekunden), und die Übersicht meldet es in der Zwischenzeit als ausgefallen. `python actions_monitor.py --account personal` führt nur dieses Konto aus, als gewöhnlicher Monitor.

## Die Seite

Die Seite ist die bekannte, mit einer Kontoauswahl oben in der Seitenleiste und einem Eintrag **Alle Konten**, der eine Karte pro Konto zeigt (Zustand, Repositorys, laufend, fehlerhaft) und jedes davon öffnet. Jedes Fenster behält sein eigenes Konto und seine Ansicht: Sie werden aus der Adresse gelesen, nie aus einer einzigen Einstellung, die ein anderes Fenster überschreiben würde.

| Adresse | Was sie zeigt |
|---|---|
| `/?account=org-acme` | die Seite dieses Kontos |
| `/?account=all` | die Karten aller Konten |
| `/?view=now` `alerts` `charts` `repos` `settings` `live` | ein Panel |
| `/?chrome=0` | ohne Kopfzeilen-Tasten, Tabs und Filter: ein Bildschirm für eine Wand oder einen zweiten Monitor |

Für mehrere Bildschirme öffne ein Fenster pro Ansicht, zum Beispiel `?view=now&chrome=0`, `?view=alerts&chrome=0` und `?view=live&chrome=0`. Ein einziger Monitor bedient alle, sodass du das Kontingent nicht doppelt verbrauchst. Die Ansicht **Live** zeigt die letzten von GitHub gesendeten Ereignisse, den Zustand des Webhook-Empfängers (an oder aus, wie viele Zustellungen angenommen, ignoriert, wiederholt oder abgelehnt wurden, nie das Geheimnis) und eine Auswahl des Arbeitsmodus.

## Die API

`GET /api/accounts` ist die Übersicht, `GET /api/accounts/<id>/status` ein Konto, und jede andere Anfrage unter `/api/` geht an das Konto, das mit `?account=<id>` oder dem Header `X-Account-Id` genannt wird (das Standardkonto, wenn keines angegeben ist). Ein unbekanntes Konto ergibt 404. Die Zugriffsregeln sind die eines einzelnen Monitors: dieselbe Prüfung von Host und Origin und dasselbe Zugriffstoken im Netzwerkmodus. Das Einmal-Token einer Änderung muss bei demselben Konto angefordert werden, an das die Änderung gesendet wird.

## Ein Webhook für alle

`POST /api/webhook` ist eine einzige Adresse für die ganze Installation. Der Supervisor liest nur den Eigentümer des Repositorys in der Nutzlast (`repository.full_name`) und reicht das Ereignis unverändert an das Konto weiter, dessen `github_owner` dieser Eigentümer ist; das Konto prüft die Signatur mit seinem eigenen Geheimnis. Ein Eigentümer, den niemand beobachtet, wird beantwortet und ignoriert. Um das Konto selbst zu wählen, hänge `?account=<id>` an.

## Grenzen und Ehrlichkeit

- Mehrere Konten sind mehrere Prozesse: Jeder liest GitHub für sich, sodass das Kontingent vom verwendeten Login geteilt wird. Beobachte es in den Karten und senke bei Bedarf `refresh_seconds` oder `max_workers` pro Konto.
- Die Prüfungen, die einen echten Browser, echte GitHub-Konten und einen echten Webhook-Tunnel brauchen, führst du selbst aus; die Tests nutzen Platzhalter für den Monitor eines Kontos und rufen GitHub nie auf.
- Eine spätere Version holt die Konten in einen Prozess; Ordneraufbau und API von oben bleiben.
