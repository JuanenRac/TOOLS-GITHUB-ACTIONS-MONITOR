<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](MODES.md) | [🇪🇸 Español](MODES_spa.md) | [🇫🇷 Français](MODES_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](MODES_deu.md) | [🇨🇳 简体中文](MODES_zho.md) | [🇯🇵 日本語](MODES_jpn.md) | [🇵🇹 Português](MODES_por.md)

# Modalità di lavoro: normale, veloce e turbo

Quando vuoi osservare qualcosa più da vicino per un po' (un'ora, per esempio) puoi portare il monitor in una modalità più veloce anche se consuma prima la quota dell'API. Il selettore con l'icona del misuratore è nell'intestazione; da console usa `--mode fast` o `--mode turbo` con `--mode-minutes 60`.

| Modalità | Cosa cambia | Valori predefiniti |
|---|---|---|
| **normal** | niente: la tua configurazione | i tuoi |
| **fast** (veloce) | aggiornamento, aggiornamento a freddo, run per repository, finestra calda | 30 s, 300 s, 30 run, 6 h |
| **turbo** | lo stesso, di più | 15 s, 90 s, 50 run, 12 h |

I preset sono il blocco `modes` di `actions_monitor.json` (`modes.fast`, `modes.turbo`, `modes.default_minutes`, `modes.start`); modificali a piacere. Un preset non rende mai un valore più lento o più piccolo del tuo, e nulla scende sotto i 10 secondi, per stare lontano dai limiti secondari di GitHub (dopo uno, il monitor attende almeno un minuto e poi di più).

**Prima di partire**, la pagina mostra le chiamate all'ora della modalità nel caso peggiore, ciò che di solito risparmia la cache (una lettura condizionale che risponde `304` non consuma quota primaria) e quanto durerebbe la quota rimasta. **Torna da solo a normale** quando il tempo finisce (l'intestazione fa il conto alla rovescia) e quando la quota rimasta scende sotto `min_rate_remaining`; un avviso dice perché e la console lo stampa. **Senza accesso GitHub dà solo 60 chiamate all'ora**, quindi veloce e turbo sono disattivati con il motivo (esegui `gh auth login`).

Cambiare modalità è un'impostazione locale: richiede il token monouso della pagina come ogni altra modifica, vive solo in memoria (un riavvio torna a normale, a meno che tu scriva `modes.start`) e non invia nulla da nessuna parte. Funziona in entrambe le edizioni; la sentinella dell'edizione completa mantiene i propri intervalli e il proprio budget di chiamate (`sentinel.budget_per_hour`), descritti in [La sentinella](SENTINEL_ita.md). Il banner della console e le righe di stato indicano la modalità attiva.
