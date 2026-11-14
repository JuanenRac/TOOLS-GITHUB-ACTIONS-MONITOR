<!--
  Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
  GPL-3.0-or-later - see LICENSE
-->

[🇺🇸 English](CONSOLE_TOOLS.md) | **🇪🇸 Español** | [🇫🇷 Français](CONSOLE_TOOLS_fra.md) | [🇮🇹 Italiano](CONSOLE_TOOLS_ita.md) | [🇩🇪 Deutsch](CONSOLE_TOOLS_deu.md) | [🇨🇳 简体中文](CONSOLE_TOOLS_zho.md) | [🇯🇵 日本語](CONSOLE_TOOLS_jpn.md) | [🇵🇹 Português](CONSOLE_TOOLS_por.md)

# Herramientas de consola: linter de workflows y vista de consola

Dos herramientas de línea de comandos, opcionales. El monitor no necesita ningún paquete; la vista de consola usa Rich cuando la pides.

## El linter de workflows: `bin/lint_workflows.py`

- `py -3 bin/lint_workflows.py [RUTA ...] [--json] [--fail-on info|warn|bad]` revisa `.github/workflows/*.yml` antes de subir. Sin ruta mira la carpeta actual. Solo abre archivos.
- Reglas (cada una se puede apagar y cambiar de gravedad en la pestaña Configuración, subpestaña Linter de workflows): `unpinned_uses` (una acción sin fijar a un SHA de commit completo), `permissions` (sin bloque `permissions:`, o `write-all`), `secrets_in_clear` (algo que parece un token o clave escrito en el archivo), `injection` (texto de un tercero pegado en un script `run:`) y `pr_target` (`pull_request_target` con descarga del código del pull request).
- El código de salida es 1 cuando un hallazgo alcanza `--fail-on` (por defecto `bad`), así que sirve de hook previo al push. Cuando el monitor ve tus clones, añade además una línea al parte diario.
- Un valor que parece un secreto se clasifica sin imprimirlo ni guardarlo nunca: un formato de token conocido o una cadena larga de alta entropía es grave (`bad`), un relleno legible como `placeholder`, `dummy`, `changeme` o `ci` es solo información, cualquier otra cosa es un aviso, y `${{ secrets.X }}`, `${X}` o un valor vacío no es hallazgo. Para silenciar un hallazgo escribe un comentario en su línea o en la anterior: `# monitor-lint: ignore secrets_in_clear porque es un relleno para docker compose config` (un nombre de regla o `all`); o apunta patrones `repositorio:archivo:regla`, con `*`, en el ajuste `lint.ignore`.


## La vista de consola: `bin/tui.py`

- `pip install rich` y después `py -3 bin/tui.py [--port 8765] [--refresh 5] [--once] [--theme dark|light]`. Dibuja una cuadrícula en vivo con lo que corre, los workflows en rojo, la cola de firma y el parte, leídos del monitor en marcha en `127.0.0.1` (no gasta cuota de GitHub).
- Es de solo lectura: no hay tecla que relance, cierre o escriba nada. Sin Rich dice cómo instalarlo y sale con código 3; el monitor y sus pruebas nunca necesitan Rich.
- La aplicación interactiva de terminal `bin/tui_textual.py` (`pip install textual`; añade `--lite` para la edición lite) edita en la pestaña Ajustes los ajustes simples de los grupos que lista, las **listas** (elementos separados por comas: `a, b, c`) y los **mapas de números** (`name=3, other=5`); el servidor vuelve a comprobar cada valor, y las opciones de seguridad solo se cambian en la página.
