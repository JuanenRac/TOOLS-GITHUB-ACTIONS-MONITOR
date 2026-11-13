<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](QUOTA.md) | [🇪🇸 Español](QUOTA_spa.md) | [🇫🇷 Français](QUOTA_fra.md) | [🇮🇹 Italiano](QUOTA_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](QUOTA_zho.md) | [🇯🇵 日本語](QUOTA_jpn.md) | [🇵🇹 Português](QUOTA_por.md)

# Mehr Kontingent, weniger Verbrauch

GitHub gibt jedem Konto ein begrenztes **Kontingent an API-Aufrufen**, das alle Werkzeuge teilen, die es nutzen. Dieser Leitfaden erklärt, wie es funktioniert und alle Wege, mit denen der Monitor weniger davon verbraucht.

## Wie das Kontingent funktioniert
- **REST**: 5000 Aufrufe pro Stunde und Nutzer (60 ohne Anmeldung). **GraphQL** hat ein eigenes, getrenntes Kontingent. Das `GITHUB_TOKEN` eines Workflows in Actions hat ebenfalls ein eigenes. Eine **GitHub-App** hat ein eigenes, von Ihrem getrenntes Kontingent, das mit den Repositories wächst, in denen sie installiert ist (etwa 10 000 pro Stunde bei 130 Repositories).
- Was zählt und was nicht: Ein bedingter Lesezugriff, der mit `304 Not Modified` (ETag) antwortet, zählt nicht; `rate_limit` abzufragen ist kostenlos; `git push`, `git fetch` und `git clone` nutzen die API nicht.

## Die Wege, mit denen der Monitor spart
1. **Bedingte Lesezugriffe** (ETag und `304`): `cache.etag.enabled` (standardmäßig an); die Seite zeigt, wie viele Lesezugriffe gespart wurden.
2. **Sparmodus**: nur die heißen Repositories alle 4 Minuten, der Rest alle 30; `modes.auto_low` (an) schaltet unter 1000 verbleibenden Aufrufen ein und über 2500 oder bei der Erneuerung zurück; Voreinstellungen in `modes.low`. Die Leiste sagt, dass die Zahlen alt sein können, und wie alt.
3. **Zentrales Panel als Basis**: `central.source` (`off`, `git`, `http`) liest `data/sentinel.json` Ihres Profil-Repositories, das ein Workflow mit eigenem Token aktualisiert; es verbraucht nichts von Ihrem Kontingent. `central.max_age_minutes` (120): älter gilt es als "veraltet" und wird nicht beachtet.
4. **Ein Hinweis, wenn das Kontingent aufgebraucht ist**: Das Lesen pausiert bis zur Erneuerung, die Seite sagt einmal "Kontingent erschöpft bis HH:MM" (nicht einen Fehler pro Repository) und setzt von selbst fort.
5. **Eine GitHub-App für das Lesen** (`github_app.*`), unten.
6. **GraphQL für ruhige Repositories (optional, standardmäßig aus)**: `network.graphql_checks` liest die Repositories, die nicht heiß sind, in Stapeln (`network.graphql_batch`, standardmäßig 20) über GraphQL, das ein eigenes Kontingent hat; ein Aufruf ersetzt viele REST-Aufrufe. Es sieht nur den letzten Commit des Standardzweigs (ein Workflow, der darauf nicht lief, fehlt) und liefert keine Laufzeiten, Versuche oder anderen Zweige; deshalb werden die heißen Repositories und jedes Repository, das GraphQL nicht beantwortet, im selben Zyklus weiter über REST gelesen. Die Abrechnung (Stapel, Repositories, Punkte, an REST übergebene Repositories) steht in der Zusammenfassung und im Zustand für die KI-Werkzeuge.

## Eine GitHub-App, Schritt für Schritt
1. In GitHub *Settings*, *Developer settings*, *GitHub Apps*, *New GitHub App*. Kein Webhook. **Nur-Lese**-Berechtigungen: Actions, Checks, Code scanning alerts, Commit statuses, Contents, Dependabot alerts, Issues, Pull requests, Secret scanning alerts und Metadata.
2. *Generate a private key* und die `.pem` **außerhalb jedes Repositories** speichern, nur für Sie lesbar.
3. *Install App* in Ihrem Konto, in allen Repositories, die Sie beobachten wollen.
4. Im Monitor: `github_app.enabled` an, `github_app.app_id` (die Nummer der App) und `github_app.key_path` (nur der PFAD des Schlüssels). `github_app.installation_id` kann leer bleiben.
5. Prüfen mit `GET /api/github-app/status` (nur dieser Computer): zeigt Name, Installation, gewährte Berechtigungen und Kontingent der App, nie den Schlüssel oder ein Token. Der Doctor prüft `openssl`, die Schlüsseldatei und ihre Rechte.

