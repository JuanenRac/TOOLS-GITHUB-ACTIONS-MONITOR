<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](KIOSK.md) | **🇪🇸 Español** | [🇫🇷 Français](KIOSK_fra.md) | [🇮🇹 Italiano](KIOSK_ita.md) | [🇩🇪 Deutsch](KIOSK_deu.md) | [🇨🇳 简体中文](KIOSK_zho.md) | [🇯🇵 日本語](KIOSK_jpn.md) | [🇵🇹 Português](KIOSK_por.md)

# Kiosco: el monitor en una TV o una pared

El perfil de kiosco es la página del monitor para una pantalla que nadie toca: sin cabecera, sin pestañas, con letra más grande y, si quieres, un contraste alto y una rotación por unas pocas pestañas. Reutiliza lo que la página ya sabe (`?screen=`, `?tabs=`, `?rotate=`, `?chrome=0`; véase [SCREENS_spa.md](SCREENS_spa.md)) y añade dos parámetros. No lee nada de GitHub y no escribe nada: solo decide cómo se ve la página.

Está **apagado por defecto**. Con `kiosk.enabled` apagado la página ignora `kiosk=1` de la dirección, así que un enlace copiado de otro sitio no cambia nada.

## La dirección

`python bin/monitor_cli.py kiosk [PRESET] [--account ID]` la imprime; no necesita monitor en marcha. Por ejemplo, `kiosk ops` imprime:

```
http://127.0.0.1:8765/?screen=1&tabs=now,al,charts&chrome=0&kiosk=1&scale=150
```

| Parámetro | Significado |
|---|---|
| `kiosk=1` | enciende el perfil (solo cuando `kiosk.enabled` está encendido) |
| `scale=%` | el tamaño de letra, de 100 a 400 (un valor fuera del rango se lleva a él) |
| `contrast=1` / `contrast=0` | contraste alto encendido o apagado para esta ventana (el ajuste `kiosk.high_contrast` es el predeterminado) |
| `safe=PORCENTAJE` | el margen de seguridad de esta ventana, de 0 a 10 (el ajuste `kiosk.safe_margin_percent` es el valor por defecto) |
| `fit=1` / `fit=0` | la letra crece con la ventana en esta ventana, o no (el ajuste `kiosk.scale_with_window` es el valor por defecto) |
| `rotate=SECONDS` | pasar por las pestañas de `tabs=` (el parámetro que ya existía; el comando lo añade solo cuando la rotación está encendida) |
| `chrome=0`, `screen=`, `tabs=`, `account=` | los que ya existían |

## Presets

| Preset | Pestañas |
|---|---|
| `ops` | Ahora, Alertas, Gráficos |
| `team` | Alertas, Salud del equipo |
| `release` | Ahora, Repositorios, Informes |
| `quiet` | solo Alertas |

## Ajustes (Ajustes, Línea de comandos y Kiosco)

| Ajuste | Por defecto | Significado |
|---|---|---|
| `kiosk.enabled` | apagado | enciende el perfil |
| `kiosk.font_scale_percent` | 150 | el tamaño de letra, de 100 a 400 |
| `kiosk.high_contrast` | apagado | fondo negro y líneas blancas |
| `kiosk.rotate_views` | apagado | un preset con varias pestañas cambia de pestaña solo; apagado, la pantalla enseña la primera pestaña del preset |
| `kiosk.rotate_seconds` | 30 | cuánto se queda cada pestaña (de 5 a 600) |
| `screens.version_check_seconds` | 300 | cada cuánto la página consulta `/api/version` y se recarga sola si el monitor se actualizó o se reinició (0 = nunca; el mínimo es 30) |
| `kiosk.safe_margin_percent` | 0 | la parte de cada borde, en porcentaje, que la página deja libre para un televisor que recorta el borde (overscan); de 0 a 10 |
| `kiosk.scale_with_window` | apagado | el tamaño de letra de arriba es el de una ventana de 1080 px en su lado corto; encendido, crece con la ventana, así que un televisor 4K se ve como uno Full HD |

El tamaño se aplica con el zoom de la página, así que cada cifra y cada tabla crecen juntas. Un valor fuera de su rango no es un error: se sustituye por el predeterminado.
