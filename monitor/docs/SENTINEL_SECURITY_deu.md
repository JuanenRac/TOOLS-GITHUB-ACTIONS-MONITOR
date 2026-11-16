<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SENTINEL_SECURITY.md) | [🇪🇸 Español](SENTINEL_SECURITY_spa.md) | [🇫🇷 Français](SENTINEL_SECURITY_fra.md) | [🇮🇹 Italiano](SENTINEL_SECURITY_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](SENTINEL_SECURITY_zho.md) | [🇯🇵 日本語](SENTINEL_SECURITY_jpn.md) | [🇵🇹 Português](SENTINEL_SECURITY_por.md)

# Der Sicherheitswächter

Der dritte Wächter, neben dem CI-Wächter und Collab. Er liest, ohne etwas auf GitHub zu schreiben, was GitHub selbst zur Sicherheit jedes Repositorys als offen oder fehlend meldet, und macht daraus Warnungen im Reiter Warnungen (Herkunft Sicherheit). Er gehört zur Ausgabe Complete und ist standardmäßig aus (`sentinels.security.enabled`); Lite hat keine Wächter.

## Was er liest und was er meldet

| Signal | Warnung | Stufe | Standardmäßig an |
|---|---|---|---|
| Offene Dependabot-Warnungen ab der Schwere `min_severity` (standardmäßig high) | `security.dependabot` | kritisch, wenn eine kritisch ist, Fehler, wenn eine hoch ist, sonst Warnung | ja |
| Offene Code-Scanning-Warnungen ab der Schwere `min_severity` | `security.code_scanning` | ebenso | ja |
| Offene Secret-Scanning-Warnungen | `security.secret` | immer kritisch (ein von GitHub gefundenes Geheimnis ist ein offenes Geheimnis) | ja |
| Der Standardbranch hat keinen Schutz | `security.branch_unprotected` | Warnung | ja |
| Workflows erhalten standardmäßig Schreibrechte | `security.workflow_write` | Warnung | ja |
| Es gibt keine CODEOWNERS-Datei | `security.codeowners_missing` | Information | nein |

Es gibt eine Warnung je Repository und Signal, mit den Zahlen nach Schwere in den Details. Jedes Signal lässt sich abschalten (`sentinels.security.signals.<Signal>.enabled`) und bei Dependabot und Code-Scanning mit einer anderen Mindestschwere versehen. Von einem archivierten Repository wird nichts weiter erfragt.

## Was er nicht prüfen konnte

Eine Quelle, die GitHub für ein Repository nicht beantwortet (die Funktion ist dort aus oder der Zugang darf sie nicht lesen: 403, 404), ist **keine** Warnung und **kein** Gesundheitszeugnis. Sie steht im Zustand unter `unavailable`, mit der Zahl der betroffenen Repositories, und die Seite sagt es. Die einzige Ausnahme ist der Schutz des Standardbranches: GitHub antwortet 404 für einen Branch ohne Schutz, und das ist der Befund; ein 403 ist dort nur „nicht lesbar“.

Wenn der größte Teil dessen, was in die Abwertung eingeht (Dependabot, Code-Scanning, Geheimnisse), nicht gelesen werden kann, ist die Stufe `unknown` statt `ok`, und der Sicherheitsanteil der Bewertung entfällt, statt als 100 zu zählen; der Zustand zeigt `sources_readable` und `sources_total`. Hört eine Quelle auf zu antworten, solange eine Warnung offen ist, bleibt die Warnung eine Woche lang bestehen (mit `unread_since` markiert) und wird nie als behoben gemeldet. Ein Repository, dessen Lesevorgänge weiter scheitern, wartet 5 Minuten, 30 Minuten und dann 6 Stunden bis zum nächsten Versuch, sodass wenige defekte Repositories nie die ganze Runde verbrauchen.

Jeder Wächter nennt jetzt seinen **Lebenszyklus**: `healthy` (gesund), `degraded` (eingeschränkt: manche Lesevorgänge schlagen fehl, eine Quelle ist nicht lesbar oder der erste Durchgang ist nicht beendet), `paused` (pausiert, wartet auf das GitHub-Kontingent), `error` (schlägt fehl und hat noch nichts gelesen) oder `off` (aus). „Keine Warnungen“ bedeutet nur etwas, wenn der Lebenszyklus `healthy` ist.

## Kosten

Ein Durchlauf liest höchstens `sentinels.security.max_repos_per_tick` Repositories (standardmäßig 5), zuerst die am längsten nicht angesehenen und etwas früher die mit einer offenen Warnung, mit einem Zyklus alle `sentinels.security.refresh_seconds` (standardmäßig 30 Minuten). Jedes Repository kostet höchstens sieben Lesevorgänge, fast alle bedingt: Ein unverändertes Repository verbraucht kein Kontingent; die CODEOWNERS-Datei wird, wenn verlangt, höchstens einmal am Tag gesucht. Der Wächter pausiert, solange das verbleibende Kontingent unter `sentinels.security.min_rate_remaining` liegt. Sein Zustand (`security_state.json`) hält die offenen Warnungen fest: Ein Neustart meldet nichts erneut, und der erste Blick auf ein Repository schreibt keine Ereignisse.

## Ein Besitzer je Befund

Die Panels des Reiters Wächter, die schon Sicherheitszahlen zeigten (Warnungen je Repository, alte Warnungen, Abdeckung von Dependabot und CodeQL, Dependabot-Pull-Requests), bleiben Panels. Die Warnungen des Reiters Warnungen zu diesen Signalen kommen nur von diesem Wächter, damit nichts doppelt ausgelöst wird.

## Ereignisse und Benachrichtigungen

Ein neuer Befund schreibt das Ereignis `security_new`, ein geschlossener `security_fixed` in den Feed, an dem die Benachrichtigungskanäle hängen; beides sind Arten, die man in den Benachrichtigungseinstellungen wählen kann, und die Einstellungen je Benutzer haben ein Feld Sicherheit. Beim ersten Ansehen eines Repositorys wird nichts gemeldet.

## Die Einstellungen

Auf der Einstellungsseite, Unterreiter Wächter, Block Sicherheit: `sentinels.security.enabled`, `sentinels.security.refresh_seconds`, `sentinels.security.max_repos_per_tick`, `sentinels.security.min_rate_remaining`, `sentinels.security.repos`, `sentinels.security.signals.dependabot.enabled`, `sentinels.security.signals.dependabot.min_severity`, `sentinels.security.signals.code_scanning.enabled`, `sentinels.security.signals.code_scanning.min_severity`, `sentinels.security.signals.secret.enabled`, `sentinels.security.signals.branch.enabled`, `sentinels.security.signals.workflow.enabled` und `sentinels.security.signals.codeowners.enabled`. Die Punkte, die jeder Befund vom Sicherheitsteil der Punktzahl abzieht (`sentinels.security.penalty`), werden aus der Datei gelesen; siehe die Beispieldatei.
