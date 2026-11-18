<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SOUNDS.md) | [🇪🇸 Español](SOUNDS_spa.md) | [🇫🇷 Français](SOUNDS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](SOUNDS_deu.md) | [🇨🇳 简体中文](SOUNDS_zho.md) | [🇯🇵 日本語](SOUNDS_jpn.md) | [🇵🇹 Português](SOUNDS_por.md)

# Suoni

La pagina produce i propri suoni con l'API Web Audio, uno per ogni tipo di evento, così si capisce a orecchio cosa è successo senza guardare. Non ci sono file audio: i toni nascono nel browser, senza connessione, e non viene inviato nulla da nessuna parte. Ogni suono ha anche il suo avviso visivo (le tessere, le schede, le etichette); il suono non lo sostituisce mai.

| Tipo | Quando suona | Il suono |
|---|---|---|
| Rosso | Un workflow che non era rosso diventa rosso (un nuovo fallimento). | Due toni ascendenti, il classico "bing bing". |
| Sicurezza o grave | Un nuovo avviso della sentinella di sicurezza, un avviso grave (errore o critico) della sentinella di collaborazione o un account diventato cieco. | Tre impulsi gravi. |
| Bloccato | Una build bloccata, una coda fantasma o un problema con i runner. | Uno scivolamento lungo discendente. |
| Punteggio | Il punteggio della flotta scende (`score.dropped`). | Tre note discendenti. |
| Connessione | Si perde la connessione con GitHub o quella di questa pagina con il monitor. | Due note gravi e lunghe. |
| Avviso | Un nuovo avviso di livello warning (una firma in attesa, un ticket vecchio, una pull request in attesa). | Due toni medi uguali. |
| Risolto | Un workflow rosso torna verde o sparisce un avviso grave. | Tre note ascendenti. |
| Rapporto | Uno dei rapporti facoltativi mostra un rilievo che prima non c'era. | Due rintocchi dolci, acuto poi più grave. |
| Lezione | Le lezioni dei fallimenti mostrano una categoria nuova, o una che inizia a ripetersi o ad applicarsi. | Tre note acute veloci. |
| Notizia | Un nuovo avviso di livello info (la release dell'originale di un fork, per esempio). | Un segnale dolce. |
| Di nuovo online | Torna la connessione a GitHub, o di questa pagina con il monitor, dopo un’interruzione. | Quattro note ascendenti. |

## Perché un browser può restare muto e cosa fa la pagina

- Un browser lascia suonare una pagina solo dopo che hai fatto clic, toccato o premuto un tasto su di essa. Fino ad allora la barra mostra l'avviso "Suono bloccato dal browser: fai clic qui per attivarlo". Il primo clic ovunque lo sblocca.
- Ciò che è successo mentre il suono era bloccato viene conservato (al massimo dieci minuti) e suona alla prima occasione: il clic, la pagina che torna in primo piano o il controllo successivo, ogni due secondi. Non si perde nulla tra due letture; ciò che ha più di dieci minuti è una notizia vecchia e non viene annunciata.
- La prima lettura della pagina ricorda solo ciò che c'è già; anche un ricaricamento entro poche ore lo ricorda, quindi un fallimento arrivato a pagina chiusa è nuovo.
- Una scheda in secondo piano mantiene il suono finché il browser tiene sveglia la pagina; alcuni browser mettono in pausa le schede nascoste dopo un po'. Meglio lasciare gli schermi a parete e la pagina in una finestra visibile.

## Niente spam

- Un tipo che ha appena suonato aspetta `sound.cooldown_seconds` (30 s per impostazione predefinita) prima di suonare di nuovo.
- Più tipi nella stessa lettura fanno una sola raffica: al massimo tre schemi, il più grave per primo; il resto aspetta la raffica successiva. Due raffiche non si sovrappongono mai.
- Un avviso silenziato (scheda Avvisi) non suona mai.

## Impostazioni (Impostazioni, Suono)

Sono tutte nel file di configurazione e nella scheda Impostazioni; volume, tema e interruttori hanno effetto subito.

| Impostazione | Cosa fa |
|---|---|
| `sound.enabled` | Interruttore generale di tutti i suoni della pagina. |
| `sound.on_new_red`, `sound.on_connection_lost`, `sound.on_warning`, `sound.on_resolved`, `sound.on_report`, `sound.on_lesson`, `sound.on_sentinel`, `sound.on_stuck`, `sound.on_score_drop`, `sound.on_info`, `sound.on_live_recovered` | Un interruttore per tipo (tutti attivi per impostazione predefinita). |
| `sound.theme` | `classic` (toni chiari) o `soft` (toni più gravi, rotondi e lenti). Ogni tipo mantiene il suo ritmo in entrambi. |
| `sound.volume` | Da 1 a 100, moderato per impostazione predefinita. |
| `sound.cooldown_seconds` | Pausa tra due suoni dello stesso tipo. |
| `sound.quiet_enabled`, `sound.quiet_from_hour`, `sound.quiet_to_hour` | Ore di silenzio (disattivate per impostazione predefinita): tra le due ore di questo computer non suona nulla; possono attraversare la mezzanotte. |
| `sound.server_beep` | Disattivato per impostazione predefinita. Il monitor stesso suona su questo computer quando nessuna pagina è aperta o il browser blocca l’audio: un motivo per ogni tipo di evento della tabella qui sopra (toni di Windows, suoni di sistema di macOS, eventi canberra su Linux), con gli stessi interruttori e le stesse ore di silenzio della pagina, in una raffica di al massimo tre tipi alla volta; solo locale. |

## Prova ogni suono

In Impostazioni, Interfaccia, il pulsante "Prova suono" riproduce il bing bing classico e un pulsante per tipo riproduce quel tipo con il volume e il tema delle impostazioni. L'etichetta "Suono" della barra in basso silenzia tutto in questo browser.

## Schermi a parete

Gli schermi a parete (`/screen/...`) usano gli stessi suoni, con lo stesso tema, volume, interruttori e ore di silenzio. Sono disattivati per impostazione predefinita: `screens.sound` deve essere attivo e la finestra richiede `?sound=on`. Uno schermo che nessuno tocca non può ricevere il clic che chiede il browser: avvia il browser dello schermo con la sua opzione "consenti audio senza gesto" (in Chromium, `--autoplay-policy=no-user-gesture-required`) oppure fai clic una volta nella finestra.

## Dove viene conservato

L'etichetta di silenzio la ricorda ogni browser; ciò che la pagina sa della sua ultima lettura resta anch'esso nel browser. Dei suoni non viene inviato nulla a un server.
