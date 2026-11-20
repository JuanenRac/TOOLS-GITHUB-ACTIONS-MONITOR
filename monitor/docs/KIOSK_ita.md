<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](KIOSK.md) | [🇪🇸 Español](KIOSK_spa.md) | [🇫🇷 Français](KIOSK_fra.md) | **🇮🇹 Italiano** | [🇩🇪 Deutsch](KIOSK_deu.md) | [🇨🇳 简体中文](KIOSK_zho.md) | [🇯🇵 日本語](KIOSK_jpn.md) | [🇵🇹 Português](KIOSK_por.md)

# Chiosco: il monitor su una TV o una parete

Il profilo chiosco è la pagina del monitor per uno schermo che nessuno tocca: senza intestazione, senza schede, con testo più grande e, se vuoi, un alto contrasto e una rotazione tra poche schede. Riusa ciò che la pagina già conosce (`?screen=`, `?tabs=`, `?rotate=`, `?chrome=0`; vedi [SCREENS_ita.md](SCREENS_ita.md)) e aggiunge due parametri. Non legge nulla da GitHub e non scrive nulla: decide solo come appare la pagina.

È **disattivato per impostazione predefinita**. Con `kiosk.enabled` disattivato la pagina ignora `kiosk=1` nell'indirizzo, quindi un link copiato da altrove non cambia nulla.

## L'indirizzo

`python bin/monitor_cli.py kiosk [PRESET] [--account ID]` lo stampa; non ha bisogno di un monitor in funzione. Per esempio, `kiosk ops` stampa:

```
http://127.0.0.1:8765/?screen=1&tabs=now,al,charts&chrome=0&kiosk=1&scale=150
```

| Parametro | Significato |
|---|---|
| `kiosk=1` | attiva il profilo (solo quando `kiosk.enabled` è attivo) |
| `scale=%` | la dimensione del testo, da 100 a 400 (un valore fuori intervallo viene riportato nell'intervallo) |
| `contrast=1` / `contrast=0` | alto contrasto attivo o disattivo per questa finestra (l'impostazione `kiosk.high_contrast` è il valore predefinito) |
| `rotate=SECONDS` | scorrere le schede di `tabs=` (il parametro già esistente; il comando lo aggiunge solo quando la rotazione è attiva) |
| `chrome=0`, `screen=`, `tabs=`, `account=` | quelli già esistenti |

## Preset

| Preset | Schede |
|---|---|
| `ops` | Adesso, Avvisi, Grafici |
| `team` | Avvisi, Salute del team |
| `release` | Adesso, Repository, Report |
| `quiet` | solo Avvisi |

## Impostazioni (Impostazioni, Riga di comando e Chiosco)

| Impostazione | Predefinito | Significato |
|---|---|---|
| `kiosk.enabled` | disattivato | attiva il profilo |
| `kiosk.font_scale_percent` | 150 | la dimensione del testo, da 100 a 400 |
| `kiosk.high_contrast` | disattivato | sfondo nero e linee bianche |
| `kiosk.rotate_views` | disattivato | un preset con più schede cambia scheda da solo; disattivato, lo schermo mostra la prima scheda del preset |
| `kiosk.rotate_seconds` | 30 | quanto resta ogni scheda (da 5 a 600) |

La dimensione si applica con lo zoom della pagina, quindi ogni cifra e ogni tabella crescono insieme. Un valore fuori intervallo non è un errore: viene sostituito dal predefinito.