Sicherheit: Der Monitor liest, kopiert, druckt oder protokolliert den Schlüssel nie; er übergibt den Pfad an `openssl`, das ein JWT von höchstens zehn Minuten signiert. Das Installations-Token gilt eine Stunde, bleibt im Speicher und wird fünf Minuten früher erneuert. **Nur Lesezugriffe** nutzen es; Schreibzugriffe und Aktionen behalten Ihr Token. Fällt die App aus oder fehlt ihr eine Berechtigung, wird der Lesezugriff mit Ihrem Token wiederholt. Die Seite zeigt beide Kontingente.

## Wenn mehrere Werkzeuge dasselbe Kontingent teilen
Alle Werkzeuge des Kontos verbrauchen dieselben 5000 Aufrufe pro Stunde. Ein gutes Muster: ein kleiner Wrapper um `gh` mit einem **gemeinsamen Cache** von ein paar Minuten, einer **Reserve** (er verweigert Aufrufe, wenn weniger als etwa 1000 übrig sind, außer für Dringendes), Arbeit mit frischen Daten **direkt nach der Erneuerung** und nie `gh run watch` (es fragt ständig ab). Zum Beispiel ein Wrapper, der die Antwort jedes Lesezugriffs in einer temporären Datei mit dem Namen des Befehls speichert und 120 Sekunden lang erneut ausgibt und vor jedem anderen Aufruf `gh api rate_limit` prüft.

## Was man NICHT tun sollte
Nutzen Sie nicht mehrere Konten oder mehrere Tokens desselben Nutzers, um das Limit zu umgehen: Das verstößt gegen die Regeln von GitHub und kann das Konto sperren lassen. Nutzen Sie eine App, das zentrale Panel und den Sparmodus.

## Einstellungen
| Einstellung | Standard |
|---|---|
| `cache.etag.enabled` | an |
| `modes.auto_low` / `modes.auto_low_enter` / `modes.auto_low_exit` | an / 1000 / 2500 |
| `modes.low.*` (`refresh_seconds`, `cold_refresh_seconds`, `runs_per_repo`, `hot_hours`) | 240 / 1800 / 10 / 2 |
| `min_rate_remaining` | 800 |
| `central.source` / `central.max_age_minutes` | off / 120 |
| `github_app.enabled` / `github_app.app_id` / `github_app.key_path` / `github_app.installation_id` | off / leer / leer / leer |

## Fehlersuche und FAQ
- *"Kontingent erschöpft bis HH:MM"*: warten; der Monitor setzt von selbst fort. Andere Werkzeuge verbrauchen es vielleicht: deren Verbrauch ansehen.
- *Die Zahlen sind alt*: Der Sparmodus ist aktiv (gewählt oder automatisch); die Leiste sagt es.
- *Die App funktioniert nicht*: `/api/github-app/status` und den Doctor ansehen: openssl, Schlüsselpfad, Berechtigungen.
- *Kostet `git fetch` Kontingent?* Nein. Siehe auch [QUOTAS_deu.md](QUOTAS_deu.md) (Pläne und Minuten) und [MODES_deu.md](MODES_deu.md).

## Der Tab Kontingent und ein zweites Konto
Alles zum Kontingent steht an einem Ort: *Einstellungen*, Tab *Kontingent*. Er fasst die Modi zusammen (`modes.auto_low`, `modes.auto_low_enter`, `modes.auto_low_exit` und die Werte des Sparmodus in `modes.low.*`), das Sparen (`network.etag`, zusammen mit `cache.etag.enabled`), das zentrale Panel (`central.source`, `central.max_age_minutes`), die GitHub-App (`github_app.*`) und ein **zweites Konto für das Lesen**. Die Schaltflächen des Tabs zeigen das Kontingent jeder Quelle (Ihre Anmeldung, die App, das zweite Konto) mit der Erneuerungszeit, testen die App und das zweite Konto, listen fehlende Berechtigungen der App auf und wenden die empfohlenen Werte oder die Standardwerte an.

Das zweite Konto (`extra_reader.enabled`, `extra_reader.file`) ist ein Nur-Lese-Konto, dessen feingranulares Token in einer Textdatei außerhalb jedes Repositories liegt, nur für Sie lesbar; die Einstellung enthält NUR den Pfad dieser Datei. Der Monitor liest das Token im Moment der Nutzung, hält es im Speicher und speichert, druckt oder protokolliert es nie. Die Lesezugriffe verteilen sich nach den verbleibenden Aufrufen auf Ihre Anmeldung, die App und das zweite Konto (Zahl des kostenlosen Aufrufs `rate_limit` minus der seither gemachten Lesezugriffe); eine abgelehnte Quelle wird fünf Minuten ausgelassen und der Lesezugriff mit der nächsten wiederholt. Schreibzugriffe und Aktionen nutzen es nie. Es ist für ein eigenes Konto gedacht (zum Beispiel ein zweites eigenes Konto mit Lesezugriff auf die Repositories), nicht um das Limit mit fremden Konten zu umgehen.
