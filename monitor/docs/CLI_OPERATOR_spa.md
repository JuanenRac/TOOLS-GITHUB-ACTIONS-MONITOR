<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CLI_OPERATOR.md) | **🇪🇸 Español** | [🇫🇷 Français](CLI_OPERATOR_fra.md) | [🇮🇹 Italiano](CLI_OPERATOR_ita.md) | [🇩🇪 Deutsch](CLI_OPERATOR_deu.md) | [🇨🇳 简体中文](CLI_OPERATOR_zho.md) | [🇯🇵 日本語](CLI_OPERATOR_jpn.md) | [🇵🇹 Português](CLI_OPERATOR_por.md)

# La línea de comandos para el operador

Lo básico de `monitor_cli.py` está en [CLI_spa.md](CLI_spa.md). Esta página es para quien vive en una terminal: cómo se escriben las respuestas (`--format`), cómo vigilar (`watch`), cómo completar los comandos (`completions`), los códigos de salida y la dirección para una TV (`kiosk`). Todo lo de aquí lee la API del monitor de este ordenador (o la de `--url`); nada escribe en GitHub y nada gasta la cuota.

## Formatos: `--format`

| Formato | Qué obtienes |
|---|---|
| `text` | lo que cada comando ha escrito siempre. Es el predeterminado. |
| `table` | los registros en columnas que caben en el ancho de la terminal (los caracteres japoneses y chinos cuentan como dos celdas). No hay color, así que se respeta `NO_COLOR`. |
| `plain` | un registro por línea, los campos separados por un tabulador, sin cabecera: para `grep`, `cut` y `awk`. Un tabulador o un salto de línea dentro de un texto pasa a ser un espacio. |
| `json` | el documento `{"ok", "exit", "data"}`. `--json` es lo mismo. |
| `ndjson` | un objeto JSON por línea, uno por registro (una alerta, una cuenta, un repositorio, un evento). Un comando que responde una sola cosa (`status`, `health`) da una línea. |

`--format` gana a `--json`, y los dos ganan al ajuste `cli.default_format` (por defecto `text`). Los tres formatos estructurados salen del mismo documento que `--json`, así que nunca discrepan. Una lista vacía no imprime nada en `ndjson` ni en `plain`.

## `watch`: la misma lectura una y otra vez

```
python bin/monitor_cli.py watch status
python bin/monitor_cli.py watch alerts --interval 10 --format table
python bin/monitor_cli.py watch alerts --exit-on-change --format ndjson
```

`watch status|alerts` repite la lectura del comando. Lee la API del monitor, no GitHub, así que un intervalo corto no gasta la cuota. Las opciones:

- `--interval SEGUNDOS`: la pausa entre dos lecturas. El suelo es el ajuste `cli.watch.min_interval_seconds` (2 por defecto): un intervalo menor se sube hasta él. Sin `--interval` la pausa es `cli.watch.default_interval_seconds` (5).
- `--once`: una lectura y salir (el código de salida es el del comando).
- `--exit-on-change`: el bucle termina con el código de salida **6** cuando lo que vigila no es lo que era en la primera lectura (el conjunto de alertas o las cifras del estado). Un reloj que avanza no es un cambio. Sin la opción el código 6 nunca aparece.
- `--no-clear`: no borrar la pantalla entre dos lecturas (solo se borra en una terminal y solo en `text` y `table`).
- Un monitor que no se puede leer se reintenta con una pausa cada vez mayor (el intervalo duplicado, como máximo un minuto) y el error va a la salida de error. **Ctrl-C** termina el bucle con el código 0.

## `completions`: completar los comandos

```
python bin/monitor_cli.py completions bash > ~/.local/share/bash-completion/completions/monitor_cli.py
python bin/monitor_cli.py completions zsh  > "${fpath[1]}/_monitor_cli"
python bin/monitor_cli.py completions fish > ~/.config/fish/completions/monitor_cli.py.fish
python bin/monitor_cli.py completions powershell | Out-String | Invoke-Expression
```

El script se escribe a partir del analizador real de la línea de comandos, así que ofrece exactamente los comandos, palabras y opciones que existen: una opción nueva no puede quedar olvidada y una prueba compara ambos. El comando solo **imprime**; no edita ningún fichero tuyo y no necesita monitor. Pon la salida donde tu intérprete lee las compleciones, como arriba.

## Códigos de salida

| Código | Significado |
|---|---|
| 0 | todo bien (también Ctrl-C en `watch`) |
| 1 | uso incorrecto del comando |
| 2 | no se puede alcanzar el monitor |
| 3 | el monitor o GitHub rechaza la credencial |
| 4 | el monitor responde pero está degradado (sin conexión, cuota agotada, aún sin datos) o la respuesta no se puede leer |
| 5 | `alerts --fail-on NIVEL` encontró alertas de ese nivel o peor |
| 6 | `watch --exit-on-change` vio un cambio (solo cuando se da esa opción) |

Los códigos 0 a 5 son los de [CLI_spa.md](CLI_spa.md); una prueba mantiene esta tabla y el código de acuerdo.

## Ejemplos con `jq`

Estos ejemplos usan solo campos que forman parte de la forma estable de las respuestas, y una prueba los ejecuta contra un monitor de mentira (cuando `jq` está instalado).

```
monitor_cli.py alerts --json | jq -r '.data.alerts[] | select(.level=="critical") | .repo'
monitor_cli.py alerts --format ndjson | jq -r '.code'
monitor_cli.py status --json | jq '.data.red_workflows'
monitor_cli.py team --json | jq -r '.data.ranking[] | .repo'
```

## `kiosk`: la dirección para una TV o una pared

`monitor_cli.py kiosk [ops|team|release|quiet]` imprime la dirección del monitor para una pantalla que nadie toca. Véase [KIOSK_spa.md](KIOSK_spa.md).

## Ajustes

| Ajuste | Por defecto | Significado |
|---|---|---|
| `cli.default_format` | `text` | el formato cuando no se da `--format` ni `--json`: `text`, `table`, `plain`, `json` o `ndjson` |
| `cli.watch.min_interval_seconds` | 2 | la pausa más corta de `watch` (de 1 a 3600) |
| `cli.watch.default_interval_seconds` | 5 | la pausa de `watch` cuando no se da `--interval` (de 1 a 3600) |

## Lo que esta versión no hace

- `completions` no tiene `--install`: nunca escribe en los ficheros de un usuario.
- No hay comando `proposals`: el monitor aún no tiene ruta de propuestas sobre la que actuar.
