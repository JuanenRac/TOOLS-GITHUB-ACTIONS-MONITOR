<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](ORGANIZATIONS.md) | [🇪🇸 Español](ORGANIZATIONS_spa.md) | [🇫🇷 Français](ORGANIZATIONS_fra.md) | [🇮🇹 Italiano](ORGANIZATIONS_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](ORGANIZATIONS_zho.md) | [🇯🇵 日本語](ORGANIZATIONS_jpn.md) | [🇵🇹 Português](ORGANIZATIONS_por.md)

# Organisationen und große Konten

Wie Sie den Monitor auf eine Organisation oder auf ein persönliches Konto mit Hunderten Repositories richten und was zu tun ist, wenn ein Lesevorgang leer zurückkommt.

## 1. Das kleinste Token, das funktioniert

Der Monitor liest nur. Verwenden Sie die Anmeldung von `gh` (`gh auth login`) oder ein Token in `GH_TOKEN` und geben Sie ihm nur das Nötigste.

| Art des Tokens | Was es braucht |
|---|---|
| **Klassisch** (Personal Access Token) | `repo` für private Repositories (`public_repo` genügt, wenn alles öffentlich ist) und `read:org`, um die Repositories und Teams einer Organisation aufzulisten. Optional: `security_events` (Code-Scanning-Warnungen, Panel A3), `read:project` (die Projects-Boards, Panel A9). `workflow` oder ein Schreib-Scope ist nicht nötig. |
| **Fein abgestuft** | Nur ein *Ressourcenbesitzer*: ein Token je Organisation (oder je persönlichem Konto). Repository-Zugriff: alle oder die ausgewählten. Nur lesende Berechtigungen: Metadata, Actions, Contents, Pull requests, Issues, Administration (Rulesets und Branch-Regeln), Code scanning alerts, Dependabot alerts, Secret scanning alerts. Eine Organisation kann verlangen, dass ein Besitzer das Token zuerst genehmigt. |
| **GitHub App** | Liest mit dem Kontingent der App statt mit Ihrem (siehe `QUOTA.md`). |

Ein **persönliches Konto** (`github_owner` ist ein Benutzer) braucht für die eigenen Repositories nicht mehr als das Obige. Die Repositories einer Organisation, der Sie angehören, werden mit einem Token gelesen, dessen Ressourcenbesitzer (fein abgestuft) oder Scopes (klassisch) diese Organisation einschließen.

## 2. Single Sign-on (SSO) und private Repositories

Erzwingt die Organisation SAML-Single-Sign-on, muss ein klassisches Token dafür autorisiert sein: Öffnen Sie auf GitHub *Settings > Developer settings > Personal access tokens*, wählen Sie das Token und klicken Sie *Configure SSO > Authorize*. Eine Anmeldung mit `gh auth login` wird im Browser beim Bestätigen der Organisation autorisiert. Bis dahin antwortet GitHub mit `403` (*Resource protected by organization SAML enforcement*) oder, schlimmer, mit `200` und lässt die privaten Repositories weg (Header `X-GitHub-SSO: partial-results`), was wie eine Organisation mit wenigen Repositories aussieht.

Ein Token, das ein privates Repository nicht sehen kann, erhält `404`, genau als gäbe es es nicht. Eine leere Antwort kann also bedeuten: SSO nicht autorisiert, ein fehlender Scope oder eine fehlende Berechtigung, ein privates Repository, das der Zugang nicht sieht, oder gar keine Actions. Der nächste Abschnitt unterscheidet sie.

## 3. `--doctor` erklärt es

`py -3 bin/actions_monitor.py --doctor` (auch `bin/monitor_cli.py doctor`) macht drei kleine Lesevorgänge und meldet zwei Zeilen:

- **Der Zugang kann das Konto oder die Organisation lesen** (`access`): `ok` mit Anmeldename und Scopes; oder `warn` mit der Ursache im Detail: `sso` (nicht autorisiert oder private Repositories verborgen), `rate_limited`, `scope` (eine Berechtigung fehlt), `not_found` (das Konto existiert nicht oder ist nicht sichtbar), `forbidden`; `fail`, wenn GitHub die Zugangsdaten ablehnt. Ein fein abgestuftes Token hat keine Scopes zum Auflisten, und die Zeile sagt das.
- **Die Lesevorgänge pro Stunde passen ins Kontingent** (`estimate`): die Repositories des Kontos und die Lesevorgänge pro Stunde, die die aktuellen Einstellungen bräuchten, gegenüber den 5.000 pro Stunde eines persönlichen Tokens. Es ist eine Schätzung ohne Aufrufe: das Polling der Runs (ein Zehntel der Repositories heiß, alle `refresh_seconds`; der Rest alle `cold_refresh_seconds`), der Wächter (höchstens `sentinel.budget_per_hour`) und, wenn Workflow-Dateien ohne Klone gelesen werden, deren Anteil. `warn` über 60 %. Zum Senken: `cold_refresh_seconds` erhöhen, den Low-Modus einschalten, weniger Repositories beobachten (`repos`) oder mit einer GitHub App lesen.

Dieselben Ursachen werden mit dem Repository überall genannt, wo der Monitor Workflow-Dateien nicht lesen konnte: Das Wächter-Panel A13 listet sie als *nicht auswertbar* mit Grund, nie als stummes „keine Daten“.

## 4. Ein fremdes Konto beobachten (Beobachter ohne Berechtigungen)

Jedes Token kann die öffentlichen Repositories jedes Kontos lesen; so beobachten Sie eine Open-Source-Organisation mit einem Token ganz ohne Scope. Was ein Beobachter nicht bekommt und der Monitor als *unbekannt* und nie als *in Ordnung* behandelt: Rulesets und Branch-Schutz, Dependabot-, Code-Scanning- und Secret-Scanning-Warnungen, Einstellungen sowie die Run-Listen von Repositories mit deaktivierten Actions. Panels, die davon abhängen (A3, Teile von A6), bleiben für diese Repositories leer oder als nicht auswertbar markiert. Es wird nie etwas geschrieben, daher ist keine Schreibberechtigung nötig.

## 5. Bekannte Grenzen

- Das Kontingent beträgt 5.000 Lesevorgänge pro Stunde für ein persönliches Token; eine in einer großen Organisation installierte GitHub App hat mehr (siehe `QUOTA.md`). Die Schätzung oben zeigt am schnellsten, ob Sie hineinpassen.
- Der Monitor liest eine Stichprobe der letzten Runs je Repository. Ein Repository, das Hunderte Runs pro Stunde startet, wird über diese Stichprobe gesehen, nicht Run für Run.
- GitHub bewahrt Logs und Artefakte eines Runs standardmäßig 90 Tage auf; was GitHub gelöscht hat, kann der Monitor nicht lesen.
- Ein fein abgestuftes Token gehört einem Besitzer: Zwei Organisationen zu beobachten braucht zwei Tokens (zwei Konten des Monitors, siehe `ACCOUNTS.md`).
- Organisationen, die die Genehmigung von Tokens verlangen oder klassische Tokens sperren, brauchen zuerst eine Aktion eines Besitzers; keine Einstellung des Monitors kann das umgehen.
