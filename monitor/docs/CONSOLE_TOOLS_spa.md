<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CONSOLE_TOOLS.md) | **🇪🇸 Español** | [🇫🇷 Français](CONSOLE_TOOLS_fra.md) | [🇮🇹 Italiano](CONSOLE_TOOLS_ita.md) | [🇩🇪 Deutsch](CONSOLE_TOOLS_deu.md) | [🇨🇳 简体中文](CONSOLE_TOOLS_zho.md) | [🇯🇵 日本語](CONSOLE_TOOLS_jpn.md) | [🇵🇹 Português](CONSOLE_TOOLS_por.md)

# Herramientas de consola: linter de workflows y vista de consola

Dos herramientas de línea de comandos, opcionales. El monitor no necesita ningún paquete; la vista de consola usa Rich cuando la pides.

## El linter de workflows: `lint_workflows.py`

- `py -3 lint_workflows.py [RUTA ...] [--json] [--fail-on info|warn|bad]` revisa `.github/workflows/*.yml` antes de subir. Sin ruta mira la carpeta actual. Solo abre archivos.
- Reglas (cada una se puede apagar y cambiar de gravedad en la pestaña Configuración, subpestaña Linter de workflows): `unpinned_uses` (una acción sin fijar a un SHA de commit completo), `permissions` (sin bloque `permissions:`, o `write-all`), `secrets_in_clear` (algo que parece un token o clave escrito en el archivo), `injection` (texto de un tercero pegado en un script `run:`) y `pr_target` (`pull_request_target` con descarga del código del pull request).
- El código de salida es 1 cuando un hallazgo alcanza `--fail-on` (por defecto `bad`), así que sirve de hook previo al push. Cuando el monitor ve tus clones, añade además una línea al parte diario.


## La vista de consola: `tui.py`

- `pip install rich` y después `py -3 tui.py [--port 8765] [--refresh 5] [--once] [--theme dark|light]`. Dibuja una cuadrícula en vivo con lo que corre, los workflows en rojo, la cola de firma y el parte, leídos del monitor en marcha en `127.0.0.1` (no gasta cuota de GitHub).
- Es de solo lectura: no hay tecla que relance, cierre o escriba nada. Sin Rich dice cómo instalarlo y sale con código 3; el monitor y sus pruebas nunca necesitan Rich.
