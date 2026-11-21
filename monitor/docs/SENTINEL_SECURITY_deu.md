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
| Ein wichtiger Run (Push auf den Standard-Branch, manueller Run, `pull_request_target`-Run), den der Monitor gesehen hatte, wurde gelöscht | `security.runs_deleted` | error | nein |

**Gelöschte Runs** (`security.runs_deleted`, standardmäßig aus): Nach einem Leck von Secrets ist das Löschen des Runs, der sie ausgegeben hat, der übliche Weg, die Spur zu beseitigen, und GitHub hinterlässt keinen sichtbaren Eintrag. Mit `sentinels.security.signals.runs_deleted.enabled` führt der Wächter eine kurze private Liste der wichtigen Runs, die er gesehen hat, und fragt, wenn einer nicht mehr in der Run-Liste steht, genau diesen Run ab: Ein ausdrückliches 404 ist eine Löschung; eine Ablehnung (403), ein Netzwerkfehler oder ein 5xx zählt nie. Ein Run, der älter ist als `sentinels.security.signals.runs_deleted.check_window_days` (14), wird nicht abgefragt (die Aufbewahrung des Kontos kann ihn entfernt haben), und eine bemerkte Löschung bleibt ebenso viele Tage als Meldung bestehen. Pro Repository und Runde werden höchstens `sentinels.security.signals.runs_deleted.max_checks` (50) einzelne Runs abgefragt. Die Meldung nennt Workflow, Auslöser und Branch, nie Inhalte des Runs.

Es gibt eine Warnung je Repository und Signal, mit den Zahlen nach Schwere in den Details. Jedes Signal lässt sich abschalten (`sentinels.security.signals.<Signal>.enabled`) und bei Dependabot und Code-Scanning mit einer anderen Mindestschwere versehen. Von einem archivierten Repository wird nichts weiter erfragt.

## Was er nicht prüfen konnte

Eine Quelle, die GitHub für ein Repository nicht beantwortet (die Funktion ist dort aus oder der Zugang darf sie nicht lesen: 403, 404), ist **keine** Warnung und **kein** Gesundheitszeugnis. Sie steht im Zustand unter `unavailable`, mit der Zahl der betroffenen Repositories, und die Seite sagt es. Die einzige Ausnahme ist der Schutz des Standardbranches: GitHub antwortet 404 für einen Branch ohne Schutz, und das ist der Befund; ein 403 ist dort nur „nicht lesbar“.

Wenn der größte Teil dessen, was in die Abwertung eingeht (Dependabot, Code-Scanning, Geheimnisse), nicht gelesen werden kann, ist die Stufe `unknown` statt `ok`, und der Sicherheitsanteil der Bewertung entfällt, statt als 100 zu zählen; der Zustand zeigt `sources_readable` und `sources_total`. Hört eine Quelle auf zu antworten, solange eine Warnung offen ist, bleibt die Warnung eine Woche lang bestehen (mit `unread_since` markiert) und wird nie als behoben gemeldet. Ein Repository, dessen Lesevorgänge weiter scheitern, wartet 5 Minuten, 30 Minuten und dann 6 Stunden bis zum nächsten Versuch, sodass wenige defekte Repositories nie die ganze Runde verbrauchen.

Eine Quelle, die der Tarif des Kontos nicht hat (Branch-Schutz oder Code-Scanning eines privaten Repositorys im kostenlosen Tarif: GitHub antwortet, dass die Funktion einen anderen Tarif braucht), wird von einer Verweigerung und von einer ausgeschalteten Funktion unterschieden: Die Seite und `unavailable_why` im Status zeigen `N/A (Tarif)`, `N/A (kein Zugriff)` oder `N/A (aus)`. Ist `sentinels.security.plan_na` an (Standard), bleiben Quellen der ersten Art aus der Zahl der lesbaren Quellen und aus der Abdeckung der Note heraus und werden getrennt als `sources_na_plan` gezählt; keine der drei Arten ist ein Befund oder ein Persilschein. Hat der Tarif nichts von dem, was zählt, ist der Wächter `unknown` und die Note erhält keinen Sicherheitsteil. Ist es aus, zählen sie als nicht lesbare Quellen.

Jeder Wächter nennt jetzt seinen **Lebenszyklus**: `healthy` (gesund), `degraded` (eingeschränkt: manche Lesevorgänge schlagen fehl, eine Quelle ist nicht lesbar oder der erste Durchgang ist nicht beendet), `paused` (pausiert, wartet auf das GitHub-Kontingent), `error` (schlägt fehl und hat noch nichts gelesen) oder `off` (aus). „Keine Warnungen“ bedeutet nur etwas, wenn der Lebenszyklus `healthy` ist.

