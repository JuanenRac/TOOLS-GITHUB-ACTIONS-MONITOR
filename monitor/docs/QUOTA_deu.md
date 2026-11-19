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

Sicherheit: Der Monitor liest den Schlüssel nur in den Arbeitsspeicher, um ein JWT von höchstens zehn Minuten zu signieren (mit der Standardbibliothek, ohne `openssl`; `openssl` ist nur die Rückfalloption), und kopiert, druckt oder protokolliert ihn nie. Das Installations-Token gilt eine Stunde, bleibt im Speicher und wird fünf Minuten früher erneuert. **Nur Lesezugriffe** nutzen es; Schreibzugriffe und Aktionen behalten Ihr Token. Fällt die App aus oder fehlt ihr eine Berechtigung, wird der Lesezugriff mit Ihrem Token wiederholt. Die Seite zeigt beide Kontingente.

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

Das zweite Konto (`extra_reader.enabled`, `extra_reader.file`) ist ein Nur-Lese-Konto, dessen feingranulares Token in einer Textdatei außerhalb jedes Repositories liegt, nur für Sie lesbar; die Einstellung enthält NUR den Pfad dieser Datei. Der Monitor liest das Token im Moment der Nutzung, hält es im Speicher und speichert, druckt oder protokolliert es nie. Die Lesezugriffe verteilen sich nach den verbleibenden Aufrufen auf Ihre Anmeldung, die App und das zweite Konto (Zahl des kostenlosen Aufrufs `rate_limit` minus der seither gemachten Lesezugriffe); eine abgelehnte Quelle wird fünf Minuten ausgelassen und der Lesezugriff mit der nächsten wiederholt. Schreibzugriffe und Aktionen nutzen es nie. Es ist für ein eigenes Konto gedacht (zum Beispiel ein zweites eigenes Konto mit Lesezugriff auf die Repositories), nicht um das Limit mit fremden Konten zu umgehen. Die Datei muss im Kontenordner des Monitors liegen (`accounts/` oder der Ordner, den `MONITOR_ACCOUNTS_DIR` nennt) und wird nie über einen Link gelesen; `extra_reader.any_folder` (standardmäßig aus) hebt die Ordnerregel auf. Was davon abhängt, wer fragt (dein Konto, seine Organisationen, die Benachrichtigungen, eine Suche nach `@me`, `gh auth`, `gh repo list` ohne Eigentümer), beantwortet immer dein eigener Login, und nur ein einfaches Lesen `gh api ENDPOINT` (höchstens mit den Optionen `--jq`, `--paginate`, `-H`, `-i` und `--cache`) wird auf die Quellen verteilt: Jeder andere Aufruf geht an deinen Login.

## Das Programm openssl und ein Monitor je Port

Der Monitor sucht `openssl` im PATH und, falls es dort fehlt, dort, wo Git for Windows es ablegt (`Git\usr\bin`, `Git\mingw64\bin` in Programme und in den Programmen des Benutzers) sowie in den üblichen Ordnern von macOS und Linux; so findet es auch ein Monitor, der aus einer `.bat` oder als Dienst gestartet wird. `github_app.openssl_path` (absoluter Pfad zum Programm) wählt eines von Hand. `/api/github-app/status` zeigt `openssl` und `openssl_path`, und der Doctor nennt das signierende Programm, wenn es nicht das aus dem PATH ist.

Unter Windows wird der Port des Monitors exklusiv gebunden (SO_EXCLUSIVEADDRUSE): zwei Prozesse können nicht mehr gleichzeitig auf 8765 lauschen. Und ein Monitor, der startet, während schon ein Monitor auf seinem Port antwortet, sagt das und beendet sich, statt einen anderen Port zu suchen.

## Aufteilung des Kontingents: bevorzugte Quelle und Reserve

Standardmäßig geht jeder Lesezugriff an die Quelle (Benutzer, GitHub App, zweites Konto) mit den meisten freien Aufrufen. Der Block `readpool` ändert das im Tab Kontingent der Einstellungen, mit den bisherigen vorsichtigen Standardwerten (`auto`, Reserve 0):

