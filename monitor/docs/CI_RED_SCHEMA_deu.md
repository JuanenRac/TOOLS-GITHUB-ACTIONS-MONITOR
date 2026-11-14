<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CI_RED_SCHEMA.md) | [🇪🇸 Español](CI_RED_SCHEMA_spa.md) | [🇫🇷 Français](CI_RED_SCHEMA_fra.md) | [🇮🇹 Italiano](CI_RED_SCHEMA_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](CI_RED_SCHEMA_zho.md) | [🇯🇵 日本語](CI_RED_SCHEMA_jpn.md) | [🇵🇹 Português](CI_RED_SCHEMA_por.md)

# ci_red.json - Schema 2 (stabiler Vertrag)

`ci_red.json` ist der Snapshot, den der Monitor schreibt (atomar, standardmäßig neben sich selbst), damit jeder Konsument den CI-Zustand lesen kann, ohne den Monitor
oder GitHub zu fragen: ein Dashboard, ein Skript, ein Benachrichtigungs-Hook. Das Format ist **stabil: Felder werden nur hinzugefügt, nie umbenannt oder entfernt**.
Lesen Sie es mit `.get()`; ignorieren Sie Felder, die Sie nicht kennen.

Wohin es geschrieben wird, legt `actions_monitor.json` fest:

| Schlüssel (`sentinel.`) | Bedeutung |
|---|---|
| `ci_red_file` | `""` = `ai/ci_red.json` des Monitors (Standard); `"off"` = wird nicht geschrieben; ein Pfad = dorthin (relative Pfade beziehen sich auf den Monitor-Ordner; ein Laufwerk D:, ein UNC-Pfad oder ein Laufwerk, das das laufende System nicht nutzen kann, wird abgelehnt) |
| `ci_red_audit_copy` | `true` kopiert es zusätzlich in den Audit-Ordner, sofern dieser existiert |

## Aufbau

```json
{
  "schema": 2,
  "generated": "2026-01-01T12:00:00Z",
  "generated_local": "2026-01-01 13:00:00 CET (12:00:00 UTC)",
  "tool_version": "1.2.0",
  "complete": true,
  "red_repos": 1,
  "pending_sign_repos": 1,
  "pending_sign_hours_threshold": 24,
  "repos": {
    "REPO": {
      "ecosystem": "armor | urtc | hydra | eh3d | other",
      "red": [{"workflow": "CI", "conclusion": "failure", "since": "2026-01-01T10:00:00Z", "streak": 2, "url": "https://github.com/OWNER/REPO/actions/runs/1"}],
      "pending_sign_hours": 31.5,
      "pending_sign": [{"workflow": "firmware-build.yml", "hours": 31.5, "state": "built_on_gha | signed_local",
                         "signature_kind": "none | dev | release", "signature_verified": true,
                         "last_build_at": "2026-01-01T08:00:00Z", "url": "https://github.com/OWNER/REPO/actions/runs/2"}]
    }
  }
}
```

* `complete` ist `false`, solange der Wächter noch lädt: Werten Sie in diesem Fall ein fehlendes Repository nicht als grün.
* `signature_verified` ist `true`, `false` oder die Zeichenkette `"unknown"` (nie eine Vermutung: Formate, die dieses Werkzeug nicht prüfen kann, sind `"unknown"`).
* Die Felder `pending_sign*` beschreiben die **lokale Signaturseite** und sind für Ihre eigenen lokalen Werkzeuge gedacht. Ein öffentlicher Konsument sollte sie ignorieren.
* Die Zeit steht auch für Menschen da: `generated_local` enthält denselben Zeitpunkt als lokales Datum, Uhrzeit, Zone und UTC (zum Beispiel `2026-01-01 13:00:00 CET (12:00:00 UTC)`), in der Zone von `display.timezone` (standardmäßig `local`). `generated` ist immer UTC und das Feld für Programme.

## Die Regel für „rot“ (eine Definition, überall)

Betrachtet wird der **letzte abgeschlossene Lauf jedes Workflows auf dem Standard-Branch**. Er ist rot, wenn sein Ergebnis `failure`, `timed_out`,
`startup_failure` oder `action_required` lautet (er wartet auf eine Freigabe). `cancelled`, `skipped`, `neutral` und `stale` sagen nichts aus und werden ignoriert.
„Grün“ für den Signaturzustand verwendet dieselbe Liste von Läufen. Ein Konsument, der die Regel aus den Workflow-Läufen neu berechnet, muss genau diese
Definition verwenden, um mit dem Monitor übereinzustimmen.

## Das Veröffentlichen ist ein eigener, ausdrücklicher Schritt

**Entscheidung: Dieser PC veröffentlicht `ci_red.json` nicht und veröffentlicht weder `pending_sign` noch irgendeinen anderen Teil der Signaturseite in einem Repository, einem Dashboard oder einem
Dienst.** Die Datei bleibt auf dem Rechner (und, wenn `ci_red_audit_copy` aktiv ist, im lokalen Audit-Ordner). Ein öffentliches Dashboard muss die Liste der roten Workflows aus den
öffentlichen Workflow-Läufen mit der obigen Regel neu berechnen oder den im Folgenden beschriebenen Export verwenden, der den Signaturzustand nie enthält.

Nichts im Monitor veröffentlicht diese Datei in einem Repository. Braucht ein öffentliches Dashboard die Liste der roten Workflows, lassen Sie es entweder die Regel aus den
öffentlichen Laufdaten neu berechnen oder exportieren Sie den unkritischen Teil selbst:

```
python3 bin/read_report.py --export-status DIR
```

Das schreibt `ci_status_public.json` und `ci_status_public.md` in den von Ihnen genannten Ordner und **nur** die Liste der roten Workflows (Repository,
Ökosystem, Workflow, Ergebnis, seit wann, Serie, Link zum Lauf). Kein Signaturzustand, keine Schlüsselnamen, keine lokalen Pfade, keine Befehle. Das Werkzeug führt nie einen Commit oder
Push aus; was danach mit dem Ordner geschieht, liegt bei Ihnen.

`python3 bin/read_report.py --export-sign-queue FILE` (`.json` oder `.csv`) schreibt die globale Signaturwarteschlange mit den exakten lokalen Befehlen. Diese Datei ist
für den PC bestimmt, auf dem der Monitor läuft, und sagt das auch in ihrem Inneren.

Optionales Feld `ai_hint` (neu in 1.6.4) in jedem roten Workflow: `{"class": "real|transient", "cause", "action"}` für eine KI oder ein Skript. Verbraucher, die mit `.get()` lesen, können es ignorieren.
