<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CI_RED_SCHEMA.md) | [🇪🇸 Español](CI_RED_SCHEMA_spa.md) | [🇫🇷 Français](CI_RED_SCHEMA_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](CI_RED_SCHEMA_deu.md) | [🇨🇳 简体中文](CI_RED_SCHEMA_zho.md) | [🇯🇵 日本語](CI_RED_SCHEMA_jpn.md) | [🇵🇹 Português](CI_RED_SCHEMA_por.md)

# ci_red.json - schema 2 (contratto stabile)

`ci_red.json` è lo snapshot che il monitor scrive (in modo atomico, per impostazione predefinita accanto a sé) in modo che qualsiasi consumatore possa leggere lo stato della CI senza interrogare
il monitor né GitHub: una dashboard, uno script, un hook di notifica. Il formato è **stabile: i campi vengono solo aggiunti, mai rinominati né rimossi**.
Leggilo con `.get()`; ignora i campi che non conosci.

Dove viene scritto si imposta in `actions_monitor.json`:

| chiave (`sentinel.`) | significato |
|---|---|
| `ci_red_file` | `""` = `ci_red.json` accanto al monitor (predefinito); `"off"` = non viene scritto; un percorso = lì (i percorsi relativi sono relativi alla cartella del monitor; un'unità D:, un percorso UNC o un'unità che il sistema in esecuzione non può usare viene rifiutata) |
| `ci_red_audit_copy` | `true` lo copia anche nella cartella di audit quando questa esiste |

## Struttura

```json
{
  "schema": 2,
  "generated": "2026-01-01T12:00:00Z",
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

* `complete` è `false` finché la sentinella sta ancora caricando: in tal caso non considerare verde un repository mancante.
* `signature_verified` è `true`, `false` o la stringa `"unknown"` (mai una supposizione: i formati che questo strumento non può verificare sono `"unknown"`).
* I campi `pending_sign*` descrivono il **lato della firma locale** e sono per i tuoi strumenti locali. Un consumatore pubblico deve ignorarli.

## La regola del «rosso» (una sola definizione, ovunque)

Si guarda l'**ultima esecuzione completata di ciascun workflow sul ramo predefinito**. È rossa quando la sua conclusione è `failure`, `timed_out`,
`startup_failure` oppure `action_required` (attende un'approvazione). `cancelled`, `skipped`, `neutral` e `stale` non dicono nulla e vengono ignorate.
Il «verde» per lo stato della firma usa lo stesso elenco di esecuzioni. Un consumatore che ricalcola la regola a partire dalle esecuzioni dei workflow deve usare esattamente questa
definizione per concordare con il monitor.

## La pubblicazione è un passaggio separato ed esplicito

**Decisione: questo PC non pubblica `ci_red.json` e non pubblica `pending_sign` né alcun'altra parte del lato della firma in un repository, in una dashboard o in alcun
servizio.** Il file resta sulla macchina (e, quando `ci_red_audit_copy` è attivo, nella cartella di audit locale). Una dashboard pubblica deve ricalcolare l'elenco dei rossi dalle
esecuzioni pubbliche dei workflow con la regola sopra, oppure usare l'esportazione descritta di seguito, che non contiene mai lo stato della firma.

Nulla nel monitor pubblica questo file in un repository. Se una dashboard pubblica ha bisogno dell'elenco dei rossi, lasciale ricalcolare la regola dai
dati pubblici delle esecuzioni, oppure esporta tu stesso la parte non sensibile:

```
python3 read_report.py --export-status DIR
```

Questo scrive `ci_status_public.json` e `ci_status_public.md` nella cartella indicata e **solo** l'elenco dei workflow rossi (repository,
ecosistema, workflow, conclusione, da quando, serie, link all'esecuzione). Nessuno stato di firma, nessun nome di chiave, nessun percorso locale, nessun comando. Lo strumento non esegue mai commit né
push; che cosa accada alla cartella dopo dipende da te.

`python3 read_report.py --export-sign-queue FILE` (`.json` o `.csv`) scrive la coda di firma globale con i comandi locali esatti. Quel file è
per il PC che esegue il monitor e lo dichiara al proprio interno.