- `readpool.prefer.<Art>` (`auto`, `user`, `app`, `extra`): die Quelle, die eine ART Lesezugriff zuerst beantwortet. Die Arten ergeben sich aus dem Aufruf: `runs` (Läufe, Workflows, Checks), `security` (Code Scanning, Dependabot, Secret Scanning), `issues` (Issues und Pull Requests), `history` (Releases, Commits, Tags, Inhalte), `discovery` (Organisationen, Suche, Repository-Listen) und `other`. Fällt die bevorzugte Quelle aus oder liegt sie unter ihrer Reserve, antworten die anderen, der Benutzer zuletzt.
- `readpool.reserve.<Quelle>` (0 bis 4000): in dieser Quelle freigehaltene Aufrufe. Solange eine Quelle höchstens so viele Aufrufe wie ihre Reserve hat, liest der Monitor nicht mit ihr, wenn eine andere kann. Mit `readpool.reserve.user` bleiben dem `gh` deiner Werkzeuge und Agenten Aufrufe.

Schreibzugriffe und Aktionen nutzen immer das Token des Benutzers. Die Kontingentanzeige und die Arbeitsmodi (schnell und Turbo) zählen die SUMME aller Quellen: die Kachel zeigt die Summe, ihr Tooltip den Wert jeder Quelle, und der Tab Kontingent (Status) fügt neben dem Kontingent von Benutzer, App und zweitem Konto eine Zeile mit der Gesamtsumme hinzu.

## Weniger lesen: Webhook zuerst und kostenlose Quellen

Beide Wege sind **standardmäßig aus** und betreffen nur ruhige Repositories (deren letzte Läufe alle beendet und grün sind). Ein laufendes, rotes oder von einem Ereignis berührtes Repository wird wie immer gelesen.

- `savings.webhook_first`: Solange der eingehende Webhook lebt (er hat in den letzten `savings.webhook_window_minutes` Minuten ein Ereignis geliefert), wird ein ruhiges Repository in seinem langsamen Durchlauf nicht gelesen: GitHub meldet, wenn etwas passiert. Alle `savings.webhook_full_minutes` Minuten wird es trotzdem vollständig gelesen. Ohne lebenden Webhook ändert sich nichts.
- `savings.webhook_live_per_repo`: macht „lebendig“ zur Sache jedes einzelnen Repositorys. Nur ein ruhiges Repository, dessen EIGENE Ereignisse in den letzten `savings.webhook_window_minutes` Minuten ankamen, überspringt sein langsames Lesen; eines, dessen Webhook nie eingerichtet wurde oder ausfiel, wird wie immer gelesen, während die anderen geschont werden. Es spart weniger Lesevorgänge, und das Webhook-Panel zählt die Repositorys, die für sich lebendig sind. Standardmäßig aus; wirkt zusammen mit `savings.webhook_first`.
- `savings.feeds.enabled`: Bevor ein ruhiges Repository mit der API gelesen wird, wird der neueste Commit seines Standardzweigs bei einer Quelle erfragt, die kein Kontingent kostet - dem öffentlichen Atom-Feed der Commits, `git ls-remote` oder einem von beiden (`savings.feeds.method`: `atom`, `git`, `auto`). Ist es der Commit des letzten vollständigen Lesens, bleibt das Repository, wie es ist. Alle `savings.feeds.max_age_minutes` Minuten wird es trotzdem vollständig gelesen. Nur öffentliche Repositories: Bei einem privaten, einem Fehler oder einer seltsamen Antwort wird das Repository wie immer mit der API gelesen. Nur GET-Anfragen an github.com verlassen den Rechner, nie ein Passwort, und nichts wird geschrieben. Wird nicht benutzt, wenn der Monitor vom Netz getrennt ist (air-gapped).

