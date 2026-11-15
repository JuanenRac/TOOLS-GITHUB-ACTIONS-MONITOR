<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](SCREENS.md) | [🇪🇸 Español](SCREENS_spa.md) | [🇫🇷 Français](SCREENS_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](SCREENS_deu.md) | [🇨🇳 简体中文](SCREENS_zho.md) | [🇯🇵 日本語](SCREENS_jpn.md) | [🇵🇹 Português](SCREENS_por.md)

# Schermi, dimensioni e orientamento

La pagina si adatta alla dimensione della finestra, dal telefono al 4K, in verticale o in orizzontale, e un solo monitor può servire più schermi, ciascuno con le schede che scegli. Niente viene interrogato due volte: tutti gli schermi leggono lo stesso stato.

## Indirizzi

- `/` - l'intera pagina.
- `/screen/1`, `/screen/2`, `/screen/3` - le schede impostate per quello schermo (`ui.screen1_tabs` ...). Apri ciascuna in una finestra del proprio monitor o TV.
- `?orient=portrait` o `?orient=landscape` forza la disposizione di una finestra; `?tabs=now,charts` e `?rotate=30` impostano le schede e i secondi tra loro per una finestra.

## Impostazioni

| Impostazione | Cosa fa |
|---|---|
| `ui.orientation` | auto segue la finestra; portrait impila i pannelli in una colonna; landscape mantiene l'affiancamento. |
| `ui.rotate_seconds` | 0 = spento. Secondi tra le schede di uno schermo che ne ha più di una. |
| `ui.screen1_tabs` | Schede di /screen/1, separate da virgole: now, al, sent, charts, repos, hist, cfg. Vuoto = tutte. |
| `ui.screen1_orientation` | auto, portrait o landscape solo per /screen/1. |
| `ui.screen2_tabs` | Schede di /screen/2. |
| `ui.screen2_orientation` | Orientamento di /screen/2. |
| `ui.screen3_tabs` | Schede di /screen/3. |
| `ui.screen3_orientation` | Orientamento di /screen/3. |
| `ui.now_sort` | Ordine di In corso adesso per chi non ha scelto: ecosystem, severity, age, newest, repo, event o state. |
| `ui.alerts_sort` | Ordine della scheda Avvisi per chi non ha scelto: server, severity, streak, class, age, newest, repo, origin o state. |

## Ordine degli elenchi

La sezione **In corso adesso** della prima scheda è ordinata per ecosistema, con un titolo per ciascuno. L'elenco sopra la sezione lo cambia: ecosistema, gravità (prima le esecuzioni bloccate, poi quelle con un job fallito, poi in corso, poi in coda), anzianità (la più lunga per prima), più recente per prima, repository, innesco (push, pull_request, schedule...) e stato (in corso prima di in coda). La scelta viene ricordata per ogni persona: in modalità team la conserva il server con l'utente (`GET` e `POST /api/auth/me/view`, quindi lo segue in un altro browser), altrimenti questo browser. Finché nessuno sceglie, l'ordine è `ui.now_sort` del file di configurazione (ecosistema se manca o è errato). I pulsanti **Espandi tutto** e **Comprimi tutto** accanto all'elenco espandono o comprimono in un colpo tutti i repository della sezione, con qualsiasi ordine; la scelta viene ricordata per ogni persona nello stesso posto e sopravvive a un aggiornamento (un repository aperto o chiuso a mano dopo conserva la tua scelta).

L'elenco della scheda **Avvisi** mantiene l'ordine inviato dal monitor finché qualcuno non ne sceglie un altro con l'elenco sopra: gravità (critico, errore, avviso, info), prima la serie di errori consecutivi più lunga, classe (un avviso di errore o critico è reale e va prima di quelli da tenere d'occhio), prima i più vecchi, prima i più recenti, repository, origine (la sentinella che lo ha sollevato) e stato (aperti prima di silenziati). Viene ricordato allo stesso modo; finché nessuno sceglie, vale `ui.alerts_sort` del file di configurazione (`server` se manca o è errato).

## Dimensioni provate

Un test del browser apre la pagina in ciascuna di queste dimensioni, percorre tutte le schede e fallisce se c'è uno scorrimento laterale o un testo che esce dal suo riquadro. Le finestre da 2400 px in su ricevono un carattere più grande (da 3200 px, ancora più grande) invece di una disposizione allungata; una finestra più alta che larga impila i pannelli.

| Dimensione | Tipo |
|---|---|
| 1920x1080 | Full HD |
| 2560x1080 | 21:9 |
| 3440x1440 | 21:9 |
| 5120x1440 | 32:9 |
| 3840x2160 | 4K |
| 1080x1920 | Full HD |
| 2160x3840 | 4K |
| 768x1024 | tablet |
| 390x844 | phone |

## Ricetta per una postazione con due o tre schermi

1. Sul computer che esegue il monitor, imposta `ui.screen1_tabs` su `now,al`, `ui.screen2_tabs` su `charts,repos` e, per un monitor ruotato, `ui.screen2_orientation` su `portrait`.
2. Apri `http://questo-computer:8765/screen/1` in una finestra del primo monitor e `/screen/2` sul secondo; F11 per lo schermo intero. Da un altro computer usa la modalità rete con il suo token di accesso.
3. Per uno schermo a parete che nessuno tocca, dagli più schede e imposta `ui.rotate_seconds` su 20-30.

## Immagini

La scheda Adesso in quattro dimensioni, con dati inventati (4K, un monitor 21:9, un monitor ruotato, un telefono):

![4K 3840x2160](../../docs/screenshots/web_size_4k_light.png)

![ultrawide 3440x1440](../../docs/screenshots/web_size_ultrawide_light.png)

![ruotato 1080x1920](../../docs/screenshots/web_size_portrait_light.png)

![telefono 390x844](../../docs/screenshots/web_size_phone_light.png)