## Kosten

Ein Durchlauf liest höchstens `sentinels.security.max_repos_per_tick` Repositories (standardmäßig 5), zuerst die am längsten nicht angesehenen und etwas früher die mit einer offenen Warnung, mit einem Zyklus alle `sentinels.security.refresh_seconds` (standardmäßig 30 Minuten). Jedes Repository kostet höchstens sieben Lesevorgänge, fast alle bedingt: Ein unverändertes Repository verbraucht kein Kontingent; die CODEOWNERS-Datei wird, wenn verlangt, höchstens einmal am Tag gesucht. Der Wächter pausiert, solange das verbleibende Kontingent unter `sentinels.security.min_rate_remaining` liegt. Sein Zustand (`security_state.json`) hält die offenen Warnungen fest: Ein Neustart meldet nichts erneut, und der erste Blick auf ein Repository schreibt keine Ereignisse. Eine Runde beginnt außerdem nach `sentinels.security.deadline_s` Sekunden keine neuen Repositorys mehr (Standard 30; 0 = kein Limit): Die nicht erreichten warten auf die nächste Runde, und der Status führt sie namentlich als `unchecked` (mit `round_cut`) auf, statt sie als null Alarme zu zählen.

## Ein Besitzer je Befund

Die Panels des Reiters Wächter, die schon Sicherheitszahlen zeigten (Warnungen je Repository, alte Warnungen, Abdeckung von Dependabot und CodeQL, Dependabot-Pull-Requests), bleiben Panels. Die Warnungen des Reiters Warnungen zu diesen Signalen kommen nur von diesem Wächter, damit nichts doppelt ausgelöst wird. Der Inhalt jeder Workflow-Datei (nicht an einen Commit gebundene Actions, `write-all`, kein Berechtigungsblock, `pull_request_target` mit Checkout) gehört zum [Lieferketten-Wächter](SENTINEL_SUPPLY_deu.md); `security.workflow_write` bleibt hier, weil es eine Einstellung des Repositorys ist.

## Ereignisse und Benachrichtigungen

Ein neuer Befund schreibt das Ereignis `security_new`, ein geschlossener `security_fixed` in den Feed, an dem die Benachrichtigungskanäle hängen; beides sind Arten, die man in den Benachrichtigungseinstellungen wählen kann, und die Einstellungen je Benutzer haben ein Feld Sicherheit. Beim ersten Ansehen eines Repositorys wird nichts gemeldet.

## Die Einstellungen

Auf der Einstellungsseite, Unterreiter Wächter, Block Sicherheit: `sentinels.security.enabled`, `sentinels.security.refresh_seconds`, `sentinels.security.max_repos_per_tick`, `sentinels.security.min_rate_remaining`, `sentinels.security.repos`, `sentinels.security.plan_na`, `sentinels.security.signals.dependabot.enabled`, `sentinels.security.signals.dependabot.min_severity`, `sentinels.security.signals.code_scanning.enabled`, `sentinels.security.signals.code_scanning.min_severity`, `sentinels.security.signals.secret.enabled`, `sentinels.security.signals.branch.enabled`, `sentinels.security.signals.workflow.enabled` und `sentinels.security.signals.codeowners.enabled`, `sentinels.security.signals.runs_deleted.enabled`, `sentinels.security.signals.runs_deleted.check_window_days`, `sentinels.security.signals.runs_deleted.max_checks`. Die Punkte, die jeder Befund vom Sicherheitsteil der Punktzahl abzieht (`sentinels.security.penalty`), werden aus der Datei gelesen; siehe die Beispieldatei.

## Branch-Schutz per Ruleset

Ein Standardbranch gilt als geschützt, wenn er den klassischen Branch-Schutz **oder** ein aktives Ruleset hat (GitHub antwortet auf den klassischen Endpunkt mit 404, wenn ein Repository nur per Ruleset geschützt ist; deshalb liest der Wächter auch das Flag `protected` des Branches und die aktiven Regeln des Branches). `signals.branch.require` kann Regeltypen auflisten (z. B. `pull_request`, `required_status_checks`), die die Regeln haben müssen; fehlt einem geschützten Branch eine, wird er mit den fehlenden gemeldet. Standard ist eine leere Liste: jeder Schutz genügt. Ein Repository, das wegen einer Zeitüberschreitung des Aufrufs nicht gelesen werden konnte, steht mit seiner Ursache (`timeout`, `rate`, `network`, `error`) unter `errors` und `error_kinds` des Status; es ist nie ein Befund.