Was es kostet: Ein Lauf, der ohne Push beginnt (ein Zeitplan, eine Wiederholung), wird bei einem ruhigen Repository erst beim nächsten vollständigen Lesen gesehen, nicht sofort. Der Reiter Kontingent (Zustand) zeigt die Lesevorgänge, die jeder Weg seit dem Start des Monitors eingespart hat (etwa ein API-Aufruf je Lesevorgang): bedingte Lesevorgänge, GraphQL, Webhook zuerst, Atom-Feed, git und zentrales Panel.

## Große Konten: was die Laufliste abdeckt, und ein Budget

Ein Repository, das Hunderte Läufe pro Stunde startet, füllt eine Liste von 20-100 Läufen in Minuten; ein älterer Fehler oder ein selten laufender Workflow ist dann schlicht nicht darin. Der Monitor sagt das, statt grün zu wirken:

- **Abdeckung**: Die Repository-Tabelle zeigt, wie weit jede Liste zurückreicht. Eine volle Liste, die weniger als `sampling.min_coverage_minutes` zurückreicht, wird als *geringe Abdeckung* markiert; eine kürzere Liste als angefordert ist *vollständig* (sie enthält den ganzen Verlauf); eine Gesamtzahl von 2.500 oder 40.000 ist die Stelle, an der GitHub aufhört zu zählen, und wird deshalb als *mindestens* gezeigt. Der Block `sampling` von `GET /api/data` trägt dieselben Zahlen.
- **Zweiter Blick**: Mit `sampling.default_branch_probe` fragt eine volle Liste zusätzlich die Pushes auf den Standard-Branch ab (ohne Pull Requests), eine Anfrage mehr pro Lesevorgang, damit die Läufe, die über Rot auf main entscheiden, nicht von Pull Requests und Zeitplänen verdrängt werden.
- **A2 gemeinsam**: Bei einem Repository mit `sentinel.a2_resolve_batch_min` oder mehr nachzuschlagenden Workflows werden einmal die neuesten abgeschlossenen Läufe des Standard-Branches abgefragt (höchstens `sentinel.a2_resolve_batch_pages` Seiten zu 100) und gemeinsam geklärt; was diese Liste nicht zeigt, wird einzeln erfragt. Bei 100 oder mehr Workflows dauert das einige Zyklen statt vier Workflows pro Zyklus.
- **Budget**: `sampling.api_budget_per_hour` (0 = keines) begrenzt die Anfragen für Lauflisten pro Stunde. Danach werden Repositorys mit rotem Workflow zuerst gelesen, ein Zehntel des Budgets bleibt immer für sie reserviert, die übrigen warten; die Seite sagt, wie viele. Die Schätzung der Anfragen pro Stunde für Repository-Zahl und Intervalle erscheint ab 3.500 (GitHub erlaubt 5.000 pro Stunde) oder sobald ein Budget gesetzt ist.

Die Standardwerte ändern bei einem Konto mit wenigen Repositorys nichts: Zweiter Blick und Budget sind aus, und die Markierung geringer Abdeckung erscheint nur, wenn eine volle Liste weniger als eine halbe Stunde zurückreicht.

## Wenn die App eingeschaltet ist und nicht benutzt wird

Ist `github_app.enabled` an, die App kann aber kein Token liefern, laufen die Lesezugriffe mit Ihrem Token weiter und es gilt das kleinere Kontingent des Benutzers. Das geschieht nie stumm: Der Doctor wird gelb mit der Ursache, ein Fehler wird einmal in der Liste der verschluckten Fehler vermerkt und der Tab Kontingent zeigt eine Zeile `GitHub App` mit Ursache und verwendetem Limit. Die Ursachen: Der Schlüssel ist nicht lesbar oder kein RSA-Schlüssel ohne Passphrase (`key_unreadable`), der Schlüssel konnte nicht signieren (`sign_failed`), die App ist im Konto nicht installiert (`app_not_installed`), GitHub hat das Token abgelehnt (`token_refused`) und die App ist an, aber ohne Nummer oder Schlüsseldatei (`not_configured`). Derselbe Hinweis steht in `GET /api/quota` als `app` und in `GET /api/github-app/status` als `signer` und `code`.
