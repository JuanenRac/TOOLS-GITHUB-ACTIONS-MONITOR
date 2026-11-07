<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CI_RED_BRIDGE.md) | [🇪🇸 Español](CI_RED_BRIDGE_spa.md) | [🇫🇷 Français](CI_RED_BRIDGE_fra.md) | [🇮🇹 Italiano](CI_RED_BRIDGE_ita.md) | **🇩🇪 Deutsch** | [🇨🇳 简体中文](CI_RED_BRIDGE_zho.md) | [🇯🇵 日本語](CI_RED_BRIDGE_jpn.md) | [🇵🇹 Português](CI_RED_BRIDGE_por.md)

# Vom Monitor zum Dashboard: `ci_red.json`

Was der Monitor schreibt, wie man es exportiert und was ein Leser der Datei braucht. Der Monitor liest nur GitHub und schreibt lokale Dateien: Er führt nie einen Push oder Commit aus und schließt von sich aus nie etwas.

## Was der Monitor schreibt

`ci_red.json` neben `actions_monitor.py`, nach jedem Durchlauf des Wächters aktualisiert (Schema 2):

| Feld | Bedeutung |
|---|---|
| `schema` | `2`. Felder werden nur hinzugefügt, nie umbenannt. |
| `generated` | UTC-Zeit des Durchlaufs. |
| `tool_version` | Version des Werkzeugs, das die Datei geschrieben hat. |
| `complete` | `true`, wenn in diesem Durchlauf jedes überwachte Repository gelesen wurde. `false` während des Ladens, wenn das API-Kontingent knapp wurde oder wenn Klone fehlen: Handeln Sie nicht anhand der Liste der roten Repositories oder der Signaturwarteschlange, bevor es `true` ist. |
| `red_repos` / `pending_sign_repos` | Anzahlen. |
| `repos.<NAME>.ecosystem` | `armor`, `urtc`, `hydra`, `eh3d` oder `other`. |
| `repos.<NAME>.red[]` | Ein Eintrag je Workflow, dessen letzter abgeschlossener Lauf auf dem Standard-Branch fehlgeschlagen ist: `workflow`, `conclusion`, `since`, `streak`, `url`. |
| `repos.<NAME>.pending_sign[]` und `pending_sign_hours` | Gebaute, aber noch nicht signierte Releases und das Alter des ältesten. |

## So exportieren Sie es

```
py -3 read_report.py --export-status DIR          # ci_status_public.json + .md, nur was veröffentlicht werden darf
py -3 read_report.py --export-sign-queue FILE     # die Signaturwarteschlange
```

Beide lesen den laufenden Monitor auf `127.0.0.1` (ohne GitHub-Kontingent). Sie weigern sich zu schreiben, solange der Snapshot lädt, und nennen den Grund; der Exitcode ist in diesem Fall nicht null.

## Was ein Leser (der Dashboard-Generator) braucht

1. `schema` lesen; jeden Wert `>= 2` akzeptieren und unbekannte Felder ignorieren.
2. `complete` lesen; ist es `false`, den letzten vollständigen Export behalten, statt ihn zu ersetzen.
3. `generated` neben den Zahlen anzeigen, damit eine veraltete Datei auffällt.
4. `repos.<NAME>.red[].url` als Link verwenden; ihn nie neu zusammensetzen.

## Was der Monitor nicht tut

Er veröffentlicht die Datei nicht, pusht nicht in das Profil-Repository und berührt keinen Workflow. Den Export zum Dashboard zu bringen, ist ein Schritt des Eigentümers (oder eines Workflows des Profil-Repositorys, der die exportierte Datei liest).
