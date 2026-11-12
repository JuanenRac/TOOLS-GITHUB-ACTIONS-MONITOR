<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](COLLAB.md) | [🇪🇸 Español](COLLAB_spa.md) | [🇫🇷 Français](COLLAB_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](COLLAB_deu.md) | [🇨🇳 简体中文](COLLAB_zho.md) | [🇯🇵 日本語](COLLAB_jpn.md) | [🇵🇹 Português](COLLAB_por.md)

# La sentinella Collab: issue e pull request

Una seconda sentinella accanto a quella della CI. Guarda le **issue e le pull request aperte** dei tuoi repository e ti dice cosa richiede una persona: issue dimenticate, etichette critiche, revisioni che nessuno fa, bozze senza fine, conflitti che restano. Ha un orologio proprio, non cambia mai ciò che decide la sentinella CI e **non scrive mai su GitHub**. Fa parte dell'edizione completa; l'edizione lite non la carica.

## Attivarla

È disattivata di default. Impostazioni > Sentinella > Issue e pull request, oppure in `actions_monitor.json`:

```
"sentinels": {"collab": {"enabled": true, "refresh_seconds": 600, "max_repos_per_tick": 10, "repos": "all",
  "rules": {"issue_stale_days": 14, "issue_critical_labels": ["security", "critical"], "pr_review_pending_days": 3,
            "pr_draft_max_days": 30, "pr_conflict_days": 7, "watch_external_comments": false, "ignore_labels": ["monitor:ignore"]}}}
```

`repos` è `"all"`, un elenco di repository o `{"ecosystems": [...]}`.

## Le regole (codici stabili)

| Codice | Livello | Quando |
|---|---|---|
| `collab.issue.stale` | avviso | un'issue aperta senza attività da `issue_stale_days` |
| `collab.issue.critical` | errore | un'issue aperta con una etichetta di `issue_critical_labels`, qualunque sia la sua età |
| `collab.issue.external` | avviso | (solo con `watch_external_comments`) un'issue di qualcuno esterno al team a cui nessuno ha risposto dopo un giorno |
| `collab.pr.review_pending` | avviso | una pull request con una revisione richiesta in attesa da `pr_review_pending_days` |
| `collab.pr.draft_old` | info | una pull request in bozza aperta da `pr_draft_max_days` |
| `collab.pr.conflict` | avviso | una pull request con conflitti da `pr_conflict_days` |

I bot sono esclusi. I valori predefiniti sono lenti di proposito: una bozza che aspetta mesi è normale in molti team.

## Quanto costa

Un giro legge al massimo `max_repos_per_tick` repository, con due richieste condizionali ciascuno (un repository invariato non consuma quota) e fino a sei dettagli di pull request per giro. Si ferma finché la quota è sotto `min_rate_remaining`. Lo stato è in `collab_state.json` (nella cartella dell'account se ce ne sono più d'uno): un riavvio non annuncia nulla due volte.

## Meno rumore: ignorare e silenziare

- **Etichetta di esclusione**: metti su GitHub un'etichetta di `ignore_labels` (`monitor:ignore` di default) sull'issue o sulla pull request e Collab non genera avvisi per essa. Il monitor non scrive mai etichette.
- **Silenziamento nel monitor**: nella scheda Avvisi ogni avviso ha pulsanti per silenziare quell'avviso, la sua regola o l'intera sentinella per `alerts.mute_hours` ore (24 di default, da 1 a 720). Scade da solo, si può ripristinare in qualsiasi momento e la scheda conserva un breve storico di cosa è stato silenziato e fino a quando. È una nota di questo monitor; su GitHub non cambia nulla. In modalità di rete un silenziamento si può fare (e togliere) solo dal computer su cui gira il monitor (`this_computer`); un client della rete vede i silenziamenti e non può cambiarli. Resterà così finché una edizione successiva non avrà utenti propri. Il silenziamento di un avviso può anche durare «finché l'elemento non cambia» (`until_change` nella richiesta di `POST /api/alerts/mute`): termina subito quando cambia l'`updated_at` della issue o della pull request, oppure alla fine delle ore, quel che viene prima. Nella scheda Avvisi è il pulsante **Fino al cambiamento**, mostrato sugli avvisi che portano lo `updated_at` del loro elemento (quelli della sentinella Collab); l'avviso silenziato indica allora «silenziato fino al cambiamento».

## Dove si vede

- La scheda **Avvisi**: un elenco per tutte le sentinelle, filtro per origine (CI, Collab) e per livello, e i silenziati a richiesta.
- La scheda Sentinella: il livello *Issue e pull request*.
- `GET /api/alerts?sentinel=collab&level=&muted=show|hide|only` e `GET /api/sentinel/collab`; `GET /api/events?sentinel=collab&since=` per gli eventi (`collab_new`, `collab_fixed`, inviati anche dai canali di notifica se li scegli; vedi NOTIFICATIONS).

## Limiti

Di ogni repository si leggono solo le prime 100 issue aperte e le prime 100 pull request aperte, le aggiornate più di recente per prime. Collab non propone né esegue nulla; le azioni su issue e pull request spettano a un'edizione successiva.
